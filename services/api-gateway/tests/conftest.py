# conftest.py – sets asyncio_mode for pytest-asyncio >=0.21 and for 1.x
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async",
    )
