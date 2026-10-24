# VideoFlow Local

Aplicación de escritorio para Windows. Permite analizar y guardar videos autorizados de YouTube, Facebook y TikTok, con cola, progreso, historial y configuración local, dentro de su propia ventana.

## Instalar como programa de Windows

Descarga y ejecuta **VideoFlow-Local-1.5.0-Setup-x64.exe** desde la sección [Releases del repositorio](https://github.com/Marco035xd/VideoFlow-Local/releases). Es compatible con Windows 10 (versión 1809 o posterior) y Windows 11 de 64 bits.

El instalador incluye Python, FFmpeg, FFprobe y Deno. También instala Microsoft Edge WebView2 si no está disponible; este paso requiere Internet. Crea accesos directos y permite desinstalar VideoFlow desde Configuración de Windows. No requiere instalar Python ni preparar el entorno manualmente.

Abre **VideoFlow Local** desde el menú Inicio o el escritorio. Toda la interfaz aparece en una ventana propia con icono en la barra de tareas y controles para minimizar, maximizar y cerrar. Al volver a abrir el acceso directo, se recupera la ventana existente. Si cierras con descargas pendientes, VideoFlow pide confirmación antes de detenerlas.

La versión instalada guarda el historial y las preferencias en `%LOCALAPPDATA%\VideoFlowLocal\data`, fuera de la carpeta del programa. Las actualizaciones mediante un instalador nuevo conservan esos datos. La versión desde código fuente sigue usando su carpeta `data`.

El instalador inicial no tiene firma digital.

## Inicio desde el código fuente

1. Extrae toda la carpeta del ZIP.
2. Haz doble clic en **INSTALAR.bat**.
3. Cuando termine, cierra la ventana si se acaban de instalar FFmpeg o Deno.
4. Haz doble clic en **INICIAR.bat**.
5. Se abrirá la ventana de escritorio de VideoFlow Local.

## Requisitos para ejecutar desde el código fuente

- Windows 10 (1809 o posterior) u 11 de 64 bits.
- Conexión a Internet.
- Python 3.11 o superior.
- FFmpeg y FFprobe para unir y convertir archivos.
- Deno, recomendado por yt-dlp para la compatibilidad completa con YouTube.
- Microsoft Edge WebView2 Runtime para la ventana de escritorio.

`INSTALAR.bat` intenta preparar todo con WinGet. Si tu equipo no tiene WinGet, instala manualmente Python, FFmpeg, Deno y [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/), y asegúrate de que las herramientas estén disponibles en el `PATH` de Windows. El instalador `.exe` prepara estos componentes.

## Funciones incluidas

- Ventana de escritorio con pantalla de bienvenida estilo Windows 11.
- Modo claro y oscuro.
- Análisis de enlaces de YouTube, Facebook y TikTok: miniatura, título, autor, duración y calidades disponibles.
- TikTok muestra las dimensiones reales de cada versión disponible, incluidas las verticales.
- Estimación del peso del archivo antes de descargar.
- Video con audio en MP4, MKV, WEBM o VOB; video sin audio en MP4, MKV o WEBM; audio en MP3, M4A o WAV.
- Uso opcional de la sesión de Chrome, Edge o Firefox para enlaces de Facebook que la requieran.
- Video desde 144p hasta 4K cuando la fuente lo permita.
- Audio MP3 a 128, 192 o 320 kbps.
- Selector nativo de carpetas de Windows.
- Cuadro nativo «Guardar como» para elegir carpeta y nombre del archivo de cada descarga. Windows avisa antes de reemplazar un archivo existente.
- Cola máxima de 10 trabajos.
- Entre 1 y 10 descargas simultáneas, configurable.
- Progreso, velocidad, tiempo restante y progreso general.
- Pausar, reanudar, cancelar y eliminar trabajos.
- Historial local con fecha, formato, calidad, peso y ubicación.
- En cada descarga completada se guarda el enlace que pegaste, con opciones para abrirlo o copiarlo desde el historial. Los enlaces permanecen al cerrar la aplicación. Los registros anteriores a esta función muestran «Enlace no registrado».
- «Volver a descargar» en el historial analiza el enlace guardado y recupera la carpeta, el modo, el formato y la calidad anteriores cuando siguen disponibles. Revisa las opciones y agrega el video a la cola; la nueva descarga recibe un nombre automático.
- YouTube, Facebook y TikTok recuerdan cada uno su propia carpeta de destino, también al cerrar y abrir la aplicación. Puedes cambiarlas por separado en Configuración o con «Guardar como» en cada plataforma.
- Botón para mostrar el archivo descargado en el Explorador.
- Base de datos SQLite y ajustes guardados localmente; la aplicación instalada usa la carpeta de datos del usuario de Windows.
- Detección de FFmpeg, FFprobe y Deno instalados mediante WinGet aunque una ventana antigua de Windows todavía no los muestre en `PATH`.

## Notas importantes

- VOB se convierte a una calidad compatible de hasta 480p. Es una limitación práctica del formato orientado a DVD.
- Algunas publicaciones de Facebook requieren iniciar sesión o no son accesibles para yt-dlp. Selecciona tu navegador en la pestaña Facebook si el enlace lo necesita; no se guardan las cookies en la aplicación.
- Si no usas «Guardar como», se mantiene el nombre automático en la carpeta guardada para esa plataforma. Si cambias de formato después de elegir un nombre, abre «Guardar como» otra vez para confirmar la extensión.
- TikTok puede bloquear determinados videos según la publicación, la región o la conexión. La aplicación muestra el error correspondiente cuando no puede analizarlos.
- El tamaño mostrado antes de descargar es una estimación. Puede variar por el códec y la conversión final.
- La pausa es cooperativa: se aplica en el siguiente bloque recibido o etapa de procesamiento.
- Mantén abierta la ventana de VideoFlow mientras haya descargas activas. Cerrar la aplicación detiene los trabajos pendientes.
- Los cambios de YouTube pueden requerir una versión nueva de yt-dlp. Actualiza la aplicación con un instalador nuevo; si ejecutas desde el código fuente, usa **ACTUALIZAR.bat**.
- Las listas de reproducción se tratan como un solo video para evitar agregar más de diez elementos accidentalmente.

## Uso responsable

Utiliza la aplicación únicamente para videos propios, material de dominio público, contenido con licencia que permita su descarga o material para el que tengas autorización. Debes respetar los derechos de autor y las condiciones del servicio utilizado.

## Estructura

```text
VideoFlow_Localhost/
├── app.py
├── INSTALAR.bat
├── INICIAR.bat
├── ACTUALIZAR.bat
├── requirements.txt
├── templates/
│   └── index.html
├── static/
│   ├── app.css
│   ├── app.js
│   └── logo.svg
└── data/
    ├── settings.json   (se crea automáticamente)
    └── history.db      (se crea automáticamente)
```

## Crear otro instalador

En un equipo Windows de 64 bits, instala las dependencias con `INSTALAR.bat` y [Inno Setup 6](https://jrsoftware.org/isinfo.php). Después ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\CREAR_INSTALADOR.ps1
```

El script usa PyInstaller, prepara los iconos y las herramientas externas, descarga el instalador oficial de WebView2, comprueba su firma de Microsoft y compila el instalador en `release`. El ejecutable sin instalar queda en `dist\VideoFlowLocal\VideoFlowLocal.exe`; necesita el resto de esa carpeta y WebView2 Runtime para funcionar. Los archivos de compilación, instaladores y datos personales no se incluyen en Git.

Para una nueva versión, actualiza `APP_VERSION` en `app_paths.py` y los datos de versión en `packaging/windows-version.txt`. La versión instalada se actualiza con el instalador correspondiente; `ACTUALIZAR.bat` se usa para ejecutar desde el código fuente.

## Solución rápida de errores

**“FFmpeg/FFprobe no están disponibles”**  
La versión instalada incluye ambas herramientas: reinstala la versión más reciente si faltan sus archivos. Si ejecutas desde el código fuente, usa `INSTALAR.bat` y vuelve a iniciar la app. La aplicación también busca las herramientas en WinGet y en la carpeta `bin` del proyecto.

**El enlace no se analiza**  
Instala la versión más reciente de VideoFlow. Si ejecutas desde el código fuente, usa `ACTUALIZAR.bat` y verifica que Deno esté instalado con `deno --version`.

**Facebook muestra “Cannot parse data”**  
Comprueba que el video se abra en tu navegador y prueba la opción «Usar sesión» de ese navegador. Hay enlaces de Facebook que el extractor de yt-dlp no puede leer aunque la sesión esté iniciada.

**No aparece la ventana para elegir carpeta**  
La función usa PowerShell y Windows Forms. Comprueba que PowerShell no esté bloqueado por una política empresarial.

**No se abre la ventana de escritorio**

Ejecuta de nuevo el instalador para preparar WebView2. Si ejecutas desde el código fuente, instala WebView2 Runtime y actualiza las dependencias con `INSTALAR.bat`. El registro de errores de la versión instalada está en `%LOCALAPPDATA%\VideoFlowLocal\logs\app.log`.

**El puerto 8765 ya está ocupado**  
Cierra otra instancia de VideoFlow. Para desarrollo, puedes elegir otro puerto con `python launcher.py --port 8766`.

## Novedades de la versión 1.2.0

- Video a audio: selecciona varios videos locales y convierte a MP3, M4A, WAV o FLAC; el original se conserva. El progreso y la cancelación aparecen en Descargas y los resultados en Historial.
- Pega hasta 10 enlaces por plataforma, uno por línea, y usa «Añadir enlaces a la cola». Elige video con audio, solo video o MP3, calidad y carpeta. Los enlaces repetidos se omiten y los que fallan permanecen para corregirlos.
- Configuración: límite de velocidad por descarga (KB/s, 0 sin límite) y número de reintentos. El límite de trabajos simultáneos también controla las conversiones.
- Búsqueda del historial, exportación CSV, cancelación de pendientes y limpieza de completadas de la cola.
- Iconos de navegación de [Microsoft Fluent System Icons](https://github.com/microsoft/fluentui-system-icons), convertidos a ICO. Licencia MIT incluida en `static/icons/navigation/LICENSE.txt`.

Las pruebas de 1.2.0 comprobaron conversiones reales de un video sintético a los cuatro formatos, las pistas de salida, la conservación del original, el historial, las validaciones de configuración y el rechazo de videos sin audio. La lógica de lotes se comprobó con respuestas simuladas, sin descargar videos externos.


## Novedades de la versión 1.2.1

- Campo de enlaces de altura fija, con desplazamiento interno y sin desbordar el contenedor. Acepta hasta 10 enlaces, uno por línea.
- Rutas de carpetas, búsqueda del historial y campos numéricos con estilos coherentes en los temas claro y oscuro.
- Selectores nativos vinculados a la ventana de escritorio y ejecutados en su hilo de interfaz.
- Conversor: selección de uno o varios videos, opción de quitar cada selección y «Guardar como» por archivo para elegir nombre y ubicación del audio.
- La carpeta habitual del conversor se guarda al elegirla. Los destinos personalizados se muestran junto a cada video y se restablecen al cambiar de formato.
- Se conserva el archivo original y se requiere confirmar en el diálogo de Windows antes de reemplazar un audio existente.


## Voz e instrumentos · versión 1.3.0

La nueva sección permite seleccionar un audio o video local y obtener:

- **Voz y música**: dos archivos, voz e instrumental.
- **4 pistas**: voz, batería, bajo y otros instrumentos.
- **6 pistas (experimental)**: añade guitarra y piano; la precisión depende de la mezcla y estas dos pistas pueden contener restos de otros sonidos.

Selecciona el archivo, el modo, WAV de 24 bits, FLAC o MP3, y una carpeta de destino. VideoFlow recuerda la carpeta del separador de forma independiente. Cada trabajo crea una subcarpeta nueva. Puedes cancelar, seguir el progreso y escuchar las pistas desde la sección; también se registra cada pista en Historial. Los reproductores de esta sesión permanecen disponibles mientras el trabajo siga en la cola.

El motor usa HT-Demucs con ONNX Runtime en CPU. No requiere GPU, Python ni una cuenta adicional en la versión instalada. Recomendamos 8 GB de RAM; la velocidad depende del equipo y la duración. Una sola separación se procesa a la vez para limitar el consumo de memoria. El audio se prepara en estéreo a 44,1 kHz y se procesa por fragmentos, sin subirlo a servicios externos.

La primera separación necesita Internet para descargar el modelo: aproximadamente **166 MB** para los modos de 2/4 pistas, o **136 MB** para 6 pistas. Se valida el SHA-256 antes de cargarlo. Los modelos quedan en la carpeta de datos del usuario (`separation-models`) y se reutilizan sin conexión. Cancelar la primera descarga elimina su archivo parcial; el siguiente intento empieza de nuevo. El instalador incluye el motor y descarga los modelos solo al utilizarlos.

La separación no es perfecta: puede dejar artefactos o filtraciones. «Otros» reúne sonidos que no pertenecen a las pistas reconocidas. Se preservan los niveles relativos entre las pistas aplicando una reducción común de ganancia cuando hace falta evitar saturación.

Fuentes y licencias: [Demucs de Meta](https://github.com/facebookresearch/demucs), [exportación ONNX de StemSplit](https://github.com/StemSplit/demucs-onnx), [modelo de cuatro pistas](https://huggingface.co/StemSplitio/htdemucs-onnx) y [modelo de seis pistas](https://huggingface.co/StemSplitio/htdemucs-6s-onnx). Las revisiones y sumas de integridad están fijadas en `separation_models.py`; las licencias MIT acompañan al instalador.

## Convertir video · versión 1.4.0

La sección **Convertir video** acepta archivos locales y crea MP4, MOV, MKV o WEBM. Para intentar importar un archivo problemático en VEGAS Pro, selecciona **MP4**. Esta opción vuelve a codificar el video como H.264 con color YUV 4:2:0 y fotogramas constantes, y el audio como AAC a 48 kHz; también funciona cuando el archivo de origen ya es MP4. Cambiar únicamente la extensión del archivo no realiza esta conversión.

Puedes elegir calidad, una carpeta independiente para estas conversiones o usar **Guardar como…** para elegir el nombre y ubicación exactos. Se conserva el original, los trabajos aparecen en Descargas y el resultado en Historial. La compatibilidad final depende también de la versión de VEGAS Pro, del archivo original y de la configuración del proyecto. MKV y WEBM sirven para otros usos y pueden no importarse en VEGAS Pro.

### Conversión simultánea · versión 1.4.1

En **Convertir video**, selecciona hasta 10 archivos en una sola ventana. Puedes añadir más a la selección, quitar videos y elegir «Guardar como…» para cada archivo. El formato y la calidad seleccionados se aplican a todo el lote. Los demás archivos se guardan con nombres automáticos en la carpeta de conversión. Las conversiones se ejecutan a la vez hasta el límite de trabajos simultáneos de Configuración; los archivos que no pudieron entrar a la cola permanecen seleccionados para reintentarlos.

## Apariencia · versión 1.5.0

Abre **Apariencia** en la barra lateral o desde Configuración. Los cambios tienen vista previa inmediata, se guardan automáticamente en este equipo y se aplican a las distintas secciones de la app.

- Modo **claro, oscuro o automático** según la preferencia de Windows. El botón de la barra superior recorre los tres modos.
- Seis temas: **VideoFlow, Grafito, Océano, Bosque, Ciruela y Arena**.
- Acento del tema, azul, verde, amarillo, rosa, naranja, morado, blanco o un color personalizado.
- Fuente del sistema, Trebuchet MS, Georgia o Consolas; espaciado cómodo o compacto y reducción de movimiento.
- Personalización avanzada de fondo y texto con selector de color y código hexadecimal. Se requiere contraste suficiente para conservar la legibilidad.
- **Restablecer apariencia** recupera el estilo original sin modificar descargas, destinos ni historial.

Los usuarios que ya tenían un tema claro u oscuro conservan esa preferencia al actualizar. Los colores de los logos de las plataformas se mantienen. Las pruebas de preferencias se ejecutan con `.venv\Scripts\python.exe tests\check_appearance.py` y `node tests\check_appearance.cjs`; usan datos aislados, comprueban persistencia y validación, contraste en 162 combinaciones y guardado de cambios rápidos.
