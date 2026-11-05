"""Qt acceptance checks for AEGIS v0.3 (run on developer's Windows/Qt setup).

Tests are skipped in minimal backend-only environments without PySide6.
All vaults created by this suite are strictly temporary, fictional and isolated.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
    from aegis.gui import Aegis, SecondStepDialog
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from aegis.auth import enrol_totp, remaining_recovery_codes, verify_second_step
from aegis.totp import create_secret, current_code
from aegis.vault import new_data, read_vault, write_vault

MASTER = 'A fictional test master passphrase 123!'


@unittest.skipUnless(QT_AVAILABLE, 'PySide6-Essentials is required for Qt acceptance checks')
class StudioAndUnlockUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._prev_env = os.environ.get('AEGIS_DATA_DIR')
        os.environ['AEGIS_DATA_DIR'] = self.tmp.name
        self.addCleanup(self._restore_env)
        self.path = Path(self.tmp.name) / 'vault.aegis'
        self.initial = new_data()
        write_vault(self.path, self.initial, MASTER)
        self.window = Aegis()
        self.addCleanup(self._close_window)
        self.window.master = MASTER
        self.window.data = self.initial
        self.window.refresh_entries()
        self.window.set_page(0)

    def _restore_env(self):
        if self._prev_env is None:
            os.environ.pop('AEGIS_DATA_DIR', None)
        else:
            os.environ['AEGIS_DATA_DIR'] = self._prev_env

    def _close_window(self):
        self.qt.removeEventFilter(self.window)
        self.window.timer.stop()
        self.window.close()

    def test_password_version_and_studio_specific_feedback(self):
        self.assertEqual(self.window.revision_input.accessibleName(), 'Password version')
        self.assertEqual(self.window.revision_input.value(), 1)
        self.window.output.setText('temporary-test-string')
        self.window.site_input.setText('example.test/demo')
        self.assertEqual(self.window.output.text(), '')
        self.assertIn('Inputs changed', self.window.studio_feedback.text())
        self.assertNotIn('Inputs changed', self.window.status.text())
        self.window.set_page(2)
        self.assertEqual(self.window.nav_buttons[2].objectName(), 'navActive')

    def test_rotate_produces_new_candidate_without_saving(self):
        self.window.site_input.setText('example.test/demo')
        self.window.phrase_input.setText('fictional phrase for the test only')
        self.window.generate()
        original = self.window.output.text()
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            self.window.rotate_password()
        self.assertEqual(self.window.revision_input.value(), 2)
        self.assertNotEqual(self.window.output.text(), original)
        self.assertEqual(read_vault(self.path, MASTER)['entries'], [])
        self.assertIn('Update the website', self.window.studio_feedback.text())

    def test_search_preserves_correct_account_identity(self):
        self.window.data['entries'] = [
            {'account': 'discord.example', 'length': 24, 'revision': 1},
            {'account': 'github.example', 'length': 41, 'revision': 3},
        ]
        self.window.refresh_entries()
        self.window.account_search.setText('github')
        self.assertEqual(self.window.entries_list.count(), 1)
        self.window.entries_list.setCurrentRow(0)
        selected = self.window.selected_entry()
        self.assertEqual(selected['account'], 'github.example')
        self.window.load_account()
        self.assertEqual(self.window.site_input.text(), 'github.example')
        self.assertEqual(self.window.revision_input.value(), 3)
        self.assertEqual(self.window.phrase_input.text(), '')

    def test_security_button_responds_to_enrolment(self):
        self.assertIn('Set up', self.window.enroll_button.text())
        self.window.data['totp_secret'] = create_secret()
        self.window.refresh_entries()
        self.assertIn('Change authenticator', self.window.enroll_button.text())

    def test_saved_version_change_requires_confirmation(self):
        self.window.data['entries'] = [{'account': 'example.test', 'length': 24, 'revision': 1}]
        write_vault(self.path, self.window.data, MASTER)
        self.window.site_input.setText('example.test')
        self.window.phrase_input.setText('test phrase')
        self.window.revision_input.setValue(2)
        self.window.generate()
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            self.window.save_account()
        self.assertEqual(read_vault(self.path, MASTER)['entries'][0]['revision'], 1)

    def test_rotation_of_recovery_kit_consumes_authorising_code_even_if_cancelled(self):
        secret = create_secret()
        enrolment = enrol_totp(self.window.data, secret, current_code(secret))
        self.window.data = enrolment.updated
        write_vault(self.path, self.window.data, MASTER)
        first_recovery_code = enrolment.recovery_codes[0]
        with (mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes),
              mock.patch.object(self.window, 'sensitive_reauthentication', return_value=True),
              mock.patch.object(self.window, 'ask_second_step', return_value=(first_recovery_code, True)),
              mock.patch.object(self.window, 'show_recovery_kit', return_value=False)):
            self.window.replace_recovery_codes()
        reloaded = read_vault(self.path, MASTER)
        self.assertEqual(remaining_recovery_codes(reloaded), 9)
        with self.assertRaises(ValueError):
            verify_second_step(reloaded, first_recovery_code)


@unittest.skipUnless(QT_AVAILABLE, 'PySide6-Essentials is required for Qt acceptance checks')
class SecondStepDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def test_must_enter_exact_six_digits_on_authenticator_tab(self):
        dialog = SecondStepDialog()
        dialog.totp_input.setText('123')
        dialog.validate_and_accept()
        self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertIn('six digits', dialog.error_label.text())
        dialog.totp_input.setText('001234')
        dialog.validate_and_accept()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(dialog.supplied_code(), '001234')
        dialog.clear_secrets()
        self.assertEqual(dialog.totp_input.text(), '')

    def test_recovery_tab_has_explicit_label_and_accepts_full_code(self):
        dialog = SecondStepDialog()
        dialog.tabs.setCurrentIndex(1)
        dialog.recovery_input.setText('AEGIS-' + 'A'*24)
        dialog.validate_and_accept()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(dialog.supplied_code(), 'AEGIS-' + 'A'*24)
        dialog.clear_secrets()
        self.assertEqual(dialog.recovery_input.text(), '')


if __name__ == '__main__':
    unittest.main()
