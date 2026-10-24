"""Validated download options, shared by single videos and collection imports."""
import math
import re

VIDEO_FORMATS = {'mp4', 'mkv', 'mov', 'avi', 'webm', 'vob'}
AUDIO_FORMATS = {'mp3', 'm4a', 'wav', 'flac'}


def timestamp(value):
    if value in (None, ''):
        return None
    parts = str(value).strip().split(':')
    if len(parts) > 3 or any(not re.fullmatch(r'\d+(?:\.\d+)?', part) for part in parts):
        raise ValueError('Usa segundos, mm:ss o hh:mm:ss para el recorte.')
    if len(parts) > 1 and any(float(part) >= 60 for part in parts[1:]):
        raise ValueError('Los minutos y segundos del recorte deben ser menores que 60.')
    result = 0
    for part in parts:
        result = result * 60 + float(part)
    if not math.isfinite(result):
        raise ValueError('Tiempo de recorte no válido.')
    return result


def validate_options(payload):
    value = payload.get('advanced') or {}
    if not isinstance(value, dict):
        raise ValueError('Opciones avanzadas no válidas.')
    start, end = timestamp(value.get('start')), timestamp(value.get('end'))
    if start is not None or end is not None:
        start = start or 0
        if end is None or end <= start:
            raise ValueError('Indica un final del recorte mayor que el inicio.')
        if payload.get('duration') and end > float(payload['duration']):
            raise ValueError('El recorte termina después del final del video.')
    subtitles = value.get('subtitles', 'none')
    if subtitles not in {'none', 'srt', 'embed'}:
        raise ValueError('Selecciona una opción de subtítulos válida.')
    language = str(value.get('language') or 'es')
    if not re.fullmatch(r'[A-Za-z0-9-]{2,20}', language):
        raise ValueError('Usa un código de idioma como es, en o pt-BR.')
    if subtitles == 'embed' and (payload.get('mode') == 'audio' or payload.get('format') not in {'mp4', 'mkv', 'mov'}):
        raise ValueError('Los subtítulos incrustados requieren video MP4, MKV o MOV.')
    if start is not None and subtitles != 'none':
        raise ValueError('Descarga el video completo para conservar la sincronización de los subtítulos.')
    fps = str(value.get('fps', 'best'))
    dynamic_range = value.get('dynamic_range', 'auto')
    if fps not in {'best', '30', '60'} or dynamic_range not in {'auto', 'sdr', 'hdr'}:
        raise ValueError('Preferencia de FPS o HDR no válida.')
    if payload.get('mode') == 'audio':
        fps, dynamic_range = 'best', 'auto'
    if dynamic_range == 'hdr' and payload.get('format') not in {'mkv', 'webm'}:
        raise ValueError('Para conservar HDR, selecciona MKV o WebM.')
    return dict(start=start, end=end, subtitles=subtitles, language=language,
                automatic=value.get('automatic') is True, fps=fps, dynamic_range=dynamic_range,
                incognito=value.get('incognito') is True)


def video_selector(task):
    options = task.advanced
    height = f'[height<={int(task.quality)}]' if int(task.quality) else ''
    filters = height
    if options.get('fps') == '60':
        filters += '[fps>=50]'
    elif options.get('fps') == '30':
        filters += '[fps<=30]'
    if options.get('dynamic_range') == 'hdr':
        filters += "[dynamic_range~='^(HDR|HLG|DV)']"
    elif options.get('dynamic_range') == 'sdr':
        filters += '[dynamic_range=SDR]'
    return (f'bestvideo{filters}/best{filters}' if task.mode == 'video_only'
            else f'bestvideo{filters}+bestaudio/best{filters}')


def apply_options(options, task):
    advanced = task.advanced
    if advanced.get('start') is not None:
        from yt_dlp.utils import download_range_func
        options['download_ranges'] = download_range_func(None, [(advanced['start'], advanced['end'])])
        options['force_keyframes_at_cuts'] = True
    if advanced.get('subtitles', 'none') != 'none':
        options.update(writesubtitles=True, writeautomaticsub=advanced['automatic'],
                       subtitleslangs=[advanced['language']], subtitlesformat='srt/vtt/best')
        options.setdefault('postprocessors', []).append({'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'})
        if advanced['subtitles'] == 'embed':
            options['postprocessors'].append({'key': 'FFmpegEmbedSubtitle', 'already_have_subtitle': True})
    return options
