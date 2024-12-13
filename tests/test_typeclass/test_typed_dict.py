import sys

import pytest
from typing_extensions import TypedDict

from classes import typeclass

if sys.version_info[:2] >= (3, 9):  # noqa: C901
    pytestmark = pytest.mark.skip('Only python3.7 and python3.8 are supported')
else:
    # TODO drop it completely since classes support Python 3.10+
    class _User(TypedDict):
        name: str
        registered: bool

    class _UserDictMeta(type):
        def __instancecheck__(cls, arg: object) -> bool:
            return (
                isinstance(arg, dict) and
                isinstance(arg.get('name'), str) and
                isinstance(arg.get('registered'), bool)
            )

    _Meta = type('_Meta', (_UserDictMeta, type(TypedDict)), {})

    class UserDict(_User, metaclass=_Meta):
        """We use this class to represent a typed dict with instance check."""

    @typeclass
    def get_name(instance) -> str:
        """Example typeclass."""

    @get_name.instance(delegate=UserDict)
    def _get_name_user_dict(instance: UserDict) -> str:
        return instance['name']

    def test_correct_typed_dict():
        """Ensures that typed dict dispatch works."""
        user: UserDict = {'name': 'sobolevn', 'registered': True}
        assert get_name(user) == 'sobolevn'

    @pytest.mark.parametrize('test_value', [
        [],
        {},
        {'name': 'sobolevn', 'registered': None},
        {'name': 'sobolevn'},
        {'registered': True},
    ])
    def test_wrong_typed_dict(test_value):
        """Ensures that typed dict dispatch works."""
        with pytest.raises(NotImplementedError):
            get_name(test_value)
