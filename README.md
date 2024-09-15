# Python function overload

A function decorator that allows for real function overloading in Python 3.  Not
that `typing.overload` nonsense, but actual function overloading.

This module is a joke, please don't use it in production code.

## Usage

Overload-decorated function are grouped by name.  The name of the group is 
determined either by the name of the decorated function or by the `name`
argument to the `overload` decorator.

When a overloaded function is called, the arguments are matched against the
signatures of the functions in the group.  The first function whose signature
matches the arguments is called (in the order they were defined).

```python
from overload import overload

@overload
def foo(x: int):
    return x + 1

@overload
def foo(x: str):
    return x + '!'

assert foo(1) == 2
assert foo('hello') == 'hello!'
```
