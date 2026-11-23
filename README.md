<div align="center">
  <img src="static/logo.svg" width="88" height="88" alt="Logo de VideoFlow Local">
  <h1>VideoFlow Local</h1>
  <p>Descarga, convierte y reproduce video y audio en Windows.</p>
  <p>
    <a href="https://github.com/Marco035xd/VideoFlow-Local/releases/latest"><img src="https://img.shields.io/github/v/release/Marco035xd/VideoFlow-Local?label=Versi%C3%B3n&amp;color=2563eb" alt="Última versión publicada"></a>
    <img src="https://img.shields.io/badge/Windows-10%20%2F%2011%20x64-1e3a5f" alt="Windows 10 y 11 de 64 bits">
  </p>
  <p><a href="https://github.com/Marco035xd/VideoFlow-Local/releases/latest"><strong>Descargar para Windows</strong></a></p>
  <p>
    <a href="#capturas-de-pantalla">Capturas</a> ·
    <a href="#funciones">Funciones</a> ·
    <a href="#instalación">Instalación</a> ·
    <a href="#código-fuente">Código fuente</a> ·
    <a href="https://github.com/Marco035xd/VideoFlow-Local-Android">Android</a>
  </p>
</div>

![Inicio de VideoFlow Local en modo oscuro con el selector de plataformas y el campo para pegar enlaces](docs/capturas/windows/inicio.png)

## Funciones

| Área | Qué puedes hacer |
| --- | --- |
| **Descargas** | Guarda videos de YouTube, Facebook, TikTok, Reddit, Instagram, X y clips de Twitch. Elige formato, resolución, pista de audio, recorte y subtítulos según el origen. |
| **Listas y canales** | Importa colecciones de YouTube y consulta el peso total aproximado antes de añadirlas a la cola. |
| **Cola, galería e historial** | Filtra los trabajos por estado, ordénalos y copia sus enlaces originales. Reanuda descargas interrumpidas, restaura registros retirados y busca por título o plataforma en la galería. |
| **Conversión y compresión** | Convierte videos a MP4, MKV, MOV, AVI o WebM. Extrae audio en MP3, M4A, WAV, FLAC u OGG Vorbis, reduce el tamaño de tus videos y separa voz e instrumentos en tu equipo. |
| **Reproductor** | Abre tus archivos locales y sigue viendo en ventana flotante o Picture-in-Picture. |
| **Personalización** | Elige temas, fondos y opacidad. Personaliza tu perfil, configura los sonidos y usa la app en español, inglés o portugués. |
| **Herramientas locales** | Protege copias de archivos en la carpeta cifrada con PIN y actualiza FFmpeg y FFprobe desde Configuración. |

## Capturas de pantalla

<table>
  <tr>
    <td width="50%" valign="top">
      <a href="docs/capturas/windows/descargas.png"><img src="docs/capturas/windows/descargas.png" alt="Cola de descargas con filtros de estado y orden"></a><br>
      <strong>Descargas</strong> · Estado, orden y progreso
    </td>
    <td width="50%" valign="top">
      <a href="docs/capturas/windows/listas-y-canales.png"><img src="docs/capturas/windows/listas-y-canales.png" alt="Formulario de importación de listas y canales de YouTube"></a><br>
      <strong>Listas y canales</strong> · Colecciones de YouTube
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <a href="docs/capturas/windows/comprimir-video.png"><img src="docs/capturas/windows/comprimir-video.png" alt="Formulario para comprimir varios videos"></a><br>
      <strong>Compresión</strong> · Reducción y resolución de salida
    </td>
    <td width="50%" valign="top">
      <a href="docs/capturas/windows/reproductor.png"><img src="docs/capturas/windows/reproductor.png" alt="Reproductor de archivos con controles de ventana flotante y Picture-in-Picture"></a><br>
      <strong>Reproductor</strong> · Ventana flotante y Picture-in-Picture
    </td>
  </tr>
</table>

**[Ver las 15 capturas en tamaño completo](docs/CAPTURAS.md)**

## Instalación

1. Descarga el archivo `VideoFlow-Local-…-Setup-x64.exe` de la [última publicación para Windows](https://github.com/Marco035xd/VideoFlow-Local/releases/latest).
2. Ejecuta el instalador y abre **VideoFlow Local** desde el menú Inicio.

Compatible con **Windows 10 (1809 o posterior)** y **Windows 11** de 64 bits. El instalador incluye Python, FFmpeg, FFprobe y Deno. Si falta WebView2, lo instala durante la configuración.

## Código fuente

Para ejecutar el proyecto, clona o descarga el repositorio en Windows. Ejecuta [`INSTALAR.bat`](INSTALAR.bat) y luego [`INICIAR.bat`](INICIAR.bat). El entorno usa Python 3.11 o posterior, FFmpeg, FFprobe y WebView2. El script usa WinGet para preparar las herramientas que falten, incluido Deno para mejorar la compatibilidad con YouTube.

Para compilar el instalador, instala Inno Setup 6 y ejecuta [`CREAR_INSTALADOR.ps1`](CREAR_INSTALADOR.ps1) desde PowerShell. El resultado queda en `release/`.

Consulta la [documentación de idiomas](docs/IDIOMAS.md) y los [avisos de los componentes incluidos](packaging/THIRD_PARTY_NOTICES.md).

## Proyecto

¿Encontraste un problema o tienes una idea? Abre una [incidencia](https://github.com/Marco035xd/VideoFlow-Local/issues) con los pasos y la versión de la app. El código y las APK de Android están en el [repositorio de VideoFlow Local para Android](https://github.com/Marco035xd/VideoFlow-Local-Android).

Usa VideoFlow Local para guardar contenido propio o que tengas autorización para descargar.
