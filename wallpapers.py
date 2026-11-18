"""Local wallpaper gallery with an active selection stored in the same database."""
from contextlib import closing
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import sqlite3

from flask import jsonify, request, send_file
from PIL import ImageOps, Image

from local_images import read_background, webp_bytes

GALLERY_API = '/api/appearance/wallpapers'
DEFAULT_OPACITY = 54


def register(app, settings):
    from desktop_dialogs import choose

    database = settings.path.parent / 'wallpapers.db'
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS wallpapers (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, photo BLOB NOT NULL, thumbnail BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS wallpaper_selection (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                active TEXT REFERENCES wallpapers(id)
            );
            INSERT OR IGNORE INTO wallpaper_selection (singleton) VALUES (1);
        ''')
        connection.execute('BEGIN IMMEDIATE')
        columns = {column[1] for column in connection.execute('PRAGMA table_info(wallpapers)')}
        if 'opacity' not in columns:
            connection.execute(f'ALTER TABLE wallpapers ADD COLUMN opacity INTEGER NOT NULL DEFAULT {DEFAULT_OPACITY} CHECK (opacity BETWEEN 25 AND 100)')

    @app.route(GALLERY_API, methods=['GET', 'POST', 'PUT'])
    def wallpaper_gallery():
        cancelled = False
        imported = None
        try:
            if request.method == 'POST':
                paths = choose('OPEN', settings.load()['default_folder'],
                               file_types=('Imágenes (*.jpg;*.jpeg;*.png;*.webp)',), allow_multiple=False)
                if paths:
                    path = Path(paths[0])
                    image = read_background(path, max_edge=2560)
                    photo = webp_bytes(image)
                    thumbnail = ImageOps.fit(image, (320, 180), Image.Resampling.LANCZOS)
                    imported = (sha256(photo).hexdigest(), path.stem, photo, webp_bytes(thumbnail, quality=80))
                else:
                    cancelled = True

            with closing(sqlite3.connect(database)) as connection, connection:
                if imported:
                    connection.execute('INSERT OR IGNORE INTO wallpapers (id, name, photo, thumbnail) VALUES (?, ?, ?, ?)', imported)
                    connection.execute('UPDATE wallpaper_selection SET active = ? WHERE singleton = 1', imported[:1])
                if request.method == 'PUT':
                    payload = request.get_json(silent=True)
                    if not isinstance(payload, dict):
                        raise ValueError('Selecciona un fondo guardado.')
                    if 'opacity' in payload:
                        opacity = payload['opacity']
                        if type(opacity) is not int or not 25 <= opacity <= 100:
                            raise ValueError('Elige una opacidad entre 25 % y 100 %.')
                        key = payload.get('photo')
                        if not isinstance(key, str) or not connection.execute(
                            'UPDATE wallpapers SET opacity = ? WHERE id = ?', (opacity, key)
                        ).rowcount:
                            raise ValueError('Selecciona un fondo guardado.')
                    else:
                        if 'active' not in payload:
                            raise ValueError('Selecciona un fondo guardado.')
                        active = payload['active']
                        if active is not None and (not isinstance(active, str) or connection.execute(
                            'SELECT 1 FROM wallpapers WHERE id = ?', (active,)
                        ).fetchone() is None):
                            raise ValueError('Selecciona un fondo guardado.')
                        connection.execute('UPDATE wallpaper_selection SET active = ? WHERE singleton = 1', (active,))

                active, = connection.execute('SELECT active FROM wallpaper_selection WHERE singleton = 1').fetchone()
                photos = [dict(id=key, name=name, opacity=opacity) for key, name, opacity in connection.execute(
                    'SELECT id, name, opacity FROM wallpapers ORDER BY rowid DESC'
                )]
            return jsonify(ok=True, active=active, photos=photos, cancelled=cancelled)
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 400
        except (OSError, sqlite3.Error):
            app.logger.exception('Could not update the local wallpaper gallery')
            return jsonify(ok=False, error='No se pudo guardar o leer la galería de fondos.'), 500

    @app.get(GALLERY_API + '/<key>/<size>')
    def wallpaper_image(key, size):
        if size not in ('photo', 'thumbnail'):
            return '', 404
        with closing(sqlite3.connect(database)) as connection:
            if size == 'thumbnail':
                image = connection.execute('SELECT thumbnail FROM wallpapers WHERE id = ?', (key,)).fetchone()
            else:
                image = connection.execute('SELECT photo FROM wallpapers WHERE id = ?', (key,)).fetchone()
        if image is None:
            return '', 404
        return send_file(BytesIO(image[0]), mimetype='image/webp')
