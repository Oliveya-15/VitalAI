import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ADMIN_KEY"] = "test-admin"
os.environ["LLM_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.main import app

P = "/api/v1"


def make_user(c, email, name="Test User", password="Passw0rd1", phone=None):
    body = {"name": name, "email": email, "password": password}
    if phone:
        body["phone"] = phone
    r = c.post(f"{P}/auth/register", json=body)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="session")
def client():
    """A TestClient already signed in as a default user (so feature tests need no extra setup)."""
    with TestClient(app) as c:
        session = make_user(c, "main@example.com", phone="9111111111")
        c.headers.update({"Authorization": f"Bearer {session['token']}"})
        yield c


@pytest.fixture(scope="session")
def anon(client):
    """A client with NO login (depends on `client` so the app has started)."""
    return TestClient(app)
