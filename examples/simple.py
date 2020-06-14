"""Sample Python module for py-s-lang"""


__all__ = [
    'hello',
    'repeater',
    'complicated',
]


def hello(name: str):
    print('Hello,', name)


def repeater(text: str, times: int):
    print(text * times)


def complicated(first: int, *more: int, kw_only: str, with_default: str = 'nothing'):
    print('first * sum(more) =', first * sum(more))
    print('the keyword argument is', kw_only)
    print(with_default, 'was passed for the argument that has a default')
