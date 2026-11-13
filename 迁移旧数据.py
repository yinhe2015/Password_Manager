"""一次性离线迁移；仅允许旧 pickle 中的基本数据类型，绝不加载类或函数。"""
from datetime import datetime
from getpass import getpass
import hashlib
import hmac
import io
import os
from pathlib import Path
import pickle
import secrets
import tempfile

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
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

from 密码管理器 import 密码管理器, 密码文件, _读取文件, _原子写入, _检查数据


class _受限读取器(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError('旧密码库含有可执行对象，已拒绝迁移')

    def persistent_load(self, pid):
        raise ValueError('旧密码库含有外部引用，已拒绝迁移')


def 读取旧数据(旧文件, 校验文件, 主密码):
    密钥 = hashlib.sha256(主密码).digest()
    校验 = _读取文件(校验文件)  # 缺失时拒绝，不能跳过验证。
    if len(校验) == 32:
        正确 = hmac.compare_digest(hashlib.sha256(密钥).digest(), 校验)
    else:
        正确 = 验证密码校验(密钥, 校验)
    if not 正确:
        raise ValueError('主密码错误')
    流 = io.BytesIO(_读取文件(旧文件))
    原数据 = _受限读取器(流).load()
    if 流.read(1) or type(原数据) is not dict:
        raise ValueError('旧密码库格式无效')
    数据 = {}
    for 名称, 记录 in 原数据.items():
        if (type(名称) is not str or type(记录) not in (list, tuple) or len(记录) != 3
                or type(记录[0]) is not bytes or len(记录[0]) < 32
                or len(记录[0]) % 16 != 0):
            raise ValueError('旧密码库记录格式无效')
        密文, 用户名, 备注 = 记录
        明文 = unpad(AES.new(密钥, AES.MODE_CBC, 密文[:16]).decrypt(密文[16:]), 16).decode('utf-8')
        数据[名称] = [明文, 用户名, 备注]
    _检查数据(数据)
    return 数据


def 迁移旧数据(目录, 主密码):
    目录 = Path(目录).resolve()
    旧文件, 校验文件 = 目录 / '密码.pkl', 目录 / '密码哈希.dat'
    新文件 = 目录 / 密码文件
    if 新文件.exists():
        raise FileExistsError('新密码库已存在，拒绝重复迁移或覆盖')
    原文件内容 = {文件: _读取文件(文件) for 文件 in (旧文件, 校验文件)}
    数据 = 读取旧数据(旧文件, 校验文件, 主密码)
    备份目录 = 目录 / ('旧格式备份-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3))
    备份目录.mkdir(mode=0o700)
    for 文件 in (旧文件, 校验文件):
        _原子写入(备份目录 / 文件.name, 原文件内容[文件], 仅新建=True)
    # 在私有临时目录中生成并核对，失败不会留下半成品目标库。
    with tempfile.TemporaryDirectory(prefix='.迁移-', dir=目录) as 临时目录:
        暂存 = Path(临时目录) / 密码文件
        管理器 = 密码管理器(str(暂存), 主密码)
        try:
            管理器._保存(数据)
            管理器.锁定()
            核对 = 密码管理器(str(暂存), 主密码)
            try:
                if 核对.密码数据 != 数据:
                    raise ValueError('迁移核对失败，原数据已保留')
            finally:
                核对.锁定()
            _原子写入(新文件, _读取文件(暂存), 仅新建=True)
        finally:
            管理器.锁定()
    # 新文件完整落盘并逐条核对通过后，才移除工作目录中的旧副本。
    if any(_读取文件(文件) != 内容 for 文件, 内容 in 原文件内容.items()):
        raise ValueError('迁移期间旧文件发生变化，新旧文件均已保留，请人工核对')
    旧文件.unlink()
    校验文件.unlink()
    return len(数据), 备份目录


if __name__ == '__main__':
    try:
        数量, 备份 = 迁移旧数据(Path(__file__).resolve().parent, getpass('旧主密码: ').encode('utf-8'))
        print(f'迁移成功，已核对 {数量} 条记录。旧格式备份：{备份.name}')
    except Exception as 错误:
        print(f'迁移失败: {错误}')
        raise SystemExit(1)
