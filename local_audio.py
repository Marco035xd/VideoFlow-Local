"""Local media conversion using the shared work queue."""
import json
import subprocess
import tempfile
import time
import threading
from pathlib import Path


_processes = set()
_process_lock = threading.RLock()
_closing = False


def start_process(command, **options):
    with _process_lock:
        if _closing:
            raise RuntimeError('La aplicación se está cerrando.')
        process = subprocess.Popen(command, **options)
        _processes.add(process)
        return process


def shutdown():
    global _closing
    with _process_lock:
        _closing = True
        processes = list(_processes)
    for process in processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def convert(task, history, find_tool):
    from app import now_iso
    source = Path(task.local_path)
    folder = Path(task.folder)
    target = folder / f'{source.stem[:120]} [{task.id}].{task.output_format}'
    partial = folder / f'.{task.id}.partial.{task.output_format}'
    process = None
    try:
        folder.mkdir(parents=True, exist_ok=True)
        task.status = 'Procesando'
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        process = start_process([find_tool('ffprobe'), '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(source)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=flags)
        probe_output, _ = process.communicate(timeout=30)
        with _process_lock:
            _processes.discard(process)
        if process.returncode:
            raise ValueError('No se pudo leer el archivo de video.')
        if task.cancel_event.is_set():
            task.status = 'Cancelado'
            return
        info = json.loads(probe_output)
        if not any(s.get('codec_type') == 'audio' for s in info.get('streams', [])):
            raise ValueError('Este archivo no contiene una pista de audio.')
        duration = float(info.get('format', {}).get('duration') or 0)
        task.duration = int(duration)
        codecs = {'mp3': 'libmp3lame', 'm4a': 'aac', 'wav': 'pcm_s16le', 'flac': 'flac'}
        command = [find_tool('ffmpeg'), '-nostdin', '-v', 'error', '-n', '-i', str(source), '-map', '0:a:0', '-vn', '-c:a', codecs[task.output_format]]
        if task.output_format in {'mp3', 'm4a'}:
            command += ['-b:a', f'{task.quality}k']
        command += ['-progress', 'pipe:1', str(partial)]
        with tempfile.TemporaryDirectory(prefix='videoflow-progress-') as temp, open(Path(temp) / 'progress', 'w+b') as progress, open(Path(temp) / 'progress', 'rb') as reader, tempfile.TemporaryFile(mode='w+b') as errors:
            process = start_process(command, stdout=progress, stderr=errors, creationflags=flags)
            position = 0
            while process.poll() is None:
                if task.cancel_event.wait(.25):
                    process.terminate()
                    process.wait(timeout=10)
                    task.status = 'Cancelado'
                    return
                reader.seek(position)
                lines = reader.read().decode('utf-8', errors='replace').splitlines()
                position = reader.tell()
                for line in lines:
                    if line.startswith('out_time_us=') and duration:
                        try:
                            task.progress = min(99, float(line.split('=')[1]) / 1000000 / duration * 100)
                        except ValueError:
                            pass
            if task.cancel_event.is_set():
                task.status = 'Cancelado'
                return
            if process.returncode:
                errors.seek(0)
                raise ValueError(errors.read().decode('utf-8', errors='replace')[-800:] or 'No se pudo convertir el archivo.')
        partial.rename(target)
        task.final_path = str(target)
        task.final_size = target.stat().st_size
        task.progress = 100
        task.completed_at = now_iso()
        history.add(task)
        task.status = 'Completado'
    except Exception as exc:
        task.status = 'Cancelado' if task.cancel_event.is_set() else 'Error'
        task.error = str(exc)
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        with _process_lock:
            _processes.discard(process)
        partial.unlink(missing_ok=True)


def register(app, settings, manager, find_tool):
    from flask import request, jsonify

    @app.post('/api/local-files')
    def local_files():
        script = '''Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Title = 'Selecciona videos para convertir a audio'
$d.Filter = 'Videos|*.mp4;*.mkv;*.mov;*.webm;*.avi;*.wmv;*.flv;*.mpeg;*.vob;*.m4v;*.ts|Todos los archivos|*.*'
$d.Multiselect = $true
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
if ($d.ShowDialog() -eq 'OK') { ConvertTo-Json -Compress -InputObject @($d.FileNames) } else { '[]' }
'''
        try:
            result = subprocess.run(['powershell.exe', '-NoProfile', '-STA', '-Command', script], capture_output=True, text=True, encoding='utf-8', timeout=600, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                raise ValueError('No se pudo abrir el selector de archivos.')
            return jsonify(ok=True, paths=json.loads(result.stdout.strip() or '[]'))
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/convert')
    def add_conversion():
        data = request.get_json(silent=True) or {}
        try:
            source = Path(str(data.get('path', ''))).expanduser().resolve()
            if not source.is_file():
                raise ValueError('Selecciona un archivo existente.')
            if data.get('format') not in {'mp3', 'm4a', 'wav', 'flac'}:
                raise ValueError('Formato de audio no válido.')
            quality = str(data.get('quality', '192'))
            if quality not in {'128', '192', '320'}:
                raise ValueError('Calidad no válida.')
            if not find_tool('ffmpeg') or not find_tool('ffprobe'):
                raise ValueError('Faltan las herramientas de conversión. Reinstala VideoFlow.')
            raw_folder = str(data.get('folder') or settings.load().get('conversion_folder') or settings.load()['default_folder'])
            folder = Path(raw_folder).expanduser().resolve()
            folder.mkdir(parents=True, exist_ok=True)
            task = manager.add(dict(url='', local_path=str(source), title=source.stem, format=data['format'], quality=quality, folder=str(folder), mode='audio'))
            settings.update({'conversion_folder': str(folder)})
            return jsonify(ok=True, download=task.as_dict()), 201
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400
