import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from 命令行界面 import 命令行用户界面
from 密码管理器 import 密码管理器, 密码文件


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        before = Path.cwd()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, before)
        os.chdir(self.tmp.name)

    def test_missing_vault_confirmation(self):
        for answers in [('master', 'different'), ('',)]:
            with self.subTest(answers=answers):
                with patch('命令行界面.getpass', side_effect=answers), \
                        patch.object(命令行用户界面, '运行') as run, patch('builtins.print'):
                    命令行用户界面()
                run.assert_not_called()
                self.assertFalse(Path(密码文件).exists())
        with patch('命令行界面.getpass', side_effect=[' master ', ' master ']) as prompt, \
                patch.object(命令行用户界面, '运行') as run, patch('builtins.print'):
            ui = 命令行用户界面()
        self.assertEqual(prompt.call_count, 2)
        run.assert_called_once()
        self.assertEqual(ui.密码本.获取数量(), 0)
        self.assertEqual(密码管理器(密码文件, b' master ').获取数量(), 0)

    def test_existing_vault_only_prompts_once(self):
        manager = 密码管理器(密码文件, b'master')
        manager.添加('demo', 'secret')
        manager.锁定()
        with patch('命令行界面.getpass', return_value='master') as prompt, \
                patch.object(命令行用户界面, '运行') as run, patch('builtins.print'):
            ui = 命令行用户界面()
        prompt.assert_called_once()
        run.assert_called_once()
        self.assertFalse(Path(密码文件).with_suffix('.lock').exists())
        manager = 密码管理器(密码文件, b'master')
        self.assertEqual(manager.获取密码('demo'), 'secret')
        manager.锁定()

    def test_interrupted_command_loop_releases_lock(self):
        with patch('命令行界面.getpass', side_effect=['master', 'master']), \
                patch.object(命令行用户界面, '运行', side_effect=KeyboardInterrupt), \
                patch('builtins.print'):
            with self.assertRaises(KeyboardInterrupt):
                命令行用户界面()
        self.assertTrue(Path(密码文件).exists())
        self.assertFalse(Path(密码文件).with_suffix('.lock').exists())
