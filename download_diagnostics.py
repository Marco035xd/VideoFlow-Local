"""Identify the stage of a failed job without including raw error text in reports."""
from network_recovery import is_connection_error


def classify_failure(error, local_path='', phase='', progress=0):
    message = str(error).lower()
    if isinstance(error, PermissionError) or any(term in message for term in (
        'no space left', 'disk full', 'permission denied', 'access is denied', 'winerror 112',
        'no hay permiso', 'no hay espacio', 'destino ya existe', 'archivo elegido ya existe', 'winerror 5',
    )):
        return 'storage'
    if any(term in message for term in (
        'postprocessing:', 'unable to merge', 'conversion failed', 'error while opening encoder',
        'ffmpeg', 'ffprobe', 'vorbis', 'formato esperado', 'archivo intermedio',
        'archivo final', 'formato elegido',
    )):
        return 'processing'
    if not local_path:
        if is_connection_error(error) or any(term in message for term in (
            'conexión con el servidor', 'conectar con el servidor', 'certificate verify failed',
            'connection refused', 'unable to resolve', 'getaddrinfo', 'http error 50',
        )):
            return 'connection'
        if any(term in message for term in (
            'http error 401', 'http error 403', 'http error 404', 'http error 429',
            'login required', 'authentication', 'sign in', 'cookies', 'private video', 'age-restricted',
            'not a bot', 'login', 'video unavailable', 'too many requests', 'rate-limit',
            'no media found', 'no video in', 'cannot parse data', 'ip address is blocked',
            'solicita confirmar', 'limitó el acceso', 'limitado temporalmente',
            'no contiene un video disponible', 'bloqueó el acceso', 'no permitido leer esa sesión',
        )):
            return 'access'
    if any(term in message for term in (
        'requested format is not available', 'no formats', 'formato no disponible',
        'pista de audio', 'subtitles', 'subtítulos',
    )):
        return 'format'
    if isinstance(error, FileNotFoundError) or any(term in message for term in (
        'no such file or directory', 'archivo original', 'carpeta elegida', 'enough space',
    )):
        return 'storage'
    if local_path or progress >= 98.5 or phase.startswith('Convirtiendo'):
        return 'processing'
    return 'unknown'
