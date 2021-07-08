import pytest

from classes import typeclass


@typeclass
def example(instance) -> int:
    """Example typeclass."""


def _example_str(instance: str) -> int:
    return len(instance)


def test_invalid_argumnets() -> None:
    """Tests that invalid arguments do raise."""
    with pytest.raises(ValueError, match='Both .* passed'):
        example.instance(
            str, is_protocol=True, delegate=str,
        )(_example_str)  # type: ignore
