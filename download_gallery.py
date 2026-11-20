"""Persistent download gallery with local thumbnails and WebView-compatible playback."""
import json
import subprocess
import tempfile
import threading
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from flask import jsonify, send_file

from local_audio import start_process, _processes, _process_lock
from media_tools import register_media

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.vob', '.mov', '.avi', '.wmv', '.flv', '.mpeg', '.mpg', '.m4v', '.ts'}


def create_gallery(connection, platforms):
    existing = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'gallery'"
    ).fetchone()
    if existing:
        return
    connection.execute("""
        CREATE TABLE gallery (
            id INTEGER PRIMARY KEY,
            filepath TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            duration INTEGER NOT NULL,
            downloaded_at TEXT NOT NULL
        )
    """)
    placeholders = ', '.join('?' for _ in platforms)
    connection.execute(f"""
        INSERT OR REPLACE INTO gallery (id, filepath, title, source, duration, downloaded_at)
        SELECT id, filepath, title, source, COALESCE(duration, 0), downloaded_at
        FROM history
        WHERE source IN ({placeholders}) AND mode IN ('video_audio', 'video_only') AND filepath != ''
        ORDER BY id
    """, tuple(platforms))


def record_video(connection, task):
    connection.execute("""
        INSERT OR REPLACE INTO gallery (filepath, title, source, duration, downloaded_at)
        VALUES (?, ?, ?, ?, ?)
    """, (task.final_path, task.title, task.source, task.duration or 0, task.completed_at))


def run_tool(args, timeout):
    process = start_process(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        output, errors = process.communicate(timeout=timeout)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, args, output, errors)
        return output
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
        with _process_lock:
            _processes.discard(process)


@lru_cache(maxsize=192)
def thumbnail(ffmpeg, path, mtime_ns, size):
    # Use the file signature as part of the cache key so replacements get fresh artwork.
    return run_tool([
        ffmpeg, '-nostdin', '-v', 'error', '-protocol_whitelist', 'file', '-i', str(path),
        '-map', '0:V:0', '-an', '-frames:v', '1',
        '-vf', 'scale=480:270:force_original_aspect_ratio=decrease',
        '-f', 'image2pipe', '-c:v', 'mjpeg', 'pipe:1',
    ], timeout=15)


def native_playback(ffprobe, path):
    extension = path.suffix.lower()
    if extension not in {'.mp4', '.m4v', '.webm'}:
        return False
    if not ffprobe:
        return True
    streams = json.loads(run_tool([
        ffprobe, '-v', 'error', '-protocol_whitelist', 'file',
        '-show_entries', 'stream=codec_type,codec_name,pix_fmt',
        '-of', 'json', str(path),
    ], timeout=15)).get('streams', [])
    video = next((stream for stream in streams if stream.get('codec_type') == 'video'), {})
    audio = next((stream.get('codec_name') for stream in streams if stream.get('codec_type') == 'audio'), None)
    if extension == '.webm':
        return video.get('codec_name') in {'vp8', 'vp9', 'av1'} and audio in {None, 'opus', 'vorbis'}
    return video.get('codec_name') == 'h264' and video.get('pix_fmt') in {'yuv420p', 'yuvj420p'} and audio in {None, 'aac', 'mp3'}


def register(app, history, platforms, find_tool, human_duration):
    platform_keys = {platform.name: key for key, platform in platforms.items()}
    artwork_slots = threading.BoundedSemaphore(3)
    transcode_lock = threading.Lock()
    preview_directory = None

    def saved_video(row):
        path = Path(row['filepath'])
        return path.suffix.lower() in VIDEO_EXTENSIONS and path.is_file()

    def entry(video_id):
        with history.connect() as connection:
            row = connection.execute("SELECT * FROM gallery WHERE id = ?", (video_id,)).fetchone()
        if row and saved_video(row):
            return row
        return None

    @app.get('/api/gallery')
    def list_gallery():
        with history.connect() as connection:
            rows = connection.execute('SELECT * FROM gallery ORDER BY downloaded_at DESC, id DESC').fetchall()
        return jsonify(ok=True, videos=[
            dict(id=row['id'], title=row['title'], source=row['source'],
                 platform=platform_keys[row['source']], duration=human_duration(row['duration']))
            for row in rows if row['source'] in platform_keys and saved_video(row)
        ])

    @app.get('/api/gallery/<int:video_id>/thumbnail')
    def gallery_thumbnail(video_id):
        row = entry(video_id)
        ffmpeg = find_tool('ffmpeg')
        if not row or not ffmpeg:
            return '', 404
        path = Path(row['filepath'])
        try:
            stat = path.stat()
            with artwork_slots:
                image = thumbnail(ffmpeg, path, stat.st_mtime_ns, stat.st_size)
        except (OSError, subprocess.SubprocessError):
            return '', 404
        return send_file(BytesIO(image), mimetype='image/jpeg') if image else ('', 404)

    @app.post('/api/gallery/<int:video_id>/play')
    def play(video_id):
        nonlocal preview_directory
        row = entry(video_id)
        if not row:
            return jsonify(ok=False, error='El video ya no está en su carpeta original.'), 404
        path = Path(row['filepath'])
        try:
            if native_playback(find_tool('ffprobe'), path):
                return jsonify(register_media(path, title=row['title']))
            ffmpeg = find_tool('ffmpeg')
            if not ffmpeg:
                return jsonify(ok=False, error='Se necesita FFmpeg para reproducir este formato.'), 422
            with transcode_lock:
                if preview_directory is None:
                    preview_directory = tempfile.TemporaryDirectory(prefix='videoflow-gallery-', ignore_cleanup_errors=True)
                stat = path.stat()
                preview = Path(preview_directory.name) / f'{video_id}-{stat.st_mtime_ns}-{stat.st_size}.mp4'
                if not preview.is_file():
                    partial = preview.with_suffix('.partial.mp4')
                    try:
                        run_tool([
                            ffmpeg, '-nostdin', '-v', 'error', '-y', '-protocol_whitelist', 'file', '-i', str(path),
                            '-map', '0:V:0', '-map', '0:a:0?', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac', '-movflags', '+faststart', str(partial),
                        ], timeout=1200)
                        partial.replace(preview)
                    finally:
                        partial.unlink(missing_ok=True)
                return jsonify(register_media(preview, title=row['title']))
        except (ValueError, OSError, subprocess.SubprocessError):
            return jsonify(ok=False, error='No se pudo preparar este video para reproducirlo.'), 422
