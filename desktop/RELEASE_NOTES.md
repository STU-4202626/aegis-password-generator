# AEGIS v0.3.9: Windows installer builder

- Added `build-installer.cmd` for a double-click developer build on 64-bit Windows.
- Improved the PowerShell packaging script: checks for Inno Setup first, uses a private build virtual environment, installs dependencies, runs all tests, includes the app icon asset, checks build output and writes a SHA-256 checksum.
- Versioned Windows EXE metadata and installer shortcuts. The desktop shortcut is optional; Start menu shortcut is automatic.
- Installer leaves encrypted vault data in the user profile on uninstall.
- Adds static packaging regression tests and a Windows acceptance checklist.
- Application security and password derivation are unchanged from v0.3.7. Vaults remain compatible.
- **A Windows EXE must be built and tested on Windows; it is not included in this source ZIP.**

- Installer builder separates non-GUI build-gating tests from GUI lifecycle tests.
- Native Qt shutdown errors are reported, not silently treated as passing tests.
- Optional `-RunGuiTests` diagnostic preserves the original full test suite.
