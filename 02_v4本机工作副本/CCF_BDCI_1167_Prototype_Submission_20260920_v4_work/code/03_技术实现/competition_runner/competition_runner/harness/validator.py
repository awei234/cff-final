from dataclasses import dataclass

from .profiles import ALLOWED_TOOLS, FALLBACK_MANIFEST, PROFILES


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    manifest: dict[str, object]
    errors: tuple[str, ...] = ()
    fallback_reason: str | None = None


def validate_manifest(manifest: dict[str, object]) -> ValidationResult:
    errors: list[str] = []
    profile = manifest.get("profile")
    if profile not in PROFILES:
        errors.append("unknown profile")
    tools = manifest.get("enabled_tools", [])
    if not isinstance(tools, list) or not set(tools).issubset(ALLOWED_TOOLS):
        errors.append("tool not allowlisted")
    calls = manifest.get("max_provider_calls")
    retries = manifest.get("max_retries")
    if not isinstance(calls, int) or calls < 0 or calls > 3:
        errors.append("provider budget exceeded")
    if not isinstance(retries, int) or retries < 0 or retries > 1:
        errors.append("retry budget exceeded")
    if manifest.get("rail_enabled", True) is False:
        errors.append("rail cannot be disabled")
    required = {"profile", "memory_mode", "planning_mode", "enabled_tools", "max_provider_calls", "max_retries", "selection_reason"}
    if not required.issubset(manifest):
        errors.append("manifest fields missing")
    if errors:
        return ValidationResult(False, dict(FALLBACK_MANIFEST), tuple(errors), "; ".join(errors))
    return ValidationResult(True, dict(manifest))
