"""Keep API import-time initialization out of every shared application store."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory

_bootstrap = None


def pytest_configure(config):
    global _bootstrap
    if _bootstrap is None:
        _bootstrap = TemporaryDirectory(prefix='builder-pytest-bootstrap-')
    # Fixtures select their own stores. This protects eager `main.app` creation
    # during collection, including when an operator has a database URL exported.
    os.environ['BUILDER_DATABASE_URL'] = str(Path(_bootstrap.name) / 'unused-default.sqlite3')
