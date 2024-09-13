from __future__ import annotations

__all__ = ['FunctionOverload', 'overload']

from collections import defaultdict
from functools import partial
from inspect import Parameter, signature, stack
from types import ModuleType
from typing import Any, Callable, DefaultDict, Dict, overload as typing_overload
import warnings

_overload_registry = None


def _get_overload_registry(
) -> defaultdict[ModuleType, DefaultDict[str, Dict[int, Callable[..., Any]]]]:
    global _overload_registry

    if _overload_registry is not None:
        return _overload_registry

    try:
        from typing import _overload_registry as impl  # Not public API.

        _overload_registry = impl
        return _overload_registry
    except ImportError:
        warnings.warn(
            'could not find `_overload_registry` in `typing` module;  using'
            ' custom implementation', ImportWarning)

    # Copy of the [standard implementation][1].
    # [1]: https://github.com/python/cpython/blob/c5e11bec91c9980e6a718b5281362fb33e7999bf/Lib/typing.py#L2502
    _overload_registry = defaultdict(partial(defaultdict, dict))
    return _overload_registry


class FunctionOverload:
    """Callable object that dispatches calls to the first stored function with
    the appropriate signature.
    """

    def __init__(self, name: str, register: bool = True):
        self.name = name
        self.register = register
        self._fns = []  # Order is important.

    def add(self, fn: Callable[..., Any]) -> FunctionOverload:
        self._fns.append(fn)

        if self.register:
            # May help type checkers.
            reg = _get_overload_registry()
            reg[fn.__module__][fn.__qualname__][fn.__code__.co_firstlineno] = fn

        return self

    def _dispatch(self, *args, **kwargs) -> int:
        for i, fn in enumerate(self._fns):
            sig = signature(fn)

            try:
                # Arguments should at least bind to the signature (right number
                # of arguments).
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()

                # Check type hints.
                for param, value in bound.arguments.items():
                    typ = sig.parameters[param].annotation

                    if typ is Parameter.empty:
                        continue
                    elif isinstance(value, typ):
                        continue
                    elif typ is Any:  # TODO: Check for `typing` types.
                        continue

                    #raise TypeError(f'expected `{typ.__name__}` type for'
                    #                ' argument `{param}`')
                    raise TypeError()
            except TypeError:
                continue

            return i

        raise TypeError(f'no matching overload for function `{self.name}` and'
                        ' call signature')

    def __call__(self, *args, **kwargs) -> Any:
        i = self._dispatch(*args, **kwargs)
        return self._fns[i](*args, **kwargs)


@typing_overload
def overload(fn: Callable[..., Any]) -> FunctionOverload:
    ...


@typing_overload
def overload(
    name: str | None = None
) -> Callable[[Callable[..., Any]], FunctionOverload]:
    ...


# Yes, we typing-overload the non-typing `overload` function.
def overload(arg=None):
    """Function overload decorator.  It can be applied to functions within the
    same scope to define multiple overloads for a single function.
    Call signatures are checked in order of definition, and the first matching
    overload is called.
    Be aware that the decorator will not return a function, but a
    `FunctionOverload` callable object.
    """

    if callable(arg):
        return overload()(arg, scope_level=2)
    elif arg is None:
        pass
    elif not isinstance(arg, str):
        raise TypeError('expected function name as argument')

    def decorator(fn: Callable[..., Any],
                  scope_level: int = 1) -> FunctionOverload:
        name = arg or fn.__name__

        frame = stack()[scope_level][0]

        if name in frame.f_locals:  # Variable already defined in scope.
            fn_overload = frame.f_locals[name]
        else:
            fn_overload = FunctionOverload(name)

        fn_overload.add(fn)
        frame.f_locals[name] = fn_overload

        # Will set the `fn_overload` to the local scope (name of the decorated
        # function).
        return fn_overload

    return decorator
