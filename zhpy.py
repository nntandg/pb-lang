#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB 编程语言解释器
核心设计：中文语法 → Python 代码 → exec执行
支持逐行翻译+块级翻译，兼容 Python 生态
"""

import sys
import os
import re
import json
import types
import builtins
import keyword
from enum import Enum
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

PB_VERSION = "0.3.1"
PB_AUTHOR = "PengBooo / 彭博"
PB_LANGUAGE_NAME = "PB"

PB_ASCII_ART = r"""
 ____                  ____
|  _ \ ___ _ __   __ _| __ )  ___   ___   ___
| |_) / _ \ '_ \ / _` |  _ \ / _ \ / _ \ / _ \
|  __/  __/ | | | (_| | |_) | (_) | (_) | (_) |
|_|   \___|_| |_|\__, |____/ \___/ \___/ \___/
                 |___/
""".strip("\n")


def print_startup_page():
    """打印 PB 启动页，风格参考原生 Python 交互器欢迎信息。"""
    print(PB_ASCII_ART)
    print(f"PengBooo 编程语言 {PB_VERSION}")
    print(f"作者: {PB_AUTHOR}")
    print("输入 help 或 帮助 查看用法；输入 退出 离开。")


def print_help_page():
    """打印简洁帮助。"""
    print(f"PB {PB_VERSION} 快速帮助")
    print("用法:")
    print("  pb 文件.pb                         运行 PB 程序文件（推荐 .pb 后缀）")
    print("  pb 旧文件.zhpy                     运行历史 ZHPY 文件（兼容旧后缀）")
    print("  pb -c '输出(\"你好\")'             执行一行代码")
    print("  pb --compile 文件.pb               只翻译为 Python，不执行")
    print("  pb --version                       查看版本")
    print("交互模式:")
    print("  直接运行 pb 或 python3 zhpy.py 进入交互模式。")
    print("常用语法:")
    print("  输出(\"你好\")；如果 条件 则；对于 i 在 范围(3) 执行；定义 函数名(...):")


class ZHEnum(Enum):
    """带中文属性别名的枚举基类。"""
    @property
    def 名称(self):
        return self.name

    @property
    def 名字(self):
        return self.name

    @property
    def 值(self):
        return self.value

# ──────────────────────────────────────────────────────────────
# 第一部分：关键字/运算符映射表
# ──────────────────────────────────────────────────────────────

# 控制流关键字
CONTROL_KEYWORDS = {
    # 变量声明
    '将': 'let',
    '定义为': 'define_as',
    '令': 'let',
    '为': 'as',
    '变量': 'var',
    # 条件
    '如果': 'if',
    '则': ':',
    '那么': ':',
    '否则如果': 'elif',
    '否则': 'else',
    # 循环
    '当': 'while',
    '时循环': '',  # 特殊处理
    '结束循环': '',  # 结束标记
    '重复': 'for _ in range',
    '次': '):',
    '结束重复': '',
    '对于': 'for',
    '在': 'in',
    '中的每一个': 'in',
    '执行': ':',
    '结束对于': '',
    # 跳转
    '继续': 'continue',
    '跳出': 'break',
    '过': 'pass',
    '返回': 'return',
    # 异常
    '尝试': 'try',
    '捕获': 'except',
    '当错误为': 'except',
    '当任何错误': 'except Exception',
    '最终': 'finally',
    '抛出': 'raise',
    # 函数与类
    '定义': 'def',
    '定义函数': 'def',
    '参数为': '(',
    '结束定义': '',
    '定义类': 'class',
    '类': 'class',
    '枚举类': 'enum_class',
    '继承自': '(',
    '结束类定义': '',
    '实例化': 'self',
    '自身': 'self',
    '全局': 'global',
    '非局部': 'nonlocal',
    # 导入
    '导入': 'import',
    '从': 'from',
    '导出': 'import',
    '导入所有': 'import *',
    '作为': 'as',
    # 判断
    '为真如果': 'assert',
    '删除': 'del',
    '产生': 'yield',
    '从这里产生': 'yield from',
    # 类和方法装饰器
    '属性': '@property',
    '取属性值': '@getter',
    '设置属性值': '@setter',
    '类方法': '@classmethod',
    '静态方法': '@staticmethod',
    # 结构标记
    '开始': ':',
    '做': ':',
    '结束': '',  # 结束标记
    '的': 'of',  # 用于 的次方 语法
}

# 算术运算符
ARITH_OPS = {
    '加': '+',
    '减': '-',
    '乘': '*',
    '除以': '/',
    '整除': '//',
    '取余': '%',
    '的次方': '**',  # a 的 b 次方 → a ** b
    '次方': '**',
}

# 比较运算符
COMPARE_OPS = {
    '等于': '==',
    '不等于': '!=',
    '大于': '>',
    '小于': '<',
    '大于等于': '>=',
    '小于等于': '<=',
}

# 赋值运算符
ASSIGN_OPS = {
    '=': '=',
    '加等于': '+=',
    '减等于': '-=',
    '乘等于': '*=',
    '除等于': '/=',
    '整除等于': '//=',
    '取余等于': '%=',
    '幂等于': '**=',
    '与等于': '&=',
    '或等于': '|=',
    '异或等于': '^=',
    '左移等于': '<<=',
    '右移等于': '>>=',
}

# 逻辑运算符
LOGIC_OPS = {
    '与': 'and',
    '或': 'or',
    '非': 'not',
    '且': 'and',
    '或者': 'or',
    '不': 'not',
}

# 位运算符
BITWISE_OPS = {
    '位与': '&',
    '位或': '|',
    '位异或': '^',
    '位非': '~',
    '左移': '<<',
    '右移': '>>',
}

# 成员运算符
MEMBER_OPS = {
    '属于': 'in',
    '不属于': 'not in',
}

# 身份运算符
IDENTITY_OPS = {
    '是': 'is',
    '不是': 'is not',
}

# 内置函数映射
BUILTIN_MAP = {
    '输出': 'print',
    '输出无换行': 'print(end="")',
    '读取输入': 'input',
    '绝对值': 'abs',
    '全为真': 'all',
    '存在为真': 'any',
    '二进制': 'bin',
    '布尔': 'bool',
    '字节数组': 'bytearray',
    '字节': 'bytes',
    '可调用': 'callable',
    '字符': 'chr',
    '类方法': 'classmethod',
    '编译码': 'compile',
    '复数': 'complex',
    '删除属性': 'delattr',
    '字典': 'dict',
    '目录': 'dir',
    '商余数对': 'divmod',
    '枚举': 'enumerate',
    '计算表达式': 'eval',
    '执行代码': 'exec',
    '过滤': 'filter',
    '浮点': 'float',
    '格式化': 'format',
    '冻结集合': 'frozenset',
    '获取属性': 'getattr',
    '全局变量': 'globals',
    '有属性': 'hasattr',
    '哈希': 'hash',
    '散列': 'hash',
    '帮助': 'help',
    '十六进制': 'hex',
    '身份': 'id',
    '输入': 'input',
    '整数': 'int',
    '是实例': 'isinstance',
    '是子类': 'issubclass',
    '迭代器': 'iter',
    '长度': 'len',
    '列表': 'list',
    '局部变量': 'locals',
    '映射': 'map',
    '最大值': 'max',
    '最小值': 'min',
    '下一个': 'next',
    '对象': 'object',
    '八进制': 'oct',
    '打开': 'open',
    '评分': 'ord',
    '幂': 'pow',
    '打印': 'print',
    '属性': 'property',
    '范围': 'range',
    '表示': 'repr',
    '倒序': 'reversed',
    '四舍五入': 'round',
    '集合': 'set',
    '设置属性': 'setattr',
    '片段': 'slice',
    '排序': 'sorted',
    '静态方法': 'staticmethod',
    '字符串': 'str',
    '求和': 'sum',
    '超集': 'super',
    '元组': 'tuple',
    '类型': 'type',
    '变量词典': 'vars',
    '包含当前迭代': 'zip',
    '异常': 'Exception',
}

# 字面量映射
LITERAL_MAP = {
    '真': 'True',
    '假': 'False',
    '空': 'None',
}

# 组合成一个大的识别表
ALL_OPS = {}
for d in [ARITH_OPS, COMPARE_OPS, ASSIGN_OPS, LOGIC_OPS, BITWISE_OPS, MEMBER_OPS, IDENTITY_OPS]:
    ALL_OPS.update(d)

# 中文模块名映射表（中文模块名 → Python 模块名）
# 核心策略：常用模块映射到中文封装模块（stdlib/下的 .py 文件），
# 这样可以同时获得原模块功能 + 中文属性别名。
# 若需要原生英文模块，可直接使用英文名导入。
MODULE_NAME_MAP = {
    # → 中文封装模块（带中文别名）
    '数学': '数学',
    '随机': '随机',
    '时间': '时间',
    '日期时间': '日期时间',
    '正则': '正则',
    'json模块': 'json模块',
    '字符串模块': '字符串模块',
    '收集器': '收集器',
    '类型提示': '类型提示',
    '拷贝': '拷贝',
    '迭代工具': '迭代工具',
    '函数工具': '函数工具',
    '数学统计': '数学统计',
    '路径': '路径',
    '集合工具': '集合工具',
    'CSV模块': 'CSV模块',
    '哈希': '哈希',
    # → 原生英文模块（无中文封装或不常用）
    '系统': 'sys',
    '操作系统': 'os',
    '路径库': 'pathlib',
    '进程': 'multiprocessing',
    '线程': 'threading',
    '异常处理': 'traceback',
    '二进制数据': 'struct',
    '编码': 'codecs',
    '哈希库': 'hashlib',
    '网络': 'socket',
    'url模块': 'urllib',
    'http模块': 'http',
    'ftp模块': 'ftplib',
    'smtp模块': 'smtplib',
    '日志': 'logging',
    '调试': 'pdb',
    '单元测试': 'unittest',
    '表单操作': 'pickle',
    '压缩': 'gzip',
    'zip文件': 'zipfile',
    'tar文件': 'tarfile',
    'csv模块': 'csv',
    '配置解析': 'configparser',
    'xml模块': 'xml',
    'html模块': 'html',
    '网页解析': 'html.parser',
    'web服务': 'http.server',
    # → 文件操作
    '文件操作': '文件操作',
}

# 中文异常类映射表（用于 try...catch 语句）
# 这些映射会在 Translator 处理 "捕获 ..." 时使用
EXCEPTION_MAP = {
    # 常见运行时异常
    '零除错误': 'ZeroDivisionError',
    '值错误': 'ValueError',
    '类型错误': 'TypeError',
    '键错误': 'KeyError',
    '索引错误': 'IndexError',
    '属性错误': 'AttributeError',
    '文件未找到': 'FileNotFoundError',
    '文件已存在': 'FileExistsError',
    '权限错误': 'PermissionError',
    '输入输出错误': 'IOError',
    '运行时错误': 'RuntimeError',
    '内存错误': 'MemoryError',
    '导入错误': 'ImportError',
    '模块未找到': 'ModuleNotFoundError',
    '断言错误': 'AssertionError',
    '未实现错误': 'NotImplementedError',
    '递归错误': 'RecursionError',
    '系统错误': 'SystemError',
    '系统退出': 'SystemExit',
    '键盘中断': 'KeyboardInterrupt',
    '生成器退出': 'GeneratorExit',
    '停止迭代': 'StopIteration',
    '算术错误': 'ArithmeticError',
    '查找错误': 'LookupError',
    '溢出错误': 'OverflowError',
    '浮点错误': 'FloatingPointError',
    '引用错误': 'ReferenceError',
    '环境错误': 'EnvironmentError',
    '操作系统错误': 'OSError',
    '阻塞IO错误': 'BlockingIOError',
    '子进程错误': 'ChildProcessError',
    '连接中止': 'ConnectionAbortedError',
    '连接拒绝': 'ConnectionRefusedError',
    '连接重置': 'ConnectionResetError',
    '中断错误': 'InterruptedError',
    '是目录错误': 'IsADirectoryError',
    '非目录错误': 'NotADirectoryError',
    '超时错误': 'TimeoutError',
    '联网错误': 'ConnectionError',
    '无效字符集': 'UnicodeError',
    '编码错误': 'UnicodeEncodeError',
    '解码错误': 'UnicodeDecodeError',
    '映射错误': 'UnicodeTranslateError',
    '命名冲突': 'NameError',
    '未定义': 'UnboundLocalError',
    '语法错误': 'SyntaxError',
    '缺少引号': 'IndentationError',
    '缺少制表符': 'TabError',
    # 泛指
    '错误': 'Exception',
    '基础错误': 'BaseException',
}

# 用于词法分析的关键字集合和最大长度
ALL_KEYWORDS_SET = set(CONTROL_KEYWORDS) | set(ALL_OPS) | set(BUILTIN_MAP) | set(LITERAL_MAP)
MAX_KW_LEN = max(len(kw) for kw in ALL_KEYWORDS_SET) if ALL_KEYWORDS_SET else 1
# 普通标识符内部切分时，只切分控制流关键字和运算符（不切分内置函数和字面量）
SPLIT_KEYWORDS_SET = set(CONTROL_KEYWORDS) | set(ALL_OPS)
MAX_SPLIT_KW_LEN = max(len(kw) for kw in SPLIT_KEYWORDS_SET) if SPLIT_KEYWORDS_SET else 1

# ──────────────────────────────────────────────────────────────
# 第二部分：词法分析器
# ──────────────────────────────────────────────────────────────

class Token:
    """词法单元"""
    def __init__(self, type_, value, line=0, col=0):
        self.type = type_  # 'KEYWORD', 'OP', 'NAME', 'NUMBER', 'STRING', 'NEWLINE', 'INDENT', 'DEDENT', 'EOF'
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


class Lexer:
    """
    词法分析器：将中文代码字符串分解为 Token 序列
    支持逐行解析，兼容 Python 的缩进规则
    """

    def __init__(self, text):
        self.text = text
        self.lines = text.split('\n')
        self.pos = 0
        self.line = 1
        self.col = 0
        self.tokens = []
        self.indent_stack = [0]

    def error(self, msg):
        raise SyntaxError(f"[词法错误] 第{self.line}行第{self.col}列: {msg}")

    def tokenize(self):
        """主分词函数"""
        raw_lines = self.lines
        logical_lines = []

        # 第一遍：处理行连接符 (\)
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            while line.rstrip().endswith('\\') and i + 1 < len(raw_lines):
                line = line.rstrip()[:-1] + raw_lines[i + 1]
                i += 1
            logical_lines.append(line)
            i += 1

        for line_idx, line in enumerate(logical_lines, 1):
            self.line = line_idx
            self._tokenize_line(line)

        # 处理最后的 DEDENT
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token('DEDENT', '', self.line))

        self.tokens.append(Token('EOF', '', self.line))
        return self.tokens

    def _tokenize_line(self, line):
        """分析单行"""
        stripped = line.lstrip(' ')
        indent = len(line) - len(stripped)

        # 空行或纯注释行
        if not stripped or stripped.startswith('#'):
            return

        # 处理缩进
        if indent > self.indent_stack[-1]:
            self.indent_stack.append(indent)
            self.tokens.append(Token('INDENT', '', self.line))
        elif indent < self.indent_stack[-1]:
            while indent < self.indent_stack[-1]:
                self.indent_stack.pop()
                self.tokens.append(Token('DEDENT', '', self.line))
            if indent != self.indent_stack[-1]:
                self.error("缩进不一致")

        # 开始分析行内容
        self.col = indent
        i = 0
        text = stripped
        n = len(text)

        while i < n:
            ch = text[i]

            # 跳过空格
            if ch == ' ':
                i += 1
                self.col += 1
                continue

            # 注释
            if ch == '#':
                break

            # f-string / r-string / b-string 前缀字符串（如 f"hello {name}"）
            if ch in ('f', 'F', 'r', 'R', 'b', 'B') and i + 1 < n and text[i + 1] in ('"', "'"):
                start = i
                prefix = ch
                i += 1
                quote = text[i]
                i += 1
                while i < n and text[i] != quote:
                    if text[i] == '\\':
                        i += 2
                    else:
                        i += 1
                if i >= n:
                    self.error("未闭合的字符串")
                val = text[start + 2:i]
                i += 1
                self.tokens.append(Token('STRING', prefix + quote + val + quote, self.line, self.col))
                self.col += (i - start)
                continue

            # 字符串（支持三引号字符串）
            if ch in ('"', "'"):
                start = i
                quote = ch
                i += 1
                # 检测三引号
                if i + 1 < n and text[i] == quote and text[i + 1] == quote:
                    quote *= 3
                    i += 2
                    end_idx = text.find(quote, i)
                    if end_idx == -1:
                        self.error("未闭合的三引号字符串")
                    val = text[i:end_idx]
                    i = end_idx + 3
                else:
                    while i < n and text[i] != quote:
                        if text[i] == '\\':
                            i += 2
                        else:
                            i += 1
                    if i >= n:
                        self.error("未闭合的字符串")
                    val = text[start + 1:i]
                    i += 1
                self.tokens.append(Token('STRING', val, self.line, self.col))
                self.col += (i - start)
                continue

            # 数字（支持整数、浮点、复数、二/八/十六进制）
            if ch.isdigit() or (ch == '.' and i + 1 < n and text[i + 1].isdigit()):
                start = i
                # 检测进制前缀
                if text[i:i + 2] == '0b' or text[i:i + 2] == '0B':
                    i += 2
                    while i < n and text[i] in '01':
                        i += 1
                elif text[i:i + 2] == '0o' or text[i:i + 2] == '0O':
                    i += 2
                    while i < n and text[i] in '01234567':
                        i += 1
                elif text[i:i + 2] == '0x' or text[i:i + 2] == '0X':
                    i += 2
                    while i < n and text[i].lower() in '0123456789abcdef':
                        i += 1
                else:
                    while i < n and text[i].isdigit():
                        i += 1
                    if i < n and text[i] == '.':
                        i += 1
                        while i < n and text[i].isdigit():
                            i += 1
                    # 科学记数法
                    if i < n and text[i].lower() in 'ej':
                        i += 1
                        if i < n and text[i] in '+-':
                            i += 1
                        while i < n and text[i].isdigit():
                            i += 1
                num_str = text[start:i]
                self.tokens.append(Token('NUMBER', num_str, self.line, self.col))
                self.col += (i - start)
                continue

            # 识别中文/英文标识符和关键字（最长关键字匹配 + 普通标识符内部关键字检测）
            if ch.isalpha() or ch == '_' or '\u4e00' <= ch <= '\u9fff':
                start = i
                # 1) 尝试最长关键字匹配
                matched_kw = None
                matched_len = 0
                max_check = min(MAX_KW_LEN, n - i)
                for L in range(max_check, 0, -1):
                    substr = text[i:i + L]
                    if substr in ALL_KEYWORDS_SET:
                        # 单字符运算符如果后面紧跟标识符字符，则不单独切分
                        # 例如：加法（变量名） vs x 加 y（运算）
                        if L == 1 and i + 1 < n and (text[i + 1].isalnum() or text[i + 1] == '_' or '\u4e00' <= text[i + 1] <= '\u9fff'):
                            if substr in ALL_OPS:
                                continue
                        matched_kw = substr
                        matched_len = L
                        break

                if matched_kw:
                    # 如果匹配到的关键字/运算符后面紧跟标识符字符，
                    # 则跳过此匹配（避免把"当前"切分为"当"+"前"）
                    # 但多字符关键字（如"如果"、"否则"）通常不会出现在普通标识符内，所以仍然匹配
                    if i + matched_len < n:
                        next_ch = text[i + matched_len]
                        is_next_id = next_ch.isalnum() or next_ch == '_' or '\u4e00' <= next_ch <= '\u9fff'
                        if is_next_id:
                            # 运算符：总是跳过（如 "加法"中的"加"）
                            if matched_kw in ALL_OPS:
                                matched_kw = None
                            # 单字符控制流关键字：只跳过容易与常用词汇混淆的
                            elif matched_len == 1 and matched_kw in CONTROL_KEYWORDS:
                                if matched_kw in ('当', '为', '在', '过'):
                                    matched_kw = None
                            # 内置函数和字面量：如果后面紧跟标识符，也跳过
                            # 避免 类型错误 被切分为 类型 + 错误
                            elif matched_kw in BUILTIN_MAP or matched_kw in LITERAL_MAP:
                                matched_kw = None
                    if matched_kw:
                        word = matched_kw
                        i += matched_len
                    else:
                        # 重置为普通标识符读取
                        j = i
                        while j < n and (text[j].isalnum() or text[j] == '_' or '\u4e00' <= text[j] <= '\u9fff'):
                            found_kw = False
                            if j + 1 < n:
                                max_l2 = min(MAX_SPLIT_KW_LEN, n - (j + 1))
                                for L2 in range(max_l2, 0, -1):
                                    substr = text[j + 1:j + 1 + L2]
                                    if substr in SPLIT_KEYWORDS_SET and substr not in ('在', '类', '取余'):
                                        found_kw = True
                                        break
                            if found_kw:
                                j += 1
                                break
                            j += 1
                        word = text[i:j]
                        i = j
                else:
                    # 2) 不是关键字开头，读取普通标识符
                    # 但在读取过程中检查下一个位置是否有控制流/运算符关键字开头
                    j = i
                    while j < n and (text[j].isalnum() or text[j] == '_' or '\u4e00' <= text[j] <= '\u9fff'):
                        found_kw = False
                        if j + 1 < n:
                            max_l2 = min(MAX_SPLIT_KW_LEN, n - (j + 1))
                            for L2 in range(max_l2, 0, -1):
                                substr = text[j + 1:j + 1 + L2]
                                if substr in SPLIT_KEYWORDS_SET and substr not in ('在', '类', '取余'):
                                    found_kw = True
                                    break
                        if found_kw:
                            j += 1
                            break
                        j += 1
                    word = text[i:j]
                    i = j

                # 分类
                if word in CONTROL_KEYWORDS:
                    self.tokens.append(Token('KEYWORD', word, self.line, self.col))
                elif word in ALL_OPS:
                    self.tokens.append(Token('OP', word, self.line, self.col))
                elif word in BUILTIN_MAP:
                    self.tokens.append(Token('BUILTIN', word, self.line, self.col))
                elif word in LITERAL_MAP:
                    self.tokens.append(Token('LITERAL', word, self.line, self.col))
                else:
                    self.tokens.append(Token('NAME', word, self.line, self.col))
                self.col += len(word)
                continue

            # 单字符运算符
            if ch in '+-*/%=<>!&|^~@':
                start = i
                # 检查双字符运算符
                if i + 1 < n:
                    two = text[i:i + 2]
                    if two in ('**', '//', '==', '!=', '<=', '>=', '<<', '>>', '+=', '-=', '*=', '/=', '//=', '%=', '**=', '&=', '|=', '^='):
                        self.tokens.append(Token('OP', two, self.line, self.col))
                        i += 2
                        self.col += 2
                        continue
                self.tokens.append(Token('OP', ch, self.line, self.col))
                i += 1
                self.col += 1
                continue

            # 括号
            if ch in '()[]{},.:;':
                self.tokens.append(Token('PUNCT', ch, self.line, self.col))
                i += 1
                self.col += 1
                continue

            # 未知字符
            self.error(f"未知字符: '{ch}'")

        self.tokens.append(Token('NEWLINE', '\n', self.line))


# ──────────────────────────────────────────────────────────────
# 第三部分：语法分析与翻译
# ──────────────────────────────────────────────────────────────

class Translator:
    """
    中文 → Python 翻译器
    将 Token 序列翻译为 Python 代码
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current = tokens[0] if tokens else None
        self.output = []
        self.indent_level = 0
        self.in_class_body = False  # 跟踪是否在类定义体内
        self.class_indent_level = -1  # 类定义所在缩进级别
        self.pending_decorator_block = False  # 属性:/类方法:/静态方法: 的伪块
        self.skip_indent_levels = 0  # 伪块产生的缩进层数，不输出到 Python
        self.decorator_block_base_indent = None  # 伪块对应的 Python 缩进层
        self.pending_method_decorator = None  # 影响下一个函数参数的装饰器类型

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current = self.tokens[self.pos]
        else:
            self.current = Token('EOF', '', 0)

    def error(self, msg):
        raise SyntaxError(f"[语法错误] 第{self.current.line}行: {msg}")

    def peek(self, offset=1):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token('EOF', '', 0)

    def expect(self, type_, value=None):
        if self.current.type != type_:
            raise SyntaxError(f"预期 {type_}，但得到 {self.current.type}({self.current.value!r}) 在第{self.current.line}行")
        if value is not None and self.current.value != value:
            raise SyntaxError(f"预期 '{value}'，但得到 '{self.current.value}' 在第{self.current.line}行")
        self.advance()

    def translate(self):
        """主翻译入口"""
        while self.current.type != 'EOF':
            stmt = self.parse_statement()
            if stmt:
                self.emit(stmt)
            if self.current.type == 'NEWLINE':
                self.advance()
        return '\n'.join(self.output)

    def emit(self, code):
        indent = '    ' * self.indent_level
        self.output.append(indent + code)

    def parse_statement(self):
        """解析单条语句"""
        tok = self.current

        if tok.type == 'EOF':
            return None
        if tok.type == 'NEWLINE':
            self.advance()
            return None

        # 处理缩进
        if tok.type == 'INDENT':
            if self.pending_decorator_block:
                # 装饰器块只是中文语法分组，不增加 Python 缩进
                self.pending_decorator_block = False
                self.skip_indent_levels += 1
                self.decorator_block_base_indent = self.indent_level
            else:
                self.indent_level += 1
            self.advance()
            return None
        if tok.type == 'DEDENT':
            if self.skip_indent_levels > 0 and self.indent_level == self.decorator_block_base_indent:
                self.skip_indent_levels -= 1
                if self.skip_indent_levels == 0:
                    self.decorator_block_base_indent = None
            else:
                self.indent_level -= 1
                # 只有当退出到类定义层之前时，才标记离开类体
                if self.in_class_body and self.indent_level < self.class_indent_level:
                    self.in_class_body = False
            self.advance()
            return None

        # 英文/原生 Python 装饰器兼容：@property / @xxx.setter / @staticmethod 等
        if tok.type == 'OP' and tok.value == '@':
            return self.parse_python_decorator_statement()

        # 英文关键字兼容（测试文件中可能混用 def/if/for/yield）
        if tok.type == 'NAME' and tok.value == 'def':
            return self.parse_english_func_def()
        if tok.type == 'NAME' and tok.value == 'if':
            return self.parse_english_if_statement()
        if tok.type == 'NAME' and tok.value == 'yield':
            return self.parse_english_yield_statement()
        if tok.type == 'NAME' and tok.value == 'for':
            return self.parse_english_for_statement()

        # 变量定义 / 赋值（'定义' 已在 KEYWORDS_MAP 中，由 parse_keyword_statement 处理）
        if tok.type in ('NAME', 'LITERAL') or (tok.type == 'KEYWORD' and tok.value in ('将', '令')):
            return self.parse_assignment_or_expr()

        # 关键字语句
        if tok.type == 'KEYWORD':
            stmt = self.parse_keyword_statement()
            if stmt is not None:
                return stmt
            # 未被识别的关键字（如 自身），回退到赋值/表达式
            return self.parse_assignment_or_expr()

        # 函数调用 / 以内置名作为变量赋值
        if tok.type == 'BUILTIN':
            if self.peek().type == 'OP' and self.peek().value in ASSIGN_OPS:
                return self.parse_assignment_or_expr()
            return self.parse_builtin_call()

        # 表达式语句
        return self.parse_expression_statement()

    def parse_assignment_or_expr(self):
        """解析赋值或表达式"""
        # 查看是否是复合赋值（中文特有的“将...定义为...”）
        if self.current.value == '将':
            return self.parse_define_statement()

        if self.current.value == '令':
            return self.parse_let_statement()

        left = self.parse_expression()

        # 检查赋值运算符
        if self.current.type == 'OP' and self.current.value in ASSIGN_OPS:
            op = ASSIGN_OPS[self.current.value]
            self.advance()
            right = self.parse_expression()
            return f"{left} {op} {right}"

        if self.current.type == 'OP' and self.current.value == '=':
            self.advance()
            right = self.parse_expression()
            return f"{left} = {right}"

        return left

    def parse_define_statement(self):
        """解析“将x定义为...”"""
        self.advance()  # 跳过 '将'
        if self.current.type not in ('NAME', 'OP', 'BUILTIN'):
            self.error("将后面必须跟变量名")
        name = self.current.value
        if name == '自身':
            name = '自身'
        self.advance()
        self.expect('KEYWORD', '定义为')
        value = self.parse_expression()
        return f"{name} = {value}"

    def parse_let_statement(self):
        """解析“令x为...”"""
        self.advance()  # 跳过 '令'
        if self.current.type not in ('NAME', 'OP', 'BUILTIN'):
            self.error("令后面必须跟变量名")
        name = self.current.value
        if name == '自身':
            name = '自身'
        self.advance()
        self.expect('KEYWORD', '为')
        value = self.parse_expression()
        return f"{name} = {value}"

    def parse_keyword_statement(self):
        """解析关键字引导的语句"""
        kw = self.current.value

        # 条件语句
        if kw == '如果':
            return self.parse_if_statement()
        if kw == '否则如果':
            return self.parse_elif_statement()
        if kw == '否则':
            return self.parse_else_statement()

        # 循环
        if kw == '当':
            return self.parse_while_statement()
        if kw == '重复':
            return self.parse_repeat_statement()
        if kw == '对于':
            return self.parse_for_statement()

        # 跳转
        if kw in ('继续', '跳出', '过', '返回'):
            return self.parse_jump_statement()

        # 函数定义
        if kw == '定义函数':
            return self.parse_func_def()
        if kw == '定义':
            return self.parse_func_def()

        # 类定义
        if kw == '定义类':
            return self.parse_class_def()

        # 枚举类定义（枚举类 名称: → class 名称(Enum):）
        if kw == '枚举类':
            return self.parse_enum_class_def()

        # 简写类定义（类 类名:）
        if kw == '类':
            return self.parse_class_def_shorthand()

        # 装饰器声明（属性: / 类方法: / 静态方法: → @property / @classmethod / @staticmethod）
        if kw in ('属性', '取属性值', '设置属性值', '类方法', '静态方法'):
            return self.parse_decorator_declaration()

        # 异常
        if kw == '尝试':
            return self.parse_try_statement()
        if kw == '捕获':
            return self.parse_except_statement()
        if kw == '最终':
            return self.parse_finally_statement()
        if kw == '抛出':
            return self.parse_raise_statement()

        # 导入
        if kw == '导入':
            return self.parse_import_statement()
        if kw == '从':
            return self.parse_from_import_statement()

        # 断言
        if kw == '为真如果':
            return self.parse_assert_statement()

        # 删除
        if kw == '删除':
            return self.parse_del_statement()

        # 生成器
        if kw == '产生':
            return self.parse_yield_statement()

        return None

    def parse_if_statement(self):
        self.advance()  # 跳过 '如果'
        cond = self.parse_expression()
        # 检查是否有 '则' / '那么' / ':'
        if self.current.type == 'KEYWORD' and self.current.value in ('则', '那么'):
            self.advance()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        return f"if {cond}:"

    def parse_elif_statement(self):
        self.advance()
        cond = self.parse_expression()
        if self.current.type == 'KEYWORD' and self.current.value in ('则', '那么'):
            self.advance()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        return f"elif {cond}:"

    def parse_else_statement(self):
        self.advance()
        if self.current.type == 'KEYWORD' and self.current.value in ('则', '那么'):
            self.advance()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        return "else:"

    def parse_while_statement(self):
        self.advance()  # 跳过 '当'
        cond = self.parse_expression()
        # 跳过 '时循环' 或 ':'
        if self.current.type == 'KEYWORD' and self.current.value == '时循环':
            self.advance()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        return f"while {cond}:"

    def parse_repeat_statement(self):
        self.advance()  # 跳过 '重复'
        count = self.parse_expression()
        # 跳过 '次' 或 ':'
        if self.current.type == 'KEYWORD' and self.current.value == '次':
            self.advance()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        return f"for _ in range({count}):"

    def parse_for_statement(self):
        self.advance()  # 跳过 '对于'
        vars_ = []
        while not ((self.current.type == 'KEYWORD' and self.current.value == '在') or (self.current.type == 'NAME' and self.current.value == 'in')):
            if self.current.type in ('EOF', 'NEWLINE'):
                self.error("for 循环缺少 在/in")
            if self.current.type == 'PUNCT' and self.current.value == ',':
                vars_.append(',')
                self.advance()
                continue
            vars_.append(self.current.value)
            self.advance()
        var = ' '.join(vars_).replace(' , ', ', ')
        # 跳过 在/in
        self.advance()
        iterable = self.parse_expression()
        # 生成器方法常见中文简写：对于 x 在 obj.生成xxx 执行 → for x in obj.生成xxx():
        if isinstance(iterable, str) and '.生成' in iterable and not iterable.endswith(')'):
            iterable = f"{iterable}()"
        # 跳过 '中的每一个' 或 '里的每一个' 或 '执行'
        if self.current.type == 'KEYWORD' and self.current.value == '中的每一个':
            self.advance()
        if self.current.type == 'KEYWORD' and self.current.value == '执行':
            self.advance()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        return f"for {var} in {iterable}:"

    def parse_jump_statement(self):
        kw = self.current.value
        self.advance()
        if kw == '返回':
            if self.current.type != 'NEWLINE' and self.current.type != 'EOF' and self.current.type != 'DEDENT':
                val = self.parse_expression()
                return f"return {val}"
            return "return"
        return CONTROL_KEYWORDS[kw]

    def parse_func_def(self):
        """解析函数定义（包括类方法）

        在类体内且没有参数时自动添加 self（支持类方法简写语法）
        """
        self.advance()  # 跳过 '定义函数' 或 '定义'
        name_parts = []
        while self.current.type in ('NAME', 'KEYWORD', 'BUILTIN'):
            # 参数为 是参数起始标记，不能并入函数名
            if self.current.type == 'KEYWORD' and self.current.value == '参数为':
                break
            name_parts.append(self.current.value)
            self.advance()
        name = ''.join(name_parts)
        params = []

        # 检查括号参数语法：定义 __init__(自身, 名字)
        if self.current.type == 'PUNCT' and self.current.value == '(':
            self.advance()
            while self.current.type != 'PUNCT' or self.current.value != ')':
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                param = self.current.value
                if param == '自身':
                    param = 'self'
                params.append(param)
                self.advance()
            self.advance()  # 跳过 ')'
        # 检查参数（Phase 2 语法：参数为 a, b）
        elif self.current.type == 'KEYWORD' and self.current.value == '参数为':
            self.advance()
            while self.current.type not in ('NEWLINE', 'EOF', 'KEYWORD'):
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                param = self.current.value
                if param == '自身':
                    param = 'self'
                params.append(param)
                self.advance()
        elif self.current.type == 'PUNCT' and self.current.value == ':':
            # 支持带冒号的语法：定义 函数名:
            self.advance()

        # 消费函数定义冒号
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()

        # 在类体内且没有参数时，根据装饰器/方法名自动补参数
        if self.in_class_body and not params:
            if self.pending_method_decorator == 'classmethod':
                params = ['cls']
            elif self.pending_method_decorator == 'staticmethod':
                if name in ('加', '乘'):
                    params = ['a', 'b']
                else:
                    params = []
            elif name.startswith('设置'):
                # 中文 setter 简写：def 设置年龄: ... 值 ...
                # 调用形态通常是 obj.设置年龄(30)，需要接收 value 参数。
                params = ['self', '值']
            else:
                params = ['self']
        self.pending_method_decorator = None

        result = f"def {name}({', '.join(params)}):"
        return result

    def parse_english_func_def(self):
        """兼容英文 def 函数定义：def 名称: / def 名称(a, b):"""
        self.advance()  # 跳过 def
        name = self.current.value
        if name == '自身':
            name = '自身'
        self.advance()
        params = []
        if self.current.type == 'PUNCT' and self.current.value == '(':
            self.advance()
            while self.current.type != 'PUNCT' or self.current.value != ')':
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                param = self.current.value
                if param == '自身':
                    param = 'self'
                params.append(param)
                self.advance()
            self.advance()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        if self.in_class_body and not params:
            if self.pending_method_decorator == 'classmethod':
                params = ['cls']
            elif self.pending_method_decorator == 'staticmethod':
                if name in ('加', '乘'):
                    params = ['a', 'b']
                else:
                    params = []
            elif name.startswith('设置'):
                params = ['self', '值']
            else:
                params = ['self']
        self.pending_method_decorator = None
        return f"def {name}({', '.join(params)}):"

    def parse_english_if_statement(self):
        self.advance()  # 跳过 if
        cond = self.parse_expression()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        return f"if {cond}:"

    def parse_english_yield_statement(self):
        self.advance()  # 跳过 yield
        if self.current.type == 'NAME' and self.current.value == 'from':
            self.advance()
            expr = self.parse_expression()
            if isinstance(expr, str) and '.生成' in expr and not expr.endswith(')'):
                expr = f"{expr}()"
            return f"yield from {expr}"
        expr = self.parse_expression()
        return f"yield {expr}"

    def parse_english_for_statement(self):
        self.advance()  # 跳过 for
        vars_ = []
        while not (self.current.type == 'NAME' and self.current.value == 'in'):
            if self.current.type == 'PUNCT' and self.current.value == ',':
                vars_.append(',')
                self.advance()
                continue
            vars_.append(self.current.value)
            self.advance()
        self.advance()  # 跳过 in
        iterable = self.parse_expression()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        return f"for {' '.join(vars_).replace(' , ', ', ')} in {iterable}:"

    def parse_class_def(self):
        """解析类定义"""
        self.advance()  # 跳过 '定义类'
        name = self.current.value
        if name == '自身':
            name = '自身'
        self.advance()
        bases = []
        # 检查继承
        if self.current.type == 'KEYWORD' and self.current.value == '继承自':
            self.advance()
            while self.current.type not in ('NEWLINE', 'EOF', 'KEYWORD'):
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                bases.append(self.current.value)
                self.advance()

        # 消费冒号（支持 定义类 类名: 语法）
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()

        # 标记进入类体（后续的方法定义需要自动加 self）
        self.in_class_body = True
        self.class_indent_level = self.indent_level  # 记录类定义所在的缩进层

        # 构建类定义代码
        if bases:
            return f"class {name}({', '.join(bases)}):"
        else:
            return f"class {name}:"

    def parse_class_def_shorthand(self):
        """解析简写类定义语法（类 类名: / 类 类名(父类):）"""
        self.advance()  # 跳过 '类'
        name = self.current.value
        if name == '自身':
            name = '自身'
        self.advance()

        bases = []
        # 检查继承（括号语法：类 狗(动物):）
        if self.current.type == 'PUNCT' and self.current.value == '(':
            self.advance()
            while self.current.type != 'PUNCT' or self.current.value != ')':
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                bases.append(self.current.value)
                self.advance()
            self.advance()  # 跳过 ')'

        # 消费冒号
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()

        # 标记进入类体
        self.in_class_body = True
        self.class_indent_level = self.indent_level

        if bases:
            return f"class {name}({', '.join(bases)}):"
        else:
            return f"class {name}:"

    def parse_enum_class_def(self):
        """解析枚举类定义：枚举类 颜色: → class 颜色(Enum):"""
        self.advance()  # 跳过 '枚举类'
        if self.current.type not in ('NAME', 'KEYWORD', 'BUILTIN'):
            self.error("枚举类后面必须跟类名")
        name = self.current.value
        self.advance()
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
        self.in_class_body = True
        self.class_indent_level = self.indent_level
        return f"class {name}(ZHEnum):"

    def parse_python_decorator_statement(self):
        """解析原生 Python 装饰器行，如 @property / @name.setter。"""
        self.advance()  # 跳过 @
        parts = []
        while self.current.type not in ('NEWLINE', 'EOF'):
            parts.append(self.current.value)
            self.advance()
        decorator = '@' + ''.join(parts)
        if decorator == '@classmethod':
            self.pending_method_decorator = 'classmethod'
        elif decorator == '@staticmethod':
            self.pending_method_decorator = 'staticmethod'
        else:
            self.pending_method_decorator = None
        return decorator

    def parse_decorator_declaration(self):
        """解析装饰器声明（属性:/类方法:/静态方法:）

        中文语法:
            属性:
                def 获取xxx:
                    ...

        翻译为 Python:
            @property
            def get_xxx(self):
                ...
        """
        decorator_map = {
            '属性': '',
            '取属性值': '',
            '设置属性值': '',
            '类方法': '@classmethod',
            '静态方法': '@staticmethod',
        }
        kw = self.current.value
        self.advance()  # 跳过装饰器关键字

        # 消费冒号
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()

        # 生成装饰器代码
        dec_code = decorator_map.get(kw, f'@{kw}')
        # 装饰器后的缩进只是中文分组，不能变成 Python 缩进
        self.pending_decorator_block = True
        if kw == '类方法':
            self.pending_method_decorator = 'classmethod'
        elif kw == '静态方法':
            self.pending_method_decorator = 'staticmethod'
        else:
            self.pending_method_decorator = None
        return dec_code

    def parse_try_statement(self):
        self.advance()
        return "try:"

    def parse_except_statement(self):
        """解析捕获异常语句
        支持:
          捕获
          捕获 零除错误
          捕获 零除错误 作为 e
          捕获 当错误为 零除错误
          捕获 当错误为 零除错误 作为 e
          捕获 当任何错误
        """
        self.advance()  # 跳过 '捕获'
        exc_type = 'Exception'
        exc_var = ''

        # 检查是否有 '当错误为' 或 '当任何错误'
        if self.current.type == 'KEYWORD' and self.current.value == '当错误为':
            self.advance()
            if self.current.type in ('NAME', 'KEYWORD', 'BUILTIN'):
                exc_type = EXCEPTION_MAP.get(self.current.value, self.current.value)
                self.advance()
        elif self.current.type == 'KEYWORD' and self.current.value == '当任何错误':
            self.advance()
            exc_type = 'Exception'
        elif self.current.type in ('NAME', 'KEYWORD', 'BUILTIN'):
            # 直接跟随异常类名
            exc_name = self.current.value
            exc_type = EXCEPTION_MAP.get(exc_name, exc_name)
            if exc_type == exc_name and exc_name.endswith('错误'):
                exc_type = EXCEPTION_MAP.get(exc_name[:-2] + '错误', exc_name)
            self.advance()

        # 检查是否有变量别名（作为 x）
        if self.current.type == 'KEYWORD' and self.current.value == '作为':
            self.advance()
            if self.current.type in ('NAME', 'KEYWORD', 'BUILTIN'):
                exc_var = self.current.value
                self.advance()

        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()

        if exc_var:
            return f"except {exc_type} as {exc_var}:"
        return f"except {exc_type}:"

    def parse_finally_statement(self):
        self.advance()
        return "finally:"

    def parse_raise_statement(self):
        self.advance()
        if self.current.type != 'NEWLINE':
            exc = self.parse_expression()
            for zh_exc, py_exc in EXCEPTION_MAP.items():
                if exc == zh_exc or exc.startswith(f"{zh_exc}("):
                    exc = py_exc + exc[len(zh_exc):]
                    break
            return f"raise {exc}"
        return "raise"

    def parse_import_statement(self):
        """解析导入语句
        支持:
          导入 xxx
          导入 xxx 作为 yyy
          导入 xxx, yyy, zzz
          导入 零除错误
          导入 零除错误 作为 e
        """
        self.advance()  # 跳过 '导入'
        modules = []
        while self.current.type not in ('NEWLINE', 'EOF'):
            if self.current.type == 'PUNCT' and self.current.value == ',':
                self.advance()
                continue
            # 获取名称
            if self.current.type in ('NAME', 'KEYWORD', 'BUILTIN'):
                name = self.current.value
                self.advance()
            else:
                name = self.current.value
                self.advance()

            # 检查是否是异常类
            if name in EXCEPTION_MAP:
                # 异常类特殊处理：直接导入异常类到当前命名空间
                py_exc = EXCEPTION_MAP[name]
                modules.append(py_exc)
            else:
                # 普通模块名映射
                py_mod = MODULE_NAME_MAP.get(name, name)
                # 检查是否有别名
                alias = None
                if self.current.type == 'KEYWORD' and self.current.value == '作为':
                    self.advance()
                    if self.current.type in ('NAME', 'KEYWORD', 'BUILTIN'):
                        alias = self.current.value
                        self.advance()
                if alias:
                    modules.append(f"{py_mod} as {alias}")
                else:
                    modules.append(py_mod)
        return f"import {', '.join(modules)}"

    def parse_from_import_statement(self):
        """解析从...导入语句
        支持:
          从 xxx 导入 yyy
          从 xxx 导入 yyy 作为 zzz
          从 xxx 导入 *
          从 xxx 导入 a, b, c
          从 . 导入 xxx (相对导入)
        """
        self.advance()  # 跳过 '从'
        # 获取模块名（支持相对导入的点号）
        module_parts = []
        while self.current.type not in ('NEWLINE', 'EOF', 'KEYWORD'):
            if self.current.type == 'PUNCT' and self.current.value == '.':
                module_parts.append('.')
                self.advance()
            elif self.current.type in ('NAME', 'KEYWORD', 'BUILTIN', 'OP'):
                module_parts.append(self.current.value)
                self.advance()
            else:
                break
        module = ''.join(module_parts)
        # 中文模块名映射
        # 特殊处理相对导入（以点开头）
        if module.startswith('.'):
            py_module = module  # 相对导入保留原样
        else:
            py_module = MODULE_NAME_MAP.get(module, module)
        self.expect('KEYWORD', '导入')
        items = []
        while self.current.type not in ('NEWLINE', 'EOF'):
            if self.current.type == 'PUNCT' and self.current.value == ',':
                self.advance()
                continue
            if self.current.type == 'OP' and self.current.value == '*':
                self.advance()
                return f"from {py_module} import *"
            if self.current.type == 'NAME' and self.current.value == '所有':
                self.advance()
                return f"from {py_module} import *"
            # 获取导入项名
            if self.current.type in ('NAME', 'KEYWORD', 'BUILTIN'):
                item_name = self.current.value
                self.advance()
            else:
                item_name = self.current.value
                self.advance()
            # 检查是否有别名
            alias = None
            if self.current.type == 'KEYWORD' and self.current.value == '作为':
                self.advance()
                if self.current.type in ('NAME', 'KEYWORD', 'BUILTIN'):
                    alias = self.current.value
                    self.advance()
            if alias:
                items.append(f"{item_name} as {alias}")
            else:
                items.append(item_name)
        return f"from {py_module} import {', '.join(items)}"

    def parse_assert_statement(self):
        self.advance()
        expr = self.parse_expression()
        msg = ''
        if self.current.type == 'PUNCT' and self.current.value == ',':
            self.advance()
            msg = self.parse_expression()
            return f"assert {expr}, {msg}"
        return f"assert {expr}"

    def parse_del_statement(self):
        self.advance()
        target = self.parse_expression()
        return f"del {target}"

    def parse_yield_statement(self):
        self.advance()
        if self.current.type == 'KEYWORD' and self.current.value == '从':
            self.advance()
            expr = self.parse_expression()
            if isinstance(expr, str) and '.生成' in expr and not expr.endswith(')'):
                expr = f"{expr}()"
            return f"yield from {expr}"
        expr = self.parse_expression()
        return f"yield {expr}"

    def parse_builtin_call(self):
        """解析内置函数调用"""
        builtin_name = BUILTIN_MAP.get(self.current.value, self.current.value)
        self.advance()

        # 检查是否带括号
        if self.current.type == 'PUNCT' and self.current.value == '(':
            self.advance()
            args = []
            while self.current.type != 'PUNCT' or self.current.value != ')':
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                arg = self.parse_expression()
                args.append(arg)
            self.advance()  # 跳过 ')'
            # 跳过 NEWLINE
            while self.current.type == 'NEWLINE':
                self.advance()
            # 检查后面是否有冒号
            if self.current.type == 'PUNCT' and self.current.value == ':':
                self.advance()
                return f"{builtin_name}({', '.join(args)}):"
            return f"{builtin_name}({', '.join(args)})"

        # 无括号，查看后面的表达式
        args = []
        while self.current.type not in ('NEWLINE', 'EOF', 'DEDENT', 'PUNCT'):
            if self.current.type == 'PUNCT' and self.current.value == ',':
                self.advance()
                continue
            arg = self.parse_expression()
            if arg:
                args.append(arg)

        # 检查后面是否有冒号
        if self.current.type == 'PUNCT' and self.current.value == ':':
            self.advance()
            return f"{builtin_name}({', '.join(args)}):"
        return f"{builtin_name}({', '.join(args)})"

    def parse_builtin_call_with_colon(self):
        """解析带冒号的内置函数调用（如 print("..."):）"""
        # 解析函数调用
        builtin_name = BUILTIN_MAP.get(self.current.value, self.current.value)
        self.advance()

        # 检查是否带括号
        if self.current.type == 'PUNCT' and self.current.value == '(':
            self.advance()
            args = []
            while self.current.type != 'PUNCT' or self.current.value != ')':
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                arg = self.parse_expression()
                args.append(arg)
            self.advance()  # 跳过 ')'
            return f"{builtin_name}({', '.join(args)}):"

        # 无括号
        return f"{builtin_name}():"

    def parse_expression_statement(self):
        """解析表达式语句"""
        expr = self.parse_expression()
        return expr

    def parse_expression(self):
        """解析表达式（支持运算符优先级和逗号元组）"""
        left = self.parse_or()
        if self.current.type == 'PUNCT' and self.current.value == ',':
            items = [left]
            while self.current.type == 'PUNCT' and self.current.value == ',':
                self.advance()
                if self.current.type in ('NEWLINE', 'EOF', 'DEDENT'):
                    break
                items.append(self.parse_or())
            return ', '.join(items)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.current.type == 'OP' and self.current.value in ('或', '或者'):
            op = LOGIC_OPS[self.current.value]
            self.advance()
            right = self.parse_and()
            left = f"({left} {op} {right})"
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.current.type == 'OP' and self.current.value in ('与', '且'):
            op = LOGIC_OPS[self.current.value]
            self.advance()
            right = self.parse_not()
            left = f"({left} {op} {right})"
        return left

    def parse_not(self):
        if self.current.type == 'OP' and self.current.value in ('非', '不'):
            self.advance()
            operand = self.parse_not()
            return f"(not {operand})"
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_bit_or()
        # 合并比较、成员、身份运算符
        all_compare = {}
        all_compare.update(COMPARE_OPS)
        all_compare.update(MEMBER_OPS)
        all_compare.update(IDENTITY_OPS)
        all_compare.update({'==': '==', '!=': '!=', '>': '>', '<': '<', '>=': '>=', '<=': '<='})
        while self.current.type == 'OP' and self.current.value in all_compare:
            op = all_compare[self.current.value]
            self.advance()
            right = self.parse_bit_or()
            left = f"({left} {op} {right})"
        return left

    def parse_bit_or(self):
        left = self.parse_bit_xor()
        while self.current.type == 'OP' and self.current.value == '位或':
            self.advance()
            right = self.parse_bit_xor()
            left = f"({left} | {right})"
        return left

    def parse_bit_xor(self):
        left = self.parse_bit_and()
        while self.current.type == 'OP' and self.current.value == '位异或':
            self.advance()
            right = self.parse_bit_and()
            left = f"({left} ^ {right})"
        return left

    def parse_bit_and(self):
        left = self.parse_shift()
        while self.current.type == 'OP' and self.current.value == '位与':
            self.advance()
            right = self.parse_shift()
            left = f"({left} & {right})"
        return left

    def parse_shift(self):
        left = self.parse_arith()
        while self.current.type == 'OP' and self.current.value in ('左移', '右移'):
            op = BITWISE_OPS[self.current.value]
            self.advance()
            right = self.parse_arith()
            left = f"({left} {op} {right})"
        return left

    def parse_arith(self):
        left = self.parse_term()
        while self.current.type == 'OP' and self.current.value in ('加', '减', '+', '-'):
            op = '+' if self.current.value in ('加', '+') else '-'
            self.advance()
            right = self.parse_term()
            left = f"({left} {op} {right})"
        return left

    def parse_term(self):
        left = self.parse_power()
        while self.current.type == 'OP' and self.current.value in ('乘', '除以', '整除', '取余', '*', '/', '//', '%'):
            op_map = {'乘': '*', '除以': '/', '整除': '//', '取余': '%', '*': '*', '/': '/', '//': '//', '%': '%'}
            op = op_map[self.current.value]
            self.advance()
            right = self.parse_power()
            left = f"({left} {op} {right})"
        return left

    def parse_power(self):
        left = self.parse_unary()
        # 支持 "的次方" 语法：a 的 b 次方 → a ** b
        if self.current.type in ('OP', 'KEYWORD') and self.current.value == '的':
            self.advance()
            right = self.parse_unary()
            if self.current.type == 'OP' and self.current.value == '次方':
                self.advance()
                return f"({left} ** {right})"
        # 支持 "的次方" 组合运算符
        elif self.current.type == 'OP' and self.current.value == '的次方':
            self.advance()
            right = self.parse_unary()
            return f"({left} ** {right})"
        elif self.current.type == 'OP' and self.current.value == '**':
            self.advance()
            right = self.parse_unary()
            return f"({left} ** {right})"
        return left

    def parse_unary(self):
        if self.current.type == 'OP' and self.current.value in ('加', '减', '位非', '+', '-', '~'):
            if self.current.value in ('加', '+'):
                self.advance()
                return f"(+{self.parse_unary()})"
            elif self.current.value in ('减', '-'):
                self.advance()
                return f"(-{self.parse_unary()})"
            elif self.current.value in ('位非', '~'):
                self.advance()
                return f"(~{self.parse_unary()})"
        return self.parse_postfix()

    def parse_postfix(self):
        left = self.parse_atom()

        while True:
            # 属性访问或方法调用：对象.属性 或 对象.方法()
            # 支持多 token 属性名合并（如 文件操作.获取 当前目录 → 文件操作.获取当前目录）
            if self.current.type == 'PUNCT' and self.current.value == '.':
                self.advance()
                attr_parts = []
                while self.current.type in ('NAME', 'KEYWORD', 'BUILTIN', 'OP'):
                    # 这些是语句/表达式边界，不能并入属性名
                    if self.current.type == 'KEYWORD' and self.current.value in ('执行', '则', '那么'):
                        break
                    # 属性名中允许“追加”等中文词被词法器拆成 NAME + 运算符；
                    # 但如果下一个 token 不是属性名的一部分（如 数学.pi 乘 r），则停止。
                    if self.current.type == 'OP':
                        if attr_parts and self.peek().type == 'PUNCT' and self.peek().value == '(' and self.peek(2).type != 'NAME':
                            attr_parts.append(self.current.value)
                            self.advance()
                            continue
                        if not attr_parts and self.current.value in ('加', '乘'):
                            attr_parts.append(self.current.value)
                            self.advance()
                        break
                    attr_parts.append(self.current.value)
                    self.advance()
                if attr_parts:
                    attr = ''.join(attr_parts)
                    left = f"{left}.{attr}"
                continue

            # 函数调用：函数(参数1, 参数2)
            if self.current.type == 'PUNCT' and self.current.value == '(':
                self.advance()
                args = []
                while self.current.type != 'PUNCT' or self.current.value != ')':
                    if self.current.type == 'PUNCT' and self.current.value == ',':
                        self.advance()
                        continue
                    arg = self.parse_expression()
                    args.append(arg)
                self.advance()  # 跳过 ')'
                # 中文 next 兼容：fib.下一个() / fib.next() → next(fib)
                if left.endswith('.下一个'):
                    left = f"next({left[:-4]})"
                elif left.endswith('.next'):
                    left = f"next({left[:-5]})"
                elif left.endswith('.分割行'):
                    left = f"{left[:-4]}.splitlines({', '.join(args)})"
                elif left.endswith('.分割'):
                    left = f"{left[:-3]}.split({', '.join(args)})"
                elif left.endswith('.替换'):
                    left = f"{left[:-3]}.replace({', '.join(args)})"
                elif left.endswith('.去空白'):
                    left = f"{left[:-4]}.strip({', '.join(args)})"
                else:
                    left = f"{left}({', '.join(args)})"
                continue

            # 下标访问：对象[索引]
            if self.current.type == 'PUNCT' and self.current.value == '[':
                self.advance()
                index = self.parse_expression()
                self.expect('PUNCT', ']')
                left = f"{left}[{index}]"
                continue

            break

        return left

    def parse_atom(self):
        """解析原子（基本元素）"""
        tok = self.current

        # 字面量
        if tok.type == 'LITERAL':
            self.advance()
            return LITERAL_MAP[tok.value]

        # 数字
        if tok.type == 'NUMBER':
            self.advance()
            return tok.value

        # 字符串
        if tok.type == 'STRING':
            self.advance()
            # f-string / r-string / b-string 已经携带前缀和引号，直接返回
            if len(tok.value) >= 3 and tok.value[0] in ('f', 'F', 'r', 'R', 'b', 'B') and tok.value[1] in ('"', "'"):
                return tok.value
            # 普通字符串转义处理
            val = tok.value.replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
            return f'"{val}"'

        # 变量前缀：变量 a → a
        if tok.type == 'KEYWORD' and tok.value == '变量':
            self.advance()
            if self.current.type in ('NAME', 'OP', 'BUILTIN'):
                name = self.current.value
                self.advance()
                return name
            else:
                self.error("变量后面必须跟变量名")

        # 自身/self
        if tok.type == 'KEYWORD' and tok.value == '自身':
            self.advance()
            return 'self'

        # 名称（变量名或函数名）
        if tok.type == 'NAME':
            self.advance()
            return tok.value

        # 内置函数（作为值使用时）
        if tok.type == 'BUILTIN':
            if tok.value == '哈希' and self.peek().type == 'PUNCT' and self.peek().value == '.':
                self.advance()
                return '哈希'
            self.advance()
            return BUILTIN_MAP.get(tok.value, tok.value)

        # 括号表达式
        if tok.type == 'PUNCT' and tok.value == '(':
            self.advance()
            expr = self.parse_expression()
            # 生成器表达式：(x ** 2 for x in range(5))
            if self.current.type == 'NAME' and self.current.value == 'for':
                self.advance()
                var = self.current.value
                self.advance()
                if self.current.type == 'NAME' and self.current.value == 'in':
                    self.advance()
                iterable = self.parse_expression()
                self.expect('PUNCT', ')')
                return f"({expr} for {var} in {iterable})"
            self.expect('PUNCT', ')')
            return f"({expr})"

        # 列表字面量
        if tok.type == 'PUNCT' and tok.value == '[':
            self.advance()
            items = []
            while self.current.type != 'PUNCT' or self.current.value != ']':
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                item = self.parse_expression()
                items.append(item)
            self.advance()  # 跳过 ']'
            return f"[{', '.join(items)}]"

        # 字典字面量
        if tok.type == 'PUNCT' and tok.value == '{':
            self.advance()
            items = []
            while self.current.type != 'PUNCT' or self.current.value != '}':
                if self.current.type == 'PUNCT' and self.current.value == ',':
                    self.advance()
                    continue
                key = self.parse_expression()
                self.expect('PUNCT', ':')
                val = self.parse_expression()
                items.append(f"{key}: {val}")
            self.advance()  # 跳过 '}'
            return f"{{{', '.join(items)}}}"

        self.error(f"未预期的 token: {tok}")


# ───────────────────────────────────────────────────────────────
# 第四部分：执行引擎
# ──────────────────────────────────────────────────────────────

class ZHPyRunner:
    """中文Python执行器"""

    def __init__(self):
        self.globals = {
            '__name__': '__main__',
            '__file__': None,
            'Enum': Enum,
            'ZHEnum': ZHEnum,
        }
        # 注入中文别名的内置函数
        for zh_name, py_name in BUILTIN_MAP.items():
            try:
                self.globals[zh_name] = eval(py_name)
            except:
                pass
        # 也注入标准内置函数
        self.globals.update({k: v for k, v in builtins.__dict__.items() if not k.startswith('_')})
        # 添加中文标准库路径到 sys.path
        self._setup_stdlib_path()

    def _setup_stdlib_path(self):
        """设置中文标准库搜索路径"""
        # 获取 zhpy.py 所在目录
        zhpy_dir = os.path.dirname(os.path.abspath(__file__))
        stdlib_dir = os.path.join(zhpy_dir, 'stdlib')
        if os.path.isdir(stdlib_dir) and stdlib_dir not in sys.path:
            sys.path.insert(0, stdlib_dir)
        # 同时在 globals 中也注入 sys.path 便于模块导入
        self.globals['sys'] = sys
        self.globals['os'] = os
        # 注入中文模块别名（直接导入常用模块供使用）
        self._inject_chinese_modules()

    def _inject_chinese_modules(self):
        """尝试预加载常用中文模块并注入到 globals"""
        preload_list = [
            ('数学', '数学'),
            ('随机', '随机'),
            ('时间', '时间'),
            ('日期时间', '日期时间'),
            ('正则', '正则'),
            ('json模块', 'json模块'),
            ('文件操作', '文件操作'),
            ('路径', '路径'),
            ('集合工具', '集合工具'),
            ('CSV模块', 'CSV模块'),
            ('哈希', '哈希'),
            ('字符串模块', '字符串模块'),
            ('拷贝', '拷贝'),
            ('类型提示', '类型提示'),
        ]
        for zh_name, py_name in preload_list:
            try:
                mod = __import__(py_name)
                self.globals[zh_name] = mod
            except Exception:
                pass

    def _preprocess_exception_imports(self, source):
        """预处理源代码：将异常类导入语句转换为直接赋值

        将 "导入 零除错误" 转换为 "globals()['零除错误'] = ZeroDivisionError"
        将 "导入 零除错误 作为 e" 转换为 "e = ZeroDivisionError"
        """
        import re

        # 定义异常类映射（只处理常用异常）
        EXCEPTION_IMPORTS = {
            '零除错误': 'ZeroDivisionError',
            '值错误': 'ValueError',
            '类型错误': 'TypeError',
            '键错误': 'KeyError',
            '索引错误': 'IndexError',
            '文件未找到': 'FileNotFoundError',
            '错误': 'Exception',
            '文件已存在': 'FileExistsError',
            '权限错误': 'PermissionError',
            '输入输出错误': 'IOError',
            '运行时错误': 'RuntimeError',
            '内存错误': 'MemoryError',
            '导入错误': 'ImportError',
            '模块未找到': 'ModuleNotFoundError',
            '断言错误': 'AssertionError',
            '未实现错误': 'NotImplementedError',
            '递归错误': 'RecursionError',
            '系统错误': 'SystemError',
            '系统退出': 'SystemExit',
            '键盘中断': 'KeyboardInterrupt',
            '生成器退出': 'GeneratorExit',
            '停止迭代': 'StopIteration',
            '算术错误': 'ArithmeticError',
            '查找错误': 'LookupError',
            '溢出错误': 'OverflowError',
            '浮点错误': 'FloatingPointError',
            '引用错误': 'ReferenceError',
            '环境错误': 'EnvironmentError',
            '操作系统错误': 'OSError',
            '阻塞IO错误': 'BlockingIOError',
            '子进程错误': 'ChildProcessError',
            '连接中止': 'ConnectionAbortedError',
            '连接拒绝': 'ConnectionRefusedError',
            '连接重置': 'ConnectionResetError',
            '中断错误': 'InterruptedError',
            '是目录错误': 'IsADirectoryError',
            '非目录错误': 'NotADirectoryError',
            '超时错误': 'TimeoutError',
            '联网错误': 'ConnectionError',
            '无效字符集': 'UnicodeError',
            '编码错误': 'UnicodeEncodeError',
            '解码错误': 'UnicodeDecodeError',
            '映射错误': 'UnicodeTranslateError',
            '命名冲突': 'NameError',
            '未定义': 'UnboundLocalError',
            '语法错误': 'SyntaxError',
            '缺少引号': 'IndentationError',
            '缺少制表符': 'TabError',
        }

        # 查找所有 "导入 xxx" 模式的语句
        pattern = r'导入\s+(\w+)'

        def replace_import(match):
            exc_name = match.group(1)
            # 查找异常类的 Python 名称
            if exc_name in EXCEPTION_IMPORTS:
                py_exc = EXCEPTION_IMPORTS[exc_name]
                return f"globals()['{exc_name}'] = {py_exc}"
            else:
                return match.group(0)  # 保留原语句

        return re.sub(pattern, replace_import, source)

    def compile(self, source):
        """编译中文代码为 Python 代码"""
        # 预处理异常类导入
        processed_source = self._preprocess_exception_imports(source)

        lexer = Lexer(processed_source)
        tokens = lexer.tokenize()
        translator = Translator(tokens)
        py_code = translator.translate()
        return py_code

    def run(self, source, filename='<string>'):
        """运行中文代码"""
        py_code = self.compile(source)
        self.globals['__file__'] = filename

        # 重定向输出
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        result = None
        error = None

        try:
            code_obj = compile(py_code, filename, 'exec')
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code_obj, self.globals)
        except Exception as e:
            error = e

        return {
            'py_code': py_code,
            'stdout': stdout_capture.getvalue(),
            'stderr': stderr_capture.getvalue(),
            'error': error,
        }

    def run_file(self, filepath):
        """运行文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        return self.run(source, filepath)


# ──────────────────────────────────────────────────────────────
# 第五部分：CLI 交互
# ──────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if args and args[0] in ('--version', '-V'):
        print(f"PB {PB_VERSION}")
        return

    if args and args[0] in ('--help', '-h', 'help', '帮助'):
        print_startup_page()
        print()
        print_help_page()
        return

    if len(args) == 0:
        # 交互式模式
        print_startup_page()
        runner = ZHPyRunner()
        while True:
            try:
                line = input("PB >>> ")
                if line.strip() in ('退出', 'exit', 'quit'):
                    break
                if line.strip() in ('帮助', 'help'):
                    print_help_page()
                    continue
                if not line.strip():
                    continue
                result = runner.run(line)
                if result['error']:
                    print(f"[错误] {result['error']}")
                else:
                    if result['stdout']:
                        print(result['stdout'], end='')
                    # 显示编译后的 Python 代码（调试用）
                    # print(f"[翻译] {result['py_code']}")
            except KeyboardInterrupt:
                print("\n使用 '退出' 离开")
            except EOFError:
                break
        print("再见!")
        return

    if args[0] == '-c':
        # 执行命令
        source = args[1] if len(args) > 1 else ''
        runner = ZHPyRunner()
        result = runner.run(source)
        if result['error']:
            print(f"[错误] {result['error']}")
            sys.exit(1)
        print(result['stdout'], end='')
        return

    if args[0] == '--compile':
        # 只翻译不执行
        if len(args) < 2:
            print("错误: --compile 需要文件路径")
            sys.exit(1)
        filepath = args[1]
        runner = ZHPyRunner()
        source = open(filepath, 'r', encoding='utf-8').read()
        py_code = runner.compile(source)
        print("=== 编译后的 Python 代码 ===")
        print(py_code)
        print("=== 结束 ===")
        return

    # 执行文件
    filepath = args[0]
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在 {filepath}")
        sys.exit(1)

    runner = ZHPyRunner()
    result = runner.run_file(filepath)
    if result['error']:
        print(f"[错误] {result['error']}")
        sys.exit(1)
    print(result['stdout'], end='')


if __name__ == '__main__':
    main()
