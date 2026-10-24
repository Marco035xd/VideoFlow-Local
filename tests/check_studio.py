"""Offline integration: scheduling, collection expansion, encryption, real FFmpeg output."""
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def wait_for(predicate, timeout=15):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError('Timed out')


with tempfile.TemporaryDirectory(prefix='videoflow-studio-') as temporary:
    root = Path(temporary)
    os.environ['VIDEOFLOW_DATA_DIR'] = str(root / 'data')
    import app
    from vault import Vault
    from download_options import validate_options, video_selector, apply_options
    from collections_download import CollectionJobs
    from desktop_runtime import blocked_url
    client = app.app.test_client()
    assert client.get('/').status_code == 200
    assert client.put('/api/settings', json={'max_concurrent': 0}).status_code == 200
    assert client.put('/api/settings', json={'max_concurrent': -1}).status_code == 400
    assert client.get('/api/vault', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.get('/api/vault', headers={'Host': 'evil.example'}).status_code == 403
    assert client.post('/api/vault/lock', data='x=1').status_code == 415
    assert blocked_url('https://ads.doubleclick.net/video')
    assert blocked_url('http://127.0.0.1:8765/api/settings')
    assert not blocked_url('https://www.youtube.com/watch?v=example')

    for advanced in ({'start':'3:00','end':'2:00'}, {'start':'2:65','end':'3:30'},
                     {'subtitles':'embed'}, {'language':'.*'}, {'start':'1','end':'2','subtitles':'srt'}):
        try:
            validate_options({'format':'mp3','mode':'audio','advanced':advanced})
        except ValueError:
            pass
        else:
            raise AssertionError(advanced)

    # Simultaneous work exceeds the old 10-item cap, honors a finite setting,
    # and releases slots even when a job fails.
    settings = app.SettingsStore(root / 'scheduler.json')
    settings.update({'max_concurrent': 2})
    manager = app.DownloadManager(settings, app.HistoryStore(root / 'scheduler.db'))
    started, guard, release = [], threading.Lock(), threading.Event()
    def fake_download(task):
        task.status = 'Descargando'
        with guard:
            started.append(task.id)
        release.wait(15)
        task.status = 'Completado'
    manager._download = fake_download
    payload = dict(url='https://www.youtube.com/watch?v=example', format='mp4', quality='0', folder=str(root))
    tasks = [manager.add(payload) for _ in range(15)]
    wait_for(lambda: len(started) == 2)
    time.sleep(.15)
    assert len(started) == 2
    manager.cancel(tasks[-1].id)
    settings.update({'max_concurrent': 0})
    manager.notify_settings_changed()
    wait_for(lambda: len(started) == 14)
    release.set()
    wait_for(lambda: manager.active_count == 0)
    assert tasks[-1].status == 'Cancelado'

    # Stream hundreds of entries, deduplicate and skip missing entries.
    collection = CollectionJobs(manager, settings, lambda *_: {}, app.source_for_url)
    class FakeYDL:
        def __init__(self, options):
            assert options['lazy_playlist'] is True
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def extract_info(self, *_args, **_kwargs):
            entries = [dict(id=f'test{i}', url=f'https://www.youtube.com/watch?v=test{i}', title=f'Video {i}') for i in range(350)]
            return {'_type':'playlist','title':'350 videos','entries':iter(entries + [entries[0], None])}
    with patch('collections_download.yt_dlp.YoutubeDL', FakeYDL):
        identifier = collection.start({**payload, 'url':'https://www.youtube.com/playlist?list=fixture'})
        wait_for(lambda: collection.jobs[identifier]['status'] != 'Leyendo')
        job = collection.jobs[identifier]
        assert (job['added'], job['skipped']) == (350, 2), job
    wait_for(lambda: manager.count_unfinished() == 0)

    # PIN failures, encrypted names/data, process restart and corrupted ciphertext.
    vault = Vault(root / 'private')
    vault.unlock('12345678')
    original = root / 'secret-video.mp4'
    original.write_bytes(b'private media content' * 150000)
    identifier = vault.protect(original)
    vault.add_index(identifier, original)
    assert b'secret-video' not in (vault.root / 'index.bin').read_bytes()
    assert b'private media content' not in vault.path(identifier).read_bytes()
    vault.close()
    try: vault.list()
    except ValueError: pass
    else: raise AssertionError('Locked vault readable')
    restored = Vault(vault.root)
    try: restored.unlock('87654321')
    except ValueError: pass
    else: raise AssertionError('Wrong PIN accepted')
    restored.unlock('12345678')
    exported = root / 'restored.mp4'
    restored.export(identifier, exported)
    assert hashlib.sha256(original.read_bytes()).digest() == hashlib.sha256(exported.read_bytes()).digest()
    with restored.path(identifier).open('r+b') as file:
        file.seek(-40, 2); file.write(b'corruption')
    try: restored.export(identifier, root / 'bad.mp4')
    except Exception: pass
    else: raise AssertionError('Corruption not detected')
    assert not (root / 'bad.mp4').exists()
    assert not list(root.glob('*.vault-export'))

    # Format selector keeps real 8K HDR at 60 fps.
    task = app.DownloadTask(id='selector', url='', video_id='', title='', thumbnail='', duration=0,
                            output_format='mkv', quality='4320', folder=str(root),
                            advanced=validate_options({'format':'mkv','advanced':{'fps':'60','dynamic_range':'hdr'}}))
    formats = [dict(format_id='low',height=1080, fps=30, dynamic_range='SDR', vcodec='h264',acodec='none',url='https://example.org/low',ext='mp4'),
               dict(format_id='ultra',height=4320, fps=60,dynamic_range='HDR10',vcodec='vp9',acodec='none',url='https://example.org/ultra',ext='webm'),
               dict(format_id='audio',vcodec='none',acodec='opus',url='https://example.org/audio',ext='webm')]
    with app.yt_dlp.YoutubeDL({'quiet':True}) as ydl:
        selection = list(ydl.build_format_selector(video_selector(task))({'formats':formats,'has_merged_format':False,'incomplete_formats':False}))
    assert selection and selection[0]['format_id'] == 'ultra+audio', selection

    ffmpeg, ffprobe = app.find_tool('ffmpeg'), app.find_tool('ffprobe')
    source = root / 'fixture.mp4'
    subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=24',
                    '-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','4',
                    '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(source)], check=True)
    for fmt in ('mp4','mkv','mov','avi'):
        convert_task = app.DownloadTask(id=f'convert{fmt}',url='',video_id='',title='Fixture',thumbnail='',duration=4,
                                       output_format=fmt,quality='20',folder=str(root),local_path=str(source),mode='video_convert')
        manager._download = app.DownloadManager._download.__get__(manager)
        manager._download(convert_task)
        assert convert_task.status == 'Completado', (fmt,convert_task.error)
        info=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-of','json',convert_task.final_path]))
        assert any(stream['codec_type']=='video' for stream in info['streams'])
    for fmt in ('mp3','flac','m4a'):
        audio = app.DownloadTask(id=f'audio{fmt}',url='',video_id='',title='Fixture',thumbnail='',duration=4,
                                 output_format=fmt,quality='320',folder=str(root),local_path=str(source),mode='audio')
        manager._download(audio)
        assert audio.status == 'Completado', (fmt, audio.error)

    # Real subtitle conversion and embedding retain a separate SRT.
    from yt_dlp.postprocessor.ffmpeg import FFmpegSubtitlesConvertorPP, FFmpegEmbedSubtitlePP
    subtitle = root / 'fixture.es.vtt'
    subtitle.write_text('WEBVTT\n\n00:00:00.500 --> 00:00:02.000\nHola VideoFlow\n', encoding='utf-8')
    info = dict(filepath=str(source), ext='mp4', requested_subtitles={'es':{'ext':'vtt','filepath':str(subtitle)}}, __files_to_move={str(subtitle):str(subtitle)})
    with app.yt_dlp.YoutubeDL({'quiet':True, 'ffmpeg_location':str(Path(ffmpeg).parent)}) as ydl:
        _, info = FFmpegSubtitlesConvertorPP(ydl, format='srt').run(info)
        _, info = FFmpegEmbedSubtitlePP(ydl, already_have_subtitle=True).run(info)
    assert (root / 'fixture.es.srt').is_file()
    streams=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-of','json',str(source)]))['streams']
    assert any(stream['codec_type']=='subtitle' for stream in streams)

    class SilentServer(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SilentServer,directory=str(root)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        cut=app.DownloadTask(id='cutfixture',url=f'http://127.0.0.1:{server.server_port}/fixture.mp4',video_id='',title='Cut',thumbnail='',duration=4,
                             output_format='mp4',quality='0',folder=str(root),source='Web',advanced=validate_options({'advanced':{'start':'1','end':'3','incognito':True}}))
        before=len(manager.history.list())
        manager._download(cut)
        assert cut.status=='Completado',cut.error
        assert len(manager.history.list())==before
        result=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_format','-of','json',cut.final_path]))
        assert 1.7 <= float(result['format']['duration']) <= 2.4, result['format']['duration']
    finally:
        server.shutdown()
    print('PASS: 350-entry collection, >10 concurrent jobs, validation, 8K HDR selection, PIN encryption/restart/tamper, 7 real conversions and trimmed incognito download.')
