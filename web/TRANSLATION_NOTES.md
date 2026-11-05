# Translation verification notes

Source: `AEGIS_v0.3.9_Installer_Test_Fix/aegis/security.py`.
Target: `web/engine.js` using standard browser `crypto.subtle`, `TextEncoder`, `Uint8Array` and `DataView`.

| Python construct | JavaScript equivalent |
|---|---|
| `hashlib.pbkdf2_hmac('sha256', ..., 310_000)` | `crypto.subtle.deriveBits({name:'PBKDF2', hash:'SHA-256', iterations:310000}, ...)` |
| `hmac.new(key, message, hashlib.sha256).digest()` | `crypto.subtle.sign('HMAC', importedKey, message)` |
| `int.to_bytes(4, 'big')` | `DataView.setUint32(..., false)` |
| `int.to_bytes(8, 'big')` | `DataView.setBigUint64(..., false)` |
| Rejection sampling | Same byte threshold and first-eligible-byte selection |
| Fisher–Yates shuffle | Same descending index order, HMAC counter and 32-bit rejection rule |
| Python `account.strip().lower()` | JavaScript `account.trim().toLowerCase()` (Unicode edge cases can differ between implementations) |

Note: The `private_secret` isn't the memorable phrase or vault master passphrase. It is the separate random key kept inside the encrypted desktop vault. The web translation uses local test keys and a fresh random session key; it does **not** expose or extract live vault keys.

To prove parity, run `node tests/test_password_parity.cjs` and compare all expected outputs against Python-generated `tests/python_vectors.json`.
