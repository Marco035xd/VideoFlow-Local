"""Bounded recovery of transient connections, keeping TLS verification enabled."""
CONNECTION_MODES = {'auto': None, 'ipv4': '0.0.0.0', 'ipv6': '::'}


def is_connection_error(error):
    message = str(error).lower()
    if any(term in message for term in ('postprocessing:', 'certificate verify failed', 'http error 403', 'http error 429')):
        return False
    return any(term in message for term in (
        'timed out', 'timeout', 'connection reset', 'connection aborted',
        'network is unreachable', 'network is down', 'name resolution',
        'getaddrinfo failed', 'winerror 10060', 'winerror 10054',
    ))


def connection_error_message(error, source):
    if not is_connection_error(error):
        return None
    if source == 'YouTube':
        return 'No se pudo conectar con el servidor que entrega el video de YouTube. Si el video funciona en tu navegador, prueba IPv4 o IPv6 en Configuración → Conexión para YouTube y pulsa Reintentar. La disponibilidad del servidor depende de tu conexión y de YouTube.'
    return 'Se interrumpió la conexión con el servidor del archivo. Revisa tu conexión y vuelve a intentarlo.'


def run_with_recovery(task, attempt, checkpoint, clean_partials, retry_count, connection_mode):
    """Normal yt-dlp retries, then at most one fresh IPv4 extraction in auto mode."""
    checkpoint(task)
    try:
        return attempt(None, None)
    except Exception as error:
        checkpoint(task)  # Cancellation must not start another connection.
        if task.source != 'YouTube' or connection_mode != 'auto' or not retry_count or not is_connection_error(error):
            raise
    task.error = ''
    task.phase = 'Reconectando con YouTube mediante IPv4…'
    task.status = 'Descargando'
    task.speed, task.eta = 0, None
    clean_partials()
    task.progress, task.downloaded_bytes, task.total_bytes = 0, 0, 0
    checkpoint(task)
    return attempt('0.0.0.0', 0)
