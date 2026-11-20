"""Local media conversion using the shared work queue."""
import json
import math
import subprocess
import tempfile
import time
import threading
from pathlib import Path


_processes = set()
_process_lock = threading.RLock()
_closing = False
AUDIO_FORMATS = {'mp3', 'm4a', 'wav', 'flac', 'ogg'}


def audio_info(task, path, find_tool):
    from audio_separation import command
    with tempfile.TemporaryDirectory(prefix='videoflow-audio-info-') as temporary:
        return json.loads(command(task, [find_tool('ffprobe'), '-v', 'error', '-show_format',
                                        '-show_streams', '-of', 'json', str(path)], Path(temporary)))


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
    target = Path(task.save_path) if task.save_path else folder / f'{source.stem[:120]} [{task.id}].{task.output_format}'
    partial = folder / f'.{task.id}.partial.{task.output_format}'
    process = None
    try:
        folder.mkdir(parents=True, exist_ok=True)
        task.status = 'Procesando'
        task.phase = 'Leyendo el archivo de audio o video'
        if target.resolve() == source.resolve() or (target.exists() and source.samefile(target)):
            raise ValueError('El destino no puede ser el archivo original.')
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        info = audio_info(task, source, find_tool)
        if task.cancel_event.is_set():
            task.status = 'Cancelado'
            return
        if not any(s.get('codec_type') == 'audio' for s in info.get('streams', [])):
            raise ValueError('Este archivo no contiene una pista de audio.')
        duration = float(info.get('format', {}).get('duration') or 0)
        duration = duration if math.isfinite(duration) and duration > 0 else 0
        task.duration = int(duration)
        codecs = {'mp3': 'libmp3lame', 'm4a': 'aac', 'wav': 'pcm_s16le', 'flac': 'flac', 'ogg': 'libvorbis'}
        command = [find_tool('ffmpeg'), '-nostdin', '-v', 'error', '-n', '-i', str(source), '-map', '0:a:0', '-vn', '-c:a', codecs[task.output_format]]
        if task.output_format in {'mp3', 'm4a', 'ogg'}:
            command += ['-b:a', f'{task.quality}k']
        if task.output_format == 'ogg':
            command += ['-ar', '48000', '-ac', '2', '-f', 'ogg']
        task.phase = 'Convirtiendo a OGG · Vorbis' if task.output_format == 'ogg' else f'Convirtiendo a {task.output_format.upper()}'
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
        if task.output_format == 'ogg':
            task.phase = 'Comprobando el audio OGG · Vorbis'
            output = audio_info(task, partial, find_tool)
            audio = next((stream for stream in output.get('streams', []) if stream.get('codec_type') == 'audio'), {})
            output_duration = float(output.get('format', {}).get('duration') or 0)
            if (audio.get('codec_name') != 'vorbis' or not partial.stat().st_size
                    or not math.isfinite(output_duration) or output_duration <= 0
                    or (duration and abs(output_duration - duration) > max(1, duration * .02))):
                raise ValueError('No se pudo obtener un archivo OGG con audio Vorbis completo y válido.')
        if task.cancel_event.is_set():
            raise InterruptedError('Cancelado')
        if target.resolve() == source.resolve() or (target.exists() and source.samefile(target)):
            raise ValueError('El destino no puede ser el archivo original.')
        if target.exists() and not task.overwrite:
            raise ValueError('El archivo de destino ya existe. Elige otro nombre con Guardar como.')
        history.prepare_output(task, partial, target)
        if task.overwrite:
            partial.replace(target)
        else:
            partial.rename(target)
        task.final_path = str(target)
        task.final_size = target.stat().st_size
        task.progress = 100
        task.completed_at = now_iso()
        task.phase = 'Audio guardado · OGG Vorbis' if task.output_format == 'ogg' else 'Audio guardado'
        history.add(task)
        task.status = 'Completado'
    except Exception as exc:
        task.status = 'Cancelado' if task.cancel_event.is_set() else 'Error'
        task.error = '' if task.status == 'Cancelado' else str(exc)
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        with _process_lock:
            _processes.discard(process)
        partial.unlink(missing_ok=True)


def register(app, settings, manager, find_tool):
    from flask import request, jsonify
    from desktop_dialogs import choose, save_audio, AUDIO_VIDEO_TYPES

    @app.post('/api/local-files')
    def local_files():
        try:
            paths = choose('OPEN', settings.load().get('conversion_input_folder', ''), file_types=AUDIO_VIDEO_TYPES)
            if paths:
                settings.update({'conversion_input_folder': str(Path(paths[0]).parent)})
            return jsonify(ok=True, paths=paths)
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/conversion-save-path')
    def conversion_save_path():
        data = request.get_json(silent=True) or {}
        try:
            source = Path(str(data.get('path', ''))).expanduser().resolve()
            output_format = data.get('format')
            if not source.is_file() or output_format not in AUDIO_FORMATS:
                raise ValueError('Selecciona un archivo y un formato de audio válidos.')
            target = save_audio(data.get('initial') or settings.load().get('conversion_folder') or settings.load()['default_folder'], f'{source.stem[:110]}.{output_format}', output_format)
            if target is None:
                return jsonify(ok=True, cancelled=True)
            if target == source or (target.exists() and source.samefile(target)):
                raise ValueError('El destino no puede ser el archivo original.')
            settings.update({'conversion_folder': str(target.parent)})
            return jsonify(ok=True, path=str(target), folder=str(target.parent), overwrite=target.exists())
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/convert')
    def add_conversion():
        data = request.get_json(silent=True) or {}
        try:
            source = Path(str(data.get('path', ''))).expanduser().resolve()
            if not source.is_file():
                raise ValueError('Selecciona un archivo existente.')
            if data.get('format') not in AUDIO_FORMATS:
                raise ValueError('Formato de audio no válido.')
            quality = str(data.get('quality', '192'))
            if quality not in {'128', '192', '320'}:
                raise ValueError('Calidad no válida.')
            if not find_tool('ffmpeg') or not find_tool('ffprobe'):
                raise ValueError('Faltan las herramientas de conversión. Reinstala VideoFlow.')
            raw_folder = str(data.get('folder') or settings.load().get('conversion_folder') or settings.load()['default_folder'])
            folder = Path(raw_folder).expanduser().resolve()
            target = None
            if data.get('save_path'):
                target = Path(str(data['save_path'])).expanduser().resolve()
                if target.suffix.lower() != '.' + data['format'] or not target.parent.is_dir():
                    raise ValueError('Elige un destino válido con Guardar como.')
                if target == source or (target.exists() and source.samefile(target)):
                    raise ValueError('El destino no puede ser el archivo original.')
                if target.exists() and data.get('overwrite') is not True:
                    raise ValueError('El archivo ya existe. Confirma su reemplazo con Guardar como.')
                folder = target.parent
            folder.mkdir(parents=True, exist_ok=True)
            task = manager.add(dict(url='', local_path=str(source), title=source.stem, format=data['format'], quality=quality, folder=str(folder), mode='audio', save_path=str(target) if target else '', overwrite=data.get('overwrite') is True))
            settings.update({'conversion_folder': str(folder)})
            return jsonify(ok=True, download=task.as_dict()), 201
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400
