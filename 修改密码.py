"""交互修改 v2 密码库的主密码，不在源码中保存密码。"""
from getpass import getpass
from pathlib import Path
from 密码管理器 import 密码管理器, 密码文件


def 修改主密码(密码文件路径: str, 旧密码字节: bytes, 新密码字节: bytes):
    管理器 = 密码管理器(密码文件路径, 旧密码字节)
    try:
        管理器.修改主密码(新密码字节)
    finally:
        管理器.锁定()
    return True


if __name__ == '__main__':
    try:
        旧密码 = getpass('原主密码: ').encode('utf-8')
        新密码 = getpass('新主密码: ')
        if 新密码 != getpass('再次输入新主密码: '):
            raise ValueError('两次新密码不一致')
        修改主密码(str(Path(__file__).resolve().parent / 密码文件), 旧密码, 新密码.encode('utf-8'))
        print('主密码修改成功')
    except Exception as 错误:
        print(f'修改失败: {错误}')
        raise SystemExit(1)
