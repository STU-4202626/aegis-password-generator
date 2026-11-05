# AEGIS

A private desktop password studio for Windows, macOS and Linux, built in Python with PySide6.

Create an account-specific password from a memorable phrase. Save account settings to your encrypted local vault, then generate the same password again when needed.

A **memorable phrase** is a long, unique sentence or combination of words you can recall. For example, `Blue lanterns glow beside my river` shows the idea, but make up your own phrase rather than using a published example. The app combines your phrase, account details and a private vault secret to produce a longer password. It does not store the phrase.

## What you can do

- **Password Studio:** create repeatable passwords for separate accounts, with adjustable length and Password Version. Use the eye icon inside Memorable phrase to check your typing. On Windows, a Caps Lock hint appears when you type with Caps Lock enabled.
- **Saved Accounts:** search, load and remove account settings. Your memorable phrases and generated passwords are not saved there.
- **Security Centre:** add an authenticator, use single-use recovery codes, and back up or restore your encrypted vault.
- **Automatic lock:** AEGIS locks the interface after five minutes without activity.

## Run AEGIS

Install Python 3.11 or newer, then run from this folder:

```powershell
python -m pip install -r requirements.txt
python run.py
```

Your vault is stored in your user data folder, outside the AEGIS source directory. Existing AEGIS v0.3.x vaults remain compatible.

### Windows installer

`build-installer.cmd` runs the Windows packaging script and, with Inno Setup 6.3+ installed, builds a setup installer. This source ZIP is **not** a compiled installer. See [packaging/README.md](packaging/README.md).

## First time using AEGIS

1. Create a long, unique master passphrase. You need it to open the encrypted vault.
2. Optionally connect an authenticator app such as Google or Microsoft Authenticator.
3. If you enable it, save the ten single-use recovery codes somewhere private.
4. Open Password Studio and choose an account name, memorable phrase, length and Password Version.
5. Save account settings. For a new version, update the password on the website before saving that version in AEGIS.

## Backups, recovery and forgotten passphrases

**Back up vault** creates a separate encrypted `.aegis` file. **Restore from backup** checks that file before replacing the current vault and saves a safety copy of the prior encrypted vault. Restoring an older file also restores older account settings and authenticator state.

A **recovery code** substitutes for the phone's code if you lose access to your authenticator. It does not substitute for your master passphrase. A backup cannot be decrypted without the master passphrase that was used to create it.

There is no password-reset service or hidden master key. **Forgot master passphrase?** on the login screen explains the available options. If you cannot recall the master passphrase for the active vault or any available backup, the encrypted data cannot be recovered by AEGIS.

## Security information

AEGIS uses Argon2id and AES-256-GCM to encrypt the local vault. Password derivation uses a versioned PBKDF2/HMAC method with a private vault secret and account-specific context. Changing Password Version produces a different derived password; it does not update a website automatically.

Authenticator verification is an **application-level** access check. It does not add a second key component to vault encryption. Restoring an older backup can revive previously used authenticator and recovery-code state. The software has not had an independent security assessment. Functional tests and a working interface alone do not establish security for sensitive use.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [SECURITY_TEST_REPORT.md](SECURITY_TEST_REPORT.md) for design details, security limitations and testing.

## Development checks

```powershell
python -m unittest discover -s tests -v
```

GUI checks require PySide6. Before distribution, validate the installer and the application on each supported operating system. Never include your personal `.aegis` vault or recovery codes in source control or distribution packages.

## Release readiness

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the tasks remaining before public distribution.

## v0.3.9 Windows installer builder

Double-click `build-installer.cmd` after installing Inno Setup 6.3+ on a 64-bit Windows build PC. The generated `installer-output/AEGIS-Setup-0.3.9-Windows-x64.exe` includes the Python runtime and dependencies. End users do not install Python. Read [BUILD_WINDOWS.md](BUILD_WINDOWS.md) for instructions and testing limits. The ZIP contains builder source, not a precompiled installer.

## v0.3.7 visual updates

The memorable-phrase field has a larger, inset, vertically centred show/hide eye button. It is masked by default and returns to masked mode when AEGIS locks or another saved account is loaded. Navigation buttons have uniform, fully inset borders. Neither feature changes how passwords are derived or how the vault is encrypted.

### Windows build tests

The default Windows installer builder gates on backend and packaging tests.
Qt integration tests are a separate diagnostic run because some Windows Qt
runtimes report a native shutdown crash after unittest displays `OK`. A
standalone installer must still be smoke-tested and reviewed before release.
See `BUILD_WINDOWS.md` for instructions.

