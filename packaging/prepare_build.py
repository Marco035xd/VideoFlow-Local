"""Prepare reproducible Windows assets and bundled external tools."""
from __future__ import annotations

import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import find_tool
from app_paths import APP_VERSION


def main() -> None:
    import resvg_py
    from PIL import Image
    import io

    svg = ROOT / "static" / "logo.svg"
    png = resvg_py.svg_to_bytes(svg_path=str(svg), width=256, height=256)
    Image.open(io.BytesIO(png)).save(ROOT / "static" / "app.ico", format="ICO",
                                  sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    vendor = ROOT / "build" / "vendor"
    binary_dir = vendor / "bin"
    license_dir = vendor / "licenses"
    binary_dir.mkdir(parents=True, exist_ok=True)
    license_dir.mkdir(parents=True, exist_ok=True)
    tool_paths = {}
    for name in ("ffmpeg", "ffprobe", "deno"):
        source = find_tool(name)
        if not source:
            raise SystemExit(f"Falta {name}. Ejecuta INSTALAR.bat antes de compilar.")
        shutil.copy2(source, binary_dir / f"{name}.exe")
        tool_paths[name] = source

    ffmpeg_root = Path(tool_paths["ffmpeg"]).parent.parent
    for filename in ("LICENSE", "README.txt"):
        source = ffmpeg_root / filename
        if source.is_file():
            target = license_dir / "ffmpeg" / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name", "package")
        for item in distribution.files or []:
            path = Path(str(item))
            if not any(part.endswith(".dist-info") for part in path.parts):
                continue
            if not ("licenses" in path.parts or path.name.upper().startswith(("LICENSE", "COPYING", "NOTICE"))):
                continue
            source = Path(distribution.locate_file(item))
            if source.is_file():
                relative = Path(*path.parts[1:])
                target = license_dir / "python" / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, license_dir / "PYTHON-LICENSE.txt")
    shutil.copy2(ROOT / "packaging" / "DENO-LICENSE.txt", license_dir / "DENO-LICENSE.txt")
    (vendor / "build-info.json").write_text(json.dumps({
        "version": APP_VERSION,
        "python": sys.version,
        "packages": {name: importlib.metadata.version(name) for name in ("yt-dlp", "yt-dlp-ejs", "Flask", "waitress", "curl-cffi", "pywebview", "pythonnet", "numpy", "onnxruntime", "soundfile")},
    }, indent=2), encoding="utf-8")
    print(f"Recursos preparados para VideoFlow Local {APP_VERSION}")


if __name__ == "__main__":
    main()
