"""Static checks for packaging; real Windows build must be verified on Windows."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WindowsPackagingTests(unittest.TestCase):
    def test_developer_scripts_present(self):
        for path in ('build-installer.cmd','packaging/build_windows.ps1',
                     'packaging/aegis.iss','packaging/version_info.txt',
                     'assets/aegis.ico','BUILD_WINDOWS.md','packaging/run_build_tests.py'):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_installer_bundles_standalone_app_and_preserves_data(self):
        script = (ROOT / 'packaging/aegis.iss').read_text(encoding='utf-8')
        self.assertIn('Source: "..\\dist\\AEGIS\\*"', script)
        self.assertIn('PrivilegesRequired=lowest', script)
        self.assertIn('Name: "desktopicon"', script)
        self.assertIn('Flags: unchecked', script)
        self.assertIn('AppId={{8D8E0B2A-53BB-42D7-85F4-C2A81A83091B}', script)
        self.assertNotIn('DelTree', script)

    def test_version_consistency(self):
        script = (ROOT / 'packaging/aegis.iss').read_text(encoding='utf-8')
        version = (ROOT / 'packaging/version_info.txt').read_text(encoding='utf-8')
        build = (ROOT / 'packaging/build_windows.ps1').read_text(encoding='utf-8')
        self.assertIn('#define AppVersion "0.3.9"', script)
        self.assertIn("StringStruct('ProductVersion', '0.3.9.0')", version)
        self.assertIn('AEGIS-Setup-0.3.9-Windows-x64.exe', build)

    def test_runtime_resource_and_bundle_flags(self):
        build = (ROOT / 'packaging/build_windows.ps1').read_text(encoding='utf-8')
        gui = (ROOT / 'aegis/gui.py').read_text(encoding='utf-8')
        self.assertIn("--add-data 'assets;assets'", build)
        self.assertIn("'_MEIPASS'", gui)
        self.assertIn('app.setWindowIcon', gui)
        self.assertIn("'packaging\\run_build_tests.py'", build)
        self.assertIn('RunGuiTests', build)
        self.assertIn('Check-Exit', build)

if __name__ == '__main__': unittest.main()
