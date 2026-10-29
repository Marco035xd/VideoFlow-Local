"""Local playback and explicit downloads from the isolated private browser."""
import secrets
import threading
import json
import re
from pathlib import Path

from desktop_runtime import runtime, public_url
from download_options import validate_options
from player_sessions import sessions, normalize_state

_media, _media_lock = {}, threading.RLock()
_player_palettes = {}
MEDIA_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.webm', '.avi', '.wmv', '.flv', '.mpeg', '.mpg',
                    '.vob', '.m4v', '.ts', '.mp3', '.m4a', '.wav', '.flac', '.ogg', '.opus', '.aac'}


def register_media(path):
    """Grant a playback token only for a user-selected or natively dropped file."""
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Archivo no encontrado.')
    if path.suffix.lower() not in MEDIA_EXTENSIONS:
        raise ValueError('Elige un archivo de video o audio.')
    token = secrets.token_urlsafe(32)
    with _media_lock:
        _media[token] = path
        sessions.open(token)
    return dict(ok=True, url=f'/api/media/{token}', token=token, name=path.name)


def bind_player_drop(window):
    """Use WebView2's native file objects, without accepting paths from an HTTP API."""
    from webview.dom import DOMEventHandler

    def ready():
        target = window.dom.get_element('#playerDropTarget')
        if target is None:
            return

        def dropped(event):
            request_id = event.get('videoflowDropId')
            files = event.get('dataTransfer', {}).get('files', [])
            if not request_id or len(files) != 1:
                return
            try:
                path = files[0].get('pywebviewFullPath')
                if not path:
                    raise ValueError('No se pudo abrir el archivo arrastrado. Usa Abrir archivo.')
                data = register_media(path)
                window.evaluate_js(f'window.openPlayerMedia({json.dumps(data)}, {json.dumps(request_id)})')
            except Exception as exc:
                window.evaluate_js(f'window.playerDropError({json.dumps(str(exc))}, {json.dumps(request_id)})')

        target.on('drop', DOMEventHandler(dropped, prevent_default=True))
        window.evaluate_js("document.querySelector('#playerDropTarget').dataset.nativeDrop = 'ready'")

    window.events.loaded += ready


def register(app, manager, settings):
    from flask import jsonify, request, send_file, render_template
    from desktop_dialogs import choose, VIDEO_TYPES
    media, lock = _media, _media_lock

    @app.post('/api/player')
    def select_media():
        try:
            paths = choose('OPEN', settings.load()['default_folder'], file_types=VIDEO_TYPES, allow_multiple=False)
            if not paths:
                return jsonify(ok=True, cancelled=True)
            return jsonify(register_media(paths[0]))
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.get('/api/media/<token>')
    def media_stream(token):
        with lock:
            path = media.get(token)
        if not path or not path.is_file():
            return jsonify(ok=False, error='Vuelve a abrir el archivo.'), 404
        response = send_file(path, conditional=True, max_age=0)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/player/<token>')
    def floating_player(token):
        with lock:
            if token not in media:
                return 'Archivo no abierto', 404
        mode = 'pip' if request.args.get('mode') == 'pip' else 'floating'
        return render_template('player.html', token=token, mode=mode, palette=_player_palettes.get(token, {}))

    @app.route('/api/player/<token>/state', methods=['GET', 'POST'])
    def player_state(token):
        if token not in sessions.items:
            return jsonify(ok=False, error='Vuelve a abrir el archivo.'), 404
        try:
            if request.method == 'POST':
                data = request.get_json() or {}
                role = data.get('role') if 'report' in data else None
                if 'report' in data and role not in {'main', 'floating'}:
                    raise ValueError('Reproductor no válido.')
                state = sessions.update(token, data.get('report', data.get('changes', {})),
                                        report_role=role, revision=data.get('revision'))
            else:
                state = sessions.snapshot(token)
            return jsonify(ok=True, state=state)
        except (ValueError, TypeError) as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/player/<token>/close')
    def close_player(token):
        with sessions.lock:
            window = sessions.windows.get(token)
        if window:
            window.destroy()
        if runtime.window and (request.get_json() or {}).get('return_to_main'):
            runtime.window.show()
        return jsonify(ok=True)

    @app.post('/api/player/<token>/floating')
    def open_floating_player(token):
        with lock:
            if token not in media:
                return jsonify(ok=False, error='Abre un video primero.'), 404
        if not runtime.window:
            return jsonify(ok=False, error='Abre la versión de escritorio para la ventana flotante.'), 400
        import webview
        try:
            data = request.get_json() or {}
            mode = 'pip' if data.get('mode') == 'pip' else 'floating'
            changes = normalize_state(data.get('state', {}))
            allowed_colors={'--surface-solid','--text','--muted','--line','--line-strong','--primary','--on-primary'}
            _player_palettes[token]={key:value for key,value in data.get('palette',{}).items()
                if key in allowed_colors and isinstance(value,str) and re.fullmatch(r'(?:#[0-9a-fA-F]{3,8}|rgba?\([0-9.,% /]+\))',value)}
            # Mark the replacement first: closing its predecessor must not take ownership.
            marker = object()
            with sessions.lock:
                old = sessions.windows.get(token)
                if old and getattr(old, '_videoflow_mode', '') == mode:
                    old.show()
                    return jsonify(ok=True, state=sessions.snapshot(token), mode=mode)
                sessions.windows[token] = marker
            if old:
                old.destroy()
            state = sessions.update(token, changes, owner='floating')
            window = webview.create_window('VideoFlow · PiP' if mode == 'pip' else 'VideoFlow · Reproductor',
                f'{request.host_url}player/{token}?mode={mode}', width=440 if mode == 'pip' else 680,
                height=248 if mode == 'pip' else 480, min_size=(240, 135) if mode == 'pip' else (360, 230), on_top=True,
                frameless=True, easy_drag=False, resizable=True,
                background_color='#000000' if mode == 'pip' else '#101827')
            window._videoflow_mode = mode
            with sessions.lock:
                sessions.windows[token] = window
            window.events.closed += lambda: sessions.release(token, window)
            return jsonify(ok=True, state=state, mode=mode)
        except Exception as exc:
            sessions.update(token, {}, owner='main')
            return jsonify(ok=False, error=str(exc)), 400

    @app.route('/api/browser', methods=['GET', 'POST', 'DELETE'])
    def browser():
        if request.method == 'GET':
            with runtime.lock:
                return jsonify(ok=True, detected=runtime.detected.copy(), blocked=runtime.blocked)
        if request.method == 'DELETE':
            with runtime.lock:
                runtime.detected.clear()
            return jsonify(ok=True)
        try:
            runtime.open_browser(str((request.get_json() or {}).get('url', '')))
            return jsonify(ok=True)
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/browser/download')
    def browser_download():
        try:
            data = request.get_json() or {}
            url = public_url(data.get('url', ''))
            mode, fmt = data.get('mode', 'video_audio'), data.get('format', 'mp4')
            if (mode, fmt) not in {('video_audio', 'mp4'), ('video_audio', 'mkv'), ('audio', 'mp3'), ('audio', 'ogg')}:
                raise ValueError('Formato no válido.')
            folder = Path(data.get('folder') or settings.load()['default_folder']).expanduser().resolve()
            quality = '320' if mode == 'audio' else '0'
            payload = dict(url=url, title='Video del navegador', mode=mode, format=fmt, quality=quality,
                           folder=str(folder), advanced={'incognito': True})
            validate_options(payload)
            task = manager.add(payload)
            return jsonify(ok=True, download=task.as_dict()), 201
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400
