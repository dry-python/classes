from mypy.types import ProperType, Type, UnionType, get_proper_type


def union_items(typ: Type) -> list[ProperType]:
    """Return the flattened items of a union type.

    For non-union types, return a list containing just the argument.

    This is a re-implementation of the old `mypy.types.union_items`
    function (v0.970):
    Since mypy version 0.980 they removed this function from `mypy.types`.
    """
    # https://github.com/python/mypy/blob/1f08cf44c7ec3dc4111aaf817958f7a51018ba38/mypy/types.py#L2960
    typ = get_proper_type(typ)
    if isinstance(typ, UnionType):
        union_types = []
        for a_type in typ.items:
            union_types.extend(union_items(a_type))
        return union_types

    return [typ]
