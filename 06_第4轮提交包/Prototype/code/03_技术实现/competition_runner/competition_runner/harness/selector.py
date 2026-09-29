from .profiles import PROFILES


def select_harness(task_features: dict[str, object]) -> dict[str, object]:
    if task_features.get("repair_required"):
        profile = "repair_first"
    elif task_features.get("cost_limited"):
        profile = "cost_limited"
    elif task_features.get("experiment_required"):
        profile = "experiment_first"
    else:
        profile = "evidence_first" if task_features.get("requires_evidence") else "experiment_first"
    return {**PROFILES[profile], "profile": profile, "selection_reason": f"deterministic selection for {profile}"}
