"""主密码校验格式：版本标识 + 32 字节随机盐 + SHA256(盐 + AES 密钥)。"""

from hashlib import sha256 as _SHA256
from hmac import compare_digest as _安全比较
from secrets import token_bytes as _随机字节


_格式标识 = b'PMHASH\x01'
_盐长度 = 32
_哈希长度 = 32


def 生成密码校验(加密密钥: bytes) -> bytes:
    """接收 SHA256(主密码) 得到的 AES 密钥，生成带盐校验数据。"""
    盐 = _随机字节(_盐长度)
    校验值 = _SHA256(盐 + 加密密钥).digest()
    return _格式标识 + 盐 + 校验值


def 验证密码校验(加密密钥: bytes, 校验数据: bytes) -> bool:
    """按文件中保存的盐验证密钥；拒绝旧格式或损坏的校验数据。"""
    if (len(校验数据) != len(_格式标识) + _盐长度 + _哈希长度
            or not 校验数据.startswith(_格式标识)):
        raise ValueError('密码哈希文件格式无效')
    盐起点 = len(_格式标识)
    盐终点 = 盐起点 + _盐长度
    盐 = 校验数据[盐起点:盐终点]
    校验值 = _SHA256(盐 + 加密密钥).digest()
    return _安全比较(校验值, 校验数据[盐终点:])
