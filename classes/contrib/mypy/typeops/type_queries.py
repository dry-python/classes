from mypy.plugin import MethodContext
from mypy.type_visitor import TypeQuery
from mypy.types import Instance
from mypy.types import Type as MypyType
from mypy.types import TypeVarType, UnboundType, get_proper_type


def has_concrete_type(instance_type: MypyType, ctx: MethodContext) -> bool:
    """
    Queries if your instance has any concrete types.

    What do we call "concrete types"? Some examples:

    ``List[X]`` is generic, ``List[int]`` is concrete.
    ``List[Union[int, str]]`` is also concrete.
    ``Dict[str, X]`` is also concrete.

    So, this helps to write code like this:

    .. code:: python

      @some.instance(list)
      def _some_list(instance: List[X]): ...

    And not like:

    .. code:: python

      @some.instance(list)
      def _some_list(instance: List[int]): ...

    """
    instance_type = get_proper_type(instance_type)
    if isinstance(instance_type, Instance):
        return any(
            type_arg.accept(_HasNoConcreteTypes(lambda _: True))
            for type_arg in instance_type.args
        )
    return False


def has_unbound_type(runtime_type: MypyType, ctx: MethodContext) -> bool:
    """
    Queries if your instance has any unbound types.

    Note, that you need to understand
    how semantic and type analyzers work in ``mypy``
    to understand what "unbound type" is.

    Long story short, this helps to write code like this:

    .. code:: python

      @some.instance(list)
      def _some_list(instance: List[X]): ...

    And not like:

    .. code:: python

      @some.instance(List[X])
      def _some_list(instance: List[X]): ...

    """
    runtime_type = get_proper_type(runtime_type)
    if isinstance(runtime_type, Instance):
        return any(
            type_arg.accept(_HasUnboundTypes(lambda _: False))
            for type_arg in runtime_type.args
        )
    return False


class _HasNoConcreteTypes(TypeQuery[bool]):  # TODO: support explicit `any`
    def visit_type_var(self, type_: TypeVarType) -> bool:
        return False


class _HasUnboundTypes(TypeQuery[bool]):
    def visit_unbound_type(self, type_: UnboundType) -> bool:
        return True
