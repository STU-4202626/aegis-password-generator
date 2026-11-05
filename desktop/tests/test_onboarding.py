"""First-run navigation regression tests; GUI cases run when Qt is available."""
import os
import tempfile
import unittest
from pathlib import Path

from aegis.auth import enrol_totp
from aegis.onboarding import (WELCOME, MASTER, AUTH_CHOICE, AUTH_VERIFY, RECOVERY,
                              READY, FINISHED, next_page, prepare_first_vault)
from aegis.totp import create_secret, current_code
from aegis.vault import new_data, read_vault

TEST_MASTER = 'Only a fictional master passphrase for the automated tests'


class OnboardingRoutingTests(unittest.TestCase):
    def test_skip_authenticator_has_real_next_page(self):
        self.assertEqual([next_page(i, False) for i in (0, 1, 2, 5)],
                         [MASTER, AUTH_CHOICE, READY, FINISHED])
        self.assertNotEqual(next_page(AUTH_CHOICE, False), FINISHED)

    def test_enable_authenticator_visits_recovery_then_ready(self):
        self.assertEqual([next_page(i, True) for i in (0, 1, 2, 3, 4, 5)],
                         [MASTER, AUTH_CHOICE, AUTH_VERIFY, RECOVERY, READY, FINISHED])

    def test_no_unknown_page_ids(self):
        for bad in (-1, 6, 999):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                next_page(bad, False)

    def test_skip_creates_clean_vault_even_if_prior_enrolment_exists(self):
        secret = create_secret()
        enrolment = enrol_totp(new_data(), secret, current_code(secret))
        result = prepare_first_vault(TEST_MASTER, TEST_MASTER, enable_authenticator=False,
                                     enrolment=enrolment, recovery_saved=False)
        self.assertIsNone(result['totp_secret'])
        self.assertEqual(result['recovery_hashes'], [])

    def test_authenticator_requires_verified_code_and_kit_saved(self):
        secret = create_secret()
        enrolment = enrol_totp(new_data(), secret, current_code(secret))
        for en, saved in ((None, True), (enrolment, False)):
            with self.subTest(en=en is not None, saved=saved), self.assertRaises(ValueError):
                prepare_first_vault(TEST_MASTER, TEST_MASTER,
                                    enable_authenticator=True, enrolment=en, recovery_saved=saved)
        data = prepare_first_vault(TEST_MASTER, TEST_MASTER,
                                   enable_authenticator=True, enrolment=enrolment, recovery_saved=True)
        self.assertEqual(data['totp_secret'], secret)
        self.assertEqual(len(data['recovery_hashes']), 10)
        self.assertIsNot(data, enrolment.updated)

    def test_master_password_rules_still_apply_on_finish(self):
        with self.assertRaises(ValueError):
            prepare_first_vault('short', 'short', enable_authenticator=False,
                                enrolment=None, recovery_saved=False)
        with self.assertRaises(ValueError):
            prepare_first_vault(TEST_MASTER, 'different', enable_authenticator=False,
                                enrolment=None, recovery_saved=False)


try:
    # Optional UI integration tests; run on the user's Windows installation.
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication, QWizard
    from aegis.wizard import FirstRunWizard
    GUI_PRESENT = True
except ImportError:
    GUI_PRESENT = False


@unittest.skipUnless(GUI_PRESENT, 'PySide6-Essentials is not installed here')
class QtWizardNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test_vault.aegis'
        self.w = FirstRunWizard(self.path)
        self.w.show()
        self.app.processEvents()
        self.addCleanup(self.w.close)

    def enter_master(self):
        self.w.next()
        self.assertEqual(self.w.currentId(), MASTER)
        self.w.page(MASTER).first.setText(TEST_MASTER)
        self.w.page(MASTER).confirm.setText(TEST_MASTER)
        self.w.next()
        self.assertEqual(self.w.currentId(), AUTH_CHOICE)

    def test_skip_branch_reaches_ready_then_creates_vault(self):
        self.enter_master()
        self.w.page(AUTH_CHOICE).skip.setChecked(True)
        self.app.processEvents()
        self.assertTrue(self.w.button(QWizard.WizardButton.NextButton).isEnabled())
        self.w.next()
        self.assertEqual(self.w.currentId(), READY)
        self.assertFalse(self.path.exists())
        self.w.accept()
        self.assertTrue(self.path.exists())
        self.assertIsNone(read_vault(self.path, TEST_MASTER)['totp_secret'])

    def test_authenticator_branch_reaches_ready_after_saved_codes(self):
        self.enter_master()
        self.w.next()
        self.assertEqual(self.w.currentId(), AUTH_VERIFY)
        secret = self.w.page(AUTH_VERIFY).secret
        self.w.page(AUTH_VERIFY).code.setText(current_code(secret))
        self.w.next()
        self.assertEqual(self.w.currentId(), RECOVERY)
        self.assertFalse(self.w.page(RECOVERY).isComplete())
        next_button = self.w.button(QWizard.WizardButton.NextButton)
        self.assertFalse(next_button.isEnabled(), 'Next must be disabled until codes are acknowledged')
        self.w.page(RECOVERY).saved.setChecked(True)
        self.app.processEvents()
        self.assertTrue(next_button.isEnabled(), 'Next must enable after recovery checkbox is checked')
        next_button.click()  # Test the real user action, not merely w.next().
        self.app.processEvents()
        self.assertEqual(self.w.currentId(), READY)
        self.assertFalse(self.path.exists())
        self.w.accept()
        self.assertTrue(self.path.exists())
        self.assertEqual(read_vault(self.path, TEST_MASTER)['totp_secret'], secret)

    def test_recovery_acknowledgement_can_be_unchecked(self):
        self.enter_master()
        self.w.next()
        secret = self.w.page(AUTH_VERIFY).secret
        self.w.page(AUTH_VERIFY).code.setText(current_code(secret))
        self.w.next()
        self.assertEqual(self.w.currentId(), RECOVERY)
        next_button = self.w.button(QWizard.WizardButton.NextButton)
        self.w.page(RECOVERY).saved.setChecked(True)
        self.app.processEvents()
        self.assertTrue(next_button.isEnabled())
        self.w.page(RECOVERY).saved.setChecked(False)
        self.app.processEvents()
        self.assertFalse(next_button.isEnabled(), 'Unchecking must re-disable Next')
        next_button.click()
        self.assertEqual(self.w.currentId(), RECOVERY)

    def test_cancel_creates_no_vault(self):
        self.enter_master()
        self.w.reject()
        self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
