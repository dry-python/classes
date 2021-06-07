import pytest

from classes import typeclass


class _Example(object):
    def __call__(self, instance) -> str:
        """Example class-based typeclass def."""


def _example(instance) -> str:
    """Example function-based typeclass def."""


def test_class_reuse() -> None:
    """Ensures that it is impossible to reuse classes."""
    typeclass(_Example)

    with pytest.raises(TypeError):
        typeclass(_Example)


def test_function_reuse() -> None:
    """Ensures that it is possible to reuse classes."""
    typeclass(_example)
    typeclass(_example)
