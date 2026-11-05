"""Security regression tests independent of PySide6/UI availability."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aegis.auth import (enrol_totp, generate_recovery_codes, recovery_digest,
                        remaining_recovery_codes, rotate_recovery_codes,
                        validate_new_master, verify_second_step)
from aegis.totp import current_code, create_secret
from aegis.vault import new_data, decrypt_data, encrypt_data, read_vault, write_vault

MASTER = 'A long master passphrase for testing only!'


class RecoveryTests(unittest.TestCase):
    def test_recovery_codes_have_high_entropy_and_are_unique(self):
        codes, hashes = generate_recovery_codes()
        self.assertEqual(len(codes), 10)
        self.assertEqual(len(set(codes)), 10)
        self.assertEqual(len(set(hashes)), 10)
        self.assertTrue(all(c.startswith('AEGIS-') and len(c.replace('-', '')[5:]) == 24 for c in codes))
        self.assertTrue(all(c not in hashes for c in codes))

    def test_recovery_code_normalisation_and_rejection(self):
        codes, hashes = generate_recovery_codes()
        self.assertEqual(recovery_digest(codes[0].lower()), hashes[0])
        self.assertEqual(recovery_digest(' ' + codes[0] + ' '), hashes[0])
        for bad in ('AEGIS-123', 'AEGIS-0000-0000-0000-0000-0000-0000', '', 'test'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                recovery_digest(bad)

    def test_enrollment_requires_valid_live_code(self):
        data = new_data()
        secret = create_secret()
        with self.assertRaises(ValueError):
            enrol_totp(data, secret, 'not-a-code', 100000)
        self.assertIsNone(data['totp_secret'])
        enrolled = enrol_totp(data, secret, current_code(secret, 100000), 100000)
        self.assertEqual(enrolled.updated['totp_secret'], secret)
        self.assertEqual(len(enrolled.updated['recovery_hashes']), 10)
        self.assertNotIn('recovery_codes', enrolled.updated)
        self.assertIsNone(data['totp_secret'])

    def test_each_recovery_code_works_only_once(self):
        secret = create_secret(); epoch = 100000
        en = enrol_totp(new_data(), secret, current_code(secret, epoch), epoch)
        original = en.updated
        updated, kind = verify_second_step(original, en.recovery_codes[0], epoch)
        self.assertEqual(kind, 'recovery')
        self.assertEqual(remaining_recovery_codes(updated), 9)
        self.assertEqual(remaining_recovery_codes(original), 10)
        with self.assertRaises(ValueError):
            verify_second_step(updated, en.recovery_codes[0], epoch)
        self.assertEqual(verify_second_step(updated, en.recovery_codes[1], epoch)[1], 'recovery')

    def test_totp_replay_prevention(self):
        secret = create_secret(); epoch = 100000
        enrolled = enrol_totp(new_data(), secret, current_code(secret, epoch), epoch)
        with self.assertRaises(ValueError):
            verify_second_step(enrolled.updated, current_code(secret, epoch), epoch)
        newer = epoch + 90
        changed, kind = verify_second_step(enrolled.updated, current_code(secret, newer), newer)
        self.assertEqual(kind, 'totp')
        with self.assertRaises(ValueError):
            verify_second_step(changed, current_code(secret, newer), newer)

    def test_rotation_revokes_all_old_recovery_codes(self):
        epoch = 100000; secret = create_secret()
        en = enrol_totp(new_data(), secret, current_code(secret, epoch), epoch)
        new = rotate_recovery_codes(en.updated)
        self.assertEqual(remaining_recovery_codes(new.updated), 10)
        with self.assertRaises(ValueError):
            verify_second_step(new.updated, en.recovery_codes[0], epoch)
        self.assertEqual(verify_second_step(new.updated, new.recovery_codes[0], epoch)[1], 'recovery')

    def test_master_password_confirmation(self):
        with self.assertRaises(ValueError):
            validate_new_master('long enough passphrase!', 'not the same')
        with self.assertRaises(ValueError):
            validate_new_master('short', 'short')
        validate_new_master(MASTER, MASTER)

    def test_backward_compatible_encrypted_vault(self):
        old = new_data()
        del old['recovery_hashes']; del old['totp_last_counter']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'vault.aegis'
            write_vault(path, old, MASTER)
            data = read_vault(path, MASTER)
            self.assertEqual(data['recovery_hashes'], [])
            self.assertEqual(data['totp_last_counter'], -1)

    def test_encrypted_vault_never_contains_recovery_codes_or_totp_secret(self):
        epoch = 100000; secret = create_secret()
        en = enrol_totp(new_data(), secret, current_code(secret, epoch), epoch)
        blob = encrypt_data(en.updated, MASTER)
        self.assertNotIn(secret.encode(), blob)
        for code in en.recovery_codes:
            self.assertNotIn(code.encode(), blob)
        self.assertEqual(decrypt_data(blob, MASTER), en.updated)

    def test_failed_atomic_replace_preserves_previous_encrypted_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'vault.aegis'
            data = new_data(); write_vault(path, data, MASTER)
            previous = path.read_bytes()
            changed = copy.deepcopy(data)
            changed['entries'] = [{'account': 'not-saved', 'length': 24, 'revision': 1}]
            with mock.patch('aegis.vault.os.replace', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    write_vault(path, changed, MASTER)
            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(read_vault(path, MASTER), data)
            self.assertEqual(list(path.parent.glob('.aegis-*')), [])

    def test_consumption_can_be_persisted_and_remains_consumed_after_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'vault.aegis'; epoch = 100000; secret = create_secret()
            en = enrol_totp(new_data(), secret, current_code(secret, epoch), epoch)
            write_vault(path, en.updated, MASTER)
            loaded = read_vault(path, MASTER)
            used, _ = verify_second_step(loaded, en.recovery_codes[0], epoch)
            write_vault(path, used, MASTER)
            with self.assertRaises(ValueError):
                verify_second_step(read_vault(path, MASTER), en.recovery_codes[0], epoch)


if __name__ == '__main__':
    unittest.main()
