"""Windowed Windows launcher. The existing interface opens in the browser."""
from __future__ import annotations

import argparse
import ctypes
import json
import logging
import os
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

from app_paths import APP_DIR, APP_VERSION, DATA_DIR


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
            return json.load(response).get("app") == "VideoFlow Local"
    except Exception:
        return False


def run() -> None:
    parser = argparse.ArgumentParser(description="VideoFlow Local")
    parser.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8765, help=argparse.SUPPRESS)
    args = parser.parse_args()
    configure_logging()
    url = f"http://127.0.0.1:{args.port}"
    mutex = None
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
                webbrowser.open_new(url)
            return
    try:
        if existing_app(url):
            if not args.headless:
                webbrowser.open_new(url)
            return

        from waitress import create_server
        from app import app, download_manager

        server = create_server(app, host="127.0.0.1", port=args.port, threads=16)
        if args.headless:
            server.run()
            return

        import tkinter as tk
        from tkinter import messagebox, ttk

        root = tk.Tk()
        root.title("VideoFlow Local")
        root.geometry("470x245")
        root.resizable(False, False)
        icon = APP_DIR / "static" / "app.ico"
        if icon.is_file():
            root.iconbitmap(str(icon))
        root.configure(bg="#101827")
        style = ttk.Style(root)
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        tk.Label(root, text="VideoFlow Local", font=("Segoe UI", 22, "bold"),
                 fg="#eef3ff", bg="#101827").pack(pady=(24, 5))
        tk.Label(root, text="YouTube · Facebook · TikTok", font=("Segoe UI", 11),
                 fg="#92b6ff", bg="#101827").pack()
        tk.Label(root, text="La aplicación está lista. Administra tus descargas\nen la ventana del navegador.",
                 font=("Segoe UI", 10), fg="#b9c5d8", bg="#101827", justify="center").pack(pady=13)
        actions = tk.Frame(root, bg="#101827")
        actions.pack()

        def close() -> None:
            active = any(task["status"] not in {"Completado", "Error", "Cancelado"}
                         for task in download_manager.list())
            if active and not messagebox.askyesno("Cerrar VideoFlow", "Hay descargas en curso. ¿Quieres detenerlas y cerrar?"):
                return
            for task in list(download_manager.tasks.values()):
                task.cancel_event.set()
                task.pause_event.clear()
            server.close()
            root.destroy()

        ttk.Button(actions, text="Abrir VideoFlow", command=lambda: webbrowser.open_new(url)).pack(side="left", padx=5)
        ttk.Button(actions, text="Cerrar aplicación", command=close).pack(side="left", padx=5)
        root.protocol("WM_DELETE_WINDOW", close)
        threading.Thread(target=server.run, daemon=True, name="videoflow-server").start()
        root.after(500, lambda: webbrowser.open_new(url))
        root.mainloop()
    finally:
        if mutex:
            kernel.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        logging.exception("No se pudo iniciar VideoFlow")
        if "--headless" not in sys.argv:
            import tkinter as tk
            from tkinter import messagebox
            error_root = tk.Tk()
            error_root.withdraw()
            messagebox.showerror("VideoFlow Local", f"No se pudo iniciar la aplicación.\n\n{exc}\n\nRevisa el registro en:\n{DATA_DIR.parent / 'logs' / 'app.log'}")
            error_root.destroy()
        raise SystemExit(1)
