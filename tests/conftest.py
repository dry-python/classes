from contextlib import contextmanager

import pytest


@pytest.fixture(scope='session')
def clear_cache():
    """Fixture to clear typeclass'es cache before and after."""
    @contextmanager
    def factory(typeclass):
        typeclass._dispatch_cache.clear()  # noqa: WPS437
        yield
        typeclass._dispatch_cache.clear()  # noqa: WPS437
    return factory
