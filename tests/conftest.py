import os
from pathlib import Path

import httpx
import pytest

from contract import Contract

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"


@pytest.fixture
def api():
    with httpx.Client(base_url=BASE_URL, timeout=5) as client:
        yield client


@pytest.fixture(autouse=True)
def reset(api):
    # Скидаємо дані перед кожним тестом. Режим дрейфу НЕ чіпаємо.
    api.post("/_admin/reset").raise_for_status()


@pytest.fixture(scope="session")
def contract():
    return Contract(SPEC_PATH, BASE_URL)
