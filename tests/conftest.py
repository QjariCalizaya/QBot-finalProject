import os
import sys
import tempfile
import pytest
import importlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))



@pytest.fixture
def temp_db(monkeypatch):
    fd, path = tempfile.mkstemp()
    os.close(fd)

    monkeypatch.setenv("DB_PATH", path)

    if "db" in sys.modules:
        del sys.modules["db"]

    import db
    importlib.reload(db)

    db.init_db()

    yield path

    os.remove(path)
