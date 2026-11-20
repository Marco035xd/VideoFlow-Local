# Componentes incluidos

VideoFlow Local incluye el intérprete de Python y las dependencias de `requirements.txt`.
Sus licencias se distribuyen en la carpeta `_internal/licenses` de la aplicación.

- Python: https://www.python.org/psf/license/
- yt-dlp: Unlicense, https://github.com/yt-dlp/yt-dlp
- yt-dlp-ejs: Unlicense / MIT / ISC, https://github.com/yt-dlp/ejs
- Flask: BSD-3-Clause, https://github.com/pallets/flask
- Waitress: ZPL-2.1, https://github.com/Pylons/waitress
- curl-cffi: MIT, https://github.com/lexiforest/curl_cffi
- pywebview: BSD-3-Clause, https://github.com/r0x0r/pywebview
- Python.NET: MIT, https://github.com/pythonnet/pythonnet
- Microsoft Edge WebView2: componente de Microsoft instalado solo si falta, mediante su instalador oficial firmado.
  Distribución y condiciones: https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution
- Deno: MIT, https://github.com/denoland/deno
- FFmpeg/FFprobe: compilación Gyan con GPLv3; licencia completa incluida en `licenses/ffmpeg`.
  Código fuente de FFmpeg: https://ffmpeg.org/download.html
  Compilaciones, versiones y configuración: https://www.gyan.dev/ffmpeg/builds/
  La versión inicial de VideoFlow usa FFmpeg 9.0.2 (Gyan release full),
  cuyo código corresponde a https://github.com/FFmpeg/FFmpeg/commit/946fcce07b.

Los nombres e iconos de YouTube, Facebook, TikTok, Reddit, Instagram, X y Twitch identifican sus plataformas.

- Microsoft Fluent System Icons: MIT, https://github.com/microsoft/fluentui-system-icons. Licencia incluida en static/icons/navigation/LICENSE.txt.

- NumPy: BSD-3-Clause, https://github.com/numpy/numpy
- ONNX Runtime: MIT, https://github.com/microsoft/onnxruntime
- SoundFile: BSD-3-Clause; libsndfile: LGPL-2.1, https://github.com/bastibe/python-soundfile y https://github.com/libsndfile/libsndfile
- HT-Demucs: MIT, Copyright Meta Platforms, Inc. and affiliates, https://github.com/facebookresearch/demucs
- Exportaciones ONNX y esquema de inferencia de referencia: MIT, Copyright (c) 2026 StemSplit, https://github.com/StemSplit/demucs-onnx
  VideoFlow implementa un adaptador de procesamiento por fragmentos para estas exportaciones. Licencias completas en `licenses/separation`.
  Los pesos se descargan al utilizarlos desde los repositorios públicos StemSplitio/htdemucs-onnx y StemSplitio/htdemucs-6s-onnx, con revisión y SHA-256 fijados. No se incluyen en el instalador.

- cryptography: Apache-2.0 / BSD-3-Clause; OpenSSL y componentes de Rust incluidos según sus licencias, https://github.com/pyca/cryptography
