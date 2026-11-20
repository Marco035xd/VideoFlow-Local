"""Check Windows queue recovery with isolated data and a local HTTP Range server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch

from yt_dlp import YoutubeDL
from yt_dlp.extractor.common import InfoExtractor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def wait_for_worker(manager):
    with manager.condition:
        assert manager.condition.wait_for(lambda: not manager.running_tasks, 12)


def main():
    with tempfile.TemporaryDirectory(prefix='videoflow-queue-check-') as directory:
        root = Path(directory)
        os.environ['VIDEOFLOW_DATA_DIR'] = str(root / 'data')
        import app

        movie = root / 'fixture.mp4'
        subprocess.run([app.find_tool('ffmpeg'), '-v', 'error', '-f', 'lavfi',
                        '-i', 'testsrc2=s=320x240:d=2', '-c:v', 'libx264', str(movie)], check=True)
        body = movie.read_bytes()
        offset = len(body) // 3
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requested = self.headers.get('Range')
                requests.append(requested)
                start = int(requested.split('=')[1].split('-')[0]) if requested else 0
                self.send_response(206 if requested else 200)
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Content-Length', str(len(body) - start))
                if requested:
                    self.send_header('Content-Range', f'bytes {start}-{len(body) - 1}/{len(body)}')
                self.end_headers()
                self.wfile.write(body[start:])

            def log_message(self, *_):
                pass

        url = 'https://www.reddit.com/comments/fixture/'
        manager = app.download_manager
        started = threading.Event()
        written = []

        def interrupted(task, attempt, checkpoint, *_):
            partial = root / f'Recover [fixture] [original] [{task.id}].mp4.part'
            partial.write_bytes(body[:offset])
            written.append(partial)
            started.set()
            assert task.cancel_event.wait(8)
            checkpoint(task)

        with patch.object(app, 'run_with_recovery', interrupted):
            original = manager.add(dict(url=url, format='mp4', quality='0', folder=str(root), title='Recover'))
            assert started.wait(8)
            manager.shutdown()
            wait_for_worker(manager)
        assert written[0].stat().st_size == offset

        history = app.HistoryStore(app.DB_FILE)
        private = app.DownloadTask('private', url, 'fixture', 'Private title', '', 0, 'mp4', '0',
                                   str(root), advanced={'incognito': True})
        history.save_pending(private)
        cookie_job = app.DownloadTask('cookies', 'https://www.youtube.com/watch?v=AAAAAAAAAAA',
                                      'AAAAAAAAAAA', 'Cookie job', '', 0, 'mp4', '0', str(root),
                                      browser='cookies:' + 'a' * 32)
        history.save_pending(cookie_job)
        assert all('Private title' not in row['payload'] and 'cookies:aaaaaaaa' not in row['payload']
                   for row in history.pending_downloads())

        # Simulate a restart after an atomic move committed the file but before history was recorded.
        staged, target = root / 'saved.stage', root / 'chosen-name.mp4'
        staged.write_bytes(body)
        saved = app.DownloadTask('saved', url, 'fixture', 'Already saved', '', 2, 'mp4', '0', str(root),
                                 source='Reddit', save_path=str(target))
        history.save_pending(saved)
        history.prepare_output(saved, staged, target)
        staged.replace(target)

        recovered = app.DownloadManager(app.settings_store, history)
        task = recovered.get(original.id)
        assert (task.status, task.quality, task.folder, task.url) == ('Interrumpido', '0', str(root), url)
        assert recovered.get('private') is None
        assert recovered.get('saved').status == 'Completado'
        assert recovered.get('saved').final_path == str(target)
        assert recovered.get('cookies').as_dict()['needs_cookie_file']
        try:
            recovered.resume('cookies')
            raise AssertionError('Expected a request for a new cookie file')
        except ValueError:
            pass
        recovered.cancel('cookies')

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()

            class FixtureIE(InfoExtractor):
                _VALID_URL = r'https://www\.reddit\.com/comments/(?P<id>fixture)/'

                def _real_extract(self, _):
                    return dict(id='fixture', title='Recover', duration=2, formats=[
                        dict(url=f'http://127.0.0.1:{server.server_port}/fixture.mp4', ext='mp4',
                             format_id='original', vcodec='h264', acodec='none', height=240),
                    ])

            def fixture_downloader(options):
                downloader = YoutubeDL(options, auto_init=False)
                downloader.add_info_extractor(FixtureIE())
                return downloader

            finished = threading.Event()
            download = recovered._download

            def tracked_download(task):
                try:
                    download(task)
                finally:
                    finished.set()

            with patch.object(app.yt_dlp, 'YoutubeDL', fixture_downloader), \
                    patch.object(recovered, '_download', tracked_download):
                recovered.resume(original.id)
                assert finished.wait(15)
                wait_for_worker(recovered)
            assert any(request and request.startswith(f'bytes={offset}-') for request in requests), requests
            server.shutdown()
            server_thread.join()
        assert recovered.get(original.id).status == 'Completado', recovered.get(original.id).error
        assert Path(recovered.get(original.id).final_path).is_file()
        assert history.pending_downloads() == []
        again = app.DownloadManager(app.settings_store, history)
        assert not again.list()
        assert sorted(row['task_id'] for row in history.list()) == sorted([original.id, 'saved'])

        assert app.classify_failure('Connection to sample timed out') == 'connection'
        assert app.classify_failure('HTTP Error 403: Forbidden') == 'access'
        assert app.classify_failure('Postprocessing: ffmpeg exited with status 1') == 'processing'
        assert app.classify_failure('Requested format is not available') == 'format'
        assert app.classify_failure(PermissionError('Destination')) == 'storage'
        print('PASS: restart, real HTTP Range continuation, completed output recovery, incognito, session privacy and diagnostics.')


if __name__ == '__main__':
    main()
