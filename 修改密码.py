from hashlib import sha256 as _SHA256
from pickle import load as _读取, dump as _写入
from os.path import exists as _路径存在

from Crypto.Cipher import AES as _AES算法
from Crypto.Util.Padding import pad as _填充, unpad as _解填充

def _aes加密(密码哈希: bytes, 明文: str) -> bytes:
    数据字节 = 明文.encode('utf-8')
    加密器 = _AES算法.new(密码哈希, _AES算法.MODE_CBC)
    加密数据 = 加密器.encrypt(_填充(数据字节, _AES算法.block_size))
    return 加密器.iv + 加密数据

def _aes解密(密码哈希: bytes, 密文: bytes) -> str:
    if len(密文) < _AES算法.block_size:
        raise ValueError(f'数据长度必须大于等于{_AES算法.block_size}字节')
    初始化向量 = 密文[:_AES算法.block_size]
    加密数据 = 密文[_AES算法.block_size:]
    解密器 = _AES算法.new(密码哈希, _AES算法.MODE_CBC, 初始化向量)
    解密数据 = _解填充(解密器.decrypt(加密数据), _AES算法.block_size)
    return 解密数据.decode('utf-8')

def 修改主密码(密码文件路径: str, 旧密码字节: bytes, 新密码字节: bytes):
    """
    修改密码管理器的主密码，并更新所有加密数据
    
    参数:
        密码文件路径: 密码数据文件的路径（如 'passwords.dat'）
        旧密码字节: 原主密码的bytes类型（如 b'old_password123'）
        新密码字节: 新主密码的bytes类型（如 b'new_password456'）
    
    返回:
        bool: 修改成功返回True，失败返回False
    
    异常:
        FileNotFoundError: 密码文件不存在
        ValueError: 旧密码验证失败或解密出错
    """
    # 1. 验证密码文件存在
    if not _路径存在(密码文件路径):
        raise FileNotFoundError(f"密码文件 {密码文件路径} 不存在")
    
    # 2. 验证旧密码（通过密码哈希文件）
    旧密码哈希 = _SHA256(旧密码字节).digest()

    密码哈希文件路径 = '密码哈希.dat'
    if _路径存在(密码哈希文件路径):
    
        with open(密码哈希文件路径, 'rb') as f:
            旧密码哈希 = f.read()
        
        if _SHA256(旧密码字节).digest() != 旧密码哈希:
            raise ValueError("旧密码验证失败，请输入正确的旧密码")
    else:
        print('密码哈希文件不存在, 取消验证')
    
    # 3. 读取原密码数据
    with open(密码文件路径, 'rb') as f:
        原数据 = _读取(f)
    
    # 4. 生成新旧密码的哈希
    
    新密码哈希 = _SHA256(新密码字节).digest()
    
    # 5. 遍历数据，解密后重新加密
    新数据 = {}
    try:
        for 名称, (加密密码, 用户名, 备注) in 原数据.items():
            # 用旧密码解密
            明文密码 = _aes解密(旧密码哈希, 加密密码)
            # 用新密码重新加密
            新加密密码 = _aes加密(新密码哈希, 明文密码)
            # 保存新数据
            新数据[名称] = [新加密密码, 用户名, 备注]
    except Exception as e:
        raise ValueError(f"解密/加密过程出错: {str(e)}")
    
    # 6. 写入新的密码数据
    with open(密码文件路径, 'wb') as f:
        _写入(新数据, f)
    
    # 7. 更新密码哈希文件
    with open(密码哈希文件路径, 'wb') as f:
        f.write(_SHA256(新密码哈希).digest())
    
    print(f"主密码修改成功！共更新 {len(新数据)} 条密码记录")
    return True

# ------------------- 使用示例 -------------------
if __name__ == "__main__":
    # 配置参数
    密码文件路径 = "密码.pkl"  # 你的密码数据文件路径
    旧密码 = b""  # 旧主密码
    新密码 = b""  # 新主密码
    
    try:
        # 执行主密码修改
        修改主密码(密码文件路径, 旧密码, 新密码)
    except Exception as e:
        print(f"修改失败: {e}")