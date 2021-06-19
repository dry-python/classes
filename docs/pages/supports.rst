.. _supports:

Supports
========

We also have a special type to help you specifying
that you want to work with only types that are a part of a specific typeclass.

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

.. warning::
  ``Supports`` only works with typeclasses defined with associated types.
