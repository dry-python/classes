from typing import TypeVar

import pytest

from classes import AssociatedType

_FirstType = TypeVar('_FirstType')
_SecondType = TypeVar('_SecondType')
_ThirdType = TypeVar('_ThirdType')


def test_type_validation():
    """Ensures that type validation still works."""
    with pytest.raises(TypeError):
        class Example(AssociatedType[1]):
            """Should fail, because of ``1``."""


def test_type_resets():
    """Ensures that params are reset correctly."""
    class Example(AssociatedType[_FirstType]):
        """Correct type."""

    old_args = Example.__parameters__  # noqa: WPS609
    assert Example[int, int, int]
    assert Example.__parameters__ == old_args  # noqa: WPS609


def test_subtype_is_variadic():
    """Ensures that subtypes are variadic."""
    class Example(AssociatedType[_FirstType]):
        """Correct type."""

    assert Example[int]
    assert Example[int, int]
    assert Example[int, int, str]
