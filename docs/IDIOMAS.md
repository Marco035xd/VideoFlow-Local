# Idiomas de la interfaz

En **Configuración → Idioma de la aplicación**, elige **Español**, **English** o **Português**. La selección se aplica al instante, se guarda automáticamente y se conserva al volver a abrir VideoFlow. La configuración anterior sigue usando español hasta que el usuario elija otro idioma.

El cambio conserva la sección abierta, los trabajos en curso y las selecciones de archivos. Incluye menús, botones, formularios, ayudas, estados habituales, avisos, Apariencia y controles del reproductor. PiP y las ventanas flotantes abiertas reciben el cambio de idioma. Los nombres de archivos, títulos de videos, rutas y enlaces se conservan.

Las fechas y cantidades de la interfaz utilizan el formato del idioma seleccionado. Los botones nativos proporcionados por Windows y los mensajes técnicos externos pueden seguir el idioma del sistema o del componente que los genera. Los mensajes sin traducción disponible conservan su texto original.

## Mantenimiento

- `localization.py` declara los idiomas admitidos, valida la preferencia y proporciona textos para las ventanas nativas.
- `static/locales/messages.json` contiene frases de origen en español y un par de traducciones en este orden: **inglés, portugués**.
- `static/language.js` aplica las traducciones de presentación y escucha las actualizaciones de la interfaz. Conserva el texto original para cambiar de idioma varias veces. Los valores de formularios, identificadores, URLs y datos del usuario no se traducen.
- Las frases con variables utilizan marcadores `{0}`, `{1}`, etc. Las traducciones deben conservarlos.
- Los elementos con `translate="no"` se excluyen de la traducción. Se usa para los nombres propios de los idiomas y para contenido del usuario.

No se consulta un servicio de traducción ni se envían archivos a Internet para cambiar de idioma. Los catálogos se incluyen en la aplicación.
