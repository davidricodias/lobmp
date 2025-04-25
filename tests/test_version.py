import tomllib
from pathlib import Path

from lobmp._version import VERSION


def test_versions_match():
    cargo = Path().absolute() / "Cargo.toml"
    with open(cargo, "rb") as f:
        data = tomllib.load(f)
        cargo_version = data["package"]["version"]

    assert VERSION == cargo_version
