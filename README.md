# VideoFlow Local

Aplicación local para Windows que funciona en `http://127.0.0.1:8765`. Permite analizar y guardar videos autorizados de YouTube, Facebook y TikTok, con cola, progreso, historial y configuración local.

## Inicio rápido

1. Extrae toda la carpeta del ZIP.
2. Haz doble clic en **INSTALAR.bat**.
3. Cuando termine, cierra la ventana si se acaban de instalar FFmpeg o Deno.
4. Haz doble clic en **INICIAR.bat**.
5. El navegador se abrirá automáticamente en VideoFlow Local.

## Requisitos

- Windows 10 u 11.
- Conexión a Internet.
- Python 3.11 o superior.
- FFmpeg y FFprobe para unir y convertir archivos.
- Deno, recomendado por yt-dlp para la compatibilidad completa con YouTube.

El instalador intenta preparar todo con WinGet. Si tu equipo no tiene WinGet, instala manualmente Python, FFmpeg y Deno, y asegúrate de que estén disponibles en el `PATH` de Windows.

## Funciones incluidas

- Pantalla de bienvenida estilo Windows 11.
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
- Botón para mostrar el archivo descargado en el Explorador.
- Base de datos SQLite y ajustes guardados solo en la carpeta `data`.
- Detección de FFmpeg, FFprobe y Deno instalados mediante WinGet aunque una ventana antigua de Windows todavía no los muestre en `PATH`.

## Notas importantes

- VOB se convierte a una calidad compatible de hasta 480p. Es una limitación práctica del formato orientado a DVD.
- Algunas publicaciones de Facebook requieren iniciar sesión o no son accesibles para yt-dlp. Selecciona tu navegador en la pestaña Facebook si el enlace lo necesita; no se guardan las cookies en la aplicación.
- Si no usas «Guardar como», se mantiene el nombre automático en la carpeta predeterminada. Si cambias de formato después de elegir un nombre, abre «Guardar como» otra vez para confirmar la extensión.
- TikTok puede bloquear determinados videos según la publicación, la región o la conexión. La aplicación muestra el error correspondiente cuando no puede analizarlos.
- El tamaño mostrado antes de descargar es una estimación. Puede variar por el códec y la conversión final.
- La pausa es cooperativa: se aplica en el siguiente bloque recibido o etapa de procesamiento.
- No cierres la ventana negra mientras haya descargas activas.
- Los cambios de YouTube pueden requerir una versión nueva de yt-dlp. Ejecuta **ACTUALIZAR.bat** si deja de analizar enlaces.
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

## Solución rápida de errores

**“FFmpeg/FFprobe no están disponibles”**  
Ejecuta `INSTALAR.bat` y vuelve a iniciar la app. También puedes comprobarlo con `ffmpeg -version` y `ffprobe -version` en CMD. La aplicación busca ambas herramientas en WinGet y en la carpeta `bin` del proyecto.

**El enlace no se analiza**  
Ejecuta `ACTUALIZAR.bat`. Verifica también que Deno esté instalado con `deno --version`.

**Facebook muestra “Cannot parse data”**  
Comprueba que el video se abra en tu navegador y prueba la opción «Usar sesión» de ese navegador. Hay enlaces de Facebook que el extractor de yt-dlp no puede leer aunque la sesión esté iniciada.

**No aparece la ventana para elegir carpeta**  
La función usa PowerShell y Windows Forms. Comprueba que PowerShell no esté bloqueado por una política empresarial.

**El puerto 8765 ya está ocupado**  
Cierra otra instancia de VideoFlow. Si necesitas cambiarlo, edita la constante `PORT` al inicio de `app.py`.
