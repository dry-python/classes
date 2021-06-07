from mypy.plugin import MethodContext
from mypy.type_visitor import TypeQuery
from mypy.types import Instance
from mypy.types import Type as MypyType
from mypy.types import TypeVarType, UnboundType, get_proper_type


def has_concrete_type(instance_type: MypyType, ctx: MethodContext) -> bool:
    instance_type = get_proper_type(instance_type)
    if isinstance(instance_type, Instance):
        return any(
            type_arg.accept(_HasNoConcreteTypes(lambda _: True))
            for type_arg in instance_type.args
        )
    return False


def has_unbound_type(runtime_type: MypyType, ctx: MethodContext) -> bool:
    runtime_type = get_proper_type(runtime_type)
    if isinstance(runtime_type, Instance):
        return any(
            type_arg.accept(_HasUnboundTypes(lambda _: False))
            for type_arg in runtime_type.args
        )
    return False


class _HasNoConcreteTypes(TypeQuery[bool]):
    def visit_type_var(self, t: TypeVarType) -> bool:
        return False


class _HasUnboundTypes(TypeQuery[bool]):
    def visit_unbound_type(self, t: UnboundType) -> bool:
        return True
