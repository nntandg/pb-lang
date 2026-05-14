# -*- coding: utf-8 -*-
"""
中文标准库：路径模块 (pathlib)
用法: 导入 路径
"""
from pathlib import Path, PurePath, PosixPath, WindowsPath

class 中文路径(type(Path())):
    """pathlib.Path 子类，增加常用中文属性别名。"""
    @property
    def 名称(self):
        return self.name

    @property
    def 后缀(self):
        return self.suffix

    @property
    def 父目录(self):
        return 中文路径(self.parent)

    @property
    def 主干(self):
        return self.stem

    @property
    def 部件(self):
        return self.parts

    def 存在(self):
        return self.exists()

    def 是文件(self):
        return self.is_file()

    def 是目录(self):
        return self.is_dir()

    def 读取文本(self, 编码='utf-8'):
        return self.read_text(encoding=编码)

    def 写入文本(self, 内容, 编码='utf-8'):
        return self.write_text(内容, encoding=编码)

路径对象 = 中文路径
路径 = 中文路径
纯路径 = PurePath

# 常用构造/查询
def 当前目录():
    """返回当前工作目录的 Path 对象。"""
    return Path.cwd()

def 用户目录():
    """返回用户主目录的 Path 对象。"""
    return Path.home()

def 存在(路径值):
    return Path(路径值).exists()

def 是文件(路径值):
    return Path(路径值).is_file()

def 是目录(路径值):
    return Path(路径值).is_dir()

def 读取文本(路径值, 编码='utf-8'):
    return Path(路径值).read_text(encoding=编码)

def 写入文本(路径值, 内容, 编码='utf-8'):
    return Path(路径值).write_text(内容, encoding=编码)

__all__ = [
    'Path', 'PurePath', 'PosixPath', 'WindowsPath',
    '中文路径', '路径对象', '路径', '纯路径',
    '当前目录', '用户目录', '存在', '是文件', '是目录', '读取文本', '写入文本',
]
