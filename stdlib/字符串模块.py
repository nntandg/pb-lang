# -*- coding: utf-8 -*-
"""
中文标准库：字符串模块 (string)
用法: 导入 字符串模块
"""
from string import *
import string as _string

小写字母 = _string.ascii_lowercase
大写字母 = _string.ascii_uppercase
英文字母 = _string.ascii_letters
数字字符 = _string.digits
十六进制字符 = _string.hexdigits
八进制字符 = _string.octdigits
标点符号 = _string.punctuation
空白字符 = _string.whitespace
可打印字符 = _string.printable
模板 = _string.Template
格式化器 = _string.Formatter

__all__ = [name for name in globals() if not name.startswith('_')]
