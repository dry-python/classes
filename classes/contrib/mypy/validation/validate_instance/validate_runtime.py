from typing import Optional

from mypy.erasetype import erase_type
from mypy.plugin import MethodContext
from mypy.sametypes import is_same_type
from mypy.subtypes import is_subtype
from mypy.types import CallableType, Instance, TupleType
from mypy.types import Type as MypyType
from typing_extensions import Final

from classes.contrib.mypy.typeops import type_queries
from classes.contrib.mypy.typeops.instance_context import InstanceContext

# Messages:

_INSTANCE_RUNTIME_MISMATCH_MSG: Final = (
    'Instance "{0}" does not match runtime type "{1}"'
)

_IS_PROTOCOL_MISSING_MSG: Final = (
    'Protocols must be passed with "is_protocol=True"'
)

_IS_PROTOCOL_UNWANTED_MSG: Final = (
    'Regular types must be passed with "is_protocol=False"'
)

_DELEGATE_STRICT_SUBTYPE_MSG: Final = (
    'Delegate types used for instance annotation "{0}" ' +
    'must be a direct subtype of runtime type "{1}"'
)

_CONCRETE_GENERIC_MSG: Final = (
    'Instance "{0}" has concrete generic type, ' +
    'it is not supported during runtime'
)

_UNBOUND_TYPE_MSG: Final = (
    'Runtime type "{0}" has unbound type, use implicit any'
)

_TUPLE_LENGTH_MSG: Final = (
    'Expected variadic tuple "Tuple[{0}, ...]", got "{1}"'
)


def check_type(
    instance_context: InstanceContext,
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
    return all([
        _check_matching_types(
            instance_context.runtime_type,
            instance_context.instance_type,
            instance_context.delegate,
            instance_context.ctx,
        ),
        _check_runtime_protocol(
            instance_context.runtime_type,
            is_protocol=instance_context.is_protocol,
            ctx=instance_context.ctx,
        ),
        _check_delegate_type(
            instance_context.runtime_type,
            instance_context.instance_signature,
            instance_context.delegate,
            instance_context.ctx,
        ),
        _check_concrete_generics(
            instance_context.runtime_type,
            instance_context.instance_type,
            instance_context.delegate,
            instance_context.ctx,
        ),
        _check_tuple_size(
            instance_context.instance_type,
            instance_context.delegate,
            instance_context.ctx,
        ),
    ])


def _check_matching_types(
    runtime_type: MypyType,
    instance_type: MypyType,
    delegate: Optional[MypyType],
    ctx: MethodContext,
) -> bool:
    instance_check = is_same_type(
        erase_type(instance_type),
        erase_type(runtime_type),
    )

    if not instance_check and delegate is not None:
        instance_check = is_same_type(
            instance_type,
            delegate,
        )

    if not instance_check:
        ctx.api.fail(
            _INSTANCE_RUNTIME_MISMATCH_MSG.format(instance_type, runtime_type),
            ctx.context,
        )
        return False
    return True


def _check_runtime_protocol(
    runtime_type: MypyType,
    ctx: MethodContext,
    *,
    is_protocol: Optional[bool],
) -> bool:
    if isinstance(runtime_type, Instance) and runtime_type.type:
        if is_protocol is False and runtime_type.type.is_protocol:
            ctx.api.fail(_IS_PROTOCOL_MISSING_MSG, ctx.context)
            return False
        elif is_protocol and not runtime_type.type.is_protocol:
            ctx.api.fail(_IS_PROTOCOL_UNWANTED_MSG, ctx.context)
            return False
    return True


def _check_delegate_type(
    runtime_type: MypyType,
    instance_signature: CallableType,
    delegate: Optional[MypyType],
    ctx: MethodContext,
) -> bool:
    if delegate is None:
        return True

    # We use direct `instance_signature` type here,
    # because `instance_context.instance_type` is a complicated beast.
    instance_type = instance_signature.arg_types[0]
    if not is_same_type(instance_type, delegate):
        return True

    is_runtime_subtype = is_subtype(delegate, runtime_type)
    if not is_runtime_subtype:
        ctx.api.fail(
            _DELEGATE_STRICT_SUBTYPE_MSG.format(delegate, runtime_type),
            ctx.context,
        )
        return False
    return True


def _check_concrete_generics(
    runtime_type: MypyType,
    instance_type: MypyType,
    delegate: Optional[MypyType],
    ctx: MethodContext,
) -> bool:
    has_concrete_type = False
    type_settings = (  # Not a dict, because of `hash` problems
        (instance_type, False),
        (runtime_type, True),
    )

    if delegate is None:
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
    return not has_concrete_type


def _check_tuple_size(
    instance_type: MypyType,
    delegate: Optional[MypyType],
    ctx: MethodContext,
) -> bool:
    if isinstance(instance_type, TupleType):
        ctx.api.fail(
            _TUPLE_LENGTH_MSG.format(instance_type.items[0], instance_type),
            ctx.context,
        )
        return False
    return True
