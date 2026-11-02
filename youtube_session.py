"""Explicit YouTube session choices. Imported cookies stay in process memory."""
import io
import re
import threading
import time
import uuid
from pathlib import Path

BROWSERS = {'', 'brave', 'chrome', 'edge', 'firefox'}
_sessions, _lock = {}, threading.RLock()


def validate_choice(choice):
    if not isinstance(choice, str):
        raise ValueError('Selecciona una opción de sesión de YouTube válida.')
    if choice in BROWSERS:
        return choice
    if re.fullmatch(r'cookies:[a-f0-9]{32}', choice):
        with _lock:
            if choice in _sessions:
                return choice
        raise ValueError('Vuelve a seleccionar el archivo de cookies de YouTube. La sesión importada solo dura mientras la app está abierta.')
    raise ValueError('Selecciona una opción de sesión de YouTube válida.')


def session_options(choice):
    choice = validate_choice(choice)
    if choice.startswith('cookies:'):
        with _lock:
            # yt-dlp may update its cookie file on close; only this in-memory copy changes.
            return {'cookiefile': io.StringIO(_sessions[choice])}
    return {'cookiesfrombrowser': (choice,)} if choice else {}


def import_cookies(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Selecciona un archivo cookies.txt válido de hasta 2 MB.')
    try:
        text = path.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError):
        raise ValueError('No se pudo leer el archivo de cookies. Selecciona un archivo de texto en formato Netscape.') from None
    lines = text.splitlines()
    if not lines or not re.match(r'^#(?: Netscape)? HTTP Cookie File', lines[0]):
        raise ValueError('El archivo debe estar en formato Netscape cookies.txt, no JSON.')
    accepted = []
    for line in lines[1:]:
        httponly = line.startswith('#HttpOnly_')
        if not line.strip() or (line.startswith('#') and not httponly):
            continue
        value = line[len('#HttpOnly_'):] if httponly else line
        fields = value.split('\t')
        if (len(fields) != 7 or fields[1] not in {'TRUE', 'FALSE'} or fields[3] not in {'TRUE', 'FALSE'}
                or not re.fullmatch(r'\.?[A-Za-z0-9.-]+', fields[0])
                or (fields[1] == 'TRUE') != fields[0].startswith('.')
                or re.search(r'[\x00-\x1f\x7f]', ''.join(fields))
                or (fields[4] and not fields[4].isascii())
                or (fields[4] and not fields[4].isdigit())):
            raise ValueError('El archivo de cookies tiene un formato no válido. Expórtalo otra vez en formato Netscape.')
        domain = fields[0].lstrip('.').lower()
        if not any(domain == allowed or domain.endswith('.' + allowed) for allowed in ('youtube.com', 'youtu.be', 'googlevideo.com')):
            continue
        if fields[4] and int(fields[4]) != 0 and int(fields[4]) <= time.time():
            continue
        accepted.append(line)
    if not accepted:
        raise ValueError('No se encontraron cookies vigentes de YouTube. Inicia sesión en YouTube y vuelve a exportarlas.')
    sanitized = '# Netscape HTTP Cookie File\n' + '\n'.join(accepted) + '\n'
    # Validate without printing parser warnings or cookie values.
    try:
        from yt_dlp.cookies import YoutubeDLCookieJar
        jar = YoutubeDLCookieJar(io.StringIO(sanitized))
        jar.load()
        if not list(jar):
            raise ValueError()
    except Exception:
        raise ValueError('El archivo de cookies tiene un formato no válido. Expórtalo otra vez en formato Netscape.') from None
    token = 'cookies:' + uuid.uuid4().hex
    with _lock:
        _sessions[token] = sanitized
    return token


def register(app):
    from flask import jsonify
    from desktop_dialogs import choose

    @app.post('/api/youtube/session-file')
    def select_youtube_session_file():
        try:
            paths = choose('OPEN', file_types=('Archivo de cookies (*.txt)', 'Todos los archivos (*.*)'), allow_multiple=False)
            if not paths:
                return jsonify(ok=True, cancelled=True)
            token = import_cookies(paths[0])
            return jsonify(ok=True, token=token, name=Path(paths[0]).name)
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 400
        except Exception:
            return jsonify(ok=False, error='No se pudo seleccionar el archivo de cookies.'), 400
