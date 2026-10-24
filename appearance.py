"""Validated, local appearance preferences shared by settings reads and writes."""
import re

DEFAULT_APPEARANCE = {
    'preset': 'videoflow',
    'accent': 'default',
    'custom_accent': '#8b5cf6',
    'custom_colors': False,
    'background': '#181818',
    'foreground': '#ffffff',
    'font': 'system',
    'density': 'comfortable',
    'reduce_motion': False,
}
CHOICES = {
    'preset': {'videoflow', 'graphite', 'ocean', 'forest', 'plum', 'sand'},
    'accent': {'default', 'blue', 'green', 'yellow', 'pink', 'orange', 'purple', 'white', 'custom'},
    'font': {'system', 'humanist', 'serif', 'mono'},
    'density': {'comfortable', 'compact'},
}
COLOR_KEYS = {'custom_accent', 'background', 'foreground'}
BOOL_KEYS = {'custom_colors', 'reduce_motion'}


def contrast_ratio(first, second):
    def luminance(color):
        components = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in components]
        return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + .05) / (dark + .05)


def normalize_appearance(value, strict=False):
    if not isinstance(value, dict):
        if strict:
            raise ValueError('Las opciones de apariencia no son válidas.')
        value = {}
    result = DEFAULT_APPEARANCE.copy()
    for key, item in value.items():
        valid = False
        if key in CHOICES:
            valid = isinstance(item, str) and item in CHOICES[key]
        elif key in COLOR_KEYS:
            valid = isinstance(item, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', item) is not None
        elif key in BOOL_KEYS:
            valid = isinstance(item, bool)
        if not valid:
            if strict:
                raise ValueError(f'El valor de apariencia «{key}» no es válido.')
            continue
        result[key] = item.lower() if key in COLOR_KEYS else item
    if result['custom_colors'] and contrast_ratio(result['background'], result['foreground']) < 4.5:
        if strict:
            raise ValueError('Elige un texto y un fondo con más contraste para que la aplicación sea legible.')
        result['custom_colors'] = False
    return result
