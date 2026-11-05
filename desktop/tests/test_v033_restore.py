"""v0.3.3: real encrypted restore and safety snapshots, all with dummy credentials."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.exceptions import InvalidTag

from aegis.vault import (new_data, read_vault, write_vault,
    restore_encrypted_backup, export_encrypted_backup)

MASTER = 'A strictly fictional master passphrase for backup tests 2026'
DIFFERENT = 'A separate fictional master passphrase for old backup tests!'


class RestoreBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.live = self.base / 'vault.aegis'
        self.old = self.base / 'backup.aegis'
        self.initial = new_data()
        self.initial['entries'] = [{'account':'updated.example', 'length':24, 'revision':3}]
        write_vault(self.live, self.initial, MASTER)
        self.snapshot = new_data()
        self.snapshot['entries'] = [{'account':'older.example', 'length':28, 'revision':1}]
        write_vault(self.old, self.snapshot, DIFFERENT)

    def test_restore_preserves_previous_ciphertext_and_changes_master(self):
        before = self.live.read_bytes()
        old_blob = self.old.read_bytes()
        rescue = restore_encrypted_backup(self.old, self.live, DIFFERENT)
        self.assertIsNotNone(rescue)
        self.assertTrue(rescue.exists())
        self.assertEqual(rescue.read_bytes(), before)
        self.assertEqual(self.live.read_bytes(), old_blob)
        self.assertEqual(read_vault(self.live, DIFFERENT), self.snapshot)
        self.assertEqual(read_vault(rescue, MASTER), self.initial)
        with self.assertRaises(InvalidTag):
            read_vault(self.live, MASTER)
        self.assertNotIn(b'older.example', self.live.read_bytes())

    def test_restore_without_existing_vault(self):
        self.live.unlink()
        safety = restore_encrypted_backup(self.old, self.live, DIFFERENT)
        self.assertIsNone(safety)
        self.assertEqual(read_vault(self.live, DIFFERENT), self.snapshot)

    def test_wrong_passphrase_never_changes_live_or_creates_safety_copy(self):
        before = self.live.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Incorrect backup master'):
            restore_encrypted_backup(self.old, self.live, MASTER)
        self.assertEqual(self.live.read_bytes(), before)
        self.assertEqual(list(self.base.glob('vault.pre-restore-*.aegis')), [])

    def test_corrupt_or_oversize_backup_rejected_without_changes(self):
        before = self.live.read_bytes()
        self.old.write_bytes(b'corrupt or incomplete vault')
        with self.assertRaises((ValueError, UnicodeDecodeError)):
            restore_encrypted_backup(self.old, self.live, DIFFERENT)
        self.assertEqual(self.live.read_bytes(), before)
        with mock.patch('aegis.vault.MAX_RESTORE_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                restore_encrypted_backup(self.old, self.live, DIFFERENT)
        self.assertEqual(self.live.read_bytes(), before)

    def test_refuses_backup_equal_to_active(self):
        before = self.live.read_bytes()
        with self.assertRaises(ValueError):
            restore_encrypted_backup(self.live, self.live, MASTER)
        self.assertEqual(self.live.read_bytes(), before)

    def test_atomic_replace_error_preserves_active_and_old_backup(self):
        before = self.live.read_bytes()
        with mock.patch('aegis.vault.os.replace', side_effect=OSError('disk trouble')):
            with self.assertRaises(OSError):
                restore_encrypted_backup(self.old, self.live, DIFFERENT)
        self.assertEqual(self.live.read_bytes(), before)
        self.assertEqual(read_vault(self.old, DIFFERENT), self.snapshot)
        safety = list(self.base.glob('vault.pre-restore-*.aegis'))
        self.assertEqual(len(safety), 1)
        self.assertEqual(safety[0].read_bytes(), before)
        self.assertEqual(list(self.base.glob('.aegis-restore-*')), [])

    def test_refuses_symlink_active_and_source_when_supported(self):
        symlink = self.base / 'symlink.aegis'
        try:
            symlink.symlink_to(self.old)
        except (NotImplementedError, OSError):
            self.skipTest('Symlinks not supported in this test environment')
        before = self.live.read_bytes()
        with self.assertRaisesRegex(ValueError, 'regular'):
            restore_encrypted_backup(symlink, self.live, DIFFERENT)
        self.assertEqual(self.live.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'symbolic link'):
            restore_encrypted_backup(self.old, symlink, DIFFERENT)


os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
    from aegis.gui import Aegis
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, 'Requires PySide6 on desktop')
class RestoreUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        previous = os.environ.get('AEGIS_DATA_DIR')
        os.environ['AEGIS_DATA_DIR'] = self.tmp.name
        self.addCleanup(self._revert_env, previous)
        self.live = Path(self.tmp.name) / 'vault.aegis'
        write_vault(self.live, new_data(), MASTER)
        self.backup = Path(self.tmp.name) / 'example-backup.aegis'
        data = new_data(); data['entries'] = [{'account':'restored.example', 'length':32, 'revision':2}]
        write_vault(self.backup, data, DIFFERENT)
        self.window = Aegis()
        self.addCleanup(self._close)

    def _revert_env(self, value):
        if value is None:
            os.environ.pop('AEGIS_DATA_DIR', None)
        else:
            os.environ['AEGIS_DATA_DIR'] = value

    def _close(self):
        self.qt.removeEventFilter(self.window)
        self.window.timer.stop()
        self.window.close()

    def test_restore_available_from_locked_screen_and_security_centre(self):
        self.assertIn('Restore', self.window.login_restore_button.text())
        self.assertIn('Restore', self.window.restore_button.text())
        self.assertIsNone(self.window.master)

    def test_gui_restore_requires_confirmation_and_stays_locked(self):
        from unittest.mock import patch
        with (patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes),
              patch.object(QMessageBox, 'information'),
              patch.object(QFileDialog, 'getOpenFileName', return_value=(str(self.backup),'AEGIS')),
              patch.object(self.window, 'ask_text', return_value=(DIFFERENT, True))):
            self.window.restore_vault()
        self.assertIsNone(self.window.master)
        self.assertIsNone(self.window.data)
        self.assertEqual(read_vault(self.live, DIFFERENT)['entries'][0]['account'], 'restored.example')
        self.assertEqual(len(list(Path(self.tmp.name).glob('vault.pre-restore-*.aegis'))), 1)

if __name__ == '__main__':
    unittest.main()
