from __future__ import annotations

import json
from pathlib import Path

import pytest

from competition_runner.research_matrix import (
    ResearchMatrixError,
    parse_arxiv,
    parse_crossref,
    parse_openalex,
    load_matrix_config,
    run_local_benchmark,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "research_matrix_v3.json"


def test_matrix_config_has_exactly_three_topics():
    matrix = load_matrix_config(CONFIG)
    assert [item["topic_id"] for item in matrix["topics"]] == [
        "context-engineering", "memory-engine", "self-evolution"
    ]


def test_public_source_parsers_and_dedup_keys():
    openalex = parse_openalex({"results": [{
        "id": "https://openalex.org/W1", "title": "Agent memory",
        "publication_year": 2025,
        "authorships": [{"author": {"display_name": "A"}}],
        "primary_location": {"landing_page_url": "https://example.org/paper"},
    }]}, "RAW")
    crossref = parse_crossref({"message": {"items": [{
        "DOI": "10.1000/test", "title": ["Agent memory"],
        "author": [{"given": "A", "family": "B"}],
        "published": {"date-parts": [[2025]]},
        "URL": "https://doi.org/10.1000/test",
    }]}}, "RAW")
    arxiv = parse_arxiv("""<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'>
      <entry><id>https://arxiv.org/abs/2501.00001</id><title>Agent memory</title>
      <published>2025-01-01T00:00:00Z</published><summary>Memory abstract</summary>
      <author><name>A</name></author></entry></feed>""", "RAW")
    assert openalex[0]["source_id"] == "openalex:W1"
    assert crossref[0]["source_id"] == "doi:10.1000/test"
    assert arxiv[0]["source_id"] == "arxiv:2501.00001"
    assert all(item["content_sha256"] for item in openalex + crossref + arxiv)


def test_local_benchmark_is_reproducible(tmp_path):
    _, first, _ = run_local_benchmark("context-engineering", tmp_path / "a", 42)
    _, second, _ = run_local_benchmark("context-engineering", tmp_path / "b", 42)
    assert first["input_hash"] == second["input_hash"]
    assert first["reproducibility_token"] == second["reproducibility_token"]
    assert first["benchmark_kind"] == "pipeline_process_evidence_not_topic_scientific_result"
    assert first["arms"]["full_rail"]["blocked"] == 1


def test_invalid_call_budget_is_rejected(tmp_path):
    from competition_runner.research_matrix import run_matrix
    with pytest.raises(ResearchMatrixError, match="between 1 and 3"):
        run_matrix(CONFIG, ROOT / "config" / "providers.json", tmp_path / "out", tmp_path / "cache", "deepseek", True, True, True, 4, 9, 42)
