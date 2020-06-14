"""sample for substitutions"""

__all__ = [
    'double',
    'echo',
]


def double(number: int):
    return 2 * number


def echo(text: str):  # print() can't be introspected
    print(text)
