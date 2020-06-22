"""Use builtin commands"""
import sys

__all__ = [
    'takes_list',
    'takes_dict',
    'flush_stdout',
]


def takes_list(first: list, second: list):
    for x in zip(first, second):
        print(*x)


def takes_dict(first: dict, second: dict):
    for k in first:
        if k in second:
            print(second[k])
        else:
            print(first[k])


def flush_stdout():
    sys.stdout.flush()
