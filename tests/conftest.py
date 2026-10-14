import os
import pytest
from pathlib import Path

@pytest.fixture(autouse=True, scope="session")
def isolate_test_database(tmp_path_factory):
    test_data_dir = tmp_path_factory.mktemp("test_clipforge_data")
    os.environ["CLIPFORGE_DATA_DIR"] = str(test_data_dir)
    from core.storage import init_db
    init_db()
    yield
