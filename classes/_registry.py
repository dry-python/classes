from types import MethodType
from typing import Callable, Dict, NoReturn, Optional

TypeRegistry = Dict[type, Callable]


def choose_registry(  # noqa: WPS211
    # It has multiple argumnets, but I don't see an easy and performant way
    # to refactor it: I don't want to create extra structures
    # and I don't want to create a class with methods.
    typ: type,
    is_protocol: bool,
    delegate: Optional[type],
    concretes: TypeRegistry,
    instances: TypeRegistry,
    protocols: TypeRegistry,
) -> TypeRegistry:
    """
    Returns the appropriate registry to store the passed type.

    It depends on how ``instance`` method is used and also on the type itself.
    """
    if is_protocol:
        return protocols

    is_concrete = (
        delegate is not None or
        isinstance(getattr(typ, '__instancecheck__', None), MethodType)
    )
    if is_concrete:
        # This means that this type has `__instancecheck__` defined,
        # which allows dynamic checks of what `isinstance` of this type.
        # That's why we also treat this type as a conrete.
        return concretes
    return instances


def default_implementation(instance, *args, **kwargs) -> NoReturn:
    """By default raises an exception."""
    raise NotImplementedError(
        'Missing matched typeclass instance for type: {0}'.format(
            type(instance).__qualname__,
        ),
    )
