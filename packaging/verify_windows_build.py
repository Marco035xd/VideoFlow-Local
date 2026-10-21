"""Exercise the actual frozen executable using isolated data and bundled tools."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=Path("dist/VideoFlowLocal/VideoFlowLocal.exe"))
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()
    executable = args.exe.resolve()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"

    def api(path: str, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(base_url + path, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)

    with tempfile.TemporaryDirectory(prefix="videoflow-exe-") as temporary:
        root = Path(temporary)
        env = os.environ.copy()
        env["VIDEOFLOW_DATA_DIR"] = str(root / "data")
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        env["PATH"] = os.pathsep.join([str(Path(system_root) / "System32"), system_root])
        process = subprocess.Popen([str(executable), "--headless", "--port", str(port)], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"El ejecutable se cerró con código {process.returncode}. Registro: {(root / 'logs/app.log').read_text(encoding='utf-8') if (root / 'logs/app.log').exists() else 'no creado'}")
                try:
                    health = api("/api/system")
                    break
                except OSError:
                    time.sleep(.25)
            else:
                raise RuntimeError("El ejecutable no inició su servidor local.")
            assert health["app"] == "VideoFlow Local" and all(health[key] for key in ("ffmpeg", "ffprobe", "deno")), health
            for path in ("/", "/static/app.js", "/static/icons/youtube.png"):
                with urllib.request.urlopen(base_url + path) as response:
                    assert response.status == 200 and response.read()
            tools = executable.parent / "_internal/bin"
            for name in ("ffmpeg", "ffprobe", "deno"):
                result = subprocess.run([str(tools / f"{name}.exe"), "--version" if name == "deno" else "-version"],
                                        capture_output=True, text=True, check=True,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                print(result.stdout.splitlines()[0])
            print("EXE inicia sin Python ni herramientas externas en PATH; recursos y dependencias disponibles.")
            if args.smoke_only:
                return
            urls = {
                "YouTube": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "Facebook": "https://www.facebook.com/cnn/videos/10155529876156509/",
                "TikTok": "https://www.tiktok.com/@pokemonlife22/video/7059698374567611694",
            }
            videos = {}
            for source, url in urls.items():
                videos[source] = api("/api/analyze", {"url": url})["video"]
                assert videos[source]["source"] == source
                print("Análisis desde EXE:", source)
            for source, mode, output_format, quality in (("YouTube", "video_audio", "mp4", "144"), ("TikTok", "audio", "mp3", "128")):
                video = videos[source]
                target = root / f"Elegido-{source}.{output_format}"
                queued = api("/api/downloads", {
                    "url": video["url"], "original_url": video["original_url"],
                    "video_id": video["id"], "title": video["title"], "duration": video["duration"],
                    "mode": mode, "format": output_format, "quality": quality,
                    "folder": str(root), "save_path": str(target),
                })["download"]
                deadline = time.monotonic() + 100
                while time.monotonic() < deadline:
                    task = next(item for item in api("/api/downloads")["downloads"] if item["id"] == queued["id"])
                    if task["status"] in {"Completado", "Error", "Cancelado"}:
                        break
                    time.sleep(.3)
                assert task["status"] == "Completado", task
                assert target.is_file() and target.stat().st_size > 0
                probe = subprocess.run([str(tools / "ffprobe.exe"), "-v", "quiet", "-show_streams", "-of", "json", str(target)],
                                       capture_output=True, text=True, check=True,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                streams = [entry["codec_type"] for entry in json.loads(probe.stdout)["streams"]]
                assert "audio" in streams and ("video" in streams) == (mode != "audio"), streams
                print("Descarga desde EXE:", source, output_format, streams)
            history = api("/api/history")["history"]
            assert len(history) == 2 and all(item["url"] for item in history)
            print("Historial y nombres elegidos verificados.")
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
