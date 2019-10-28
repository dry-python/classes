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
  ...
  >>> @example.instance(str)
  ... def _example_str(instance: str, arg: int, *, keyword: str) -> bool:
  ...     return instance * arg + keyword
  ...

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
