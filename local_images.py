"""Read user-selected background photos into a bounded raster image."""
from io import BytesIO
from pathlib import Path


def read_background(path, max_edge=1600):
    from PIL import Image, ImageOps

    try:
        with Path(path).open('rb') as file:
            data = file.read(15 * 1024 * 1024 + 1)
        if len(data) > 15 * 1024 * 1024:
            raise ValueError('La foto debe pesar 15 MB o menos.')
        with Image.open(BytesIO(data), formats=('JPEG', 'PNG', 'WEBP')) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError('Elige una foto de hasta 40 megapíxeles.')
            image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            return ImageOps.exif_transpose(image).convert('RGB')
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError('No se pudo abrir la foto. Elige un archivo JPG, PNG o WebP.') from exc


def webp_bytes(image, quality=88):
    output = BytesIO()
    image.save(output, 'WEBP', quality=quality)
    return output.getvalue()
