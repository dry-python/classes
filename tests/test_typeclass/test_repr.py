from classes import AssociatedType, typeclass


class MyType(AssociatedType):
    """Docs for type."""


@typeclass(MyType)
def my_typeclass_with_type(instance) -> str:
    """Docs."""


@typeclass
def my_typeclass(instance) -> str:
    """Docs."""


def test_str() -> None:
    """Ensures that ``str`` is correct."""
    assert str(my_typeclass) == '<typeclass "my_typeclass">'
    assert str(
        my_typeclass_with_type,
    ) == '<typeclass "my_typeclass_with_type": "MyType">'
