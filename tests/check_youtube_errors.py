"""Check YouTube availability messages in analysis and collection downloads."""
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import MagicMock, patch

from yt_dlp.utils import DownloadError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    with tempfile.TemporaryDirectory(prefix='videoflow-youtube-errors-') as directory:
        os.environ['VIDEOFLOW_DATA_DIR'] = str(Path(directory) / 'data')
        import app
        from localization import translate

        cases = {
            'AAAAAAAAAAA': ('Sign in to confirm your age. This video may be inappropriate for some users.',
                            'Este video tiene restricción de edad.'),
            'BBBBBBBBBBB': ('Private video. If the owner of this video has granted you access, please sign in.',
                            'Este video es privado y no está disponible para el público.'),
            'CCCCCCCCCCC': ('Video unavailable. This video has been removed by the uploader.',
                            'Este video fue retirado o no está disponible en YouTube.'),
            'DDDDDDDDDDD': ('Sign in to confirm you’re not a bot.', 'YouTube solicita confirmar el acceso'),
        }
        video_urls = {f'https://www.youtube.com/watch?v={video_id}': video_id for video_id in cases}
        playlist = 'https://www.youtube.com/playlist?list=PLfixture'

        def extract_info(url, download):
            if url == playlist:
                return {'title': 'Fixture collection', 'entries': [
                    {'id': video_id, 'url': video_url, 'title': 'Fixture video'}
                    for video_url, video_id in video_urls.items()
                ]}
            video_id = video_urls[url]
            reason, _ = cases[video_id]
            raise DownloadError(f'ERROR: [youtube] {video_id}: {reason} Use --cookies for the authentication.')

        downloader = MagicMock()
        downloader.__enter__.return_value.extract_info.side_effect = extract_info
        client = app.app.test_client()

        with patch.object(app.yt_dlp, 'YoutubeDL', return_value=downloader), \
                patch.object(app, 'YouTubeCDNDownloader', return_value=downloader), \
                patch.object(app, 'find_tool', return_value='fixture.exe'):
            analysis_errors = {}
            for url, video_id in video_urls.items():
                response = client.post('/api/analyze', json={'url': url})
                assert response.status_code == 422, response.json
                message = response.json['error']
                assert message.startswith(cases[video_id][1]), message
                assert '--cookies' not in message
                assert all(translate(message, language) != message for language in ('en', 'pt'))
                analysis_errors[video_id] = message

            response = client.post('/api/collections', json={'url': playlist, 'folder': directory})
            assert response.status_code == 202, response.json
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                downloads = client.get('/api/downloads').json['downloads']
                if len(downloads) == len(cases) and all(task['can_retry'] for task in downloads):
                    break
                time.sleep(.05)
            else:
                raise AssertionError(f'Collection downloads did not finish: {downloads}')

            for task in downloads:
                assert task['error'] == analysis_errors[task['video_id']], task
                assert task['diagnostic'] == 'access', task

        # An archived error created by an older version uses the same message when restored.
        old_job = app.download_manager.get(next(task['id'] for task in downloads if task['video_id'] == 'BBBBBBBBBBB'))
        old_job.error, old_job.diagnostic = cases['BBBBBBBBBBB'][0], ''
        assert client.delete(f'/api/downloads/{old_job.id}').status_code == 200
        assert client.get('/api/removed-downloads').json['downloads'][0]['error'] == analysis_errors['BBBBBBBBBBB']
        restored = client.post(f'/api/removed-downloads/{old_job.id}/restore').json['download']
        assert restored['error'] == analysis_errors['BBBBBBBBBBB'] and restored['diagnostic'] == 'access'
        app.download_manager.shutdown()

    print('PASS: YouTube age checks, private and removed videos, bot prompts, translations and restored errors.')


if __name__ == '__main__':
    main()
