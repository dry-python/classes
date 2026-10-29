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

from collections.abc import Callable
from typing import Final, final

from mypy.plugin import (
    AnalyzeTypeContext,
    FunctionContext,
    MethodContext,
    MethodSigContext,
    Plugin,
)
from mypy.types import CallableType
from mypy.types import Type as MypyType

from classes.contrib.mypy.features import associated_type, supports, typeclass

_ASSOCIATED_TYPE_FULLNAME: Final = "classes._typeclass.AssociatedType"
_TYPECLASS_FULLNAME: Final = "classes._typeclass._TypeClass"
_TYPECLASS_DEF_FULLNAME: Final = "classes._typeclass._TypeClassDef"
_TYPECLASS_INSTANCE_DEF_FULLNAME: Final = (
    "classes._typeclass._TypeClassInstanceDef"
)


@final
class _TypeClassPlugin(Plugin):
    """
    Our plugin for typeclasses.

    It has four steps:
    - Creating typeclasses via ``typeclass`` function
    - Adding cases for typeclasses via ``.instance()`` calls with explicit types
    - Adding callbacks functions after the ``.instance()`` decorator
    - Converting typeclasses to simple callable via ``__call__`` method

    Hooks are in the logical order.
    """

    def get_type_analyze_hook(
        self,
        fullname: str,
    ) -> Callable[[AnalyzeTypeContext], MypyType] | None:
        """Hook that works on type analyzer phase."""
        if fullname == _ASSOCIATED_TYPE_FULLNAME:
            return associated_type.variadic_generic
        if fullname == "classes._typeclass.Supports":
            associated_type_node = self.lookup_fully_qualified(
                _ASSOCIATED_TYPE_FULLNAME,
            )
            assert associated_type_node
            return supports.VariadicGeneric(associated_type_node)
        return None

    def get_function_hook(
        self,
        fullname: str,
    ) -> Callable[[FunctionContext], MypyType] | None:
        """Here we adjust the typeclass constructor."""
        if fullname == "classes._typeclass.typeclass":
            return typeclass.TypeClassReturnType(
                typeclass=_TYPECLASS_FULLNAME,
                typeclass_def=_TYPECLASS_DEF_FULLNAME,
            )
        return None

    def get_method_hook(
        self,
        fullname: str,
    ) -> Callable[[MethodContext], MypyType] | None:
        """Here we adjust the typeclass with new allowed types."""
        if fullname == f"{_TYPECLASS_DEF_FULLNAME}.__call__":
            return typeclass.TypeClassDefReturnType(_ASSOCIATED_TYPE_FULLNAME)
        if fullname == f"{_TYPECLASS_INSTANCE_DEF_FULLNAME}.__call__":
            return typeclass.InstanceDefReturnType()
        if fullname == f"{_TYPECLASS_FULLNAME}.instance":
            return typeclass.instance_return_type
        return None

    def get_method_signature_hook(
        self,
        fullname: str,
    ) -> Callable[[MethodSigContext], CallableType] | None:
        """Here we fix the calling method types to accept only valid types."""
        if fullname == f"{_TYPECLASS_FULLNAME}.__call__":
            return typeclass.call_signature
        return None


def plugin(version: str) -> type[Plugin]:
    """Plugin's public API and entrypoint."""
    return _TypeClassPlugin
