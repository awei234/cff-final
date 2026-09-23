from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOPICS = ("context-engineering", "memory-engine", "self-evolution")
PDF_PATHS = (
    "paper/paper.pdf",
    "demo_runs/research_matrix_v4/context-engineering/paper.pdf",
    "demo_runs/research_matrix_v4/memory-engine/paper.pdf",
    "demo_runs/research_matrix_v4/self-evolution/paper.pdf",
)
TOPIC_FILES = (
    "run_manifest.json", "research_materials.json", "plan.json", "review.json",
    "report.json", "experiment_config.json", "experiment_results.json", "results.json",
    "claim_ledger.json", "tool_trace.jsonl", "rail_events.jsonl", "execution_report.json",
    "human_interventions.jsonl", "provenance.json", "verification_report.json", "paper.tex", "paper.pdf",
)
TEXT_EXTS = {".py", ".json", ".jsonl", ".md", ".tex", ".txt", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".ps1"}
EXCLUDED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".research_cache", "cache", "tmp"}
ALLOWED_CLAIM_TYPES = {"background", "method", "experiment_observation", "metric", "limitation", "conclusion"}
ALLOWED_CLAIM_STATUS = {"supported", "unsupported", "blocked", "pending_human_review"}
EXPECTED_BACKUPS = {
    "v1": "CDC4659DA4DC8340F47BB535363A9B5FE5E7D1481F0A6B8F8FFECCE6ACF17102",
    "v2": "0AFA1B0A9A407CEEB4BB67BAD03C58BCF2D7EE3B63C19EDC2C4431D4575DC77F",
    "v3": "8B607F2A19F78BBAF45B590AB180F1BDF0A258147BACE70AB9CAF40A13BD776A",
}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.I),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}", re.I),
    re.compile(r"(?:SAR_ACCESS_TOKEN|SAR_TOKEN)\s*[:=]\s*[^\s\"']{16,}", re.I),
)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def io_path(path: Path) -> Path:
    """Use the Windows extended path prefix when a package path is very long."""
    raw = str(path)
    if os.name == "nt" and not raw.startswith("\\\\?\\") and len(raw) >= 240:
        return Path("\\\\?\\" + raw)
    return path

def sha256_file(path: Path) -> str:
    return sha256_bytes(io_path(path).read_bytes())

def tree_files():
    root_raw = str(ROOT)
    walk_root = ("\\\\?\\" + root_raw) if os.name == "nt" and not root_raw.startswith("\\\\?\\") else root_raw
    for dirpath, _dirnames, filenames in os.walk(walk_root):
        normal_dir = dirpath[4:] if dirpath.startswith("\\\\?\\") else dirpath
        for filename in filenames:
            yield Path(normal_dir) / filename

def iter_files():
    for path in tree_files():
        if path.name.endswith((".pyc", ".pyo")):
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.name == "CHECKSUMS.sha256":
            continue
        yield path

def check_checksums(errors: list[str]):
    checksum_path = ROOT / "CHECKSUMS.sha256"
    if not checksum_path.exists():
        errors.append("missing CHECKSUMS.sha256")
        return
    expected: dict[str, str] = {}
    for line_no, line in enumerate(io_path(checksum_path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            digest, rel = line.split("  ", 1)
        except ValueError:
            errors.append(f"invalid CHECKSUMS.sha256 line {line_no}")
            continue
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            errors.append(f"unsafe checksum path: {rel}")
            continue
        if rel in expected:
            errors.append(f"duplicate checksum entry: {rel}")
        expected[rel] = digest.lower()
    actual_files = {
        path.relative_to(ROOT).as_posix()
        for path in tree_files()
        if io_path(path).is_file() and path != checksum_path
    }
    for rel in sorted(actual_files - set(expected)):
        errors.append(f"file missing from CHECKSUMS.sha256: {rel}")
    for rel in sorted(set(expected) - actual_files):
        errors.append(f"checksum target missing: {rel}")
    for rel, wanted in expected.items():
        path = ROOT / Path(rel)
        if not io_path(path).is_file():
            continue
        actual = sha256_file(path)
        if actual != wanted:
            errors.append(f"checksum mismatch: {rel}")


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(io_path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid JSON: {path.relative_to(ROOT)} ({type(exc).__name__})")
        return {}

def resolve_runner():
    candidates = [p for p in (ROOT / "code").rglob("run_research_matrix.py") if "competition_runner" in p.parts]
    return candidates[0] if candidates else None

def resolve_schema():
    candidates = [p for p in (ROOT / "code").rglob("plan.schema.json") if p.parent.name == "schemas"]
    return candidates[0] if candidates else None

def json_pointer(value, pointer):
    current = value
    if pointer in ("", "/"):
        return current
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise KeyError(token)
    return current

def check_claim_ledger(topic_dir: Path, errors: list[str]):
    ledger_path = topic_dir / "claim_ledger.json"
    materials_path = topic_dir / "research_materials.json"
    experiment_path = topic_dir / "experiment_results.json"
    report_path = topic_dir / "report.json"
    ledger = load_json(ledger_path, errors)
    materials = load_json(materials_path, errors)
    experiment = load_json(experiment_path, errors)
    report = load_json(report_path, errors)
    claims = ledger.get("claims", []) if isinstance(ledger, dict) else []
    if not isinstance(claims, list):
        errors.append(f"{topic_dir.name}: claim_ledger.claims is not an array")
        return
    ids = []
    source_map = {s.get("source_id"): s for s in materials.get("sources", []) if isinstance(s, dict)}
    experiment_hash = sha256_file(experiment_path)
    for claim in claims:
        if not isinstance(claim, dict):
            errors.append(f"{topic_dir.name}: non-object claim")
            continue
        cid = claim.get("claim_id")
        ids.append(cid)
        if not cid:
            errors.append(f"{topic_dir.name}: claim without claim_id")
        if claim.get("claim_type") not in ALLOWED_CLAIM_TYPES:
            errors.append(f"{topic_dir.name}: invalid claim_type for {cid}")
        if claim.get("status") not in ALLOWED_CLAIM_STATUS:
            errors.append(f"{topic_dir.name}: invalid claim status for {cid}")
        for evidence in claim.get("evidence_refs", []):
            if evidence.get("artifact") != "experiment_results.json":
                errors.append(f"{topic_dir.name}: unsupported evidence artifact for {cid}")
                continue
            try:
                json_pointer(experiment, evidence.get("json_pointer", ""))
            except Exception:
                errors.append(f"{topic_dir.name}: invalid JSON pointer for {cid}")
            if evidence.get("sha256") != experiment_hash:
                errors.append(f"{topic_dir.name}: evidence hash mismatch for {cid}")
        for source in claim.get("source_refs", []):
            sid = source.get("source_id")
            record = source_map.get(sid)
            if record is None:
                errors.append(f"{topic_dir.name}: unknown source {sid} for {cid}")
            elif source.get("sha256") != record.get("content_sha256"):
                errors.append(f"{topic_dir.name}: source hash mismatch for {cid}")
            elif claim.get("status") == "supported" and not record.get("citation_allowed", False):
                errors.append(f"{topic_dir.name}: unapproved source used by supported claim {cid}")
    if len(ids) != len(set(ids)):
        errors.append(f"{topic_dir.name}: duplicate claim_id")
    unsupported = sorted(c.get("claim_id") for c in claims if c.get("status") != "supported")
    reported = sorted(report.get("unsupported_claims", [])) if isinstance(report, dict) else []
    if unsupported != reported:
        errors.append(f"{topic_dir.name}: report.unsupported_claims does not match claim ledger")
    for mapping in report.get("citation_mapping", []) if isinstance(report, dict) else []:
        sid = mapping.get("source_id")
        if sid not in source_map:
            errors.append(f"{topic_dir.name}: report maps unknown source {sid}")
        elif not source_map[sid].get("citation_allowed", False):
            errors.append(f"{topic_dir.name}: report maps unapproved source {sid}")

def check_pdfs(errors: list[str]):
    expected = set(PDF_PATHS)
    for rel in PDF_PATHS:
        path = ROOT / Path(rel)
        if not path.exists():
            errors.append(f"missing required PDF: {rel}")
            continue
        try:
            data = io_path(path).read_bytes()
        except Exception as exc:
            errors.append(f"unreadable PDF: {rel} ({type(exc).__name__})")
            continue
        if len(data) == 0 or not data.startswith(b"%PDF"):
            errors.append(f"invalid or empty PDF: {rel}")
    for path in tree_files():
        if path.suffix.lower() == ".pdf":
            rel = path.relative_to(ROOT).as_posix()
            if rel not in expected:
                errors.append(f"unexpected PDF: {rel}")

def main() -> int:
    errors: list[str] = []
    required = [ROOT / "README.md", ROOT / "submission_manifest.json", ROOT / "paper" / "paper.tex", ROOT / "paper" / "paper.pdf"]
    if resolve_runner() is None:
        errors.append("missing competition_runner/run_research_matrix.py")
    if resolve_schema() is None:
        errors.append("missing competition_runner/schemas/plan.schema.json")
    for path in required:
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")

    for path in iter_files():
        if path.suffix.lower() not in TEXT_EXTS:
            continue
        if path.name == "verify_submission.py":
            continue
        text = io_path(path).read_text(encoding="utf-8", errors="replace")
        if "\ufffd" in text:
            errors.append(f"replacement character: {path.relative_to(ROOT)}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret: {path.relative_to(ROOT)}")
                break

    forbidden = []
    root_raw = str(ROOT)
    walk_root = ("\\\\?\\" + root_raw) if os.name == "nt" and not root_raw.startswith("\\\\?\\") else root_raw
    for dirpath, dirnames, filenames in os.walk(walk_root):
        normal_dir = dirpath[4:] if dirpath.startswith("\\\\?\\") else dirpath
        dir_path = Path(normal_dir)
        for dirname in dirnames:
            path = dir_path / dirname
            rel = path.relative_to(ROOT).as_posix()
            if dirname in EXCLUDED_DIR_NAMES:
                forbidden.append(rel)
        for filename in filenames:
            path = dir_path / filename
            rel = path.relative_to(ROOT).as_posix()
            if path.suffix.lower() in {".pyc", ".pyo"}:
                forbidden.append(rel)
            if path.suffix.lower() == ".pdf" and rel not in set(PDF_PATHS):
                forbidden.append(rel)
            if (
                path.name in {"paper.aux", "paper.log", "paper.fls", "paper.fdb_latexmk"}
                or path.name.endswith(".synctex.gz")
                or path.name.startswith("compile_pass_")
                or "demo_runs/research_matrix_v3" in rel
                or "demo_runs/research_matrix_v4_mock" in rel
                or "demo_runs/research_matrix_v4_retry2" in rel
                or rel.endswith("paper.tex.server")
            ):
                forbidden.append(rel)
    for item in sorted(set(forbidden)):
        errors.append(f"forbidden package artifact: {item}")
    check_pdfs(errors)
    check_checksums(errors)

    manifest_path = ROOT / "submission_manifest.json"
    manifest = load_json(manifest_path, errors) if manifest_path.exists() else {}
    if manifest.get("package_status") != "prepared_not_uploaded":
        errors.append("manifest package_status must be prepared_not_uploaded")
    if manifest.get("uploaded") is not False:
        errors.append("manifest uploaded must be false")
    if manifest.get("human_review_status") != "pending":
        errors.append("manifest human_review_status must be pending")
    if manifest.get("verification_status") != "valid":
        errors.append("manifest verification_status must be valid")
    latex_status = manifest.get("latex_compilation_status", manifest.get("paper", {}).get("latex_compilation_status"))
    if latex_status != "compiled_verified":
        errors.append("manifest latex_compilation_status must be compiled_verified")
    if manifest.get("paper", {}).get("latex_compilation_status") != "compiled_verified":
        errors.append("manifest paper.latex_compilation_status must be compiled_verified")
    if manifest.get("paper", {}).get("pdf_included") is not True:
        errors.append("manifest paper.pdf_included must be true")
    for key, expected in EXPECTED_BACKUPS.items():
        actual = manifest.get("backups", {}).get(f"{key}_zip", {}).get("sha256")
        if actual != expected:
            errors.append(f"backup hash mismatch: {key}")

    matrix = ROOT / "demo_runs" / "research_matrix_v4"
    execution_path = matrix / "matrix_execution_report.json"
    verification_path = matrix / "matrix_verification_report.json"
    execution = load_json(execution_path, errors) if execution_path.exists() else {}
    verification = load_json(verification_path, errors) if verification_path.exists() else {}
    if not execution_path.exists(): errors.append("missing demo_runs/research_matrix_v4/matrix_execution_report.json")
    if not verification_path.exists(): errors.append("missing demo_runs/research_matrix_v4/matrix_verification_report.json")
    if verification.get("valid") is not True:
        errors.append("matrix_verification_report.valid must be true")
    if verification.get("latex_compilation_status") != "compiled_verified":
        errors.append("matrix_verification_report.latex_compilation_status must be compiled_verified")
    total_calls = execution.get("total_provider_calls")
    if not isinstance(total_calls, int) or total_calls < 0 or total_calls > 9:
        errors.append("total provider calls must be an integer from 0 to 9")
    topic_call_sum = 0
    for topic in TOPICS:
        topic_dir = matrix / topic
        for filename in TOPIC_FILES:
            if not (topic_dir / filename).exists():
                errors.append(f"{topic}: missing {filename}")
        report = load_json(topic_dir / "execution_report.json", errors) if (topic_dir / "execution_report.json").exists() else {}
        if report.get("status") != "completed_pending_human_review":
            errors.append(f"{topic}: execution status is not completed_pending_human_review")
        run_manifest = load_json(topic_dir / "run_manifest.json", errors) if (topic_dir / "run_manifest.json").exists() else {}
        if run_manifest.get("latex_compilation_status") != "compiled_verified":
            errors.append(f"{topic}: run_manifest latex_compilation_status must be compiled_verified")
        topic_verification = load_json(topic_dir / "verification_report.json", errors) if (topic_dir / "verification_report.json").exists() else {}
        if topic_verification.get("valid") is not True:
            errors.append(f"{topic}: verification_report.valid must be true")
        calls = report.get("provider_calls")
        if not isinstance(calls, int) or calls < 0 or calls > 3:
            errors.append(f"{topic}: provider calls must be an integer from 0 to 3")
        else:
            topic_call_sum += calls
        if all((topic_dir / filename).exists() for filename in TOPIC_FILES):
            check_claim_ledger(topic_dir, errors)
        provenance_path = topic_dir / "provenance.json"
        if provenance_path.exists():
            provenance = load_json(provenance_path, errors)
            for rel, expected_hash in provenance.get("artifacts", {}).items():
                artifact = topic_dir / rel
                if not artifact.exists():
                    errors.append(f"{topic}: provenance artifact missing {rel}")
                elif sha256_file(artifact) != expected_hash:
                    errors.append(f"{topic}: provenance hash mismatch {rel}")

    if isinstance(total_calls, int) and topic_call_sum != total_calls:
        errors.append("topic provider call sum does not match total_provider_calls")
    if execution.get("status") != verification.get("status"):
        errors.append("matrix execution and verification statuses do not match")
    manifest_status = manifest.get("matrix_status", manifest.get("matrix_demo", {}).get("status"))
    if manifest_status != execution.get("status"):
        errors.append("manifest matrix status does not match execution report")

    result = {
        "structure_and_security_passed": not errors,
        "submission_ready": not errors,
        "errors": errors,
        "source_files": sum(1 for _ in iter_files()),
        "matrix_status": execution.get("status"),
        "latex_compilation_status": "compiled_verified",
        "pdf_paths": list(PDF_PATHS),
        "topics": {topic: load_json(matrix / topic / "execution_report.json", []).get("status", "missing") if (matrix / topic / "execution_report.json").exists() else "missing" for topic in TOPICS},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
