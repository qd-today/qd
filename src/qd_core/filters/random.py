import random


def get_random(min_num, max_num, unit):
    random_num = random.uniform(min_num, max_num)
    # result = "%.{0}f".format(int(unit)) % random_num
    result = f"{random_num:.{int(unit)}f}"
    return result


def random_fliter(*args, **kwargs):
    try:
        result = get_random(*args, **kwargs)
    except Exception:
        result = random.choice(*args, **kwargs)
    return result


def randomize_list(mylist, seed=None):
    try:
        mylist = list(mylist)
        if seed:
            r = random.Random(seed)
            r.shuffle(mylist)
        else:
            random.shuffle(mylist)
    except Exception as e:
        raise e
    return mylist
