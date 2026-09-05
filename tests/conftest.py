import json
from pathlib import Path

import pytest


@pytest.fixture
def record():
    def load(kind):
        return json.loads(
            (Path(__file__).parent / "fixtures/contracts" / f"{kind}.json").read_text()
        )

    return load
