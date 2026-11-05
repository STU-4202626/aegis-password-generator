# Security notes

AEGIS is a source-available password generation project. It has **not** received an independent security audit or penetration test. Passing functional tests does not guarantee that it is safe for important real-world credentials.

## Protect your data

- Do not open issues or pull requests containing private generation keys, master passphrases, TOTP enrolment codes, recovery codes, `.aegis` vault files or exported passwords.
- Never commit encrypted backups or private accounts to a Git repository. Git history can retain deleted secrets.
- The Web Edition uses an ephemeral browser key, **not** the desktop's encrypted vault. It will produce the same password only when all inputs, including the private key, match exactly.
- `Save .txt` and plaintext clipboard operations may expose a password to other programs.

## Design caveats

- TOTP checks are applied in the desktop application, not as a second cryptographic component of the vault encryption key.
- Restoring an old encrypted backup can restore previously consumed recovery-code and TOTP-counter state (rollback risk).
- Forgotten master passphrases cannot be reset by a recovery code.
- A Qt-based integration test process has previously reported a Windows native exit error after its tests completed; this needs investigation before a wider release.
- The algorithm uses a custom deterministic password-composition step. No proof of password entropy is claimed.

For a technical discussion, see [desktop/ARCHITECTURE.md](desktop/ARCHITECTURE.md), [desktop/SECURITY_TEST_REPORT.md](desktop/SECURITY_TEST_REPORT.md) and [desktop/RELEASE_CHECKLIST.md](desktop/RELEASE_CHECKLIST.md).

## Reporting a vulnerability

Please avoid publicly posting exploit details or private security material. Contact the repository owner privately through a supported GitHub private security-reporting channel if enabled.
