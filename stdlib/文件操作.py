# -*- coding: utf-8 -*-
"""
中文标准库：文件操作模块
基于 pathlib 和内置 open，提供中文友好的文件操作 API
用法: 导入 文件操作
"""
import os
import shutil
from pathlib import Path

# 打开文件（简化版，返回文件对象）
打开 = open

# 路径类（pathlib.Path 的中文别名）
路径 = Path

# 文件操作函数
def 读取文件(文件路径, 编码='utf-8'):
    """读取整个文件内容"""
    with open(文件路径, 'r', encoding=编码) as f:
        return f.read()

def 写入文件(文件路径, 内容, 编码='utf-8'):
    """写入内容到文件（覆盖模式）"""
    with open(文件路径, 'w', encoding=编码) as f:
        f.write(内容)

def 追加文件(文件路径, 内容, 编码='utf-8'):
    """追加内容到文件末尾"""
    with open(文件路径, 'a', encoding=编码) as f:
        f.write(内容)

def 逐行读取(文件路径, 编码='utf-8'):
    """逐行读取文件，返回行列表"""
    with open(文件路径, 'r', encoding=编码) as f:
        return f.readlines()

def 写入行(文件路径, 行列表, 编码='utf-8'):
    """写入多行到文件"""
    with open(文件路径, 'w', encoding=编码) as f:
        f.writelines(行列表)

def 文件存在(文件路径):
    """检查文件或目录是否存在"""
    return os.path.exists(文件路径)

def 是文件(文件路径):
    """检查路径是否是文件"""
    return os.path.isfile(文件路径)

def 是目录(文件路径):
    """检查路径是否是目录"""
    return os.path.isdir(文件路径)

def 创建目录(目录路径, 父目录=True, 存在忽略=True):
    """创建目录"""
    if 父目录:
        os.makedirs(目录路径, exist_ok=存在忽略)
    else:
        os.mkdir(目录路径)

def 删除文件(文件路径):
    """删除文件"""
    os.remove(文件路径)

def 删除目录(目录路径, 递归=False):
    """删除目录"""
    if 递归:
        shutil.rmtree(目录路径)
    else:
        os.rmdir(目录路径)

def 列出目录(目录路径='.'):
    """列出目录内容"""
    return os.listdir(目录路径)

def 获取文件大小(文件路径):
    """获取文件大小（字节）"""
    return os.path.getsize(文件路径)

def 复制文件(源路径, 目标路径):
    """复制文件"""
    shutil.copy2(源路径, 目标路径)

def 移动文件(源路径, 目标路径):
    """移动文件或目录"""
    shutil.move(源路径, 目标路径)

def 重命名(旧名, 新名):
    """重命名文件或目录"""
    os.rename(旧名, 新名)

def 获取当前目录():
    """获取当前工作目录"""
    return os.getcwd()

def 切换目录(目录路径):
    """切换工作目录"""
    os.chdir(目录路径)

def 拼接路径(*路径片段):
    """拼接路径"""
    return os.path.join(*路径片段)

def 获取扩展名(文件路径):
    """获取文件扩展名"""
    return os.path.splitext(文件路径)[1]

def 获取文件名(文件路径):
    """获取文件名（不含路径）"""
    return os.path.basename(文件路径)

def 获取目录名(文件路径):
    """获取目录名"""
    return os.path.dirname(文件路径)

def 绝对路径(文件路径):
    """获取绝对路径"""
    return os.path.abspath(文件路径)

def 规范化路径(文件路径):
    """规范化路径"""
    return os.path.normpath(文件路径)
