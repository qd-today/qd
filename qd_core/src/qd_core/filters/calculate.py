from qd_core.filters.judge import is_num


def add(*args):
    result = 0
    if args and is_num(args[0]):
        result = float(args[0])
        for i in args[1:]:
            if is_num(i):
                result += float(i)
            else:
                return
        return f"{result:f}"
    return result


def sub(*args):
    result = 0
    if args and is_num(args[0]):
        result = float(args[0])
        for i in args[1:]:
            if is_num(i):
                result -= float(i)
            else:
                return
        return f"{result:f}"
    return result


def multiply(*args):
    result = 0
    if args and is_num(args[0]):
        result = float(args[0])
        for i in args[1:]:
            if is_num(i):
                result *= float(i)
            else:
                return
        return f"{result:f}"
    return result


def divide(*args):
    result = 0
    if args and is_num(args[0]):
        result = float(args[0])
        for i in args[1:]:
            if is_num(i) and float(i) != 0:
                result /= float(i)
            else:
                return
        return f"{result:f}"
    return result
