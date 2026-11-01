import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox
from 图形 import LoginWindow, PasswordManagerUI, ViewPasswordDialog, IdleLock
from 密码管理器 import 密码管理器, 默认密码文件


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_login_details_clipboard_and_lock(self):
        before = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                manager = 密码管理器(默认密码文件, b' test master ', 创建=True)
                manager.添加('demo', ' saved password ', 'user', 'notes')
                login = LoginWindow()
                received = []
                login.login_success.connect(received.append)
                login.password_input.setText(' test master ')
                login.verify_password()
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

    def test_missing_vault_login_never_creates_one(self):
        before = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                login = LoginWindow()
                login.password_input.setText('some master')
                with patch.object(QMessageBox, 'warning') as warning:
                    login.verify_password()
                warning.assert_called_once()
                self.assertFalse(Path(默认密码文件).exists())
                login.deleteLater()
                self.app.processEvents()
            finally:
                os.chdir(before)
