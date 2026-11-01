"""v2 密码库：scrypt 派生密钥，AES-GCM 认证加密整个 JSON 数据库。"""
import atexit
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
from Crypto.Random import get_random_bytes

密码文件 = '密码.json'
最大文件大小 = 16 * 1024 * 1024 # 16MB
_KDF = {'name': 'scrypt', 'n': 131072, 'r': 8, 'p': 1}


def _json(数据):
    return json.dumps(数据, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _编码(数据):
    return base64.b64encode(数据).decode('ascii')


def _解码(数据):
    return base64.b64decode(数据, validate=True)


def _检查数据(数据):
    if type(数据) is not dict:
        raise ValueError('密码库数据格式无效')
    for 名称, 记录 in 数据.items():
        if (type(名称) is not str or type(记录) is not list or len(记录) != 3
                or type(记录[0]) is not str
                or any(x is not None and type(x) is not str for x in 记录[1:])):
            raise ValueError('密码库记录格式无效')


def _读取文件(路径):
    with open(路径, 'rb') as 文件:
        数据 = 文件.read(最大文件大小 + 1)
    if len(数据) > 最大文件大小:
        raise ValueError('密码库文件过大')
    return 数据


def _原子写入(路径, 数据, *, 仅新建=False):
    """只替换完整文件；临时文件始终仅允许当前用户读写。"""
    路径 = Path(路径)
    if len(数据) > 最大文件大小:
        raise ValueError('密码库文件过大')
    fd, 临时路径 = tempfile.mkstemp(prefix='.' + 路径.name + '.', dir=路径.parent)
    try:
        with os.fdopen(fd, 'wb') as 文件:
            文件.write(数据)
            文件.flush()
            os.fsync(文件.fileno())
        if 仅新建:
            # 原子发布且绝不覆盖已有文件，包括同时创建的密码库。
            os.link(临时路径, 路径)
        else:
            os.replace(临时路径, 路径)
        if os.name == 'posix':
            目录fd = os.open(路径.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(目录fd)
            finally:
                os.close(目录fd)
    finally:
        if os.path.exists(临时路径):
            os.unlink(临时路径)


def _进程存在(pid):
    if pid <= 0:
        return False
    if os.name == 'nt':
        # Windows 的 os.kill(pid, 0) 可能终止进程，改用只读进程查询。
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            error = ctypes.get_last_error()
            if error == 5:  # ERROR_ACCESS_DENIED：进程存在但无权查询。
                return True
            if error == 87:  # ERROR_INVALID_PARAMETER：PID 不存在。
                return False
            raise OSError(error, '无法检查锁文件中的进程')
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise ctypes.WinError(ctypes.get_last_error())
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class 密码管理器:
    def __init__(self, 密码文件路径: str, 密码字节: bytes):
        if not isinstance(密码字节, bytes) or not 密码字节:
            raise ValueError('主密码不能为空')
        self.密码文件路径 = Path(密码文件路径).resolve()
        self._密钥 = None
        self.密码数据 = {}
        self._锁文件 = None
        try:
            self._获取文件锁()
            self._加载(密码字节)
        except BaseException:
            self.锁定()
            raise
        atexit.register(self.锁定)

    def _加载(self, 密码字节):
        if not self.密码文件路径.exists():
            self._初始化密钥(密码字节)
            self.密码数据 = {}
            self._文件指纹 = None
            self._保存(self.密码数据)
        else:
            原文 = _读取文件(self.密码文件路径)
            try:
                外层 = json.loads(原文)
                if (type(外层) is not dict or set(外层) != {'header', 'nonce', 'ciphertext', 'tag'}):
                    raise ValueError()
                头 = 外层['header']
                if (type(头) is not dict or set(头) != {'format', 'version', 'kdf', 'salt'}
                        or 头['format'] != 'password-manager' or type(头['version']) is not int
                        or 头['version'] != 2 or _json(头['kdf']) != _json(_KDF)):
                    raise ValueError()
                盐 = _解码(头['salt'])
                nonce, tag = _解码(外层['nonce']), _解码(外层['tag'])
                if len(盐) != 32 or len(nonce) != 12 or len(tag) != 16:
                    raise ValueError()
                self._头 = 头
                self._密钥 = scrypt(密码字节, 盐, 32, N=_KDF['n'], r=8, p=1)
                解密器 = AES.new(self._密钥, AES.MODE_GCM, nonce=nonce)
                解密器.update(_json(头))
                明文 = 解密器.decrypt_and_verify(_解码(外层['ciphertext']), tag)
                self.密码数据 = json.loads(明文)
                _检查数据(self.密码数据)
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as 错误:
                raise ValueError('主密码错误或密码库已损坏/被篡改') from 错误
            self._文件指纹 = hashlib.sha256(原文).digest()

    def _获取文件锁(self):
        self._锁路径 = self.密码文件路径.with_suffix('.lock')
        while True:
            fd = os.open(self._锁路径, os.O_RDWR | os.O_CREAT, 0o600)
            文件 = os.fdopen(fd, 'r+b', buffering=0)
            try:
                try:
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as 错误:
                    raise ValueError('密码库正在被其他实例使用，无法打开') from 错误
                # 等待期间旧持有者可能已删除文件，不能锁住已经脱离路径的旧文件。
                try:
                    if not os.path.samestat(os.fstat(fd), self._锁路径.stat()):
                        文件.close()
                        continue
                except FileNotFoundError:
                    文件.close()
                    continue
                内容 = 文件.read(64).strip()
                try:
                    pid = int(内容)
                except ValueError:
                    pid = 0  # 空文件或损坏的锁也按残留锁处理。
                if _进程存在(pid):
                    raise ValueError(f'密码库正在被进程 {pid} 使用，无法打开')
                self._锁文件 = 文件
                文件.seek(0)
                文件.write(str(os.getpid()).encode('ascii'))
                文件.truncate()
                os.fsync(fd)
                return
            except BaseException:
                if self._锁文件 is not 文件:
                    文件.close()
                raise

    def _释放文件锁(self):
        文件 = self._锁文件
        if 文件 is None:
            return
        self._锁文件 = None
        try:
            try:
                属于自己 = os.path.samestat(os.fstat(文件.fileno()), self._锁路径.stat())
            except FileNotFoundError:
                属于自己 = False
            if os.name == 'nt':
                # Windows 必须先关闭句柄才能删除；PID 仍存活，其他实例会拒绝接管。
                文件.close()
            if 属于自己:
                self._锁路径.unlink(missing_ok=True)
        finally:
            文件.close()

    def _初始化密钥(self, 密码字节):
        盐 = get_random_bytes(32)
        self._头 = {'format': 'password-manager', 'version': 2, 'kdf': dict(_KDF), 'salt': _编码(盐)}
        self._密钥 = scrypt(密码字节, 盐, 32, N=_KDF['n'], r=8, p=1)

    def _封装(self, 数据):
        if self._密钥 is None:
            raise ValueError('密码库已锁定')
        _检查数据(数据)
        加密器 = AES.new(self._密钥, AES.MODE_GCM, nonce=get_random_bytes(12))
        加密器.update(_json(self._头))
        密文, tag = 加密器.encrypt_and_digest(_json(数据))
        return _json({'header': self._头, 'nonce': _编码(加密器.nonce),
                      'ciphertext': _编码(密文), 'tag': _编码(tag)})

    def _保存(self, 数据):
        if self._文件指纹 is None:
            if self.密码文件路径.exists():
                raise FileExistsError('密码库已存在')
        elif (not self.密码文件路径.exists()
              or hashlib.sha256(_读取文件(self.密码文件路径)).digest() != self._文件指纹):
            raise ValueError('密码库已被其他程序修改，请重新登录后操作')
        内容 = self._封装(数据)
        _原子写入(self.密码文件路径, 内容, 仅新建=self._文件指纹 is None)
        self._文件指纹 = hashlib.sha256(内容).digest()
        self.密码数据 = 数据

    def _副本(self):
        if self._密钥 is None:
            raise ValueError('密码库已锁定')
        return {名称: list(记录) for 名称, 记录 in self.密码数据.items()}

    def 锁定(self):
        self._密钥 = None
        self.密码数据 = {}
        atexit.unregister(self.锁定)
        self._释放文件锁()

    def 获取数量(self):
        return len(self.密码数据)

    def 获取所有名称(self):
        return self.密码数据.keys()

    def 读取所有(self):
        for 名称, (密码, 用户名, 备注) in self.密码数据.items():
            yield 名称, 密码, 用户名, 备注

    def 获取密码(self, 名称):
        return self.密码数据[名称][0]

    def 获取用户名(self, 名称):
        return self.密码数据[名称][1]

    def 获取备注(self, 名称):
        return self.密码数据[名称][2]

    def 添加(self, 名称, 密码, 用户名=None, 备注=None):
        数据 = self._副本()
        if 名称 in 数据:
            return False
        数据[名称] = [密码, 用户名, 备注]
        self._保存(数据)
        return True

    def 移除(self, 名称):
        数据 = self._副本()
        if 名称 not in 数据:
            return False
        del 数据[名称]
        self._保存(数据)
        return True

    def 修改名称(self, 旧名称, 新名称):
        数据 = self._副本()
        if 旧名称 not in 数据 or 新名称 in 数据:
            return False
        数据[新名称] = 数据.pop(旧名称)
        self._保存(数据)
        return True

    def _修改字段(self, 名称, 字段, 新值):
        数据 = self._副本()
        if 名称 not in 数据:
            return False
        数据[名称][字段] = 新值
        self._保存(数据)
        return True

    def 修改密码(self, 名称, 新密码):
        return self._修改字段(名称, 0, 新密码)

    def 修改用户名(self, 名称, 新用户名):
        return self._修改字段(名称, 1, 新用户名)

    def 修改备注(self, 名称, 新备注):
        return self._修改字段(名称, 2, 新备注)

    def 修改主密码(self, 新密码字节):
        if not isinstance(新密码字节, bytes) or not 新密码字节:
            raise ValueError('主密码不能为空')
        旧头, 旧密钥 = self._头, self._密钥
        try:
            数据 = self._副本()
            self._初始化密钥(新密码字节)
            self._保存(数据)
        except Exception:
            self._头, self._密钥 = 旧头, 旧密钥
            raise
