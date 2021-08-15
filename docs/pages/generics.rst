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
  ... def copy(instance: X) -> X:
  ...     ...

This one will typecheck correctly:

.. code:: python

  >>> @copy.instance(int)
  ... def _copy_int(instance: int) -> int:
  ...     ...

But, this won't:

.. code:: python

  @copy.instance(str)
  def _copy_str(instance: str) -> bool:
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


Complex concrete generics
-------------------------

There are several advanced techniques
in using concrete generic types when working with ``delegate`` types.

Here's the collection of them.

TypedDicts
~~~~~~~~~~

At first, we need to define a typed dictionary itself:

.. code:: python

  >>> from typing_extensions import TypedDict
  >>> from classes import typeclass

  >>> class _User(TypedDict):
  ...     name: str
  ...     registered: bool

Then, we need a special class with ``__instancecheck__`` defined.
Because original ``TypedDict`` just raises
a ``TypeError`` on ``isinstance(obj, User)``.

.. code:: python

  >>> import sys

  >>> class _UserDictMeta(type):
  ...     def __instancecheck__(cls, arg: object) -> bool:
  ...        return (
  ...             isinstance(arg, dict) and
  ...             isinstance(arg.get('name'), str) and
  ...             isinstance(arg.get('registered'), bool)
  ...         )

  >>> # Without this we would have a metaclass conflict on older versions:
  >>> if sys.version_info[:2] < (3, 9):
  ...     _UserMeta = type('UserMeta', (_UserDictMeta, type(TypedDict)), {})
  ... else:
  ...     from typing import _TypedDictMeta
  ...     _UserMeta = type('UserMeta', (_UserDictMeta, _TypedDictMeta), {})

  >>> class UserDict(_User, metaclass=_UserMeta):
  ...     ...

And finally we can use it!
Take a note that we always use the resulting ``UserDict`` type,
not the base ``_User``.

.. code:: python

  >>> @typeclass
  ... def get_name(instance) -> str:
  ...     ...

  >>> @get_name.instance(delegate=UserDict)
  ... def _get_name_user_dict(instance: UserDict) -> str:
  ...     return instance['name']

  >>> user: UserDict = {'name': 'sobolevn', 'registered': True}
  >>> assert get_name(user) == 'sobolevn'
