# -*- coding: utf-8 -*-
"""safe_eval 的操作码白名单回归测试。

CPython 每升级一次大版本都会改动字节码（新增/合并/改名 opcode），而白名单是
「按名字」维护的，漏一个不会有任何提示，直到某个条件表达式在运行期被误判成
forbidden opcode。所以这里用一份表达式语料把「常见的条件写法必须能算」钉死；
CPython 再加新 opcode 时，用例会直接报出缺了哪些名字。

运行: python -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from types import CodeType

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dis  # noqa: E402

from libs import safe_eval as se  # noqa: E402


def _opcodes(code_obj):
    """递归收集 code object 里出现的全部操作码名字。"""
    names = set()
    for instr in dis.get_instructions(code_obj):
        names.add(instr.opname)
    for const in code_obj.co_consts:
        if isinstance(const, CodeType):
            names |= _opcodes(const)
    return names


def _allowed_names():
    """把白名单的 opcode 数字还原成名字（含 opmap 里的伪指令）。"""
    from opcode import opmap

    name_of = {value: name for name, value in opmap.items()}
    return {name_of.get(op, str(op)) for op in se._SAFE_OPCODES}


# (表达式, 求值环境, 期望结果)
EXPR_CASES = [
    # 条件表达式：变量是字符串形态的数字，模板里最常见的写法
    ('int(count) > 0', {'count': '5'}, True),
    ('int(count) > 0', {'count': '0'}, False),
    ('int(loop) < 20 and int(flag)!=0', {'loop': '1', 'flag': '1'}, True),
    ('int(loop) < 20 and int(flag)!=0', {'loop': '21', 'flag': '1'}, False),
    ('int(loop) < 20 and int(flag)!=0', {'loop': '1', 'flag': '0'}, False),
    ('ret != 0 or ret is None', {'ret': None}, True),
    # 布尔 / 比较
    ('not ret', {'ret': 0}, True),
    ('1 < 2 < 3', {}, True),
    ('x in y and x not in z', {'x': 1, 'y': [1], 'z': [2]}, True),
    ('isinstance(a, int)', {'a': 1}, True),
    # 算术 / 一元
    ('-1 + 2 - (-3)', {}, 4),
    ('abs(-1)', {}, 1),
    ('~0', {}, -1),
    ('+1', {}, 1),
    ('7 // 2 % 3 * 2', {}, 0),
    # 字面量容器与解包
    ('[1, 2, {"k": (3,)}]', {}, [1, 2, {'k': (3,)}]),
    ('[*a, 1]', {'a': [2, 3]}, [2, 3, 1]),
    ('(*a, 1)', {'a': (2,)}, (2, 1)),
    ('{**a, "k": 1}', {'a': {'z': 0}}, {'z': 0, 'k': 1}),
    ('{1, 2}', {}, {1, 2}),
    # 下标 / 切片
    ('d["k"]', {'d': {'k': 1}}, 1),
    ('d[1:2]', {'d': [1, 2, 3]}, [2]),
    ('d[::-1]', {'d': [1, 2, 3]}, [3, 2, 1]),
    # 推导式与生成器
    ('[x for x in range(3)]', {}, [0, 1, 2]),
    ('[x for x in range(5) if x > 2]', {}, [3, 4]),
    ('{k: v for k, v in items}', {'items': [('a', 1)]}, {'a': 1}),
    ('{x for x in range(3)}', {}, {0, 1, 2}),
    ('sum(x for x in range(3))', {}, 3),
    ('[y for x in z for y in x]', {'z': [[1], [2, 3]]}, [1, 2, 3]),
    ('[[y for y in x] for x in z]', {'z': [[1], [2]]}, [[1], [2]]),
    ('[i for i, j in enumerate(items) if j]', {'items': [0, 5]}, [1]),
    # 调用 / lambda / 关键字参数
    ('str(round(1.234, 2))', {}, '1.23'),
    ('sorted(items, key=lambda v: v[0])', {'items': [(2, 'a'), (1, 'b')]}, [(1, 'b'), (2, 'a')]),
    ('(lambda x, y=2: x + y)(1)', {}, 3),
    ('"".join(map(str, range(3)))', {}, '012'),
    # 字符串 / 格式化
    ('"a" + "b"', {}, 'ab'),
    ('"%s-%s" % (a, b)', {'a': 1, 'b': 2}, '1-2'),
    ('"{}".format(a)', {'a': 1}, '1'),
    ('f"{a}-{b}"', {'a': 1, 'b': 2}, '1-2'),
    ('f"{a!r:>4}"', {'a': 'x'}, " 'x'"),
    # 条件表达式
    ('a if b else c', {'a': 1, 'b': 0, 'c': 2}, 2),
]

# exec 模式仍然只放行「无副作用」的语句形态
STMT_CASES = [
    'if a:\n    b = 1\n',
    'while a:\n    break\n',
    'for i in y:\n    pass\n',
    'try:\n    a\nexcept Exception:\n    pass\n',
    'x = 1\ny = x + 1\n',
    'def f():\n    return 1\n',
    'assert a\n',
    'x = [i for i in y]\n',
    'x = {k: v for k, v in y}\n',
    'if x is None:\n    y = 1\n',
    'while x is not None:\n    break\n',
    'a[1:2] = b\n',
]

# (源码, 模式): 必须被字节码校验拒绝
FORBIDDEN_AT_COMPILE = [
    ('().__class__', 'eval'),
    ('a.__class__.__bases__', 'eval'),
    ('import os\n', 'exec'),
    ('from os import *\n', 'exec'),
    ('from os import path\n', 'exec'),
    ('a.b = 1\n', 'exec'),
    ('del a.b\n', 'exec'),
    ('global x\nx = 1\n', 'exec'),
    # 推导式里套 lambda 会生成 cell 变量 (LOAD_CLOSURE/MAKE_CELL/STORE_DEREF...)。
    # 这类 opcode upstream 也没放行, 模板里从未用到, 所以按「不放行」钉住:
    # 想支持的话要连同这里一起改, 别只改白名单。
    ('[lambda: x for x in y]', 'eval'),
    # 不带下划线的自省入口, 靠 _UNSAFE_ATTRIBUTES 拦
    ('x.mro()', 'eval'),
    ('x.mro()[1]', 'eval'),
    ('f.f_code', 'eval'),
    ('x.tb_frame', 'eval'),
    ('g.gi_yieldfrom', 'eval'),
    ('c.cr_frame', 'eval'),
    ('x._co_code_adaptive', 'eval'),
]

# 字节码层面放行（都是普通 LOAD_NAME/CALL），靠沙箱内的 builtins 与名称检查兜住
FORBIDDEN_AT_RUNTIME = [
    'open("/etc/passwd")',
    '__import__("os").system("id")',
    'eval("1")',
    'exec("1")',
]


class TestSafeEvalOpcodes(unittest.TestCase):
    def test_expression_corpus(self):
        for expr, env, expected in EXPR_CASES:
            with self.subTest(expr=expr):
                self.assertEqual(se.safe_eval(expr, dict(env)), expected)

    def test_statement_corpus(self):
        for src in STMT_CASES:
            with self.subTest(src=src):
                se.test_expr(src, se._SAFE_OPCODES, mode='exec')

    def test_forbidden_at_compile(self):
        for src, mode in FORBIDDEN_AT_COMPILE:
            with self.subTest(src=src):
                with self.assertRaises((ValueError, NameError)):
                    se.test_expr(src, se._SAFE_OPCODES, mode=mode)

    def test_forbidden_at_runtime(self):
        for expr in FORBIDDEN_AT_RUNTIME:
            with self.subTest(expr=expr):
                with self.assertRaises((ValueError, NameError)):
                    se.safe_eval(expr)

    def test_whitelist_covers_corpus(self):
        """一次性报出语料里所有缺失的操作码，升级 Python 时看这条就够了。"""
        allowed = _allowed_names()
        missing = set()
        for expr, _, _ in EXPR_CASES:
            missing |= _opcodes(compile(expr, '<test>', 'eval')) - allowed
        for src in STMT_CASES:
            missing |= _opcodes(compile(src, '<test>', 'exec')) - allowed
        self.assertFalse(
            missing,
            f'Python {sys.version.split()[0]} 新增了未被放行的操作码 {sorted(missing)}，'
            '请更新 libs/safe_eval.py 里的白名单',
        )

    def test_intrinsic_operand_is_checked(self):
        """CALL_INTRINSIC_1 一个 opcode 多种语义，import * 必须按操作数挡下来。"""
        self.assertNotIn(
            'INTRINSIC_IMPORT_STAR',
            se._ALLOWED_INTRINSIC_1_NAMES,
            'import * 决不能进白名单',
        )
        # (*a, *b) 走 INTRINSIC_LIST_TO_TUPLE，属于允许的语义
        se.test_expr('(*a,)', se._SAFE_OPCODES)

    def test_unsafe_attributes_cover_introspection(self):
        """frame / code / 生成器 / 协程 的自省属性必须全部禁用，别只拦带 __ 的。"""
        required = {
            'f_builtins', 'f_code', 'f_globals', 'f_locals', 'f_generator',
            'func_code', 'func_globals', 'co_code', '_co_code_adaptive', 'mro',
            'tb_frame', 'gi_code', 'gi_frame', 'gi_yieldfrom',
            'cr_await', 'cr_code', 'cr_frame', 'ag_await', 'ag_code', 'ag_frame',
        }
        missing = required - set(se._UNSAFE_ATTRIBUTES)
        self.assertFalse(missing, f'_UNSAFE_ATTRIBUTES 缺少自省属性: {sorted(missing)}')

    def test_blacklist_never_leaks(self):
        leaks = se._BLACKLIST & se._SAFE_OPCODES
        self.assertFalse(leaks, f'黑名单操作码混进了白名单: {sorted(leaks)}')


if __name__ == '__main__':
    unittest.main()
