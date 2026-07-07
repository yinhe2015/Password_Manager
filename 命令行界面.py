from os import chdir as _切换目录
from os.path import dirname as _获取上级目录
_切换目录(_获取上级目录(__file__))

from 密码管理器 import 密码管理器

class 命令行用户界面:
    空格 = ' '

    def _计算字符长度(self, 字符串: str) -> int:
        '''
        计算字符长度
        中文占用 2 个字符
        '''

        输出 = 0
        for 字符 in 字符串:
            if ord(字符) > 127:
                # 中文占用 2 个字符
                输出 += 2
            else:
                输出 += 1

        return 输出

    def __init__(self):
        print('欢迎使用 Python 密码管理器 作者: 张因和')

        解密密码 = input('请输入解密密码: ')
        if 解密密码 in ['取消','cancel','exit','quit','q']:
            print('取消')
            return

        解密密码字节 = 解密密码.encode('utf-8')

        try:
            self.密码本 = 密码管理器('./密码.pkl', 解密密码字节)
        except Exception as 错误:
            if str(错误) == '密码与密码哈希不匹配':
                print('密码错误')
                return
            from traceback import format_exc as _格式化异常
            print(f'加载密码失败: {_格式化异常()}')
            return

        self.初始化命令()

        self.运行()

    def 初始化命令(self):
        self.命令列表 = []
        self.命令列表.append([('help','h'), '显示帮助', self.显示帮助])
        self.命令列表.append([('add','a'), '添加密码 名称 密码 用户名(可选) 备注(可选)', self.添加])
        self.命令列表.append([('delete','del'), '删除密码 *名称', self.删除])
        self.命令列表.append([('read','rd'), '读取密码 *名称', self.读取])
        self.命令列表.append([('list','ls'), '列出所有密码', self.读取所有])
        self.命令列表.append([('rename','rn'), '重命名 旧名称 新名称', self.重命名])
        self.命令列表.append([('reset','rs'), '修改密码 名称 新密码', self.修改密码])
        self.命令列表.append([('resetusername','run'), '修改用户名 名称 新用户名', self.修改用户名])
        self.命令列表.append([('resetnotes','rns'), '修改备注 名称 新备注', self.修改备注])
        self.命令列表.append([('exit','quit','q'), '退出', '退出'])

    def 运行(self):
        while True:
            输入内容 = input('请输入命令(help 查看帮助): ')
            输入内容 = 输入内容.strip().split(' ')
            命令 = 输入内容[0]
            if 命令 == '':
                continue
            输入内容 = 输入内容[1:]
            命令函数 = None
            for 命令组, 描述, 函数 in self.命令列表:
                if 命令 in 命令组:
                    命令函数 = 函数
                    break
            if 命令函数 == '退出':
                break
            if 命令函数 is None:
                print(f'未知的命令: {命令}')
                continue

            try:
                命令函数(*输入内容)
            except Exception:
                # 可能是参数错误或函数有问题
                from traceback import format_exc as _格式化异常
                print(f'执行命令 {命令} 失败: {_格式化异常()}')

    def 显示帮助(self):
        命令字符串列表 = [('|'.join(命令组), 描述) for 命令组, 描述, 函数 in self.命令列表]
        命令字符串列表长度索引 = {命令字符串: self._计算字符长度(命令字符串) for 命令字符串, 描述 in 命令字符串列表}
        命令字符串列表最大长度 = max(命令字符串列表长度索引.values())

        print('帮助:')
        for 命令字符串, 描述 in 命令字符串列表:
            空格数量 = 命令字符串列表最大长度 - 命令字符串列表长度索引[命令字符串]
            空格字符串 = self.空格 * 空格数量
            print(f'{命令字符串}{空格字符串}: {描述}')

    def 添加(self, 名称, 密码, 用户名=None, 备注=None):
        if self.密码本.添加(名称, 密码, 用户名, 备注):
            print(f'添加成功: {名称!r}')
        else:
            print(f'密码已存在: {名称!r}')
    def 删除(self, *名称列表):
        if input(f'确认删除 {',' .join(名称列表)}? (y/n)') == 'y':
            for 名称 in 名称列表:
                if self.密码本.移除(名称):
                    print(f'删除成功: {名称!r}')
                else:
                    print(f'密码不存在: {名称!r}')
        else:
            print('取消删除')

    def _列出(self, 密码列表: list[tuple[str, str, str | None, str | None]]):
        # 计算名称和密码的长度, + 2 是为了在打印时留出 repr 中的引号
        名称长度索引 = {名称: self._计算字符长度(名称) for 名称, 密码, 用户名, 备注 in 密码列表}
        密码长度索引 = {密码: self._计算字符长度(密码) for 名称, 密码, 用户名, 备注 in 密码列表}
        用户名长度索引 = {用户名: self._计算字符长度(用户名) for 名称, 密码, 用户名, 备注 in 密码列表 if 用户名 != None}
        名称最长长度 = max(名称长度索引.values()) + 2
        密码最长长度 = max(密码长度索引.values()) + 2
        用户名最长长度 = max(用户名长度索引.values()) + 2 if len(用户名长度索引) > 0 else 0

        for 名称,密码,用户名,备注 in 密码列表:
            名称 = 名称.__repr__() + self.空格 * (名称最长长度 - 名称长度索引[名称])
            密码 = 密码.__repr__() + self.空格 * (密码最长长度 - 密码长度索引[密码])
            用户名 = (用户名.__repr__() if 用户名 != None else '无') + self.空格 * (用户名最长长度 - (用户名长度索引[用户名] if 用户名 != None else 0))
            备注 = 备注.__repr__() if 备注 != None else '无'

            print(f'{名称}: 密码={密码} 用户名={用户名} 备注={备注}')
    def 读取(self, *名称列表: tuple[str]):
        if len(名称列表) == 0:
            print('输入错误: 读取密码需要至少 1 个参数')
            return

        密码列表 = []
        for 名称 in 名称列表:
            密码 = self.密码本.获取密码(名称)
            用户名 = self.密码本.获取用户名(名称)
            备注 = self.密码本.获取备注(名称)
            密码列表.append((名称, 密码, 用户名, 备注))

        if len(密码列表) == 0:
            print('警告: 没有密码被读取')
            return

        self._列出(密码列表)
    def 读取所有(self):
        数量 = self.密码本.获取数量()
        if 数量 == 0:
            print('警告: 没有密码被存储')
        else:
            print(f'共存储 {数量} 个密码')
            密码列表 = list(self.密码本.读取所有())
            密码列表.sort(key=lambda x: x[0])
            self._列出(密码列表)

    def 重命名(self, 旧名称, 新名称):
        if 旧名称 == 新名称:
            print('错误: 旧名称和新名称不能相同')
        else:
            if self.密码本.修改名称(旧名称, 新名称):
                print(f'修改名称成功: {旧名称!r} -> {新名称!r}')
            else:
                print(f'密码不存在: {旧名称!r}')
    def 修改密码(self, 名称, 新密码):
        旧密码 = self.密码本.获取密码(名称)
        if 旧密码 == 新密码:
            print('错误: 新密码不能和旧密码相同')
        else:
            if self.密码本.修改密码(名称,新密码):
                print(f'修改密码成功: {名称!r} -> {新密码!r}')
            else:
                print(f'密码不存在: {名称!r}')
    def 修改用户名(self, 名称, 新用户名):
        旧用户名 = self.密码本.获取用户名(名称)
        if 旧用户名 == 新用户名:
            print('错误: 新用户名不能和旧用户名相同')
        else:
            if self.密码本.修改用户名(名称,新用户名):
                print(f'修改用户名成功: {名称!r} -> {新用户名!r}')
            else:
                print(f'密码不存在: {名称!r}')
    def 修改备注(self, 名称, 新备注):
        旧备注 = self.密码本.获取备注(名称)
        if 旧备注 == 新备注:
            print('错误: 新备注不能和旧备注相同')
        else:
            if self.密码本.修改备注(名称,新备注):
                print(f'修改备注成功: {名称!r} -> {新备注!r}')
            else:
                print(f'密码不存在: {名称!r}')

if __name__ == '__main__':
    命令行用户界面()