from mypy.erasetype import erase_type
from mypy.plugin import MethodContext
from mypy.sametypes import is_same_type
from mypy.subtypes import is_subtype
from mypy.types import AnyType, CallableType, Instance, LiteralType, TupleType
from mypy.types import Type as MypyType
from mypy.types import TypeOfAny

from classes.contrib.mypy.typeops import inference, type_queries


def check_typeclass(
    typeclass_signature: CallableType,
    instance_signature: CallableType,
    passed_types: TupleType,
    ctx: MethodContext,
) -> bool:
    """
    We need to typecheck passed functions in order to build correct typeclasses.

    What do we do here?
    1. When ``@some.instance(type_)`` is used, we typecheck that ``type_``
       matches original typeclass definition,
       like: ``def some(instance: MyType)``
    2. If ``def _some_ex(instance: type_)`` is used,
       we also check the function signature
       to be compatible with the typeclass definition
    3. TODO

    TODO: explain covariance and contravariance
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
    # TODO: check cases like `some.instance(1)`, only allow types and calls
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
    simplified_typeclass_signature = typeclass_signature.copy_modified(
        arg_types=[
            AnyType(TypeOfAny.implementation_artifact),
            *typeclass_signature.arg_types[1:],
        ]
    )
    simplified_instance_signature = instance_signature.copy_modified(
        arg_types=[
            AnyType(TypeOfAny.implementation_artifact),
            *instance_signature.arg_types[1:],
        ]
    )
    signature_check = is_subtype(
        simplified_typeclass_signature,
        simplified_instance_signature,
    )
    if not signature_check:
        ctx.api.fail(
            'Argument 1 has incompatible type "{0}"; expected "{1}"'.format(
                instance_signature,
                typeclass_signature.copy_modified(arg_types=[
                    instance_signature.arg_types[0],
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
    instance_check = is_subtype(
        instance_signature.arg_types[0],
        typeclass_signature.arg_types[0],
    )
    if not instance_check:
        ctx.api.fail(
            'Instance "{0}" does not match original type "{1}"'.format(
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
    runtime_type = inference.infer_runtime_type_from_context(
        passed_types.items[0],
        ctx,
    )

    if len(passed_types.items) == 2:
        assert isinstance(passed_types.items[1], Instance)
        assert isinstance(passed_types.items[1].last_known_value, LiteralType)
        is_protocol = passed_types.items[1].last_known_value.value
        assert isinstance(is_protocol, bool)
    else:
        is_protocol = False


    instance_type = instance_signature.arg_types[0]
    instance_check = is_same_type(
        erase_type(instance_type),
        erase_type(runtime_type),
    )
    if not instance_check:
        ctx.api.fail(
            'Instance "{0}" does not match runtime type "{1}"'.format(
                instance_type,
                runtime_type,
            ),
            ctx.context,
        )

    return (
        _check_runtime_protocol(runtime_type, ctx, is_protocol=is_protocol) and
        _check_concrete_generics(instance_type, runtime_type, ctx) and
        instance_check
    )


def _check_runtime_protocol(
    runtime_type: MypyType,
    ctx: MethodContext,
    *,
    is_protocol: bool,
) -> bool:
    if isinstance(runtime_type, Instance) and not is_protocol:
        if runtime_type.type and runtime_type.type.is_protocol:
            ctx.api.fail(
                'Protocols must be passed with `is_protocol=True`',
                ctx.context,
            )
            return False
    return True


def _check_concrete_generics(
    instance_type: MypyType,
    runtime_type: MypyType,
    ctx: MethodContext,
) -> bool:
    has_concrete_type = type_queries.has_concrete_type(instance_type, ctx)
    if has_concrete_type:
        ctx.api.fail(
            'Instance "{0}" has concrete type, use generics instead'.format(
                instance_type,
            ),
            ctx.context,
        )

    has_unbound_type = type_queries.has_unbound_type(runtime_type, ctx)
    if has_unbound_type:
        print(runtime_type.args[0], type(runtime_type.args[0]))
        ctx.api.fail(
            'Runtime type "{0}" has unbound type, use implicit any'.format(
                runtime_type,
            ),
            ctx.context,
        )
    return has_concrete_type and has_unbound_type
