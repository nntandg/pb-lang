# -*- coding: utf-8 -*-
"""
中文标准库：哈希模块 (hashlib)
用法: 导入 哈希
"""
from hashlib import *
import hashlib as _hashlib

md5 = _hashlib.md5
sha1 = _hashlib.sha1
sha224 = _hashlib.sha224
sha256 = _hashlib.sha256
sha384 = _hashlib.sha384
sha512 = _hashlib.sha512
blake2b = _hashlib.blake2b
blake2s = _hashlib.blake2s

MD5 = md5
SHA1 = sha1
SHA224 = sha224
SHA256 = sha256
SHA384 = sha384
SHA512 = sha512

新建 = _hashlib.new
可用算法 = _hashlib.algorithms_available
保证算法 = _hashlib.algorithms_guaranteed


def _to_bytes(数据, 编码='utf-8'):
    if isinstance(数据, bytes):
        return 数据
    if isinstance(数据, bytearray):
        return bytes(数据)
    return str(数据).encode(编码)


def 摘要(算法, 数据, 编码='utf-8'):
    h = _hashlib.new(算法)
    h.update(_to_bytes(数据, 编码))
    return h.hexdigest()


def MD5文本(文本, 编码='utf-8'):
    return 摘要('md5', 文本, 编码)


def SHA1文本(文本, 编码='utf-8'):
    return 摘要('sha1', 文本, 编码)


def SHA224文本(文本, 编码='utf-8'):
    return 摘要('sha224', 文本, 编码)


def SHA256文本(文本, 编码='utf-8'):
    return 摘要('sha256', 文本, 编码)


def SHA384文本(文本, 编码='utf-8'):
    return 摘要('sha384', 文本, 编码)


def SHA512文本(文本, 编码='utf-8'):
    return 摘要('sha512', 文本, 编码)

__all__ = [name for name in globals() if not name.startswith('_')]
