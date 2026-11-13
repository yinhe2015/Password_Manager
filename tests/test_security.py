"""安全回归测试仅使用临时合成密码库。"""
import base64
import hashlib
import json
import os
from pathlib import Path
import pickle
import tempfile
import unittest
from unittest.mock import patch

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from 密码管理器 import 密码管理器, 密码文件
from 修改密码 import 修改主密码
from 迁移旧数据 import 迁移旧数据, 生成密码校验

MASTER = b'test-only-master'


class UnsafeObject:
    def __reduce__(self):
        return print, ('SHOULD NEVER EXECUTE',)


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 密码文件

    def create(self):
        manager = 密码管理器(str(self.path), MASTER)
        manager.添加('private-service', ' saved password ', 'private-user', 'private-note')
        self.addCleanup(manager.锁定)
        return manager

    def legacy(self, malicious=False):
        key = hashlib.sha256(MASTER).digest()
        cipher = AES.new(key, AES.MODE_CBC)
        record = cipher.iv + cipher.encrypt(pad(' saved password '.encode(), 16))
        data = UnsafeObject() if malicious else {'private-service': [record, 'private-user', 'private-note']}
        (self.root / '密码.pkl').write_bytes(pickle.dumps(data))
        (self.root / '密码哈希.dat').write_bytes(生成密码校验(key))

    def test_roundtrip_and_crud(self):
        manager = self.create()
        self.assertFalse(manager.添加('private-service', 'duplicate'))
        manager.添加('other', 'second')
        self.assertFalse(manager.修改名称('private-service', 'other'))
        self.assertEqual(manager.获取数量(), 2)
        manager.修改名称('private-service', 'renamed')
        manager.修改密码('renamed', ' new password ')
        manager.修改用户名('renamed', None)
        manager.修改备注('renamed', 'changed')
        manager.移除('other')
        manager.锁定()
        reopened = 密码管理器(str(self.path), MASTER)
        self.assertEqual(list(reopened.读取所有()), [('renamed', ' new password ', None, 'changed')])
        self.assertNotIn(b'renamed', self.path.read_bytes())
        self.assertNotIn(b'changed', self.path.read_bytes())
        if os.name == 'posix':
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_wrong_password_does_not_write(self):
        self.create().锁定()
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            密码管理器(str(self.path), b'wrong')
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_vault_automatically_created(self):
        manager = 密码管理器(str(self.path), MASTER)
        self.assertTrue(self.path.exists())
        self.assertEqual(manager.获取数量(), 0)
        manager.锁定()
        self.assertEqual(密码管理器(str(self.path), MASTER).获取数量(), 0)

    def test_empty_password_does_not_create_vault(self):
        with self.assertRaises(ValueError):
            密码管理器(str(self.path), b'')
        self.assertFalse(self.path.exists())

    def test_tampering_rejected(self):
        self.create().锁定()
        original = self.path.read_bytes()
        for field in ('nonce', 'ciphertext', 'tag'):
            envelope = json.loads(original)
            value = bytearray(base64.b64decode(envelope[field]))
            value[0] ^= 1
            envelope[field] = base64.b64encode(value).decode()
            self.path.write_text(json.dumps(envelope))
            with self.assertRaises(ValueError, msg=field):
                密码管理器(str(self.path), MASTER)
        envelope = json.loads(original)
        envelope['header']['kdf']['n'] = 2**30
        self.path.write_text(json.dumps(envelope))
        with self.assertRaises(ValueError):
            密码管理器(str(self.path), MASTER)

    def test_failed_write_preserves_disk_and_memory(self):
        manager = self.create()
        original = self.path.read_bytes()
        with patch('密码管理器.os.replace', side_effect=OSError('simulated failure')):
            with self.assertRaises(OSError):
                manager.修改密码('private-service', 'lost')
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(manager.获取密码('private-service'), ' saved password ')
        self.assertEqual(set(self.root.iterdir()), {self.path, self.path.with_suffix(".lock")})

    def test_password_rotation_and_lock(self):
        manager = self.create()
        manager.锁定()
        with self.assertRaises(ValueError):
            修改主密码(str(self.path), b'wrong', b'new-master')
        修改主密码(str(self.path), MASTER, b'new-master')
        with self.assertRaises(ValueError):
            密码管理器(str(self.path), MASTER)
        self.assertEqual(密码管理器(str(self.path), b'new-master').获取数量(), 1)
        with self.assertRaises(ValueError):
            manager.添加('stale-session', 'password')
        manager.锁定()
        self.assertEqual(manager.获取数量(), 0)
        with self.assertRaises(ValueError):
            manager.添加('locked', 'password')

    def test_migration_preserves_every_field_and_archives_originals(self):
        self.legacy()
        old = {name: (self.root / name).read_bytes() for name in ('密码.pkl', '密码哈希.dat')}
        count, backup = 迁移旧数据(self.root, MASTER)
        self.assertEqual(count, 1)
        self.assertEqual(list(密码管理器(str(self.path), MASTER).读取所有()),
                         [('private-service', ' saved password ', 'private-user', 'private-note')])
        for name, content in old.items():
            self.assertEqual((backup / name).read_bytes(), content)
            self.assertFalse((self.root / name).exists())
        with self.assertRaises(FileExistsError):
            迁移旧数据(self.root, MASTER)

    def test_migration_wrong_password_missing_verifier_and_executable_pickle(self):
        self.legacy()
        original = (self.root / '密码.pkl').read_bytes()
        with self.assertRaises(ValueError):
            迁移旧数据(self.root, b'wrong')
        self.assertFalse(self.path.exists())
        (self.root / '密码哈希.dat').unlink()
        with self.assertRaises(FileNotFoundError):
            迁移旧数据(self.root, MASTER)
        self.assertEqual((self.root / '密码.pkl').read_bytes(), original)
        self.legacy(malicious=True)
        with patch('builtins.print') as printer:
            with self.assertRaises(ValueError):
                迁移旧数据(self.root, MASTER)
            printer.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_migration_write_failure_preserves_originals(self):
        self.legacy()
        with patch('密码管理器.密码管理器._保存', side_effect=OSError('simulated failure')):
            with self.assertRaises(OSError):
                迁移旧数据(self.root, MASTER)
        self.assertFalse(self.path.exists())
        self.assertTrue((self.root / '密码.pkl').exists())
        self.assertTrue((self.root / '密码哈希.dat').exists())


if __name__ == '__main__':
    unittest.main()
