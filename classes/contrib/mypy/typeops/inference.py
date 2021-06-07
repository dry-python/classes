
from typing import Optional

from mypy.nodes import Decorator, Expression
from mypy.plugin import MethodContext
from mypy.typeops import make_simplified_union
from mypy.types import FunctionLike, Instance, LiteralType
from mypy.types import Type as MypyType
from typing_extensions import Final

_TYPECLASS_DEF_FULLNAMES: Final = frozenset((
    'classes._typeclass._TypeClassInstanceDef',
))


def infer_runtime_type_from_context(
    fallback: MypyType,
    ctx: MethodContext,
    fullname: Optional[str] = None,
) -> MypyType:
    """
    Infers instance type from several ``@some.instance()`` decorators.

    We have a problem: when user has two ``.instance()`` decorators
    on a single function, inference will work only
    for a single one of them at the time.

    So, let's say you have this:

    .. code:: python

      @some.instance(str)
      @some.instance(int)
      def _some_int_str(instance: Union[str, int]): ...

    Your instance has ``Union[str, int]`` annotation as it should have.
    But, our ``fallback`` type would be just ``int`` on the first call
    and just ``str`` on the second call.

    And this will break our ``is_same_type`` check,
    because ``Union[str, int]`` is not the same as ``int`` or ``str``.

    In this case we need to fetch all typeclass decorators and infer
    the resulting type manually.
    """
    if isinstance(ctx.context, Decorator) and len(ctx.context.decorators) > 1:
        # Why do we only care for this case?
        # Because if it is a call / or just a single decorator,
        # then we are fine with regular type inference.
        # Infered type from `mypy` is good enough, just return `fallback`.
        instance_types = []
        for decorator in ctx.context.decorators:
            instance_type = _get_typeclass_instance_type(decorator, fullname, ctx)
            if instance_type is not None:
                instance_types.append(_post_process_type(instance_type))

        # Infered resulting type:
        return make_simplified_union(instance_types)
    return _post_process_type(fallback)


def _get_typeclass_instance_type(
    expr: Expression,
    fullname: Optional[str],
    ctx: MethodContext,
) -> Optional[MypyType]:
    expr_type = ctx.api.expr_checker.accept(expr)  # type: ignore
    is_typeclass_instance_def = (
        isinstance(expr_type, Instance) and
        bool(expr_type.type) and
        expr_type.type.fullname in _TYPECLASS_DEF_FULLNAMES and
        isinstance(expr_type.args[1], Instance)
    )
    if is_typeclass_instance_def:
        is_same_typeclass = (
            isinstance(expr_type.args[1].args[3], LiteralType) and
            expr_type.args[1].args[3].value == fullname or
            fullname is None
        )
        if is_same_typeclass:
            return expr_type.args[0].items[0]
    return None


def _post_process_type(type_: MypyType) -> MypyType:
    if isinstance(type_, FunctionLike) and type_.is_type_obj():
        # What happens here?
        # Let's say you define a function like this:
        #
        # @some.instance(Sized)
        # (instance: Sized, b: int) -> str: ...
        #
        # So, you will recieve callable type
        # `def () -> Sized` as `runtime_type` in this case.
        # We need to convert it back to regular `Instance`.
        #
        # It can also be `Overloaded` type,
        # but they are safe to return the same `type_object`,
        # however we still use `ret_type`,
        # because it is practically the same thing,
        # but with proper type arguments.
        return type_.items()[0].ret_type
    return type_
