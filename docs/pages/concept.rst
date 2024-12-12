.. _concept:

Concept
=======


Typeclass
---------

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
The first one is "Typeclass definition", where we create a new typeclass:

.. code:: python

  >>> from classes import typeclass
  >>> from typing import Union

  >>> @typeclass
  ... def to_json(instance) -> str:
  ...     """That's a definition!"""

When typeclass is defined it only has a name and a signature
that all instances will share.
Let's define some instances:

.. code:: python

  >>> @to_json.instance(str)
  ... def _to_json_str(instance: str) -> str:
  ...     return '"{0}"'.format(instance)

  >>> @to_json.instance(int)
  ... @to_json.instance(float)
  ... def _to_json_int_float(instance: Union[float, int]) -> str:
  ...     return str(instance)

  >>> @to_json.instance(None)
  ... def _to_json_none(instance: None) -> str:
  ...     return 'null'

That's how we define instances for our typeclass.
These instances will be executed when the corresponding type will be supplied.

And the last step is to call our typeclass
with different value of different types:

.. code:: python

  >>> assert to_json('text') == '"text"'
  >>> assert to_json(1) == '1'
  >>> assert to_json(1.5) == '1.5'
  >>> assert to_json(None) == 'null'

That's it. There's nothing extra about typeclasses. They can be:

- defined
- extended by new instances
- and called


Protocols
---------

We also support ``Protocol`` items to be registered,
the only difference is that they do require ``protocol=`` named argument
to be specified on ``.instance()`` call:

.. code:: python

  >>> from typing import Sequence

  >>> @to_json.instance(protocol=Sequence)
  ... def _to_json_sequence(instance: Sequence) -> str:
  ...     return '[{0}]'.format(', '.join(to_json(i) for i in instance))

  >>> assert to_json([1, 'a', None]) == '[1, "a", null]'


Delegates
---------

Let's say that you want to handle types like ``Sequence[int]`` with ``classes``.
The simple approach won't work, because Python cannot tell
that some object is ``Sequence[int]`` or ``Sequence[str]``:

.. code:: python

  >>> from typing import Sequence

  >>> isinstance([1, 2, 3], Sequence[int])
  Traceback (most recent call last):
    ...
  TypeError: Subscripted generics cannot be used with class and instance checks

``__instancecheck__`` magic method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We need some custom type inference mechanism.
For this purpose we use
`__instancecheck__ <https://docs.python.org/3/reference/datamodel.html#class.__instancecheck>`_
magic method:

.. code:: python

  >>> from typing import List

  >>> class _SequenceOfIntMeta(type):
  ...     def __instancecheck__(self, arg) -> bool:
  ...         try:
  ...             return (
  ...                 # We need to have at least one `int` element
  ...                 bool(arg) and
  ...                 all(isinstance(item, int) for item in arg)
  ...             )
  ...         except TypeError:
  ...             return False

  >>> class SequenceOfInt(List[int], metaclass=_SequenceOfIntMeta):
  ...     ...

Now we can be sure that our ``List[int]`` can be checked in runtime:

.. code:: python

  >>> assert isinstance([1, 2, 3], SequenceOfInt) is True
  >>> assert isinstance([1, 'a'], SequenceOfInt) is False
  >>> assert isinstance([], SequenceOfInt) is False  # empty

``delegate`` argument
~~~~~~~~~~~~~~~~~~~~~

And now we can use it with ``classes``:

.. code:: python

  >>> from classes import typeclass
  >>> from typing import Sequence

  >>> @typeclass
  ... def sum_all(instance) -> int:
  ...     ...

  >>> @sum_all.instance(delegate=SequenceOfInt)
  ... def _sum_all_list_int(instance: Sequence[int]) -> int:
  ...     return sum(instance)

  >>> your_list = [1, 2, 3]
  >>> assert sum_all(your_list) == 6

What happens here? When defining an instance with ``delegate`` argument,
what we really do is: we add our ``delegate``
into a special registry inside ``sum_all`` typeclass.

This registry is using ``isinstance`` function
to find handler that fits the defined predicate.
It has the highest priority among other dispatch methods.

This allows us to sync both runtime and ``mypy`` behavior:

.. code:: python

  >>> # Mypy will raise a type error:
  >>> # Argument 1 to "sum_all" has incompatible type "List[str]"; expected "List[int]"

  >>> sum_all(['a', 'b'])
  Traceback (most recent call last):
    ...
  NotImplementedError: Missing matched typeclass instance for type: list

Phantom types
~~~~~~~~~~~~~

Notice, that ``SequenceOfInt`` is very verbose,
it even has an explicit metaclass!

There's a better way, you need to define a "phantom" type
(it is called "phantom" because it does not exist in runtime):

.. code:: python

  >>> from phantom import Phantom
  >>> from phantom.predicates import boolean, collection, generic, numeric

  >>> class SequenceOfInt(
  ...     Sequence[int],
  ...     Phantom,
  ...     predicate=boolean.both(
  ...         collection.count(numeric.greater(0)),
  ...         collection.every(generic.of_type(int)),
  ...     ),
  ... ):
  ...     ...

  >>> assert isinstance([1, 2, 3], SequenceOfInt)
  >>> assert type([1, 2, 3]) is list

Short, easy, and readable:

- By defining ``predicate`` we ensure
  that all non-empty lists with ``int`` elements
  will be treated as ``SequenceOfInt``
- In runtime ``SequenceOfInt`` does not exist, because it is phantom!
  In reality it is just ``Sequence[int]``.

.. note::
  Notice that newer versions of ``phantom-types`` do not accept the mutable
  ``List`` type constructor for this purpose because you can add items of other
  types to the list after the validation is done, which makes it unsafe.
  Use immutable types like ``Sequence``.

Now, we can define our typeclass with ``phantom`` type support:

.. code:: python

  >>> from phantom import Phantom
  >>> from phantom.predicates import boolean, collection, generic, numeric

  >>> class SequenceOfInt(
  ...    Sequence[int],
  ...    Phantom,
  ...    predicate=boolean.both(
  ...       collection.count(numeric.greater(0)),
  ...       collection.every(generic.of_type(int)),
  ...    ),
  ... ):
  ...     ...

  >>> from classes import typeclass

  >>> @typeclass
  ... def sum_all(instance) -> int:
  ...     ...

  >>> @sum_all.instance(delegate=SequenceOfInt)
  ... def _sum_all_list_int(instance: Sequence[int]) -> int:
  ...     return sum(instance)

  >>> assert sum_all([1, 2, 3]) == 6

That's why we need a ``delegate=`` argument here:
we don't really work with ``Sequence[int]``,
we delegate all the runtime type checking to ``SequenceOfInt`` phantom type.

Performance considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

Types that are matched via ``__instancecheck__`` are the first one we try.
Traversing the whole list to check that all elements
are of the given type can be really slow.
The worst case complexity of this is ``O(n)``
where ``n`` is the number of types to try.
We also always try them first and do not cache the result.

You might need a different algorithm.
Take a look at `beartype <https://github.com/beartype/beartype>`_.
It promises runtime type checking with ``O(1)`` non-amortized worst-case time
with negligible constant factors.

Take a look at their docs to learn more.

We recommend to think at least
twice about the performance side of this feature.
Maybe you can just write a function?


Type resolution order
---------------------

Here's how typeclass resolve types:

1. At first we try to resolve types via delegates and ``isinstance`` check
2. We try to resolve exact match by a passed type
3. Then we try to match passed type with ``isinstance``
   against protocol types,
   first match wins
4. Then we traverse ``mro`` entries of a given type,
   looking for ones we can handle,
   first match wins

We use cache for all parts of algorithm except the first step
(it is never cached),
so calling typeclasses with same object types is fast.

In other words, it can fallback to more common types:

.. code:: python

  >>> from classes import typeclass

  >>> @typeclass
  ... def example(instance) -> str:
  ...     ...

  >>> class A(object):
  ...     ...

  >>> class B(A):
  ...     ...

  >>> @example.instance(A)
  ... def _example_a(instance: A) -> str:
  ...     return 'a'

Now, let's test that the fallback to more common types work:

  >>> assert example(A()) == 'a'
  >>> assert example(B()) == 'a'

And now, let's specify a special case for ``B``:

.. code:: python

  >>> @example.instance(B)
  ... def _example_b(instance: B) -> str:
  ...     return 'b'

  >>> assert example(A()) == 'a'
  >>> assert example(B()) == 'b'

How it fallback works?
We traverse the ``mro`` of a given type and find the closest supported type.
This helps us to still treat first typeclass argument as covariant.

There's even a pattern to allow all objects in:

.. code:: python

  >>> @example.instance(object)
  ... def _example_all_in(instance: object) -> str:
  ...     return 'obj'

  >>> assert example(A()) == 'a'
  >>> assert example(B()) == 'b'

  >>> assert example(1) == 'obj'
  >>> assert example(None) == 'obj'
  >>> assert example('a') == 'obj'


Overriding and extending existing instances
-------------------------------------------

Sometimes we really need to override how things work.
With objects and classes this can be problematic,
because we would need to define a new subclass
and chances are that it won't be used in some situations.

With ``@typeclass`` overriding something is as easy.
Let's define a typeclass with an instance to be overridden later:

.. code:: python

  >>> from classes import typeclass

  >>> @typeclass
  ... def example(instance) -> str:
  ...    ...

  >>> @example.instance(str)
  ... def _example_str(instance: str) -> str:
  ...      return instance.lower()

  >>> assert example('Hello') == 'hello'

Now, let's change how ``example`` behaves for ``str``.
The only thing we need to do is to define ``.instance(str)`` once again:

.. code:: python

  >>> @example.instance(str)
  ... def _example_str_new(instance: str) -> str:
  ...      return instance.upper()

  >>> assert example('Hello') == 'HELLO'

Note, that we can reuse the original implementation
by calling the instance case directly:

.. code:: python

  >>> @example.instance(str)
  ... def _example_str_new(instance: str) -> str:
  ...      return _example_str(instance) + '!'

  >>> assert example('Hello') == 'hello!'


supports typeguard
------------------

You can check if a typeclass is supported via ``.supports()`` method.
Example:

.. code:: python

  >>> from classes import typeclass

  >>> @typeclass
  ... def convert_to_number(instance) -> int:
  ...     ...

  >>> @convert_to_number.instance(int)
  ... def _convert_int(instance: int) -> int:
  ...     return instance

  >>> @convert_to_number.instance(float)
  ... def _convert_float(instance: float) -> int:
  ...     return int(instance)

  >>> assert convert_to_number.supports(1) is True
  >>> assert convert_to_number.supports(1.5) is True
  >>> assert convert_to_number.supports({}) is False

It uses the same runtime dispatching mechanism as calling a typeclass directly,
but returns a boolean.

It also uses `TypeGuard <https://www.python.org/dev/peps/pep-0647/>`_ type
to narrow types inside ``if convert_to_number.supports(item)`` blocks:

.. code:: python

  >>> from typing import Union
  >>> from random import randint

  >>> def get_random_item() -> Union[int, dict]:
  ...    return {'example': 1} if randint(0, 1) else 1

  >>> item: Union[int, dict] = get_random_item()

So, if you try to call ``convert_to_number(item)`` right now,
it won't pass ``mypy`` typecheck and will possibly throw runtime exception,
because ``dict`` is not supported by ``convert_to_number`` typeclass.

So, you can narrow the type with our ``TypeGuard``:

  >>> if convert_to_number.supports(item):
  ...    # `reveal_type(item)` will produce `Union[int, float]`,
  ...    # or basically all the types that are supported by `to_json`,
  ...    # now you can safely call `to_json`, `mypy` will be happy:
  ...    assert convert_to_number(1.5) == 1


Typeclasses with associated types
---------------------------------

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
will be the only option if you need to use :ref:`Supports <supports>` type.


.. _type-restrictions:

Type restrictions
-----------------

You can restrict typeclasses
to have only subtypes of some specific types during typechecking
(we will still accept all types in runtime).

.. code:: python

  >>> from classes import typeclass

  >>> class A(object):
  ...     ...

  >>> class B(A):
  ...     ...

  >>> @typeclass
  ... def example(instance: A) -> str:
  ...     ...

With this setup, this will typecheck:

.. code:: python

  >>> @example.instance(A)
  ... def _example_a(instance: A) -> str:
  ...     return 'a'

  >>> @example.instance(B)
  ... def _example_b(instance: B) -> str:
  ...     return 'b'

  >>> assert example(A()) == 'a'
  >>> assert example(B()) == 'b'

But, this won't typecheck:

.. code:: python

  >>> @example.instance(int)
  ... def _example_int(instance: int) -> str:
  ...    return 'int'

  # error: Instance "builtins.int" does not match original type "ex.A"


Further reading
---------------

- `Wikipedia <https://en.wikipedia.org/wiki/Type_class>`_
- `Typeclasses in Haskell <http://learnyouahaskell.com/types-and-typeclasses>`_
- `Typeclasses in Swift <https://bow-swift.io/docs/fp-concepts/type-classes/>`_
