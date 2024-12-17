from abc import ABCMeta, abstractmethod

from classes import typeclass


@typeclass
def my_typeclass(instance) -> int:
    """Example typeclass."""


class _MyABC(metaclass=ABCMeta):
    @abstractmethod
    def get_number(self) -> int:
        """Example abstract method."""


class _MyConcrete(_MyABC):
    def get_number(self) -> int:
        """Concrete method."""
        return 1


class _MyRegistered:
    def get_number(self) -> int:
        """Would be registered in ``_MyABC`` later."""
        return 2


def _my_int(instance: int) -> int:
    return instance


def _my_abc(instance: _MyABC) -> int:
    return instance.get_number()


def test_cache_concrete(clear_cache) -> None:  # noqa: WPS218
    """Ensures that cache invalidation for ABC types work correctly."""
    with clear_cache(my_typeclass):
        assert not my_typeclass._dispatch_cache  # noqa: WPS437

        my_typeclass.instance(_MyABC)(_my_abc)
        assert not my_typeclass._dispatch_cache  # noqa: WPS437

        assert my_typeclass(_MyConcrete()) == 1
        assert _MyConcrete in my_typeclass._dispatch_cache  # noqa: WPS437

        _MyABC.register(_MyRegistered)
        assert my_typeclass(_MyRegistered()) == 2  # type: ignore
        assert _MyRegistered in my_typeclass._dispatch_cache  # noqa: WPS437


def test_cached_calls(clear_cache) -> None:
    """Ensures that regular types trigger cache."""
    with clear_cache(my_typeclass):
        my_typeclass.instance(int)(_my_int)
        assert not my_typeclass._dispatch_cache  # noqa: WPS437

        assert my_typeclass(1)
        assert my_typeclass._dispatch_cache  # noqa: WPS437
