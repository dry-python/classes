Generics
========


Generic typeclasses
-------------------

You can define generic typeclasses, just like regular generic functions.
You have to ways of doing this:

- Via raw type variables like in ``def copy(instance: X) -> X``
- Via instances with type variables like
  in ``get_zero_item(instance: Sequence[X]) -> X``

Using typevars
~~~~~~~~~~~~~~

When defining typeclasses with generic instances,
we will typecheck that all instance definitions
match the shape of the typeclass itself:

.. code:: python

  >>> from typing import TypeVar
  >>> from classes import typeclass

  >>> X = TypeVar('X')

  >>> @typeclass
  ... def is_equal(first: X, second: X) -> bool:
  ...     ...

This one will typecheck correctly:

.. code:: python

  >>> @is_equal.instance(int)
  ... def _is_equal_int(first: int, second: int) -> bool:
  ...     ...

But, this won't:

.. code:: python

  @is_equal.instance(str)
  def _is_equal_str(first: str, second: float) -> bool:
      ...

  # error: Instance callback is incompatible "def (first: builtins.str, second: builtins.float) -> builtins.bool"; expected "def (first: builtins.str, second: builtins.str*) -> builtins.bool"

Using instances
~~~~~~~~~~~~~~~

When using instances,
you can define :ref:`type restrictions <type-restrictions>`
to limit typeclass instances to only subtypes of a given restriction.

Here's an example definition:

.. code:: python

  >>> from typing import Iterable, TypeVar, List
  >>> from classes import typeclass

  >>> X = TypeVar('X')

  >>> @typeclass
  ... def get_item(instance: Iterable[X], index: int) -> X:
  ...    ...

This instance will match the definition:

.. code:: python

  >>> @get_item.instance(list)
  ... def _get_item_list(instance: List[X], index: int) -> X:
  ...     ...

  reveal_type(get_item([1, 2, 3], 0))  # Revealed type is "builtins.int*"
  reveal_type(get_item(['a', 'b'], 0)) # Revealed type is "builtins.str*"

But, this won't match and ``mypy`` will warn you:

.. code:: python

  @get_item.instance(int)
  def _get_item_int(instance: int, index: int) -> int:
      ...
  # error: Instance callback is incompatible "def (instance: builtins.int, index: builtins.int) -> builtins.int"; expected "def [X] (instance: builtins.int, index: builtins.int) -> X`-1"
  # error: Instance "builtins.int" does not match original type "typing.Iterable[X`-1]"


Generic Supports type
---------------------

You can also use generic ``Supports`` type with generic ``AssociatedType``.

To do so, you will need:
1. Declare ``AssociatedType`` with type arguments, just like regular ``Generic``
2. Use correct type arguments to define a variable

Let's get back to ``get_item`` example and use a generic ``Supports`` type:

.. code:: python

  >>> from typing import Iterable, List, TypeVar
  >>> from classes import AssociatedType, Supports, typeclass

  >>> X = TypeVar('X')

  >>> class GetItem(AssociatedType[X]):
  ...     ...

  >>> @typeclass(GetItem)
  ... def get_item(instance: Iterable[X], index: int) -> X:
  ...     ...

  >>> numbers: Supports[GetItem[int]]
  >>> strings: Supports[GetItem[str]]

  reveal_type(get_item(numbers, 0))  # Revealed type is "builtins.int*"
  reveal_type(get_item(strings, 0))  # Revealed type is "builtins.str*"


Limitations
-----------

We are limited in generics support.
We support them, but without concrete type parameters.

- We support: ``X``, ``list``, ``List``, ``Dict``,
  ``Mapping``, ``Iterable``, ``MyCustomGeneric``
- We also support: ``Iterable[Any]``, ``List[X]``, ``Dict[X, Y]``, etc
- We don't support ``List[int]``, ``Dict[str, str]``, etc

Why? Because we cannot tell the difference
between ``List[int]`` and ``List[str]`` in runtime.

Python just does not have this information.
It requires types to be inferred by some other tool.
And that's currently not supported.

So, this would not work:

.. code:: python

  >>> from typing import List
  >>> from classes import typeclass

  >>> @typeclass
  ... def generic_typeclass(instance) -> str:
  ...     """We use this example to demonstrate the typing limitation."""

  >>> @generic_typeclass.instance(List[int])
  ... def _generic_typeclass_list_int(instance: List[int]):
  ...   ...
  ...
  Traceback (most recent call last):
  ...
  TypeError: ...
