from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager

import pytest

from classes._typeclass import _TypeClass  # noqa: WPS450


@pytest.fixture(scope="session")
def clear_cache() -> Callable[[_TypeClass], AbstractContextManager]:
    """Fixture to clear typeclass'es cache before and after."""
    @contextmanager
    def factory(typeclass: _TypeClass) -> Generator[None]:
        typeclass._dispatch_cache.clear()  # noqa: WPS437
        yield
        typeclass._dispatch_cache.clear()  # noqa: WPS437
    return factory
