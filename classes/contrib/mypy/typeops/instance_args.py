from typing import List, Union

from mypy.plugin import FunctionContext, MethodContext
from mypy.typeops import make_simplified_union
from mypy.types import Instance, TupleType
from mypy.types import Type as MypyType
from mypy.types import TypeVarType, UninhabitedType


def add_unique(
    new_instance_type: MypyType,
    existing_instance_type: MypyType,
) -> MypyType:
    unified = list(filter(
        lambda type_: not isinstance(type_, (TypeVarType, UninhabitedType)),
        [new_instance_type, existing_instance_type],
    ))
    return make_simplified_union(unified)


def mutate_typeclass_instance_def(
    instance: Instance,
    *,
    passed_types: List[MypyType],
    typeclass: Instance,
    ctx: Union[MethodContext, FunctionContext],
) -> None:
    tuple_type = TupleType(
        passed_types,
        fallback=ctx.api.named_type('builtins.tuple'),  # type: ignore
    )

    instance.args = (
        tuple_type,  # Passed runtime types, like str in `@some.instance(str)`
        typeclass,  # `_TypeClass` instance itself
    )
