"""v0.3.7 UI regression checks; run with PySide6 on Windows."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication, QLineEdit, QToolButton
    from aegis.gui import Aegis, STYLE, phrase_eye_icon, windows_caps_lock_enabled
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from aegis.vault import new_data, write_vault

MASTER = 'A fictional test master passphrase 123!'


@unittest.skipUnless(QT_AVAILABLE, 'GUI tests require PySide6')
class PhraseVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        previous = os.environ.get('AEGIS_DATA_DIR')
        os.environ['AEGIS_DATA_DIR'] = self.tmp.name
        self.addCleanup(self.restore_env, previous)
        self.initial = new_data()
        write_vault(Path(self.tmp.name) / 'vault.aegis', self.initial, MASTER)
        self.window = Aegis()
        self.addCleanup(self.close_window)
        self.window.master = MASTER
        self.window.data = self.initial
        self.window.set_page(0)

    @staticmethod
    def restore_env(previous):
        if previous is None:
            os.environ.pop('AEGIS_DATA_DIR', None)
        else:
            os.environ['AEGIS_DATA_DIR'] = previous

    def close_window(self):
        self.app.removeEventFilter(self.window)
        self.window.timer.stop()
        self.window.close()

    def test_eye_is_embedded_and_large_enough_to_see(self):
        field = self.window.phrase_input
        eye = self.window.phrase_eye_button
        self.assertIs(eye.parent(), field)
        self.assertIsInstance(eye, QToolButton)
        self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Password)
        self.assertIn('Show', eye.accessibleName())
        self.assertFalse(eye.icon().isNull())
        self.assertGreaterEqual(eye.iconSize().width(), 26)
        self.assertGreaterEqual(eye.width(), 38)

    def test_eye_is_vertically_centered_and_inset_from_edge(self):
        self.window.show()
        self.app.processEvents()
        field = self.window.phrase_input
        eye = self.window.phrase_eye_button
        self.assertGreaterEqual(field.width() - (eye.x() + eye.width()), 10)
        self.assertLessEqual(abs(eye.y() + eye.height() / 2 - field.height() / 2), 1)

    def test_eye_toggle_retains_text_but_switches_visibility(self):
        field = self.window.phrase_input
        field.setText('Some made-up words, never a real passphrase')
        eye = self.window.phrase_eye_button
        eye.click()
        self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertIn('Hide', eye.accessibleName())
        self.assertEqual(field.text(), 'Some made-up words, never a real passphrase')
        eye.click()
        self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Password)
        self.assertIn('Show', eye.accessibleName())
        self.assertEqual(field.text(), 'Some made-up words, never a real passphrase')

    def test_lock_clears_and_hides_phrase(self):
        self.window.phrase_input.setText('sample-only')
        self.window.phrase_eye_button.click()
        self.window.lock()
        self.assertFalse(self.window.phrase_revealed)
        self.assertEqual(self.window.phrase_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(self.window.phrase_input.text(), '')

    def test_loading_saved_account_hides_phrase(self):
        self.window.data['entries'] = [{'account': 'example.test', 'length': 24, 'revision': 1}]
        self.window.refresh_entries()
        self.window.entries_list.setCurrentRow(0)
        self.window.phrase_input.setText('sample-only')
        self.window.phrase_eye_button.click()
        self.window.load_account()
        self.assertFalse(self.window.phrase_revealed)
        self.assertEqual(self.window.phrase_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(self.window.phrase_input.text(), '')

    def test_navigation_borders_use_consistent_width_and_have_inset(self):
        self.assertIn('QPushButton#nav, QPushButton#navActive { border-width:2px;', STYLE)
        self.assertIn('QPushButton#navActive:focus {border-color:', STYLE)
        self.window.set_page(1)
        self.assertEqual(self.window.nav_buttons[1].objectName(), 'navActive')
        self.window.set_page(2)
        self.assertEqual(self.window.nav_buttons[1].objectName(), 'nav')

    def test_caps_lock_hint_has_no_non_windows_false_positives(self):
        if os.name != 'nt':
            self.assertFalse(windows_caps_lock_enabled())
        self.assertEqual(self.window.caps_warning.text(), 'Caps Lock is on.')


if __name__ == '__main__':
    unittest.main()
