"""Versioned, deterministic password derivation. No external cryptography dependency."""
from __future__ import annotations
import hashlib
import hmac
import string

UPPER = string.ascii_uppercase
LOWER = string.ascii_lowercase
DIGITS = string.digits
SYMBOLS = '!@#$%^&*()-_=+[]{};:,.?'
GROUPS = (UPPER, LOWER, DIGITS, SYMBOLS)
ALPHABET = ''.join(GROUPS)
VERSION = 'aegis-derive-v1'


def _sample(seed: bytes, alphabet: str, counter: list[int]) -> str:
    """Select a character without modulo bias using HMAC-SHA256 rejection sampling."""
    n = len(alphabet)
    limit = 256 - (256 % n)
    while True:
        block = hmac.new(seed, counter[0].to_bytes(8, 'big'), hashlib.sha256).digest()
        counter[0] += 1
        for byte in block:
            if byte < limit:
                return alphabet[byte % n]


def generate_password(memorable: str, account: str, length: int, private_secret: bytes,
                      revision: int = 1) -> str:
    """Regenerate a site-specific password. Same inputs always produce same result.

    This is a personal/academic prototype, not an independently audited password manager.
    The private_secret is random, persisted only inside the encrypted vault.
    """
    if not isinstance(memorable, str) or len(memorable) < 1:
        raise ValueError('Enter a memorable phrase.')
    if not account or not account.strip():
        raise ValueError('Enter an account or website identifier.')
    if not isinstance(length, int) or not 12 <= length <= 128:
        raise ValueError('Password length must be between 12 and 128.')
    if not isinstance(private_secret, bytes) or len(private_secret) < 32:
        raise ValueError('A valid, private 32-byte vault secret is required.')
    if not isinstance(revision, int) or not 1 <= revision <= 999999:
        raise ValueError('Revision must be a positive integer.')
    # Delimited domain separation prevents ambiguous concatenations.
    identifier = account.strip().lower().encode('utf-8')
    context = (VERSION.encode() + b'\0' + len(identifier).to_bytes(4, 'big') +
               identifier + revision.to_bytes(4, 'big'))
    material = hashlib.pbkdf2_hmac('sha256', memorable.encode('utf-8'),
                                  private_secret + context, 310_000, dklen=32)
    seed = hmac.new(material, b'aegis-output-v1', hashlib.sha256).digest()
    counter = [0]
    # Ensure character-class coverage without replacing already generated characters.
    chars = [_sample(seed, group, counter) for group in GROUPS]
    chars.extend(_sample(seed, ALPHABET, counter) for _ in range(length - len(chars)))
    # Deterministic Fisher-Yates, using PRF bytes. Do not claim ideal random entropy.
    for i in range(len(chars)-1, 0, -1):
        # Uniform index via rejection on 32-bit integers.
        limit = 2**32 - (2**32 % (i + 1))
        while True:
            digest = hmac.new(seed, b'shuffle' + counter[0].to_bytes(8, 'big'), hashlib.sha256).digest()
            counter[0] += 1
            value = int.from_bytes(digest[:4], 'big')
            if value < limit:
                break
        j = value % (i+1)
        chars[i], chars[j] = chars[j], chars[i]
    return ''.join(chars)
