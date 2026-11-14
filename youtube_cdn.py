"""Try only the Google video mirrors advertised by the original media URL.

The query/path and its access signatures remain unchanged. Each request has a
bounded set of candidates; normal cookie, proxy, TLS and range handling belongs
to yt-dlp. See upstream issue yt-dlp/yt-dlp#1986.
"""
import re
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit

from yt_dlp import YoutubeDL
from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import HTTPError, ProxyError, RequestError, SSLError

from network_recovery import is_connection_error


def media_candidates(url):
    """Original and up to two mirrors explicitly present in YouTube's mn field."""
    try:
        parts = urlsplit(url)
        if (parts.scheme != 'https' or parts.username or parts.password
                or parts.port not in (None, 443)):
            return [url]
        host = re.fullmatch(r'(r{1,2}\d{1,3})(---|\.)(sn-[a-z0-9-]{1,80})\.googlevideo\.com',
                            parts.hostname or '')
        if not host or not re.match(r'^/(?:videoplayback(?:/|$)|api/manifest/)', parts.path):
            return [url]
        fields = parse_qs(parts.query).get('mn', [])
        if len(fields) == 1:
            advertised = fields[0].split(',')
        elif not fields:
            match = re.search(r'(?:^|/)mn/([^/]+)', parts.path)
            advertised = unquote(match[1]).split(',') if match else []
        else:
            return [url]
        if host[3] not in advertised:
            return [url]
        result = [url]
        for server in advertised[:8]:
            if not re.fullmatch(r'sn-[a-z0-9-]{1,80}', server) or server == host[3]:
                continue
            mirror = host[1] + host[2] + server + '.googlevideo.com'
            netloc = mirror + (':443' if parts.port == 443 else '')
            candidate = urlunsplit(parts._replace(netloc=netloc))
            if candidate not in result:
                result.append(candidate)
            if len(result) == 3:
                break
        return result
    except (TypeError, ValueError):
        return [url]


def retryable_server_error(error):
    if isinstance(error, (SSLError, ProxyError)):
        return False
    if isinstance(error, HTTPError):
        return error.status in {500, 502, 503, 504}
    return is_connection_error(error)


class YouTubeCDNDownloader(YoutubeDL):
    def __init__(self, params, *, checkpoint, on_server_change, enabled=True):
        self._cdn_checkpoint = checkpoint
        self._cdn_on_change = on_server_change
        self._cdn_enabled = enabled
        self._cdn_preferred = {}
        super().__init__(params)

    def urlopen(self, request):
        if not self._cdn_enabled or not isinstance(request, (str, Request)):
            return super().urlopen(request)
        original = Request(request) if isinstance(request, str) else request
        if original.method not in {'GET', 'HEAD'} or original.data is not None:
            return super().urlopen(request)
        candidates = media_candidates(original.url)
        if len(candidates) < 2:
            return super().urlopen(request)
        origin_host = urlsplit(original.url).hostname
        preferred = self._cdn_preferred.get(origin_host)
        candidates.sort(key=lambda url: urlsplit(url).hostname != preferred)
        for index, url in enumerate(candidates):
            self._cdn_checkpoint()
            if url != original.url:
                self._cdn_on_change()
            current = original.copy()
            current.update(url=url)
            if 'Host' in current.headers:
                current.headers['Host'] = urlsplit(url).netloc
            # Avoid spending every ordinary retry on one unresponsive cache.
            timeout = current.extensions.get('timeout') or self.params.get('socket_timeout') or 30
            current.extensions['timeout'] = min(float(timeout), 12)
            try:
                response = super().urlopen(current)
            except RequestError as error:
                if not retryable_server_error(error) or index == len(candidates) - 1:
                    raise
                if isinstance(error, HTTPError):
                    error.close()
                continue
            self._cdn_preferred[origin_host] = urlsplit(url).hostname
            return response
