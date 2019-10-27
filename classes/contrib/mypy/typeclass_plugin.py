# -*- coding: utf-8 -*-

"""
Custom mypy plugin to enable typeclass concept to work.

Features:

- We return a valid ``typeclass`` generic instance from `@typeclass` contructor
- We force ``.instance()`` calls to extend the union of allowed types
- We ensure that when calling the typeclass'es function
  we know what values can be used as inputs

``mypy`` API docs are here:
https://mypy.readthedocs.io/en/latest/extending_mypy.html

We use ``pytest-mypy-plugins`` to test that it works correctly, see:
https://github.com/TypedDjango/pytest-mypy-plugins
"""

from typing import Type

from mypy.plugin import Plugin
from mypy.types import AnyType, UnionType, TypeOfAny, CallableType


def _adjust_arguments(ctx):
    typeclass_def = ctx.default_return_type.args[2]
    if not isinstance(typeclass_def, CallableType):
        return ctx.default_return_type

    ctx.default_return_type.args = [
        typeclass_def.arg_types[0],
        typeclass_def.ret_type,
    ]

    # We use `Any` here to filter it later in `_add_new_type` method:
    typeclass_def.arg_types[0] = AnyType(TypeOfAny.unannotated)
    ctx.default_return_type.args.append(typeclass_def)
    return ctx.default_return_type


def _adjust_call_signature(ctx):
    real_signature = ctx.type.args[2]
    if not isinstance(real_signature, CallableType):
        return ctx.default_signature

    real_signature.arg_types[0] = ctx.type.args[0]
    return real_signature


class _AdjustInstanceSignature(object):
    def instance(self, ctx):
        instance_type = self._adjust_typeclass_callable(ctx)
        self._adjust_typeclass_type(ctx, instance_type)
        return ctx.default_return_type

    def _adjust_typeclass_callable(self, ctx):
        real_signature = ctx.type.args[2]
        to_adjust = ctx.default_return_type.arg_types[0]

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

    def _adjust_typeclass_type(self, ctx, instance_type):
        unified = list(filter(
            # It means that function was defined without annotation
            # or with explicit `Any`, we prevent our Union from polution.
            # Because `Union[Any, int]` is just `Any`.
            lambda type_: not isinstance(type_, AnyType),
            [instance_type, ctx.type.args[0]],
        ))

        if len(unified) == 1:
            # We don't want to mix `Union[A]` into the types,
            # which sometimes works just like an alias for `Optional[A]`:
            ctx.type.args[0] = instance_type
        else:
            ctx.type.args[0] = UnionType(unified)


class _TypedDecoratorPlugin(Plugin):
    def get_method_signature_hook(self, fullname: str):
        """Here we fix the calling method types to accept only valid types."""
        if fullname == 'classes.typeclass._TypeClassMethod.__call__':
            return _adjust_call_signature
        return None

    def get_method_hook(self, fullname: str):
        """Here we adjust the typeclass with new allowed types."""
        if fullname == 'classes.typeclass._TypeClassMethod.instance':
            return _AdjustInstanceSignature().instance
        return None

    def get_function_hook(self, fullname: str):
        """Here we adjust the typeclass constructor."""
        if fullname == 'classes.typeclass.typeclass':
            return _adjust_arguments
        return None


def plugin(version: str) -> Type[Plugin]:
    """Plugin's public API and entrypoint."""
    return _TypedDecoratorPlugin
