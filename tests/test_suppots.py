from typing import List, Sized

import pytest

from classes import typeclass


class _ListOfStrMeta(type):
    def __instancecheck__(cls, other) -> bool:
        return (
            isinstance(other, list) and
            bool(other) and
            all(isinstance(list_item, str) for list_item in other)
        )


class _ListOfStr(List[str], metaclass=_ListOfStrMeta):
    """We use this for testing concrete type calls."""


class _MyList(list):  # noqa: WPS600
    """We use it to test mro."""


@typeclass
def my_len(instance) -> int:
    """Returns a length of an object."""


@my_len.instance(Sized, is_protocol=True)
def _my_len_sized(instance: Sized) -> int:
    return 0


@my_len.instance(list)
def _my_len_list(instance: list) -> int:
    return 1


@my_len.instance(List[str], delegate=_ListOfStr)
def _my_len_list_str(instance: List[str]) -> int:
    return 2


@pytest.mark.parametrize(('data_type', 'expected'), [
    ([], True),  # direct list call
    ('', True),  # sized protocol
    (1, False),  # default impl
    (_MyList(), True),  # mro fallback
    (_ListOfStr(), True),  # mro fallback
    (_ListOfStr(['a']), True),  # mro fallback
])
def test_supports(data_type, expected: bool, clear_cache) -> None:
    """Ensures that ``.supports`` works correctly."""
    with clear_cache(my_len):
        assert my_len.supports(data_type) is expected


def test_supports_twice_regular(clear_cache) -> None:
    """Ensures that calling ``supports`` twice for regular type is cached."""
    with clear_cache(my_len):
        assert list not in my_len._dispatch_cache  # noqa: WPS437
        assert my_len.supports([]) is True
        assert list in my_len._dispatch_cache  # noqa: WPS437
        assert my_len.supports([]) is True


def test_supports_twice_concrete(clear_cache) -> None:
    """Ensures that calling ``supports`` twice for concrete type is ignored."""
    with clear_cache(my_len):
        for _ in range(2):
            assert not my_len._dispatch_cache  # noqa: WPS437
            assert my_len.supports(['a', 'b']) is True
