"""boolean parameters"""

__all__ = [
    'switcher',
    'complicated',
    'positional_only',
]


def switcher(arg_1: str, some_flag: bool, whatever: str):
    if some_flag:
        print(arg_1)
    else:
        print(whatever)


def complicated(req_pos,
                with_default_pos=None,
                some_bool: bool = True,
                *,
                req_kw,
                some_other_bool: bool,
                with_default_kw=None,
                ):
    print(some_bool, some_other_bool)


def positional_only(*args: bool):
    print(args)
