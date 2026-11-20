"""Check and stage verified FFmpeg releases for this Windows application."""
import hashlib
import logging
import os
import re
import subprocess
import tempfile
import threading
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

VERSION_URL = 'https://www.gyan.dev/ffmpeg/builds/release-version'
DOWNLOAD_URL = 'https://www.gyan.dev/ffmpeg/builds/'
TOOLS = ('ffmpeg', 'ffprobe')
MAX_ARCHIVE_SIZE = 512 * 1024**2
BUSY_INSTALL_STATES = {'downloading', 'validating'}
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


class UpdateError(ValueError):
    pass


class GyanRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urlsplit(newurl)
        if url.scheme != 'https' or url.netloc != 'www.gyan.dev':
            raise UpdateError('El proveedor devolvió una dirección de descarga no válida.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def provider_open(request, timeout):
    return urllib.request.build_opener(GyanRedirects()).open(request, timeout=timeout)


def version_tuple(value):
    match = re.fullmatch(r'(\d+)\.(\d+)(?:\.(\d+))?', value.strip())
    if not match:
        raise ValueError('El proveedor no devolvió una versión válida de FFmpeg.')
    return tuple(int(part or 0) for part in match.groups())


def read_version(executable, tool, runner=subprocess.run):
    if not executable:
        return ''
    try:
        result = runner([str(executable), '-version'], capture_output=True, text=True,
                        timeout=8, creationflags=CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return ''
    match = re.match(rf'^{tool} version (\d+\.\d+(?:\.\d+)?)\b', result.stdout)
    return match.group(1) if result.returncode == 0 and match else ''


def valid_pair(folder, version, runner=subprocess.run):
    expected = version_tuple(version)
    for tool in TOOLS:
        executable = folder / f'{tool}.exe'
        detected = read_version(executable, tool, runner) if executable.is_file() else ''
        if not detected or version_tuple(detected) != expected:
            return False
    return True


def select_managed_pair(root, fallback, runner=subprocess.run):
    """Select once at launch so a running job keeps using the same build."""
    try:
        directories = list(root.iterdir())
    except OSError:
        return None
    candidates = []
    for directory in directories:
        match = re.fullmatch(r'(\d+\.\d+(?:\.\d+)?)-[0-9a-f]{12}', directory.name)
        if match and directory.is_dir():
            version = match.group(1)
            candidates.append((version_tuple(version), version, directory))
    if not candidates:
        return None
    current = read_version(fallback('ffmpeg'), 'ffmpeg', runner)
    minimum = version_tuple(current) if current else (0, 0, 0)
    for parts, version, folder in sorted(candidates, reverse=True):
        if parts < minimum:
            break
        if valid_pair(folder, version, runner):
            return folder
    return None


def system_tar():
    if os.name == 'nt':
        path = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'tar.exe'
        if path.is_file():
            return str(path)
    return None


def unpack_release(archive, destination, version, tar):
    # Stream only the exact requested entries. Archive paths never become output paths.
    command = [tar, '-xOf', str(archive)]
    prefix = f'ffmpeg-{version}-full_build'
    for tool in TOOLS:
        name = f'{tool}.exe'
        with (destination / name).open('xb') as output:
            subprocess.run([*command, f'{prefix}/bin/{name}'], stdout=output,
                           stderr=subprocess.PIPE, timeout=160, check=True, creationflags=CREATE_NO_WINDOW)


class FFmpegUpdates:
    def __init__(self, find_tool, opener=provider_open, runner=subprocess.run, *, root=None,
                 unpack=unpack_release):
        self.find_tool, self.opener, self.runner = find_tool, opener, runner
        self.root, self.unpack = root, unpack
        self.tar = system_tar() if root is not None else None
        self.lock = threading.RLock()
        self.state = dict(status='idle', current='', latest='', available=False, checked_at='', error='',
                          download_url=DOWNLOAD_URL, install_supported=self.tar is not None,
                          install_status='idle', install_error='', pending_version='', downloaded=0, total=0)

    def status(self):
        with self.lock:
            return self.state.copy()

    def start(self):
        with self.lock:
            if self.state['status'] == 'checking' or self.state['install_status'] in BUSY_INSTALL_STATES:
                return self.state.copy()
            self.state.update(status='checking', error='')
        threading.Thread(target=self.check, name='ffmpeg-version-check', daemon=True).start()
        return self.status()

    def check(self):
        current = ''
        try:
            current = read_version(self.find_tool('ffmpeg'), 'ffmpeg', self.runner)
            latest = self._read_text(VERSION_URL)
            latest_parts = version_tuple(latest)
            available = not current or latest_parts > version_tuple(current)
            if self.tar and current and latest_parts == version_tuple(current):
                probe = read_version(self.find_tool('ffprobe'), 'ffprobe', self.runner)
                available = not probe or version_tuple(probe) != latest_parts
            with self.lock:
                self.state.update(status='ready', current=current, latest=latest, available=available, error='',
                                  checked_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        except Exception as exc:
            with self.lock:
                self.state.update(status='error', current=current, available=False, error=str(exc)[:240],
                                  checked_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))

    def _open(self, url, timeout):
        request = urllib.request.Request(url, headers={'User-Agent': 'VideoFlowLocal/FFmpegUpdates',
                                                       'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity'})
        return self.opener(request, timeout=timeout)

    def _read_text(self, url):
        with self._open(url, 10) as response:
            return response.read(128).decode('utf-8').strip()

    def install(self):
        with self.lock:
            if self.state['install_status'] in BUSY_INSTALL_STATES or self.state['pending_version']:
                return self.state.copy()
            if not self.tar:
                raise UpdateError('La instalación desde VideoFlow requiere el descompresor de Windows.')
            if self.state['status'] != 'ready' or not self.state['available']:
                raise UpdateError('Comprueba si hay una nueva versión de FFmpeg primero.')
            version = self.state['latest']
            self.state.update(install_status='downloading', install_error='', downloaded=0, total=0)
        threading.Thread(target=self._install, args=(version,), name='ffmpeg-install', daemon=True).start()
        return self.status()

    def _download_archive(self, url, archive):
        expected = self._read_text(url + '.sha256')
        if not re.fullmatch(r'[a-fA-F0-9]{64}', expected):
            raise UpdateError('El proveedor no devolvió una suma SHA-256 válida.')
        digest = hashlib.sha256()
        downloaded = 0
        with self._open(url, 40) as response, archive.open('xb') as output:
            total = int(response.headers.get('Content-Length') or 0)
            if getattr(response, 'status', 200) != 200 or not 0 <= total <= MAX_ARCHIVE_SIZE:
                raise UpdateError('El proveedor no devolvió un paquete completo de FFmpeg.')
            with self.lock:
                self.state['total'] = total
            while chunk := response.read(1024**2):
                downloaded += len(chunk)
                if downloaded > MAX_ARCHIVE_SIZE:
                    raise UpdateError('El paquete de FFmpeg supera el tamaño permitido.')
                output.write(chunk)
                digest.update(chunk)
                with self.lock:
                    self.state['downloaded'] = downloaded
        if (total and downloaded != total) or digest.hexdigest() != expected.lower():
            raise UpdateError('La descarga de FFmpeg no coincide con la suma SHA-256 del proveedor.')

    def _install(self, version):
        try:
            version_tuple(version)
            self.root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='stage-', dir=self.root, ignore_cleanup_errors=True) as temporary:
                work = Path(temporary)
                archive, binary_folder = work / 'release.7z', work / 'verified'
                url = f'{DOWNLOAD_URL}packages/ffmpeg-{version}-full_build.7z'
                self._download_archive(url, archive)
                with self.lock:
                    self.state['install_status'] = 'validating'
                binary_folder.mkdir()
                self.unpack(archive, binary_folder, version, self.tar)
                if not valid_pair(binary_folder, version, self.runner):
                    raise UpdateError('FFmpeg y FFprobe deben funcionar y coincidir con la versión descargada.')
                binary_folder.rename(self.root / f'{version}-{uuid.uuid4().hex[:12]}')
            with self.lock:
                self.state.update(install_status='staged', pending_version=version)
        except Exception as exc:
            logging.getLogger(__name__).warning('Could not stage FFmpeg', exc_info=True)
            message = str(exc) if isinstance(exc, UpdateError) else 'No se pudo instalar FFmpeg. Comprueba tu conexión y el espacio libre.'
            with self.lock:
                self.state.update(install_status='error', install_error=message)


def register(app, find_tool, root):
    from flask import jsonify, request
    updater = FFmpegUpdates(find_tool, root=root)

    @app.route('/api/updates/ffmpeg', methods=['GET', 'POST'])
    def ffmpeg_update_status():
        return jsonify(ok=True, update=updater.start() if request.method == 'POST' else updater.status())

    @app.post('/api/updates/ffmpeg/install')
    def ffmpeg_install():
        try:
            return jsonify(ok=True, update=updater.install()), 202
        except UpdateError as exc:
            return jsonify(ok=False, error=str(exc)), 409

    return updater
