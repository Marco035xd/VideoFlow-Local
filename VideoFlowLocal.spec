from pathlib import Path
from importlib.metadata import packages_distributions
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
datas = [(str(root / name), name) for name in ("templates", "static")]
datas += [
    (str(root / "build/vendor/bin"), "bin"),
    (str(root / "build/vendor/licenses"), "licenses"),
    (str(root / "build/vendor/build-info.json"), "."),
    (str(root / "packaging/THIRD_PARTY_NOTICES.md"), "."),
    (str(root / "README.md"), "."),
    (str(root / "packaging/separation-licenses"), "licenses/separation"),
]
binaries = []
hiddenimports = ["webview.platforms.winforms", "webview.platforms.edgechromium", "clr"]
for package in ("yt_dlp", "yt_dlp_ejs", "curl_cffi"):
    package_data, package_binaries, package_imports = collect_all(package)
    datas += package_data
    binaries += package_binaries
    hiddenimports += package_imports

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata
binaries += collect_dynamic_libs('onnxruntime')
datas += collect_data_files('onnxruntime', includes=['LICENSE', 'ThirdPartyNotices.txt'])
for runtime in packages_distributions().get('onnxruntime', ()):
    datas += copy_metadata(runtime)

a = Analysis([str(root / "launcher.py")], pathex=[str(root)], binaries=binaries,
             datas=datas, hiddenimports=hiddenimports, hookspath=[],
             excludes=["pytest", "resvg_py", "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
                       "webview.platforms.android", "webview.platforms.cocoa", "webview.platforms.gtk",
                       "webview.platforms.qt", "webview.platforms.cef"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="VideoFlowLocal",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(root / "static/app.ico"),
          version=str(root / "packaging/windows-version.txt"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="VideoFlowLocal")
