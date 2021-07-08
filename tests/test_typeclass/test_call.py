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


@typeclass
def my_len(instance) -> int:
    """Returns a length of an object."""


@my_len.instance(List[str], delegate=_ListOfStr)
def _my_len_list_str(instance: List[str]) -> int:
    return 0


@my_len.instance(list)
def _my_len_list(instance: list) -> int:
    return 1


@my_len.instance(Sized, is_protocol=True)
def _my_len_sized(instance: Sized) -> int:
    return 2


@my_len.instance(object)
def _my_len_object(instance: object) -> int:
    return 3


@pytest.mark.parametrize('clear_initial_cache', [True, False])
@pytest.mark.parametrize('check_supports', [True, False])
@pytest.mark.parametrize('clear_supports_cache', [True, False])
@pytest.mark.parametrize(('data_type', 'expected'), [
    (['a', 'b'], 0),  # concrete type
    ([], 1),  # direct list call
    ([1, 2, 3], 1),  # direct list call
    ('', 2),  # sized protocol
    (1, 3),  # object fallback
])
def test_call_order(
    data_type,
    expected,
    clear_initial_cache: bool,
    check_supports: bool,
    clear_supports_cache: bool,
) -> None:
    """
    Ensures that call order is correct.

    This is a very tricky test.
    It tests all dispatching order.
    Moreover, it also tests how cache
    interacts with ``__call__`` and ``supports``.

    We literally model all possible cases here.
    """
    if clear_initial_cache:
        my_len._dispatch_cache.clear()  # noqa: WPS437
    if check_supports:
        assert my_len.supports(data_type)
    if clear_supports_cache:
        my_len._dispatch_cache.clear()  # noqa: WPS437
    assert my_len(data_type) == expected
