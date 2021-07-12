from typing import NamedTuple, Optional, Tuple

from mypy.plugin import MethodContext
from mypy.sametypes import is_same_type
from mypy.types import (
    CallableType,
    FunctionLike,
    Instance,
    LiteralType,
    TupleType,
)
from mypy.types import Type as MypyType
from mypy.types import UninhabitedType
from typing_extensions import final

from classes.contrib.mypy.typeops import inference


@final
class InstanceContext(NamedTuple):
    """
    Instance definition context.

    We use it to store all important types and data in one place
    to help with validation and type manipulations.
    """

    # Signatures:
    typeclass_signature: CallableType
    instance_signature: CallableType
    infered_signature: CallableType

    # Instance / runtime types:
    instance_type: MypyType
    runtime_type: MypyType

    # Passed arguments:
    passed_args: TupleType
    is_protocol: Optional[bool]
    delegate: Optional[MypyType]

    # Meta:
    fullname: str
    associated_type: MypyType

    # Mypy context:
    ctx: MethodContext

    @classmethod  # noqa: WPS211
    def build(  # noqa: WPS211
        # It has a lot of arguments, but I don't see how I can simply it.
        # I don't want to add steps or intermediate types.
        # It is okay for this method to have a lot arguments,
        # because it store a lot of data.
        cls,
        typeclass_signature: CallableType,
        instance_signature: CallableType,
        passed_args: TupleType,
        associated_type: MypyType,
        fullname: str,
        ctx: MethodContext,
    ) -> 'InstanceContext':
        """
        Builds instance context.

        It also infers several missing parts from the present data.
        Like real ``instance_type`` and arg types.
        """
        runtime_type = inference.infer_runtime_type_from_context(
            fallback=passed_args.items[0],
            fullname=fullname,
            ctx=ctx,
        )

        infered_signature = inference.try_to_apply_generics(
            signature=typeclass_signature,
            runtime_type=runtime_type,
            ctx=ctx,
        )

        is_protocol, delegate = _ArgumentInference(passed_args)()
        instance_type = _infer_instance_type(
            instance_type=instance_signature.arg_types[0],
            runtime_type=runtime_type,
            delegate=delegate,
        )

        return InstanceContext(
            typeclass_signature=typeclass_signature,
            instance_signature=instance_signature,
            infered_signature=infered_signature,
            instance_type=instance_type,
            runtime_type=runtime_type,
            passed_args=passed_args,
            is_protocol=is_protocol,
            delegate=delegate,
            associated_type=associated_type,
            fullname=fullname,
            ctx=ctx,
        )


@final
class _ArgumentInference(object):
    __slots__ = ('_passed_args',)

    def __init__(self, passed_args: TupleType) -> None:
        self._passed_args = passed_args

    def __call__(self) -> Tuple[Optional[bool], Optional[MypyType]]:
        _, is_protocol, delegate = self._passed_args.items
        return (
            self._infer_protocol_arg(is_protocol),
            self._infer_delegate_arg(delegate),
        )

    def _infer_protocol_arg(
        self,
        is_protocol: MypyType,
    ) -> Optional[bool]:
        if isinstance(is_protocol, UninhabitedType):
            return False

        is_protocol_bool = (
            isinstance(is_protocol, Instance) and
            isinstance(is_protocol.last_known_value, LiteralType) and
            isinstance(is_protocol.last_known_value.value, bool)
        )
        if is_protocol_bool:
            return is_protocol.last_known_value.value  # type: ignore
        return None

    def _infer_delegate_arg(
        self,
        delegate: MypyType,
    ) -> Optional[MypyType]:
        if isinstance(delegate, FunctionLike) and delegate.is_type_obj():
            return delegate.items()[-1].ret_type
        return None


def _infer_instance_type(
    instance_type: MypyType,
    runtime_type: MypyType,
    delegate: Optional[MypyType],
) -> MypyType:
    """
    Infers real instance type.

    We have three options here.
    First one, ``delegate`` is not set at all:

    .. code:: python

        @some.instance(list)
        def _some_list(instance: list) -> int:
            ...

    Then, infered instance type is just ``list``.

    Second, we have a delegate of its own:

    .. code:: python

        @some.instance(list, delegate=SomeDelegate)
        def _some_list(instance: list) -> int:
            ...

    Then, infered instance type is ``list`` as well.

    Lastly, we can have this case,
    when ``delegate`` type is used for instance annotation:

    .. code:: python

        @some.instance(list, delegate=SomeDelegate)
        def _some_list(instance: SomeDelegate) -> int:
            ...

    In this case, we will use runtime type ``list`` for instance type.
    """
    if delegate is not None and is_same_type(instance_type, delegate):
        return runtime_type
    return instance_type
