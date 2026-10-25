"""Version checks and playback handoffs without changing installed tools."""
import io
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ffmpeg_updates import FFmpegUpdates, VERSION_URL, version_tuple
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
print('PASS: FFmpeg update/new/equal/invalid responses, advancing playback clock, stale reports, ownership and handoff position.')
