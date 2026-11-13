import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog, QPushButton
from 图形 import LoginWindow, PasswordManagerUI, ViewPasswordDialog, IdleLock
from 密码管理器 import 密码管理器, 密码文件


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_login_details_clipboard_and_lock(self):
        before = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                manager = 密码管理器(密码文件, b' test master ')
                manager.添加('demo', ' saved password ', 'user', 'notes')
                manager.锁定()
                login = LoginWindow()
                received = []
                login.login_success.connect(received.append)
                login.password_input.setText(' test master ')
                with patch.object(QInputDialog, 'getText') as confirmation:
                    login.verify_password()
                confirmation.assert_not_called()
                self.assertEqual(len(received), 1)
                self.assertEqual(login.password_input.text(), '')
                window = PasswordManagerUI(received[0])
                detail = ViewPasswordDialog(received[0], 'demo', window)
                self.assertEqual(detail.password_input.text(), ' saved password ')
                with patch.object(QMessageBox, 'information'):
                    detail.copy_password()
                self.assertEqual(self.app.clipboard().text(), ' saved password ')
                detail.clear_copied_password(self.app.clipboard(), ' saved password ')
                self.assertEqual(self.app.clipboard().text(), '')
                self.app.clipboard().setText('unrelated text')
                detail.clear_copied_password(self.app.clipboard(), ' saved password ')
                self.assertEqual(self.app.clipboard().text(), 'unrelated text')
                lock = IdleLock(self.app, received[0])
                self.assertEqual(lock.timer.interval(), 300000)
                lock.clear_secrets()
                self.assertEqual(received[0].获取数量(), 0)
                self.assertEqual(detail.password_input.text(), '')
                self.assertEqual(detail.original_data, {})
                self.assertEqual(self.app.clipboard().text(), '')
                lock.timer.stop()
                self.app.removeEventFilter(lock)
                self.app.aboutToQuit.disconnect(lock.clear_secrets)
                lock.deleteLater()
                detail.deleteLater()
                window.deleteLater()
                login.deleteLater()
                self.app.processEvents()
            finally:
                os.chdir(before)

    def test_missing_vault_requires_matching_confirmation(self):
        before = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                login = LoginWindow()
                received = []
                login.login_success.connect(received.append)
                self.assertNotIn('新建密码库', [b.text() for b in login.findChildren(QPushButton)])
                login.password_input.setText(' some master ')
                for confirmation, ok in [('different', True), (' some master ', False)]:
                    with self.subTest(confirmation=confirmation, ok=ok):
                        with patch.object(QInputDialog, 'getText', return_value=(confirmation, ok)), \
                                patch.object(QMessageBox, 'warning'):
                            login.verify_password()
                        self.assertFalse(Path(密码文件).exists())
                        self.assertEqual(received, [])
                with patch.object(QInputDialog, 'getText', return_value=(' some master ', True)):
                    login.verify_password()
                self.assertTrue(Path(密码文件).exists())
                self.assertEqual(len(received), 1)
                self.assertEqual(login.password_input.text(), '')
                received[0].锁定()
                reopened = 密码管理器(密码文件, b' some master ')
                self.assertEqual(reopened.获取数量(), 0)
                reopened.锁定()
                login.deleteLater()
                self.app.processEvents()
            finally:
                os.chdir(before)
