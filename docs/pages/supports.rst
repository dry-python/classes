.. _supports:

Supports
========

We also have a special type to help you specifying
that you want to work with only types that are a part of a specific typeclass.

.. warning::
  ``Supports`` only works with typeclasses defined with associated types.


Regular types
-------------

For example, you might want to work with only types
that are able to be converted to JSON.

You need to do several extra things:
1. Define unique "associated type" for this typeclass
2. Pass it during the typeclass definition

.. code:: python

    >>> from classes import AssociatedType, Supports, typeclass

    >>> class ToJson(AssociatedType):  # defining associated type
    ...     ...

    >>> @typeclass(ToJson)  # passing it to the typeclass
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


Supports for instance annotations
---------------------------------

You can also use ``Supports`` as a type annotation for defining typeclasses:

.. code:: python

    >>> class MyFeature(AssociatedType):
    ...     ...

    >>> @typeclass(MyFeature)
    ... def my_feature(instance: 'Supports[MyFeature]') -> str:
    ...     ...

It might be helpful, when you have ``no-untyped-def`` rule enabled.

One more tip, our team would recommend this style:

.. code:: python

    >>> from typing_extensions import final

    >>> @final  # This type cannot have sub-types
    ... class MyFeature(AssociatedType):
    ...     """Tell us, what this typeclass is about."""


Supports and delegates
----------------------

``Supports`` type has a special handling of ``delegate`` types.
Let's see an example. We would start with defining a ``delegate`` type:

.. code:: python

  >>> from typing import List
  >>> from classes import AssociatedType, Supports, typeclass

  >>> class ListOfIntMeta(type):
  ...     def __instancecheck__(cls, arg) -> bool:
  ...         return (
  ...             isinstance(arg, list) and
  ...             bool(arg) and
  ...             all(isinstance(list_item, int) for list_item in arg)
  ...         )

  >>> class ListOfInt(List[int], metaclass=ListOfIntMeta):
  ...     ...

Now, let's define a typeclass:

.. code:: python

  >>> class SumAll(AssociatedType):
  ...     ...

  >>> @typeclass(SumAll)
  ... def sum_all(instance) -> int:
  ...     ...

  >>> @sum_all.instance(delegate=ListOfInt)
  ... def _sum_all_list_int(
  ...     # It can be either `List[int]` or `ListOfInt`
  ...     instance: List[int],
  ... ) -> int:
  ...     return sum(instance)

And a function with ``Supports`` type:

.. code:: python

  >>> def test(to_sum: Supports[SumAll]) -> int:
  ...     return sum_all(to_sum)

This will not make ``mypy`` happy:

.. code:: python

  >>> list1 = [1, 2, 3]
  >>> assert test(list1) == 6  # Argument 1 to "test" has incompatible type "List[int]"; expected "Supports[SumAll]"

It will be treated the same as unsupported cases, like ``List[str]``:

.. code:: python

  list2: List[str]
  test(list2)  # Argument 1 to "test" has incompatible type "List[int]"; expected "Supports[SumAll]"

But, this will work correctly:

.. code:: python

  >>> list_of_int = ListOfInt([1, 2, 3])
  >>> assert test(list_of_int) == 6  # ok

  >>> list1 = [1, 2, 3]
  >>> if isinstance(list1, ListOfInt):
  ...     assert test(list1) == 6  # ok

This happens because we don't treat ``List[int]`` as ``Supports[SumAll]``.
This is by design.

But, we treat ``ListOfInt`` as ``Supports[SumAll]``.
So, you would need to narrow ``List[int]`` to ``ListOfInt`` to make it work.

Why? Because we insert ``Supports[SumAll]`` as a super-type of ``List``,
there's no way currently to make ``List[int]`` supported 
and ``List[str]`` not supported.
That's why we've decided to only make ``ListOfInt`` work.

General cases
~~~~~~~~~~~~~

One way to make ``List[int]`` to work without explicit type narrowing
is to define a generic case for all ``list`` subtypes:

.. code:: python

  >>> @sum_all.instance(list)
  ... def _sum_all_list(instance: list) -> int:
  ...     return 0

Now, this will work:

.. code:: python

  >>> list1 = [1, 2, 3]
  >>> assert test(list1) == 6  # ok

  >>> list2 = ['a', 'b']
  >>> assert test(list2) == 0  # ok
