"""Local encrypted JSON envelope. Vault data is never written in plaintext."""
from __future__ import annotations
import base64
import json
import os
import tempfile
from pathlib import Path
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

FORMAT = 1
KDF_TIME = 3
KDF_MEMORY_KIB = 65536
KDF_PARALLELISM = 2


def app_data_path() -> Path:
    """Portable default for Windows, macOS and Linux, overridable for testing."""
    override = os.environ.get('AEGIS_DATA_DIR')
    if override:
        return Path(override).expanduser() / 'vault.aegis'
    if os.name == 'nt':
        root = Path(os.environ.get('APPDATA', str(Path.home())))
    elif __import__('sys').platform == 'darwin':
        root = Path.home() / 'Library' / 'Application Support'
    else:
        root = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share')))
    return root / 'AEGIS' / 'vault.aegis'


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def _unb64(data: str) -> bytes:
    return base64.b64decode(data, validate=True)


def _derive(master: str, salt: bytes) -> bytes:
    if len(master) < 12:
        raise ValueError('Master password must contain at least 12 characters.')
    return hash_secret_raw(master.encode('utf-8'), salt, time_cost=KDF_TIME,
                           memory_cost=KDF_MEMORY_KIB, parallelism=KDF_PARALLELISM,
                           hash_len=32, type=Type.ID)


def new_data() -> dict:
    return {'secret': _b64(os.urandom(32)), 'entries': [], 'totp_secret': None,
            'recovery_hashes': [], 'totp_last_counter': -1,
            'settings': {'auto_lock_minutes': 5}}


def encrypt_data(data: dict, master: str) -> bytes:
    salt, nonce = os.urandom(16), os.urandom(12)
    key = _derive(master, salt)
    aad = b'AEGIS-VAULT-1'
    ciphertext = AESGCM(key).encrypt(nonce, json.dumps(data, separators=(',', ':')).encode(), aad)
    envelope = {'format': FORMAT, 'kdf': 'argon2id', 'time': KDF_TIME,
                'memory_kib': KDF_MEMORY_KIB, 'parallelism': KDF_PARALLELISM,
                'salt': _b64(salt), 'nonce': _b64(nonce), 'ciphertext': _b64(ciphertext)}
    return json.dumps(envelope, indent=2).encode('utf-8')


def decrypt_data(blob: bytes, master: str) -> dict:
    try:
        env = json.loads(blob)
        if env.get('format') != FORMAT or env.get('kdf') != 'argon2id':
            raise ValueError('Unsupported vault format.')
        # Never obey untrusted file-supplied KDF costs.
        if (env.get('time'), env.get('memory_kib'), env.get('parallelism')) != (KDF_TIME, KDF_MEMORY_KIB, KDF_PARALLELISM):
            raise ValueError('Unsupported KDF configuration.')
        salt, nonce = _unb64(env['salt']), _unb64(env['nonce'])
        if len(salt) != 16 or len(nonce) != 12:
            raise ValueError('Malformed vault header.')
        key = _derive(master, salt)
        plain = AESGCM(key).decrypt(nonce, _unb64(env['ciphertext']), b'AEGIS-VAULT-1')
        data = json.loads(plain)
        if not isinstance(data, dict) or not isinstance(data.get('entries'), list) or len(_unb64(data['secret'])) != 32:
            raise ValueError('Malformed decrypted vault.')
        # v0.1 vault migration: old files have no recovery-code metadata.
        data.setdefault('recovery_hashes', [])
        data.setdefault('totp_last_counter', -1)
        if not isinstance(data['recovery_hashes'], list):
            raise ValueError('Malformed recovery data.')
        return data
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError('Vault is corrupt or unsupported.') from exc


def write_vault(path: Path, data: dict, master: str) -> None:
    blob = encrypt_data(data, master)
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    # Only tighten permissions on AEGIS's own application directory.
    # Do NOT chmod an arbitrary AEGIS_DATA_DIR override supplied by the user.
    if os.name != 'nt' and not os.environ.get('AEGIS_DATA_DIR') and path.parent.name == 'AEGIS':
        os.chmod(path.parent, 0o700)
    fd, temporary = tempfile.mkstemp(prefix='.aegis-', dir=path.parent)
    try:
        if os.name != 'nt':
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as file:
            file.write(blob)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        if os.name != 'nt':
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_vault(path: Path, master: str) -> dict:
    return decrypt_data(path.read_bytes(), master)


def vault_secret(data: dict) -> bytes:
    return _unb64(data['secret'])


def export_encrypted_backup(source: Path, destination: Path, master: str) -> None:
    """Safely export an authenticated encrypted-vault snapshot to a NEW file.

    Validates the source with the master passphrase; does not reveal plaintext,
    mutate its contents, or overwrite existing backups. No restore is performed.
    Open AEGIS only once per vault until concurrency protection is implemented.
    """
    source = Path(source)
    destination = Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Backup must be a different file from the active vault.')
    if destination.exists():
        raise FileExistsError(f'Backup already exists: {destination.name}')
    blob = source.read_bytes()
    try:
        decrypt_data(blob, master)  # Reject corruption or an incorrect passphrase.
    except InvalidTag as exc:
        raise ValueError('Encrypted source vault cannot be authenticated with this master passphrase.') from exc
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(destination, flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(blob)
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        # A partial file must not be misidentified as a usable backup.
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise


# Backups and restores are manual operations. Never interpret a recovery code
# as a decryption key: only the backup's master passphrase unlocks its data.
MAX_RESTORE_BYTES = 25 * 1024 * 1024


def restore_encrypted_backup(source: Path, active: Path, backup_master: str) -> Path | None:
    """Verify an encrypted backup and atomically replace the active vault.

    Save a distinct encrypted pre-restore safety snapshot if an active vault
    exists. Returns the safety snapshot path (or None for a new installation).
    Caller must ensure no other AEGIS process is accessing the vault; the GUI
    holds a QLockFile for its entire lifetime. Older snapshots can restore
    previously used TOTP or recovery codes (local rollback is not prevented).
    """
    from datetime import datetime, timezone
    import secrets
    source, active = Path(source), Path(active)
    if active.is_symlink():
        raise ValueError('The active vault path must not be a symbolic link.')
    if not source.is_file() or source.is_symlink():
        raise ValueError('Select a regular encrypted AEGIS backup file.')
    if source.resolve() == active.resolve():
        raise ValueError('Select a backup file, not the active AEGIS vault.')
    if source.stat().st_size > MAX_RESTORE_BYTES:
        raise ValueError('The selected backup exceeds the allowed file size.')
    blob = source.read_bytes()
    if not blob or len(blob) > MAX_RESTORE_BYTES:
        raise ValueError('The selected backup is empty or too large.')
    try:
        decrypt_data(blob, backup_master)  # Validate AEAD authentication and schema first.
    except InvalidTag as exc:
        raise ValueError('Incorrect backup master passphrase or unauthentic backup.') from exc

    original = active.read_bytes() if active.exists() else None
    active.parent.mkdir(parents=True, exist_ok=True)
    safety_path = None
    if original is not None:
        from datetime import datetime, timezone
        label = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        safety_path = active.with_name(
            f'vault.pre-restore-{label}-{secrets.token_hex(4)}.aegis')
        _write_exclusive(safety_path, original)
    temporary = None
    try:
        # Detect an external change between the safety copy and replacement.
        # Process locking prevents other AEGIS instances, not arbitrary file edits.
        if (active.read_bytes() if active.exists() else None) != original:
            raise RuntimeError('The active vault changed during restoration. No replacement made.')
        fd, temporary = tempfile.mkstemp(prefix='.aegis-restore-', dir=active.parent)
        if os.name != 'nt':
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as target:
            target.write(blob)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, active)
        temporary = None
        if os.name != 'nt':
            _fsync_directory(active.parent)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return safety_path


def _fsync_directory(parent: Path) -> None:
    if os.name != 'nt':
        fd = os.open(str(parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _write_exclusive(destination: Path, blob: bytes) -> None:
    """Durable create-new write; refuse clobbering existing files."""
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(blob)
            target.flush()
            os.fsync(target.fileno())
        _fsync_directory(destination.parent)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
