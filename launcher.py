"""Desktop entry point: serve the UI inside a native Windows application window."""
from __future__ import annotations

import argparse
import ctypes
import json
import logging
import os
import sys
import threading
import time
import urllib.request

from app_paths import APP_DIR, DATA_DIR

WINDOW_TITLE = "VideoFlow Local"


def configure_logging() -> None:
    log_dir = DATA_DIR.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if sys.stdout is None:
        sys.stdout = log_file.open("a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        sys.stderr = sys.stdout


def existing_app(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "/api/system", timeout=2) as response:
            return json.load(response).get("app") == WINDOW_TITLE
    except Exception:
        return False


def focus_existing_window() -> None:
    """Restore the first instance when its shortcut is opened a second time."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    user.FindWindowW.restype = ctypes.c_void_p
    user.IsIconic.argtypes = [ctypes.c_void_p]
    user.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    for _ in range(50):
        handle = user.FindWindowW(None, WINDOW_TITLE)
        if handle:
            if user.IsIconic(handle):
                user.ShowWindow(handle, 9)  # SW_RESTORE
            user.SetForegroundWindow(handle)
            return
        time.sleep(0.1)


def run() -> None:
    parser = argparse.ArgumentParser(description=WINDOW_TITLE)
    parser.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8765, help=argparse.SUPPRESS)
    args = parser.parse_args()
    configure_logging()
    url = f"http://127.0.0.1:{args.port}"
    mutex = None
    server = None
    manager = None
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        mutex = kernel.CreateMutexW(None, False, f"Local\\VideoFlowLocal-{args.port}")
        if not mutex:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:
            kernel.CloseHandle(mutex)
            if not args.headless:
                focus_existing_window()
            return
        # Give the app its own taskbar identity instead of grouping it with Python.
        shell = ctypes.WinDLL("shell32")
        shell.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
        shell.SetCurrentProcessExplicitAppUserModelID("VideoFlow.Local.Desktop")
    try:
        if existing_app(url):
            raise RuntimeError("Cierra la versión anterior de VideoFlow antes de abrir la aplicación de escritorio.")

        from waitress import create_server
        from app import app, download_manager

        manager = download_manager
        server = create_server(app, host="127.0.0.1", port=args.port, threads=16)
        if args.headless:
            server.run()
            return

        import webview

        webview.settings["ALLOW_FILE_URLS"] = False
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        profile_dir = DATA_DIR / "webview"
        profile_dir.mkdir(parents=True, exist_ok=True)
        window = webview.create_window(
            WINDOW_TITLE, url, width=1280, height=820, min_size=(960, 640),
            resizable=True, maximized=True, text_select=True, zoomable=True,
            background_color="#101827",
        )

        def on_closing() -> bool:
            if manager.count_unfinished():
                return window.create_confirmation_dialog(
                    "Cerrar VideoFlow",
                    "Hay descargas pendientes o en curso. ¿Quieres detenerlas y cerrar?",
                )
            return True

        window.events.closing += on_closing
        threading.Thread(target=server.run, daemon=True, name="videoflow-server").start()
        webview.start(
            gui="edgechromium", debug=False, private_mode=False,
            storage_path=str(profile_dir), icon=str(APP_DIR / "static" / "app.ico"),
            localization={
                "global.ok": "Aceptar", "global.cancel": "Cancelar",
                "global.quit": "Cerrar", "global.saveFile": "Guardar archivo",
                "windows.fileFilter.allFiles": "Todos los archivos",
            },
        )
    finally:
        if manager is not None:
            with manager.lock:
                for task in manager.tasks.values():
                    task.cancel_event.set()
                    task.pause_event.clear()
        if server is not None:
            server.close()
        if mutex:
            kernel.CloseHandle(mutex)


def main() -> None:
    try:
        run()
    except Exception as exc:
        logging.exception("No se pudo iniciar VideoFlow")
        if "--headless" not in sys.argv and os.name == "nt":
            message = (
                f"No se pudo iniciar VideoFlow.\n\n{exc}\n\n"
                "Si falta Microsoft Edge WebView2, ejecuta de nuevo el instalador de VideoFlow.\n\n"
                f"Registro: {DATA_DIR.parent / 'logs' / 'app.log'}"
            )
            user = ctypes.WinDLL("user32")
            user.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
            user.MessageBoxW(None, message, WINDOW_TITLE, 0x10)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
