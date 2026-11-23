"""Identify the stage of a failed job without including raw error text in reports."""
from network_recovery import is_connection_error


_YOUTUBE_PLAYABILITY_MESSAGES = {
    ('Este video es privado y no está disponible para el público. Si el propietario te dio acceso, '
     'abre el video con la cuenta autorizada, elige ese navegador en «Sesión de YouTube» y vuelve a analizar.'): (
        'private video', 'video is private',
    ),
    ('Este video tiene restricción de edad. Inicia sesión en YouTube y confirma tu edad si te lo solicita. '
     'Si puedes reproducirlo, elige ese navegador en «Sesión de YouTube» y vuelve a analizar.'): (
        'confirm your age', 'age-restricted', 'age restriction', 'age verification required',
    ),
    'Este video fue retirado o no está disponible en YouTube.': (
        'video unavailable', 'video is unavailable', 'video is not available', "video isn't available",
        'video is no longer available', 'video has been removed', 'video was removed',
        'video has been deleted', 'video was deleted',
    ),
}


def youtube_playability_message(message: str) -> str | None:
    if message in _YOUTUBE_PLAYABILITY_MESSAGES:
        return message
    reason = message.lower().replace('’', "'")
    for text, markers in _YOUTUBE_PLAYABILITY_MESSAGES.items():
        if any(marker in reason for marker in markers):
            return text
    return None


def classify_failure(error, local_path='', phase='', progress=0):
    raw_message = str(error)
    message = raw_message.lower()
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
        if youtube_playability_message(raw_message) or any(term in message for term in (
            'http error 401', 'http error 403', 'http error 404', 'http error 429',
            'login required', 'authentication', 'sign in', 'cookies',
            'not a bot', 'login', 'too many requests', 'rate-limit',
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
