"""Check migration, persistence and validation without touching the user's settings."""
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory(prefix='videoflow-appearance-') as temporary:
    os.environ['VIDEOFLOW_DATA_DIR'] = str(Path(temporary) / 'data')
    import app
    from appearance import DEFAULT_APPEARANCE

    client = app.app.test_client()
    legacy = Path(temporary) / 'legacy.json'
    legacy.write_text(json.dumps({'theme': 'light', 'notifications': False}), encoding='utf-8')
    migrated = app.SettingsStore(legacy).load()
    assert migrated['theme'] == 'light' and migrated['appearance'] == DEFAULT_APPEARANCE
    assert migrated['notifications'] is False

    for mode in ('light', 'dark', 'system'):
        for preset in ('videoflow', 'graphite', 'ocean', 'forest', 'plum', 'sand'):
            preferences = {**DEFAULT_APPEARANCE, 'preset': preset, 'accent': 'green', 'font': 'humanist'}
            response = client.put('/api/settings', json={'theme': mode, 'appearance': preferences})
            assert response.status_code == 200, response.json
            restored = app.SettingsStore(app.SETTINGS_FILE).load()
            assert restored['theme'] == mode and restored['appearance'] == preferences

    custom = {**DEFAULT_APPEARANCE, 'accent': 'custom', 'custom_accent': '#BD74EC',
              'custom_colors': True, 'background': '#181818', 'foreground': '#ffffff',
              'font': 'mono', 'density': 'compact', 'reduce_motion': True}
    response = client.put('/api/settings', json={'theme': 'system', 'appearance': custom})
    assert response.status_code == 200, response.json
    saved = response.json['settings']['appearance']
    assert saved['custom_accent'] == '#bd74ec'
    client.put('/api/settings', json={'notifications': False, 'retry_count': 7})
    assert client.get('/api/settings').json['settings']['appearance'] == saved

    for invalid in (
        {'theme': 'sepia'}, {'theme': []}, {'appearance': []},
        {'appearance': {**custom, 'preset': 'unknown'}},
        {'appearance': {**custom, 'font': 'url(https://example.test/font)'}},
        {'appearance': {**custom, 'foreground': '#181818'}},
        {'appearance': {**custom, 'custom_accent': '#xyzxyz'}},
        {'appearance': {**custom, 'background': 'red;display:none'}},
        {'appearance': {**custom, 'reduce_motion': 'false'}},
    ):
        assert client.put('/api/settings', json=invalid).status_code == 400, invalid
    assert client.get('/api/settings').json['settings']['appearance'] == saved
    assert app.SettingsStore._merge({'theme': [], 'appearance': {'custom_colors': True, 'background': '#fff'}})['theme'] == 'dark'
    assert app.SettingsStore._merge({'appearance': {'custom_colors': True, 'foreground': '#181818'}})['appearance']['custom_colors'] is False
    print('OK: legacy theme migration; all six themes and three modes persist; custom colors survive other settings; invalid and unreadable preferences are rejected.')
