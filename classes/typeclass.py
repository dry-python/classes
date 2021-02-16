from typing import Callable, Dict, Generic, NoReturn, Type, TypeVar, overload

from typing_extensions import Literal

_TypeClassType = TypeVar('_TypeClassType')
_ReturnType = TypeVar('_ReturnType')
_CallbackType = TypeVar('_CallbackType', bound=Callable)
_InstanceType = TypeVar('_InstanceType')


class _TypeClass(Generic[_TypeClassType, _ReturnType, _CallbackType]):
    """
    That's how we represent typeclasses.

    You should also use this type to annotate places
    where you expect some specific typeclass to be used.

    .. code:: python

        >>> from typing import Callable
        >>> from classes import typeclass
        >>> @typeclass
        ... def used(instance, other: int) -> int:
        ...     '''Example typeclass to be used later.'''

        >>> @used.instance(int)
        ... def _used_int(instance: int, other: int) -> int:
        ...     return instance + other

        >>> def accepts_typeclass(
        ...     callback: Callable[[int, int], int],
        ... ) -> int:
        ...     return callback(1, 3)

        >>> assert accepts_typeclass(used) == 4

    Take a note, that we structural subtyping here.
    And all typeclasses that match ``Callable[[int, int], int]`` signature
    will typecheck.

    """

    def __init__(self, signature: _CallbackType) -> None:
        """
        Protected constuctor of the typeclass.

        Use public :func:`~typeclass` constructor instead.

        How does this magic work? It heavily relies on custom ``mypy`` plugin.
        Without it - it is just a nonsence.

        The logic is quite unsual.
        We use "mypy-plugin-time" variables to construct a typeclass.

        What variables we use and why?

        - ``_TypeclassType`` is a type variable that indicates
          what type can be passed into this typeclass.
          This type is updated each time we call ``.instance``,
          because that how we introduce new types to the typeclass

        - ``_ReturnType`` is used to enforce
          the same return type for all cases.
          Only modified once during ``@typeclass`` creation

        - ``_CallbackType`` is used to ensude that all parameters
          for all type cases are the same.
          That's how we enforce consistency in all function signatures.
          The only exception is the first argument: it is polymorfic.

        """
        self._signature = signature
        self._instances: Dict[type, Callable] = {}
        self._protocols: Dict[type, Callable] = {}

    def __call__(
        self,
        instance: _TypeClassType,
        *args,
        **kwargs,
    ) -> _ReturnType:
        """
        We use this method to actually call a typeclass.

        The resolution order is the following:

        1. Exact types that are passed as ``.instance`` arguments
        2. Protocols that are passed with ``is_protocol=True``

        We don't guarantee the order of types inside groups.
        Use correct types, do not rely on our order.

        .. rubric:: Callbacks

        Since, we define ``__call__`` method for this class,
        it can be used and typechecked everywhere,
        where a regular ``Callable`` is expected.

        """
        instance_type = type(instance)
        implementation = self._instances.get(instance_type, None)
        if implementation is not None:
            return implementation(instance, *args, **kwargs)

        for protocol, callback in self._protocols.items():
            if isinstance(instance, protocol):
                return callback(instance, *args, **kwargs)

        raise NotImplementedError(
            'Missing matched typeclass instance for type: {0}'.format(
                instance_type.__qualname__,
            ),
        )

    @overload
    def instance(
        self,
        type_argument: Type[_InstanceType],
        *,
        is_protocol: Literal[False] = ...,
    ) -> Callable[
        [Callable[[_InstanceType], _ReturnType]],
        NoReturn,  # We need this type to disallow direct instance calls
    ]:
        """Case for regular typeclasses."""

    @overload
    def instance(
        self,
        type_argument,
        *,
        is_protocol: Literal[True],
    ) -> Callable[
        [Callable[[_InstanceType], _ReturnType]],
        NoReturn,  # We need this type to disallow direct instance calls
    ]:
        """Case for protocol based typeclasses."""

    def instance(
        self,
        type_argument,
        *,
        is_protocol: bool = False,
    ):
        """
        We use this method to store implementation for each specific type.

        The only setting we provide is ``is_protocol`` which is required
        when passing protocols.
        That's why we also have this ugly ``@overload`` cases.
        Otherwise, ``Protocol`` instances
        would not match ``Type[_InstanceType]`` type due to ``mypy`` rules.

        """
        isinstance(object(), type_argument)  # That's how we check for generics

        def decorator(implementation):
            container = self._protocols if is_protocol else self._instances
            container[type_argument] = implementation
            return implementation
        return decorator


def typeclass(
    signature: _CallbackType,
    # By default `_TypeClassType` and `_ReturnType` are `nothing`,
    # but we enhance them via mypy plugin later:
) -> _TypeClass[_TypeClassType, _ReturnType, _CallbackType]:
    """
    Function to define typeclasses.

    Basic usage
    ~~~~~~~~~~~

    The first and the simplest example of a typeclass is just its definition:

    .. code:: python

        >>> from classes import typeclass
        >>> @typeclass
        ... def example(instance) -> str:
        ...     '''Example typeclass.'''

        >>> example(1)
        Traceback (most recent call last):
        ...
        NotImplementedError: Missing matched typeclass instance for type: int

    In this example we work with the default implementation of a typeclass.
    It raise a ``NotImplementedError`` when no instances match.
    And we don't yet have a special case for ``int``,
    that why we fallback to the default implementation.

    It works like a regular function right now.
    Let's do the next step and introduce
    the ``int`` instance for the typeclass:

    .. code:: python

        >>> @example.instance(int)
        ... def _example_int(instance: int) -> str:
        ...     return 'int case'

        >>> assert example(1) == 'int case'

    Now we have a specific instance for ``int``
    which does something different from the default implementation.

    What will happen if we pass something new, like ``str``?

    .. code:: python

        >>> example('a')
        Traceback (most recent call last):
        ...
        NotImplementedError: Missing matched typeclass instance for type: str

    Because again, we don't yet have
    an instance of this typeclass for ``str`` type.
    Let's fix that.

    .. code:: python

        >>> @example.instance(str)
        ... def _example_str(instance: str) -> str:
        ...     return instance

        >>> assert example('a') == 'a'

    Now it works with ``str`` as well. But differently.
    This allows developer to base the implementation on type information.

    So, the rule is clear:
    if we have a typeclass instance for a specific type,
    then it will be called,
    otherwise the default implementation will be called instead.

    .. rubric:: Generics

    We also support generic, but the support is limited.
    We cannot rely on type parameters of the generic type,
    only on the base generic class:

    .. code:: python

        >>> from typing import Generic, TypeVar
        >>> T = TypeVar('T')
        >>> class MyGeneric(Generic[T]):
        ...     def __init__(self, arg: T) -> None:
        ...          self.arg = arg

    Now, let's define the typeclass instance for this type:

    .. code:: python

        >>> @example.instance(MyGeneric)
        ... def _my_generic_example(instance: MyGeneric) -> str:
        ...     return 'generi' + str(instance.arg)

        >>> assert example(MyGeneric('c')) == 'generic'

    This case will work for all type parameters of ``MyGeneric``,
    or in other words it can be assumed as ``MyGeneric[Any]``:

    .. code:: python

        >>> assert example(MyGeneric(1)) == 'generi1'

    In the future, when Python will have new type mechanisms,
    we would like to improve our support for specific generic instances
    like ``MyGeneric[int]`` only. But, that's the best we can do for now.

    .. rubric:: Protocols

    We also support protocols. It has the same limitation as ``Generic`` types.
    It is also dispatched after all regular instances are checked.

    To work with protocols, one needs to pass ``is_protocol`` flag to instance:

    .. code:: python

        >>> from typing import Sequence
        >>> @example.instance(Sequence, is_protocol=True)
        ... def _sequence_example(instance: Sequence) -> str:
        ...     return ','.join(str(item) for item in instance)

        >>> assert example([1, 2, 3]) == '1,2,3'

    But, ``str`` will still have higher priority over ``Sequence``:

    .. code:: python

        >>> assert example('abc') == 'abc'

    We also support user-defined protocols:

    .. code:: python

        >>> from typing_extensions import Protocol
        >>> class CustomProtocol(Protocol):
        ...     field: str

        >>> @example.instance(CustomProtocol, is_protocol=True)
        ... def _custom_protocol_example(instance: CustomProtocol) -> str:
        ...     return instance.field

    Now, let's build a class that match this protocol and test it:

    .. code:: python

        >>> class WithField(object):
        ...    field: str = 'with field'

        >>> assert example(WithField()) == 'with field'

    Remember, that generic protocols have the same limitation as generic types.

    """
    return _TypeClass(signature)
