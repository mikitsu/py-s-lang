"""very simple shell-like language"""
import shlex
import argparse
import codecs
import string
import inspect
import typing
import importlib
import runpy
import sys


class LangError(Exception):
    pass


class VariableTemplate(string.Template):
    """also allow numbers"""
    idpattern = r'(?a:[_a-z0-9]+)'


class BuiltinCommands:
    def print(*values, end='\n', sep=' ', file=sys.stdout, flush: bool = False):
        print(*values, end=end, sep=sep, file=file, flush=flush)
    def fwrite(file, content):
        with open(file, mode='w') as f:
            f.write(content)
    def fread(file, mode='r'):
        with open(file, mode) as f:
            return f.read()
    def list(*args): return list(args)
    def dict(**kwargs): return kwargs
    def int(value: int): return value
    def float(value: float): return value


def parse_arguments(argv, option_kwargs=()):
    """parse arguments and return (args, kwargs)

        ``option_kwargs`` may be a container of flag options
            which will be translated to True for --option
            and False for --no-option. Before comparison,
            dashes in the option are replaced by underscores.
    """
    args = []
    kwargs = {}
    argv_iter = iter(argv)
    for arg in argv_iter:
        if arg == '--':
            args.extend(argv_iter)
        elif arg.startswith('--'):
            if '=' in arg:
                name, value = arg[2:].split('=', 1)
                name = name.replace('-', '_')
            else:
                name = arg[2:]
                name = name.replace('-', '_')
                if name[3*name.startswith('no_'):] in option_kwargs:
                    value = not name.startswith('no_')
                    name = name[3*name.startswith('no_'):]
                else:
                    try:
                        value = next(argv_iter)
                    except StopIteration:
                        raise LangError('no value for keyword argument "{}"'
                                        .format(name))
            if not name.isidentifier():
                raise LangError('invalid argument name "{}"'
                                .format(name))
            kwargs[name] = value
        else:
            args.append(arg)
    return args, kwargs


class FunctionWrapper:
    def __init__(self, func):
        """wrap a function"""
        self.func = func
        self.sig = inspect.signature(func)
        # don't use sig.parameters[x].annotation to follow strings
        self.arg_types = typing.get_type_hints(func)
        self.bool_params = [k for k, v in self.arg_types.items() if v is bool]

    def parse(self, argv):
        return parse_arguments(argv, option_kwargs=self.bool_params)

    def apply(self, args, kwargs):
        """call the function with the specified arguments, enforcing type hints"""
        def convert(type_, value):
            if isinstance(type_, type) and isinstance(value, type_):
                return value
            else:
                return type_(value)

        try:
            bound = self.sig.bind(*args, **kwargs)
        except TypeError as e:
            raise LangError(str(e))

        for name, value in bound.arguments.items():
            arg_type = self.arg_types.get(name)
            param_kind = self.sig.parameters[name].kind
            if arg_type is not None:
                if param_kind is inspect.Parameter.VAR_POSITIONAL:
                    value = [convert(arg_type, v) for v in value]
                elif param_kind is inspect.Parameter.VAR_KEYWORD:
                    value = {k: convert(arg_type, v) for k, v in value.items()}
                else:
                    value = convert(arg_type, value)
                bound.arguments[name] = value

        return self.func(*bound.args, **bound.kwargs)


def interpret(functions, code):
    """interpret the given code with the given functions"""
    def apply_substitutions(value):
        if not isinstance(value, str):
            return value
        m = VariableTemplate.pattern.match(value)
        name = m and (m.group('named') or m.group('braced'))
        try:
            if name and m.end() == len(value):
                return substitutions[name]
            else:
                return VariableTemplate(value).substitute(substitutions)
        except KeyError as e:
            raise LangError(str(e))

    def execute_function(func_name, *args):
        try:
            func = functions[func_name]
        except KeyError:
            raise LangError('no such function "{}"'.format(func_name))

        args, kwargs = func.parse(args)
        subst_args = [apply_substitutions(a) for a in args]
        subst_kwargs = {k: apply_substitutions(v) for k, v in kwargs.items()}

        return func.apply(subst_args, subst_kwargs)

    variables = {}
    last_results = []
    for func_name, *args in code:
        substitutions = {str(i): v for i, v in
                         enumerate(reversed(last_results))}
        substitutions.update(variables)
        if func_name.endswith('='):
            target = func_name[:-1]
            if not args:
                value = None
            elif len(args) == 1:
                value = apply_substitutions(args[0])
            else:
                value = execute_function(*args)
            variables[target] = value
        else:
            last_results.append(execute_function(func_name, *args))


def prepare_code(text):
    """parse the source and apply escapes"""
    return filter(None, (
        shlex.split(
            codecs.decode(line.encode('latin-1'), 'unicode_escape'),
            comments=True
        ) for line in text.replace('\\\n', '').splitlines()
    ))


def prepare_functions(module_dict, include_builtins=True):
    """get module callables and wrap them in FunctionWrapper

        If __all__ is available, use it; otherwise fall back
        to searching the whole namespace for callables

        ``include_builtins`` may be an iterable of functions from
            the builtin commands to also include or a true value
            to include all available builtin commands
    """
    if not isinstance(include_builtins, typing.Iterable):
        if include_builtins:
            include_builtins = (k for k in dir(BuiltinCommands) if not k.startswith('_'))
        else:
            include_builtins = ()
    functions = {k: getattr(BuiltinCommands, k) for k in include_builtins}
    names = module_dict.get('__all__', module_dict)
    functions.update({name: module_dict[name]
                      for name in names if callable(module_dict[name])})
    return {k: FunctionWrapper(v) for k, v in functions.items()}


def main(args):
    functions = prepare_functions(args.input_dict)
    code = prepare_code(args.infile.read())
    args.infile.close()
    interpret(functions, code)


def get_args():
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '-m', '--module',
        help='an import path to a Python module providing the functions',
        type=lambda m: importlib.import_module(m).__dict__,
        dest='input_dict',
        metavar='MODULE',
    )
    input_group.add_argument(
        '-f', '--file',
        help='a Python file providing the functions',
        type=runpy.run_path,
        dest='input_dict',
        metavar='FILE',
    )
    parser.add_argument('infile', help='the file with the commands. STDIN by default',
                        nargs='?', type=argparse.FileType(), default='-')
    return parser.parse_args()


if __name__ == '__main__':
    main(get_args())
