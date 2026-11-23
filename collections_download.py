"""Stream a playlist/channel into the existing download manager in a background job."""
import threading
import uuid
from pathlib import Path

import yt_dlp
from download_options import validate_options, VIDEO_FORMATS, AUDIO_FORMATS
from youtube_session import validate_choice


def collection_options(payload, source_for_url):
    url = str(payload.get('url', '')).strip()
    if source_for_url(url) != 'YouTube':
        raise ValueError('Pega el enlace de una lista o un canal de YouTube.')
    mode, fmt = payload.get('mode', 'video_audio'), payload.get('format', 'mp4')
    if mode not in {'audio', 'video_only', 'video_audio'} or fmt not in (AUDIO_FORMATS if mode == 'audio' else VIDEO_FORMATS - {'vob'}):
        raise ValueError('Formato de la colección no válido.')
    quality = int(payload.get('quality', 0))
    audio_qualities = {128, 192, 320} if fmt in {'mp3', 'ogg'} else {0}
    video_qualities = {0, 144, 240, 360, 480, 720, 1080, 1440, 2160, 4320}
    if quality not in (audio_qualities if mode == 'audio' else video_qualities):
        raise ValueError('Calidad de la colección no válida.')
    advanced = validate_options({**payload, 'mode': mode, 'format': fmt})
    browser = validate_choice(payload.get('browser') or '')
    return url, dict(format=fmt, mode=mode, quality=str(quality), advanced=advanced, browser=browser)


def collection_entries(info, source_for_url, check):
    def flatten(entry):
        check()
        if entry and (entry.get('_type') in ('playlist', 'multi_video') or 'entries' in entry):
            for child in entry.get('entries') or ():
                yield from flatten(child)
        else:
            yield entry

    seen = set()
    for entry in flatten(info):
        if not entry or entry.get('availability') in {'private', 'premium_only', 'subscriber_only'}:
            yield None, ''
            continue
        url = entry.get('webpage_url') or entry.get('url') or ''
        if source_for_url(url) != 'YouTube' and entry.get('id'):
            url = f"https://www.youtube.com/watch?v={entry['id']}"
        if url in seen or source_for_url(url) != 'YouTube':
            yield None, ''
            continue
        seen.add(url)
        yield entry, url


class CollectionJobs:
    def __init__(self, manager, settings, environment, source_for_url, describe_error=None):
        self.manager, self.settings = manager, settings
        self.environment, self.source_for_url = environment, source_for_url
        self.describe_error = describe_error or (lambda exc, source: str(exc)[:500])
        self.jobs, self.lock = {}, threading.RLock()

    def start(self, payload):
        url, base = collection_options(payload, self.source_for_url)
        folder = Path(payload.get('folder') or self.settings.folder_for('YouTube')).expanduser().resolve()
        folder.mkdir(parents=True, exist_ok=True)
        identifier = uuid.uuid4().hex
        job = dict(id=identifier, title='Leyendo colección…', status='Leyendo', added=0, skipped=0,
                   error='', task_ids=[], cancel=threading.Event())
        with self.lock:
            self.jobs[identifier] = job
        self.settings.remember_folder('YouTube', str(folder))
        base['folder'] = str(folder)
        threading.Thread(target=self._run, args=(job, url, base), daemon=True).start()
        return identifier

    def _run(self, job, url, base):
        class StopCollection(Exception):
            pass

        def check(*args, **kwargs):
            if job['cancel'].is_set():
                raise StopCollection()

        try:
            opts = dict(quiet=True, no_warnings=True, extract_flat='in_playlist', lazy_playlist=True,
                        ignoreerrors='only_download', skip_download=True, socket_timeout=25, retries=3,
                        match_filter=check, **self.environment('YouTube', base.get('browser', '')))
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError('No se pudo leer la colección. Comprueba que sea pública o accesible.')
                with self.lock:
                    job['title'] = info.get('title') or 'Colección de YouTube'
                for entry, video_url in collection_entries(info, self.source_for_url, check):
                    if entry is None:
                        with self.lock:
                            job['skipped'] += 1
                        continue
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
    from collection_estimates import CollectionEstimates

    jobs = CollectionJobs(manager, settings, environment, source_for_url, describe_error)
    estimates = CollectionEstimates(environment, source_for_url)

    @app.post('/api/collections/estimate')
    def estimate_collection():
        try:
            return jsonify(ok=True, id=estimates.start(request.get_json() or {})), 202
        except (ValueError, TypeError) as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.route('/api/collections/estimate/<identifier>', methods=['GET', 'DELETE'])
    def collection_estimate(identifier):
        if request.method == 'DELETE':
            estimates.cancel(identifier)
            return jsonify(ok=True)
        result = estimates.result(identifier)
        if result is None:
            return jsonify(ok=False, error='La estimación ya no está disponible.'), 404
        return jsonify(ok=True, **result)

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
