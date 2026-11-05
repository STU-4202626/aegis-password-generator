# AEGIS Web Edition v0.1.0

A browser-based translation of AEGIS's Python password generator, using HTML, CSS, and JavaScript. Runs without external libraries or an internet connection.

## Run the app

**Easiest:** double-click `AEGIS_Web_Edition.html` and open it in Microsoft Edge, Chrome, or another modern browser. All code is inside that one file.

**Separated source:** open `web/index.html` in a browser. Its scripts and stylesheet are included in the same `web` folder. If the browser restricts Web Crypto for local files, serve the folder on localhost with `python -m http.server 8000 --directory web` and open `http://localhost:8000`. No server is needed for password generation; localhost only serves static files.

## What it does

Enter an account, memorable phrase, password length (12–128), and version (1–999999), then select **Generate password**. Use **Copy password** or **Save .txt** as needed. Use the eye button to inspect the phrase. Use **Try an example** to load a known test phrase and a *public test key*.

The web version creates a random 32-byte session key in your browser tab. The key is **not stored automatically**. If you close or refresh the page and lose it, you cannot recreate the same passwords. Save your key securely if you intend to use the web version again, and never send it to anyone. You can paste an existing *test* key and select **Use entered key** to compare against Python.

**The Web Edition does not unlock, decrypt, or import the desktop `.aegis` vault.** It does not implement desktop backup, authenticator, or saved-account functionality. It translates the **password generator**, not the entire desktop vault system. Matching outputs require the same private secret bytes; knowing only a memorable phrase and account is insufficient. Do not enter the private key from a live desktop vault into an untrusted website.

## Security and data handling

- Password generation runs locally in the browser with Web Crypto APIs (PBKDF2-HMAC-SHA256 and HMAC-SHA256).
- The web app makes no network requests, uses no remote dependencies, does not use browser localStorage/cookies, and does not save the memorable phrase.
- The new session key is lost on refresh unless you save it securely outside the app.
- **Save .txt creates an unencrypted password file** and asks for confirmation.
- The browser clipboard may retain copied secrets after you leave the page.
- The desktop vault uses Argon2id and AES-256-GCM; vault encryption and TOTP are **not** part of this web translation.
- This educational translation has not undergone an independent security audit. Don't publish live private keys, phrases or vault backups in demonstrations, screenshots or version-control repositories.

## Verify that it matches Python

A Python reference file is included at `references/python_security_reference.py` and Python-generated test vectors are at `tests/python_vectors.json`. Run:

```powershell
node tests/test_password_parity.cjs
```

Eight test cases cover the minimum/maximum lengths, phrase Unicode, account casing and whitespace, version changes, different accounts and punctuation. JavaScript must match every Python expected output byte for byte.

## Where the code is

| File | Function |
|---|---|
| `AEGIS_Web_Edition.html` | Single-file offline application. |
| `web/index.html` | Browser interface. |
| `web/styles.css` | AEGIS dark theme and responsive layout. |
| `web/engine.js` | JavaScript password derivation, faithfully translated from `aegis/security.py`. |
| `web/app.js` | Interface actions and form validation. |
| `tests/python_vectors.json` | Reference outputs generated with Python v0.3.9. |
| `tests/test_password_parity.cjs` | Cross-language and validation tests. |
| `references/python_security_reference.py` | Python reference algorithm, unchanged. |

## Design notes: exact algorithm translation

Both languages use: UTF-8 encoding → a length-delimited domain-separated salt → 310,000 iterations of PBKDF2-HMAC-SHA256 → HMAC-SHA256 output seed → rejection sampling that guarantees upper/lower/digit/symbol coverage → deterministic Fisher–Yates shuffle. The counter is a big-endian unsigned 64-bit integer and shuffle samples are 32-bit big-endian values. The algorithm version identifier is `aegis-derive-v1`.

The desktop software also has features beyond derivation (an encrypted vault and account records). This deliverable deliberately focuses on the directly comparable password-generator logic, rather than claiming a non-existent web vault implementation.
