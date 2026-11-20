# VideoFlow Local

Aplicación de escritorio para Windows. Permite analizar y guardar videos autorizados de YouTube, Facebook, TikTok, Reddit, Instagram, X y clips de Twitch, con cola, galería, historial y configuración local.

## Capturas de pantalla

Conoce la interfaz y sus herramientas en este recorrido de **11 capturas**, tomadas el **25 de octubre de 2026** y ordenadas según las secciones de la aplicación.

![Pantalla de inicio de VideoFlow Local con TikTok seleccionado y entrada de varios enlaces.](docs/capturas/01-inicio-descargas.png)

La pantalla de inicio permite elegir la plataforma, pegar uno o varios enlaces y preparar sus opciones de descarga. En esta captura está seleccionada la pestaña de TikTok.

| Pantalla | Qué muestra |
| --- | --- |
| [01. Inicio](docs/CAPTURAS.md#01-inicio-y-nueva-descarga) | Selección de plataforma, entrada de enlaces y opciones de descarga. |
| [02. Descargas](docs/CAPTURAS.md#02-gestión-de-descargas) | Cola de trabajos, contadores y progreso general. |
| [03. Video a audio](docs/CAPTURAS.md#03-video-a-audio) | Selección de videos locales, formato de audio y carpeta de salida. |
| [04. Voz e instrumentos](docs/CAPTURAS.md#04-voz-e-instrumentos) | Separación local de pistas, con el modo experimental de seis pistas seleccionado. |
| [05. Historial](docs/CAPTURAS.md#05-historial) | Búsqueda, exportación CSV y estado vacío después de limpiar los registros. |
| [06. Listas y canales](docs/CAPTURAS.md#06-listas-y-canales) | Descarga de colecciones de YouTube con formato, calidad y destino. |
| [07. Reproductor](docs/CAPTURAS.md#07-reproductor-local) | Apertura o arrastre de archivos y controles de reproducción. |
| [08. Navegador privado](docs/CAPTURAS.md#08-navegador-privado) | Apertura de direcciones y consulta de recursos multimedia detectados. |
| [09. Carpeta privada](docs/CAPTURAS.md#09-carpeta-privada) | Acceso mediante PIN a las copias cifradas de archivos. |
| [10. Apariencia](docs/CAPTURAS.md#10-apariencia) | Modos de color, seis temas, acentos y vista previa. |
| [11. Configuración](docs/CAPTURAS.md#11-configuración) | Destinos por plataforma, concurrencia y comprobación de FFmpeg. |

**[Ver todas las capturas con sus descripciones →](docs/CAPTURAS.md)**

## Instalar como programa de Windows

Descarga y ejecuta el instalador de Windows desde la sección [Releases del repositorio](https://github.com/Marco035xd/VideoFlow-Local/releases). Es compatible con Windows 10 (versión 1809 o posterior) y Windows 11 de 64 bits.

### Actualizar FFmpeg desde Configuración · versión 1.6.30

En **Configuración → Conexión y recuperación**, pulsa **Actualizar FFmpeg** cuando aparezca una nueva versión. VideoFlow descarga la compilación completa de Gyan, verifica su SHA-256 y comprueba que FFmpeg y FFprobe funcionen y coincidan. Los dos se guardan en los datos de VideoFlow. [Compilaciones de FFmpeg para Windows](https://www.gyan.dev/ffmpeg/builds/)

Cuando la app indique que la actualización está lista, ciérrala por completo y vuelve a abrirla. Si VideoFlow se queda en la bandeja, usa **Salir** en el icono junto al reloj. Las tareas en curso conservan la compilación que estaban usando durante la descarga y la verificación.

### Cola recuperable, búsqueda y diagnóstico · versión 1.6.29

En **Descargas**, los trabajos pendientes o en curso aparecen como **Interrumpido** después de reiniciar VideoFlow. Pulsa **Reanudar** para continuar con su formato, pista y destino. Las descargas compatibles aprovechan sus archivos parciales. Las conversiones locales vuelven a empezar y los trabajos en incógnito duran solo la sesión. Si usaste un archivo de cookies de YouTube, vuelve a seleccionarlo en **Inicio** antes de reanudar.

En **Galería**, puedes buscar por título y combinar la búsqueda con el filtro por plataforma. También puedes ordenar por fecha, título o duración. Si un trabajo falla, abre **Ver diagnóstico** en su tarjeta. Desde ahí puedes copiar un informe con la categoría del error, la plataforma y el formato, sin URLs, títulos, rutas ni datos de sesión.

### Descargas de Reddit e Instagram · versión 1.6.24

Hay dos pestañas nuevas en Inicio. Pega el enlace de una publicación de Reddit, un enlace directo al video de Reddit, una publicación de Instagram o un Reel. Puedes ver las calidades disponibles, elegir el formato y guardar el video o su audio cuando esté disponible. También puedes añadir varios enlaces de una misma plataforma y configurar una carpeta para cada sitio. Si una publicación incluye varios videos, se toma el primero que devuelve la plataforma. Si el sitio pide iniciar sesión, selecciona el navegador en el que puedes abrir la publicación.

### X, clips de Twitch y galería de descargas · versión 1.6.25

En **Inicio**, puedes pegar enlaces de publicaciones de `x.com` o `twitter.com` y de clips de `clips.twitch.tv` o `twitch.tv/canal/clip/…`. Ambas plataformas admiten descargas individuales y por lotes, con su propia carpeta de destino.

Abre **Galería** en la barra lateral o **Ver galería** en Descargas. Cada video guardado muestra su título, una miniatura generada desde el archivo local y el logo de su plataforma. Selecciona la tarjeta para abrirlo en el reproductor integrado. La galería incorpora los videos disponibles del historial anterior y conserva sus registros al limpiar el historial o la cola. Los trabajos en modo incógnito se excluyen.

### Fondos personalizados y ventana flotante · versión 1.6.22

En **Apariencia → Fondos de pantalla**, puedes añadir fotos JPG, PNG o WebP y volver a usar las anteriores desde sus miniaturas. El control **Opacidad del fondo** cambia en vivo la intensidad de la foto entre 25 % y 100 %. Cada foto conserva su ajuste al cambiar de fondo o cerrar la aplicación. **Fondo del tema** recupera el fondo del tema y mantiene la galería.

La ventana flotante y Picture-in-Picture tienen saltos de diez segundos, botones de tamaño y volumen amplificado hasta 200 %. El botón de opciones permite elegir una foto y ajustar la opacidad de la ventana. Los colores se actualizan al cambiar Apariencia con el reproductor abierto.

### Servidores alternativos de YouTube · versión 1.6.19

VideoFlow utiliza [yt-dlp](https://github.com/yt-dlp/yt-dlp) como biblioteca de Python para el análisis y las descargas. Esta versión incluye **yt-dlp 2026.10.26**. La interfaz, el reproductor, el historial y las herramientas de conversión pertenecen a VideoFlow.

Se corrige el caso en el que el enlace dirige al motor a un servidor de video que no responde, aunque el navegador pueda reproducir el contenido desde otro servidor. El problema está documentado en [yt-dlp #1986](https://github.com/yt-dlp/yt-dlp/issues/1986). Si la URL de un formato de YouTube contiene la lista de servidores `mn`, las solicitudes nativas HTTP de descarga pueden utilizar hasta **dos alternativas** de esa misma lista tras un error de conexión o un HTTP 500/502/503/504.

Se conserva la URL del archivo con su ruta, consulta firmada, rango solicitado, formato y pista de audio; solo cambia el servidor dentro de los dominios de video que anuncia YouTube. Las solicitudes con alternativas tienen una espera máxima de 12 segundos sin respuesta. Si una alternativa responde, se prefiere para solicitudes posteriores de la misma instancia cuando también figura en el enlace correspondiente. Se muestra **Conectando a un servidor alternativo de YouTube…** y continúa el progreso habitual.

No se usan servidores ajenos, no se cambian ajustes de Windows y se mantiene la validación TLS. Los errores 401/403/429 y los errores de certificado no activan el cambio de servidor. **0 reintentos** desactiva esta recuperación. Las solicitudes sin alternativas declaradas, los métodos con cuerpo y los descargadores externos conservan su comportamiento normal. El recorte que se descarga mediante FFmpeg externo no utiliza este cambio de servidor nativo.

En el diagnóstico del caso reportado, el servidor principal agotó el tiempo de conexión y una alternativa anunciada devolvió **HTTP 200** para las cabeceras de la misma pista de audio. No se descargó el contenido del audio o video durante esa comprobación. Que un servidor responda a HEAD no garantiza una descarga completa; el acceso depende también de la sesión, la vigencia del enlace y la disponibilidad del servidor.

### Recuperación de conexiones de descarga · versión 1.6.18

Si el análisis obtiene el título y la miniatura pero la descarga falla con **googlevideo.com timed out**, la conexión con el servidor que entrega el archivo está agotando el tiempo de espera. Poder reproducirlo en el navegador no confirma que el motor de descarga pueda llegar al mismo servidor por la misma ruta.

En **Configuración → Conexión y recuperación → Conexión para YouTube**, elige **Automática**, **IPv4** o **IPv6** y guarda la configuración. IPv6 requiere soporte de tu red. La elección se aplica al análisis, las colecciones y los siguientes intentos de descarga. Son las [opciones de conexión de yt-dlp](https://github.com/yt-dlp/yt-dlp#network-options); no se modifican los ajustes de red de Windows.

En modo Automática, tras agotar los reintentos normales por un fallo de conexión, la app vuelve a consultar el enlace una sola vez mediante IPv4. Esta recuperación adicional no repite los reintentos internos y se desactiva si configuras **0 reintentos**. Los reintentos normales esperan 1, 2, 4 y hasta 8 segundos entre solicitudes. La recuperación conserva formato, calidad, sesión, recorte y pista de audio; la cancelación y la pausa siguen disponibles.

Las descargas de Internet que terminan con error tienen un botón **↻ Reintentar descarga**. Devuelve el mismo trabajo a la cola y utiliza la conexión configurada, conservando sus opciones y destino. Se impiden reintentos simultáneos del mismo trabajo y conflictos con una ruta reservada. Los trabajos completados no se vuelven a descargar con este botón. Los registros con error restaurados desde Retiradas temporalmente también pueden reintentarse; una sesión importada de cookies que haya vencido requiere volver a analizar el video con una sesión vigente.

Se descarga un fragmento a la vez por archivo y se detiene el trabajo si falta uno, evitando marcar como completos videos con fragmentos omitidos. Se muestran las fases de conexión y recuperación y mensajes comprensibles en español, inglés y portugués. El resultado depende de la conectividad con YouTube; estos cambios no garantizan que un servidor inaccesible vuelva a responder.

### Sesión de YouTube y avisos de acceso · versión 1.6.17

Si aparece **Sign in to confirm you’re not a bot**, YouTube está solicitando confirmar el acceso. En **Inicio → YouTube → Sesión de YouTube (opcional)**, elige **Brave, Chrome, Edge o Firefox** después de abrir el video e iniciar sesión en ese navegador. Completa allí cualquier comprobación que aparezca y vuelve a pulsar **Analizar video**. Si el navegador mantiene ocupada su base de cookies, ciérralo por completo antes de reintentar. El análisis, la descarga individual, los lotes y las colecciones utilizan la sesión que hayas elegido; la descarga individual conserva la utilizada al analizar. Desde Listas y canales puedes ir directamente al selector.

Si Windows protege las cookies de un navegador Chromium y no permite leerlas, usa Firefox o **Usar archivo cookies.txt → Seleccionar cookies.txt**. Se admite un archivo de texto Netscape de hasta 2 MB, con cookies vigentes de YouTube. Consulta las [instrucciones oficiales de yt-dlp para exportar cookies de YouTube](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies). La importación filtra los dominios de YouTube; su contenido permanece en memoria, no se incluye en el historial ni se modifica el archivo original. Tras cerrar la app debes volver a seleccionarlo.

El valor inicial es **Sin sesión**: no se lee una sesión del navegador sin elegirla. Los errores habituales de acceso, sesión ocupada, protección de Windows y límite de solicitudes se muestran en español, inglés o portugués con el paso siguiente. El error del análisis también queda junto al enlace, sin depender de la notificación temporal. Usar una sesión no garantiza que YouTube permita el acceso: la comprobación y los permisos del video dependen del sitio.

### Elegir la pista de audio de un video · versión 1.6.16

Pega un enlace y pulsa **Analizar video**. En **Información y opciones → Pista de audio** aparecen las pistas que el sitio permite descargar, con su nombre o idioma y las marcas **Original**, **Predeterminada** o **Audiodescripción** cuando estén identificadas. Elige una pista y pulsa **Agregar a la cola** para guardar el video con ese audio. **Automático · recomendado** conserva la selección habitual del motor. La elección también sirve para **Solo audio**, incluidos OGG Vorbis, MP3, M4A, WAV y FLAC; **Solo video** desactiva el selector.

Las variantes de calidad que comparten los mismos datos de pista se agrupan para elegir la mejor disponible dentro de la calidad de video indicada. La descarga vuelve a consultar las pistas y restringe tanto la selección principal como sus alternativas a la elegida: si ya no está disponible, muestra un error en lugar de cambiar a otro audio. Esto se integra con la [selección de formatos de yt-dlp](https://github.com/yt-dlp/yt-dlp#format-selection).

La pista elegida se muestra en Descargas, se guarda en Historial y se conserva en los registros retirados temporalmente. Al volver a descargar desde Historial se intenta preseleccionar esa pista si sigue disponible. Los lotes y colecciones mantienen la selección automática de cada video. Algunos sitios solo exponen una pista o no informan los idiomas; la app muestra los datos disponibles y no crea doblajes. Se mantiene el diseño, con textos en español, inglés y portugués.

### OGG con audio Vorbis y conversión de WAV · versión 1.6.15

En **Video a audio**, pulsa **Seleccionar archivos** y elige uno o varios **WAV**, audios o videos. Selecciona **OGG · Vorbis**, elige **128, 192 o 320 kbps**, indica la carpeta de salida y pulsa **Convertir archivos**. **Guardar como…** permite elegir el nombre y destino por archivo. Se crea un `.ogg` nuevo con audio Vorbis, conservando el original; el progreso y la cancelación aparecen en Descargas y el resultado se añade a Historial.

La selección nativa incluye WAV y otros formatos de audio. OGG también está disponible en **Solo audio** para descargas individuales, lotes y listas o canales, en el navegador privado y como formato predeterminado en Configuración. La extensión de salida y el formato interno se corresponden: se comprueba que la pista de audio sea Vorbis antes de marcar el trabajo como completado. Los controles y mensajes nuevos incluyen inglés y portugués.

Vorbis usa compresión con pérdida; la tasa de bits es aproximada, según las [opciones de libvorbis en FFmpeg](https://ffmpeg.org/ffmpeg-codecs.html#libvorbis). Para conversiones locales se genera audio estéreo a 48 kHz. Si una descarga ya contiene Vorbis, el motor puede conservarlo sin recodificar, manteniendo su tasa original.

### Comprimir videos para ahorrar espacio · versión 1.6.14

Abre **Comprimir video**, selecciona uno o varios archivos y elige una reducción **ligera (aproximadamente 30%)**, **equilibrada (50%)** o **alta (70%)**. Se muestran el tamaño original, la salida estimada y el ahorro del lote. Puedes mantener la resolución o limitar la altura a **1080p, 720p o 480p**, sin aumentarla. Elige la carpeta de destino o usa **Guardar como…** junto a cada archivo. La carpeta de compresión se recuerda por separado de las conversiones.

**Comprimir archivos** añade los trabajos a Descargas, con progreso y cancelación, respetando el límite de trabajos simultáneos configurado. Al terminar se muestra el tamaño real antes y después y el porcentaje ahorrado; el archivo también aparece en Historial. Los originales se conservan y la salida lleva un nombre nuevo, como `Video - comprimido [id].mp4`. No se guarda como completado un resultado vacío, incompleto o que pese más que el original. Se eliminan los archivos parciales tras un error o cancelación.

La salida es MP4 con H.264 y la primera pista de audio en AAC, si existe. No se copian subtítulos ni pistas adicionales; los videos HDR se convierten a SDR. Se calcula un presupuesto de bits según el tamaño original y la duración y se codifica en [dos pasadas con FFmpeg](https://ffmpeg.org/ffmpeg.html#Video-Options). El tamaño es orientativo y reducirlo puede disminuir la nitidez. Los videos muy pequeños o ya muy comprimidos pueden requerir un nivel distinto o una resolución menor. La pantalla, los mensajes y las fases de trabajo incluyen traducciones al inglés y al portugués.

### Vaciar las descargas retiradas · versión 1.6.13

En **Descargas → Retiradas temporalmente**, el botón **Vaciar retiradas** permite quitar todos los registros temporales de una vez, incluidos los de incógnito disponibles durante la sesión. Antes de hacerlo aparece una confirmación que aclara que esos registros ya no podrán restaurarse desde este apartado. **Cancelar** conserva los registros; **Confirmar** vacía únicamente el archivo temporal de registros, sin borrar ni modificar archivos descargados, el historial o la cola de Descargas.

El botón conserva el estilo de las acciones de limpieza de la app y se desactiva cuando no hay registros. Mientras se confirma o se vacía, las acciones del apartado quedan bloqueadas para evitar operaciones simultáneas. Al terminar se actualiza la lista y se muestra cuántos registros se quitaron. Los controles, la confirmación y los mensajes incluyen traducciones al inglés y al portugués.

### Restaurar todas las descargas retiradas · versión 1.6.12

En **Descargas → Retiradas temporalmente**, pulsa **Restaurar todas** para devolver a la cola todos los registros disponibles en una sola acción. Conservan su estado anterior (**Completado**, **Error** o **Cancelado**), sin volver a descargar, convertir ni separar archivos y sin crear entradas nuevas en el historial. También incluye los registros de incógnito disponibles durante la sesión y respeta el plazo de conservación configurado.

El botón usa el estilo de la aplicación, se desactiva cuando la lista está vacía o mientras restaura, y muestra el resultado con la cantidad restaurada. Al terminar se actualizan la cola y el apartado temporal. Los registros que ya estén en la cola no se duplican; un conflicto no impide restaurar los demás. La restauración individual sigue disponible. Los controles y mensajes nuevos incluyen traducciones al inglés y al portugués.

### Plazo de conservación configurable · versión 1.6.11

En **Configuración → Descargas retiradas temporalmente → Tiempo de conservación**, elige **7, 15 o 30 días** y pulsa **Guardar configuración**. La opción se conserva al reiniciar; el valor inicial es 30 días. El plazo se cuenta desde que retiraste cada descarga y se aplica también a los registros temporales existentes, sin reiniciar su antigüedad.

Al acortar el plazo se descartan los registros que ya lo superen. Ampliarlo conserva durante más tiempo los registros que siguen disponibles; no recupera registros vencidos. La sección de retiradas muestra el plazo elegido y la fecha de vencimiento de cada registro. Solo se eliminan registros temporales: los archivos y el historial se conservan. En modo incógnito siguen disponibles únicamente durante la sesión. El selector y los avisos están traducidos al inglés y al portugués.

### Descargas retiradas temporalmente · versión 1.6.10

Al pulsar **Quitar de la lista** o **Quitar completadas de la cola**, los registros pasan al apartado **Retiradas temporalmente**, debajo de la cola de Descargas. Se conservan durante **30 días**, también al cerrar la app. **Restaurar a Descargas** devuelve el registro con su estado anterior sin volver a descargar ni crear otra entrada en Historial. Desde ese apartado también puedes mostrar el archivo o quitar un registro temporal con confirmación.

Esta función guarda la información del trabajo; no mueve, copia ni elimina el video o audio. El historial permanece intacto. Al vencer el plazo se descarta únicamente el registro temporal, durante la siguiente consulta o inicio. Los trabajos en modo incógnito se mantienen solo en memoria durante la sesión. Los registros quitados en versiones anteriores no pueden recuperarse mediante esta función.

### Inicio de colecciones · versión 1.6.9

Corregido el botón **Descargar colección**, que compartía identificador con el campo de inicio del recorte y no recibía la acción de descarga. Ahora muestra una confirmación persistente al iniciar, conserva el enlace y presenta los errores de lectura junto a la colección. **Ver descargas** abre la cola de canciones o videos añadidos. «Lectura finalizada» indica que se terminó de importar la lista; el estado de cada archivo se consulta en Descargas. Una colección sin entradas disponibles se marca como error.

### Idiomas de la interfaz · versión 1.6.8

En **Configuración → Idioma de la aplicación**, elige **Español**, **English** o **Português**. El cambio se aplica al instante y se guarda automáticamente para los próximos inicios. Se traducen las pantallas, controles y mensajes habituales, incluido el reproductor y sus ventanas flotantes. Se conservan los títulos de videos, nombres de archivos, rutas y enlaces. Las fechas y cantidades siguen el idioma elegido. Los catálogos se incluyen en el programa y funcionan sin un servicio externo de traducción.

Consulta [cómo funciona y cómo mantener las traducciones](docs/IDIOMAS.md). Los diálogos proporcionados por Windows y los mensajes técnicos externos pueden conservar su idioma original.

### Clic sobre el video en PiP · versión 1.6.6

Haz clic directamente sobre el video en Picture-in-Picture para pausar o reanudar; al terminar, otro clic lo inicia desde el principio. Arrastrar el video sigue moviendo la ventana en tiempo real y no cambia la reproducción. El clic sobre el video también está disponible en la ventana flotante normal. Se conserva el diseño minimalista de PiP y los controles de la ventana principal continúan sincronizados.

### Mostrar la ubicación de un archivo · versión 1.6.5

El botón para abrir la ubicación selecciona el archivo mediante la API nativa de Windows `SHOpenFolderAndSelectItems`, en lugar de ejecutar `explorer.exe` con argumentos. Las carpetas se siguen abriendo con la acción de apertura del sistema. Los errores al abrir una ubicación aparecen en la aplicación. Este cambio no garantiza que un antivirus deje de avisar: la clasificación depende del proveedor del antivirus.

### Picture-in-Picture minimalista · versión 1.6.4

El video ocupa toda la miniventana PiP, sin barra de título ni panel de controles permanente. Al mover el puntero aparecen botones discretos para pausar/reproducir, volver al reproductor principal o cerrar; se ocultan tras un momento de inactividad. Arrastra directamente el video para mover la ventana en tiempo real mientras continúa reproduciéndose. Las flechas y la barra espaciadora siguen controlando la reproducción con el video enfocado.

### Ventana flotante, PiP y FFmpeg · versión 1.6.3

La ventana flotante distribuye toda su altura entre video y controles. Conserva la posición, reproducción/pausa, volumen, velocidad y brillo al abrirse y al volver al reproductor principal. La barra de tiempo del reproductor principal también controla la ventana pequeña; solo una de las ventanas reproduce audio.

En escritorio, **Picture-in-Picture** abre una miniventana propia siempre encima. Arrastra el video para moverla en vivo. Este movimiento usa la región de arrastre de la app y conserva la reproducción. Usa ↗ para volver al reproductor principal o × para cerrar. En el modo navegador se utiliza PiP nativo cuando está disponible.

Cada inicio comprueba la versión estable de FFmpeg en segundo plano mediante la API de versiones de Gyan. Configuración muestra la versión instalada, la última publicada y la hora de comprobación. **Comprobar ahora** repite la consulta. Desde la versión 1.6.30, puedes descargar e instalar las actualizaciones dentro de VideoFlow.

### Reproductor y secreto retro · versión 1.6.2

El reproductor principal y la ventana flotante tienen controles propios siempre visibles: barra de tiempo arrastrable, volumen, silencio, reproducción, reinicio y pantalla completa con los controles incluidos. Las barras están separadas del área de gestos del video. Se conserva el soporte para abrir o arrastrar archivos y retomar el video al cambiar de sección.

Introduce **↑ ↑ ↓ ↓ ← → ← → B A** fuera de un campo de escritura para descubrir **VideoFlow Arcade**, un juego local de atrapar notas durante 30 segundos. Usa las flechas, A/D o el mouse. Se cierra con Esc o Cerrar; pausa el video mientras juegas y lo reanuda al cerrar si antes estaba reproduciéndose. Las descargas siguen su curso y el juego no cambia tus preferencias.

### Reproductor · versión 1.6.1

Abre un video o audio con **Abrir archivo** o arrástralo sobre el panel del reproductor. Los archivos se leen directamente desde su ubicación, sin copiarlos ni subirlos. Al terminar, **Volver a reproducir** lo inicia desde el principio; **Reiniciar** está disponible en cualquier momento. Al cambiar de sección, se pausa y retoma la misma posición al regresar si estaba reproduciéndose. Si lo pausaste, conserva esa pausa. Los controles de reproducción también están disponibles en la ventana flotante. En el modo navegador, los archivos arrastrados se reproducen localmente, y la ventana flotante de escritorio requiere abrir el archivo desde el selector.

El instalador incluye Python, FFmpeg, FFprobe y Deno. También instala Microsoft Edge WebView2 si no está disponible; este paso requiere Internet. Crea accesos directos y permite desinstalar VideoFlow desde Configuración de Windows. No requiere instalar Python ni preparar el entorno manualmente.

Abre **VideoFlow Local** desde el menú Inicio o el escritorio. Toda la interfaz aparece en una ventana propia con icono en la barra de tareas y controles para minimizar, maximizar y cerrar. Al volver a abrir el acceso directo, se recupera la ventana existente. Por defecto, cerrar la ventana la oculta en la bandeja y los trabajos continúan. Usa el icono junto al reloj para abrirla o salir y detener los trabajos. Puedes desactivar este comportamiento en Configuración.

La versión instalada guarda el historial y las preferencias en `%LOCALAPPDATA%\VideoFlowLocal\data`, fuera de la carpeta del programa. Las actualizaciones mediante un instalador nuevo conservan esos datos. La versión desde código fuente sigue usando su carpeta `data`.

El instalador inicial no tiene firma digital.

## Perfil y sonidos

En **Perfil** puedes guardar un nombre visible, un nombre de usuario y una descripción. Elige un avatar de ejemplo, importa una imagen o un GIF, o descarga una imagen desde su enlace HTTPS directo si el sitio lo permite. El encuadre, el fondo y el avatar se guardan en este equipo. Un banner de video de hasta 30 segundos se repite en silencio y dispone de un control de reproducción.

**Perfil → Suscripciones** muestra los beneficios propuestos para Usuario Pro. **Configuración → Sonidos (Tester)** permite activar y probar por separado los sonidos de clic, descarga completa y error.

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
- Análisis de enlaces de YouTube, Facebook, TikTok, Reddit, Instagram, X y clips de Twitch con miniatura, título, autor, duración y calidades disponibles.
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
- Cada plataforma recuerda su carpeta de destino al cerrar y abrir la aplicación. Puedes cambiarla en Configuración o con «Guardar como».
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

En **Voz e instrumentos → Procesador para Demucs**, elige **CPU**, **GPU automática** o el proveedor GPU disponible. En Windows, el instalador predeterminado incluye **DirectML** para adaptadores compatibles con DirectX 12. Si no se puede iniciar o mantener la inferencia en la GPU, la app continúa con CPU e indica qué procesador se utilizó.

Para usar **CUDA** con una GPU NVIDIA, instala la variante con `INSTALAR.bat cuda` desde el repositorio o compila con `CREAR_INSTALADOR.ps1 -SeparationRuntime cuda`. Esa variante usa CUDA 13 y cuDNN 9. Sus DLL deben estar disponibles en Windows. `ACTUALIZAR.bat directml` vuelve a instalar la variante predeterminada. Cada variante incluye el motor de CPU. Consulta los requisitos del [proveedor CUDA de ONNX Runtime](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html) y de [DirectML](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html).

Si ejecutas VideoFlow desde el repositorio con la variante CUDA, también puedes instalar CUDA y cuDNN en su entorno de Python con `.venv\Scripts\python.exe -m pip install "onnxruntime-gpu[cuda,cudnn]==1.31.0"`.

Una sola separación se procesa a la vez. El audio se prepara en estéreo a 44,1 kHz y se procesa localmente por fragmentos.

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
