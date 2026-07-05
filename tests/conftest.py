"""
Shared pytest fixtures.

IMPORTANT: `db/database.py`'s SQLAlchemy engine is a module-level singleton,
created once and cached for the entire pytest process (Python caches
imports). If individual test files each delete `local.db` in their own
fixtures, a later deletion can happen *after* an earlier test module has
already opened connections against that file -- deleting it out from under
an already-open engine can leave SQLite in a corrupted-looking state
(observed as "attempt to write a readonly database").

Centralizing the cleanup here, as a session-scoped autouse fixture, means
`local.db` is removed exactly once, before any test module gets a chance
to import `api.main` (and therefore `db.database`) for the first time.
Individual test files should NOT delete `local.db` themselves.
"""
import os

import pytest

LOCAL_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local.db")


@pytest.fixture(scope="session", autouse=True)
def _clean_local_db_once_per_session():
    if os.path.exists(LOCAL_DB):
        os.remove(LOCAL_DB)
    yield
