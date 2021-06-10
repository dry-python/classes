
from mypy.nodes import Decorator
from mypy.plugin import FunctionContext, MethodContext, MethodSigContext
from mypy.types import (
    AnyType,
    CallableType,
    FunctionLike,
    Instance,
    LiteralType,
    TupleType,
)
from mypy.types import Type as MypyType
from mypy.types import TypeOfAny, UnionType
from typing_extensions import final

from classes.contrib.mypy.typeops import (
    associated_types,
    inference,
    instance_args,
    type_loader,
    typecheck,
)


@final
class TypeClassReturnType(object):
    """
    Adjust argument types when we define typeclasses via ``typeclass`` function.

    It has two modes:
    1. As a decorator ``@typeclass``
    2. As a regular call with a class definition: ``typeclass(SomeProtocol)``

    It also checks how typeclasses are defined.
    """

    __slots__ = ('_typeclass', '_typeclass_def')

    def __init__(self, typeclass: str, typeclass_def: str) -> None:
        """We pass exact type names as the context."""
        self._typeclass = typeclass
        self._typeclass_def = typeclass_def

    def __call__(self, ctx: FunctionContext) -> MypyType:
        """Main entry point."""
        defn = ctx.arg_types[0][0]

        is_typeclass_def = (
            isinstance(ctx.default_return_type, Instance) and
            ctx.default_return_type.type.fullname == self._typeclass_def and
            isinstance(defn, FunctionLike) and
            defn.is_type_obj()
        )
        is_typeclass = (
            isinstance(ctx.default_return_type, Instance) and
            ctx.default_return_type.type.fullname == self._typeclass and
            isinstance(defn, CallableType) and
            defn.definition
        )

        if is_typeclass_def:
            assert isinstance(ctx.default_return_type, Instance)
            assert isinstance(defn, FunctionLike)
            return self._process_typeclass_def_return_type(
                ctx.default_return_type,
                defn,
                ctx,
            )
        elif is_typeclass:
            assert isinstance(ctx.default_return_type, Instance)
            assert isinstance(defn, CallableType)
            assert defn.definition
            instance_args.mutate_typeclass_def(
                ctx.default_return_type,
                defn.definition.fullname,
                ctx,
            )
            return ctx.default_return_type
        return AnyType(TypeOfAny.from_error)

    def _process_typeclass_def_return_type(
        self,
        typeclass_intermediate_def: Instance,
        defn: FunctionLike,
        ctx: FunctionContext,
    ) -> MypyType:
        type_info = defn.type_object()
        instance = Instance(type_info, [])
        typeclass_intermediate_def.args = (instance,)
        return typeclass_intermediate_def


def typeclass_def_return_type(ctx: MethodContext) -> MypyType:
    """
    Callback for cases like ``@typeclass(SomeType)``.

    What it does? It works with the associated types.
    It checks that ``SomeType`` is correct, modifies the current typeclass.
    And returns it back.
    """
    assert isinstance(ctx.default_return_type, Instance)
    # TODO: change to condition
    # This will allow us to warn users on `x = typeclass(T)(func)`,
    # instead of falling with exception.
    assert isinstance(ctx.context, Decorator)

    if isinstance(ctx.default_return_type.args[2], Instance):
        associated_types.check_type(ctx.default_return_type.args[2], ctx)

    instance_args.mutate_typeclass_def(
        ctx.default_return_type,
        ctx.context.func.fullname,
        ctx,
    )
    return ctx.default_return_type


def instance_return_type(ctx: MethodContext) -> MypyType:
    """Adjusts the typing signature on ``.instance(type)`` call."""
    assert isinstance(ctx.default_return_type, Instance)
    assert isinstance(ctx.type, Instance)

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
    """
    Class to check how instance definition is created.

    When it is called?
    It is called on the second call of ``.instance(str)(callback)``.

    We do a lot of stuff here:
    1. Typecheck usage correctness
    2. Adding new instance types to typeclass definition
    3. Adding ``Supports[]`` metadata

    """

    def __call__(self, ctx: MethodContext) -> MypyType:  # noqa: WPS218
        """Main entry point."""
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

        # We need to add `Supports` metadata before typechecking,
        # because it will affect type hierarchies.
        self._add_supports_metadata(typeclass, instance_type, ctx)

        typecheck.check_typeclass(
            typeclass_signature=typeclass.args[1],
            instance_signature=instance_signature,
            passed_types=ctx.type.args[0],
            ctx=ctx,
        )
        self._add_new_instance_type(
            typeclass=typeclass,
            new_type=instance_type,
            fullname=typeclass_ref.args[3].value,
            ctx=ctx,
        )

        # Without this line we won't mutate args of a class-defined typeclass:
        ctx.type.args[1].args = typeclass.args
        return ctx.default_return_type

    def _add_new_instance_type(
        self,
        typeclass: Instance,
        new_type: MypyType,
        fullname: str,
        ctx: MethodContext,
    ) -> None:
        has_multiple_decorators = (
            isinstance(ctx.context, Decorator) and
            len(ctx.context.decorators) > 1
        )
        if has_multiple_decorators:
            # If we have multiple decorators on a function,
            # it is not safe to assume
            # that all the regular instance type is fine. Here's an example:
            #
            # @some.instance(str)
            # @other.instance(int)
            # (instance: Union[str, int]) -> ...
            #
            # So, if we just copy copy `instance`,
            # both typeclasses will have both `int` and `str`
            # as their instance types. This is not what we want.
            # We want: `some` to have `str` and `other` to have `int`
            new_type = inference.infer_runtime_type_from_context(
                fallback=new_type,
                fullname=fullname,
                ctx=ctx,
            )

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

          >>> class ToStr(object):
          ...     ...

          >>> @typeclass(ToStr)
          ... def to_str(instance) -> str:
          ...     ...

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
        if not isinstance(typeclass.args[2], Instance):
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
