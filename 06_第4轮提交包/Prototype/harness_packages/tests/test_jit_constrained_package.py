"""Structural contract for the importable JIT Harness package."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "dist" / "jit-constrained-research-harness.zip"
PREFIX = "jit-constrained-research-harness/"


def test_importable_package_has_required_files() -> None:
    assert ZIP_PATH.is_file(), "run build_jit_constrained_package.py first"
    with ZipFile(ZIP_PATH) as archive:
        members = set(archive.namelist())
        assert PREFIX + "harness_config.yaml" in members
        assert PREFIX + "manifest.json" in members
        assert PREFIX + "safety_profile.json" in members
        assert PREFIX + "harness.schema.json" in members
        assert PREFIX + "README.md" in members
        manifest = json.loads(archive.read(PREFIX + "manifest.json"))
    assert manifest["profile"] == "full-rail"
    assert manifest["enabled_tools"] == ["retrieval", "ucr", "citation_rail"]
    assert manifest["max_provider_calls"] == 3
    assert manifest["max_retries"] == 1


if __name__ == "__main__":
    test_importable_package_has_required_files()
    print("JIT Harness package contract passed")
