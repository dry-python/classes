The concept
===========

Typeclasses are another form of polymorphism
that is widely used in some functional languages.

What's the point?

Well, we need to do different logic based on input type.

Like ``len()`` function which
works differently for ``"string"`` and ``[1, 2]``.
Or ``+`` operator that works for numbers like "add"
and for strings it works like "concatenate".

Existing approaches
-------------------

Classes and interfaces
~~~~~~~~~~~~~~~~~~~~~~

Traditionally, object oriented languages solve it via classes.

And classes are hard.
They have internal state, inheritance, methods (including static ones),
strong type, structure, class-level constants, life-cycle, and etc.

Magic methods
~~~~~~~~~~~~~

That's why Python is not purely built around this idea.
It also has protocols: ``__len__``, ``__iter__``, ``__add__``, etc.
Which are called "magic mathods" most of the time.

This really helps and keeps the language easy.
But, have some serious problem:
we cannot add new protocols / magic methods to the existing data types.

You cannot add new methods to the ``list`` type (and that's a good thing!),
you cannot also change how ``__len__`` for example work there.

But, sometimes we really need this!
One of the most simple example is ``json`` serialisation and deserialisation.
Each type should be covered, each one works differently, they can nest.
And moreover, it is 100% fine and expected
to add your own types to this process.

So, how does it work?


Typeclasses
-----------

So, typeclasses help us to build new abstractions near the existing types,
not inside them.

Basically, we will learn how to dispatch
different logic based on predefined set of types.

Steps
~~~~~

To use typeclasses you should understand these steps:

.. mermaid::
  :caption: Typeclass steps.

   graph LR
       F1["Typeclass definition"] --> F2["Instance definition"]
       F2                         --> F2
       F2                         --> F3["Calling"]

Let's walk through this process step by step.
The first on is "Typeclass definition", where we create a new typeclass:

.. code:: python

  >>> from classes import typeclass
  >>> from typing import Union

  >>> @typeclass
  ... def json(instance) -> str:
  ...     """That's definition!"""

When typeclass is defined it only has a name and a signature
that all instances will share.
Let's define some instances:

.. code:: python

  >>> @json.instance(str)
  ... def _json_str(instance: str) -> str:
  ...     return '"{0}"'.format(instance)

  >>> @json.instance(int)
  ... @json.instance(float)
  ... def _json_int_float(instance: Union[float, int]) -> str:
  ...     return str(instance)

  >>> @json.instance(None)
  ... def _json_none(instance: None) -> str:
  ...     return 'null'

That's how we define instances for our typeclass.
These instances will be executed when the corresponding type will be supplied.

And the last step is to call our typeclass
with different value of different types:

.. code:: python

  >>> assert json('text') == '"text"'
  >>> assert json(1) == '1'
  >>> assert json(1.5) == '1.5'
  >>> assert json(None) == 'null'

That's it. There's nothing extra about typeclasses. They can be:

- defined
- extended by new instances
- and called

supports method
~~~~~~~~~~~~~~~

You can check if a typeclass is supported via ``.supports()`` method.
Example:

.. code:: python

  >>> assert json.supports(1) is True
  >>> assert json.supports({}) is False

Typeclasses with associated types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also define typeclasses with associated types.
It will allow you to use ``Supports`` type later on.

The syntax looks like this:

.. code:: python

  >>> from classes import AssociatedType, typeclass

  >>> class CanBeTrimmed(AssociatedType):  # Associated type definition
  ...     ...

  >>> @typeclass(CanBeTrimmed)
  ... def can_be_trimmed(instance, length: int) -> str:
  ...    ...

The instance definition syntax is the same:

.. code:: python

   >>> @can_be_trimmed.instance(str)
   ... def _can_be_trimmed_str(instance: str, length: int) -> str:
   ...     return instance[:length]

   >>> assert can_be_trimmed('abcde', 3) == 'abc'

Defining typeclasses as Python classes
will be the only option if you need to use ``Supports`` type.


Supports
--------

We also have a special type to help you specifying
that you want to work with only types that are a part of a specific typeclass.

For example, you might want to work with only types
that are able to be converted to JSON:

.. code:: python

    >>> from classes import AssociatedType, Supports, typeclass

    >>> class ToJson(AssociatedType):
    ...     ...

    >>> @typeclass(ToJson)
    ... def to_json(instance) -> str:
    ...    ...

    >>> @to_json.instance(int)
    ... def _to_json_int(instance: int) -> str:
    ...     return str(instance)

    >>> @to_json.instance(str)
    ... def _to_json_str(instance: str) -> str:
    ...     return '"{0}"'.format(instance)

    >>> def convert_to_json(
    ...     instance: Supports[ToJson],
    ... ) -> str:
    ...     return to_json(instance)

    >>> assert convert_to_json(1) == '1'
    >>> assert convert_to_json('a') == '"a"'

And this will fail (both in runtime and during type checking):

    >>> # This will produce a mypy issue:
    >>> # error: Argument 1 to "convert_to_json" has incompatible type "None";
    >>> # expected "Supports[ToJson]"

    >>> convert_to_json(None)
    Traceback (most recent call last):
      ...
    NotImplementedError: Missing matched typeclass instance for type: NoneType

You can also use ``Supports`` as a type annotation for defining typeclasses:

.. code:: python

    >>> class MyFeature(AssociatedType):
    ...     ...

    >>> @typeclass(MyFeature)
    ... def my_feature(instance: 'Supports[MyFeature]') -> str:
    ...     ...

It might be helpful, when you have ``no-untyped-def`` rule enabled.

One more tip: our team would recommend this style:

.. code:: python

    >>> from typing_extensions import Protocol, final

    >>> @final  # This type cannot have sub-types
    ... class MyTypeclass(AssociatedType):
    ...     """Tell us, what this typeclass is about."""

.. warning::
  ``Supports`` only works with typeclasses defined with associated types.


Related concepts
----------------

singledispatch
~~~~~~~~~~~~~~

One may ask, what is the difference
with `singledispatch <https://docs.python.org/3/library/functools.html#functools.singledispatch>`_
function from the standard library?

The thing about ``singledispatch`` is that it allows almost the same features.
But, it lacks type-safety.
For example, it does not check for the same
function signatures and return types in all cases:

.. code:: python

  >>> from functools import singledispatch

  >>> @singledispatch
  ... def example(instance) -> str:
  ...     return 'default'

  >>> @example.register(int)
  ... def _example_int(instance: int, other: int) -> int:
  ...     return instance + other

  >>> @example.register(str)
  ... def _example_str(instance: str) -> bool:
  ...     return bool(instance)

  >>> assert bool(example(1, 0)) == example('a')

As you can see: you are able to create
instances with different return types and number of parameters.

Good luck working with that!


Further reading
---------------

- `Wikipedia <https://en.wikipedia.org/wiki/Type_class>`_
- `Typeclasses in Haskell <http://learnyouahaskell.com/types-and-typeclasses>`_
- `Typeclasses in Swift <https://bow-swift.io/docs/fp-concepts/type-classes/>`_
