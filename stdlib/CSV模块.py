# -*- coding: utf-8 -*-
"""
中文标准库：CSV 模块 (csv)
用法: 导入 CSV模块
"""
from csv import *
import csv as _csv

读取器 = _csv.reader
写入器 = _csv.writer
字典读取器 = _csv.DictReader
字典写入器 = _csv.DictWriter
注册方言 = _csv.register_dialect
获取方言 = _csv.get_dialect
列出方言 = _csv.list_dialects
注销方言 = _csv.unregister_dialect
字段大小限制 = _csv.field_size_limit

__all__ = [name for name in globals() if not name.startswith('_')]
