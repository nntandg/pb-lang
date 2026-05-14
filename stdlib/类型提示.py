# -*- coding: utf-8 -*-
"""
中文标准库：类型提示模块 (typing)
用法: 导入 类型提示
"""
from typing import *
import typing as _typing

任意 = _typing.Any
可选 = _typing.Optional
联合 = _typing.Union
列表 = _typing.List
字典 = _typing.Dict
元组 = _typing.Tuple
集合 = _typing.Set
可调用 = _typing.Callable
迭代器 = _typing.Iterator
可迭代 = _typing.Iterable
序列 = _typing.Sequence
类型 = _typing.Type
泛型 = _typing.Generic
类型变量 = _typing.TypeVar
最终 = _typing.Final
字面量 = getattr(_typing, 'Literal', None)

__all__ = [name for name in globals() if not name.startswith('_')]
