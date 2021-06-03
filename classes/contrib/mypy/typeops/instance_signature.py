from mypy.argmap import map_actuals_to_formals
from mypy.checker import detach_callable
from mypy.constraints import infer_constraints_for_callable
from mypy.expandtype import expand_type
from mypy.nodes import TempNode
from mypy.plugin import MethodContext
from mypy.stats import is_generic
from mypy.types import CallableType
from mypy.types import Type as MypyType


def prepare(
    typeclass_signature: CallableType,
    instance_type: MypyType,
    ctx: MethodContext,
) -> CallableType:
    """Creates proper signature from typeclass definition and given instance."""
    instance_definition = typeclass_signature.arg_types[0]
    if is_generic(instance_definition):
        return _prepare_generic(typeclass_signature, instance_type, ctx)
    return _prepare_regular(typeclass_signature, instance_type, ctx)


def _prepare_generic(
    typeclass_signature: CallableType,
    instance_type: MypyType,
    ctx: MethodContext,
) -> CallableType:
    formal_to_actual = map_actuals_to_formals(
        [typeclass_signature.arg_kinds[0]],
        [typeclass_signature.arg_names[0]],
        typeclass_signature.arg_kinds,
        typeclass_signature.arg_names,
        lambda index: ctx.api.accept(TempNode(  # type: ignore
            instance_type, context=ctx.context,
        )),
    )
    constraints = infer_constraints_for_callable(
        typeclass_signature,
        [instance_type],
        [typeclass_signature.arg_kinds[0]],
        formal_to_actual,
    )
    return detach_callable(expand_type(
        typeclass_signature,
        {
            constraint.type_var: constraint.target
            for constraint in constraints
        },
    ))


def _prepare_regular(
    typeclass_signature: CallableType,
    instance_type: MypyType,
    ctx: MethodContext,
) -> CallableType:
    to_adjust = ctx.default_return_type.arg_types[0]

    assert isinstance(typeclass_signature, CallableType)
    assert isinstance(to_adjust, CallableType)

    instance_kind = to_adjust.arg_kinds[0]
    instance_name = to_adjust.arg_names[0]

    to_adjust.arg_types = typeclass_signature.arg_types
    to_adjust.arg_kinds = typeclass_signature.arg_kinds
    to_adjust.arg_names = typeclass_signature.arg_names
    to_adjust.variables = typeclass_signature.variables
    to_adjust.is_ellipsis_args = typeclass_signature.is_ellipsis_args
    to_adjust.ret_type = typeclass_signature.ret_type

    to_adjust.arg_types[0] = instance_type
    to_adjust.arg_kinds[0] = instance_kind
    to_adjust.arg_names[0] = instance_name

    return detach_callable(to_adjust)
