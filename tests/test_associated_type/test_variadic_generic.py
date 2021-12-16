import sys
from typing import TypeVar

import pytest

from classes import AssociatedType

_FirstType = TypeVar('_FirstType')


@pytest.mark.skipif(sys.version_info[:2] >= (3, 10), reason='Does not work')
def test_type_validation():
    """Ensures that type validation still works."""
    with pytest.raises(TypeError):
        class Example(AssociatedType[1]):  # type: ignore
            """Should fail, because of ``1``."""


def test_type_resets():
    """Ensures that params are reset correctly."""
    class Example(AssociatedType[_FirstType]):
        """Correct type."""

    old_args = Example.__parameters__  # type: ignore # noqa: WPS609
    assert Example[int, int, int]  # type: ignore
    assert Example.__parameters__ == old_args  # type: ignore # noqa: WPS609


def test_subtype_is_variadic():
    """Ensures that subtypes are variadic."""
    class Example(AssociatedType[_FirstType]):
        """Correct type."""

    assert Example[int]
    assert Example[int, int]  # type: ignore
    assert Example[int, int, str]  # type: ignore
