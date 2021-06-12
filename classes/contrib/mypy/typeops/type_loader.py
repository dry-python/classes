from typing import Union

from mypy.plugin import MethodContext, MethodSigContext
from mypy.types import Instance
from mypy.types import Type as MypyType
from typing_extensions import Final


def load_typeclass(
    fullname: str,
    ctx: MethodContext,
) -> Instance:
    """Loads given typeclass from a symboltable by a fullname."""
    typeclass_info = ctx.api.lookup_qualified(fullname)  # type: ignore
    assert isinstance(typeclass_info.type, Instance)
    return typeclass_info.type
