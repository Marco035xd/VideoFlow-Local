"""Local video transcoding with progress and safe output paths."""
import json
import re
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from audio_separation import command as run_command
from desktop_dialogs import choose, save_audio, VIDEO_TYPES
from local_audio import start_process, _processes, _process_lock

FORMATS = {'mp4', 'mov', 'mkv', 'webm'}
QUALITIES = {'18', '20', '23'}


def transcode(task, history, find_tool):
    from app import now_iso
    source = Path(task.local_path)
    folder = Path(task.folder)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', source.stem).strip(' .')[:110] or 'Video'
    target = Path(task.save_path) if task.save_path else folder / f'{name} - convertido [{task.id}].{task.output_format}'
    partial = folder / f'.{task.id}.partial.{task.output_format}'
    process = None
    try:
        task.status, task.phase = 'Procesando', 'Leyendo el video'
        folder.mkdir(parents=True, exist_ok=True)
        if target.resolve() == source.resolve() or (target.exists() and source.samefile(target)):
            raise ValueError('El archivo de salida debe ser distinto del video original.')
        with tempfile.TemporaryDirectory(prefix='videoflow-video-') as temporary:
            work = Path(temporary)
            info = json.loads(run_command(task, [find_tool('ffprobe'), '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(source)], work))
            videos = [stream for stream in info.get('streams', []) if stream.get('codec_type') == 'video' and stream.get('disposition', {}).get('attached_pic') != 1]
            if not videos:
                raise ValueError('El archivo no contiene una pista de video válida.')
            duration = float(info.get('format', {}).get('duration') or videos[0].get('duration') or 0)
            task.duration = max(0, int(duration))
            rate = videos[0].get('avg_frame_rate') or videos[0].get('r_frame_rate') or '30/1'
            try:
                fps = Fraction(rate)
                if not (10 <= fps <= 120):
                    fps = Fraction(30, 1)
            except (ValueError, ZeroDivisionError):
                fps = Fraction(30, 1)
            fps_text = f'{fps.numerator}/{fps.denominator}'
            video_index = int(videos[0]['index'])
            command = [find_tool('ffmpeg'), '-nostdin', '-hide_banner', '-v', 'error', '-n', '-i', str(source),
                       '-map', f'0:{video_index}', '-map', '0:a:0?', '-map_metadata', '-1', '-map_chapters', '-1',
                       '-fps_mode', 'cfr', '-r', fps_text]
            if task.output_format == 'webm':
                command += ['-c:v', 'libvpx-vp9', '-deadline', 'good', '-cpu-used', '3', '-crf', str(int(task.quality) + 12), '-b:v', '0', '-pix_fmt', 'yuv420p', '-c:a', 'libopus', '-b:a', '160k']
            else:
                command += ['-vf', 'scale=ceil(iw/2)*2:ceil(ih/2)*2,setsar=1', '-c:v', 'libx264', '-preset', 'medium',
                            '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', task.quality,
                            '-c:a', 'aac', '-b:a', '192k', '-ar', '48000']
                if task.output_format in {'mp4', 'mov'}:
                    command += ['-movflags', '+faststart']
            command += ['-progress', 'pipe:1', str(partial)]
            task.phase = f'Convirtiendo a {task.output_format.upper()}'
            with open(work / 'progress.log', 'w+b') as progress, open(work / 'progress.log', 'rb') as reader, open(work / 'error.log', 'w+b') as errors:
                process = start_process(command, stdout=progress, stderr=errors,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                position = 0
                while True:
                    if task.cancel_event.wait(.2):
                        raise InterruptedError('Cancelado')
                    reader.seek(position)
                    for line in reader.read().decode('utf-8', errors='replace').splitlines():
                        if line.startswith(('out_time_us=', 'out_time_ms=')) and duration:
                            try:
                                task.progress = min(98, int(line.split('=', 1)[1]) / 1_000_000 / duration * 98)
                            except ValueError:
                                pass
                    position = reader.tell()
                    if process.poll() is not None:
                        break
                if process.returncode:
                    errors.seek(0)
                    raise ValueError(errors.read().decode('utf-8', errors='replace')[-800:] or 'FFmpeg no pudo convertir este video.')
        if task.cancel_event.is_set():
            raise InterruptedError('Cancelado')
        task.phase = 'Comprobando el video convertido'
        with tempfile.TemporaryDirectory(prefix='videoflow-check-') as temporary:
            output_info = json.loads(run_command(task, [find_tool('ffprobe'), '-v', 'error', '-show_streams', '-of', 'json', str(partial)], Path(temporary)))
        output_video = next((stream for stream in output_info.get('streams', []) if stream.get('codec_type') == 'video'), None)
        expected_video = 'vp9' if task.output_format == 'webm' else 'h264'
        expected_audio = 'opus' if task.output_format == 'webm' else 'aac'
        output_audio = next((stream for stream in output_info.get('streams', []) if stream.get('codec_type') == 'audio'), None)
        if (not output_video or output_video.get('codec_name') != expected_video or output_video.get('pix_fmt') != 'yuv420p'
                or (output_audio and output_audio.get('codec_name') != expected_audio)):
            raise ValueError('El video convertido no tiene el formato esperado.')
        if target.exists() and not task.overwrite:
            raise ValueError('El archivo ya existe. Elige otro nombre con Guardar como.')
        if task.overwrite:
            partial.replace(target)
        else:
            partial.rename(target)
        task.final_path, task.final_size = str(target), target.stat().st_size
        task.completed_at = now_iso()
        task.progress, task.status, task.phase = 100, 'Completado', 'Video guardado'
        history.add(task)
    except Exception as exc:
        task.status = 'Cancelado' if task.cancel_event.is_set() else 'Error'
        task.error = '' if task.status == 'Cancelado' else str(exc)
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
        partial.unlink(missing_ok=True)


def register(app, settings, manager, find_tool):
    from flask import request, jsonify

    @app.post('/api/video-file')
    def select_video():
        try:
            paths = choose('OPEN', settings.load().get('video_conversion_input_folder', ''), file_types=VIDEO_TYPES, allow_multiple=False)
            if paths:
                settings.update({'video_conversion_input_folder': str(Path(paths[0]).parent)})
            return jsonify(ok=True, path=paths[0] if paths else '', cancelled=not paths)
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/video-save-path')
    def save_video_path():
        data = request.get_json(silent=True) or {}
        try:
            source = Path(str(data.get('path', ''))).expanduser().resolve()
            fmt = data.get('format')
            if not source.is_file() or fmt not in FORMATS:
                raise ValueError('Selecciona un video y un formato válidos.')
            folder = data.get('initial') or settings.load().get('video_conversion_folder') or settings.load()['default_folder']
            target = save_audio(folder, f'{source.stem[:100]} - convertido.{fmt}', fmt)
            if target is None:
                return jsonify(ok=True, cancelled=True)
            if target == source or (target.exists() and source.samefile(target)):
                raise ValueError('No se puede reemplazar el video original.')
            settings.update({'video_conversion_folder': str(target.parent)})
            return jsonify(ok=True, path=str(target), folder=str(target.parent), overwrite=target.exists())
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/video-convert')
    def add_video_conversion():
        data = request.get_json(silent=True) or {}
        try:
            source = Path(str(data.get('path', ''))).expanduser().resolve()
            fmt, quality = data.get('format'), str(data.get('quality', '20'))
            if not source.is_file() or fmt not in FORMATS or quality not in QUALITIES:
                raise ValueError('Selecciona un archivo, formato y calidad válidos.')
            if not find_tool('ffmpeg') or not find_tool('ffprobe'):
                raise ValueError('Faltan FFmpeg o FFprobe. Reinstala VideoFlow.')
            folder = Path(data.get('folder') or settings.load().get('video_conversion_folder') or settings.load()['default_folder']).expanduser().resolve()
            target = None
            if data.get('save_path'):
                target = Path(str(data['save_path'])).expanduser().resolve()
                if target.suffix.lower() != f'.{fmt}' or not target.parent.is_dir() or target == source or (target.exists() and source.samefile(target)):
                    raise ValueError('Elige un destino válido con Guardar como.')
                if target.exists() and data.get('overwrite') is not True:
                    raise ValueError('Confirma el reemplazo del archivo desde Guardar como.')
                folder = target.parent
            folder.mkdir(parents=True, exist_ok=True)
            task = manager.add(dict(url='', local_path=str(source), title=source.stem, format=fmt, quality=quality,
                                    folder=str(folder), mode='video_convert', save_path=str(target) if target else '',
                                    overwrite=data.get('overwrite') is True))
            settings.update({'video_conversion_folder': str(folder)})
            return jsonify(ok=True, download=task.as_dict()), 201
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400
