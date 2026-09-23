"""Machine-independent project path resolution."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping


PATH_FIELDS = ("workspace_root", "output_root", "experiment_script")
SUPPORTED_FIELDS = ("project_root", *PATH_FIELDS, "jiuwenswarm_command")
DEFAULTS = {
    "workspace_root": "workspace",
    "output_root": "runs",
    "experiment_script": "03_技术实现/ucr_benchmark/run_experiment.py",
    "jiuwenswarm_command": "jiuwenswarm",
}


class PathConfigError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ResolvedPaths:
    project_root: Path
    workspace_root: Path
    output_root: Path
    experiment_script: Path
    jiuwenswarm_command: str
    sources: dict[str, str]

    def as_report(self) -> dict[str, object]:
        report: dict[str, object] = {}
        for name in ("project_root", *PATH_FIELDS):
            value = getattr(self, name)
            report[name] = {
                "value": str(value),
                "source": self.sources[name],
                "exists": value.exists(),
            }
        report["jiuwenswarm_command"] = {
            "value": self.jiuwenswarm_command,
            "source": self.sources["jiuwenswarm_command"],
        }
        return report


def _implementation_dir(directory: Path) -> Path | None:
    """Return the implementation root for both workspace and public-package layouts."""
    direct = directory / "03_技术实现"
    packaged = directory / "code" / "03_技术实现"
    if direct.is_dir():
        return direct
    if packaged.is_dir():
        return packaged
    return None


def find_project_root(anchor: Path) -> Path:
    candidate = anchor.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    directories = (candidate, *candidate.parents)
    # Prefer the public-package root when the anchor is inside code/.
    for directory in directories:
        if (directory / "README.md").is_file() and (directory / "code" / "03_技术实现").is_dir():
            return directory
    # The development workspace keeps the implementation directly under the
    # project root (03_技术实现/...).
    for directory in directories:
        if (directory / "README.md").is_file() and (directory / "03_技术实现").is_dir():
            return directory
    raise PathConfigError("project_root_not_found", "project root was not found from anchor")


def _load_config(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if not path.is_file():
        raise PathConfigError("config_missing", f"configuration file does not exist: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PathConfigError("config_invalid_json", f"invalid JSON configuration: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise PathConfigError("config_invalid_type", "path configuration must be a JSON object")
    unknown = sorted(set(parsed) - set(SUPPORTED_FIELDS))
    if unknown:
        raise PathConfigError("config_unknown_field", f"unknown path configuration field: {unknown[0]}")
    for name, value in parsed.items():
        if not isinstance(value, str) or not value.strip():
            raise PathConfigError("config_invalid_field", f"path configuration field must be a non-empty string: {name}")
    return parsed


def _resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()

    direct = (root / path).resolve()
    if direct.exists():
        return direct

    # The public submission nests the implementation under code/, while the
    # working repository keeps it at the project root. Prefer the packaged
    # counterpart when it exists so documented commands work after extraction.
    packaged = (root / "code" / path).resolve()
    if packaged.exists() or (path.parts and path.parts[0] == "03_技术实现"):
        return packaged
    return direct


def resolve_paths(
    *,
    anchor: Path | None = None,
    project_root: str | Path | None = None,
    config_path: str | Path | None = None,
    overrides: Mapping[str, str | Path | None] | None = None,
) -> ResolvedPaths:
    config = _load_config(Path(config_path) if config_path is not None else None)
    overrides = {name: value for name, value in (overrides or {}).items() if value is not None}
    unknown_overrides = sorted(set(overrides) - set(PATH_FIELDS) - {"jiuwenswarm_command"})
    if unknown_overrides:
        raise PathConfigError("override_unknown_field", f"unknown path override: {unknown_overrides[0]}")

    explicit_root = project_root if project_root is not None else config.get("project_root")
    if explicit_root is None:
        root = find_project_root(anchor or Path(__file__))
        root_source = "inferred"
    else:
        root = Path(explicit_root).expanduser().resolve()
        root_source = "cli" if project_root is not None else "config"
    if not root.is_dir():
        raise PathConfigError("project_root_missing", f"project root does not exist: {root}")

    values: dict[str, str | Path] = {}
    sources: dict[str, str] = {"project_root": root_source}
    for name in (*PATH_FIELDS, "jiuwenswarm_command"):
        if name in overrides:
            values[name] = overrides[name]  # type: ignore[assignment]
            sources[name] = "cli"
        elif name in config:
            values[name] = config[name]
            sources[name] = "config"
        else:
            values[name] = DEFAULTS[name]
            sources[name] = "default"

    return ResolvedPaths(
        project_root=root,
        workspace_root=_resolve_path(root, values["workspace_root"]),
        output_root=_resolve_path(root, values["output_root"]),
        experiment_script=_resolve_path(root, values["experiment_script"]),
        jiuwenswarm_command=str(values["jiuwenswarm_command"]),
        sources=sources,
    )

