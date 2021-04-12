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
from mypy.types import AnyType, CallableType, Instance
from mypy.types import Type as MypyType
from mypy.types import TypeOfAny, TypeVarType, UnionType


def _adjust_arguments(ctx: FunctionContext) -> MypyType:
    assert isinstance(ctx.default_return_type, Instance)

    typeclass_def = ctx.default_return_type.args[2]
    if not isinstance(typeclass_def, CallableType):  # TODO: FunctionLike?
        return ctx.default_return_type

    args = [
        typeclass_def.arg_types[0],
        typeclass_def.ret_type,
    ]

    # We use `Any` here to filter it later in `_add_new_type` method:
    typeclass_def.arg_types[0] = AnyType(TypeOfAny.unannotated)

    ctx.default_return_type.args = (
        *args,
        typeclass_def,
    )
    return ctx.default_return_type


def _adjust_call_signature(ctx: MethodSigContext) -> CallableType:
    assert isinstance(ctx.type, Instance)

    real_signature = ctx.type.args[2]
    if not isinstance(real_signature, CallableType):
        return ctx.default_signature

    real_signature.arg_types[0] = ctx.type.args[0]
    return real_signature


class _AdjustInstanceSignature(object):
    def instance(self, ctx: MethodContext) -> MypyType:
        instance_type = self._adjust_typeclass_callable(ctx)
        self._adjust_typeclass_type(ctx, instance_type)
        return ctx.default_return_type

    def _adjust_typeclass_callable(self, ctx: MethodContext) -> MypyType:
        assert isinstance(ctx.type, Instance)
        assert isinstance(ctx.default_return_type, CallableType)

        real_signature = ctx.type.args[2]
        to_adjust = ctx.default_return_type.arg_types[0]

        assert isinstance(real_signature, CallableType)
        assert isinstance(to_adjust, CallableType)

        instance_type = to_adjust.arg_types[0]
        instance_kind = to_adjust.arg_kinds[0]
        instance_name = to_adjust.arg_names[0]

        to_adjust.arg_types = real_signature.arg_types
        to_adjust.arg_kinds = real_signature.arg_kinds
        to_adjust.arg_names = real_signature.arg_names
        to_adjust.variables = real_signature.variables
        to_adjust.is_ellipsis_args = real_signature.is_ellipsis_args

        to_adjust.arg_types[0] = instance_type
        to_adjust.arg_kinds[0] = instance_kind
        to_adjust.arg_names[0] = instance_name

        return instance_type

    def _adjust_typeclass_type(
        self,
        ctx: MethodContext,
        instance_type: MypyType,
    ) -> None:
        assert isinstance(ctx.type, Instance)

        unified = list(filter(
            # It means that function was defined without annotation
            # or with explicit `Any`, we prevent our Union from polution.
            # Because `Union[Any, int]` is just `Any`.
            # We also clear accidential type vars.
            self._filter_out_unified_types,
            [instance_type, ctx.type.args[0]],
        ))

        if not isinstance(instance_type, TypeVarType):
            ctx.type.args = (
                UnionType.make_union(unified),
                *ctx.type.args[1:],
            )

    def _filter_out_unified_types(self, type_: MypyType) -> bool:
        return not isinstance(type_, (AnyType, TypeVarType))


class _TypedDecoratorPlugin(Plugin):
    def get_method_signature_hook(
        self,
        fullname: str,
    ) -> Optional[Callable[[MethodSigContext], CallableType]]:
        """Here we fix the calling method types to accept only valid types."""
        if fullname == 'classes.typeclass._TypeClass.__call__':
            return _adjust_call_signature
        return None

    def get_method_hook(
        self,
        fullname: str,
    ) -> Optional[Callable[[MethodContext], MypyType]]:
        """Here we adjust the typeclass with new allowed types."""
        if fullname == 'classes.typeclass._TypeClass.instance':
            return _AdjustInstanceSignature().instance
        return None

    def get_function_hook(
        self,
        fullname: str,
    ) -> Optional[Callable[[FunctionContext], MypyType]]:
        """Here we adjust the typeclass constructor."""
        if fullname == 'classes.typeclass.typeclass':
            return _adjust_arguments
        return None


def plugin(version: str) -> Type[Plugin]:
    """Plugin's public API and entrypoint."""
    return _TypedDecoratorPlugin
