# VideoFlow Local

Aplicación de escritorio para Windows. Permite analizar y guardar videos autorizados de YouTube, Facebook y TikTok, con cola, progreso, historial y configuración local, dentro de su propia ventana.

## Instalar como programa de Windows

Descarga y ejecuta **VideoFlow-Local-1.6.5-Setup-x64.exe** desde la sección [Releases del repositorio](https://github.com/Marco035xd/VideoFlow-Local/releases). Es compatible con Windows 10 (versión 1809 o posterior) y Windows 11 de 64 bits.

### Mostrar la ubicación de un archivo · versión 1.6.5

El botón para abrir la ubicación selecciona el archivo mediante la API nativa de Windows `SHOpenFolderAndSelectItems`, en lugar de ejecutar `explorer.exe` con argumentos. Las carpetas se siguen abriendo con la acción de apertura del sistema. Los errores al abrir una ubicación aparecen en la aplicación. Este cambio no garantiza que un antivirus deje de avisar: la clasificación depende del proveedor del antivirus.

### Picture-in-Picture minimalista · versión 1.6.4

El video ocupa toda la miniventana PiP, sin barra de título ni panel de controles permanente. Al mover el puntero aparecen botones discretos para pausar/reproducir, volver al reproductor principal o cerrar; se ocultan tras un momento de inactividad. Arrastra directamente el video para mover la ventana en tiempo real mientras continúa reproduciéndose. Las flechas y la barra espaciadora siguen controlando la reproducción con el video enfocado.

### Ventana flotante, PiP y FFmpeg · versión 1.6.3

La ventana flotante distribuye toda su altura entre video y controles. Conserva la posición, reproducción/pausa, volumen, velocidad y brillo al abrirse y al volver al reproductor principal. La barra de tiempo del reproductor principal también controla la ventana pequeña; solo una de las ventanas reproduce audio.

En escritorio, **Picture-in-Picture** abre una miniventana propia siempre encima. Arrastra el video para moverla en vivo. Este movimiento usa la región de arrastre de la app y conserva la reproducción. Usa ↗ para volver al reproductor principal o × para cerrar. En el modo navegador se utiliza PiP nativo cuando está disponible.

Cada inicio comprueba la versión estable de FFmpeg en segundo plano mediante la API de versiones de Gyan. Configuración muestra la versión instalada, la última publicada y la hora de comprobación; si hay una nueva, aparece un aviso y un enlace a la página del proveedor. **Comprobar ahora** repite la consulta. La comprobación avisa de las actualizaciones y la descarga se abre al pulsar el enlace. Sin conexión, la app conserva sus funciones locales y permite reintentar la búsqueda.

### Reproductor y secreto retro · versión 1.6.2

El reproductor principal y la ventana flotante tienen controles propios siempre visibles: barra de tiempo arrastrable, volumen, silencio, reproducción, reinicio y pantalla completa con los controles incluidos. Las barras están separadas del área de gestos del video. Se conserva el soporte para abrir o arrastrar archivos y retomar el video al cambiar de sección.

Introduce **↑ ↑ ↓ ↓ ← → ← → B A** fuera de un campo de escritura para descubrir **VideoFlow Arcade**, un juego local de atrapar notas durante 30 segundos. Usa las flechas, A/D o el mouse. Se cierra con Esc o Cerrar; pausa el video mientras juegas y lo reanuda al cerrar si antes estaba reproduciéndose. Las descargas siguen su curso y el juego no cambia tus preferencias.

### Reproductor · versión 1.6.1

Abre un video o audio con **Abrir archivo** o arrástralo sobre el panel del reproductor. Los archivos se leen directamente desde su ubicación, sin copiarlos ni subirlos. Al terminar, **Volver a reproducir** lo inicia desde el principio; **Reiniciar** está disponible en cualquier momento. Al cambiar de sección, se pausa y retoma la misma posición al regresar si estaba reproduciéndose. Si lo pausaste, conserva esa pausa. Los controles de reproducción también están disponibles en la ventana flotante. En el modo navegador, los archivos arrastrados se reproducen localmente, y la ventana flotante de escritorio requiere abrir el archivo desde el selector.

El instalador incluye Python, FFmpeg, FFprobe y Deno. También instala Microsoft Edge WebView2 si no está disponible; este paso requiere Internet. Crea accesos directos y permite desinstalar VideoFlow desde Configuración de Windows. No requiere instalar Python ni preparar el entorno manualmente.

Abre **VideoFlow Local** desde el menú Inicio o el escritorio. Toda la interfaz aparece en una ventana propia con icono en la barra de tareas y controles para minimizar, maximizar y cerrar. Al volver a abrir el acceso directo, se recupera la ventana existente. Por defecto, cerrar la ventana la oculta en la bandeja y los trabajos continúan. Usa el icono junto al reloj para abrirla o salir y detener los trabajos. Puedes desactivar este comportamiento en Configuración.

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
- Video con audio en MP4, MKV, MOV, AVI, WEBM o VOB; video sin audio en MP4, MKV, MOV, AVI o WEBM; audio en MP3, M4A, WAV o FLAC.
- Uso opcional de la sesión de Chrome, Edge o Firefox para enlaces de Facebook que la requieran.
- Video desde 144p hasta 8K cuando la fuente lo permita.
- Audio MP3 a 128, 192 o 320 kbps.
- Selector nativo de carpetas de Windows.
- Cuadro nativo «Guardar como» para elegir carpeta y nombre del archivo de cada descarga. Windows avisa antes de reemplazar un archivo existente.
- Cantidad de trabajos sin límite fijo de la aplicación.
- Concurrencia configurable; 0 inicia todos los trabajos sin límite de la aplicación. La capacidad real depende de CPU, RAM, red y límites del sitio.
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
- Con el modo de segundo plano activo, la ventana puede ocultarse en la bandeja. La pantalla puede apagarse; la suspensión manual, hibernación, apagado o salir por completo detienen los trabajos. Las tareas pendientes no se restauran tras salir.
- Los cambios de YouTube pueden requerir una versión nueva de yt-dlp. Actualiza la aplicación con un instalador nuevo; si ejecutas desde el código fuente, usa **ACTUALIZAR.bat**.
- Usa «Listas y canales» para colecciones completas de YouTube. El análisis de Inicio sigue enfocado en videos individuales.

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
- Pega varios enlaces por plataforma, uno por línea, y usa «Añadir enlaces a la cola». Elige video con audio, solo video o MP3, calidad y carpeta. Los enlaces repetidos se omiten y los que fallan permanecen para corregirlos.
- Configuración: límite de velocidad por descarga (KB/s, 0 sin límite) y número de reintentos. El límite de trabajos simultáneos también controla las conversiones.
- Búsqueda del historial, exportación CSV, cancelación de pendientes y limpieza de completadas de la cola.
- Iconos de navegación de [Microsoft Fluent System Icons](https://github.com/microsoft/fluentui-system-icons), convertidos a ICO. Licencia MIT incluida en `static/icons/navigation/LICENSE.txt`.

Las pruebas de 1.2.0 comprobaron conversiones reales de un video sintético a los cuatro formatos, las pistas de salida, la conservación del original, el historial, las validaciones de configuración y el rechazo de videos sin audio. La lógica de lotes se comprobó con respuestas simuladas, sin descargar videos externos.


## Novedades de la versión 1.2.1

- Campo de enlaces de altura fija, con desplazamiento interno y sin desbordar el contenedor. Acepta múltiples enlaces, uno por línea.
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

En **Convertir video**, selecciona varios archivos en una sola ventana. Puedes añadir más a la selección, quitar videos y elegir «Guardar como…» para cada archivo. El formato y la calidad seleccionados se aplican a todo el lote. Los demás archivos se guardan con nombres automáticos en la carpeta de conversión. Las conversiones se ejecutan a la vez hasta el límite de trabajos simultáneos de Configuración; los archivos que no pudieron entrar a la cola permanecen seleccionados para reintentarlos.

## Apariencia · versión 1.6.0

Abre **Apariencia** en la barra lateral o desde Configuración. Los cambios tienen vista previa inmediata, se guardan automáticamente en este equipo y se aplican a las distintas secciones de la app.

- Modo **claro, oscuro o automático** según la preferencia de Windows. El botón de la barra superior recorre los tres modos.
- Seis temas: **VideoFlow, Grafito, Océano, Bosque, Ciruela y Arena**.
- Acento del tema, azul, verde, amarillo, rosa, naranja, morado, blanco o un color personalizado.
- Fuente del sistema, Trebuchet MS, Georgia o Consolas; espaciado cómodo o compacto y reducción de movimiento.
- Personalización avanzada de fondo y texto con selector de color y código hexadecimal. Se requiere contraste suficiente para conservar la legibilidad.
- **Restablecer apariencia** recupera el estilo original sin modificar descargas, destinos ni historial.

Los usuarios que ya tenían un tema claro u oscuro conservan esa preferencia al actualizar. Los colores de los logos de las plataformas se mantienen. Las pruebas de preferencias se ejecutan con `.venv\Scripts\python.exe tests\check_appearance.py` y `node tests\check_appearance.cjs`; usan datos aislados, comprueban persistencia y validación, contraste en 162 combinaciones y guardado de cambios rápidos.


## Descargas y herramientas de la versión 1.6

- **Listas y canales:** importa de forma progresiva videos, Shorts y emisiones disponibles de canales de YouTube, o listas completas. Una colección puede contener cientos de videos. Duplicados dentro de la colección y entradas no disponibles se omiten; cada descarga tiene su estado. Cancelar la colección cancela también sus trabajos pendientes o activos. No se garantiza acceso a videos privados, borrados o restringidos.
- **Calidad avanzada:** hasta 4320p (8K), filtros de FPS y SDR/HDR. Los filtros estrictos muestran un error si no existen versiones compatibles; no se inventa resolución ni se convierte SDR en HDR. MKV/WebM permiten conservar los códecs HDR originales. MP3 a 320 kbps y FLAC no recuperan información perdida en el audio fuente.
- **Recortes:** inicio y final en segundos, mm:ss o hh:mm:ss. yt-dlp/FFmpeg solicitan el fragmento y recodifican los bordes; el ahorro de transferencia depende del servidor. Los recortes y los subtítulos no se combinan en esta versión para evitar desincronización.
- **Subtítulos:** idioma por código, opción de automáticos, archivo SRT o pista incrustada seleccionable en MP4/MKV/MOV. Se conserva también el SRT. Si el idioma no está disponible, el trabajo informa de ello. No son subtítulos quemados sobre la imagen.
- **AVI local:** conversión a MPEG-4 con MP3 a 320 kbps; MP4/MOV/MKV usan H.264/AAC y WebM usa VP9/Opus.
- **Navegador privado:** ventana WebView2 InPrivate, sin acceso al puente de la aplicación, con bloqueo integrado de dominios publicitarios y detección de respuestas de audio/video/manifiestos. El bloqueo es básico, no una implementación de EasyList. La lista detectada permanece en RAM. El motor puede descargar sitios compatibles con yt-dlp; no se garantiza cualquier sitio, DRM, URLs blob o recursos que requieran cookies privadas (la sesión no se copia al descargador).
- **Incógnito:** evita registrar nuevos trabajos en el historial. Los archivos se guardan en la carpeta elegida y los trabajos se ven mientras la sesión permanece abierta.
- **Carpeta privada:** copias cifradas con AES-256-GCM y clave derivada del PIN con scrypt; nombres e índice también cifrados. Se bloquea después de 5 minutos sin uso y al ocultar la ventana. Conserva los originales. Exportar crea una copia normal y requiere un nombre nuevo. El PIN no es recuperable; esta versión no usa patrones ni Windows Hello. La carpeta oculta por sí sola no es la protección: lo es el cifrado. Un PIN largo reduce el riesgo de adivinación fuera de la aplicación.
- **Segundo plano:** icono de bandeja con Abrir y Salir. Opción para evitar suspensión automática mientras hay trabajo, permitiendo apagar la pantalla. Las preferencias de energía no impiden una suspensión manual.
- **Reproductor:** abre videos/audios locales, ofrece controles, velocidad, brillo visual del video, gestos de volumen/brillo, PiP cuando WebView2 lo permite y una ventana flotante alternativa. La reproducción depende de los códecs soportados por WebView2; AVI y otros formatos pueden requerir convertir a MP4 H.264.
- No se incluyen nube ni transmisión a TV, por decisión del usuario.

Las herramientas nuevas siguen las paletas, fuentes y espaciado de Apariencia. El navegador usa una barra nativa con los colores actuales; las páginas visitadas conservan su propio diseño.

### Comprobación de esta versión

`python tests/check_studio.py` usa datos temporales y comprueba 350 entradas de colección, concurrencia superior a 10, selección 8K/HDR/60 fps, validación de opciones y protección de la API local. Verifica PIN, reapertura del cifrado, rechazo de alteraciones, conversiones reales con FFmpeg, SRT/pista incrustada y descarga de un recorte con un servidor local sin registrar historial. Las pruebas de Apariencia siguen disponibles.
