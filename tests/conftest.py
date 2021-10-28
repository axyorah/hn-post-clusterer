import os
import tempfile

import pytest

from flaskr import create_app
from flaskr.db import init_db

#(scope="session"): fixture will be shared by all the tests requesting it
@pytest.fixture(scope="session")
def client():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({'TESTING': True, 'DATABASE': db_path})

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)