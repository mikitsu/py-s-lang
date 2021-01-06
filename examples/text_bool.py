"""TextBool usage"""
import py_s_lang

__all__ = ['is_true', 'get_object', 'get_zero']


def text_to_bool(value):
    if isinstance(value, str):
        value = value.lower()
    return value not in ('false', 'off', 'no', '-', '0') and bool(value)


def is_true(value: text_to_bool):
    print('yep' if value else 'nope')


def get_object():
    return object()


def get_zero():
    return 0
