# VideoFlow Local

Aplicación de escritorio para Windows. Permite analizar y guardar videos autorizados de YouTube, Facebook y TikTok, con cola, progreso, historial y configuración local, dentro de su propia ventana.

## Instalar como programa de Windows

Descarga y ejecuta **VideoFlow-Local-1.1.0-Setup-x64.exe** desde la sección [Releases del repositorio](https://github.com/Marco035xd/VideoFlow-Local/releases). Es compatible con Windows 10 (versión 1809 o posterior) y Windows 11 de 64 bits.

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
