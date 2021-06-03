from mypy.plugin import MethodContext
from mypy.subtypes import is_subtype
from mypy.types import AnyType, CallableType, Instance, TypeOfAny


def check_typeclass(
    instance_signature: CallableType,
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

    """
    assert isinstance(ctx.default_return_type, CallableType)
    assert isinstance(ctx.type, Instance)
    assert isinstance(ctx.type.args[1], CallableType)

    typeclass_signature = ctx.type.args[1]
    assert isinstance(typeclass_signature, CallableType)

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
    return signature_check and instance_check


def _check_typeclass_signature(
    typeclass_signature: CallableType,
    instance_signature: CallableType,
    ctx: MethodContext,
) -> bool:
    if ctx.arg_names[0]:
        # This check only makes sence when we use annotations directly.
        return True

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
