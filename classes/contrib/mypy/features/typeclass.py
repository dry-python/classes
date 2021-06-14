from typing import Tuple

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
from mypy.types import TypeOfAny
from typing_extensions import final

from classes.contrib.mypy.typeops import (
    call_signatures,
    instance_args,
    mro,
    type_loader,
)
from classes.contrib.mypy.validation import (
    validate_associated_type,
    validate_typeclass,
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
    assert isinstance(ctx.context, Decorator)

    if isinstance(ctx.default_return_type.args[2], Instance):
        validate_associated_type.check_type(
            associated_type=ctx.default_return_type.args[2],
            ctx=ctx,
        )

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

    def __call__(self, ctx: MethodContext) -> MypyType:
        """Main entry point."""
        assert isinstance(ctx.type, Instance)
        assert isinstance(ctx.type.args[0], TupleType)
        assert isinstance(ctx.type.args[1], Instance)

        typeclass, fullname = self._load_typeclass(ctx.type.args[1], ctx)
        assert isinstance(typeclass.args[1], CallableType)

        instance_signature = ctx.arg_types[0][0]
        if not isinstance(instance_signature, CallableType):
            return ctx.default_return_type

        # We need to add `Supports` metadata before typechecking,
        # because it will affect type hierarchies.
        metadata = mro.MetadataInjector(
            typeclass.args[2],
            instance_signature.arg_types[0],
            ctx,
        )
        metadata.add_supports_metadata()

        is_proper_typeclass = validate_typeclass.check_typeclass(
            typeclass_signature=typeclass.args[1],
            instance_signature=instance_signature,
            fullname=fullname,
            passed_types=ctx.type.args[0],
            ctx=ctx,
        )
        if not is_proper_typeclass:
            # Since the typeclass is not valid,
            # we undo the metadata manipulation,
            # otherwise we would spam with invalid `Supports[]` base types:
            metadata.remove_supports_metadata()
            return AnyType(TypeOfAny.from_error)

        # If typeclass is checked, than it is safe to add new instance types:
        self._add_new_instance_type(
            typeclass=typeclass,
            new_type=instance_signature.arg_types[0],
            ctx=ctx,
        )
        return ctx.default_return_type

    def _load_typeclass(
        self,
        typeclass_ref: Instance,
        ctx: MethodContext,
    ) -> Tuple[Instance, str]:
        assert isinstance(typeclass_ref.args[3], LiteralType)
        assert isinstance(typeclass_ref.args[3].value, str)

        typeclass = type_loader.load_typeclass(
            fullname=typeclass_ref.args[3].value,
            ctx=ctx,
        )
        assert isinstance(typeclass, Instance)
        return typeclass, typeclass_ref.args[3].value

    def _add_new_instance_type(
        self,
        typeclass: Instance,
        new_type: MypyType,
        ctx: MethodContext,
    ) -> None:
        typeclass.args = (
            instance_args.add_unique(new_type, typeclass.args[0]),
            *typeclass.args[1:],
        )


def call_signature(ctx: MethodSigContext) -> CallableType:
    """Returns proper ``__call__`` signature of a typeclass."""
    assert isinstance(ctx.type, Instance)

    real_signature = ctx.type.args[1]
    if not isinstance(real_signature, CallableType):
        return ctx.default_signature

    passed_type = ctx.api.expr_checker.accept(ctx.args[0][0])  # type: ignore
    return call_signatures.SmartCallSignature(
        signature=real_signature,
        instance_type=ctx.type.args[0],
        associated_type=ctx.type.args[2],
        ctx=ctx,
    ).mutate_and_infer(passed_type)
