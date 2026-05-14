# -*- coding: utf-8 -*-
"""
中文标准库：拷贝模块 (copy)
用法: 导入 拷贝
"""
from copy import *
import copy as _copy

浅拷贝 = _copy.copy
深拷贝 = _copy.deepcopy
错误 = _copy.Error

__all__ = [name for name in globals() if not name.startswith('_')]
