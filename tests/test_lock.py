"""PID 锁及跨进程退出恢复测试，仅使用临时密码库。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from 密码管理器 import 密码管理器


class VaultLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / '测试密码库.json'
        self.lock = self.path.with_suffix('.lock')

    def open(self, password=b'master'):
        manager = 密码管理器(str(self.path), password)
        self.addCleanup(manager.锁定)
        return manager

    def test_lock_contains_pid_and_rejects_second_instance(self):
        manager = self.open()
        self.assertEqual(self.lock.read_text(), str(os.getpid()))
        with self.assertRaisesRegex(ValueError, '正在被'):
            self.open()
        self.assertEqual(self.lock.read_text(), str(os.getpid()))
        manager.添加('demo', 'secret')
        manager.锁定()
        manager.锁定()  # 重复清理不能影响下一次打开。
        self.assertFalse(self.lock.exists())
        reopened = self.open()
        self.assertEqual(reopened.获取密码('demo'), 'secret')
        manager.锁定()
        self.assertTrue(self.lock.exists())

    def test_existing_live_pid_is_not_overwritten_or_deleted(self):
        self.lock.write_text(str(os.getpid()))
        with self.assertRaisesRegex(ValueError, str(os.getpid())):
            self.open()
        self.assertEqual(self.lock.read_text(), str(os.getpid()))
        self.assertFalse(self.path.exists())

    def test_empty_and_invalid_lock_are_replaced(self):
        for content in ('', 'invalid', '0', '-1'):
            with self.subTest(content=content):
                self.lock.write_text(content)
                manager = self.open()
                self.assertEqual(self.lock.read_text(), str(os.getpid()))
                manager.锁定()
                self.assertFalse(self.lock.exists())

    def test_failed_load_and_failed_create_release_lock(self):
        self.open().锁定()
        with self.assertRaises(ValueError):
            self.open(b'wrong')
        self.assertFalse(self.lock.exists())
        self.open().锁定()
        self.path.unlink()
        with patch('密码管理器.密码管理器._保存', side_effect=OSError('write failed')):
            with self.assertRaises(OSError):
                self.open()
        self.assertFalse(self.lock.exists())
        self.assertFalse(self.path.exists())

    def test_other_process_and_crash_recovery(self):
        code = '''
import sys
from 密码管理器 import 密码管理器
manager = 密码管理器(sys.argv[1], b'master')
print('ready', flush=True)
sys.stdin.read()
'''
        child = subprocess.Popen(
            [sys.executable, '-B', '-c', code, str(self.path)],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
            self.assertEqual(self.lock.read_text(), str(child.pid))
            with self.assertRaisesRegex(ValueError, '正在被'):
                self.open()
            child.kill()
            child.communicate(timeout=10)
            self.assertEqual(self.lock.read_text(), str(child.pid))
            manager = self.open()
            self.assertEqual(self.lock.read_text(), str(os.getpid()))
            manager.锁定()
            self.assertFalse(self.lock.exists())
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)

    def test_simultaneous_open_has_exactly_one_owner(self):
        code = """
import sys
from 密码管理器 import 密码管理器
sys.stdin.readline()
try:
    manager = 密码管理器(sys.argv[1], b'master')
except ValueError:
    print('blocked', flush=True)
else:
    print('opened', flush=True)
    sys.stdin.read()
"""
        children = []
        try:
            for _ in range(2):
                children.append(subprocess.Popen(
                    [sys.executable, '-B', '-c', code, str(self.path)],
                    cwd=Path(__file__).resolve().parents[1],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True,
                ))
            for child in children:
                child.stdin.write('go\n')
                child.stdin.flush()
            results = [child.stdout.readline().strip() for child in children]
            self.assertCountEqual(results, ['opened', 'blocked'])
            owner = children[results.index('opened')]
            self.assertEqual(self.lock.read_text(), str(owner.pid))
            for child in children:
                child.communicate(timeout=10)
                self.assertEqual(child.returncode, 0)
            self.assertFalse(self.lock.exists())
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=10)

    def test_normal_process_exit_removes_lock(self):
        result = subprocess.run(
            [sys.executable, '-B', '-c',
             "import sys; from 密码管理器 import 密码管理器; manager = 密码管理器(sys.argv[1], b'master')",
             str(self.path)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.path.exists())
        self.assertFalse(self.lock.exists())


if __name__ == '__main__':
    unittest.main()
