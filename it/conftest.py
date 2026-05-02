from pathlib import Path

import pytest

from src.driver import create_driver


NAVTEST_OUTPUT = Path(__file__).parent / "last-navtest-output.txt"


def pytest_sessionstart(session):
    NAVTEST_OUTPUT.write_text("")


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests that hit real websites")


@pytest.fixture(scope="class")
def driver():
    d = create_driver()
    yield d
    d.quit()
