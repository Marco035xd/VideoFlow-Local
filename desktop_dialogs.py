"""Native dialogs owned by the desktop window, with a browser-mode fallback."""
import json
import subprocess
import threading
from pathlib import Path

_window = None
_lock = threading.Lock()
VIDEO_TYPES = ('Videos (*.mp4;*.mkv;*.mov;*.webm;*.avi;*.wmv;*.flv;*.mpeg;*.vob;*.m4v;*.ts)', 'Todos los archivos (*.*)')
AUDIO_VIDEO_TYPES = ('Audio y video (*.wav;*.mp3;*.m4a;*.aac;*.flac;*.ogg;*.opus;*.wma;*.aiff;*.aif;*.mp4;*.mkv;*.mov;*.webm;*.avi;*.wmv;*.flv;*.mpeg;*.mpg;*.vob;*.m4v;*.ts)',
                     'Audio WAV (*.wav)', 'Todos los archivos (*.*)')


def bind_window(window):
    global _window
    _window = window


def choose(kind, directory='', filename='', file_types=(), allow_multiple=True):
    """Always return a list, including for one selected file and cancellation."""
    if not _lock.acquire(blocking=False):
        raise ValueError('Ya hay un selector abierto. Ciérralo antes de abrir otro.')
    try:
        directory = str(directory) if Path(directory).is_dir() else str(Path.home())
        if _window is not None:
            import webview
            from System import Action
            # Flask requests run on worker threads; Windows dialogs require the UI STA thread.
            selection = {}
            def show():
                try:
                    selection['result'] = _window.create_file_dialog(
                        getattr(webview.FileDialog, kind), directory=directory,
                        allow_multiple=kind == 'OPEN' and allow_multiple, save_filename=filename, file_types=file_types,
                    )
                except Exception as exc:
                    selection['error'] = exc
            _window.native.Invoke(Action(show))
            if 'error' in selection:
                raise selection['error']
            result = selection.get('result')
        else:
            def quoted(value):
                return "'" + str(value).replace("'", "''") + "'"

            from webview.util import parse_file_type
            filters = '|'.join(f'{label} ({pattern})|{pattern}' for label, pattern in map(parse_file_type, file_types))
            dialog = {'OPEN': 'OpenFileDialog', 'SAVE': 'SaveFileDialog', 'FOLDER': 'FolderBrowserDialog'}[kind]
            properties = f'$d.SelectedPath = {quoted(directory)}' if kind == 'FOLDER' else f'$d.InitialDirectory = {quoted(directory)}\n$d.Filter = {quoted(filters)}'
            if kind == 'OPEN':
                properties += '\n$d.Multiselect = ' + ('$true' if allow_multiple else '$false') + '\n$d.Title = "Selecciona un archivo multimedia"'
            if kind == 'SAVE':
                properties += f'\n$d.FileName = {quoted(filename)}\n$d.OverwritePrompt = $true\n$d.AddExtension = $true\n$d.DefaultExt = {quoted(Path(filename).suffix.lstrip("."))}'
            selected = '$d.SelectedPath' if kind == 'FOLDER' else '$d.FileNames' if kind == 'OPEN' else '$d.FileName'
            script = f'''Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$d = New-Object System.Windows.Forms.{dialog}
{properties}
try {{
    if ($d.ShowDialog($owner) -eq 'OK') {{ ConvertTo-Json -Compress -InputObject @({selected}) }} else {{ '[]' }}
}} finally {{ $d.Dispose(); $owner.Dispose() }}
'''
            completed = subprocess.run(
                ['powershell.exe', '-NoProfile', '-STA', '-Command', script],
                capture_output=True, text=True, encoding='utf-8', timeout=600,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            if completed.returncode:
                raise RuntimeError('Windows no pudo abrir el selector de archivos.')
            result = json.loads(completed.stdout.strip() or '[]')
        if not result:
            return []
        return [result] if isinstance(result, str) else list(result)
    finally:
        _lock.release()


def save_audio(directory, filename, output_format):
    paths = choose('SAVE', directory, filename, (f'{output_format.upper()} (*.{output_format})',))
    if not paths:
        return None
    target = Path(paths[0]).resolve()
    if target.suffix.lower() != f'.{output_format}' or not target.parent.is_dir():
        raise ValueError('El archivo debe tener la extensión elegida y una carpeta existente.')
    return target
