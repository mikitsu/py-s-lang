"""object substituation"""

__all__ = [
    'get_object',
    'use_object',
]


def get_object(**kwargs):
    return kwargs


def use_object(data: dict):
    for k, v in data.items():
        print(k, v)
