from typing import List

from mypy.types import ProperType
from mypy.types import Type as MypyType
from mypy.types import flatten_nested_unions, get_proper_type


def union_items(typ: MypyType) -> List[ProperType]:
    """Get and flat all union types."""
    return [
        get_proper_type(union_member)
        for union_member in flatten_nested_unions([typ])
    ]
