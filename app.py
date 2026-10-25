from __future__ import annotations

import json
import os
import queue
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, jsonify, render_template, request
from app_paths import APP_DIR, APP_VERSION, DATA_DIR, IS_FROZEN
from appearance import DEFAULT_APPEARANCE, normalize_appearance
from localization import LANGUAGES, normalize_language
from download_options import validate_options, video_selector, apply_options

SETTINGS_FILE = DATA_DIR / "settings.json"
DB_FILE = DATA_DIR / "history.db"
HOST = "127.0.0.1"
PORT = 8765
PLATFORMS = {"youtube": "YouTube", "facebook": "Facebook", "tiktok": "TikTok"}

DEFAULT_FOLDER = str((Path.home() / "Downloads").resolve())
DEFAULT_SETTINGS = {
    "language": "es",
    "default_folder": DEFAULT_FOLDER,
    "platform_folders": {},
    "default_format": "mp4",
    "default_video_quality": "720",
    "default_audio_quality": "192",
    "theme": "dark",
    "appearance": DEFAULT_APPEARANCE.copy(),
    "notifications": True,
    "max_concurrent": 3,
    "background_mode": True,
    "keep_awake": True,
    "welcome_seen": False,
    "rate_limit_kbps": 0,
    "retry_count": 5,
    "conversion_folder": DEFAULT_FOLDER,
    "video_conversion_folder": DEFAULT_FOLDER,
}

SUPPORTED_FORMATS = [
    "mp4", "mp3", "vob", "avi", "mkv", "mov",
    "wmv", "flv", "webm", "mpeg", "wav", "aac"
]

AUDIO_FORMATS = ["mp3", "wav", "aac", "flac", "ogg", "m4a"]



def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def human_bytes(value: int | float | None) -> str:
    if not value:
        return "—"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return "—"


def human_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def source_for_url(url: str) -> str | None:
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"}:
            return None
        if host == "youtu.be" or any(host == name or host.endswith("." + name) for name in ("youtube.com", "youtube-nocookie.com")):
            return "YouTube"
        if host == "fb.watch" or any(host == name or host.endswith("." + name) for name in ("facebook.com", "fb.com")):
            return "Facebook"
        if host == "tiktok.com" or host.endswith(".tiktok.com"):
            return "TikTok"
        return None
    except Exception:
        return None


def find_tool(name: str) -> str | None:
    bundled = APP_DIR / "bin" / (name + ".exe")
    if IS_FROZEN and bundled.is_file():
        return str(bundled)
    found = shutil.which(name)
    if found:
        return found
    exe = name + (".exe" if os.name == "nt" else "")
    candidates = [APP_DIR / "bin" / exe, APP_DIR / exe]
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        package = "Gyan.FFmpeg_*" if name in {"ffmpeg", "ffprobe"} else "DenoLand.Deno_*"
        if local.exists():
            candidates.extend(local.glob(f"{package}/**/{exe}"))
    return next((str(path) for path in candidates if path.is_file()), None)


def ydl_environment(source: str = "YouTube", browser: str = "") -> dict[str, Any]:
    options: dict[str, Any] = {}
    ffmpeg = find_tool("ffmpeg")
    if ffmpeg:
        options["ffmpeg_location"] = str(Path(ffmpeg).parent)
    deno = find_tool("deno")
    if deno:
        options["js_runtimes"] = {"deno": {"path": deno}}
    if source == "Facebook":
        from yt_dlp.networking.impersonate import ImpersonateTarget
        options["impersonate"] = ImpersonateTarget("chrome")
        if browser in {"chrome", "edge", "firefox"}:
            options["cookiesfrombrowser"] = (browser,)
    return options


def describe_error(exc: Exception, source: str) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    if source == "Facebook" and "Cannot parse data" in message:
        return "Facebook no entregó datos de este video. Comprueba que el enlace abra en el navegador y, si requiere sesión, elige ese navegador en la pestaña Facebook."
    if source == "TikTok" and "IP address is blocked" in message:
        return "TikTok bloqueó el acceso a esta publicación desde esta conexión. Prueba otro enlace público o inténtalo más tarde."
    return message[:600]


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        if not self.path.exists():
            self.save(DEFAULT_SETTINGS.copy())

    def load(self) -> dict[str, Any]:
        with self.lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            return self._merge(data)

    @staticmethod
    def _merge(data: dict[str, Any]) -> dict[str, Any]:
        merged = {**DEFAULT_SETTINGS, **data}
        merged['language'] = normalize_language(data.get('language'))
        merged['theme'] = data.get('theme') if data.get('theme') in ('light', 'dark', 'system') else 'dark'
        merged['appearance'] = normalize_appearance(data.get('appearance'))
        folders = data.get("platform_folders")
        folders = folders if isinstance(folders, dict) else {}
        merged["platform_folders"] = {
            source: str(folders.get(source) or merged["default_folder"])
            for source in PLATFORMS
        }
        return merged

    def save(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            merged = self._merge(data)
            self.path.write_text(
                json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return merged

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            current = self.load()
            patch = patch.copy()
            if "platform_folders" in patch:
                current["platform_folders"].update(patch.pop("platform_folders"))
            current.update(patch)
            return self.save(current)

    def folder_for(self, source: str) -> str:
        return self.load()["platform_folders"][source.lower()]

    def remember_folder(self, source: str, folder: str) -> dict[str, Any]:
        source_key = source.lower()
        if source_key not in PLATFORMS:
            raise ValueError("Plataforma no válida.")
        return self.update({"platform_folders": {source_key: folder}})


class HistoryStore:
    def __init__(self, path: Path):
        self.path = path
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=20)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    def _init_db(self) -> None:
        with self.connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    video_id TEXT,
                    title TEXT NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    format TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    size_bytes INTEGER DEFAULT 0,
                    filepath TEXT NOT NULL,
                    thumbnail TEXT,
                    duration INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'YouTube',
                    mode TEXT DEFAULT 'video_audio',
                    url TEXT NOT NULL DEFAULT ''
                )
                """
            )
            columns = {row[1] for row in con.execute("PRAGMA table_info(history)")}
            if "source" not in columns:
                con.execute("ALTER TABLE history ADD COLUMN source TEXT DEFAULT 'YouTube'")
            if "mode" not in columns:
                con.execute("ALTER TABLE history ADD COLUMN mode TEXT DEFAULT 'video_audio'")
            if "url" not in columns:
                con.execute("ALTER TABLE history ADD COLUMN url TEXT NOT NULL DEFAULT ''")
            con.commit()

    def add(self, task: "DownloadTask") -> None:
        if task.advanced.get('incognito'):
            return
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO history
                (task_id, video_id, title, downloaded_at, format, quality,
                 size_bytes, filepath, thumbnail, duration, source, mode, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.video_id,
                    task.title,
                    task.completed_at or now_iso(),
                    task.output_format,
                    task.quality,
                    int(task.final_size or 0),
                    task.final_path or "",
                    task.thumbnail,
                    int(task.duration or 0),
                    task.source,
                    task.mode,
                    task.original_url or task.url,
                ),
            )
            con.commit()

    def list(self, limit: int = 250) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["size_human"] = human_bytes(item.get("size_bytes"))
            item["duration_human"] = human_duration(item.get("duration"))
            item["folder"] = str(Path(item["filepath"]).parent) if item.get("filepath") else ""
            result.append(item)
        return result

    def clear(self) -> None:
        with self.connect() as con:
            con.execute("DELETE FROM history")
            con.commit()


class DownloadCancelled(Exception):
    pass


@dataclass
class DownloadTask:
    id: str
    url: str
    video_id: str
    title: str
    thumbnail: str
    duration: int
    output_format: str
    quality: str
    folder: str
    source: str = "YouTube"
    mode: str = "video_audio"
    browser: str = ""
    save_path: str = ""
    overwrite: bool = False
    original_url: str = ""
    estimated_size: int = 0
    status: str = "Pendiente"
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: float = 0.0
    eta: int | None = None
    error: str = ""
    created_at: str = field(default_factory=now_iso)
    completed_at: str = ""
    final_path: str = ""
    final_size: int = 0
    local_path: str = ""
    phase: str = ""
    outputs: list = field(default_factory=list)
    advanced: dict = field(default_factory=dict)
    pause_event: threading.Event = field(default_factory=threading.Event, repr=False)
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "video_id": self.video_id,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "duration_human": human_duration(self.duration),
            "format": self.output_format,
            "source": self.source,
            "mode": self.mode,
            "quality": self.quality,
            "folder": self.folder,
            "save_path": self.save_path,
            "estimated_size": self.estimated_size,
            "estimated_size_human": human_bytes(self.estimated_size),
            "status": self.status,
            "progress": round(self.progress, 1),
            "downloaded_bytes": self.downloaded_bytes,
            "downloaded_human": human_bytes(self.downloaded_bytes),
            "total_bytes": self.total_bytes,
            "total_human": human_bytes(self.total_bytes),
            "speed": self.speed,
            "speed_human": f"{human_bytes(self.speed)}/s" if self.speed else "—",
            "eta": self.eta,
            "eta_human": human_duration(self.eta),
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "final_path": self.final_path,
            "final_size": self.final_size,
            "final_size_human": human_bytes(self.final_size),
            "phase": self.phase,
            "outputs": self.outputs,
            "incognito": self.advanced.get('incognito', False),
        }


class QuietLogger:
    def __init__(self, task: DownloadTask):
        self.task = task

    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        if msg and not self.task.error:
            self.task.error = str(msg)


class DownloadManager:
    def __init__(self, settings: SettingsStore, history: HistoryStore):
        self.settings = settings
        self.history = history
        self.tasks: dict[str, DownloadTask] = {}
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.work_queue: queue.Queue[str] = queue.Queue()
        self.active_count = 0
        threading.Thread(target=self._worker, name='download-dispatcher', daemon=True).start()

    def notify_settings_changed(self) -> None:
        with self.condition:
            self.condition.notify_all()

    def count_unfinished(self) -> int:
        with self.lock:
            return sum(
                1
                for task in self.tasks.values()
                if task.status not in {"Completado", "Error", "Cancelado"}
            )

    def add(self, payload: dict[str, Any]) -> DownloadTask:
        task = DownloadTask(
            id=uuid.uuid4().hex[:10],
            url=str(payload["url"]).strip(),
            video_id=str(payload.get("video_id") or "video"),
            title=str(payload.get("title") or "Video"),
            thumbnail=str(payload.get("thumbnail") or ""),
            duration=int(payload.get("duration") or 0),
            output_format=str(payload["format"]).lower(),
            quality=str(payload["quality"]),
            folder=str(Path(payload["folder"]).expanduser().resolve()),
            source="Local" if payload.get("local_path") else source_for_url(str(payload["url"])) or "Web",
            local_path=str(payload.get("local_path") or ""),
            mode=str(payload.get("mode") or "video_audio"),
            browser=str(payload.get("browser") or ""),
            save_path=str(payload.get("save_path") or ""),
            overwrite=payload.get("overwrite") is True,
            original_url=str(payload.get("original_url") or payload["url"]).strip(),
            estimated_size=int(payload.get("estimated_size") or 0),
            advanced=validate_options(payload),
        )
        with self.lock:
            if task.save_path and any(
                existing.save_path == task.save_path
                and existing.status not in {"Completado", "Error", "Cancelado"}
                for existing in self.tasks.values()
            ):
                raise ValueError("Ese archivo ya está reservado por otra descarga en curso.")
            self.tasks[task.id] = task
        self.work_queue.put(task.id)
        return task

    def list(self) -> list[dict[str, Any]]:
        with self.lock:
            values = sorted(
                self.tasks.values(), key=lambda item: item.created_at, reverse=True
            )
            return [task.as_dict() for task in values]

    def get(self, task_id: str) -> DownloadTask | None:
        with self.lock:
            return self.tasks.get(task_id)

    def pause(self, task_id: str) -> DownloadTask:
        task = self._require(task_id)
        if task.status == "Descargando":
            task.pause_event.set()
            task.status = "Pausado"
        return task

    def resume(self, task_id: str) -> DownloadTask:
        task = self._require(task_id)
        if task.status == "Pausado":
            task.pause_event.clear()
            task.status = "Descargando"
        return task

    def cancel(self, task_id: str) -> DownloadTask:
        task = self._require(task_id)
        if task.status not in {"Completado", "Error", "Cancelado"}:
            task.cancel_event.set()
            task.pause_event.clear()
            if task.status == "Pendiente":
                task.status = "Cancelado"
        return task

    def delete(self, task_id: str) -> None:
        task = self._require(task_id)
        if task.status not in {"Completado", "Error", "Cancelado"}:
            raise ValueError("Cancela la descarga antes de eliminarla de la lista.")
        with self.lock:
            self.tasks.pop(task_id, None)

    def _require(self, task_id: str) -> DownloadTask:
        task = self.get(task_id)
        if not task:
            raise KeyError("Descarga no encontrada.")
        return task

    def _worker(self) -> None:
        while True:
            task_id = self.work_queue.get()
            try:
                task = self.get(task_id)
                if not task or task.cancel_event.is_set():
                    if task:
                        task.status = "Cancelado"
                    continue

                slot_acquired = False
                with self.condition:
                    while True:
                        if task.cancel_event.is_set():
                            task.status = "Cancelado"
                            break
                        limit = int(self.settings.load().get("max_concurrent", 3))
                        if limit == 0 or self.active_count < limit:
                            self.active_count += 1
                            slot_acquired = True
                            break
                        self.condition.wait(timeout=1)

                if not slot_acquired:
                    continue

                try:
                    threading.Thread(target=self._run_task, args=(task,), daemon=True,
                                     name=f'download-{task.id}').start()
                except Exception as exc:
                    task.status, task.error = 'Error', str(exc)
                    with self.condition:
                        self.active_count -= 1
                        self.condition.notify_all()
            finally:
                self.work_queue.task_done()

    def _run_task(self, task):
        try:
            self._download(task)
        except Exception as exc:
            task.status, task.error = 'Error', str(exc)
        finally:
            with self.condition:
                self.active_count = max(0, self.active_count - 1)
                self.condition.notify_all()

    def _wait_if_paused(self, task: DownloadTask) -> None:
        while task.pause_event.is_set():
            if task.cancel_event.is_set():
                raise DownloadCancelled("Descarga cancelada")
            task.status = "Pausado"
            time.sleep(0.25)
        if task.cancel_event.is_set():
            raise DownloadCancelled("Descarga cancelada")

    def _download(self, task: DownloadTask) -> None:
        if task.mode == 'video_convert':
            from video_conversion import transcode
            return transcode(task, self.history, find_tool)
        if task.mode.startswith('separate_'):
            from audio_separation import separate
            return separate(task, self.history, find_tool)
        if task.local_path:
            from local_audio import convert
            return convert(task, self.history, find_tool)
        try:
            folder = Path(task.folder)
            folder.mkdir(parents=True, exist_ok=True)
            if not os.access(folder, os.W_OK):
                raise PermissionError("No hay permiso de escritura en la carpeta elegida.")
            if not find_tool("ffmpeg") or not find_tool("ffprobe"):
                raise RuntimeError(
                    "FFmpeg/FFprobe no están disponibles. Ejecuta INSTALAR.bat o agrégalos al PATH."
                )

            task.status = "Descargando"
            task.error = ""
            task.progress = max(task.progress, 0.1)

            def progress_hook(data: dict[str, Any]) -> None:
                self._wait_if_paused(task)
                status = data.get("status")
                if status == "downloading":
                    total = int(
                        data.get("total_bytes")
                        or data.get("total_bytes_estimate")
                        or task.estimated_size
                        or 0
                    )
                    downloaded = int(data.get("downloaded_bytes") or 0)
                    task.total_bytes = total
                    task.downloaded_bytes = downloaded
                    task.speed = float(data.get("speed") or 0)
                    task.eta = data.get("eta")
                    if total > 0:
                        task.progress = min(98.5, downloaded * 100 / total)
                    task.status = "Descargando"
                elif status == "finished":
                    task.progress = max(task.progress, 98.5)
                    task.status = "Procesando"

            def postprocessor_hook(data: dict[str, Any]) -> None:
                self._wait_if_paused(task)
                if data.get("status") in {"started", "processing"}:
                    task.status = "Procesando"
                    task.progress = max(task.progress, 98.5)

            quality_number = int(task.quality)
            quality_suffix = (f"{quality_number}kbps" if quality_number else "original") if task.mode == "audio" else (f"{quality_number}p" if quality_number else "original")
            output_template = str(
                folder / f"%(title).160B [%(id)s] [{quality_suffix}] [{task.id}].%(ext)s"
            )
            common_opts: dict[str, Any] = {
                "outtmpl": {"default": output_template},
                "noplaylist": True,
                "continuedl": True,
                "retries": self.settings.load().get("retry_count", 5),
                "fragment_retries": self.settings.load().get("retry_count", 5),
                "ratelimit": (self.settings.load().get("rate_limit_kbps", 0) * 1024) or None,
                "concurrent_fragment_downloads": 4,
                "windowsfilenames": True,
                "overwrites": False,
                "quiet": True,
                "no_warnings": True,
                "logger": QuietLogger(task),
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "socket_timeout": 30,
                **ydl_environment(task.source, task.browser),
            }

            if task.mode == "audio":
                common_opts.update(
                    {
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": task.output_format,
                                "preferredquality": str(quality_number) if task.output_format == "mp3" else None,
                            },
                            {"key": "FFmpegMetadata", "add_metadata": True},
                        ],
                    }
                )
            elif task.output_format == "vob":
                vob_height = min(480, quality_number)
                common_opts.update(
                    {
                        "format": (
                            f"bestvideo[height<={vob_height}]+bestaudio/"
                            f"best[height<={vob_height}]/best"
                        ),
                        "merge_output_format": "mp4",
                        "postprocessors": [
                            {"key": "FFmpegMetadata", "add_metadata": True}
                        ],
                    }
                )
            else:
                selector = video_selector(task)
                common_opts.update(
                    {
                        "format": selector,
                        "merge_output_format": 'mkv' if task.output_format in {'mov', 'avi'} else task.output_format,
                        "postprocessors": [
                            {
                                "key": "FFmpegVideoConvertor",
                                "preferedformat": task.output_format,
                            },
                            {"key": "FFmpegMetadata", "add_metadata": True},
                        ],
                    }
                )

            apply_options(common_opts, task)
            with yt_dlp.YoutubeDL(common_opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                if info:
                    task.video_id = str(info.get("id") or task.video_id or "video")
                    task.title = str(info.get("title") or task.title)
                    task.duration = int(task.advanced['end'] - task.advanced['start']) if task.advanced.get('start') is not None else int(info.get('duration') or task.duration)
                    if task.advanced.get('subtitles', 'none') != 'none' and not info.get('requested_subtitles'):
                        task.phase = 'Video guardado; el idioma de subtítulos elegido no está disponible.'

            self._wait_if_paused(task)
            if task.output_format == "vob":
                source_file = self._find_final_file(folder, task.id, "mp4")
                if not source_file:
                    source_file = self._find_final_file(folder, task.id, "")
                if not source_file:
                    raise RuntimeError("La descarga terminó, pero no se encontró el archivo intermedio.")
                final_file = self._convert_to_vob(task, source_file)
            else:
                final_file = self._find_final_file(folder, task.id, task.output_format)

            if final_file and task.mode == "video_only":
                final_file = self._strip_audio(task, final_file)

            if not final_file:
                raise RuntimeError("La descarga terminó, pero no se encontró el archivo final.")
            if final_file.suffix.lower() != f".{task.output_format}":
                raise RuntimeError("El archivo descargado no coincide con el formato elegido.")
            if task.save_path:
                target = Path(task.save_path)
                if target.exists() and not task.overwrite:
                    raise FileExistsError("El archivo elegido ya existe. Usa Guardar como para confirmar si deseas reemplazarlo.")
                if target.is_dir():
                    raise IsADirectoryError("La ruta elegida corresponde a una carpeta.")
                final_file.replace(target)
                for subtitle in folder.glob('*.srt'):
                    if f'[{task.id}]' in subtitle.name:
                        subtitle_target = target.with_suffix('.' + subtitle.name.rsplit('.', 2)[-2] + '.srt')
                        if subtitle_target.exists():
                            subtitle_target = subtitle_target.with_stem(f'{subtitle_target.stem} [{task.id}]')
                        subtitle.rename(subtitle_target)
                final_file = target

            task.final_path = str(final_file.resolve())
            task.final_size = final_file.stat().st_size
            task.total_bytes = task.final_size
            task.downloaded_bytes = task.final_size
            task.progress = 100.0
            task.completed_at = now_iso()
            self.history.add(task)
            task.status = "Completado"
        except DownloadCancelled:
            task.status = "Cancelado"
            task.error = ""
            self._cleanup_partials(Path(task.folder), task.id)
        except Exception as exc:
            if task.cancel_event.is_set():
                task.status = "Cancelado"
                task.error = ""
            else:
                task.status = "Error"
                task.error = describe_error(exc, task.source)
            self._cleanup_partials(Path(task.folder), task.id)

    def _strip_audio(self, task: DownloadTask, source_file: Path) -> Path:
        target_file = source_file.with_name(source_file.stem + ".video-only" + source_file.suffix)
        task.status = "Procesando"
        result = subprocess.run(
            [find_tool("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(source_file), "-map", "0:v:0", "-map", "0:s?", "-an", "-c:v", "copy", "-c:s", "copy", str(target_file)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or not target_file.is_file():
            target_file.unlink(missing_ok=True)
            raise RuntimeError("FFmpeg no pudo preparar el video sin audio: " + result.stderr[-350:])
        if task.cancel_event.is_set():
            target_file.unlink(missing_ok=True)
            raise DownloadCancelled("Descarga cancelada")
        source_file.unlink()
        target_file.replace(source_file)
        return source_file

    def _convert_to_vob(self, task: DownloadTask, source_file: Path) -> Path:
        target_file = source_file.with_suffix(".vob")
        command = [
            find_tool("ffmpeg") or "ffmpeg",
            "-y",
            "-i",
            str(source_file),
            "-vf",
            "scale=720:480:force_original_aspect_ratio=decrease,"
            "pad=720:480:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-r",
            "30000/1001",
            "-c:v",
            "mpeg2video",
            "-pix_fmt",
            "yuv420p",
            "-b:v",
            "6000k",
            "-maxrate",
            "9000k",
            "-bufsize",
            "1835k",
            "-g",
            "18",
            "-c:a",
            "ac3",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-f",
            "vob",
            "-progress",
            "pipe:1",
            "-nostats",
            str(target_file),
        ]
        task.status = "Procesando"
        task.progress = max(task.progress, 98.5)
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
        try:
            assert process.stdout is not None
            for raw_line in process.stdout:
                if task.cancel_event.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    target_file.unlink(missing_ok=True)
                    raise DownloadCancelled("Descarga cancelada")
                line = raw_line.strip()
                if line.startswith("out_time_ms=") and task.duration > 0:
                    try:
                        elapsed_seconds = int(line.split("=", 1)[1]) / 1_000_000
                        fraction = min(1.0, elapsed_seconds / task.duration)
                        task.progress = 98.5 + fraction * 1.4
                    except (TypeError, ValueError, ZeroDivisionError):
                        pass
            return_code = process.wait()
            if return_code != 0 or not target_file.exists():
                target_file.unlink(missing_ok=True)
                raise RuntimeError("FFmpeg no pudo convertir el video al formato VOB.")
        finally:
            if process.poll() is None:
                process.kill()

        if source_file != target_file:
            try:
                source_file.unlink(missing_ok=True)
            except OSError:
                pass
        return target_file

    @staticmethod
    def _find_final_file(folder: Path, video_id: str, output_format: str) -> Path | None:
        candidates: list[Path] = []
        if not folder.exists():
            return None
        for path in folder.iterdir():
            if not path.is_file():
                continue
            lower = path.name.lower()
            if lower.endswith((".part", ".ytdl", ".temp")):
                continue
            if f"[{video_id}]" in path.name:
                candidates.append(path)
        preferred = (
            [p for p in candidates if p.suffix.lower() == f".{output_format}"]
            if output_format
            else []
        )
        pool = preferred or candidates
        return max(pool, key=lambda p: p.stat().st_mtime, default=None)

    @staticmethod
    def _cleanup_partials(folder: Path, video_id: str) -> None:
        if not folder.exists():
            return
        for path in folder.iterdir():
            if not path.is_file() or f"[{video_id}]" not in path.name:
                continue
            if path.name.lower().endswith((".part", ".ytdl", ".temp")):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


settings_store = SettingsStore(SETTINGS_FILE)
history_store = HistoryStore(DB_FILE)
download_manager = DownloadManager(settings_store, history_store)
app = Flask(__name__)


@app.context_processor
def interface_language():
    return {'ui_language': settings_store.load()['language']}


app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


@app.before_request
def protect_local_api():
    if request.host.split(':')[0] not in {'127.0.0.1', 'localhost'}:
        return jsonify(ok=False, error='Host no permitido.'), 403
    if request.path.startswith('/api/'):
        origin = request.headers.get('Origin')
        if request.headers.get('Sec-Fetch-Site') in {'cross-site', 'same-site'} or (origin and origin != request.host_url.rstrip('/')):
            return jsonify(ok=False, error='Solo se permiten solicitudes desde VideoFlow.'), 403
        if request.method in {'POST', 'PUT', 'DELETE'} and request.data and not request.is_json:
            return jsonify(ok=False, error='Se requiere JSON.'), 415


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/system")
def api_system():
    try:
        ytdlp_version = yt_dlp.version.__version__
    except Exception:
        ytdlp_version = "desconocida"
    return jsonify(
        {
            "ok": True,
            "app": "VideoFlow Local",
            "version": APP_VERSION,
            "ffmpeg": bool(find_tool("ffmpeg")),
            "ffprobe": bool(find_tool("ffprobe")),
            "deno": bool(find_tool("deno")),
            "yt_dlp": ytdlp_version,
            "platform": os.name,
        }
    )


def format_size(item: dict[str, Any]) -> int:
    return int(item.get("filesize") or item.get("filesize_approx") or 0)


def estimate_video_options(info: dict[str, Any], source: str = "YouTube") -> list[dict[str, Any]]:
    formats = info.get("formats") or []
    targets = [144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]
    video_formats = [
        f
        for f in formats
        if f.get("vcodec") not in {None, "none"} and int(f.get("height") or 0) > 0
    ]
    audio_formats = [
        f
        for f in formats
        if f.get("acodec") not in {None, "none"} and f.get("vcodec") == "none"
    ]
    max_height = max((int(f.get("height") or 0) for f in video_formats), default=0)
    best_audio_size = max((format_size(f) for f in audio_formats), default=0)
    options: list[dict[str, Any]] = []
    seen_actual: set[int] = set()

    if source == "TikTok":
        for height in sorted({int(f.get("height") or 0) for f in video_formats}):
            selected = max(
                (f for f in video_formats if int(f.get("height") or 0) == height),
                key=lambda f: (float(f.get("tbr") or 0), format_size(f)),
            )
            size = format_size(selected)
            if selected.get("acodec") in {None, "none"}:
                size += best_audio_size
            width = int(selected.get("width") or 0)
            options.append({
                "value": str(height),
                "label": f"{width} × {height}" if width else f"{height}p",
                "estimated_size": size,
                "estimated_size_human": human_bytes(size),
                "actual_height": height,
            })
        return options or [{
            "value": "0", "label": "Mejor disponible", "estimated_size": 0,
            "estimated_size_human": "—", "actual_height": 0,
        }]

    for target in targets:
        if target > max_height:
            continue
        candidates = [f for f in video_formats if int(f.get("height") or 0) <= target]
        if not candidates:
            continue
        selected = max(
            candidates,
            key=lambda f: (
                int(f.get("height") or 0),
                float(f.get("tbr") or 0),
                format_size(f),
            ),
        )
        actual = int(selected.get("height") or target)
        if actual in seen_actual and target != actual:
            continue
        seen_actual.add(actual)
        size = format_size(selected)
        if selected.get("acodec") in {None, "none"}:
            size += best_audio_size
        options.append(
            {
                "value": str(target),
                "label": ("8K (4320p)" if target == 4320 else "2K (1440p)" if target == 1440 else "4K (2160p)" if target == 2160 else f"{target}p") + (f" · {selected.get('fps'):g} fps" if selected.get('fps') else '') + (f" · {selected['dynamic_range']}" if selected.get('dynamic_range') not in (None, 'SDR') else ''),
                "estimated_size": size,
                "estimated_size_human": human_bytes(size),
                "actual_height": actual,
            }
        )
    if not options:
        options.append(
            {
                "value": "360",
                "label": "360p",
                "estimated_size": 0,
                "estimated_size_human": "—",
                "actual_height": 0,
            }
        )
    return options


@app.post("/api/analyze")
def api_analyze():
    payload = request.get_json(silent=True) or {}
    url = str(payload.get("url") or "").strip()
    source = source_for_url(url)
    if not source:
        return jsonify({"ok": False, "error": "Pega una URL válida de YouTube, Facebook o TikTok."}), 400

    try:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": 25,
            **ydl_environment(source, str(payload.get("browser") or "")),
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("No se pudo leer la información del video.")
        if info.get("entries"):
            info = next((entry for entry in info["entries"] if entry), None)
            if not info:
                raise RuntimeError("No se encontró un video válido en el enlace.")

        duration = int(info.get("duration") or 0)
        audio_options = []
        for bitrate in (128, 192, 320):
            estimated = int(duration * bitrate * 1000 / 8 * 1.03) if duration else 0
            audio_options.append(
                {
                    "value": str(bitrate),
                    "label": f"{bitrate} kbps",
                    "estimated_size": estimated,
                    "estimated_size_human": human_bytes(estimated),
                }
            )

        result = {
            "id": str(info.get("id") or "video"),
            "url": str(info.get("webpage_url") or url),
            "original_url": url,
            "title": str(info.get("title") or f"Video de {source}"),
            "thumbnail": str(info.get("thumbnail") or ""),
            "duration": duration,
            "duration_human": human_duration(duration),
            "uploader": str(info.get("uploader") or info.get("channel") or source),
            "source": source,
            "view_count": int(info.get("view_count") or 0),
            "video_options": estimate_video_options(info, source),
            "audio_options": audio_options,
            "source_audio_size": max((format_size(f) for f in (info.get("formats") or []) if f.get("acodec") not in {None, "none"} and f.get("vcodec") == "none"), default=0),
        }
        return jsonify({"ok": True, "video": result})
    except Exception as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"No se pudo analizar el video: {describe_error(exc, source)[:500]}",
                }
            ),
            422,
        )


@app.post("/api/downloads")
def api_add_download():
    payload = request.get_json(silent=True) or {}
    required = ("url", "format", "quality", "folder")
    if any(not payload.get(key) for key in required):
        return jsonify({"ok": False, "error": "Faltan datos de la descarga."}), 400
    source = source_for_url(str(payload["url"]))
    if not source:
        return jsonify({"ok": False, "error": "URL de YouTube, Facebook o TikTok no válida."}), 400
    original_url = str(payload.get("original_url") or payload["url"]).strip()
    if source_for_url(original_url) != source:
        return jsonify({"ok": False, "error": "El enlace original debe pertenecer a la misma plataforma."}), 400
    payload["original_url"] = original_url
    mode = str(payload.get("mode") or ("audio" if payload["format"] in {"mp3", "m4a", "wav", "flac"} else "video_audio"))
    payload["mode"] = mode
    allowed_formats = {
        "video_audio": {"mp4", "mkv", "webm", "vob", "mov", "avi"},
        "video_only": {"mp4", "mkv", "webm", "mov", "avi"},
        "audio": {"mp3", "m4a", "wav", "flac"},
    }
    if mode not in allowed_formats or payload["format"] not in allowed_formats[mode]:
        return jsonify({"ok": False, "error": "Formato no válido."}), 400
    try:
        quality = int(payload["quality"])
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Calidad no válida."}), 400
    if mode == "audio" and quality not in ({128, 192, 320} if payload["format"] == "mp3" else {0}):
        return jsonify({"ok": False, "error": "Calidad de audio no válida."}), 400
    valid_video_quality = (
        quality == 0 or 144 <= quality <= 4320
        if source == "TikTok" else quality in {0, 144, 240, 360, 480, 720, 1080, 1440, 2160, 4320}
    )
    if mode != "audio" and not valid_video_quality:
        return jsonify({"ok": False, "error": "Calidad de video no válida."}), 400

    try:
        payload['advanced'] = validate_options(payload)
        folder = Path(str(payload["folder"])).expanduser().resolve()
        folder.mkdir(parents=True, exist_ok=True)
        payload["folder"] = str(folder)
        if payload.get("save_path"):
            raw_target = Path(str(payload["save_path"])).expanduser()
            if not raw_target.is_absolute():
                raise ValueError("La ruta de Guardar como debe ser absoluta.")
            target = raw_target.resolve()
            if target.parent != folder:
                raise ValueError("La ruta de Guardar como no coincide con la carpeta de destino.")
            if target.suffix.lower() != f".{payload['format']}":
                raise ValueError("La extensión del archivo debe coincidir con el formato elegido.")
            if target.exists() and payload.get("overwrite") is not True:
                raise FileExistsError("Ese archivo ya existe. Elígelo otra vez con Guardar como para confirmar el reemplazo.")
            payload["save_path"] = str(target)
        settings_store.remember_folder(source, str(folder))
        task = download_manager.add(payload)
        return jsonify({"ok": True, "download": task.as_dict()}), 201
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/downloads")
def api_downloads():
    return jsonify({"ok": True, "downloads": download_manager.list()})


@app.post("/api/downloads/<task_id>/<action>")
def api_download_action(task_id: str, action: str):
    try:
        if action == "pause":
            task = download_manager.pause(task_id)
        elif action == "resume":
            task = download_manager.resume(task_id)
        elif action == "cancel":
            task = download_manager.cancel(task_id)
        else:
            return jsonify({"ok": False, "error": "Acción no válida."}), 404
        return jsonify({"ok": True, "download": task.as_dict()})
    except KeyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.delete("/api/downloads/<task_id>")
def api_delete_download(task_id: str):
    try:
        download_manager.delete(task_id)
        return jsonify({"ok": True})
    except KeyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 409


@app.get("/api/history")
def api_history():
    return jsonify({"ok": True, "history": history_store.list()})


@app.delete("/api/history")
def api_clear_history():
    history_store.clear()
    return jsonify({"ok": True})


@app.get("/api/settings")
def api_get_settings():
    return jsonify({"ok": True, "settings": settings_store.load()})


@app.put("/api/settings")
def api_update_settings():
    payload = request.get_json(silent=True) or {}
    allowed: dict[str, Any] = {}
    if 'language' in payload:
        if not isinstance(payload['language'], str) or payload['language'] not in LANGUAGES:
            return jsonify(ok=False, error='Selecciona un idioma disponible.'), 400
        allowed['language'] = payload['language']
    if 'video_conversion_folder' in payload:
        folder = Path(str(payload['video_conversion_folder'])).expanduser().resolve()
        if not folder.is_dir():
            return jsonify(ok=False, error='Selecciona una carpeta existente para el video.'), 400
        allowed['video_conversion_folder'] = str(folder)
    if 'separation_folder' in payload:
        folder = Path(str(payload['separation_folder'])).expanduser().resolve()
        if not folder.is_dir():
            return jsonify(ok=False, error='Selecciona una carpeta existente para las pistas.'), 400
        allowed['separation_folder'] = str(folder)
    if "conversion_folder" in payload:
        folder = Path(str(payload["conversion_folder"])).expanduser().resolve()
        if not folder.is_dir():
            return jsonify(ok=False, error="Selecciona una carpeta existente para el audio."), 400
        allowed["conversion_folder"] = str(folder)
    if "default_folder" in payload:
        folder = Path(str(payload["default_folder"])).expanduser().resolve()
        folder.mkdir(parents=True, exist_ok=True)
        allowed["default_folder"] = str(folder)
    if "platform_folders" in payload:
        if not isinstance(payload["platform_folders"], dict):
            return jsonify({"ok": False, "error": "Los destinos por plataforma no son válidos."}), 400
        folders = {}
        for source_key in PLATFORMS:
            if source_key in payload["platform_folders"]:
                raw_folder = payload["platform_folders"][source_key]
                if not isinstance(raw_folder, str) or not raw_folder.strip():
                    return jsonify({"ok": False, "error": "El destino no puede estar vacío."}), 400
                folder = Path(raw_folder).expanduser().resolve()
                folder.mkdir(parents=True, exist_ok=True)
                folders[source_key] = str(folder)
        allowed["platform_folders"] = folders
    if payload.get("default_format") in {"mp4", "mkv", "webm", "vob", "mov", "avi", "mp3", "m4a", "wav", "flac"}:
        allowed["default_format"] = payload["default_format"]
    if str(payload.get("default_video_quality")) in {
        "0", "144", "240", "360", "480", "720", "1080", "1440", "2160", "4320"
    }:
        allowed["default_video_quality"] = str(payload["default_video_quality"])
    if str(payload.get("default_audio_quality")) in {"128", "192", "320"}:
        allowed["default_audio_quality"] = str(payload["default_audio_quality"])
    if 'theme' in payload:
        if payload['theme'] not in ('light', 'dark', 'system'):
            return jsonify(ok=False, error='Selecciona un modo de apariencia válido.'), 400
        allowed['theme'] = payload['theme']
    if 'appearance' in payload:
        try:
            allowed['appearance'] = normalize_appearance(payload['appearance'], strict=True)
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 400
    if "notifications" in payload:
        allowed["notifications"] = bool(payload["notifications"])
    if "welcome_seen" in payload:
        allowed["welcome_seen"] = bool(payload["welcome_seen"])
    if "max_concurrent" in payload:
        try:
            value = int(payload['max_concurrent'])
            if value < 0:
                raise ValueError()
            allowed['max_concurrent'] = value
        except (TypeError, ValueError, OverflowError):
            return jsonify(ok=False, error='Usa un número entero: 0 inicia todos los trabajos.'), 400
    for key in ('background_mode', 'keep_awake'):
        if key in payload:
            allowed[key] = payload[key] is True

    for key, maximum in (("rate_limit_kbps", 102400), ("retry_count", 20)):
        if key in payload:
            try:
                value = int(payload[key])
                if value < 0 or value > maximum:
                    raise ValueError()
                allowed[key] = value
            except (ValueError, TypeError):
                return jsonify(ok=False, error="Valor de configuración fuera de rango."), 400
    updated = settings_store.update(allowed)
    download_manager.notify_settings_changed()
    if 'language' in allowed:
        from desktop_runtime import runtime
        runtime.refresh_language()
    return jsonify({"ok": True, "settings": updated})


@app.post("/api/select-folder")
def api_select_folder():
    if os.name != "nt":
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "El selector nativo de carpeta está preparado para Windows.",
                }
            ),
            501,
        )
    payload = request.get_json(silent=True) or {}
    initial = str(payload.get("initial") or settings_store.load()["default_folder"])
    try:
        from desktop_dialogs import choose
        selected = choose('FOLDER', initial)
        if not selected:
            return jsonify(ok=True, cancelled=True)
        return jsonify(ok=True, path=str(Path(selected[0]).resolve()))
    except Exception as exc:
        return jsonify(ok=False, error=f"No se pudo abrir el selector: {exc}"), 500


@app.post("/api/save-path")
def api_save_path():
    if os.name != "nt":
        return jsonify({"ok": False, "error": "Guardar como está preparado para Windows."}), 501
    payload = request.get_json(silent=True) or {}
    source_key = str(payload.get("source") or "YouTube").lower()
    if source_key not in PLATFORMS:
        return jsonify({"ok": False, "error": "Plataforma no válida."}), 400
    output_format = str(payload.get("format") or "").lower()
    if output_format not in {"mp4", "mkv", "webm", "vob", "mov", "avi", "mp3", "m4a", "wav", "flac"}:
        return jsonify({"ok": False, "error": "Formato no válido."}), 400
    initial = Path(str(payload.get("initial") or settings_store.folder_for(source_key))).expanduser().resolve()
    if not initial.is_dir():
        initial = Path(settings_store.folder_for(source_key))
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(payload.get("title") or "Video"))
    title = title.strip(" .")[:110].rstrip(" .") or "Video"
    try:
        from desktop_dialogs import save_audio
        target = save_audio(str(initial), f"{title}.{output_format}", output_format)
        if target is None:
            return jsonify(ok=True, cancelled=True)
        settings_store.remember_folder(source_key, str(target.parent))
        return jsonify({
            "ok": True, "path": str(target), "folder": str(target.parent),
            "source": PLATFORMS[source_key],
            "overwrite": target.exists(),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": f"No se pudo elegir el archivo: {exc}"}), 500


@app.post("/api/open-path")
def api_open_path():
    payload = request.get_json(silent=True) or {}
    raw_path = str(payload.get("path") or "")
    if not raw_path:
        return jsonify({"ok": False, "error": "Ruta vacía."}), 400
    try:
        path = Path(raw_path).expanduser().resolve()
        if os.name == "nt":
            if path.is_file():
                from desktop_shell import reveal_file
                reveal_file(path)
            elif path.is_dir():
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                raise FileNotFoundError("La ruta ya no existe.")
        else:
            subprocess.Popen(["xdg-open", str(path if path.is_dir() else path.parent)])
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


from local_audio import register as register_local_audio
register_local_audio(app, settings_store, download_manager, find_tool)
from audio_separation import register as register_separation
register_separation(app, settings_store, download_manager, find_tool)
from video_conversion import register as register_video_conversion
register_video_conversion(app, settings_store, download_manager, find_tool)


from collections_download import register as register_collections
collection_jobs = register_collections(app, download_manager, settings_store, ydl_environment, source_for_url)


from vault import register as register_vault
private_vault = register_vault(app, DATA_DIR)
from media_tools import register as register_media_tools
register_media_tools(app, download_manager, settings_store)
from ffmpeg_updates import register as register_ffmpeg_updates
ffmpeg_updates = register_ffmpeg_updates(app, find_tool)


if __name__ == "__main__":
    import sys

    # Reuse this module rather than creating a second download queue on import.
    sys.modules["app"] = sys.modules[__name__]
    from launcher import main

    main()
