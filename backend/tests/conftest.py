import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
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


@pytest.fixture(scope="session")
def apply_migrations() -> None:
    """Run alembic upgrade head once per test session if TEST_DATABASE_URL is set."""
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url:
        return

    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))

    # Pass TEST_DATABASE_URL to alembic migrations
    os.environ["DATABASE_URL"] = test_db_url
    command.upgrade(alembic_cfg, "head")


@pytest.fixture
def db_conn(apply_migrations: None) -> Iterator[psycopg.Connection]:
    """Yield a database connection to TEST_DATABASE_URL and clean tables between tests."""
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.skip("Requires TEST_DATABASE_URL environment variable")

    with psycopg.connect(test_db_url, autocommit=True) as conn:
        # Clean identity tables before test execution
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE api_tokens, workstations, employees CASCADE;")
        yield conn
        # Clean identity tables after test execution
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE api_tokens, workstations, employees CASCADE;")
