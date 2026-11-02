"""Discover audio tracks and enforce an explicit choice during format selection."""
import hashlib
import json
import math
import re


def has_audio(fmt):
    return fmt.get('acodec') not in (None, 'none') and not fmt.get('has_drm')


def track_details(fmt):
    language = str(fmt.get('language') or '').strip()[:64]
    # Track names precede quality/codec notes in the YouTube extractor.
    name = str(fmt.get('format_note') or '').split(',', 1)[0].strip()[:200]
    original = 'original' in name.casefold() or fmt.get('language_preference') == 10
    default = '(default)' in name.casefold() or fmt.get('language_preference') == 5
    name = re.sub(r'\((?:default|original)\)', '', name, flags=re.I).strip()
    if re.fullmatch(r'(?:(?:audio[ _-]*)?(?:low|medium|high|best)|dash audio|audio only|hls|dash|\d+p(?:\d+)?|\d+(?:\.\d+)?k|drc)', name, re.I):
        name = ''
    descriptive = language.endswith('-desc') or any(word in name.casefold() for word in ('descriptive', 'description', 'audiodescrip'))
    identity = json.dumps([language.casefold(), name.casefold(), original, descriptive], ensure_ascii=False)
    return dict(id=hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32], language=language,
                name=name, original=original, default=default, descriptive=descriptive)


def available_tracks(formats):
    groups = {}
    for fmt in formats:
        if not has_audio(fmt) or not fmt.get('url'):
            continue
        details = track_details(fmt)
        track = groups.setdefault(details['id'], {**details, 'estimated_size': 0, 'channels': set()})
        track['default'] = track['default'] or details['default']
        size = fmt.get('filesize') or fmt.get('filesize_approx') or 0
        if fmt.get('vcodec') == 'none' and isinstance(size, (int, float)) and math.isfinite(size):
            track['estimated_size'] = max(track['estimated_size'], int(size))
        channels = fmt.get('audio_channels')
        if isinstance(channels, (int, float)) and math.isfinite(channels) and channels > 0:
            track['channels'].add(int(channels))
    result = []
    for track in groups.values():
        track['channels'] = sorted(track['channels'])
        track['label'] = track['name'] or track['language'] or 'Pista de audio'
        if track['original']:
            track['label'] += ' · Original'
        if track['descriptive']:
            track['label'] += ' · Audiodescripción'
        result.append(track)
    return sorted(result, key=lambda item: (not item['default'], not item['original'], item['language'], item['name']))


def restrict_audio_selector(base_selector, task):
    """Keep only the chosen track; quality fallbacks may never select other audio."""
    selected_id = task.advanced['audio_track']

    def select(context):
        formats = context['formats']
        track = next((item for item in available_tracks(formats) if item['id'] == selected_id), None)
        if not track:
            raise ValueError('La pista de audio elegida ya no está disponible. Analiza el video otra vez y elige una pista disponible.')
        matching = {id(fmt) for fmt in formats if has_audio(fmt) and track_details(fmt)['id'] == selected_id}
        allowed = [fmt for fmt in formats if fmt.get('acodec') == 'none' or id(fmt) in matching]
        narrowed = {**context, 'formats': allowed,
                    'has_merged_format': any(fmt.get('vcodec') not in (None, 'none') and has_audio(fmt) for fmt in allowed),
                    'incomplete_formats': (all(fmt.get('vcodec') == 'none' for fmt in allowed)
                                           or all(fmt.get('acodec') == 'none' for fmt in allowed))}
        found = False
        for selected in base_selector(narrowed):
            streams = selected.get('requested_formats') or [selected]
            audio = [fmt for fmt in streams if has_audio(fmt)]
            if not audio or any(track_details(fmt)['id'] != selected_id for fmt in audio):
                continue
            task.advanced['audio_track_label'] = track['label']
            task.advanced['audio_track_language'] = track['language']
            found = True
            yield selected
        if not found:
            raise ValueError('La pista elegida no está disponible con esa calidad de video. Elige otra calidad o pista de audio.')

    return select
