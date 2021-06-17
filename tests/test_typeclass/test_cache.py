from abc import ABCMeta, abstractmethod

from classes import typeclass


@typeclass
def my_typeclass(instance) -> int:
    """Example typeclass."""


class _MyABC(object, metaclass=ABCMeta):
    @abstractmethod
    def get_number(self) -> int:
        """Example abstract method."""


class _MyConcete(_MyABC):
    def get_number(self) -> int:
        """Concrete method."""
        return 1


class _MyRegistered(object):
    def get_number(self) -> int:
        """Would be registered in ``_MyABC`` later."""
        return 2


def _my_int(instance: int) -> int:
    return instance


def _my_abc(instance: _MyABC) -> int:
    return instance.get_number()


def test_cache_invalidation():  # noqa: WPS218
    """Ensures that cache invalidation for ABC types work correctly."""
    assert not my_typeclass._dispatch_cache  # noqa: WPS437
    assert not my_typeclass._cache_token  # noqa: WPS437

    my_typeclass.instance(_MyABC)(_my_abc)
    assert not my_typeclass._dispatch_cache  # noqa: WPS437
    assert my_typeclass._cache_token  # noqa: WPS437

    assert my_typeclass(_MyConcete()) == 1
    assert my_typeclass._dispatch_cache  # noqa: WPS437

    _MyABC.register(_MyRegistered)
    assert my_typeclass(_MyRegistered()) == 2  # type: ignore
    assert my_typeclass._dispatch_cache  # noqa: WPS437
