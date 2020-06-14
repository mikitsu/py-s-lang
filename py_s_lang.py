"""very simple shell-like language""" 
import shlex
import argparse
import codecs
import string
import inspect
import typing
import importlib


class LangError(Exception):
    pass


class FuncArgumentParser(argparse.ArgumentParser):
    """don't exit on errors, but raise LangError"""
    def error(self, message):
        raise LangError(message)


class VariableTemplate(string.Template):
    """also allow numbers"""
    idpattern = r'(?a:[_a-z0-9]+)'


class FunctionWrapper:
    def __init__(self, func):
        """wrap a function"""
        self.func = func
        self.sig = inspect.signature(func)
        # don't use sig.parameters[x].annotation to follow strings
        self.arg_types = typing.get_type_hints(func)
        parser = FuncArgumentParser()
        parser.add_argument('*positional', nargs='*')
        for name, param in self.sig.parameters.items():
            if param.kind in (inspect.Parameter.KEYWORD_ONLY,
                              inspect.Parameter.POSITIONAL_OR_KEYWORD):
                # no type= here bc. we also have positional arguments
                parser.add_argument('--'+name, default=argparse.SUPPRESS)
        self.parser = parser

    def apply(self, argv):
        """call the function with the specified arguments"""
        args = self.parser.parse_args(argv)
        positional = args.__dict__.pop('*positional')
        try:
            bound = self.sig.bind(*positional, **args.__dict__)
        except TypeError as e:
            raise LangError(str(e))

        for name, value in bound.arguments.items():
            arg_type = self.arg_types.get(name, str)
            param_kind = self.sig.parameters[name].kind
            if param_kind is inspect.Parameter.VAR_POSITIONAL:
                value = [arg_type(v) for v in value]
            elif param_kind is inspect.Parameter.VAR_KEYWORD:
                value = {k: arg_type(v) for k, v in value.items()}
            else:
                value = arg_type(value)
            bound.arguments[name] = value

        return self.func(*bound.args, **bound.kwargs)


def interpret(functions, code):
    """interpret the given code with the given functions"""
    variables = {}
    last_results = []
    for func_name, *args in code:
        try:
            func = functions[func_name]
        except KeyError:
            raise LangError('no such function "{}"'.format(func_name))
        last_res_subst = dict(enumerate(reversed(last_results)))
        subst_args = []
        for arg in args:
            try:
                if False:  # TODO: for only a single substitution, use the object
                    pass
                else:
                    arg = arg.substitute(last_res_subst, **variables)
            except KeyError as e:
                raise LangError(str(e))
            else:
                subst_args.append(arg)
        last_results.append(func.apply(subst_args))


def prepare_code(text):
    """parse the source, apply escapes and wrap with VariableTemplate"""
    return [
        [split_line[0], *map(VariableTemplate, split_line[1:])]
        for split_line in
        (shlex.split(
            codecs.decode(line.encode('latin-1'), 'unicode_escape'),
            comments=True
         ) for line in
         map(str.strip, text.replace('\\\n', '').splitlines())
         if line
        )
    ]


def prepare_functions(module_dict):
    """get module callables and wrap them in FunctionWrapper

        If __all__ is available, use it; otherwise fall back
        to searching the whole namespace for callables
    """
    names = module_dict.get('__all__', module_dict)
    return {name: FunctionWrapper(module_dict[name])
            for name in names if callable(module_dict[name])}


def main(args):
    functions = prepare_functions(args.module.__dict__)
    code = prepare_code(args.infile.read())
    args.infile.close()
    interpret(functions, code)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('module', help='the Python module providing the functions',
                        type=importlib.import_module)
    parser.add_argument('infile', help='the file with the commands. STDIN by default',
                        nargs='?', type=argparse.FileType(), default='-')
    return parser.parse_args()


if __name__ == '__main__':
    main(get_args())
