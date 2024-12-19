from typing import Type

import pytest

from classes import typeclass


class _MyClass:
    """We use this class to test `Type[MyClass]`."""


class _MyClassTypeMeta(type):
    def __instancecheck__(cls, typ) -> bool:
        return typ is _MyClass


class _MyClassType(Type[_MyClass], metaclass=_MyClassTypeMeta):  # type: ignore
    """Delegate class."""


@typeclass
def class_type(typ) -> Type:
    """Returns the type representation."""


@class_type.instance(delegate=_MyClassType)
def _my_class_type(typ: Type[_MyClass]) -> Type:
    return typ


def test_correct_class_type():
    """Ensures `Type[T]` works correctly with delegate."""
    assert class_type(_MyClass) is _MyClass


@pytest.mark.parametrize('typ', [
    int, float, type, dict, list,
])
def test_wrong_class_type(typ):
    """Ensures other types doesn't works with our delegate."""
    with pytest.raises(NotImplementedError):
        class_type(typ)


def test_passing_class_type_instance():
    """Ensures passing a instance of the expected type doesn't work."""
    with pytest.raises(NotImplementedError):
        class_type(_MyClass())  # type: ignore[arg-type]
