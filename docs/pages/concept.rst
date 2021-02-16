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


Steps
-----

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
  ... def _json_int_float(instance) -> str:
  ...     return str(instance)

That's how we define instances for our typeclass.
These instances will be executed when the corresponding type will be supplied.

And the last step is to call our typeclass
with different value of different types:

.. code:: python

  >>> assert json('text') == 'text'
  >>> assert json(1) == '1'
  >>> assert json(1.5) == '1.5'

That's it. There's nothing extra about typeclasses. They can be:

- defined
- extended by new instances
- and called


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
