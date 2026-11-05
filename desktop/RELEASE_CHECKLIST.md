# AEGIS | Release-readiness checklist

AEGIS has working core flows on the Windows test computer. That does not establish production security. Use this checklist before distributing it as a tool for real accounts.

## Blocking work before a trusted release

- [ ] Run all automated tests **with PySide6** on Windows; fix any failures and preserve a test log.
- [ ] Complete an independent review of password derivation, vault encryption/storage, master-passphrase handling, authenticator recovery, restore, and file operations. Record findings and fixes.
- [ ] Define and test a defensible policy for **restoring older backups**, which can make previously used TOTP/recovery codes valid again. The current app warns about this but does not prevent it.
- [ ] Test lock and clipboard cleanup, including idle lock, sleep/resume, close/reopen, invalid passwords, corrupt vault files, power interruption, and permission errors.
- [ ] Build the Windows installer with `packaging/build_windows.ps1` and Inno Setup 6.3+, then test install, launch, shortcuts, upgrade, uninstall and preservation of vault data on a **clean Windows device without Python**.
- [ ] Ensure release ZIPs/installers contain no private vault files, authenticator secrets, recovery kits, screenshots of secrets, or debug logs with credentials.
- [ ] Test common Windows display settings (100%, 125%, 150%), keyboard-only navigation and screen-reader labels.

## Recommended for distribution

- [ ] Sign Windows executables and installer where feasible; publish SHA-256 checksums with downloads.
- [ ] Choose a versioned, tested update process that does not alter already-derived passwords.
- [ ] Publish a clear backup-and-recovery guide, including that forgetting the master passphrase is not recoverable by a TOTP code.
- [ ] Offer secure defaults for generated-password display, plaintext export and clipboard handling, and document risks of copying to the system clipboard.
- [ ] Test on macOS/Linux if claiming native support, and prepare platform-specific signed/notarized packages as appropriate.
- [ ] Make the application's public description accurate: AEGIS stores encrypted account settings and a private generation secret, **not generated account passwords** by default.

## Later enhancements

- [ ] Optional independent emergency decryption/recovery key (requires cryptographic redesign and review, not a reset bypass).
- [ ] More advanced account grouping, account-type templates and onboarding help.
- [ ] Optional secure synchronization and multi-device migration with conflict handling, only after backup/rollback risks are addressed.

## Release gate

Do not describe AEGIS as independently security-audited or suitable for important credentials until the blocking items have been verified by qualified reviewers and on real target platforms.

- [ ] Resolve/report Qt 0xC0000409 crash from full GUI test process on Windows.
- [ ] Run standalone bundled AEGIS.exe on Windows with dummy vault.
- [ ] Test setup, uninstall, and shortcuts on Windows before shipping.
