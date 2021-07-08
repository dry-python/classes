import sys
from pathlib import Path
from types import MappingProxyType

from typing_extensions import Final

PYTHON_VERSION: Final = (sys.version_info.major, sys.version_info.minor)
ENABLE_SINCE: Final = MappingProxyType({
    (3, 8): frozenset((
        Path('docs/pages/concept.rst'),
    )),
})
PATHS_TO_IGNORE_NOW: Final = frozenset(
    path.absolute()
    for since_python, to_ignore in ENABLE_SINCE.items()
    for path in to_ignore
    if PYTHON_VERSION < since_python
)


# TODO: remove after `phantom-types` release with `python3.7` support
def pytest_collection_modifyitems(items) -> None:  # noqa: WPS110
    """Conditionally removes some collected docstests."""
    to_ignore_items = []
    for test_item in items:
        if not getattr(test_item, 'dtest', None):
            continue
        if Path(test_item.dtest.filename) in PATHS_TO_IGNORE_NOW:
            to_ignore_items.append(test_item)

    for to_ignore in to_ignore_items:
        items.remove(to_ignore)
