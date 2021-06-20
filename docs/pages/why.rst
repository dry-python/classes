What and why?
=============

Typeclasses are another
`form of polymorphism <https://en.wikipedia.org/wiki/Ad_hoc_polymorphism>`_
that is widely used in some functional languages.

Let's learn why would you can possibly need it in Python.


Problem definition
------------------

Let's say you want some function to behave differently for different types
(like ``len()`` does for ``str`` and ``dict`` types).

What options do you traditionally have in Python?

isinstance
~~~~~~~~~~

The easiest way to do that is to define
a function with multiple ``isinstance`` cases:

.. code:: python

  >>> from typing import Union

  >>> def my_len(container: Union[str, dict]) -> int:
  ...    if isinstance(container, str):
  ...        return len(container)
  ...    elif isinstance(container, dict):
  ...        return len(container.keys())
  ...    raise TypeError('Type {0} is not supported'.format(type(container)))

  >>> assert my_len('abc') == 3
  >>> assert my_len({}) == 0
  >>> my_len(1)
  Traceback (most recent call last):
    ...
  TypeError: Type <class 'int'> is not supported

It is a great solution if you know all types you need to support in advance.
In our case it is ``Union[str, dict]``.

But, it does not work if you want to have extandable set of supported types.

Classes and methods
~~~~~~~~~~~~~~~~~~~

Traditionally, object oriented languages solve it via classes.

For example, in our case of the custom ``len`` function,
you will have to subclass some ``HasLength``
super type to make ``len`` method available to your type:

.. code:: python

  >>> import abc

  >>> class HasLength(object):
  ...     @abc.abstractmethod
  ...     def len(self) -> int:
  ...         """You have to implement this method to get the length."""

And classes are hard.
They have internal state, inheritance, methods (including static ones),
structure, class-level constants, name conflicts, life-cycle, and etc.

Moreover, it changes the semantics
from a simple function to a full-featured classes and methods.
Which is not always desirable.

That's why Python is not purely built around this idea.
It also has protocols: ``__len__``, ``__iter__``, ``__add__``, etc.
Which are called
`magic methods <https://docs.python.org/3/reference/datamodel.html>`_
most of the time.
This really helps and keeps the language easy.

But, it also has some serious problem:
we cannot add new protocols / magic methods to the existing data types.
For example, we cannot add ``__len__`` to ``int`` even if we need to.
We would have to create our own subtype of ``int``
called ``MyInt`` with ``__len__`` defined.

Of course, adding ``__len__`` to ``int`` type is not really useful,
but, sometimes we really need this with other features!
Like ``to_json`` or ``from_json`` when using serialization.

One more philosophical problem with methods is that sometimes
our "utilitary" methods break our abstractions.
For example, imagine you have a typical domain ``Person`` class:

.. code:: python

  >>> from typing import Sequence

  >>> class Person(object):
  ...     def become_friends(self, friend: 'Person') -> None:
  ...          ...
  ...
  ...     def is_friend_of(self, person: 'Person') -> bool:
  ...          ...
  ...
  ...     def get_pets(self) -> Sequence['Pet']:
  ...          ...

And now, we want to make our ``Person`` JSON serializable.
And our library requires this extra API:

.. code:: diff

  --- class Person(object):
  +++ class Person(JSONSerializable):

  +++ def to_json(self) -> str:
  +++     ...

  +++ def from_json(self, json_str: str) -> 'Person':
  +++     ...

But, now our domain models knows some ugly implementation details.
And it will become even uglier in the future!

Extra abstractions
~~~~~~~~~~~~~~~~~~

Ok, we cannot add new methods to the object itself,
but we can create new extra abstractions. For example:

.. code:: python

  class PersonJSONSerializer(JSONSerializer):
      """This type can serialize to JSON and deserialize `Person` objects."""

This looks ok, doesn't it?
Many popular libraries like
`django-rest-framework <https://www.django-rest-framework.org/api-guide/serializers/>`_
use this approach.

But, once again: we have shifted from a simple single
function to a complex DSL around such a common task.

It is now really hard to pass parameters and context
through all abstraction levels,
it is hard to track what types are supported and which are not.
And it is impossible to express this with types when you need to do so:

.. code:: python

  def serialize_to_json(instance: '???') -> str:
      ...

  serialize_to_json(Person())

And I am not even touching how hard it actually is to do some
non-trivial things with DSLs like this in real life.

singledispatch
~~~~~~~~~~~~~~

One more option, that is not so common, but native, is
`functools.singledispatch <https://docs.python.org/3/library/functools.html#functools.singledispatch>`_.

It is a great way to express our initial idea:
different types behave differently for a single function.
We can rewrite our initial ``my_len`` example like this:

.. code:: python

  >>> from functools import singledispatch

  >>> @singledispatch
  ... def my_len(container) -> int:
  ...    raise TypeError('Type {0} is not supported'.format(type(container)))

  >>> @my_len.register
  ... def _(container: str) -> int:
  ...    return len(container)

  >>> @my_len.register
  ... def _(container: dict) -> int:
  ...    return len(container.keys())

  >>> assert my_len('abc') == 3
  >>> assert my_len({}) == 0
  >>> my_len(1)
  Traceback (most recent call last):
    ...
  TypeError: Type <class 'int'> is not supported

And that's exactly what we are looking for!
But, this still has some problems:

1. Currently, ``mypy`` does not support typechecking ``singledispatch`` cases,
   this is a temporary problem and people are working on this

2. You still cannot express
   "I need any object that supports ``my_len`` function" with a type annotation

For example, ``mypy`` does not check for the same
function signatures and return types in all cases:

.. code:: python

  >>> from functools import singledispatch

  >>> @singledispatch
  ... def example(instance) -> str:
  ...     return 'default'

  >>> @example.register(int)
  ... def _(instance: int, other: int) -> int:
  ...     return instance + other

  >>> @example.register(str)
  ... def _(instance: str) -> bool:
  ...     return bool(instance)

  >>> example(2, 3)
  5
  >>> example('a')
  True

As you can see: you are able to create
instances with different return types and number of parameters.

Good luck working with that!


Typeclasses
-----------

That's why we are creating this library.
It allows to:

1. Have functions that behave differently on different types
2. Express it with types using special :ref:`Supports <supports>` annotation
3. Be sure that your typings are always correct

Now, let's dive into the :ref:`implementation <concept>` details!
