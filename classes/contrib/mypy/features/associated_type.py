from mypy.plugin import AnalyzeTypeContext
from mypy.types import Type as MypyType
from mypy.types import Instance


def variadic_generic(ctx: AnalyzeTypeContext) -> MypyType:
    sym = ctx.api.lookup_qualified(ctx.type.name, ctx.context)
    if not sym or not sym.node:
        return ctx.type
    return Instance(sym.node, ctx.api.anal_array(ctx.type.args))
