"""v0.3.1 polish and encrypted-backup regression checks.

Only fictional, isolated vault data is used. GUI checks are optional when Qt is
not installed in a backend-only validation environment.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from aegis.onboarding import setup_complete_message
from aegis.vault import export_encrypted_backup, new_data, read_vault, write_vault

MASTER = 'A fictitious master passphrase for backup tests 123!'


class ContextAndBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.live = self.root / 'vault.aegis'
        self.backup = self.root / 'backup.aegis'
        data = new_data()
        data['entries'].append({'account': 'fictional.example', 'length': 29, 'revision': 2})
        self.data = data
        write_vault(self.live, data, MASTER)

    def test_skip_does_not_claim_recovery_codes_exist(self):
        text = setup_complete_message(False)
        self.assertIn('Authenticator is off', text)
        self.assertIn('Back up encrypted vault', text)
        self.assertNotIn('Keep your ten', text)

    def test_enrolled_setup_distinguishes_two_recovery_mechanisms(self):
        text = setup_complete_message(True)
        self.assertIn('10 recovery codes work once', text)
        self.assertIn('do not reset your master passphrase or restore a lost vault', text)
        self.assertIn('Back up encrypted vault', text)

    def test_backup_contains_encrypted_copy_and_can_be_decrypted(self):
        export_encrypted_backup(self.live, self.backup, MASTER)
        self.assertEqual(self.backup.read_bytes(), self.live.read_bytes())
        self.assertEqual(read_vault(self.backup, MASTER), self.data)
        self.assertNotIn(b'fictional.example', self.backup.read_bytes())
        self.assertNotIn(b'private generation secret', self.backup.read_bytes())

    def test_backup_never_overwrites_existing_backup(self):
        self.backup.write_bytes(b'keep this prior backup')
        with self.assertRaises(FileExistsError):
            export_encrypted_backup(self.live, self.backup, MASTER)
        self.assertEqual(self.backup.read_bytes(), b'keep this prior backup')

    def test_backup_refuses_active_vault_path(self):
        original = self.live.read_bytes()
        with self.assertRaises(ValueError):
            export_encrypted_backup(self.live, self.live, MASTER)
        self.assertEqual(self.live.read_bytes(), original)

    def test_backup_rejects_wrong_master_and_corrupt_source(self):
        with self.assertRaisesRegex(ValueError, 'cannot be authenticated'):
            export_encrypted_backup(self.live, self.backup, 'wrong master phrase 123456')
        self.assertFalse(self.backup.exists())
        self.live.write_bytes(b'not an encrypted vault')
        with self.assertRaises((ValueError, UnicodeDecodeError)):
            export_encrypted_backup(self.live, self.backup, MASTER)
        self.assertFalse(self.backup.exists())


os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication, QAbstractSpinBox, QPushButton
    from aegis.gui import Aegis, CleanSelectionDelegate
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, 'PySide6 needed to verify GUI polish')
class NumberAndSelectionGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.prior_dir = os.environ.get('AEGIS_DATA_DIR')
        os.environ['AEGIS_DATA_DIR'] = self.tmp.name
        self.addCleanup(self._restore)
        write_vault(Path(self.tmp.name) / 'vault.aegis', new_data(), MASTER)
        self.window = Aegis()
        self.addCleanup(self._close)
        self.window.data = read_vault(self.window.path, MASTER)
        self.window.master = MASTER

    def _restore(self):
        if self.prior_dir is None:
            os.environ.pop('AEGIS_DATA_DIR', None)
        else:
            os.environ['AEGIS_DATA_DIR'] = self.prior_dir

    def _close(self):
        self.qt.removeEventFilter(self.window)
        self.window.timer.stop()
        self.window.close()

    def _click_step(self, spin, action):
        shell = spin.parentWidget()
        self.assertEqual(shell.objectName(), 'numberShell')
        self.assertEqual(spin.buttonSymbols(), QAbstractSpinBox.ButtonSymbols.NoButtons)
        target = next(b for b in shell.findChildren(QPushButton)
                      if b.accessibleName() == action)
        target.click()

    def test_length_increment_and_decrement_are_rounded_controls(self):
        self.assertEqual(self.window.length_input.value(), 24)
        self._click_step(self.window.length_input, 'Increase password length')
        self.assertEqual(self.window.length_input.value(), 25)
        self._click_step(self.window.length_input, 'Decrease password length')
        self.assertEqual(self.window.length_input.value(), 24)

    def test_version_buttons_respect_minimum(self):
        self.assertEqual(self.window.revision_input.value(), 1)
        shell = self.window.revision_input.parentWidget()
        down = next(b for b in shell.findChildren(QPushButton)
                    if b.accessibleName() == 'Decrease password version')
        self.assertFalse(down.isEnabled())
        self._click_step(self.window.revision_input, 'Increase password version')
        self.assertTrue(down.isEnabled())

    def test_saved_account_uses_focus_clean_delegate(self):
        self.assertIsInstance(self.window.entries_list.itemDelegate(), CleanSelectionDelegate)

    def test_security_centre_exposes_encrypted_backup(self):
        self.assertEqual(self.window.backup_button.text(), 'Back up encrypted vault')


if __name__ == '__main__':
    unittest.main()
