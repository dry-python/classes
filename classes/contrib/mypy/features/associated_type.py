from mypy.plugin import AnalyzeTypeContext
from mypy.types import Instance
from mypy.types import Type as MypyType


def variadic_generic(ctx: AnalyzeTypeContext) -> MypyType:
    """
    Variadic generic support.

    What is "variadic generic"?
    It is a generic type with any amount of type variables.
    Starting with 0 up to infinity.

    We primarily use it for our ``AssociatedType`` implementation.
    """
    sym = ctx.api.lookup_qualified(ctx.type.name, ctx.context)  # type: ignore
    if not sym or not sym.node:
        # This will happen if `Supports[IsNotDefined]` will be called.
        return ctx.type
    return Instance(
        sym.node,
        ctx.api.anal_array(ctx.type.args),  # type: ignore
    )
