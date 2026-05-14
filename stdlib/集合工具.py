# -*- coding: utf-8 -*-
"""
中文标准库：集合工具模块 (collections)
用法: 导入 集合工具
"""
from collections import *
from collections import Counter, deque, defaultdict, OrderedDict, ChainMap, namedtuple

# 常用类型中文别名
计数器 = Counter
双端队列 = deque
默认字典 = defaultdict
有序字典 = OrderedDict
链映射 = ChainMap
命名元组 = namedtuple

# 为双端队列补充中文方法别名（直接给 C 扩展类型赋值可能失败，因此创建子类）
class 中文双端队列(deque):
    def 追加(self, 值):
        return self.append(值)

    def 追(self, 值):
        """兼容词法器把“追加”拆为 追 + 加 的情况。"""
        return self.append(值)

    def 左追加(self, 值):
        return self.appendleft(值)

    def 弹出(self):
        return self.pop()

    def 左弹出(self):
        return self.popleft()

    def 扩展(self, 可迭代对象):
        return self.extend(可迭代对象)

    def 左扩展(self, 可迭代对象):
        return self.extendleft(可迭代对象)

    def 清空(self):
        return self.clear()

    def 计数(self, 值):
        return self.count(值)

    def 移除(self, 值):
        return self.remove(值)

    def 反转(self):
        return self.reverse()

    def 旋转(self, 步数=1):
        return self.rotate(步数)

双端队列 = 中文双端队列

__all__ = [
    'Counter', 'deque', 'defaultdict', 'OrderedDict', 'ChainMap', 'namedtuple',
    '计数器', '双端队列', '默认字典', '有序字典', '链映射', '命名元组', '中文双端队列',
]
