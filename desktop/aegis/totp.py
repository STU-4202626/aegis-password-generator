"""RFC 6238 SHA-1 TOTP, compatible with standard authenticator apps."""
import base64
import hashlib
import hmac
import os
import struct
import time
from urllib.parse import urlencode


def create_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode('ascii').strip('=')


def current_code(secret: str, at: int | None = None) -> str:
    raw = base64.b32decode(secret + '=' * ((-len(secret)) % 8))
    counter = (int(time.time()) if at is None else at) // 30
    digest = hmac.new(raw, struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff
    return f'{value % 1_000_000:06d}'


def matching_counter(secret: str, code: str, at: int | None = None) -> int | None:
    """Return the matched RFC 6238 30-second time counter, including ±1 window."""
    if not (isinstance(code, str) and len(code) == 6 and code.isascii() and code.isdecimal()):
        return None
    now = int(time.time()) if at is None else at
    for offset in (-1, 0, 1):
        when = now + offset * 30
        if hmac.compare_digest(current_code(secret, when), code):
            return when // 30
    return None


def verify_code(secret: str, code: str, at: int | None = None) -> bool:
    return matching_counter(secret, code, at) is not None


def provisioning_uri(secret: str, user: str = 'Local Vault') -> str:
    label = f'AEGIS:{user}'
    return 'otpauth://totp/' + __import__('urllib.parse', fromlist=['quote']).quote(label) + '?' + urlencode(
        {'secret': secret, 'issuer': 'AEGIS', 'algorithm': 'SHA1', 'digits': 6, 'period': 30})
