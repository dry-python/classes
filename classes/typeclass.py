# -*- coding: utf-8 -*-

from typing import Generic, TypeVar, Type, Callable, NoReturn, overload, Optional

import typing_inspect
from typing_extensions import Literal

_TypeclassType = TypeVar('_TypeclassType')
_ReturnType = TypeVar('_ReturnType')
_CallbackType = TypeVar('_CallbackType')
_InstanceType = TypeVar('_InstanceType')


class _TypeClassMethod(Generic[_TypeclassType, _ReturnType, _CallbackType]):
    """"""

    _fallback: Optional[_CallbackType]

    def __init__(self, signature: _CallbackType) -> None:
        self._signature = signature
        self._fallback = None
        self._instances = {}  # type: ignore

    def __call__(
        self,
        instance: _TypeclassType,
        *args,
        **kwargs,
    ) -> _ReturnType:
        instance_type = type(instance)
        implementation = self._instances.get(instance_type, None)
        if implementation is not None:
            return implementation(instance, *args, **kwargs)
        if self._fallback:
            return self._fallback(instance, *args, **kwargs)  # type: ignore
        raise NotImplementedError(
            'Missing matched typeclass instance for type: {0}'.format(
                instance_type,
            ),
        )

    def instance(
        self,
        type_argument: Type[_InstanceType],
        *,
        is_protocol: bool = False,  # TODO: protocol checks
    ) -> Callable[
        [Callable[[_InstanceType], _ReturnType]],
        NoReturn,
    ]:
        if typing_inspect.is_generic_type(type_argument):
            # This is required due to `isinstance([], List[int])`
            # raising a `TypeError` in runtime:
            # https://github.com/python/mypy/issues/949
            type_argument = typing_inspect.get_origin(type_argument)

        def decorator(implementation):
            self._instances[type_argument] = implementation
            return implementation
        return decorator

    def test(self) -> None:
        return None


def typeclass(
    default_implementation: _CallbackType,
) -> _TypeClassMethod[_TypeclassType, _ReturnType, _CallbackType]:
    """

    Basic usage
    ~~~~~~~~~~~

    The first and the simplest example of a typeclass is just its definition:

    .. code:: python

        >>> from classes import typeclass
        >>> @typeclass(default=True)
        ... def example(instance) -> str:
        ...     return 'default example'
        ...
        >>> example(1)
        'default example'

    In this example we work with the default implementation of a typeclass.
    Default implementation is executed when no other types matches.
    And we don't yet have a special case for ``int``,
    that why we fallback to the default implementation.

    It works like a regular function right now.
    Let's do the next step and introduce
    the ``int`` instance for the typeclass:

    .. code:: python

        >>> @example.instance(int)
        ... def _example_int(instance: int) -> str:
        ...     return 'int case'
        ...
        >>> example(1)
        'int case'

    Now we have a specific instance for ``int``
    which does something different from the default implementation.

    What will happen if we pass something new, like ``str``?

    .. code:: python

        >>> example('a')
        'default example'

    Because again, we don't yet have
    an instance of this typeclass for ``str`` type.
    Let's fix that.

    .. code:: python

        >>> @example.instance(str)
        ... def _example_str(instance: str) -> str:
        ...     return instance
        ...
        >>> example('a')
        'a'

    Now it works with ``str`` as well.

    So, the rule is clear:
    if we have a typeclass instance for a specific type,
    then it will be called,
    otherwise the default implementation will be called instead.

    Removing default implementation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    """
    return _TypeClassMethod(default_implementation)
