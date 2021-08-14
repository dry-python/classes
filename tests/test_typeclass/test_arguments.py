import pytest

from classes import typeclass


@typeclass
def example(instance) -> int:
    """Example typeclass."""


def _example_str(instance: str) -> int:
    return len(instance)


def test_invalid_arguments_empty() -> None:
    """Tests that invalid arguments do raise."""
    with pytest.raises(ValueError, match='At least one argument to .*'):
        example.instance()


def test_invalid_arguments_delegate() -> None:
    """Tests that invalid arguments do raise."""
    with pytest.raises(ValueError, match='Only a single argument can .*'):
        example.instance(str, delegate=str)  # type: ignore


def test_invalid_arguments_protocol() -> None:
    """Tests that invalid arguments do raise."""
    with pytest.raises(ValueError, match='Only a single argument can .*'):
        example.instance(str, protocol=str)  # type: ignore


def test_invalid_arguments_all() -> None:
    """Tests that invalid arguments do raise."""
    with pytest.raises(ValueError, match='Only a single argument can .*'):
        example.instance(str, protocol=True, delegate=str)  # type: ignore
