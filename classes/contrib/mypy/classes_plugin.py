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

from typing import Callable, Optional, Type, Union

from mypy.plugin import FunctionContext, MethodContext, MethodSigContext, Plugin
from mypy.typeops import bind_self
from mypy.types import AnyType, CallableType, Instance
from mypy.types import Type as MypyType
from mypy.types import (
    TypeOfAny,
    TypeVarType,
    UninhabitedType,
    UnionType,
    get_proper_type,
)
from typing_extensions import final


@final
class _AdjustArguments(object):
    """
    Adjust argument types when we define typeclasses via ``typeclass`` function.

    It has two modes:
    1. As a decorator ``@typeclass``
    2. As a regular call with a class definition: ``typeclass(SomeProtocol)``

    It also checks how typeclasses are defined.
    """

    def __call__(self, ctx: FunctionContext) -> MypyType:
        is_defined_by_class = (
            isinstance(ctx.arg_types[0][0], CallableType) and
            not ctx.arg_types[0][0].arg_types and
            isinstance(ctx.arg_types[0][0].ret_type, Instance)
        )

        if is_defined_by_class:
            return self._adjust_protocol_arguments(ctx)
        elif isinstance(ctx.arg_types[0][0], CallableType):
            return self._adjust_function_arguments(ctx)
        return ctx.default_return_type

    def _adjust_protocol_arguments(self, ctx: FunctionContext) -> MypyType:
        assert isinstance(ctx.arg_types[0][0], CallableType)
        assert isinstance(ctx.arg_types[0][0].ret_type, Instance)

        instance = ctx.arg_types[0][0].ret_type
        type_info = instance.type
        signature = type_info.get_method('__call__')
        if not signature:
            ctx.api.fail(
                'Typeclass definition must have `__call__` method',
                ctx.context,
            )
            return AnyType(TypeOfAny.from_error)

        signature_type = get_proper_type(signature.type)
        assert isinstance(signature_type, CallableType)
        return self._adjust_typeclass(
            bind_self(signature_type),
            ctx,
            class_definition=instance,
        )

    def _adjust_function_arguments(self, ctx: FunctionContext) -> MypyType:
        assert isinstance(ctx.default_return_type, Instance)

        typeclass_def = ctx.default_return_type.args[2]
        assert isinstance(typeclass_def, CallableType)
        return self._adjust_typeclass(typeclass_def, ctx)

    def _adjust_typeclass(
        self,
        typeclass_def: MypyType,
        ctx: FunctionContext,
        class_definition: Optional[Instance] = None,
    ) -> MypyType:
        assert isinstance(typeclass_def, CallableType)
        assert isinstance(ctx.default_return_type, Instance)
        self._check_typeclass_definition(typeclass_def, ctx)

        typeclass_def.arg_types[0] = UninhabitedType()

        args = [
            typeclass_def.arg_types[0],
            typeclass_def.ret_type,
        ]

        definition_type = (
            class_definition
            if class_definition
            else UninhabitedType()
        )

        ctx.default_return_type.args = (*args, typeclass_def, definition_type)
        return ctx.default_return_type

    def _check_typeclass_definition(
        self,
        signature: CallableType,
        ctx: FunctionContext,
    ) -> None:
        instance_type = get_proper_type(signature.arg_types[0])
        if isinstance(instance_type, UninhabitedType):
            return

        if isinstance(instance_type, AnyType):
            if instance_type.type_of_any != TypeOfAny.unannotated:
                ctx.api.fail(
                    'Typeclass instance must not be annotated',
                    ctx.context,
                )
        else:
            ctx.api.fail(
                'Typeclass instance must be of `Any` type',
                ctx.context,
            )


def _adjust_call_signature(ctx: MethodSigContext) -> CallableType:
    """Returns proper ``__call__`` signature of a typeclass."""
    assert isinstance(ctx.type, Instance)

    real_signature = ctx.type.args[2]
    if not isinstance(real_signature, CallableType):
        return ctx.default_signature

    real_signature.arg_types[0] = ctx.type.args[0]

    if isinstance(ctx.type.args[3], Instance):
        supports_spec = _load_supports_type(ctx.type.args[3], ctx)
        real_signature.arg_types[0] = UnionType.make_union([
            real_signature.arg_types[0],
            supports_spec,
        ])

    return real_signature


@final
class _AdjustInstanceSignature(object):
    """
    Adjusts the typing signature after ``.instance(type)`` call.

    We need this to get typing match working:
    so the type mentioned in ``.instance()`` call
    will be the same as the one in a function later on.
    """

    def __call__(self, ctx: MethodContext) -> MypyType:
        instance_type = self._adjust_typeclass_callable(ctx)
        self._adjust_typeclass_type(ctx, instance_type)
        if isinstance(instance_type, Instance):
            self._add_supports_metadata(ctx, instance_type)
        return ctx.default_return_type

    def _adjust_typeclass_callable(
        self,
        ctx: MethodContext,
    ) -> MypyType:
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
            # or with explicit `Any`, we prevent our Union from pollution.
            # Because `Union[Any, int]` is just `Any`.
            # We also clear accidental type vars.
            self._filter_out_unified_types,
            [instance_type, ctx.type.args[0]],
        ))

        ctx.type.args = (
            UnionType.make_union(unified),
            *ctx.type.args[1:],
        )

    def _add_supports_metadata(
        self,
        ctx: MethodContext,
        instance_type: Instance,
    ) -> None:
        """
        Injects fake ``Supports[TypeClass]`` parent classes into ``mro``.

        Ok, this is wild. Why do we need this?
        Because, otherwise expressing ``Supports`` is not possible,
        here's an example:

        .. code:: python

          >>> from classes import Supports, typeclass
          >>> from typing_extensions import Protocol

          >>> class ToStr(Protocol):
          ...     def __call__(self, instance) -> str:
          ...         ...

          >>> to_str = typeclass(ToStr)
          >>> @to_str.instance(int)
          ... def _to_str_int(instance: int) -> str:
          ...      return 'Number: {0}'.format(instance)

          >>> assert to_str(1) == 'Number: 1'

        Now, let's use ``Supports`` to only pass specific
        typeclass instances in a function:

        .. code:: python

           >>> def convert_to_string(arg: Supports[ToStr]) -> str:
           ...     return to_str(arg)

        This is possible, due to a fact that we insert ``Supports[ToStr]``
        into all classes that are mentioned as ``.instance()`` for ``ToStr``
        typeclass.

        So, we can call:

        .. code:: python

           >>> assert convert_to_string(1) == 'Number: 1'

        But, ``convert_to_string(None)`` will raise a type error.
        """
        assert isinstance(ctx.type, Instance)

        supports_spec = _load_supports_type(ctx.type.args[3], ctx)

        if supports_spec not in instance_type.type.bases:
            instance_type.type.bases.append(supports_spec)
        if supports_spec.type not in instance_type.type.mro:
            instance_type.type.mro.insert(0, supports_spec.type)

    def _filter_out_unified_types(self, type_: MypyType) -> bool:
        return not isinstance(type_, (TypeVarType, UninhabitedType))


def _load_supports_type(
    arg_type: MypyType,
    ctx: Union[MethodContext, MethodSigContext],
) -> Instance:
    """
    Loads ``Supports[]`` type with proper generic type.

    It uses the short name,
    because for some reason full name is not always loaded.
    """
    assert isinstance(ctx.type, Instance)
    class_definition = ctx.type.args[3]

    supports_spec = ctx.api.named_generic_type(
        'classes.Supports',
        [class_definition],
    )
    assert supports_spec
    supports_spec.type._promote = None  # noqa: WPS437
    return supports_spec


class _TypedDecoratorPlugin(Plugin):
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
            return _AdjustArguments()
        return None

    def get_method_hook(
        self,
        fullname: str,
    ) -> Optional[Callable[[MethodContext], MypyType]]:
        """Here we adjust the typeclass with new allowed types."""
        if fullname == 'classes._typeclass._TypeClass.instance':
            return _AdjustInstanceSignature()
        return None

    def get_method_signature_hook(
        self,
        fullname: str,
    ) -> Optional[Callable[[MethodSigContext], CallableType]]:
        """Here we fix the calling method types to accept only valid types."""
        if fullname == 'classes._typeclass._TypeClass.__call__':
            return _adjust_call_signature
        return None


def plugin(version: str) -> Type[Plugin]:
    """Plugin's public API and entrypoint."""
    return _TypedDecoratorPlugin
