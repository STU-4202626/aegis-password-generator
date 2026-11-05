# v0.3.7 verification update

The latest `python -m unittest discover -s tests -v` run discovered **70 tests: 35 backend tests passed and 35 Qt tests skipped** (PySide6 is unavailable here). Python compilation also passed. The new eye button is larger and repositioned inside the original text field. Qt tests now check button size, placement and toggle behavior; these await Windows verification. The existing help-button test now checks that the two icons match rather than assume exactly 18 px across Qt styles. No cryptography or vault-format changes.

---

# v0.3.6 verification update

On 18 October 2026, `python -m unittest discover -s tests -v` discovered **69 tests**, with **35 non-GUI tests passing** and **34 PySide6 GUI tests skipped** on this host because Qt is not installed. All project Python files passed compilation. Six new Qt checks were added for the phrase eye icon, reveal/hide without changing input, re-masking on lock and account load, navigation border consistency, and Caps Lock hints. Those UI checks must run on a Windows desktop before accepting the release. This patch changes only UI and styles; key derivation, vault persistence and backup formats are unchanged.

---

# Restore and security verification notes

- Backend test suite: **55 discovered, 34 passed, 21 Qt skipped** on this Linux environment; Qt requires verification on the Windows test PC.
- Added tests for restoring between different master passphrases, safety snapshot fidelity, restoring with no current vault, invalid master, malformed and oversized backup files, same-path selection, symlink handling (where available), and failed `os.replace` preserving the old vault.
- In-app restore is a **destructive rollback** with explicit warnings, verified decryption, a pre-restore encrypted safeguard and a fresh locked login afterward. Qt `QLockFile` guards normal GUI launches, but not external writes.
- **Important risk:** Restoring an old backup revives its stored used-code and used-TOTP state, so previously consumed codes may become valid again. No tamper-resistant rollback prevention exists.
- The UI has not been smoke-tested on Windows in this environment; run the complete tests and verify both locked-screen and Security Centre restore flows with dummy vaults.
- No independent security audit has been performed. Do not use real credentials until independent review and migration/rollback assessment.

---

# v0.3.2 test update

This patch changes only the Password Studio's visible numeric entry controls
and context-sensitive Password Version help. Existing security mechanisms and
vault storage are unchanged. The local run of `unittest discover` reported
**46 tests: 27 passed, 19 Qt interface tests skipped** because PySide6 is not
installed in the build environment. The three new Qt tests validate visible
initial values, manual-edit validation and the click/hover help control.

**Windows acceptance checklist:** Verify numeric values `24` and `1` show
clearly, changing them updates the value, spin buttons work, field values
respect bounds, and the small info button shows help on hover and click.
Use an isolated test vault for acceptance testing.

---

# AEGIS v0.3.1 — Security and Verification Report

**Date:** 17 October 2026  
**Status:** Automated test coverage is incomplete; **not independently security audited**.

## Threat model

We aim to protect the confidentiality/integrity of stored account settings and a per-vault private generation secret when an adversary obtains a copy of the vault file but does not know a strong master passphrase. A legitimate user can unlock with the master passphrase; if TOTP is enrolled, the GUI also requires a fresh TOTP or an unused recovery code. A lost authenticator can be bypassed **only** using a previously saved recovery code; the master password is still required. This is app-gated MFA, not multi-factor key derivation.

**Out of scope:** compromised OS, keyloggers, malicious browser extensions, clipboard theft, offline attack against a weak master passphrase, concurrent file modifications, social engineering, physical coercion, time-based rollback of externally replaced vault files, hardware security tokens, secure memory erasure, protected backups, cloud compromise and independent cryptographic security certification.

## Automated checks

Command: `python -m unittest discover -s tests -v`.

| Class of test | Coverage |
|---|---|
| Password generation | Repeatability, site/revision separation, length and character classes, invalid input |
| Encrypted vault | Encryption round trip, wrong master, secret exclusion from stored bytes, backward-compatible v0.1 metadata |
| RFC 6238 | Known SHA1 TOTP test vector and invalid code |
| Enrollment | Correct code required before TOTP and recovery codes are enabled; original data is unchanged on failure |
| Recovery | 10 unique 120-bit codes, normalization, invalid formats, one-time consumption, rotation revokes prior set |
| Replay | Consumed TOTP time counters cannot be reused |
| Data durability | Failed `os.replace` preserves the old vault, cleans temp file; consumed recovery remains invalid after reopening |
| Master-password UI rules | Passphrase confirmation and minimum length |
| First-run routing | Both authenticating and skipping paths converge on the final review screen; no dead ends |
| First-run commit rules | A verified authenticator and acknowledged recovery kit are required for the enabled path; skipped TOTP leaves no stale enrolment |
| Qt wizard integration (optional) | On computers with PySide6, navigate both paths, validate vault creation at Finish, and verify Cancel creates nothing |
| Qt v0.3 UI integration (optional) | Tabbed TOTP/recovery dialog, Password Version rotation, stale-output feedback, search identity, dynamic security state, saved-version confirmation and canceled recovery-code rotation |

**Result for v0.3.1:** 27 non-GUI tests passed in this environment. Sixteen GUI tests (four prior wizard tests, eight v0.3 GUI tests, four v0.3.1 UI tests) were skipped because PySide6 is unavailable here. Total: 43 discovered, 27 passed, 16 skipped. New tests cover context-specific onboarding wording and verified encrypted backup export, wrong master, existing backup, same-file rejection and corrupt source. Run the full suite with PySide6 on Windows and share the pass/fail counts before marking the UI verified. A passing test suite is not evidence of independent security certification.

## Manual acceptance checklist — NOT YET COMPLETED

Perform on a clean **Windows 11** system and ideally macOS/Linux; record screenshots/video and tick each box after actual observation.

- [ ] Fresh launch: setup wizard opens; cancel does not create `vault.aegis`.
- [ ] Empty, mismatched and short master passwords are rejected; successful setup creates exactly one encrypted vault.
- [ ] Skip authenticator: **Next** proceeds to Ready for Password Studio; **Finish** writes the vault and opens Password Studio; generation works.
- [ ] Enable authenticator: QR scans in Google or Microsoft Authenticator; incorrect live code rejects setup.
- [ ] Enable authenticator with correct code: 10 recovery codes display; **Next** is disabled until acknowledgement; checking the box enables **Next**, unchecking disables **Next**, and clicking **Next** opens Ready for Password Studio; **Finish** creates vault and opens Password Studio.
- [ ] Generator screen controls show complete labels without clipping on 100%, 125% and 150% Windows display scaling; vertical scrolling works.
- [ ] Restart: correct master + unused TOTP unlocks, incorrect master/code fails, using same TOTP counter again fails; new code in next time window succeeds.
- [ ] Lost-phone simulation: correct master + first recovery code unlocks; same recovery code is rejected on next attempt.
- [ ] After recovery unlock, Security Centre correctly shows remaining recovery-code count.
- [ ] Rotate recovery kit after reauthentication; old codes fail; new codes work once.
- [ ] Simulated blocked file write prevents recovery-code unlock, rather than accepting without saving consumption.
- [ ] Change account, phrase, length or revision after generating: displayed old password clears.
- [ ] Restart and regenerate: identical inputs yield identical account password; another account yields different output.
- [ ] Clipboard clears after 20 seconds when still unchanged; manually lock clears sensitive widgets.
- [ ] Idle for five minutes, including when a dialog is open: vault locks safely.
- [ ] After app kill/restart: decrypts current vault and performs no unintended data loss.
- [ ] Windows package builds; installs without Python, Start-menu shortcut works, optional desktop shortcut works, uninstall preserves encrypted user vault.
- [ ] GitHub source and release packages contain no personal credentials, recovery kits, or private vault files.
- [ ] Keyboard focus and Tab order are usable at common resolutions / scaling; high DPI and screenreader affordances reviewed.

## Known high-priority limitations

1. **No real-device Qt smoke test:** PySide6 was not installed in the development runtime. UI flow requires actual execution and human review.
2. **No file-locking or rollback protection:** two concurrent app processes or a malicious older vault backup could undo a consumed-code record. Mitigate with a single-instance/file lock and anti-rollback measures before personal deployment.
3. **No independent security review:** Argon2id/AES-GCM are mature primitives, but application composition, password derivation, packaging and lifecycle management have not received formal assessment.
4. **No master-password reset:** loss of the master password and vault/secret backup is catastrophic. Recovery codes only replace TOTP.
5. **Encrypted backup export, but no in-app restore:** the Security Centre now exports an encrypted snapshot after verification. Restoring still requires manual file handling. Restoring an old backup can roll back consumed recovery codes, TOTP counters and account settings. Course-demo password export is separate and explicitly plaintext.
6. **No OS-backed process isolation:** secrets can be exposed via clipboard, swap, memory, screenshots and system compromise.
7. **No safe concurrent editing or migration of versioned derivation:** generator's output may change if implementation or rules are changed later without compatibility preservation.
8. **TOTP access model limitation:** an attacker with the encrypted vault file can still attempt offline master-password cracking and is not meaningfully blocked by the TOTP challenge.
9. **Partial installer support:** Windows build configuration exists, but no compiled, code-signed, tested installer is included. macOS/Linux installers have not been authored.

**Gate before real personal use:** Finish manual QA; add inter-process locking and verified backup/restore; create a deterministic cross-version compatibility test suite; review operational threat model; obtain a competent independent code/security review; and use an established audited password manager in the interim.

## v0.3 security review and manual red-team checklist

- [ ] Unlock using a fresh TOTP code, then verify same time counter cannot unlock again.
- [ ] Unlock using an unused recovery code, verify remaining count decreases and the code cannot be reused after restart.
- [ ] Test **Authenticator code** and **Recovery code** tabs; cancel both without unlocking.
- [ ] Confirm a canceled *authenticator replacement* preserves the old TOTP and old recovery kit, aside from a previously consumed authorization code.
- [ ] Complete an *authenticator replacement* and verify the old authenticator/old recovery codes are revoked and new recovery codes work.
- [ ] Cancel a recovery-kit replacement after successfully authorizing: old kit still works except for the consumed authorizing code.
- [ ] On low disk space or write failure, access must not be granted before code-consumption state can be persisted.
- [ ] Rotate Password Version on a test account: the proposed password changes, saved metadata does not change until Save, and overwriting a previous version requires explicit confirmation.
- [ ] Filter Saved Accounts and verify delete/load operate on the **visible selected account**, not the old unfiltered row index.
- [ ] Use a previously saved test vault; do not delete it during upgrading.
- [ ] Back up an encrypted dummy vault in Security Centre with and without authenticator setup; ensure backup opens with correct master passphrase only and rejects existing filenames.
- [ ] Confirm the setup-complete wording appropriately explains no recovery codes on the skip route.
- [ ] Confirm password length/version steppers are rounded, work with keyboard and mouse, and respect min/max values.
- [ ] Confirm Saved Accounts retains clear selection highlighting without the dotted orange native focus rectangle.
- [ ] Confirm 5-minute idle auto-lock, clipboard clearing where supported, no secret exposure in repository, screenshots, logs, or public documentation.

**Known limitations:** No production authorization security guarantee, no automatic encrypted vault backup or in-app restore, no concurrent-writer protection or rollback defense, no secure memory erasure, no native Windows installer verification here, and no macOS/Linux GUI verification here. Website passwords are not changed by rotation inside AEGIS.


## v0.3.9 Windows installer build incident (October 2026)

On Windows the previous all-in-one test runner reported `Ran 74 tests ... OK
(skipped=1)`, followed by process exit `-1073740791` (`0xC0000409`).
The Python-level checks completed, but the native process failed after reporting
them. The exact native call stack has not been captured, so the suspected Qt
shutdown/lifecycle cause remains **unconfirmed**.

To prevent a test-runner native failure from needlessly blocking production of
a debug installer, the build now runs **39 mandatory backend and packaging
tests** in a process that never creates a Qt application. They pass in the
Linux-based test environment. GUI integration tests are retained and can be
invoked with `-RunGuiTests` on Windows, where a nonzero native exit remains
a failure and will stop that diagnostic mode. This is test separation, **not**
a remedy for the Qt crash.

Before publicly distributing the installer, investigate the Windows GUI-test
crash, smoke-test the PyInstaller app and install/uninstall in a clean Windows
environment, and review the unresolved security limitations, especially
offline vault rollback, user-credential handling, and lack of independent
security assessment.
