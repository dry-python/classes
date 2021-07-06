from typing import NamedTuple, Optional, Tuple

from mypy.plugin import MethodContext
from mypy.types import FunctionLike, Instance, LiteralType, TupleType
from mypy.types import Type as MypyType
from mypy.types import UninhabitedType
from typing_extensions import Final, final

# Messages:

_IS_PROTOCOL_LITERAL_BOOL_MSG: Final = (
    'Use literal bool for "is_protocol" argument, got: "{0}"'
)

_PROTOCOL_AND_DELEGATE_PASSED_MSG: Final = (
    'Both "is_protocol" and "delegate" arguments passed, they are exclusive'
)


@final
class _ArgValidationContext(NamedTuple):
    """"""

    is_protocol: bool
    delegate: Optional[MypyType]
    check_result: bool


def check_type(
    passed_types: TupleType,
    ctx: MethodContext,
) -> _ArgValidationContext:
    passed_args = passed_types.items

    is_protocol, protocol_check = _check_protocol_arg(passed_args[1], ctx)
    delegate, delegate_check = _check_delegate_arg(passed_args[2], ctx)

    return _ArgValidationContext(
        is_protocol=is_protocol,
        delegate=delegate,
        check_result=all([
            protocol_check,
            delegate_check,
            _check_all_args(passed_types, ctx),
        ]),
    )


def _check_protocol_arg(
    is_protocol: MypyType,
    ctx: MethodContext,
) -> Tuple[bool, bool]:
    if isinstance(is_protocol, UninhabitedType):
        return False, True

    is_protocol_bool = (
        isinstance(is_protocol, Instance) and
        isinstance(is_protocol.last_known_value, LiteralType) and
        isinstance(is_protocol.last_known_value.value, bool)
    )
    if is_protocol_bool:
        return is_protocol.last_known_value.value, True  # type: ignore

    ctx.api.fail(
        _IS_PROTOCOL_LITERAL_BOOL_MSG.format(is_protocol),
        ctx.context,
    )
    return False, False


def _check_delegate_arg(
    delegate: MypyType,
    ctx: MethodContext,
) -> Tuple[Optional[MypyType], bool]:
    # TODO: maybe we need to inforce that `delegate` should be
    # similar to `runtime_type`?
    # For example, we can ask for subtypes of `runtime_type`.
    # However, motivation is not clear for now.
    if isinstance(delegate, FunctionLike) and delegate.is_type_obj():
        return delegate.items()[-1].ret_type, True
    return None, True


def _check_all_args(
    passed_types: TupleType,
    ctx: MethodContext,
) -> bool:
    fake_args = [
        passed_arg
        for passed_arg in passed_types.items[1:]
        if isinstance(passed_arg, UninhabitedType)
    ]
    if not fake_args:
        ctx.api.fail(_PROTOCOL_AND_DELEGATE_PASSED_MSG, ctx.context)
        return False
    return True
