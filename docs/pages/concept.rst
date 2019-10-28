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

# TODO: cover each steps
# TODO: json example for simple types


singledispatch
--------------

One may ask, what is the difference
with `singledispatch <https://docs.python.org/3/library/functools.html#functools.singledispatch>`_
function from the standard library?
