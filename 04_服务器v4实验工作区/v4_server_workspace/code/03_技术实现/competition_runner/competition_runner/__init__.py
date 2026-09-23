"""Portable competition runner configuration contracts."""

from .artifact_contract import (
    HASHED_ARTIFACTS,
    REQUIRED_ARTIFACTS,
    ContractIssue,
    load_json_object,
    load_jsonl,
    sha256_file,
)
from .generation import (
    FixtureBackend,
    GeneratedContent,
    GenerationError,
    GenerationRequest,
    generate_run,
)
from .output_guard import OutputGuardError, reserve_output_directories, reserve_output_directory
from .paths import PathConfigError, ResolvedPaths, find_project_root, resolve_paths
from .providers import ProviderConfigError, ResolvedProvider, resolve_provider
from .verification import VerificationResult, verify_run

__all__ = [
    "HASHED_ARTIFACTS",
    "ContractIssue",
    "FixtureBackend",
    "GeneratedContent",
    "GenerationError",
    "GenerationRequest",
    "PathConfigError",
    "OutputGuardError",
    "ProviderConfigError",
    "REQUIRED_ARTIFACTS",
    "ResolvedPaths",
    "ResolvedProvider",
    "VerificationResult",
    "find_project_root",
    "generate_run",
    "load_json_object",
    "load_jsonl",
    "reserve_output_directories",
    "reserve_output_directory",
    "resolve_paths",
    "resolve_provider",
    "sha256_file",
    "verify_run",
]
