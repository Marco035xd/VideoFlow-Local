"""Stream a playlist/channel into the existing download manager in a background job."""
import threading
import uuid
from pathlib import Path

import yt_dlp
from download_options import validate_options, VIDEO_FORMATS, AUDIO_FORMATS


class CollectionJobs:
    def __init__(self, manager, settings, environment, source_for_url, describe_error=None):
        self.manager, self.settings = manager, settings
        self.environment, self.source_for_url = environment, source_for_url
        self.describe_error = describe_error or (lambda exc, source: str(exc)[:500])
        self.jobs, self.lock = {}, threading.RLock()

    def start(self, payload):
        url = str(payload.get('url', '')).strip()
        if self.source_for_url(url) != 'YouTube':
            raise ValueError('Pega el enlace de una lista o un canal de YouTube.')
        mode, fmt = payload.get('mode', 'video_audio'), payload.get('format', 'mp4')
        if mode not in {'audio', 'video_only', 'video_audio'} or fmt not in (AUDIO_FORMATS if mode == 'audio' else VIDEO_FORMATS - {'vob'}):
            raise ValueError('Formato de la colección no válido.')
        quality = int(payload.get('quality', 0))
        if (mode == 'audio' and quality not in ({128, 192, 320} if fmt in {'mp3', 'ogg'} else {0})) or (mode != 'audio' and quality not in {0, 144, 240, 360, 480, 720, 1080, 1440, 2160, 4320}):
            raise ValueError('Calidad de la colección no válida.')
        advanced = validate_options({**payload, 'mode': mode, 'format': fmt})
        from youtube_session import validate_choice
        browser = validate_choice(payload.get('browser') or '')
        folder = Path(payload.get('folder') or self.settings.folder_for('YouTube')).expanduser().resolve()
        folder.mkdir(parents=True, exist_ok=True)
        identifier = uuid.uuid4().hex
        job = dict(id=identifier, title='Leyendo colección…', status='Leyendo', added=0, skipped=0,
                   error='', task_ids=[], cancel=threading.Event())
        with self.lock:
            self.jobs[identifier] = job
        self.settings.remember_folder('YouTube', str(folder))
        base = dict(format=fmt, mode=mode, quality=str(quality), folder=str(folder), advanced=advanced, browser=browser)
        threading.Thread(target=self._run, args=(job, url, base), daemon=True).start()
        return identifier

    def _run(self, job, url, base):
        class StopCollection(Exception):
            pass

        def check(*args, **kwargs):
            if job['cancel'].is_set():
                raise StopCollection()

        def entries(info):
            if not info:
                with self.lock:
                    job['skipped'] += 1
                return
            if info.get('_type') in ('playlist', 'multi_video') or 'entries' in info:
                for entry in info.get('entries') or []:
                    check()
                    yield from entries(entry)
            else:
                yield info
        try:
            opts = dict(quiet=True, no_warnings=True, extract_flat='in_playlist', lazy_playlist=True,
                        ignoreerrors='only_download', skip_download=True, socket_timeout=25, retries=3,
                        match_filter=check, **self.environment('YouTube', base.get('browser', '')))
            seen = set()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError('No se pudo leer la colección. Comprueba que sea pública o accesible.')
                with self.lock:
                    job['title'] = info.get('title') or 'Colección de YouTube'
                for entry in entries(info):
                    check()
                    video_url = entry.get('webpage_url') or entry.get('url') or ''
                    if self.source_for_url(video_url) != 'YouTube' and entry.get('id'):
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    if video_url in seen or self.source_for_url(video_url) != 'YouTube' or entry.get('availability') in {'private', 'premium_only', 'subscriber_only'}:
                        with self.lock:
                            job['skipped'] += 1
                        continue
                    seen.add(video_url)
                    with self.lock:
                        check()
                        try:
                            task = self.manager.add({**base, 'url': video_url, 'original_url': video_url,
                                                     'title': entry.get('title') or 'Video de colección',
                                                     'video_id': entry.get('id') or '', 'duration': entry.get('duration') or 0})
                        except (ValueError, TypeError) as exc:
                            job['skipped'] += 1
                            job['error'] = f"Última entrada omitida: {exc}"
                            continue
                        job['task_ids'].append(task.id)
                        job['added'] += 1
                with self.lock:
                    job['status'] = 'Completado' if job['added'] else 'Error'
                    if not job['added']:
                        job['error'] = 'No se encontraron videos disponibles.'
        except StopCollection:
            with self.lock:
                job['status'] = 'Cancelado'
        except Exception as exc:
            with self.lock:
                job['status'] = 'Cancelado' if job['cancel'].is_set() else 'Error'
                job['error'] = '' if job['cancel'].is_set() else self.describe_error(exc, 'YouTube')

    def list(self):
        with self.lock:
            return [{key: value for key, value in job.items() if key not in {'cancel', 'task_ids'}} for job in self.jobs.values()]

    def cancel(self, identifier, *, cancel_downloads=True):
        with self.lock:
            job = self.jobs[identifier]
            job['cancel'].set()
            job['status'] = 'Cancelado'
            if cancel_downloads:
                for task_id in job['task_ids']:
                    if self.manager.get(task_id):
                        self.manager.cancel(task_id)


def register(app, manager, settings, environment, source_for_url, describe_error=None):
    from flask import jsonify, request
    jobs = CollectionJobs(manager, settings, environment, source_for_url, describe_error)

    @app.route('/api/collections', methods=['GET', 'POST'])
    def collections():
        if request.method == 'GET':
            return jsonify(ok=True, collections=jobs.list())
        try:
            return jsonify(ok=True, id=jobs.start(request.get_json() or {})), 202
        except (ValueError, TypeError, OSError) as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/collections/<identifier>/cancel')
    def cancel_collection(identifier):
        try:
            jobs.cancel(identifier)
            return jsonify(ok=True)
        except KeyError:
            return jsonify(ok=False, error='Colección no encontrada.'), 404

    return jobs
