# -*- coding: utf-8 -*-

from typing import Sized

from classes import typeclass


@typeclass
def protocols(instance, other: str) -> str:
    """Example typeclass for protocols."""


@protocols.instance(Sized, is_protocol=True)
def _sized_protocols(instance: Sized, other: str) -> str:
    return str(len(instance)) + other


@protocols.instance(str)
def _str_type(instance: str, other: str) -> str:
    return instance + other


class _CustomSized(object):
    def __len__(self) -> int:
        return 2


def test_sized_protocol():
    """Ensure that sized protocol works."""
    assert protocols(_CustomSized(), '1') == '21'
    assert protocols([1, 2, 3], '0') == '30'


def test_type_takes_over():
    """Ensure that int protocol works."""
    assert protocols('a', 'b') == 'ab'
