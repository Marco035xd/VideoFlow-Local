"""Estimate saved collection sizes from YouTube metadata without queuing jobs."""
import math
import threading
import time
import uuid
from types import SimpleNamespace

import yt_dlp

from collections_download import collection_entries, collection_options
from download_options import video_selector

SAMPLE_LIMIT = 6
CATALOG_TTL = 300


class EstimateCancelled(Exception):
    pass


def positive_number(value):
    if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
        return value
    return 0


def stream_rate(stream, duration, *, silent):
    # A muxed fallback needs to exclude the audio bitrate in video-only mode.
    if silent and stream.get('acodec') != 'none':
        video_rate = positive_number(stream.get('vbr'))
        if not video_rate:
            audio_rate = positive_number(stream.get('abr'))
            video_rate = max(0, positive_number(stream.get('tbr')) - audio_rate) if audio_rate else 0
        if video_rate:
            return video_rate * 125
    size = positive_number(stream.get('filesize')) or positive_number(stream.get('filesize_approx'))
    if size and duration:
        return size / duration
    rate = positive_number(stream.get('tbr')) or positive_number(stream.get('vbr')) or positive_number(stream.get('abr'))
    return rate * 125


def output_rate(info, duration, options):
    if options['mode'] == 'audio':
        if options['format'] in {'wav', 'flac'}:
            sample_rate = positive_number(info.get('asr')) or 48000
            channels = positive_number(info.get('audio_channels')) or 2
            pcm_rate = sample_rate * channels * 2  # 16-bit samples
            # FLAC compression varies with the source. Use 60% of PCM for the estimate.
            return pcm_rate if options['format'] == 'wav' else pcm_rate * 0.6
        if options['format'] == 'm4a' and info.get('acodec') != 'aac' and not str(info.get('acodec')).startswith('mp4a'):
            return 128 * 125  # Nominal bitrate for FFmpeg's AAC conversion.
    streams = info.get('requested_formats') or [info]
    rates = [stream_rate(stream, duration, silent=options['mode'] == 'video_only') for stream in streams]
    return sum(rates) if all(rates) else 0


def estimate_size(entries, options, sample):
    """Use per-video rates where available and project the sample over the remaining durations."""
    advanced = options['advanced']
    end = advanced['end']
    eligible = [(url, duration) for url, duration in entries if end is None or not duration or duration >= end]
    total = len(eligible)
    if options['mode'] == 'audio' and options['format'] in {'mp3', 'ogg'}:
        durations = [end - advanced['start'] if end is not None else duration
                     for _, duration in eligible if duration]
        return dict(size_bytes=round(sum(durations) * int(options['quality']) * 125),
                    estimated=len(durations), total=total, samples=0, projected=False)

    sample_count = min(total, SAMPLE_LIMIT)
    indices = [i * (total - 1) // max(1, sample_count - 1) for i in range(sample_count)]
    sampled = {}
    for index in indices:
        url, duration = eligible[index]
        info = sample(url)
        duration = positive_number(info.get('duration')) or duration
        sampled[index] = (duration, output_rate(info, duration, options) if info else 0)

    size = 0
    estimated = 0
    sample_size = 0
    sample_duration = 0
    unsampled_duration = 0
    unsampled_count = 0
    for index, (_, duration) in enumerate(eligible):
        if index in sampled:
            duration, rate = sampled[index]
            if end is not None and duration and duration < end:
                total -= 1
                continue
            if duration and rate:
                seconds = end - advanced['start'] if end is not None else duration
                size += seconds * rate
                estimated += 1
                sample_size += seconds * rate
                sample_duration += seconds
        elif duration:
            unsampled_duration += end - advanced['start'] if end is not None else duration
            unsampled_count += 1
    samples = estimated
    projected = bool(sample_duration and unsampled_count)
    if projected:
        size += unsampled_duration * sample_size / sample_duration
        estimated += unsampled_count
    return dict(size_bytes=round(size), estimated=estimated, total=total, samples=samples, projected=projected)


class CollectionEstimates:
    def __init__(self, environment, source_for_url):
        self.environment = environment
        self.source_for_url = source_for_url
        self.lock = threading.Lock()
        self.current = None
        self.worker = None
        self.catalog = None

    def start(self, payload):
        url, options = collection_options(payload, self.source_for_url)
        identifier = uuid.uuid4().hex
        with self.lock:
            self.current = (identifier, url, options, {'status': 'pending'})
            if self.worker is None:
                self.worker = threading.Thread(target=self._run, daemon=True)
                self.worker.start()
        return identifier

    def cancel(self, identifier):
        with self.lock:
            if self.current and self.current[0] == identifier:
                self.current = None

    def result(self, identifier):
        with self.lock:
            if self.current and self.current[0] == identifier:
                return self.current[3].copy()

    def _run(self):
        while True:
            with self.lock:
                job = self.current
                if not job or job[3]['status'] != 'pending':
                    self.worker = None
                    return
            try:
                result = self._estimate(job)
            except EstimateCancelled:
                continue
            except Exception:
                # Extractor exceptions can contain session information and signed URLs.
                result = {'status': 'error'}
            with self.lock:
                if self.current is job:
                    job[3].update(result)

    def _estimate(self, job):
        _, url, options, _ = job

        def check(*args, **kwargs):
            with self.lock:
                if self.current is not job:
                    raise EstimateCancelled()

        browser = options['browser']
        env = self.environment('YouTube', browser)
        common = dict(quiet=True, no_warnings=True, skip_download=True, socket_timeout=12,
                      retries=0, extractor_retries=0, match_filter=check, **env)
        cache_key = (url, browser)
        cache = self.catalog
        private = options['advanced']['incognito']
        if not private and cache and cache[0] == cache_key and time.monotonic() < cache[1]:
            entries = cache[2]
        else:
            with yt_dlp.YoutubeDL(dict(common, extract_flat='in_playlist', lazy_playlist=True)) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {'status': 'error'}
                entries = [(video_url, positive_number(entry.get('duration')))
                           for entry, video_url in collection_entries(info, self.source_for_url, check) if entry]
            if not private:
                self.catalog = (cache_key, time.monotonic() + CATALOG_TTL, entries)

        selector = 'bestaudio/best' if options['mode'] == 'audio' else video_selector(SimpleNamespace(**options))

        def sample(video_url):
            check()
            try:
                with yt_dlp.YoutubeDL(dict(common, noplaylist=True, format=selector)) as ydl:
                    return ydl.extract_info(video_url, download=False) or {}
            except yt_dlp.utils.DownloadError:
                return {}

        return {'status': 'ready', **estimate_size(entries, options, sample)}
