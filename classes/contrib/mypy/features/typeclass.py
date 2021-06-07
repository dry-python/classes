from typing import Optional

from mypy.plugin import FunctionContext, MethodContext, MethodSigContext
from mypy.typeops import bind_self
from mypy.types import AnyType, CallableType, Instance, LiteralType, TupleType
from mypy.types import Type as MypyType
from mypy.types import TypeOfAny, UninhabitedType, UnionType, get_proper_type
from typing_extensions import final

from classes.contrib.mypy.typeops import instance_args, type_loader, typecheck


@final
class ConstructorReturnType(object):
    """
    Adjust argument types when we define typeclasses via ``typeclass`` function.

    It has two modes:
    1. As a decorator ``@typeclass``
    2. As a regular call with a class definition: ``typeclass(SomeProtocol)``

    It also checks how typeclasses are defined.
    """

    def __call__(self, ctx: FunctionContext) -> MypyType:
        defn = ctx.arg_types[0][0]
        is_defined_by_class = (
            isinstance(defn, CallableType) and
            not defn.arg_types and
            isinstance(defn.ret_type, Instance)
        )

        if is_defined_by_class:
            return self._adjust_protocol_arguments(ctx)
        elif isinstance(defn, CallableType):
            assert defn.definition
            return self._adjust_typeclass(defn, defn.definition.fullname, ctx)
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
            type_info.fullname,
            ctx,
            class_definition=instance,
        )

    def _adjust_typeclass(
        self,
        typeclass_def: MypyType,
        definition_fullname: str,
        ctx: FunctionContext,
        *,
        class_definition: Optional[Instance] = None,
    ) -> MypyType:
        assert isinstance(typeclass_def, CallableType)
        assert isinstance(ctx.default_return_type, Instance)

        str_fallback = ctx.api.str_type()  # type: ignore

        ctx.default_return_type.args = (
            UninhabitedType(),  # We start with empty set of instances
            typeclass_def,
            class_definition if class_definition else UninhabitedType(),
            LiteralType(definition_fullname, str_fallback),
        )
        return ctx.default_return_type


@final
class InstanceReturnType(object):
    """
    Adjusts the typing signature after ``.instance(type)`` call.

    We need this to get typing match working:
    so the type mentioned in ``.instance()`` call
    will be the same as the one in a function later on.

    We use ``ctx.arg_names[0]`` to determine which mode is used:
    1. If it is empty, than annotation-based dispatch method is used
    2. If it is not empty, that means that decorator with arguments is used,
       like ``@some.instance(MyType)``

    """

    def __call__(self, ctx: MethodContext) -> MypyType:
        """"""
        assert isinstance(ctx.default_return_type, Instance)
        assert isinstance(ctx.type, Instance)

        # This is the case for `@some.instance(str)` decorator:
        instance_args.mutate_typeclass_instance_def(
            ctx.default_return_type,
            ctx=ctx,
            typeclass=ctx.type,
            passed_types=[
                type_
                for args in ctx.arg_types
                for type_ in args
            ],
        )
        return ctx.default_return_type


@final
class InstanceDefReturnType(object):
    def __call__(self, ctx: MethodContext) -> MypyType:
        assert isinstance(ctx.type, Instance)
        assert isinstance(ctx.type.args[0], TupleType)
        assert isinstance(ctx.type.args[1], Instance)

        typeclass_ref = ctx.type.args[1]
        assert isinstance(typeclass_ref.args[3], LiteralType)
        assert isinstance(typeclass_ref.args[3].value, str)

        typeclass = type_loader.load_typeclass(
            fullname=typeclass_ref.args[3].value,
            ctx=ctx,
        )
        assert isinstance(typeclass.args[1], CallableType)

        instance_signature = ctx.arg_types[0][0]
        assert isinstance(instance_signature, CallableType)
        instance_type = instance_signature.arg_types[0]

        typecheck.check_typeclass(
            typeclass_signature=typeclass.args[1],
            instance_signature=instance_signature,
            passed_types=ctx.type.args[0],
            ctx=ctx,
        )
        self._add_new_instance_type(typeclass, instance_type)
        self._add_supports_metadata(typeclass, instance_type, ctx)
        return ctx.default_return_type

    def _add_new_instance_type(
        self,
        typeclass: Instance,
        new_type: MypyType,
    ) -> None:
        typeclass.args = (
            instance_args.add_unique(new_type, typeclass.args[0]),
            *typeclass.args[1:],
        )

    def _add_supports_metadata(
        self,
        typeclass: Instance,
        instance_type: MypyType,
        ctx: MethodContext,
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
        if not isinstance(instance_type, Instance):
            return

        assert isinstance(ctx.type, Instance)

        supports_spec = type_loader.load_supports_type(typeclass.args[2], ctx)
        if supports_spec not in instance_type.type.bases:
            instance_type.type.bases.append(supports_spec)
        if supports_spec.type not in instance_type.type.mro:
            instance_type.type.mro.insert(0, supports_spec.type)


def call_signature(ctx: MethodSigContext) -> CallableType:
    """Returns proper ``__call__`` signature of a typeclass."""
    assert isinstance(ctx.type, Instance)

    real_signature = ctx.type.args[1]
    if not isinstance(real_signature, CallableType):
        return ctx.default_signature

    real_signature.arg_types[0] = ctx.type.args[0]

    if isinstance(ctx.type.args[2], Instance):
        # Why do we need this check?
        # Let's see what will happen without it:
        # For example, typeclass `ToJson` with `int` and `str` have will have
        # `Union[str, int]` as the first argument type.
        # But, we need `Union[str, int, Supports[ToJson]]`
        # That's why we are loading this type if the definition is there.
        supports_spec = type_loader.load_supports_type(ctx.type.args[2], ctx)
        real_signature.arg_types[0] = UnionType.make_union([
            real_signature.arg_types[0],
            supports_spec,
        ])
    return real_signature
