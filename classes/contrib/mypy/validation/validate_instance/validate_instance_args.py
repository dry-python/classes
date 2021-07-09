from typing import Optional

from mypy.plugin import MethodContext
from mypy.types import TupleType, UninhabitedType
from typing_extensions import Final

from classes.contrib.mypy.typeops.instance_context import InstanceContext

# Messages:

_IS_PROTOCOL_LITERAL_BOOL_MSG: Final = (
    'Use literal bool for "is_protocol" argument, got: "{0}"'
)

_PROTOCOL_AND_DELEGATE_PASSED_MSG: Final = (
    'Both "is_protocol" and "delegate" arguments passed, they are exclusive'
)


def check_type(
    instance_context: InstanceContext,
) -> bool:
    """
    Checks that args to ``.instance`` method are correct.

    We cannot use ``@overload`` on ``.instance`` because ``mypy``
    does not correctly handle ``ctx.api.fail`` on ``@overload`` items:
    it then tries new ones, which produce incorrect results.
    So, that's why we need this custom checker.
    """
    return all([
        _check_protocol_arg(instance_context.is_protocol, instance_context.ctx),
        _check_all_args(instance_context.passed_args, instance_context.ctx),
    ])


def _check_protocol_arg(
    is_protocol: Optional[bool],
    ctx: MethodContext,
) -> bool:
    if is_protocol is None:
        ctx.api.fail(
            _IS_PROTOCOL_LITERAL_BOOL_MSG.format(is_protocol),
            ctx.context,
        )
        return False
    return True


def _check_all_args(
    passed_args: TupleType,
    ctx: MethodContext,
) -> bool:
    fake_args = [
        passed_arg
        for passed_arg in passed_args.items[1:]
        if isinstance(passed_arg, UninhabitedType)
    ]
    if not fake_args:
        ctx.api.fail(_PROTOCOL_AND_DELEGATE_PASSED_MSG, ctx.context)
        return False
    return True
