"""Application-level TOTP and single-use recovery codes.

All verifiers are stored inside the authenticated, encrypted vault envelope.
Recovery codes bypass TOTP only; the master passphrase is still required to decrypt.
This does not prevent offline password guessing against a stolen vault.
"""
from __future__ import annotations
import copy
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from .totp import matching_counter

RECOVERY_COUNT = 10
RECOVERY_BYTES = 15  # 120 bits; randomly generated, not based on a memorable phrase.


def _normalise(code: str) -> str:
    if not isinstance(code, str):
        return ''
    code = code.strip().upper().replace(' ', '').replace('-', '')
    if code.startswith('AEGIS'):
        code = code[5:]
    return code


def recovery_digest(code: str) -> str:
    value = _normalise(code)
    if len(value) != 24 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567' for c in value):
        raise ValueError('Invalid recovery-code format.')
    return hashlib.sha256(b'AEGIS-RECOVERY-v1\0' + value.encode('ascii')).hexdigest()


def generate_recovery_codes() -> tuple[list[str], list[str]]:
    """Return one-time display codes and matching SHA-256 verifiers.

    A fast digest is acceptable here only because each code has 120 bits of
    CSPRNG entropy. This is NOT a password hashing function.
    """
    import base64
    codes: list[str] = []
    for _ in range(RECOVERY_COUNT):
        base = base64.b32encode(secrets.token_bytes(RECOVERY_BYTES)).decode('ascii').rstrip('=')
        codes.append('AEGIS-' + '-'.join(base[i:i+4] for i in range(0, 24, 4)))
    return codes, [recovery_digest(c) for c in codes]


@dataclass(frozen=True)
class Enrolment:
    updated: dict
    recovery_codes: list[str]


def enrol_totp(data: dict, secret: str, code: str, at: int | None = None) -> Enrolment:
    """Enrol only after validating the authenticator's first live code."""
    if data.get('totp_secret'):
        raise ValueError('Authenticator is already enabled.')
    counter = matching_counter(secret, code, at)
    if counter is None:
        raise ValueError('Authenticator code could not be verified.')
    codes, digests = generate_recovery_codes()
    updated = copy.deepcopy(data)
    updated['totp_secret'] = secret
    updated['recovery_hashes'] = digests
    updated['totp_last_counter'] = counter
    return Enrolment(updated, codes)


def verify_second_step(data: dict, supplied: str, at: int | None = None) -> tuple[dict, str]:
    """Validate a TOTP or single-use recovery code and return amended vault data.

    Caller MUST atomically persist the amended data BEFORE granting access.
    Replayed TOTPs are rejected even if within their original time window.
    """
    secret = data.get('totp_secret')
    if not secret:
        raise ValueError('Authenticator is not enabled.')
    counter = matching_counter(secret, supplied.strip(), at)
    if counter is not None:
        if counter <= data.get('totp_last_counter', -1):
            raise ValueError('Code already used. Wait for a new code.')
        updated = copy.deepcopy(data)
        updated['totp_last_counter'] = counter
        return updated, 'totp'
    try:
        digest = recovery_digest(supplied)
    except ValueError:
        raise ValueError('Incorrect authenticator or recovery code.') from None
    hashes = data.get('recovery_hashes', [])
    match = next((i for i, stored in enumerate(hashes) if hmac.compare_digest(stored, digest)), -1)
    if match < 0:
        raise ValueError('Incorrect authenticator or recovery code.')
    updated = copy.deepcopy(data)
    del updated['recovery_hashes'][match]
    return updated, 'recovery'


def remaining_recovery_codes(data: dict) -> int:
    return len(data.get('recovery_hashes', []))


def rotate_recovery_codes(data: dict) -> Enrolment:
    """For an already unlocked and reauthenticated vault; old codes become invalid."""
    if not data.get('totp_secret'):
        raise ValueError('Enable an authenticator first.')
    codes, hashes = generate_recovery_codes()
    updated = copy.deepcopy(data)
    updated['recovery_hashes'] = hashes
    return Enrolment(updated, codes)


def validate_new_master(master: str, confirmation: str) -> None:
    if master != confirmation:
        raise ValueError('Master passwords do not match.')
    if len(master) < 12:
        raise ValueError('Choose a master passphrase of at least 12 characters.')
    if master.isspace() or not master.strip():
        raise ValueError('Master passphrase cannot be blank.')
