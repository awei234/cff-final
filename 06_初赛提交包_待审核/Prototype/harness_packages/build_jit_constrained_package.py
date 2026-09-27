"""Build the ZIP accepted by JiuwenSwarm's Auto Harness importer."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
PACKAGE_NAME = "jit-constrained-research-harness"
SOURCE = ROOT / PACKAGE_NAME
DIST = ROOT / "dist"
OUTPUT = DIST / f"{PACKAGE_NAME}.zip"


def build() -> Path:
    if not (SOURCE / "harness_config.yaml").is_file():
        raise RuntimeError("package source must contain harness_config.yaml")
    DIST.mkdir(exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(SOURCE.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT).as_posix())
    return OUTPUT


if __name__ == "__main__":
    print(build())
