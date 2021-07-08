from contextlib import contextmanager
from typing import Callable, ContextManager, Iterator

import pytest

from classes._typeclass import _TypeClass  # noqa: WPS450


@pytest.fixture(scope='session')
def clear_cache() -> Callable[[_TypeClass], ContextManager]:
    """Fixture to clear typeclass'es cache before and after."""
    @contextmanager
    def factory(typeclass: _TypeClass) -> Iterator[None]:
        typeclass._dispatch_cache.clear()  # noqa: WPS437
        yield
        typeclass._dispatch_cache.clear()  # noqa: WPS437
    return factory
