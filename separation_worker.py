"""Isolated CPU inference. Stream overlap-add audio to disk with bounded buffers.

Model tensor layout and overlap scheme follow StemSplit's MIT ONNX reference;
the streaming adapter keeps memory independent of the song's duration.
"""
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from contextlib import ExitStack
from pathlib import Path

from separation_models import model_for


def report(progress, phase, **extra):
    print(json.dumps(dict(progress=progress, phase=phase, **extra), ensure_ascii=False), flush=True)


def obtain_model(config):
    model = model_for(config['mode'])
    directory = Path(config['models'])
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / model['filename']
    report(5, 'Comprobando el modelo de separación')
    if path.is_file() and path.stat().st_size == model['size']:
        with path.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() == model['sha256']:
                return path, model
    temporary = directory / (model['filename'] + '.partial')
    url = f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/{model['filename']}"
    report(5, 'Descargando el modelo: se necesita Internet solo la primera vez')
    digest = hashlib.sha256()
    received = 0
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'VideoFlow-Local/1.3'})
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > model['size']:
                    raise ValueError('El tamaño del modelo descargado no es válido.')
                output.write(chunk)
                digest.update(chunk)
                report(5 + 15 * received / model['size'], f"Descargando modelo · {received // 1048576} / {model['size'] // 1048576} MB")
        if received != model['size'] or digest.hexdigest() != model['sha256']:
            raise ValueError('La descarga del modelo está incompleta o dañada. Vuelve a intentarlo.')
        temporary.replace(path)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError('No se pudo descargar el modelo. Comprueba tu conexión a Internet y vuelve a intentarlo.') from exc
    finally:
        temporary.unlink(missing_ok=True)
    return path, model


def run(config):
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf

    model_path, model = obtain_model(config)
    report(20, 'Cargando el modelo en memoria')
    options = ort.SessionOptions()
    options.intra_op_num_threads = max(1, min(4, (os.cpu_count() or 2) // 2))
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=['CPUExecutionProvider'])
    names = ['vocals', 'instrumental'] if config['mode'] == 'separate_2' else model['sources']
    segment = 343980  # Fixed model input: 7.8 seconds, stereo, 44.1 kHz.
    overlap = segment // 4
    stride = segment - overlap
    window = np.ones(segment, dtype=np.float32)
    ramp = np.linspace(0, 1, overlap, dtype=np.float32)
    window[:overlap], window[-overlap:] = ramp, ramp[::-1]
    accumulated = np.zeros((len(names), 2, segment), dtype=np.float32)
    weights = np.zeros(segment, dtype=np.float32)
    peak = 1.0
    with ExitStack() as stack:
        source = stack.enter_context(sf.SoundFile(config['input']))
        if source.samplerate != 44100 or source.channels != 2 or not source.frames:
            raise ValueError('No se pudo preparar una pista de audio válida.')
        outputs = [stack.enter_context(sf.SoundFile(str(Path(config['work']) / f'{name}.wav'), 'w', samplerate=44100, channels=2, subtype='FLOAT', format='RF64')) for name in names]
        report(22, 'Separando voz e instrumentos')
        for start in range(0, source.frames, stride):
            source.seek(start)
            chunk = source.read(segment, dtype='float32', always_2d=True).T
            length = chunk.shape[1]
            padded = np.zeros((1, 2, segment), dtype=np.float32)
            padded[0, :, :length] = chunk
            predicted = session.run(['stems'], {'mix': padded})[0][0]
            if not np.isfinite(predicted).all():
                raise ValueError('El modelo produjo audio no válido. Prueba otra grabación.')
            if config['mode'] == 'separate_2':
                voice_index = model['sources'].index('vocals')
                predicted = np.stack((predicted[voice_index], np.sum(np.delete(predicted, voice_index, axis=0), axis=0)))
            accumulated += predicted * window
            weights += window
            count = min(stride, source.frames - start)
            ready = accumulated[:, :, :count] / np.maximum(weights[:count], 1e-8)
            peak = max(peak, float(np.abs(ready).max()))
            for index, output in enumerate(outputs):
                output.write(ready[index].T)
            accumulated[:, :, :overlap] = accumulated[:, :, stride:]
            accumulated[:, :, overlap:] = 0
            weights[:overlap] = weights[stride:]
            weights[overlap:] = 0
            report(22 + 66 * min(start + count, source.frames) / source.frames,
                   f'Separando audio · {min(start + count, source.frames) / 44100:.0f} / {source.frames / 44100:.0f} s')
    report(88, 'Separación terminada. Preparando los archivos', stems=names, gain=0.99 / peak)


def main():
    # The frozen application has no console streams; the parent supplies a log file.
    config = json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8'))
    with open(config['events'], 'w', encoding='utf-8', buffering=1) as events:
        sys.stdout = events
        try:
            run(config)
        except MemoryError:
            report(0, 'Error', error='No hay memoria suficiente. Cierra otros programas e intenta separar de nuevo.')
            return 1
        except Exception as exc:
            report(0, 'Error', error=f'{type(exc).__name__}: {exc}')
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
