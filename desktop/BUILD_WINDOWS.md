# Build the Windows installer

This folder contains **the complete v0.3.9 AEGIS application source and installer builder**, not a compiled Windows executable. The actual `.exe` must be created on **64-bit Windows**. This is because PyInstaller is not a cross-compiler.

## Developer: build once on Windows

1. Download and install **Inno Setup 6.3+** from its official site: https://jrsoftware.org/isinfo.php
2. Make sure your **64-bit Python 3.11+** is working. You've already installed it for development.
3. Extract the project ZIP to a normal folder. Do not run from inside the ZIP.
4. Double-click **`build-installer.cmd`** in this folder. Keep the terminal open and wait for the test and build results. On first run it downloads build dependencies and may take several minutes.
5. The result will be:

   `installer-output/AEGIS-Setup-0.3.9-Windows-x64.exe`

   A separate `.sha256` checksum file is created in the same directory.

Alternative PowerShell command, run from this project folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
```

If you **only want the standalone application folder** without the installer, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1 -SkipInstaller
```

This produces `dist/AEGIS/AEGIS.exe`. **Do not distribute the `.exe` alone** in this mode; PyInstaller's `_internal` folder and other files are also required. The setup installer packages that folder as a single downloadable installer.

## What people installing AEGIS experience

1. Double-click `AEGIS-Setup-0.3.9-Windows-x64.exe`.
2. Follow the setup wizard. The **Start menu shortcut** is included; creating a **desktop shortcut** is optional.
3. Optionally tick **Launch AEGIS** on the final page.
4. Open AEGIS. There is **no separate Python or pip installation** and the completed installer needs **no network connection**.
5. Uninstall AEGIS using Windows Settings -> Installed apps when needed. User vault data stays intact by design.

## Acceptance checks (run on Windows)

- The builder runs mandatory backend and installer checks without Qt widgets.
- GUI integration tests are separate: see the diagnostic command below.
- Do not release until the actual Windows app is installed and tested with a dummy vault.
- Open `dist/AEGIS/AEGIS.exe` before building a public installer. Test onboarding and unlocking using a **dummy vault**.
- Run the generated Setup EXE on a different Windows user account, VM or test PC without Python; verify all pages, Start shortcut and optional desktop shortcut.
- Confirm the installed program has the AEGIS icon, launches normally, can create/restore encrypted backups and returns to the locked screen when appropriate.
- Test updating an existing AEGIS install: the vault is unaffected, and shortcuts still work.
- Test uninstall/reinstall: the user vault is **not deleted**.
- Verify neither the source ZIP nor the installer has `.aegis` files, recovery codes, master passwords or user-specific paths.
- Scan the binary on Windows; consider signing it before broad distribution. Unsigned new apps may trigger reputation warnings in Windows SmartScreen.

**Testing with an isolated vault** (PowerShell; the variable applies only to the current terminal):

```powershell
$env:AEGIS_DATA_DIR = Join-Path $env:TEMP ('AEGIS-packaging-test-' + (Get-Random))
.\dist\AEGIS\AEGIS.exe
```

To launch an installed app with an isolated test vault, set the same variable then run `& "$env:LOCALAPPDATA\Programs\AEGIS\AEGIS.exe"`.

Uninstall does not remove user vaults. If you want to remove a dummy vault, first confirm you are deleting **only** the test directory. Never delete a normal vault directory to reinstall the app.

## Support

- **Inno Setup missing:** install it from the site above, or use `-SkipInstaller` for the standalone app folder.
- **Python not found:** add your existing Python 3.11 installation to PATH, then reopen PowerShell.
- **Slow pip download:** rerun the command. The builder uses a 120-second network timeout and 10 retries.
- **Installer build fails:** keep the console output and provide the error details. Do not assume `installer-output` contains a valid new installer until the script reports success.
- **Windows only:** this builder creates an x64 Windows installer, not a macOS/Linux installer.

## Windows native crash after all tests print OK

If `python -m unittest discover -s tests -v` prints `OK` but Windows ends with
`-1073740791` (`0xC0000409`), the test process crashed during or after Qt
shutdown. This is not a passing process, even though the assertions passed.

The standard `build-installer.cmd` does **not** ignore that code. It runs the
mandatory backend / packaging classes separately without creating any Qt GUI,
and proceeds to PyInstaller if those pass. The GUI suite remains available
through this *optional diagnostic* command in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1 -RunGuiTests
```

If that command still exits with `0xC0000409`, do not report the GUI suite as
clean. Record the issue and test the packaged AEGIS.exe thoroughly on Windows.
Running GUI tests separately with `QT_QPA_PLATFORM=windows` may also help
identify whether the offscreen platform plugin is involved; it is not a
guaranteed repair. See `RELEASE_CHECKLIST.md` for manual acceptance checks.

The Qt teardown fault still warrants investigation before a public release.

## Windows native crash after all tests print OK

If `python -m unittest discover -s tests -v` prints `OK` but Windows ends with
`-1073740791` (`0xC0000409`), the test process crashed during or after Qt
shutdown. This is not a passing process, even though the assertions passed.

The standard `build-installer.cmd` does **not** ignore that code. It runs the
mandatory backend / packaging classes separately without creating any Qt GUI,
and proceeds to PyInstaller if those pass. The GUI suite remains available
through this *optional diagnostic* command in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1 -RunGuiTests
```

If that command still exits with `0xC0000409`, do not report the GUI suite as
clean. Record the issue and test the packaged AEGIS.exe thoroughly on Windows.
Running GUI tests separately with `QT_QPA_PLATFORM=windows` may also help
identify whether the offscreen platform plugin is involved; it is not a
guaranteed repair. See `RELEASE_CHECKLIST.md` for manual acceptance checks.

The Qt teardown fault still warrants investigation before a public release.
