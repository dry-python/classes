# -*- coding: utf-8 -*-

"""
Here we store the utility stuff to work with the implementations.

Should not be used directly.
That's our internal stuff.

Copied and modified from:
https://github.com/thejohnfreeman/python-typeclasses

Thanks!
"""


def _empty():
    pass


def _docstring():
    """Just an empty function with a docstring."""


def _elipsis():
    ...


def _elipsis_and_docstring():
    """Empty function with a docstring."""
    ...


def _code(function):
    """
    Return the byte code for a function.

    If this Python interpreter does not supply the byte code for functions,
    then this function returns NaN so that all functions compare unequal.
    """
    return (
        function.__code__.co_code
        if hasattr(function, '__code__')
        else float('nan')
    )


def is_empty(function) -> bool:
    """
    Return whether a function has an empty body.

    We need this to make sure that our default implementation can be called.
    Or not.
    """
    return _code(function) in {
        _code(_empty),
        _code(_docstring),
        _code(_elipsis),
        _code(_elipsis_and_docstring),
    }
