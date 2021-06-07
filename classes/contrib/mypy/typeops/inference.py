
from typing import Optional

from mypy.nodes import Decorator, Expression
from mypy.plugin import MethodContext
from mypy.typeops import make_simplified_union
from mypy.types import FunctionLike, Instance
from mypy.types import Type as MypyType
from typing_extensions import Final

_TYPECLASS_DEF_FULLNAMES: Final = frozenset((
    'classes._typeclass._TypeClassInstanceDef',
))


def infer_runtime_type_from_context(
    fallback: MypyType,
    ctx: MethodContext,
) -> MypyType:
    if isinstance(ctx.context, Decorator) and len(ctx.context.decorators) > 1:
        # Why do we only care for this case?
        # TODO
        instance_types = []
        for decorator in ctx.context.decorators:
            instance_type = _get_typeclass_instance_type(decorator, ctx)
            if instance_type is not None:
                instance_types.append(_post_process_type(instance_type))
        return make_simplified_union(instance_types)
    return _post_process_type(fallback)


def _get_typeclass_instance_type(
    expr: Expression,
    ctx: MethodContext,
) -> Optional[MypyType]:
    expr_type = ctx.api.expr_checker.accept(expr)
    is_typeclass_instance_def = (
        isinstance(expr_type, Instance) and
        bool(expr_type.type) and
        expr_type.type.fullname in _TYPECLASS_DEF_FULLNAMES
    )
    if is_typeclass_instance_def:
        return expr_type.args[0].items[0]  # type: ignore
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
