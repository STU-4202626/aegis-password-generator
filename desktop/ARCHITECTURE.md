# AEGIS v0.3.7 | Architecture

## Components

`run.py` launches `aegis.gui.Aegis` (PySide6 desktop). `aegis.wizard.FirstRunWizard` is a separate Qt `QWizard` shown when no encrypted vault exists. `aegis.onboarding.next_page` centralises routing so both skipping and verifying authenticator converge on the final Ready page. `aegis.onboarding.prepare_first_vault` independently checks the final state before committing an encrypted vault. It validates the master-passphrase confirmation, optionally enrols TOTP and forces the user to acknowledge viewing all single-use recovery codes before a vault file is written. `aegis.security` implements account-specific deterministic password generation. `aegis.vault` stores an encrypted JSON envelope. `aegis.auth` implements recovery enrolment, code verification and rotation, and `aegis.totp` implements RFC6238 HMAC-SHA1 6-digit time codes.

## Data and trust boundaries

```
Memorable phrase + account + length + revision + private vault secret
                           |
                    PBKDF2 / HMAC
                           |
                 Account-specific password
                           |
             Copy or deliberate plaintext export

Master passphrase --Argon2id--> AES-256-GCM key
                          |             |
                          v             v
                 Encrypted local vault (`vault.aegis`)
                 [random private secret, account settings,
                  TOTP secret, recovery-code hashes, last accepted counter]
                          |
                  Authenticator OR recovery code
                          |
       verify + persist consumed-code state BEFORE GUI unlock
```

Sensitive inputs and derived plaintext are handled locally and are not transmitted over the network by the app. The user is responsible for safe backups. The application does not save memorable phrases or derived account passwords in the vault by default.

### Recovery workflow

- Ten Base32 recovery codes of 120 random bits each, generated using OS-backed CSPRNG.
- Vault stores purpose-separated SHA-256 verifiers, not the original codes. Codes remain subject to the encryption of the vault file.
- Login prompts for master passphrase first. Once AES-GCM decrypts and authenticates the vault, an app-level challenge accepts a fresh RFC6238 code OR an unconsumed recovery code.
- Accepted TOTP counter or recovered-code consumption is persisted using a fresh AES-GCM nonce and vault salt before access is granted. Save failure refuses access (fail closed).
- Recovery kit rotation requires vault unlock, master-passphrase reauthentication and an accepted second-step code, then replaces the whole set of hashes. Old codes become invalid.

**Important:** This design does not cryptographically require a TOTP secret to derive the AES encryption key. A thief with vault bytes can attempt to crack the master passphrase offline regardless of TOTP, and can potentially bypass the GUI check with a modified client. Codes help recover from *lost phone* only, not from *lost master password*. A GUI-level single-instance guard helps avoid two AEGIS processes writing the same vault. It does not prevent external modifications or rollback to an older backup.

### Updates and fault tolerance

Vault updates create a fresh encrypted envelope and write to an owner-restricted temporary file, flush and fsync, then use an atomic rename in the local vault directory. The UI changes its in-memory state only after successful persistence for account edits, code consumption and rotation. Failure during replacement leaves the previous file in place (verified by test), but durable file replacement still depends on local filesystem guarantees. `AEGIS_DATA_DIR` is supported for test isolation; the app avoids chmod of arbitrary custom override directory.

### Security controls and open risks

- HMAC with length-delimited site identity and deterministic character sampling is **not** a formal proof that the generated passwords have their apparent strength.
- The password-derivation format (`aegis-derive-v1`) is explicitly versioned. Compatibility tests and migration strategy are essential before relying on it for long-lived accounts.
- Password Version (the on-disk `revision` field) increments produce intentionally different passwords; changing a memorable phrase, length, secret or algorithm does likewise.
- App-level 5-minute idle lock and 20-second clipboard clearing are convenience controls, not OS security boundaries.
- The GUI must be inspected using a real PySide6 installation and on each supported OS. No production security claims are made.
- A release also requires OS-specific installation tests, recovery and restore checks, and security review.

See `SECURITY_TEST_REPORT.md` for verified tests, unverified acceptance criteria and release blockers.

## v0.3 UI and authorization invariants

- Unlock second-step dialog branches between explicit **TOTP** and **recovery** tabs; both feed the **same** existing `verify_second_step()` backend. A valid code must be recorded via `write_vault()` before opening the vault UI.
- Generator *version rotation* creates a candidate but never persists a new version until the user selects **Save account**. If a saved version changes, a separate website-update confirmation appears. This is a UI safety constraint; AEGIS cannot verify that an external account was actually updated.
- When **changing TOTP**, master-password reauthentication and existing second-step authorization come first. Accepted second-step authorization is persisted before QR/confirmation. Only verified new enrolment plus recovery acknowledgement causes the old TOTP and hashes to be replaced in a single encrypted write.
- When **rotating recovery codes**, successful authorization is persisted first, before new codes are presented; canceling presentation leaves the old kit (minus the consumed authorizing code) intact.
- Saved Accounts search stores the underlying account identifier as `Qt.UserRole`, so a filtered row cannot accidentally load or delete a different account by its old row index.
- A direct attacker with the encrypted vault can still attack the master password offline. The implementation has no independent security certification. The GUI has a single-instance guard and a verified in-app backup restore workflow, but rollback and external writes remain possible.


## v0.3.1 UI and encrypted snapshot update

- `setup_complete_message` is defined in `aegis.onboarding` and imported by `aegis.gui` and never conflates authenticator recovery codes with an encrypted vault backup.
- `aegis.vault.export_encrypted_backup` authenticates the source encrypted vault with the provided master passphrase, then creates a new encrypted snapshot without overwriting existing files or writing plaintext. It **does not perform recovery**. Restoring old snapshots can revive old single-use verifier state; anti-rollback protections are not implemented.
- The generator's `QSpinBox` objects remain intact but have a custom `rounded_number_control` wrapper with `NoButtons` and two rounded accessible buttons.
- `CleanSelectionDelegate` masks `QStyle.State_HasFocus` only for drawing list items, preserving Qt keyboard focus and selection state.


## v0.3.3 restore and single-GUI-instance flow

- `vault.restore_encrypted_backup` authenticates the backup's encrypted envelope with its master passphrase **before** touching the live vault.
- If an active vault exists, it writes an exclusive-create `vault.pre-restore-*` encrypted snapshot. The selected encrypted bytes are staged to an owner-only temporary file, fsynced and atomically installed through `os.replace`. Failure leaves the previous active vault in place if replacement was not committed.
- Restoring does not unlock or update the in-memory state; the UI invokes it only from the locked state and then requires a fresh unlock.
- The main GUI entry point owns a `QLockFile` in the vault directory for its process lifetime, discouraging accidental concurrent app edits. Backend tests operate on isolated temporary paths.
- **Threat model limitation:** The pre-restore snapshot and restored backup can contain old authentication state, so a restore intentionally rewinds recovery-code and TOTP replay metadata. The app does not have an anti-rollback trusted counter.


## v0.3.7 password-entry usability

The memorable phrase input is a masked QLineEdit with a 42 × 38 px child QToolButton carrying a locally drawn Qt eye icon. Its position is recalculated when the input resizes: it stays vertically centred and 12 px inside the right border. A 56 px text margin prevents typed content from flowing beneath the button. The click handler switches only between masked and visible text, without saving or logging the phrase. Locking the vault and loading saved account settings reset the editor to masked mode. The optional Windows Caps Lock hint checks the toggle state through the local OS on key/focus events. Navigation tab borders now use equal 2 px widths in active, inactive and focus states, with extra layout inset to prevent clipping at high display scaling.
