"""Separation jobs share the application's queue, cancellation and history."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import replace
from pathlib import Path

from app_paths import APP_DIR, DATA_DIR, IS_FROZEN
from local_audio import start_process, _processes, _process_lock
from separation_models import model_for, STEM_LABELS
from separation_devices import PROVIDERS, available_devices

_separation_lock = threading.Lock()
MODES = {'separate_2', 'separate_4', 'separate_6'}
MODELS_DIR = DATA_DIR / 'separation-models'
MEDIA_TYPES = ('Audio y video (*.mp3;*.wav;*.flac;*.m4a;*.aac;*.ogg;*.opus;*.wma;*.mp4;*.mkv;*.mov;*.webm;*.avi;*.m4v)', 'Todos los archivos (*.*)')


def wait_for_cleanup():
    if _separation_lock.acquire(timeout=10):
        _separation_lock.release()


def command(task, args, work, events=None):
    """Keep every child in the application's shutdown registry; never block on pipes."""
    process = None
    last_event = {}
    with open(work / 'process-output.log', 'w+b') as output, open(work / 'process-error.log', 'w+b') as errors:
        try:
            if task.cancel_event.is_set():
                raise InterruptedError('Cancelado')
            process = start_process(args, stdout=output, stderr=errors,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            position, pending = 0, ''
            while True:
                if task.cancel_event.wait(.2):
                    raise InterruptedError('Cancelado')
                finished = process.poll() is not None
                if events and events.exists():
                    with events.open('r', encoding='utf-8') as stream:
                        stream.seek(position)
                        pending += stream.read()
                        position = stream.tell()
                    lines = pending.split('\n')
                    pending = lines.pop()
                    for line in lines:
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue
                        last_event = event
                        task.phase = str(event.get('phase', ''))
                        task.progress = max(task.progress, min(99, float(event.get('progress', 0))))
                        if event.get('device'):
                            task.separation_device_used = event['device']
                            task.separation_gpu_fallback = bool(event.get('fallback'))
                if finished:
                    break
            if process.returncode:
                errors.seek(0)
                error = last_event.get('error') or errors.read().decode('utf-8', errors='replace')[-700:]
                raise RuntimeError(error or 'El motor se cerró inesperadamente. Comprueba la memoria disponible y vuelve a intentarlo.')
            output.seek(0)
            return last_event if events else output.read().decode('utf-8', errors='replace')
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                with _process_lock:
                    _processes.discard(process)


def separate(task, history, find_tool):
    from app import now_iso
    acquired = False
    try:
        task.status = 'Procesando'
        task.phase = 'Esperando turno del separador'
        while not acquired:
            if task.cancel_event.is_set():
                raise InterruptedError('Cancelado')
            acquired = _separation_lock.acquire(timeout=.25)
        folder = Path(task.folder)
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.videoflow-separacion-', dir=folder) as temporary:
            work = Path(temporary)
            task.phase = 'Leyendo la pista de audio'
            info = json.loads(command(task, [find_tool('ffprobe'), '-v', 'error', '-select_streams', 'a:0', '-show_streams', '-show_format', '-of', 'json', task.local_path], work))
            if not info.get('streams'):
                raise ValueError('El archivo no contiene audio. Selecciona una canción o un video con sonido.')
            duration = float(info.get('format', {}).get('duration') or info['streams'][0].get('duration') or 0)
            task.duration = max(0, int(duration))
            track_count = 2 if task.mode == 'separate_2' else int(task.mode[-1])
            required = max(256 * 1024**2, duration * 44100 * 2 * (4 * (track_count + 1) + 3 * track_count))
            if shutil.disk_usage(folder).free < required:
                raise ValueError('No hay suficiente espacio libre en la carpeta de destino para separar este archivo.')
            task.phase, task.progress = 'Preparando el audio del archivo', 2
            decoded = work / 'entrada.wav'
            command(task, [find_tool('ffmpeg'), '-nostdin', '-v', 'error', '-n', '-i', task.local_path, '-map', '0:a:0', '-vn', '-ar', '44100', '-ac', '2', '-c:a', 'pcm_f32le', '-rf64', 'auto', str(decoded)], work)
            config_path, events = work / 'job.json', work / 'events.jsonl'
            config_path.write_text(json.dumps(dict(input=str(decoded), work=str(work), models=str(MODELS_DIR),
                                                   mode=task.mode, events=str(events), device=task.separation_device)), encoding='utf-8')
            args = [sys.executable, '--separation-worker', str(config_path)] if IS_FROZEN else [sys.executable, str(APP_DIR / 'separation_worker.py'), str(config_path)]
            result = command(task, args, work, events)
            expected = ['vocals', 'instrumental'] if task.mode == 'separate_2' else model_for(task.mode)['sources']
            if result.get('stems') != expected:
                raise ValueError('La separación no produjo todas las pistas esperadas.')
            destination = work / 'resultado'
            destination.mkdir()
            for index, stem in enumerate(expected):
                task.phase = f'Guardando {STEM_LABELS[stem]}'
                task.progress = 88 + 10 * index / len(expected)
                target = destination / f'{STEM_LABELS[stem]}.{task.output_format}'
                codec = {'wav': 'pcm_s24le', 'flac': 'flac', 'mp3': 'libmp3lame'}[task.output_format]
                args = [find_tool('ffmpeg'), '-nostdin', '-v', 'error', '-n', '-i', str(work / f'{stem}.wav'), '-af', f"volume={float(result['gain']):.9f}", '-c:a', codec]
                if task.output_format == 'mp3':
                    args += ['-b:a', f'{task.quality}k']
                command(task, args + [str(target)], work)
            if task.cancel_event.is_set():
                raise InterruptedError('Cancelado')
            title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', Path(task.local_path).stem).strip(' .')[:70] or 'Audio'
            final = folder / f'{title} - pistas [{task.id}]'
            destination.rename(final)
            task.completed_at = now_iso()
            task.outputs = [dict(name=STEM_LABELS[stem], path=str(final / f'{STEM_LABELS[stem]}.{task.output_format}')) for stem in expected]
            task.final_path = str(final)
            task.final_size = sum(Path(item['path']).stat().st_size for item in task.outputs)
            for stem, item in zip(expected, task.outputs):
                history.add(replace(task, id=f'{task.id}-{stem}', title=f'{task.title} · {item["name"]}', final_path=item['path'], final_size=Path(item['path']).stat().st_size))
            task.progress, task.phase, task.status = 100, 'Pistas guardadas', 'Completado'
    except Exception as exc:
        task.status = 'Cancelado' if task.cancel_event.is_set() else 'Error'
        task.error = '' if task.status == 'Cancelado' else str(exc)
        task.phase = 'Separación cancelada' if task.status == 'Cancelado' else 'No se pudo completar la separación'
    finally:
        if acquired:
            try:
                (MODELS_DIR / (model_for(task.mode)['filename'] + '.partial')).unlink(missing_ok=True)
            finally:
                _separation_lock.release()


def register(app, settings, manager, find_tool):
    from flask import request, jsonify, send_file
    from desktop_dialogs import choose

    @app.get('/api/separation/models')
    def models():
        result = {}
        for mode in MODES:
            model = model_for(mode)
            path = MODELS_DIR / model['filename']
            result[mode] = dict(ready=path.is_file() and path.stat().st_size == model['size'], megabytes=round(model['size'] / 1000000))
        try:
            import onnxruntime as ort
            devices = available_devices(ort)
        except (ImportError, OSError):
            devices = ['cpu']
        return jsonify(ok=True, models=result, devices=devices)

    @app.post('/api/separation/file')
    def select_file():
        try:
            paths = choose('OPEN', settings.load().get('separation_input_folder', ''), file_types=MEDIA_TYPES, allow_multiple=False)
            if paths:
                settings.update({'separation_input_folder': str(Path(paths[0]).parent)})
            return jsonify(ok=True, path=paths[0] if paths else '', cancelled=not paths)
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/separation')
    def add_separation():
        data = request.get_json(silent=True) or {}
        try:
            source = Path(str(data.get('path', ''))).expanduser().resolve()
            if not source.is_file():
                raise ValueError('Selecciona un archivo de audio o video existente.')
            mode, output_format = data.get('mode'), data.get('format')
            if mode not in MODES or output_format not in {'wav', 'flac', 'mp3'}:
                raise ValueError('Selecciona un modo y un formato válidos.')
            device = data.get('device', 'cpu')
            if device not in ('auto', *PROVIDERS):
                raise ValueError('Selecciona un dispositivo de separación válido.')
            quality = str(data.get('quality', '320'))
            if quality not in {'128', '192', '320'}:
                raise ValueError('Calidad de audio no válida.')
            if not find_tool('ffmpeg') or not find_tool('ffprobe'):
                raise ValueError('Faltan FFmpeg o FFprobe. Reinstala VideoFlow.')
            folder = Path(data.get('folder') or settings.load().get('separation_folder') or settings.load()['default_folder']).expanduser().resolve()
            folder.mkdir(parents=True, exist_ok=True)
            task = manager.add(dict(url='', local_path=str(source), title=source.stem, format=output_format,
                                    quality=quality, mode=mode, folder=str(folder), separation_device=device))
            settings.update({'separation_folder': str(folder)})
            return jsonify(ok=True, download=task.as_dict()), 201
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.get('/api/separation/<task_id>/audio/<int:index>')
    def play_audio(task_id, index):
        task = manager.get(task_id)
        if not task or task.mode not in MODES or task.status != 'Completado' or index < 0 or index >= len(task.outputs):
            return jsonify(ok=False, error='Pista no disponible.'), 404
        path = Path(task.outputs[index]['path'])
        if not path.is_file():
            return jsonify(ok=False, error='El archivo ya no está en su carpeta original.'), 404
        return send_file(path, conditional=True)
