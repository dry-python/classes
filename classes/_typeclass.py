"""
Typeclasses for Python.

.. rubric:: Basic usage

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
It raises a ``NotImplementedError`` when no instances match.
And we don't yet have a special case for ``int``,
that why we fallback to the default implementation.

It works almost like a regular function right now.
Let's do the next step and introduce
the ``int`` instance for our typeclass:

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

"""

from typing import (  # noqa: WPS235
    TYPE_CHECKING,
    Callable,
    Dict,
    Generic,
    Type,
    TypeVar,
    Union,
    overload,
)

from typing_extensions import final

_InstanceType = TypeVar('_InstanceType')
_SignatureType = TypeVar('_SignatureType', bound=Callable)
_AssociatedType = TypeVar('_AssociatedType')
_Fullname = TypeVar('_Fullname', bound=str)  # Literal value

_NewInstanceType = TypeVar('_NewInstanceType', bound=Type)

_StrictAssociatedType = TypeVar('_StrictAssociatedType', bound='AssociatedType')
_TypeClassType = TypeVar('_TypeClassType', bound='_TypeClass')
_ReturnType = TypeVar('_ReturnType')


@overload
def typeclass(
    definition: Type[_AssociatedType],
) -> '_TypeClassDef[_AssociatedType]':
    """Function to created typeclasses with associated types."""


@overload
def typeclass(
    signature: _SignatureType,
    # By default almost all variables are `nothing`,
    # but we enhance them via mypy plugin later:
) -> '_TypeClass[_InstanceType, _SignatureType, _AssociatedType, _Fullname]':
    """Function to define typeclasses with just functions."""


def typeclass(signature):
    """General case function to create typeclasses."""
    if isinstance(signature, type):
        return _TypeClass  # It means, that it has a associated type with it
    return _TypeClass(signature)  # In this case it is a regular function


class AssociatedType(Generic[_InstanceType]):
    """
    Base class for all associated types.

    How to use? Just import and subclass it:

    .. code:: python

      >>> from classes import AssociatedType, typeclass

      >>> class Example(AssociatedType):
      ...     ...

      >>> @typeclass(Example)
      ... def example(instance) -> str:
      ...     ...

    It is special, since it can be used as variadic generic type
    (generic with any amount of type variables),
    thanks to our ``mypy`` plugin:

    .. code:: python

      >>> from typing import TypeVar

      >>> A = TypeVar('A')
      >>> B = TypeVar('B')
      >>> C = TypeVar('C')

      >>> class WithOne(AssociatedType[A]):
      ...    ...

      >>> class WithTwo(AssociatedType[A, B]):
      ...    ...

      >>> class WithThree(AssociatedType[A, B, C]):
      ...    ...

    At the moment of writing,
    https://www.python.org/dev/peps/pep-0646/
    is not accepted and is not supported by ``mypy``.

    Right now it does nothing in runtime, but this can change in the future.
    """

    __slots__ = ()

    if not TYPE_CHECKING:  # noqa: WPS604  # pragma: no cover
        def __class_getitem__(cls, type_params) -> type:
            """
            Not-so-ugly hack to add variadic generic support in runtime.

            What it does?
            It forces class-level type ``__parameters__`` count
            and the passed one during runtime subscruption
            to match during validation.

            Then, we revert everything back.
            """
            if not isinstance(type_params, tuple):
                type_params = (type_params,)  # noqa: WPS434

            old_parameters = cls.__parameters__
            cls.__parameters__ = type_params
            try:  # noqa: WPS501
                return super().__class_getitem__(type_params)
            finally:
                cls.__parameters__ = old_parameters


@final
class Supports(Generic[_StrictAssociatedType]):
    """
    Used to specify that some value is a part of a typeclass.

    For example:

    .. code:: python

      >>> from classes import typeclass, Supports

      >>> class ToJson(object):
      ...     ...

      >>> @typeclass(ToJson)
      ... def to_json(instance) -> str:
      ...     ...

      >>> @to_json.instance(int)
      ... def _to_json_int(instance: int) -> str:
      ...     return str(instance)

      >>> def convert_to_json(instance: Supports[ToJson]) -> str:
      ...     return to_json(instance)

      >>> assert convert_to_json(1) == '1'
      >>> convert_to_json(None)
      Traceback (most recent call last):
        ...
      NotImplementedError: Missing matched typeclass instance for type: NoneType

    You can also annotate values as ``Supports`` if you need to:

    .. code:: python

      >>> my_int: Supports[ToJson] = 1

    But, this will fail in ``mypy``:

    .. code:: python

      my_str: Supports[ToJson] = 'abc'
      # Incompatible types in assignment
      # (expression has type "str", variable has type "Supports[ToJson]")

    .. warning::
      ``Supports`` only works with typeclasses defined with associated types.

    """

    __slots__ = ()


@final
class _TypeClass(
    Generic[_InstanceType, _SignatureType, _AssociatedType, _Fullname],
):
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

    __slots__ = ('_instances', '_protocols')

    def __init__(self, signature: _SignatureType) -> None:
        """
        Protected constructor of the typeclass.

        Use public :func:`~typeclass` constructor instead.

        How does this magic work? It heavily relies on custom ``mypy`` plugin.
        Without it - it is just a nonsense.

        The logic is quite unusual.
        We use "mypy-plugin-time" variables to construct a typeclass.

        What variables we use and why?

        - ``_TypeclassType`` is a type variable that indicates
          what type can be passed into this typeclass.
          This type is updated each time we call ``.instance``,
          because that how we introduce new types to the typeclass

        - ``_ReturnType`` is used to enforce
          the same return type for all cases.
          Only modified once during ``@typeclass`` creation

        - ``_SignatureType`` is used to ensure that all parameters
          for all type cases are the same.
          That's how we enforce consistency in all function signatures.
          The only exception is the first argument: it is polymorfic.

        """
        self._instances: Dict[type, Callable] = {}
        self._protocols: Dict[type, Callable] = {}

    def __call__(
        self,
        instance: Union[  # type: ignore
            _InstanceType,
            Supports[_AssociatedType],
        ],
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

    def supports(
        self,
        instance_type: type,
    ) -> bool:
        """
        Tells whether a typeclass is supported by a given type.

        .. code:: python

          >>> from classes import typeclass

          >>> @typeclass
          ... def example(instance) -> str:
          ...     '''Example typeclass.'''

          >>> @example.instance(int)
          ... def _example_int(instance: int) -> str:
          ...     return 'Example: {0}'.format(instance)

          >>> assert example.supports(int) is True
          >>> assert example.supports(list) is False

        You can go an extra mile and add ``Literal`` types here,
        something like:

        .. code:: python

          @overload
          def supports(
              self, instance_type: Type[_TypeClassType],
          ) -> Literal[True]:
              ...

          @overload
          def supports(
              self, instance_type: type,
          ) -> Literal[False]:
              ...

        This will make the return type even more specific,
        but we are not yet sure about possible errors here.
        """
        return (
            instance_type in self._instances or
            instance_type in self._protocols
        )

    def instance(
        self,
        type_argument: _NewInstanceType,
        *,
        is_protocol: bool = False,
    ) -> '_TypeClassInstanceDef[_NewInstanceType, _TypeClassType]':
        """
        We use this method to store implementation for each specific type.

        The only setting we provide is ``is_protocol`` which is required
        when passing protocols. See our ``mypy`` plugin for that.
        """
        # That's how we check for generics,
        # generics that look like `List[int]` or `set[T]` will fail this check,
        # because they are `_GenericAlias` instance,
        # which raises an exception for `__isinstancecheck__`
        isinstance(object(), type_argument)

        def decorator(implementation):
            container = self._protocols if is_protocol else self._instances
            container[type_argument] = implementation
            return implementation
        return decorator


if TYPE_CHECKING:
    from typing_extensions import Protocol

    class _TypeClassDef(Protocol[_AssociatedType]):
        """
        Callable protocol to help us with typeclass definition.

        This protocol does not exist in real life,
        we just need it because we use it in ``mypy`` plugin.
        That's why we define it under ``if TYPE_CHECKING:``.
        It should not be used directly.

        See ``TypeClassDefReturnType`` for more information.
        """

        def __call__(
            self,
            signature: _SignatureType,
        ) -> _TypeClass[
            _InstanceType,
            _SignatureType,
            _AssociatedType,
            _Fullname,
        ]:
            """It can be called, because in real life it is a function."""

    class _TypeClassInstanceDef(  # type: ignore
        Protocol[_InstanceType, _TypeClassType],
    ):
        """
        Callable protocol to help us with typeclass instance callbacks.

        This protocol does not exist in real life,
        we just need it because we use it in ``mypy`` plugin.
        That's why we define it under ``if TYPE_CHECKING:``.
        It should not be used directly.

        See ``InstanceDefReturnType`` for more information.

        One more important thing here: we fill its type vars inside our plugin,
        so, don't even care about its definition.
        """

        def __call__(self, callback: _SignatureType) -> _SignatureType:
            """It can be called, because in real life it is a function."""
