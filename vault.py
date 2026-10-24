"""PIN-protected, authenticated streaming encryption for local media."""
import hashlib
import json
import os
import re
import struct
import threading
import time
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b'VFLOWV1\0'
CHUNK = 1024 * 1024


class Vault:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(self.root), 2)
        self.config = self.root / 'vault.json'
        self.key, self.accessed = None, 0
        self.failures, self.retry_at = 0, 0
        self.lock = threading.RLock()

    @staticmethod
    def derive(pin, salt):
        if not isinstance(pin, str) or not re.fullmatch(r'\d{6,32}', pin):
            raise ValueError('Usa un PIN de entre 6 y 32 dígitos.')
        return hashlib.scrypt(pin.encode(), salt=salt, n=32768, r=8, p=1, maxmem=64*1024*1024, dklen=32)

    def unlock(self, pin):
        with self.lock:
            if time.monotonic() < self.retry_at:
                raise ValueError('Espera 30 segundos antes de volver a intentar.')
            if not self.config.exists():
                salt, nonce = os.urandom(16), os.urandom(12)
                key = self.derive(pin, salt)
                data = dict(salt=salt.hex(), nonce=nonce.hex(), verifier=AESGCM(key).encrypt(nonce, b'VideoFlow Vault', MAGIC).hex())
                with self.config.open('x', encoding='utf-8') as config:
                    json.dump(data, config)
            else:
                data = json.loads(self.config.read_text(encoding='utf-8'))
                key = self.derive(pin, bytes.fromhex(data['salt']))
                try:
                    AESGCM(key).decrypt(bytes.fromhex(data['nonce']), bytes.fromhex(data['verifier']), MAGIC)
                except Exception:
                    self.failures += 1
                    if self.failures >= 5:
                        self.retry_at = time.monotonic() + 30
                    raise ValueError('PIN incorrecto.') from None
            self.key, self.accessed, self.failures = key, time.monotonic(), 0

    def require_key(self):
        if self.key is None or time.monotonic() - self.accessed > 300:
            self.key = None
            raise ValueError('La carpeta privada está bloqueada. Introduce tu PIN.')
        self.accessed = time.monotonic()
        return self.key

    def status(self):
        with self.lock:
            if time.monotonic() - self.accessed > 300:
                self.key = None
            return dict(configured=self.config.exists(), unlocked=self.key is not None)

    def close(self):
        with self.lock:
            self.key = None

    def protect(self, source):
        source = Path(source).resolve()
        with self.lock:
            key = self.require_key()
            if not source.is_file() or self.root.resolve() in source.parents:
                raise ValueError('Selecciona un archivo fuera de la carpeta privada.')
            identifier = uuid.uuid4().hex
            target, partial = self.root / f'{identifier}.vfv', self.root / f'{identifier}.part'
            nonce = os.urandom(12)
            metadata = json.dumps(dict(name=source.name, size=source.stat().st_size), ensure_ascii=False).encode()
            encoder = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
            encoder.authenticate_additional_data(MAGIC)
            try:
                with source.open('rb') as original, partial.open('xb') as output:
                    output.write(MAGIC + nonce)
                    output.write(encoder.update(struct.pack('>I', len(metadata)) + metadata))
                    for chunk in iter(lambda: original.read(CHUNK), b''):
                        output.write(encoder.update(chunk))
                    output.write(encoder.finalize())
                    output.write(encoder.tag)
                    output.flush()
                    os.fsync(output.fileno())
                partial.rename(target)
                return identifier
            finally:
                partial.unlink(missing_ok=True)

    def path(self, identifier):
        if not re.fullmatch('[a-f0-9]{32}', identifier):
            raise ValueError('Archivo privado no válido.')
        return self.root / f'{identifier}.vfv'

    def decrypt(self, identifier, output=None):
        with self.lock:
            key = self.require_key()
            with self.path(identifier).open('rb') as file:
                if file.read(8) != MAGIC:
                    raise ValueError('Archivo privado dañado.')
                nonce = file.read(12)
                file.seek(-16, 2)
                remaining = file.tell() - 20
                decoder = Cipher(algorithms.AES(key), modes.GCM(nonce, file.read(16))).decryptor()
                decoder.authenticate_additional_data(MAGIC)
                file.seek(20)
                length = struct.unpack('>I', decoder.update(file.read(4)))[0]
                if not 0 < length < 8192:
                    raise ValueError('Metadatos privados dañados.')
                metadata = json.loads(decoder.update(file.read(length)))
                remaining -= 4 + length
                while remaining > 0:
                    block = file.read(min(CHUNK, remaining))
                    if not block:
                        raise ValueError('Archivo privado incompleto.')
                    remaining -= len(block)
                    plain = decoder.update(block)
                    if output:
                        output.write(plain)
                decoder.finalize()  # Authenticate all data before export becomes visible.
                return metadata

    def list(self):
        # Names are encrypted separately in the index. Listing does not decrypt large videos.
        with self.lock:
            key = self.require_key()
            index = self.root / 'index.bin'
            if not index.exists():
                return []
            data = index.read_bytes()
            return json.loads(AESGCM(key).decrypt(data[:12], data[12:], MAGIC))

    def add_index(self, identifier, source):
        with self.lock:
            items = self.list()
            items.append(dict(id=identifier, name=Path(source).name, size=Path(source).stat().st_size))
            nonce = os.urandom(12)
            data = nonce + AESGCM(self.require_key()).encrypt(nonce, json.dumps(items).encode(), MAGIC)
            temporary = self.root / 'index.tmp'
            temporary.write_bytes(data)
            temporary.replace(self.root / 'index.bin')

    def export(self, identifier, target):
        target = Path(target)
        if target.exists() or self.root.resolve() in target.resolve().parents:
            raise ValueError('Elige un nombre nuevo fuera de la carpeta privada.')
        temporary = target.parent / f'.{uuid.uuid4().hex}.vault-export'
        try:
            with temporary.open('xb') as output:
                self.decrypt(identifier, output)
            temporary.rename(target)
        finally:
            temporary.unlink(missing_ok=True)


def register(app, data_dir):
    from flask import request, jsonify
    from desktop_dialogs import choose
    vault = Vault(data_dir / 'vault')

    @app.get('/api/vault')
    def vault_status():
        status = vault.status()
        return jsonify(ok=True, **status)

    @app.post('/api/vault/<action>')
    def vault_action(action):
        try:
            data = request.get_json(silent=True) or {}
            if action == 'unlock':
                vault.unlock(data.get('pin'))
                return jsonify(ok=True, files=vault.list())
            if action == 'lock':
                vault.close()
            elif action == 'import':
                with vault.lock:
                    vault.require_key()
                paths = choose('OPEN', '', allow_multiple=True)
                added, errors = [], []
                for path in paths:
                    try:
                        identifier = vault.protect(path)
                        vault.add_index(identifier, path)
                        added.append(identifier)
                    except Exception as exc:
                        errors.append(f'{Path(path).name}: {exc}')
                return jsonify(ok=True, added=len(added), errors=errors, files=vault.list())
            elif action == 'export':
                with vault.lock:
                    items = vault.list()
                item = next((item for item in items if item['id'] == data.get('id')), None)
                if not item:
                    raise ValueError('Archivo privado no encontrado.')
                paths = choose('SAVE', '', filename=Path(item['name']).name)
                if paths:
                    vault.export(item['id'], paths[0])
                return jsonify(ok=True, cancelled=not paths)
            elif action != 'lock':
                raise ValueError('Acción privada no válida.')
            return jsonify(ok=True)
        except Exception as exc:
            return jsonify(ok=False, error=str(exc) or 'No se pudo abrir el archivo privado.'), 400
    return vault
