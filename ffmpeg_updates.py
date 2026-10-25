"""Non-blocking startup checks against Gyan's documented release-version API."""
import re
import subprocess
import threading
import urllib.request
from datetime import datetime, timezone

VERSION_URL = 'https://www.gyan.dev/ffmpeg/builds/release-version'
DOWNLOAD_URL = 'https://www.gyan.dev/ffmpeg/builds/'


def version_tuple(value):
    match = re.fullmatch(r'(\d+)\.(\d+)(?:\.(\d+))?', value.strip())
    if not match:
        raise ValueError('El proveedor no devolvió una versión válida de FFmpeg.')
    return tuple(int(part or 0) for part in match.groups())


class FFmpegUpdates:
    def __init__(self, find_tool, opener=urllib.request.urlopen, runner=subprocess.run):
        self.find_tool, self.opener, self.runner = find_tool, opener, runner
        self.lock = threading.RLock()
        self.state = dict(status='idle', current='', latest='', available=False, checked_at='', error='', download_url=DOWNLOAD_URL)

    def status(self):
        with self.lock:
            return self.state.copy()

    def start(self):
        with self.lock:
            if self.state['status'] == 'checking':
                return self.state.copy()
            self.state.update(status='checking', error='')
        threading.Thread(target=self.check, name='ffmpeg-version-check', daemon=True).start()
        return self.status()

    def check(self):
        current = ''
        try:
            executable = self.find_tool('ffmpeg')
            if executable:
                result = self.runner([executable, '-version'], capture_output=True, text=True, timeout=5,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                match = re.search(r'^ffmpeg version (\d+\.\d+(?:\.\d+)?)\b', result.stdout)
                if match:
                    current = match.group(1)
            request = urllib.request.Request(VERSION_URL, headers={'User-Agent':'VideoFlowLocal/FFmpegUpdates', 'Cache-Control':'no-cache'})
            with self.opener(request, timeout=10) as response:
                latest = response.read(128).decode('utf-8').strip()
            latest_parts = version_tuple(latest)
            available = not current or latest_parts > version_tuple(current)
            with self.lock:
                self.state.update(status='ready', current=current, latest=latest, available=available, error='',
                                  checked_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        except Exception as exc:
            with self.lock:
                self.state.update(status='error', current=current, available=False, error=str(exc)[:240],
                                  checked_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))


def register(app, find_tool):
    from flask import jsonify, request
    updater = FFmpegUpdates(find_tool)

    @app.route('/api/updates/ffmpeg', methods=['GET', 'POST'])
    def ffmpeg_update_status():
        return jsonify(ok=True, update=updater.start() if request.method == 'POST' else updater.status())

    return updater
