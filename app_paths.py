"""Resource and writable-data locations for source and installed builds."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_VERSION = "1.4.1"
APP_DIR = Path(__file__).resolve().parent
IS_FROZEN = bool(getattr(sys, "frozen", False))

if os.environ.get("VIDEOFLOW_DATA_DIR"):
    DATA_DIR = Path(os.environ["VIDEOFLOW_DATA_DIR"]).expanduser().resolve()
elif IS_FROZEN:
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "VideoFlowLocal" / "data"
else:
    DATA_DIR = APP_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
