"""
Custom mypy plugin to enable typeclass concept to work.

Features:

- We return a valid ``typeclass`` generic instance
  from ``@typeclass`` constructor
- We force ``.instance()`` calls to extend the union of allowed types
- We ensure that when calling the typeclass'es function
  we know what values can be used as inputs

``mypy`` API docs are here:
https://mypy.readthedocs.io/en/latest/extending_mypy.html

We use ``pytest-mypy-plugins`` to test that it works correctly, see:
https://github.com/TypedDjango/pytest-mypy-plugins

"""

from typing import Callable, Optional, Type

from mypy.plugin import FunctionContext, MethodContext, MethodSigContext, Plugin
from mypy.types import CallableType
from mypy.types import Type as MypyType
from typing_extensions import final

from classes.contrib.mypy.features import typeclass


@final
class _TypeClassPlugin(Plugin):
    """
    Our plugin for typeclasses.

    It has three steps:
    - Creating typeclasses via ``typeclass`` function
    - Adding cases for typeclasses via ``.instance()`` calls
    - Converting typeclasses to simple callable via ``__call__`` method

    Hooks are in the logical order.
    """

    def get_function_hook(
        self,
        fullname: str,
    ) -> Optional[Callable[[FunctionContext], MypyType]]:
        """Here we adjust the typeclass constructor."""
        if fullname == 'classes._typeclass.typeclass':
            return typeclass.ConstructorReturnType()
        if fullname == 'instance of _TypeClass':
            # `@some.instance` call without params:
            return typeclass.InstanceReturnType.from_function_decorator
        return None

    def get_method_hook(
        self,
        fullname: str,
    ) -> Optional[Callable[[MethodContext], MypyType]]:
        """Here we adjust the typeclass with new allowed types."""
        if fullname == 'classes._typeclass._TypeClass.instance':
            # `@some.instance` call with explicit params:
            return typeclass.InstanceReturnType()
        return None

    def get_method_signature_hook(
        self,
        fullname: str,
    ) -> Optional[Callable[[MethodSigContext], CallableType]]:
        """Here we fix the calling method types to accept only valid types."""
        if fullname == 'classes._typeclass._TypeClass.__call__':
            return typeclass.call_signature
        return None


def plugin(version: str) -> Type[Plugin]:
    """Plugin's public API and entrypoint."""
    return _TypeClassPlugin
