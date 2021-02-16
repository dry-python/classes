.. _typesafety:

Type-safety
===========

We try to bring as much type safety as possible.

However, there are some limitations.
This section will guide you through both
features and troubles of type-safe typeclasses in Python.


Features
--------

First of all, we always check that the signature is the same for all cases.

.. code:: python

  >>> from classes import typeclass
  >>> @typeclass
  ... def example(instance, arg: int, *, keyword: str) -> bool:
  ...     ...

  >>> @example.instance(str)
  ... def _example_str(instance: str, arg: int, *, keyword: str) -> bool:
  ...     return instance * arg + keyword

Let's look at this example closely:

1. We create a typeclass with the signature that all cases must share:
   except for the ``instance`` parameter, which is polymorphic.
2. We check that return type of all cases match the original one:
   ``bool`` in our particular case
3. We check that ``instance`` has the correct type in ``_example_str``

When calling typeclasses, we also do the type check:

.. code:: python

  >>> example('a', 3, keyword='b')
  'aaab'

Here are features that we support:

1. Typechecker knows that we allow only defined instances
   to be the first (or instance) parameter in a call.
2. We also check that other parameters do exist in the original signature
3. We check the return type: it matches that defined one in the signature


Limitations
-----------

We are limited in generics support.
We support them, but without type parameters.

- We support: ``list``, ``List``, ``Dict``,
  ``Mapping``, ``Iterable``, ``MyCustomGeneric``
- We don't support ``List[int]``, ``Dict[str, str]``, ``Iterable[Any]``, etc

Why? Because we cannot tell the difference
between ``List[int]`` and ``List[str]`` in runtime.

Python just does not have this information. It requires types to be infered.
And that's currently not possible.

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


But, this will (note that we use ``list`` inside ``.instance()`` call):

.. code:: python

  >>> from typing import List
  >>> from classes import typeclass
  >>> @typeclass
  ... def generic_typeclass(instance) -> str:
  ...     """We use this example to demonstrate the typing limitation."""

  >>> @generic_typeclass.instance(list)
  ... def _generic_typeclass_list_int(instance: List):
  ...   return ''.join(str(list_item) for list_item in instance)

  >>> assert generic_typeclass([1, 2, 3]) == '123'
  >>> assert generic_typeclass(['a', 1, True]) == 'a1True'

Use primitive generics as they always have ``Any`` inside.
Annotations should also be bound to any parameters.
Do not supply any other values there, we cannot even check for it.
