# AEGIS Web Edition v0.1.0: test report

**JavaScript engine:** 8 reference cases created by desktop Python `aegis.security.generate_password()` passed byte-for-byte with Node.js v22 Web Crypto. Repeated derivation, required character groups, minimum and maximum lengths, Unicode, account variations and version changes passed. Invalid inputs were rejected.

**Source integrity:** the single-file HTML contains the same JavaScript and CSS bytes as the separated source files. `node --check` passed on both JavaScript modules. Python fixture regeneration passed for all cases.

**Interface:** Chromium DOM checks passed for desktop and mobile viewport widths: sample loading, memorable-phrase eye visibility, help disclosure, version increment, stale-result clearing and layout without horizontal overflow. No JavaScript page errors were observed in those checks.

**Environment limit:** automated Chromium navigation to both local `file://` and `localhost` URLs was blocked by its managed browser policy; a `page.set_content` DOM test was used instead. That environment does not expose `crypto.subtle` to an opaque `about:blank` origin. Thus a full browser cryptography click-through test was **not** completed here. The derivation engine was independently tested against Python using Node.js Web Crypto. Please verify the real browser flow in Edge or Chrome on Windows before considering it validated on that platform.

**Not tested:** desktop `.aegis` vault import, Argon2id decryption, account persistence and TOTP. These are not Web Edition features. The complete app is not independently security audited.
