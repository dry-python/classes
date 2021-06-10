from typing import Tuple

from mypy.erasetype import erase_type
from mypy.plugin import MethodContext
from mypy.sametypes import is_same_type
from mypy.subtypes import is_subtype
from mypy.types import AnyType, CallableType, Instance, LiteralType, TupleType
from mypy.types import Type as MypyType
from mypy.types import TypeOfAny
from typing_extensions import Final

from classes.contrib.mypy.typeops import inference, type_queries

_INCOMPATIBLE_INSTANCE_MSG: Final = (
    'Instance callback is incompatible "{0}"; expected "{1}"'
)

_INSTANCE_RESTRICTION_MSG: Final = (
    'Instance "{0}" does not match original type "{1}"'
)

_INSTANCE_RUNTIME_MISMATCH_MSG: Final = (
    'Instance "{0}" does not match runtime type "{1}"'
)

_IS_PROTOCOL_LITERAL_BOOL_MSG: Final = (
    'Use literal bool for "is_protocol" argument, got: "{0}"'
)

_IS_PROTOCOL_MISSING_MSG: Final = (
    'Protocols must be passed with "is_protocol=True"'
)

_IS_PROTOCOL_UNWANTED_MSG: Final = (
    'Regular types must be passed with "is_protocol=False"'
)

_CONCRETE_GENERIC_MSG: Final = (
    'Instance "{0}" has concrete generic type, ' +
    'it is not supported during runtime'
)

_UNBOUND_TYPE_MSG: Final = (
    'Runtime type "{0}" has unbound type, use implicit any'
)


def check_typeclass(
    typeclass_signature: CallableType,
    instance_signature: CallableType,
    passed_types: TupleType,
    ctx: MethodContext,
) -> bool:
    """
    We need to typecheck passed functions in order to build correct typeclasses.

    Please, see docs on each step.
    """
    signature_check = _check_typeclass_signature(
        typeclass_signature,
        instance_signature,
        ctx,
    )
    instance_check = _check_instance_type(
        typeclass_signature,
        instance_signature,
        ctx,
    )
    runtime_check = _check_runtime_type(
        passed_types,
        instance_signature,
        ctx,
    )
    return signature_check and instance_check and runtime_check


def _check_typeclass_signature(
    typeclass_signature: CallableType,
    instance_signature: CallableType,
    ctx: MethodContext,
) -> bool:
    """
    Checks that instance signature is compatible with.

    We use contravariant on arguments and covariant on return type logic here.
    What does this mean?

    Let's say that you have this typeclass signature:

    .. code:: python

      class A: ...
      class B(A): ...
      class C(B): ...

      @typeclass
      def some(instance, arg: B) -> B: ...

    What instance signatures will be compatible?

    .. code:: python

      (instance: ..., arg: B) -> B: ...
      (instance: ..., arg: A) -> C: ...

    But, any other cases will raise an error.

    .. note::
        We don't check instance types here at all,
        we replace it with ``Any``.
        See special function, where we check instance type.

    """
    simplified_typeclass_signature = typeclass_signature.copy_modified(
        arg_types=[
            AnyType(TypeOfAny.implementation_artifact),
            *typeclass_signature.arg_types[1:],
        ],
    )
    simplified_instance_signature = instance_signature.copy_modified(
        arg_types=[
            AnyType(TypeOfAny.implementation_artifact),
            *instance_signature.arg_types[1:],
        ],
    )
    signature_check = is_subtype(
        simplified_instance_signature,
        simplified_typeclass_signature,
    )
    if not signature_check:
        ctx.api.fail(
            _INCOMPATIBLE_INSTANCE_MSG.format(
                instance_signature,
                typeclass_signature.copy_modified(arg_types=[
                    instance_signature.arg_types[0],  # Better error message
                    *typeclass_signature.arg_types[1:],
                ]),
            ),
            ctx.context,
        )
    return signature_check


def _check_instance_type(
    typeclass_signature: CallableType,
    instance_signature: CallableType,
    ctx: MethodContext,
) -> bool:
    """
    Checks instance type, helpful when typeclass has type restrictions.

    We use covariant logic on instance type.
    What does this mean?

    .. code:: python

      class A: ...
      class B(A): ...
      class C(B): ...

      @typeclass
      def some(instance: B): ...

    What can we use on instance callbacks?

    .. code:: python

      (instance: B)
      (instance: C)

    Any other cases will raise an error.
    """
    instance_check = is_subtype(
        instance_signature.arg_types[0],
        typeclass_signature.arg_types[0],
    )
    if not instance_check:
        ctx.api.fail(
            _INSTANCE_RESTRICTION_MSG.format(
                instance_signature.arg_types[0],
                typeclass_signature.arg_types[0],
            ),
            ctx.context,
        )
    return instance_check


def _check_runtime_type(
    passed_types: TupleType,
    instance_signature: CallableType,
    ctx: MethodContext,
) -> bool:
    """
    Checks runtime type.

    We call "runtime types" things that we use at runtime to dispatch our calls.
    For example:

    1. We check that type passed in ``some.instance(...)`` matches
       one defined in a type annotation
    2. We check that types don't have any concrete types
    3. We check that types don't have any unbound type variables
    4. We check that ``is_protocol`` is passed correctly

    """
    runtime_type = inference.infer_runtime_type_from_context(
        passed_types.items[0],
        ctx,
    )

    if len(passed_types.items) == 2:
        is_protocol, protocol_arg_check = _check_protocol_arg(passed_types, ctx)
    else:
        is_protocol = False
        protocol_arg_check = True

    instance_type = instance_signature.arg_types[0]
    instance_check = is_same_type(
        erase_type(instance_type),
        erase_type(runtime_type),
    )
    if not instance_check:
        ctx.api.fail(
            _INSTANCE_RUNTIME_MISMATCH_MSG.format(instance_type, runtime_type),
            ctx.context,
        )

    return (
        _check_runtime_protocol(runtime_type, ctx, is_protocol=is_protocol) and
        _check_concrete_generics(instance_type, runtime_type, ctx) and
        protocol_arg_check and
        instance_check
    )


def _check_protocol_arg(
    passed_types: TupleType,
    ctx: MethodContext,
) -> Tuple[bool, bool]:
    passed_arg = passed_types.items[1]
    is_literal_bool = (
        isinstance(passed_arg, Instance) and
        isinstance(passed_arg.last_known_value, LiteralType) and
        isinstance(passed_arg.last_known_value.value, bool)
    )
    if is_literal_bool:
        return passed_arg.last_known_value.value, True  # type: ignore

    ctx.api.fail(
        _IS_PROTOCOL_LITERAL_BOOL_MSG.format(passed_types.items[1]),
        ctx.context,
    )
    return False, False


def _check_runtime_protocol(
    runtime_type: MypyType,
    ctx: MethodContext,
    *,
    is_protocol: bool,
) -> bool:
    if isinstance(runtime_type, Instance) and runtime_type.type:
        if not is_protocol and runtime_type.type.is_protocol:
            ctx.api.fail(_IS_PROTOCOL_MISSING_MSG, ctx.context)
            return False
        elif is_protocol and not runtime_type.type.is_protocol:
            ctx.api.fail(_IS_PROTOCOL_UNWANTED_MSG, ctx.context)
            return False
    return True


def _check_concrete_generics(
    instance_type: MypyType,
    runtime_type: MypyType,
    ctx: MethodContext,
) -> bool:
    has_concrete_type = False
    type_settings = (  # Not a dict, because of `hash` problems
        (instance_type, False),
        (runtime_type, True),
    )

    for type_, forbid_explicit_any in type_settings:
        local_check = type_queries.has_concrete_type(
            type_,
            ctx,
            forbid_explicit_any=forbid_explicit_any,
        )
        if local_check:
            ctx.api.fail(_CONCRETE_GENERIC_MSG.format(type_), ctx.context)
        has_concrete_type = has_concrete_type or local_check

    if type_queries.has_unbound_type(runtime_type, ctx):
        ctx.api.fail(_UNBOUND_TYPE_MSG.format(runtime_type), ctx.context)
        return False
    return has_concrete_type
