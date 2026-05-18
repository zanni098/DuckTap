import tomllib
from pathlib import Path

import ducktap


def test_package_version_matches_pyproject():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert ducktap.__version__ == data["project"]["version"]
