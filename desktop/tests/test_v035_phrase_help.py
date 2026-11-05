"""Memorable-phrase guidance tests. GUI checks need PySide6."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication, QMessageBox, QLabel
    from aegis.gui import Aegis, MEMORABLE_PHRASE_HELP
    from aegis.wizard import Welcome
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from aegis.vault import new_data, write_vault


@unittest.skipUnless(QT_AVAILABLE, 'PySide6 needed for GUI tests')
class MemorablePhraseHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        before = os.environ.get('AEGIS_DATA_DIR')
        os.environ['AEGIS_DATA_DIR'] = self.tmp.name
        self.addCleanup(self.reset_env, before)
        write_vault(Path(self.tmp.name)/'vault.aegis', new_data(),
                    'Fictional long master passphrase only for GUI tests')
        self.window = Aegis()
        self.addCleanup(self.close_window)

    @staticmethod
    def reset_env(before):
        if before is None:
            os.environ.pop('AEGIS_DATA_DIR', None)
        else:
            os.environ['AEGIS_DATA_DIR'] = before

    def close_window(self):
        self.app.removeEventFilter(self.window)
        self.window.timer.stop()
        self.window.close()

    def test_help_matches_existing_icon_theme(self):
        button = self.window.phrase_help_button
        self.assertEqual(button.objectName(), 'helpIcon')
        # Qt style-sheet borders can add 2 logical pixels on Windows.
        # Match the existing Password Version info icon, instead of assuming
        # an exact platform-dependent pixel dimension.
        self.assertEqual(button.size(), self.window.version_help_button.size())
        self.assertGreaterEqual(button.size().width(), 18)
        self.assertLessEqual(button.size().width(), 22)
        self.assertEqual(button.accessibleName(), 'What is a memorable phrase?')
        self.assertIn('Example:', button.toolTip())
        self.assertEqual(button.whatsThis(), MEMORABLE_PHRASE_HELP)

    def test_click_opens_full_explanation(self):
        with mock.patch.object(QMessageBox, 'information') as information:
            self.window.phrase_help_button.click()
        information.assert_called_once()
        self.assertEqual(information.call_args.args[2], MEMORABLE_PHRASE_HELP)
        self.assertIn('does not save', MEMORABLE_PHRASE_HELP)
        self.assertIn('private secret', MEMORABLE_PHRASE_HELP)

    def test_studio_and_welcome_explain_product_purpose(self):
        from PySide6.QtWidgets import QLabel
        all_studio = ' '.join(x.text() for x in self.window.findChildren(QLabel))
        self.assertIn('Turn a phrase you remember', all_studio)
        page = Welcome()
        all_intro = ' '.join(x.text() for x in page.findChildren(QLabel))
        self.assertIn('Turn a phrase you remember', all_intro)


if __name__ == '__main__':
    unittest.main()
