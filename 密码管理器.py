from hashlib import sha256 as _SHA256
from pickle import load as _读取, dump as _写入
from os.path import exists as _路径存在

from Crypto.Cipher import AES as _AES算法
from Crypto.Util.Padding import pad as _填充, unpad as _解填充

class 加解密工具:
    def __init__(self, 密码字节: bytes):
        self.密码 = _SHA256(密码字节).digest()
        self._检查密码()

    def _检查密码(self) -> None:
        密码哈希文件路径 = '密码哈希.dat'

        密码_SHA256 = _SHA256(self.密码).digest()

        if _路径存在(密码哈希文件路径):
            with open(密码哈希文件路径, 'rb') as 文件:
                密码哈希 = 文件.read()
            if 密码_SHA256 != 密码哈希:
                raise ValueError('密码与密码哈希不匹配')
        else:
            print('警告: 密码哈希文件不存在, 将创建新文件')
            with open(密码哈希文件路径, 'wb') as 文件:
                文件.write(密码_SHA256)

    def 加密(self, 数据: str) -> bytes:
        数据字节 = 数据.encode('utf-8')
        加密器 = _AES算法.new(self.密码, _AES算法.MODE_CBC)
        加密数据 = 加密器.encrypt(_填充(数据字节, _AES算法.block_size))
        return 加密器.iv + 加密数据

    def 解密(self, 数据: bytes) -> str:
        if len(数据) < _AES算法.block_size:
            raise ValueError(f'数据长度必须大于等于{_AES算法.block_size}字节')
        初始化向量 = 数据[:_AES算法.block_size]
        加密数据 = 数据[_AES算法.block_size:]
        解密器 = _AES算法.new(self.密码, _AES算法.MODE_CBC, 初始化向量)
        解密数据 = _解填充(解密器.decrypt(加密数据), _AES算法.block_size)
        return 解密数据.decode('utf-8')

class 密码管理器:
    def __init__(self, 密码文件路径: str, 密码字节: bytes):
        self.密码文件路径 = 密码文件路径
        self._读取()
        self.加解密工具 = 加解密工具(密码字节)

    def _读取(self):
        if not _路径存在(self.密码文件路径):
            self.密码数据 = {}
            self._写入()
            return
        with open(self.密码文件路径,'rb') as 文件:
            self.密码数据 = _读取(文件)
    def _写入(self):
        with open(self.密码文件路径,'wb') as 文件:
            _写入(
                self.密码数据,
                文件,
            )

    def _存在(self,名称: str):
        return 名称 in self.密码数据.keys()

    def 获取数量(self):
        return len(self.密码数据)
    
    def 获取所有名称(self):
        return self.密码数据.keys()

    def 读取所有(self):
        for 名称, (加密密码,用户名,备注) in self.密码数据.items():
            yield 名称, self.加解密工具.解密(加密密码), 用户名, 备注

    def 获取密码(self, 名称: str) -> str:
        if not self._存在(名称):
            raise Exception(f'密码 {名称} 不存在')
        return self.加解密工具.解密(self.密码数据[名称][0])
    
    def 获取用户名(self, 名称: str):
        if not self._存在(名称):
            raise Exception(f'密码 {名称} 不存在')
        return self.密码数据[名称][1]
    
    def 获取备注(self, 名称: str):
        if not self._存在(名称):
            raise Exception(f'密码 {名称} 不存在')
        return self.密码数据[名称][2]

    def 添加(self, 名称: str, 密码: str, 用户名: str = None, 备注: str = None):
        if self._存在(名称):
            return False
        加密密码 = self.加解密工具.加密(密码)
        self.密码数据[名称] = [加密密码,用户名,备注]
        self._写入()
        return True

    def 移除(self, 名称: str):
        if not self._存在(名称):
            return False
        del self.密码数据[名称]
        self._写入()
        return True

    def 修改名称(self, 旧名称: str, 新名称: str):
        if not self._存在(旧名称):
            return False
        加密密码,用户名,备注 = self.密码数据[旧名称]
        del self.密码数据[旧名称]
        self.密码数据[新名称] = [加密密码,用户名,备注]
        self._写入()
        return True

    def 修改密码(self, 名称: str, 新密码: str):
        if not self._存在(名称):
            return False
        加密密码 = self.加解密工具.加密(新密码)
        self.密码数据[名称][0] = 加密密码
        self._写入()
        return True

    def 修改用户名(self, 名称: str,新用户名: str):
        if not self._存在(名称):
            return False
        self.密码数据[名称][1] = 新用户名
        self._写入()
        return True
    
    def 修改备注(self, 名称: str, 新备注: str):
        if not self._存在(名称):
            return False
        self.密码数据[名称][2] = 新备注
        self._写入()
        return True