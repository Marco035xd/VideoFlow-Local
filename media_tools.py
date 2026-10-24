"""Local playback and explicit downloads from the isolated private browser."""
import secrets
import threading
from pathlib import Path

from desktop_runtime import runtime, public_url
from download_options import validate_options


def register(app, manager, settings):
    from flask import jsonify, request, send_file, render_template
    from desktop_dialogs import choose, VIDEO_TYPES
    media, lock = {}, threading.RLock()

    @app.post('/api/player')
    def select_media():
        try:
            paths = choose('OPEN', settings.load()['default_folder'], file_types=VIDEO_TYPES)
            if not paths:
                return jsonify(ok=True, cancelled=True)
            path = Path(paths[0]).resolve()
            if not path.is_file():
                raise ValueError('Archivo no encontrado.')
            token = secrets.token_urlsafe(32)
            with lock:
                media[token] = path
            return jsonify(ok=True, url=f'/api/media/{token}', token=token, name=path.name)
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
        return render_template('player.html', token=token)

    @app.post('/api/player/<token>/floating')
    def open_floating_player(token):
        with lock:
            if token not in media:
                return jsonify(ok=False, error='Abre un video primero.'), 404
        if not runtime.window:
            return jsonify(ok=False, error='Abre la versión de escritorio para la ventana flotante.'), 400
        import webview
        webview.create_window('VideoFlow · Reproductor', f'{request.host_url}player/{token}',
                              width=600, height=400, min_size=(320, 240), on_top=True)
        return jsonify(ok=True)

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
            if (mode, fmt) not in {('video_audio', 'mp4'), ('video_audio', 'mkv'), ('audio', 'mp3')}:
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
