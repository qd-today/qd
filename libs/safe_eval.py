# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
safe_eval module - methods intended to provide more restricted alternatives to
                   evaluate simple and/or untrusted code.
Methods in this module are typically used as alternatives to eval() to parse
OpenERP domain strings, conditions and expressions, mostly based on locals
condition/math builtins.
"""

# Module partially ripped from/inspired by several different sources:
#  - http://code.activestate.com/recipes/286134/
#  - safe_eval in lp:~xrg/openobject-server/optimize-5.0
#  - safe_eval in tryton http://hg.tryton.org/hgwebdir.cgi/trytond/rev/bbb5f73319ad

import ctypes
import dis
import functools
import signal
import sys
import threading
import types
from types import CodeType

# import multiprocessing
import dateutil
from opcode import opmap, opname

import config
from libs.log import Log

__all__ = ['test_expr', 'safe_eval', 'const_eval']

# The time module is usually already provided in the safe_eval environment
# but some code, e.g. datetime.datetime.now() (Windows/Python 2.5.2, bug
# lp:703841), does import time.
_ALLOWED_MODULES = ['_strptime', 'math', 'time']

_UNSAFE_ATTRIBUTES = ['f_builtins', 'f_globals', 'f_locals', 'gi_frame', 'gi_code',
                      'co_code', 'func_globals']


def to_opcodes(opnames, _opmap=opmap):  # pylint: disable=dangerous-default-value
    for x in opnames:
        if x in _opmap:
            yield _opmap[x]


# opcodes which absolutely positively must not be usable in safe_eval,
# explicitly subtracted from all sets of valid opcodes just in case
_BLACKLIST = set(to_opcodes([
    # can't provide access to accessing arbitrary modules
    'IMPORT_STAR', 'IMPORT_NAME', 'IMPORT_FROM',
    # could allow replacing or updating core attributes on models & al, setitem
    # can be used to set field values
    'STORE_ATTR', 'DELETE_ATTR',
    # no reason to allow this
    'STORE_GLOBAL', 'DELETE_GLOBAL',
]))
# opcodes necessary to build literal values
_CONST_OPCODES = set(to_opcodes([
    # stack manipulations
    'POP_TOP', 'ROT_TWO', 'ROT_THREE', 'ROT_FOUR', 'DUP_TOP', 'DUP_TOP_TWO',
    'LOAD_CONST',
    'RETURN_VALUE',  # return the result of the literal/expr evaluation
    # literal collections
    'BUILD_LIST', 'BUILD_MAP', 'BUILD_TUPLE', 'BUILD_SET',
    # 3.6: literal map with constant keys https://bugs.python.org/issue27140
    'BUILD_CONST_KEY_MAP',
    'LIST_EXTEND', 'SET_UPDATE',
    # 3.11 replace DUP_TOP, DUP_TOP_TWO, ROT_TWO, ROT_THREE, ROT_FOUR
    'COPY',
    # Added in 3.11 https://docs.python.org/3.11/whatsnew/3.11.html
    'RESUME',
])) - _BLACKLIST

# operations which are both binary and inplace, same order as in doc'
_operations = [
    'POWER', 'MULTIPLY',  # 'MATRIX_MULTIPLY', # matrix operator (3.5+)
    'FLOOR_DIVIDE', 'TRUE_DIVIDE', 'MODULO', 'ADD',
    'SUBTRACT', 'LSHIFT', 'RSHIFT', 'AND', 'XOR', 'OR',
]
# operations on literal values
_EXPR_OPCODES = _CONST_OPCODES.union(to_opcodes([
    'UNARY_POSITIVE', 'UNARY_NEGATIVE', 'UNARY_NOT', 'UNARY_INVERT',
    *('BINARY_' + op for op in _operations), 'BINARY_SUBSCR',
    *('INPLACE_' + op for op in _operations),
    'BUILD_SLICE',
    # comprehensions
    'LIST_APPEND', 'MAP_ADD', 'SET_ADD',
    'COMPARE_OP',
    # specialised comparisons
    'IS_OP', 'CONTAINS_OP',
    'DICT_MERGE', 'DICT_UPDATE',
    # Basically used in any "generator literal"
    'GEN_START',  # added in 3.10 but already removed from 3.11.
    # Added in 3.11, replacing all BINARY_* and INPLACE_*
    'BINARY_OP',
])) - _BLACKLIST

_SAFE_OPCODES = _EXPR_OPCODES.union(to_opcodes([
    'POP_BLOCK', 'POP_EXCEPT',

    # note: removed in 3.8
    'SETUP_LOOP', 'SETUP_EXCEPT', 'BREAK_LOOP', 'CONTINUE_LOOP',

    'EXTENDED_ARG',  # P3.6 for long jump offsets.
    'MAKE_FUNCTION', 'CALL_FUNCTION', 'CALL_FUNCTION_KW', 'CALL_FUNCTION_EX',
    # Added in P3.7 https://bugs.python.org/issue26110
    'CALL_METHOD', 'LOAD_METHOD',

    'GET_ITER', 'FOR_ITER', 'YIELD_VALUE',
    'JUMP_FORWARD', 'JUMP_ABSOLUTE',
    'JUMP_IF_FALSE_OR_POP', 'JUMP_IF_TRUE_OR_POP', 'POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE',
    'SETUP_FINALLY', 'END_FINALLY',
    # Added in 3.8 https://bugs.python.org/issue17611
    'BEGIN_FINALLY', 'CALL_FINALLY', 'POP_FINALLY',

    'RAISE_VARARGS', 'LOAD_NAME', 'STORE_NAME', 'DELETE_NAME', 'LOAD_ATTR',
    'LOAD_FAST', 'STORE_FAST', 'DELETE_FAST', 'UNPACK_SEQUENCE',
    'STORE_SUBSCR',
    'LOAD_GLOBAL',

    'RERAISE', 'JUMP_IF_NOT_EXC_MATCH',

    # replacement of opcodes CALL_FUNCTION, CALL_FUNCTION_KW, CALL_METHOD
    'PUSH_NULL', 'PRECALL', 'CALL', 'KW_NAMES',
    # replacement of POP_JUMP_IF_TRUE and POP_JUMP_IF_FALSE
    'POP_JUMP_FORWARD_IF_FALSE', 'POP_JUMP_FORWARD_IF_TRUE',
    'POP_JUMP_BACKWARD_IF_FALSE', 'POP_JUMP_BACKWARD_IF_TRUE',
    # replacement of JUMP_ABSOLUTE
    'JUMP_BACKWARD',
    # replacement of JUMP_IF_NOT_EXC_MATCH
    'CHECK_EXC_MATCH',
    # new opcodes
    'RETURN_GENERATOR',
    'PUSH_EXC_INFO',
    'NOP',
    'FORMAT_VALUE', 'BUILD_STRING'

])) - _BLACKLIST

_logger = Log('QD.Http.Fetcher').getlogger()

'''
class RunnableProcessing(multiprocessing.Process):
    """ Run a function in a child process.
    Pass back any exception received.
    """
    def __init__(self, func, *args, **kwargs):
        self.queue = multiprocessing.Queue(maxsize=1)
        args = (func,) + args
        multiprocessing.Process.__init__(self, target=self.run_func, args=args, kwargs=kwargs)

    def run_func(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            self.queue.put((True, result))
        except Exception as e:
            self.queue.put((False, e))

    def done(self):
        return self.queue.full()

    def result(self):
        return self.queue.get()
'''


class TerminableThread(threading.Thread):
    """a thread that can be stopped by forcing an exception in the execution context"""

    def terminate(self, exception_cls, repeat_sec=2.0):
        if self.is_alive() is False:
            return True
        killer = ThreadKiller(self, exception_cls, repeat_sec=repeat_sec)
        killer.start()


class ThreadKiller(threading.Thread):
    """separate thread to kill TerminableThread"""

    def __init__(self, target_thread, exception_cls, repeat_sec=2.0):
        threading.Thread.__init__(self)
        self.target_thread = target_thread
        self.exception_cls = exception_cls
        self.repeat_sec = repeat_sec
        self.daemon = True

    def run(self):
        """loop raising exception incase it's caught hopefully this breaks us far out"""
        while self.target_thread.is_alive():
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.target_thread.ident),
                                                       ctypes.py_object(self.exception_cls))
            self.target_thread.join(self.repeat_sec)


def timeout(sec, raise_sec=1):
    """
    timeout decorator
    :param sec: function raise TimeoutError after ? seconds
    :param raise_sec: retry kill thread per ? seconds
    :example:
    >>> @timeout(3)
    >>> def my_func():
    >>>     ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            err_msg = f'Function {func.__name__} timed out after {sec} seconds'

            if sys.platform != 'win32':
                # '''
                # 非Windows系统, 一般对signal都有全面的支持。
                # 为了实现Timeout功能, 可以通过以下几步：
                # 1. 选用SIGALRM信号来代表Timeout事件;
                # 2. 将抛出超时异常的事件与SIGALRM信号的触发绑定;
                # 3. 设定在给定时间后触发SIGALRM信号;
                # 4. 运行目标函数（如超时, 会自动被信号绑定的异常事件打断）。
                # '''

                def _handle_timeout(signum, frame):
                    raise TimeoutError(err_msg)

                signal.signal(signal.SIGALRM, _handle_timeout)
                signal.alarm(int(sec))
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                return result

            else:
                # '''
                # Windows系统对signal的支持很差, 因此不能通过上述方法实现。
                # 新的实现思路是：开启子线程来运行目标函数, 主线程计时, 超时后中止子线程。

                # 子线程不能向主线程返回执行结果, 但是可以和主线程共享内存。
                # 因此, 我们创建result和exception两个mutable变量, 分别用来存储子线程的运行结果和异常。
                # 在子线程结束后, 主线程可以直接通过这两个变量获取线程执行结果并顺利返回。

                # 子线程运行中所有的异常, 均要保留到子线程结束后, 在主线程中处理。
                # 如果直接在子线程中抛出异常, timeout装饰器的使用者将无法通过try/except捕获并处理该异常。
                # 因此, 子线程运行的函数完全被try/except包住, 通过mutable变量交由主线程处理。
                # 如果出现FuncTimeoutError, 说明是超时所致, 在子线程内不做捕获。
                # '''
                class FuncTimeoutError(TimeoutError):
                    def __init__(self):
                        TimeoutError.__init__(self, err_msg)

                result, exception = [], []

                def run_func():
                    try:
                        res = func(*args, **kwargs)
                    except FuncTimeoutError:
                        _logger.debug('Function %s timed out after %s seconds', func.__name__, sec)
                    except Exception as e:
                        exception.append(e)
                    else:
                        result.append(res)

                # typically, a python thread cannot be terminated, use TerminableThread instead
                thread = TerminableThread(target=run_func, daemon=True)
                thread.start()
                thread.join(timeout=sec)

                if thread.is_alive():
                    # a timeout thread keeps alive after join method, terminate and raise TimeoutError
                    exc = type('TimeoutError', FuncTimeoutError.__bases__, dict(FuncTimeoutError.__dict__))
                    thread.terminate(exception_cls=FuncTimeoutError, repeat_sec=raise_sec)
                    raise exc(err_msg)
                elif exception:
                    # if exception occurs during the thread running, raise it
                    raise exception[0]
                else:
                    # if the thread successfully finished, return its results
                    return result[0]

                # # 使用子进程方式实现超时功能
                # now = time.time()
                # proc = RunnableProcessing(func, *args, **kwargs)
                # proc.start()
                # proc.join(sec)
                # if proc.is_alive():
                #     if force_kill:
                #         proc.terminate()
                #     runtime = time.time() - now
                #     raise TimeoutException('timed out after {0} seconds'.format(runtime))
                # assert proc.done()
                # success, result = proc.result()
                # if success:
                #     return result
                # else:
                #     raise result

        return wrapped_func
    return decorator


@timeout(config.unsafe_eval_timeout)
def unsafe_eval(*args, **kwargs) :
    return eval(*args, **kwargs)  # pylint: disable=eval-used


class BadCompilingInput(Exception):
    """ The user tried to input something which might cause compiler to slow down. """


def check_for_pow(expr):
    """ Python evaluates power operator during the compile time if its on constants.
    You can do CPU / memory burning attack with ``2**999999999999999999999**9999999999999``.
    We mainly care about memory now, as we catch timeoutting in any case.
    We just disable pow and do not care about it.
    """
    if "**" in expr:
        raise BadCompilingInput("Power operation is not allowed")


def assert_no_dunder_name(code_obj, expr):
    """ assert_no_dunder_name(code_obj, expr) -> None
    Asserts that the code object does not refer to any "dunder name"
    (__$name__), so that safe_eval prevents access to any internal-ish Python
    attribute or method (both are loaded via LOAD_ATTR which uses a name, not a
    const or a var).
    Checks that no such name exists in the provided code object (co_names).
    :param code_obj: code object to name-validate
    :type code_obj: CodeType
    :param str expr: expression corresponding to the code object, for debugging
                     purposes
    :raises NameError: in case a forbidden name (containing two underscores)
                       is found in ``code_obj``
    .. note:: actually forbids every name containing 2 underscores
    """
    for name in code_obj.co_names:
        if "__" in name or name in _UNSAFE_ATTRIBUTES:
            raise NameError(f'Access to forbidden name {name!r} ({expr!r})')


def assert_valid_codeobj(allowed_codes, code_obj, expr):
    """ Asserts that the provided code object validates against the bytecode
    and name constraints.
    Recursively validates the code objects stored in its co_consts in case
    lambdas are being created/used (lambdas generate their own separated code
    objects and don't live in the root one)
    :param allowed_codes: list of permissible bytecode instructions
    :type allowed_codes: set(int)
    :param code_obj: code object to name-validate
    :type code_obj: CodeType
    :param str expr: expression corresponding to the code object, for debugging
                     purposes
    :raises ValueError: in case of forbidden bytecode in ``code_obj``
    :raises NameError: in case a forbidden name (containing two underscores)
                       is found in ``code_obj``
    """
    assert_no_dunder_name(code_obj, expr)

    # set operations are almost twice as fast as a manual iteration + condition
    # when loading /web according to line_profiler
    code_codes = {i.opcode for i in dis.get_instructions(code_obj)}
    if not allowed_codes >= code_codes:
        raise ValueError(f"forbidden opcode(s) in {expr!r}: {', '.join(opname[x] for x in (code_codes - allowed_codes))}")

    for const in code_obj.co_consts:
        if isinstance(const, CodeType):
            assert_valid_codeobj(allowed_codes, const, 'lambda')


def test_expr(expr, allowed_codes, mode="eval", filename=None):
    """test_expr(expression, allowed_codes[, mode[, filename]]) -> code_object
    Test that the expression contains only the allowed opcodes.
    If the expression is valid and contains only allowed codes,
    return the compiled code object.
    Otherwise raise a ValueError, a Syntax Error or TypeError accordingly.
    :param filename: optional pseudo-filename for the compiled expression,
                 displayed for example in traceback frames
    :type filename: string
    """
    try:
        if mode == 'eval':
            # eval() does not like leading/trailing whitespace
            expr = expr.strip()
        code_obj = compile(expr, filename or "", mode)
    except (SyntaxError, TypeError, ValueError):
        raise
    except Exception as e:
        raise ValueError(f'"{e}" while compiling\n{expr!r}') from e
    assert_valid_codeobj(allowed_codes, code_obj, expr)
    return code_obj


def const_eval(expr):
    """const_eval(expression) -> value
    Safe Python constant evaluation
    Evaluates a string that contains an expression describing
    a Python constant. Strings that are not valid Python expressions
    or that contain other code besides the constant raise ValueError.
    >>> const_eval("10")
    10
    >>> const_eval("[1,2, (3,4), {'foo':'bar'}]")
    [1, 2, (3, 4), {'foo': 'bar'}]
    >>> const_eval("1+2")
    Traceback (most recent call last):
    ...
    ValueError: opcode BINARY_ADD not allowed
    """
    c = test_expr(expr, _CONST_OPCODES)
    return unsafe_eval(c)


def expr_eval(expr):
    """expr_eval(expression) -> value
    Restricted Python expression evaluation
    Evaluates a string that contains an expression that only
    uses Python constants. This can be used to e.g. evaluate
    a numerical expression from an untrusted source.
    >>> expr_eval("1+2")
    3
    >>> expr_eval("[1,2]*2")
    [1, 2, 1, 2]
    >>> expr_eval("__import__('sys').modules")
    Traceback (most recent call last):
    ...
    ValueError: opcode LOAD_NAME not allowed
    """
    c = test_expr(expr, _EXPR_OPCODES)
    return unsafe_eval(c)


def _import(name, globals=None, locals=None, fromlist=None, level=-1):
    if globals is None:
        globals = {}
    if locals is None:
        locals = {}
    if fromlist is None:
        fromlist = []
    if name in _ALLOWED_MODULES:
        return __import__(name, globals, locals, level)
    raise ImportError(name)


_BUILTINS = {
    '__import__': _import,
    'True': True,
    'False': False,
    'None': None,
    'bytes': bytes,
    'str': str,
    'unicode': str,
    'bool': bool,
    'int': int,
    'float': float,
    'enumerate': enumerate,
    'dict': dict,
    'list': list,
    'tuple': tuple,
    'map': map,
    'abs': abs,
    'min': min,
    'max': max,
    'sum': sum,
    'reduce': functools.reduce,
    'filter': filter,
    'sorted': sorted,
    'round': round,
    'len': len,
    'repr': repr,
    'set': set,
    'all': all,
    'any': any,
    'ord': ord,
    'chr': chr,
    'divmod': divmod,
    'isinstance': isinstance,
    'range': range,
    'xrange': range,
    'zip': zip,
    'Exception': Exception,
}


def safe_eval(expr, globals_dict=None, locals_dict=None, mode="eval", nocopy=False, locals_builtins=False, filename=None):
    """safe_eval(expression[, globals[, locals[, mode[, nocopy]]]]) -> result
    System-restricted Python expression evaluation
    Evaluates a string that contains an expression that mostly
    uses Python constants, arithmetic expressions and the
    objects directly provided in context.
    This can be used to e.g. evaluate
    an OpenERP domain expression from an untrusted source.
    :param filename: optional pseudo-filename for the compiled expression,
                     displayed for example in traceback frames
    :type filename: string
    :throws TypeError: If the expression provided is a code object
    :throws SyntaxError: If the expression provided is not valid Python
    :throws NameError: If the expression provided accesses forbidden names
    :throws ValueError: If the expression provided uses forbidden bytecode
    """
    if type(expr) is CodeType:
        raise TypeError("safe_eval does not allow direct evaluation of code objects.")

    # prevent altering the globals/locals from within the sandbox
    # by taking a copy.
    if not nocopy:
        # isinstance() does not work below, we want *exactly* the dict class
        if (globals_dict is not None and type(globals_dict) is not dict) \
                or (locals_dict is not None and type(locals_dict) is not dict):
            _logger.warning(
                "Looks like you are trying to pass a dynamic environment, "
                "you should probably pass nocopy=True to safe_eval().")
        if globals_dict is not None:
            globals_dict = dict(globals_dict)
        if locals_dict is not None:
            locals_dict = dict(locals_dict)

    check_values(globals_dict)
    check_values(locals_dict)

    if globals_dict is None:
        globals_dict = {}

    globals_dict['__builtins__'] = _BUILTINS
    if locals_builtins:
        if locals_dict is None:
            locals_dict = {}
        locals_dict.update(_BUILTINS)
    c = test_expr(expr, _SAFE_OPCODES, mode=mode, filename=filename)
    try:
        return unsafe_eval(c, globals_dict, locals_dict)
    except ZeroDivisionError:
        raise
    except Exception as e:
        raise ValueError(f'{type(e)}: "{e}"') from e


def test_python_expr(expr, mode="eval"):
    try:
        test_expr(expr, _SAFE_OPCODES, mode=mode)
    except (SyntaxError, TypeError, ValueError) as err:
        if len(err.args) >= 2 and len(err.args[1]) >= 4:
            error = {
                'message': err.args[0],
                'filename': err.args[1][0],
                'lineno': err.args[1][1],
                'offset': err.args[1][2],
                'error_line': err.args[1][3],
            }
            msg = f"{type(err).__name__} : {error['message']} at line {error['lineno']}\n{error['error_line']}"
        else:
            msg = err
        return msg
    return False


def check_values(d):
    if not d:
        return d
    for v in d.values():
        if isinstance(v, types.ModuleType):
            raise TypeError(f"""Module {v} can not be used in evaluation contexts
Prefer providing only the items necessary for your intended use.
If a "module" is necessary for backwards compatibility, use
`odoo.tools.safe_eval.wrap_module` to generate a wrapper recursively
whitelisting allowed attributes.
Pre-wrapped modules are provided as attributes of `odoo.tools.safe_eval`.
""")
    return d


class WrapModule:
    def __init__(self, module, attributes):
        """Helper for wrapping a package/module to expose selected attributes
        :param module: the actual package/module to wrap, as returned by ``import <module>``
        :param iterable attributes: attributes to expose / whitelist. If a dict,
                                    the keys are the attributes and the values
                                    are used as an ``attributes`` in case the
                                    corresponding item is a submodule
        """
        # builtin modules don't have a __file__ at all
        modfile = getattr(module, '__file__', '(built-in)')
        self._repr = f"<wrapped {module.__name__!r} ({modfile})>"
        for attrib in attributes:
            target = getattr(module, attrib)
            if isinstance(target, types.ModuleType):
                target = WrapModule(target, attributes[attrib])
            setattr(self, attrib, target)

    def __repr__(self):
        return self._repr


# dateutil submodules are lazy so need to import them for them to "exist"

mods = ['parser', 'relativedelta', 'rrule', 'tz']
for mod in mods:
    __import__(f'dateutil.{mod}')
datetime = WrapModule(__import__('datetime'), ['date', 'datetime', 'time', 'timedelta', 'timezone', 'tzinfo', 'MAXYEAR', 'MINYEAR'])
dateutil = WrapModule(dateutil, {  # type: ignore
    mod: getattr(dateutil, mod).__all__
    for mod in mods
})
json = WrapModule(__import__('json'), ['loads', 'dumps'])
time = WrapModule(__import__('time'), ['time', 'strptime', 'strftime', 'sleep'])
zoneinfo = WrapModule(__import__('zoneinfo'), [
    'ZoneInfo', 'available_timezones',
])
