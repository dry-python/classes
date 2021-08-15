import sys

import pytest
from typing_extensions import TypedDict

from classes import typeclass

if sys.version_info[:2] >= (3, 9):
    pytestmark = pytest.mark.skip('Only python3.7 and python3.8 are supported')
else:
    class _User(TypedDict):
        name: str
        registered: bool

    _TypedDictMeta = type(TypedDict)

    class _UserDictMeta(_TypedDictMeta):  # type: ignore
        def __instancecheck__(self, arg: object) -> bool:
            return (
                isinstance(arg, dict) and
                isinstance(arg.get('name'), str) and
                isinstance(arg.get('registered'), bool)
            )

    class UserDict(_User, metaclass=_UserDictMeta):
        """We use this class to represent a typed dict with instance check."""

    @typeclass
    def get_name(instance) -> str:
        """Example typeclass."""

    @get_name.instance(delegate=UserDict)
    def _get_name_user_dict(instance: UserDict) -> str:
        return instance['name']

    def test_typed_dict():
        """Ensures that typed dict dispatch works."""
        user: UserDict = {'name': 'sobolevn', 'registered': True}
        assert get_name(user) == 'sobolevn'
