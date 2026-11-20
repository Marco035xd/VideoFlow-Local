"""Size-budgeted video compression using the shared queue and process registry."""
import json
import math
import os
import re
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from audio_separation import command
from desktop_dialogs import choose, save_audio, VIDEO_TYPES
from local_audio import start_process, _processes, _process_lock

REDUCTIONS = {'30', '50', '70'}
HEIGHTS = {0, 1080, 720, 480}


def encode(task, args, work, duration, offset, span):
    process = None
    try:
        if task.cancel_event.is_set():
            raise InterruptedError('Cancelado')
        with (work / 'encode-progress.log').open('w+b') as progress, \
                (work / 'encode-progress.log').open('rb') as reader, \
                (work / 'encode-errors.log').open('w+b') as errors:
            process = start_process(args, stdout=progress, stderr=errors,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            pending = ''
            while True:
                if task.cancel_event.wait(.2):
                    raise InterruptedError('Cancelado')
                finished = process.poll() is not None
                pending += reader.read().decode('utf-8', errors='replace')
                lines = pending.split('\n')
                pending = lines.pop()
                for line in lines:
                    if line.startswith('out_time_us='):
                        try:
                            value = int(line.split('=', 1)[1]) / 1_000_000 / duration
                            task.progress = max(task.progress, offset + min(1, max(0, value)) * span)
                        except ValueError:
                            pass
                if finished:
                    break
            if process.returncode:
                errors.seek(0)
                raise ValueError(errors.read().decode('utf-8', errors='replace')[-800:]
                                 or 'FFmpeg no pudo comprimir este video.')
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


def compress(task, history, find_tool):
    from app import now_iso, human_bytes
    source, folder = Path(task.local_path), Path(task.folder)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', source.stem).strip(' .')[:100] or 'Video'
    target = Path(task.save_path) if task.save_path else folder / f'{name} - comprimido [{task.id}].mp4'
    partial = folder / f'.{task.id}.partial.mp4'
    try:
        task.status, task.phase = 'Procesando', 'Leyendo el video para comprimir'
        folder.mkdir(parents=True, exist_ok=True)
        if target.resolve() == source.resolve() or (target.exists() and source.samefile(target)):
            raise ValueError('No se puede reemplazar el video original.')
        original = source.stat()
        with tempfile.TemporaryDirectory(prefix='videoflow-compress-') as temporary:
            work = Path(temporary)
            info = json.loads(command(task, [find_tool('ffprobe'), '-v', 'error', '-show_format',
                                            '-show_streams', '-of', 'json', str(source)], work))
            video = next((stream for stream in info.get('streams', []) if stream.get('codec_type') == 'video'
                          and not stream.get('disposition', {}).get('attached_pic')), None)
            if not video:
                raise ValueError('El archivo no contiene una pista de video válida.')
            duration = float(info.get('format', {}).get('duration') or video.get('duration') or 0)
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError('No se pudo determinar la duración del video para calcular su tamaño.')
            task.duration = max(1, int(duration))
            try:
                fps = Fraction(video.get('avg_frame_rate') or video.get('r_frame_rate') or '30/1')
                if not 0 < fps <= 240:
                    fps = Fraction(30)
            except (ValueError, ZeroDivisionError):
                fps = Fraction(30)
            target_bytes = int(original.st_size * (100 - int(task.quality)) / 100)
            total_bitrate = int(max(0, target_bytes - 8192) * 8 / duration * .96)
            audio = next((stream for stream in info.get('streams', []) if stream.get('codec_type') == 'audio'), None)
            audio_bitrate = min(128000, max(24000, int(total_bitrate * .2))) if audio else 0
            video_bitrate = total_bitrate - audio_bitrate
            if video_bitrate < 24000:
                raise ValueError('El video es demasiado pequeño para este nivel de compresión. Prueba una reducción menor.')
            task.compression.update(original_bytes=original.st_size, target_bytes=target_bytes)
            task.estimated_size = target_bytes
            limit = task.compression.get('max_height', 0)
            height = f'min(ih,{limit})' if limit else 'ih'
            filters = f"scale=w=-2:h='max(2,trunc({height}/2)*2)'"
            hdr = video.get('color_transfer') in {'smpte2084', 'arib-std-b67'}
            if hdr:
                filters = ('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,'
                           'tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,' + filters)
            common = [find_tool('ffmpeg'), '-nostdin', '-hide_banner', '-v', 'error', '-i', str(source),
                      '-map', f"0:{video['index']}", '-map_metadata', '-1', '-map_chapters', '-1',
                      '-fps_mode', 'cfr', '-r', f'{fps.numerator}/{fps.denominator}',
                      '-vf', filters, '-c:v', 'libx264', '-preset', 'medium', '-threads', '4',
                      '-pix_fmt', 'yuv420p', '-b:v', str(video_bitrate),
                      '-passlogfile', str(work / 'pass'), '-progress', 'pipe:1']
            if hdr:
                common += ['-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv']
            task.phase = 'Analizando la compresión · paso 1 de 2'
            encode(task, common + ['-pass', '1', '-an', '-f', 'null', '-y', os.devnull], work, duration, 0, 45)
            task.phase = 'Comprimiendo el video · paso 2 de 2'
            second = common + ['-pass', '2']
            if audio:
                second += ['-map', f"0:{audio['index']}", '-c:a', 'aac', '-b:a', str(audio_bitrate),
                           '-ac', str(min(2, max(1, int(audio.get('channels') or 2)))), '-ar', '48000']
            else:
                second += ['-an']
            second += ['-movflags', '+faststart', '-n', str(partial)]
            encode(task, second, work, duration, 45, 50)
            task.phase = 'Comprobando el video comprimido'
            output = json.loads(command(task, [find_tool('ffprobe'), '-v', 'error', '-show_format',
                                              '-show_streams', '-of', 'json', str(partial)], work))
            streams = output.get('streams', [])
            out_video = next((item for item in streams if item.get('codec_type') == 'video'), {})
            out_audio = next((item for item in streams if item.get('codec_type') == 'audio'), {})
            out_duration = float(output.get('format', {}).get('duration') or 0)
            if (out_video.get('codec_name') != 'h264' or out_video.get('pix_fmt') != 'yuv420p'
                    or (audio and out_audio.get('codec_name') != 'aac') or not math.isfinite(out_duration)
                    or out_duration <= 0 or abs(out_duration - duration) > max(.25, duration * .02)):
                raise ValueError('No se pudo obtener un video comprimido completo y válido.')
        if task.cancel_event.is_set():
            raise InterruptedError('Cancelado')
        current = source.stat()
        if (current.st_size, current.st_mtime_ns) != (original.st_size, original.st_mtime_ns):
            raise ValueError('El video original cambió durante la compresión. Vuelve a seleccionarlo.')
        final_size = partial.stat().st_size
        if final_size <= 0 or final_size >= original.st_size:
            raise ValueError('Este video no se redujo de tamaño. Prueba una reducción mayor o una resolución menor.')
        if target.resolve() == source.resolve() or (target.exists() and source.samefile(target)):
            raise ValueError('No se puede reemplazar el video original.')
        if target.exists() and not task.overwrite:
            raise ValueError('El archivo ya existe. Elige otro nombre con Guardar como.')
        saved = original.st_size - final_size
        reduction = round(saved / original.st_size * 100, 1)
        task.compression.update(saved_bytes=saved, reduction_percent=reduction)
        history.prepare_output(task, partial, target)
        if task.overwrite:
            partial.replace(target)
        else:
            partial.rename(target)
        task.final_path, task.final_size, task.completed_at = str(target), final_size, now_iso()
        task.progress, task.status = 100, 'Completado'
        task.phase = f'Video comprimido · {human_bytes(original.st_size)} → {human_bytes(final_size)} · {reduction:g}% menos'
        history.add(task)
    except Exception as exc:
        task.status = 'Cancelado' if task.cancel_event.is_set() else 'Error'
        task.error = '' if task.status == 'Cancelado' else str(exc)
    finally:
        partial.unlink(missing_ok=True)


def register(app, settings, manager, find_tool):
    from flask import request, jsonify

    @app.post('/api/compression-files')
    def select_files():
        try:
            paths = list(dict.fromkeys(choose('OPEN', settings.load().get('compression_input_folder', ''),
                                             file_types=VIDEO_TYPES, allow_multiple=True)))
            files = [dict(path=str(Path(path).resolve()), size=Path(path).stat().st_size) for path in paths]
            if paths:
                settings.update({'compression_input_folder': str(Path(paths[0]).parent)})
            return jsonify(ok=True, files=files, cancelled=not files)
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/compression-save-path')
    def select_target():
        data = request.get_json(silent=True) or {}
        try:
            source = Path(str(data.get('path', ''))).expanduser().resolve()
            if not source.is_file():
                raise ValueError('Selecciona un video para comprimir.')
            folder = data.get('initial') or settings.load()['compression_folder']
            target = save_audio(folder, f'{source.stem[:100]} - comprimido.mp4', 'mp4')
            if target is None:
                return jsonify(ok=True, cancelled=True)
            if target == source or (target.exists() and source.samefile(target)):
                raise ValueError('No se puede reemplazar el video original.')
            return jsonify(ok=True, path=str(target), folder=str(target.parent), overwrite=target.exists())
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400

    @app.post('/api/video-compress')
    def add_compression():
        data = request.get_json(silent=True) or {}
        try:
            source = Path(str(data.get('path', ''))).expanduser().resolve()
            reduction, height = str(data.get('reduction', '50')), data.get('max_height', 0)
            if not source.is_file() or reduction not in REDUCTIONS or type(height) is not int or height not in HEIGHTS:
                raise ValueError('Selecciona un video, una reducción y una resolución válidos.')
            if not find_tool('ffmpeg') or not find_tool('ffprobe'):
                raise ValueError('Faltan FFmpeg o FFprobe. Reinstala VideoFlow.')
            size = source.stat().st_size
            if size <= 0:
                raise ValueError('El archivo seleccionado está vacío.')
            folder = Path(data.get('folder') or settings.load()['compression_folder']).expanduser().resolve()
            target = None
            if data.get('save_path'):
                target = Path(str(data['save_path'])).expanduser().resolve()
                if target.suffix.lower() != '.mp4' or not target.parent.is_dir() or target == source or (target.exists() and source.samefile(target)):
                    raise ValueError('Elige un destino válido con Guardar como.')
                if target.exists() and data.get('overwrite') is not True:
                    raise ValueError('Confirma el reemplazo del archivo desde Guardar como.')
                folder = target.parent
            folder.mkdir(parents=True, exist_ok=True)
            if target is None:
                settings.update({'compression_folder': str(folder)})
            with manager.lock:
                if target and any(existing.local_path and (target == Path(existing.local_path).resolve()
                    or (target.exists() and Path(existing.local_path).is_file() and target.samefile(existing.local_path)))
                    for existing in manager.tasks.values()):
                    raise ValueError('El destino coincide con un video de la cola. Elige otro nombre para conservar los originales.')
                task = manager.add(dict(url='', local_path=str(source), title=source.stem, format='mp4', quality=reduction,
                                        folder=str(folder), mode='video_compress', save_path=str(target) if target else '',
                                        overwrite=data.get('overwrite') is True,
                                        estimated_size=int(size * (100 - int(reduction)) / 100),
                                        compression={'max_height': height, 'original_bytes': size}))
            return jsonify(ok=True, download=task.as_dict()), 201
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400
