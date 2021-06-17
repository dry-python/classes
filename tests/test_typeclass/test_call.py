from typing import Sized

import pytest

from classes import typeclass


@typeclass
def my_len(instance) -> int:
    """Returns a length of an object."""


@my_len.instance(object)
def _my_len_object(instance: object) -> int:
    return -1


@my_len.instance(Sized, is_protocol=True)
def _my_len_sized(instance: Sized) -> int:
    return 0


@my_len.instance(list)
def _my_len_list(instance: list) -> int:
    return 1


@pytest.mark.parameterized(('data_type', 'expected'), [
    ([], 1),  # direct list call
    ('', 0),  # sized protocol
    (None, -1),  # object fallback
])
def test_call_order(data_type, expected):
    """Ensures that call order is correct."""
    assert my_len(data_type) == expected
