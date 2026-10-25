"""Local streaming regression: replay/range requests and native file grants."""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory(prefix='videoflow-player-') as temporary:
    root = Path(temporary)
    os.environ['VIDEOFLOW_DATA_DIR'] = str(root / 'data')
    # register() captures the picker, so replace it before importing the app.
    picker = patch('desktop_dialogs.choose')
    choose = picker.start()
    import app
    import media_tools
    client = app.app.test_client()
    source = root / 'video con espacios.mp4'
    content = bytes(range(256)) * 64
    source.write_bytes(content)
    choose.return_value = [str(source)]
    data = client.post('/api/player', json={}).get_json()
    assert choose.call_args.kwargs['allow_multiple'] is False
    picker.stop()
    for start, end in [(0,1023),(4096,8191),(0,1023),(100,499)]:
        response = client.get(data['url'], headers={'Range':f'bytes={start}-{end}'})
        assert response.status_code == 206
        assert response.data == content[start:end+1]
        assert response.headers['Content-Range'] == f'bytes {start}-{end}/{len(content)}'
        assert response.headers['Cache-Control'] == 'no-store'
        response.close()
    assert client.get(f"/player/{data['token']}").status_code == 200
    assert client.get('/api/media/unknown').status_code == 404
    bad = root / 'document.txt'; bad.write_text('not media')
    for path in (bad, root/'missing.mp4', root):
        try: media_tools.register_media(path)
        except ValueError: pass
        else: raise AssertionError('Invalid media grant')

    # Native drop opens only the actual file supplied by WebView2's file object.
    class Events:
        def __init__(self): self.loaded = []
    class Drop:
        def __init__(self): self.drop = []
    class Target:
        def __init__(self): self.events = Drop()
        def on(self, name, callback): self.events.drop += callback
    class DOM:
        def get_element(self, _): return target
    class Window:
        def __init__(self): self.events = Events(); self.dom = DOM(); self.scripts = []
        def evaluate_js(self, script): self.scripts.append(script)
    target, window = Target(), Window()
    # __iadd__ for pywebview events is represented by a tiny recorder here.
    class HandlerList:
        def __init__(self): self.callbacks = []
        def __iadd__(self, callback): self.callbacks.append(callback); return self
    window.events.loaded = HandlerList(); target.events.drop = HandlerList()
    media_tools.bind_player_drop(window)
    window.events.loaded.callbacks[0]()
    handler = target.events.drop.callbacks[0].callback
    handler({'videoflowDropId':'7','dataTransfer':{'files':[{'pywebviewFullPath':str(source)}]}})
    assert 'openPlayerMedia(' in window.scripts[-1] and '"7"' in window.scripts[-1]
    handler({'videoflowDropId':'8','dataTransfer':{'files':[{}]}})
    assert 'playerDropError(' in window.scripts[-1]
    print('PASS: repeat range/seek streams, native drop tokens, single-file picker and rejected invalid files.')
