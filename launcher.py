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
            user.ShowWindow(handle, 5)
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
        from app import app, download_manager, settings_store, collection_jobs, private_vault, ffmpeg_updates

        manager = download_manager
        server = create_server(app, host="127.0.0.1", port=args.port, threads=16)
        ffmpeg_updates.start()
        if args.headless:
            server.run()
            return

        # Local playback is explicitly started by the user in the main window.
        # Its handoff to a new WebView must retain that playback intent.
        browser_arguments = os.environ.get('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', '')
        if '--autoplay-policy=' not in browser_arguments:
            os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = (browser_arguments + ' --autoplay-policy=no-user-gesture-required').strip()
        import webview

        webview.settings["ALLOW_FILE_URLS"] = False
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        profile_dir = DATA_DIR / "webview"
        profile_dir.mkdir(parents=True, exist_ok=True)
        window = webview.create_window(
            WINDOW_TITLE, url, width=1280, height=820, min_size=(960, 640),
            resizable=True, maximized=True, text_select=True, zoomable=True,
            background_color="#101827",
        )
        from desktop_dialogs import bind_window
        bind_window(window)
        from media_tools import bind_player_drop
        bind_player_drop(window)

        from desktop_runtime import runtime
        runtime.bind(window, settings_store, manager, collection_jobs)

        def on_closing() -> bool:
            if not runtime.closing():
                return False
            if manager.count_unfinished():
                from localization import translate
                language = settings_store.load()['language']
                confirmed = window.create_confirmation_dialog(
                    translate("Cerrar VideoFlow", language),
                    translate("Hay trabajos pendientes o en curso. Puedes retomarlos al volver a abrir VideoFlow, excepto los de incógnito. ¿Quieres cerrar?", language),
                )
                if not confirmed:
                    runtime.exiting = False
                    return False
            for other_window in list(webview.windows):
                if other_window is not window:
                    other_window.destroy()
            return True

        window.events.closing += on_closing
        threading.Thread(target=server.run, daemon=True, name="videoflow-server").start()
        from localization import native_labels
        webview.start(
            gui="edgechromium", debug=False, private_mode=False,
            storage_path=str(profile_dir), icon=str(APP_DIR / "static" / "app.ico"),
            localization=native_labels(settings_store.load()['language']),
        )
    finally:
        from desktop_runtime import runtime
        runtime.shutdown()
        if manager is not None:
            from app import collection_jobs, private_vault
            private_vault.close()
            manager.shutdown()
            for job in collection_jobs.list():
                collection_jobs.cancel(job['id'], cancel_downloads=False)
        from local_audio import shutdown
        shutdown()
        from audio_separation import wait_for_cleanup
        wait_for_cleanup()
        if server is not None:
            server.close()
        if mutex:
            kernel.CloseHandle(mutex)


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == '--separation-worker':
        from separation_worker import main as separation_main
        raise SystemExit(separation_main())
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
