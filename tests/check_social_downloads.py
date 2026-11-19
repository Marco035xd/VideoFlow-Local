"""Exercise Reddit and Instagram through the queue using locally generated media."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

from yt_dlp import YoutubeDL
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class QuietServer(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def wait_for_task(client, task_id):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        task = next(task for task in client.get('/api/downloads').json['downloads'] if task['id'] == task_id)
        if task['status'] in {'Completado', 'Error', 'Cancelado'} and task_id not in app.download_manager.running_tasks:
            return task
        time.sleep(.05)
    raise AssertionError(f'Download did not finish: {task_id}')


with tempfile.TemporaryDirectory(prefix='videoflow-social-') as directory:
    root = Path(directory)
    os.environ['VIDEOFLOW_DATA_DIR'] = str(root / 'data')
    import app

    client = app.app.test_client()
    assert 'data-source="reddit"' in client.get('/').get_data(as_text=True)
    assert 'data-source="instagram"' in client.get('/').get_data(as_text=True)
    assert app.source_for_url('https://redd.it/fixture') == 'Reddit'
    assert app.source_for_url('https://v.redd.it/fixture/HLSPlaylist.m3u8') == 'Reddit'
    assert app.source_for_url('https://www.instagram.com/reel/fixture/') == 'Instagram'
    for url in ('https://reddit.com.example.org/', 'https://instagram.com@elsewhere.test/',
                'ftp://instagram.com/reel/fixture/', 'https://user@instagram.com/reel/fixture/'):
        assert client.post('/api/analyze', json={'url':url}).status_code == 400

    for name, has_audio in (('silent.mp4', False), ('with-audio.mp4', True)):
        command = [app.find_tool('ffmpeg'), '-v', 'error', '-f', 'lavfi',
                   '-i', 'color=c=black:s=256x454:r=10:d=1']
        if has_audio:
            command += ['-f', 'lavfi', '-i', 'sine=frequency=220:duration=1']
        subprocess.run([*command, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(root / name)], check=True)

    with ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietServer, directory=directory)) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base_url = f'http://127.0.0.1:{server.server_port}'
        reddit = 'https://www.reddit.com/r/example/comments/fixture/'
        reel = 'https://www.instagram.com/reel/fixture/'
        protected = 'https://www.reddit.com/comments/protected/'
        photo = 'https://www.instagram.com/p/still/'
        calls = []

        class FixtureIE(InfoExtractor):
            _VALID_URL = r'https://www\.(?:reddit\.com|instagram\.com)/.+'

            def _real_extract(self, url):
                if url == protected:
                    self.raise_login_required('Account authentication is required')
                if url == photo:
                    self.raise_no_formats('There is no video in this post', expected=True)
                source = app.source_for_url(url)
                audio = source == 'Instagram'
                info = {
                    'id':'first', 'title':f'{source} fixture', 'duration':1,
                    'formats':[{'url':base_url + ('/with-audio.mp4' if audio else '/silent.mp4'),
                                'width':256, 'height':454, 'format_id':'original', 'ext':'mp4',
                                'vcodec':'h264', 'acodec':'aac' if audio else 'none'}],
                }
                return (self.playlist_result([info, dict(info, id='second')], 'carousel') if audio else info)

        def fixture_downloader(options):
            options = options.copy()
            calls.append(dict(options))
            options.pop('cookiesfrombrowser', None)
            downloader = YoutubeDL(options, auto_init=False)
            downloader.add_info_extractor(FixtureIE())
            return downloader

        with patch.object(app.yt_dlp, 'YoutubeDL', side_effect=fixture_downloader):
            rejected = client.post('/api/analyze', json={'url':protected})
            assert rejected.status_code == 422 and 'limitó el acceso' in rejected.json['error']
            rejected = client.post('/api/analyze', json={'url':photo})
            assert rejected.status_code == 422 and 'no contiene un video' in rejected.json['error']

            folders = {key: str(root / key) for key in ('reddit', 'instagram')}
            assert client.put('/api/settings', json={'platform_folders':folders}).status_code == 200
            for link, source, browser in ((reddit, 'Reddit', ''), (reel, 'Instagram', 'firefox')):
                response = client.post('/api/analyze', json={'url':link, 'browser':browser})
                assert response.status_code == 200, response.json
                video = response.json['video']
                assert video['source'] == source and video['id'] == 'first' and video['url'] == link
                assert video['video_options'][0]['value'] == '454'
                response = client.post('/api/downloads', json={
                    'url':video['url'], 'original_url':link, 'browser':video['browser'], 'video_id':video['id'],
                    'title':video['title'], 'quality':'454', 'format':'mp4', 'mode':'video_audio',
                    'folder':folders[source.lower()],
                })
                assert response.status_code == 201, response.json
                task = wait_for_task(client, response.json['download']['id'])
                assert task['status'] == 'Completado', task
                streams = subprocess.run([app.find_tool('ffprobe'), '-v', 'error', '-show_entries', 'stream=codec_type',
                                          '-of', 'json', task['final_path']], capture_output=True, check=True)
                expected = {'audio','video'} if source == 'Instagram' else {'video'}
                assert {row['codec_type'] for row in json.loads(streams.stdout)['streams']} == expected
                assert len(list(Path(task['folder']).glob('*.mp4'))) == 1

            response = client.post('/api/downloads', json={
                'url':protected, 'quality':'0', 'format':'mp4', 'folder':folders['reddit'],
            })
            task_id = response.json['download']['id']
            assert wait_for_task(client, task_id)['can_retry']
            assert client.post(f'/api/downloads/{task_id}/retry', json={}).status_code == 200
            assert wait_for_task(client, task_id)['status'] == 'Error'

        assert all(call['playlist_items'] == '1' for call in calls)
        assert len([call for call in calls if call.get('cookiesfrombrowser') == ('firefox',)]) == 2
        assert all(call.get('cookiesfrombrowser') is None for call in calls if call.get('cookiesfrombrowser') != ('firefox',))
        assert {record['source'] for record in client.get('/api/history').json['history']} == {'Reddit','Instagram'}
        settings = app.SettingsStore(app.settings_store.path).load()
        assert all(settings['platform_folders'][key] == path for key, path in folders.items())
        server.shutdown()

print('OK: Reddit sin audio, primer video de carrusel de Instagram, calidad original, sesión, destinos, historial y reintento.')
