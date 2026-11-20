"""FFmpeg staging and playback handoffs with isolated fixtures."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ffmpeg_updates import FFmpegUpdates, VERSION_URL, select_managed_pair, version_tuple
from player_sessions import PlayerSessions, normalize_state

assert version_tuple('9.0.2')>(8,1,2)
assert version_tuple('9.0')==(9,0,0)
def runner(*args,**kwargs):return SimpleNamespace(stdout='ffmpeg version 9.0.2-full_build-www.gyan.dev\n',returncode=0)
def opener(request,timeout):
    assert request.full_url==VERSION_URL and timeout==10
    return io.BytesIO(b'9.1.0\n')
checker=FFmpegUpdates(lambda _:'ffmpeg.exe',opener,runner)
checker.check();assert checker.status()['available'] and checker.status()['current']=='9.0.2'
checker.opener=lambda *_args,**_kwargs:io.BytesIO(b'9.0.2')
checker.check();assert not checker.status()['available'] and checker.status()['status']=='ready'
checker.opener=lambda *_args,**_kwargs:io.BytesIO(b'<html>network error</html>')
checker.check();assert checker.status()['status']=='error' and not checker.status()['available']


def check_install():
    body = b'fixture archive'
    checksum = hashlib.sha256(body).hexdigest().encode()

    class Response(io.BytesIO):
        status = 200
        headers = {'Content-Length': str(len(body))}

    def version_runner(command, **_):
        executable = Path(command[0])
        version = executable.read_text() if executable.is_file() else '9.0.2'
        return SimpleNamespace(stdout=f'{executable.stem} version {version}-fixture\n', returncode=0)

    replies = {VERSION_URL: b'9.1\n'}

    def fake_provider(request, **_):
        url = request.full_url
        if url in replies:
            return io.BytesIO(replies[url])
        assert url.endswith('/ffmpeg-9.1-full_build.7z') or url.endswith('/ffmpeg-9.1-full_build.7z.sha256')
        return Response(body)

    validating = threading.Event()
    resume = threading.Event()

    def fake_unpack(archive, folder, version, tar):
        assert archive.read_bytes() == body and tar
        validating.set()
        assert resume.wait(5)
        (folder / 'ffmpeg.exe').write_text(version)
        (folder / 'ffprobe.exe').write_text(version)

    def wait_for_install(updater, status):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if updater.status()['install_status'] == status:
                return
            time.sleep(.02)
        raise AssertionError(updater.status())

    with tempfile.TemporaryDirectory() as temporary, patch('ffmpeg_updates.system_tar', return_value='system-tar'):
        root = Path(temporary) / 'tools'
        fallback = lambda tool: f'{tool}.exe'
        updater = FFmpegUpdates(fallback, fake_provider, version_runner, root=root, unpack=fake_unpack)
        updater.check()
        sha_url = 'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.1-full_build.7z.sha256'
        replies[sha_url] = b'0' * 64
        with patch('ffmpeg_updates.logging.getLogger'):
            updater.install()
            wait_for_install(updater, 'error')
        assert not validating.is_set() and not list(root.iterdir())
        assert select_managed_pair(root, fallback, version_runner) is None

        replies[sha_url] = checksum
        updater.install()
        assert validating.wait(5)
        assert updater.install()['install_status'] == 'validating'
        assert select_managed_pair(root, fallback, version_runner) is None
        resume.set()
        wait_for_install(updater, 'staged')
        folder = select_managed_pair(root, fallback, version_runner)
        assert folder and [file.name for file in sorted(folder.iterdir())] == ['ffmpeg.exe', 'ffprobe.exe']
        assert updater.status()['pending_version'] == '9.1'
        assert updater.status()['downloaded'] == len(body)
        (folder / 'ffprobe.exe').write_text('9.0.2')
        assert select_managed_pair(root, fallback, version_runner) is None
        (folder / 'ffprobe.exe').write_text('9.1')
        newer = Path(temporary) / 'ffmpeg.exe'
        newer.write_text('9.2')
        assert select_managed_pair(root, lambda _: newer, version_runner) is None


check_install()
now=[0.]
sessions=PlayerSessions(clock=lambda:now[0]);sessions.open('video')
state=sessions.update('video',dict(position=15,duration=100,playing=True,volume=.4,rate=1.5),owner='floating')
now[0]=2.;assert sessions.snapshot('video')['position']==18
command=sessions.update('video',dict(position=40,playing=False))
stale=sessions.update('video',dict(position=3,playing=True),report_role='floating',revision=state['revision'])
assert stale['position']==40 and not stale['playing'],'A stale report must not undo a seek command'
ignored=sessions.update('video',dict(position=5),report_role='main',revision=command['revision'])
assert ignored['position']==40
window=object();sessions.windows['video']=window
sessions.release('video',object());assert sessions.snapshot('video')['owner']=='floating'
sessions.release('video',window);assert sessions.snapshot('video')['owner']=='main' and sessions.snapshot('video')['position']==40
for value in (float('nan'),float('inf'),-1):
    try:normalize_state({'position':value})
    except ValueError:pass
    else:raise AssertionError(value)
print('PASS: FFmpeg checks, SHA-256, staging, atomic activation, mismatched binaries, and playback handoffs.')
