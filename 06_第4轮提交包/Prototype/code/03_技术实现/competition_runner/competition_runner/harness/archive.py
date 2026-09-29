import json
from hashlib import sha256
from pathlib import Path


def archive_run(output_dir: Path, *, manifest: dict[str, object], validation: dict[str, object], metrics: dict[str, object], evidence: list[dict[str, object]]) -> Path:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    payload = {"manifest": manifest, "validation": validation, "metrics": metrics, "evidence": evidence}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["archive_sha256"] = sha256(canonical.encode("utf-8")).hexdigest()
    (output / "harness_archive.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
