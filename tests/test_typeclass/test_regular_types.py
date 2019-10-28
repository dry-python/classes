# -*- coding: utf-8 -*-

from typing import List

from classes import typeclass


@typeclass
def example(instance) -> str:
    """Example protocol."""


@example.instance(list)
def _example_list(instance: List) -> str:
    return ''.join(str(col_item) for col_item in instance)


@example.instance(int)
def _example_int(instance: int) -> str:
    return 'a' * instance


def test_regular_type():
    """Ensures that types correctly work."""
    assert example([1, 2, 3]) == '123'
    assert example(['a', 'b', 'c']) == 'abc'
    assert example(2) == 'aa'
