"""Verify the reviewed research run and the constrained JIT comparison archive."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_RUN = ROOT / "demo_runs" / "research_matrix_live_20260924_authorized"
DEFAULT_JIT = ROOT / "demo_runs" / "jit_comparison_v1_final"
TOPICS = ("context-engineering", "memory-engine", "self-evolution")
EXCLUDED = {"claim-002", "claim-003", "claim-005", "claim-007", "claim-009"}
BACKGROUND = {"claim-018", "claim-019", "claim-020"}
ARMS = {"baseline", "prompt-only", "full-rail", "jit-constrained"}
SEEDS = {42, 43, 44}


def _json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            return value
        errors.append(f"invalid JSON object: {path}")
    except (OSError, ValueError) as exc:
        errors.append(f"cannot read JSON: {path} ({type(exc).__name__})")
    return {}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(base: Path, rel: str, errors: list[str]) -> Path | None:
    target = (base / rel).resolve()
    if not target.is_relative_to(base.resolve()):
        errors.append(f"unsafe artifact path: {rel}")
        return None
    if not target.is_file():
        errors.append(f"missing artifact: {target}")
        return None
    return target


def _pointer(value: object, pointer: str) -> object:
    current = value
    for part in pointer.lstrip("/").split("/"):
        token = part.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def verify_release(run_dir: Path, jit_dir: Path) -> dict:
    run_dir, jit_dir = Path(run_dir).resolve(), Path(jit_dir).resolve()
    errors: list[str] = []
    checked_topics = 0
    checked_pdfs = 0
    checked_pairs = 0

    audit = _json(run_dir / "claim_review_audit.json", errors)
    decisions = _json(run_dir / "human_review_decisions.json", errors)
    matrix = _json(run_dir / "matrix_verification_report.json", errors)
    pdf_check = _json(run_dir / "pdf_compile_verification.json", errors)
    if audit.get("overall_passed") is not True or set(audit.get("expected_excluded_claims", [])) != EXCLUDED:
        errors.append("Claim review audit did not pass with the five expected exclusions")
    if decisions.get("paper_release", {}).get("allow_paper") is not True:
        errors.append("human review does not allow paper release")
    if matrix.get("valid") is not True or matrix.get("status") != "completed_reviewed":
        errors.append("matrix verification is not completed_reviewed and valid")
    if matrix.get("latex_compilation_status") != "compiled_verified":
        errors.append("matrix PDF compilation is not verified")

    for topic in TOPICS:
        folder = run_dir / topic
        review = _json(folder / "review.json", errors)
        report = _json(folder / "report.json", errors)
        ledger = _json(folder / "claim_ledger.json", errors)
        materials = _json(folder / "research_materials.json", errors)
        experiment = _json(folder / "experiment_results.json", errors)
        manifest = _json(folder / "harness_manifest.json", errors)
        validation = _json(folder / "harness_validation.json", errors)
        archive = _json(folder / "harness" / "harness_archive.json", errors)
        provenance = _json(folder / "provenance.json", errors)
        if review.get("allow_paper") is not True:
            errors.append(f"{topic}: allow_paper is not true")
        for name, claim_ids in (("review", review.get("unsupported_claims")),
                                ("report", report.get("unsupported_claims"))):
            if set(claim_ids or []) != EXCLUDED:
                errors.append(f"{topic}: {name} unsupported_claims differ from explicit exclusions")
        eligible = set(review.get("paper_eligible_claims", []))
        if not BACKGROUND.issubset(eligible) or eligible & EXCLUDED:
            errors.append(f"{topic}: paper Claim allowlist is inconsistent")

        sources = {s.get("source_id"): s for s in materials.get("sources", []) if isinstance(s, dict)}
        claims = {c.get("claim_id"): c for c in ledger.get("claims", []) if isinstance(c, dict)}
        experiment_path = folder / "experiment_results.json"
        experiment_hash = _hash(experiment_path) if experiment_path.is_file() else None
        if {cid for cid, claim in claims.items() if claim.get("status") != "supported"} != EXCLUDED:
            errors.append(f"{topic}: Claim ledger statuses differ from explicit exclusions")
        for cid, claim in claims.items():
            for ref in claim.get("evidence_refs", []):
                if ref.get("artifact") != "experiment_results.json" or ref.get("sha256") != experiment_hash:
                    errors.append(f"{topic}: evidence hash mismatch for {cid}")
                else:
                    try:
                        _pointer(experiment, ref["json_pointer"])
                    except (KeyError, IndexError, TypeError, ValueError):
                        errors.append(f"{topic}: invalid evidence pointer for {cid}")
            for ref in claim.get("source_refs", []):
                source = sources.get(ref.get("source_id"))
                if not source or ref.get("sha256") != source.get("content_sha256"):
                    errors.append(f"{topic}: source hash mismatch for {cid}")
                elif claim.get("status") == "supported" and source.get("citation_allowed") is not True:
                    errors.append(f"{topic}: unapproved source for {cid}")
        for cid in BACKGROUND:
            if claims.get(cid, {}).get("status") != "supported" or not claims[cid].get("source_refs"):
                errors.append(f"{topic}: approved background Claim {cid} has no supported source")

        if validation.get("valid") is not True or archive.get("validation", {}).get("valid") is not True:
            errors.append(f"{topic}: Harness validation failed")
        if archive.get("manifest") != manifest or not set(manifest.get("enabled_tools", [])).issubset({"retrieval", "ucr", "citation_rail"}):
            errors.append(f"{topic}: Harness manifest or tool allowlist mismatch")
        if not isinstance(manifest.get("max_provider_calls"), int) or not 0 <= manifest["max_provider_calls"] <= 3:
            errors.append(f"{topic}: Harness provider budget invalid")

        for rel, expected in provenance.get("artifacts", {}).items():
            path = _artifact(folder, rel, errors)
            if path and _hash(path).lower() != str(expected).lower():
                errors.append(f"{topic}: provenance hash mismatch: {rel}")
        if provenance.get("pdf_derivation", {}).get("status") != "compiled_verified":
            errors.append(f"{topic}: PDF derivation is not verified")
        checked_topics += 1

    if pdf_check.get("status") != "compiled_verified" or pdf_check.get("return_code") != 0:
        errors.append("PDF compilation check failed")
    for key in ("text_extraction_check", "render_check", "stale_review_text_check"):
        if pdf_check.get(key) != "passed":
            errors.append(f"PDF {key} failed")
    expected_pdfs = {"paper.pdf"} | {f"{topic}/paper.pdf" for topic in TOPICS}
    if set(pdf_check.get("artifacts", {})) != expected_pdfs:
        errors.append("PDF artifact set is incomplete")
    for rel, record in pdf_check.get("artifacts", {}).items():
        path = _artifact(run_dir, rel, errors)
        if path:
            if not path.read_bytes().startswith(b"%PDF") or _hash(path).lower() != str(record.get("sha256", "")).lower():
                errors.append(f"PDF hash or format mismatch: {rel}")
            if not isinstance(record.get("pages"), int) or record["pages"] < 1:
                errors.append(f"PDF page count invalid: {rel}")
            checked_pdfs += 1

    comparison = _json(jit_dir / "comparison_results.json", errors)
    if set(comparison.get("arms", [])) != ARMS or set(comparison.get("seeds", [])) != SEEDS:
        errors.append("JIT comparison does not contain the four arms and three seeds")
    pairs: set[tuple[int, str]] = set()
    for row in comparison.get("results", []):
        seed, arm = row.get("seed"), row.get("arm")
        if (seed, arm) in pairs:
            errors.append(f"duplicate JIT result for seed {seed}, arm {arm}")
        pairs.add((seed, arm))
        if arm == "jit-constrained":
            if not row.get("rail", {}).get("accepted") or not row.get("manifest"):
                errors.append(f"JIT Rail or manifest missing for seed {seed}")
        if row.get("metrics", {}).get("latency_seconds", {}).get("value") is None:
            errors.append(f"JIT latency missing for seed {seed}, arm {arm}")
        if row.get("metrics", {}).get("cost_usd", {}).get("status") is None:
            errors.append(f"JIT cost status missing for seed {seed}, arm {arm}")
        if isinstance(seed, int) and isinstance(arm, str):
            arm_dir = jit_dir / f"seed-{seed}" / arm
            for rel in ("results.json", "provenance.json", "tool_trace.jsonl"):
                _artifact(arm_dir, rel, errors)
            raw_result = _json(arm_dir / "results.json", errors)
            for metric in ("UCR", "task_success_rate"):
                if (raw_result.get("metrics", {}).get(metric, {}).get("value")
                        != row.get("metrics", {}).get(metric, {}).get("value")):
                    errors.append(f"JIT comparison mismatch for seed {seed}, arm {arm}: {metric}")
            if raw_result.get("rail") != row.get("rail"):
                errors.append(f"JIT comparison mismatch for seed {seed}, arm {arm}: Rail")
            arm_provenance = _json(arm_dir / "provenance.json", errors)
            for rel, expected in arm_provenance.get("files", {}).items():
                path = _artifact(arm_dir, rel, errors)
                if path and _hash(path).lower() != str(expected).lower():
                    errors.append(f"JIT provenance hash mismatch for seed {seed}, arm {arm}: {rel}")
    for seed in SEEDS:
        for arm in ARMS:
            if (seed, arm) not in pairs:
                errors.append(f"missing JIT result for seed {seed}, arm {arm}")
            else:
                checked_pairs += 1
    if comparison.get("gate", {}).get("all_passed") is not True:
        errors.append("JIT comparison gate did not pass")

    return {
        "release_ready": not errors,
        "run_dir": str(run_dir),
        "jit_dir": str(jit_dir),
        "topics_checked": checked_topics,
        "pdfs_checked": checked_pdfs,
        "jit_seed_arm_pairs_checked": checked_pairs,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--jit-dir", type=Path, default=DEFAULT_JIT)
    args = parser.parse_args()
    result = verify_release(args.run_dir, args.jit_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["release_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
