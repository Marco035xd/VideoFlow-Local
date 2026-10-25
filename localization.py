"""Supported interface languages; Spanish remains the compatibility default."""
import json
from functools import lru_cache
from app_paths import APP_DIR

LANGUAGES = {'es': 'Español', 'en': 'English', 'pt': 'Português'}


def normalize_language(value):
    return value if isinstance(value, str) and value in LANGUAGES else 'es'


@lru_cache(maxsize=1)
def messages():
    return json.loads((APP_DIR / 'static/locales/messages.json').read_text(encoding='utf-8'))


def translate(text, language='es'):
    index = {'en': 0, 'pt': 1}.get(normalize_language(language))
    return messages().get(text, [text, text])[index] if index is not None else text


def native_labels(language):
    return {key: translate(text, language) for key, text in {
        'global.ok': 'Aceptar', 'global.cancel': 'Cancelar', 'global.quit': 'Cerrar',
        'global.saveFile': 'Guardar archivo', 'windows.fileFilter.allFiles': 'Todos los archivos',
    }.items()}
