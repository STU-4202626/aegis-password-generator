import unittest
from aegis.security import generate_password, GROUPS
from aegis.totp import current_code, verify_code
from aegis.vault import new_data, encrypt_data, decrypt_data
from cryptography.exceptions import InvalidTag

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.secret = b'x'*32

    def test_reproducible_and_account_specific(self):
        args = ('a memorable phrase', 'github.com', 24, self.secret)
        value = generate_password(*args)
        self.assertEqual(value, generate_password(*args))
        self.assertNotEqual(value, generate_password('a memorable phrase', 'email.com', 24, self.secret))
        self.assertNotEqual(value, generate_password(*args, revision=2))
        self.assertEqual(len(value), 24)
        for group in GROUPS:
            self.assertTrue(any(c in group for c in value))

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            generate_password('phrase', 'github.com', 5, self.secret)
        with self.assertRaises(ValueError):
            generate_password('phrase','',24,self.secret)

    def test_vault_roundtrip_and_wrong_password(self):
        data = new_data()
        data['entries'].append({'account':'example.com','length':24,'revision':1})
        blob = encrypt_data(data, 'a sufficiently long master passphrase')
        self.assertEqual(decrypt_data(blob, 'a sufficiently long master passphrase'), data)
        with self.assertRaises(InvalidTag):
            decrypt_data(blob, 'a wrong but long passphrase')
        self.assertNotIn(b'example.com', blob)

    def test_totp(self):
        # RFC 6238 SHA1 vector (8 digits in spec; our implementation uses 6)
        secret = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'
        self.assertEqual(current_code(secret, 59), '287082')
        self.assertTrue(verify_code(secret, '287082', 59))
        self.assertFalse(verify_code(secret, '000000', 59))

if __name__ == '__main__':
    unittest.main()
