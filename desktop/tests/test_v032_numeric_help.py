"""AEGIS v0.3.2 visual numeric fields and Password Version help.

Run on a machine with PySide6 for the UI checks. The underlying cryptographic
behaviour is unchanged. Tests create disposable, fictional vaults only.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox
    from aegis.gui import Aegis, PASSWORD_VERSION_HELP
    HAS_QT = True
except ImportError:
    HAS_QT = False

from aegis.vault import new_data, write_vault

MASTER = 'Fake test-only master password — do not reuse for credentials'


@unittest.skipUnless(HAS_QT, 'Qt visual tests must run on a desktop with PySide6')
class NumericHelpGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        before = os.environ.get('AEGIS_DATA_DIR')
        os.environ['AEGIS_DATA_DIR'] = self.tmp.name
        self.addCleanup(lambda: os.environ.pop('AEGIS_DATA_DIR', None) if before is None else os.environ.__setitem__('AEGIS_DATA_DIR', before))
        write_vault(Path(self.tmp.name) / 'vault.aegis', new_data(), MASTER)
        self.window = Aegis()
        self.addCleanup(self._close)
        self.window.data = new_data()
        self.window.master = MASTER

    def _close(self):
        self.app.removeEventFilter(self.window)
        self.window.timer.stop()
        self.window.close()

    def visible_editor(self, spin):
        self.assertEqual(spin.parentWidget().objectName(), 'numberShell')
        self.assertTrue(spin.isHidden())  # native Windows text renderer disabled
        editor = spin.parentWidget().findChild(QLineEdit, 'numberEditor')
        self.assertIsNotNone(editor)
        self.assertFalse(editor.isHidden())
        self.assertTrue(editor.text().isascii())
        return editor

    def test_numeric_values_are_visible_in_independent_editors(self):
        length = self.visible_editor(self.window.length_input)
        version = self.visible_editor(self.window.revision_input)
        self.assertEqual(length.text(), '24')
        self.assertEqual(version.text(), '1')
        self.window.length_input.setValue(41)
        self.window.revision_input.setValue(3)
        self.assertEqual(length.text(), '41')
        self.assertEqual(version.text(), '3')

    def test_manual_typing_updates_numeric_model_on_commit(self):
        length = self.visible_editor(self.window.length_input)
        length.setText('41')
        length.editingFinished.emit()
        self.assertEqual(self.window.length_input.value(), 41)
        length.setText('999')  # exceeds length max of 128
        length.editingFinished.emit()
        self.assertEqual(self.window.length_input.value(), 41)
        self.assertEqual(length.text(), '41')
        version = self.visible_editor(self.window.revision_input)
        version.setText('12')
        version.editingFinished.emit()
        self.assertEqual(self.window.revision_input.value(), 12)
        version.setText('')
        version.editingFinished.emit()
        self.assertEqual(version.text(), '12')

    def test_help_button_has_hover_and_click_explanations(self):
        help_btn = self.window.version_help_button
        self.assertEqual(help_btn.accessibleName(), 'What is Password Version?')
        self.assertIn('website', help_btn.toolTip())
        with mock.patch.object(QMessageBox, 'information') as info:
            help_btn.click()
        info.assert_called_once()
        self.assertIn('Password Version', info.call_args.args[1])
        self.assertEqual(info.call_args.args[2], PASSWORD_VERSION_HELP)


if __name__ == '__main__':
    unittest.main()
