import os
from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import app


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests marked 'db' when TEST_DATABASE_URL is not set."""
    if "db" in item.keywords and not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("Requires TEST_DATABASE_URL environment variable")


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Test client fixture for making requests against the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_conn() -> Iterator[psycopg.Connection]:
    """Yield a database connection to TEST_DATABASE_URL or skip if unset."""
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.skip("Requires TEST_DATABASE_URL environment variable")

    with psycopg.connect(test_db_url) as conn:
        yield conn
