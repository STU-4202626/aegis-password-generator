"""v0.3.4 copy, non-bypass master-passphrase help and theming checks."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aegis.onboarding import setup_complete_message
from aegis.vault import new_data, write_vault


class CopyContractTests(unittest.TestCase):
    def test_setup_messages_are_brief_and_context_aware(self):
        enabled = setup_complete_message(True)
        disabled = setup_complete_message(False)
        self.assertIn('Back up encrypted vault', enabled)
        self.assertIn('10 recovery codes', enabled)
        self.assertNotIn('10 recovery codes', disabled)
        for message in (enabled, disabled):
            self.assertNotIn('prototype', message.lower())
            self.assertNotIn('GitHub', message)
            self.assertNotIn('—', message)
            self.assertLess(len(message), 350)


os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication, QMessageBox
    from aegis.gui import Aegis, STYLE
    from aegis.wizard import Welcome
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, 'PySide6 required for user interface checks')
class ProductExperienceGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        previous = os.environ.get('AEGIS_DATA_DIR')
        os.environ['AEGIS_DATA_DIR'] = self.tmp.name
        self.addCleanup(self._restore_environment, previous)
        self.path = Path(self.tmp.name) / 'vault.aegis'
        write_vault(self.path, new_data(), 'A fictional long master passphrase 2026')
        self.window = Aegis()
        self.addCleanup(self._close)

    def _restore_environment(self, previous):
        if previous is None:
            os.environ.pop('AEGIS_DATA_DIR', None)
        else:
            os.environ['AEGIS_DATA_DIR'] = previous

    def _close(self):
        self.qt.removeEventFilter(self.window)
        self.window.timer.stop()
        self.window.close()

    def test_themed_tooltips_and_forgot_link(self):
        self.assertIn('QToolTip', STYLE)
        self.assertIn('border-radius:8px', STYLE)
        self.assertEqual(self.window.forgot_master_button.text(), 'Forgot master passphrase?')
        self.assertFalse(self.window.forgot_master_button.isHidden())

    def test_forgot_flow_explains_no_bypass(self):
        with mock.patch.object(QMessageBox, 'information') as info:
            self.window.forgot_master_button.click()
        self.assertEqual(info.call_count, 1)
        body = info.call_args.args[2]
        self.assertIn('cannot reveal or reset', body)
        self.assertIn('recovery codes cannot unlock', body)

    def test_security_detail_is_discoverable(self):
        with mock.patch.object(QMessageBox, 'information') as info:
            self.window.security_details_button.click()
        self.assertEqual(info.call_count, 1)
        self.assertIn('independent security audit', info.call_args.args[2])

    def test_first_run_has_no_developer_banner(self):
        from PySide6.QtWidgets import QLabel
        page = Welcome()
        texts = ' '.join(widget.text() for widget in page.findChildren(QLabel))
        self.assertNotIn('prototype', texts.lower())
        self.assertNotIn('real passwords', texts.lower())


if __name__ == '__main__':
    unittest.main()
