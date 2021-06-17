from typing import Sized

import pytest

from classes import typeclass


@typeclass
def my_len(instance) -> int:
    """Returns a length of an object."""


@my_len.instance(Sized, is_protocol=True)
def _my_len_sized(instance: Sized) -> int:
    return 0


@my_len.instance(list)
def _my_len_list(instance: list) -> int:
    return 1


class _MyList(list):  # noqa: WPS600
    """We use it to test mro."""


@pytest.mark.parametrize(('data_type', 'expected'), [
    ([], True),  # direct list call
    ('', True),  # sized protocol)
    (1, False),  # default impl
    (_MyList(), True),  # mro fallback
])
def test_supports(data_type, expected):
    """Ensures that ``.supports`` works correctly."""
    assert my_len.supports(data_type) is expected
    assert type(data_type) in my_len._dispatch_cache  # noqa: WPS437, WPS516
