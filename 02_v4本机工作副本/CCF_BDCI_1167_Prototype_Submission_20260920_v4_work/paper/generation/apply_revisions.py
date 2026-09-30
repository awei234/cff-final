"""Apply review-driven revisions to paper/paper.docx.

Revisions are anchored to paragraph indices captured BEFORE any insertion,
so insertion order is independent of index shifting.

Design rules (per 论文修改后同步更新注意事项.md):
  - no new data / experiments / results / conclusions are introduced;
  - all added text is clarification, positioning, limitation or future work;
  - new references are taken verbatim (arXiv ids) from the reviewer's report;
  - the paper must stay within 15 pages (the review site only reads the first 15),
    so every inserted block is kept deliberately concise.

Usage: python apply_revisions.py
"""
import copy
import io
import json
import os

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
DOCX = os.path.join(HERE, "..", "paper.docx")


def _first_run(p_el):
    runs = p_el.findall(qn("w:r"))
    return runs[0] if runs else None


def set_text(p_el, text):
    """Keep the paragraph's first run (and its formatting), replace its text."""
    runs = p_el.findall(qn("w:r"))
    for r in runs[1:]:
        p_el.remove(r)
    r = _first_run(p_el)
    if r is None:
        return
    for child in list(r):
        if child.tag in (qn("w:t"), qn("w:tab"), qn("w:br")):
            r.remove(child)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)


def _el(x):
    """Accept either a python-docx Paragraph or a raw CT_P element."""
    return x._p if hasattr(x, "_p") else x


def clone_after(anchor, src, text):
    new_p = copy.deepcopy(src._p)
    set_text(new_p, text)
    _el(anchor).addnext(new_p)
    return new_p


def append_run(p, text):
    r = _first_run(p._p)
    if r is None:
        return
    new_r = copy.deepcopy(r)
    for child in list(new_r):
        if child.tag in (qn("w:t"), qn("w:tab"), qn("w:br")):
            new_r.remove(child)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    new_r.append(t)
    p._p.append(new_r)


def main():
    doc = Document(os.path.abspath(DOCX))
    paras = doc.paragraphs

    # --- capture anchors before any modification ---
    a_related = paras[23]      # 1.2.4 last paragraph
    a_head_src = paras[22]     # "1.2.4 Critical assessment" (heading style)
    a_body_src = paras[23]     # body paragraph style
    a_32 = paras[74]           # 3.2 equal-marginal condition
    a_35 = paras[95]           # 3.5 write-gate thresholds
    a_37 = paras[120]          # 3.7 triple gate output
    a_39 = paras[133]          # 3.9 arbitration benefit
    a_41 = paras[140]          # 4.1 datasets
    a_42 = paras[145]          # 4.2 circularity disclosure (append)
    a_52 = paras[190]          # 5.2 measurement limitation
    a_53 = paras[193]          # 5.3 last future-work item
    a_ref = paras[237]         # [34] last reference
    ref_src = paras[237]

    log = []

    # (1) new related-work subsection 1.2.5 (single compact paragraph)
    h = clone_after(a_related, a_head_src,
                    "1.2.5 Verification-centric, budget-aware and modular-context baselines")
    clone_after(h, a_body_src,
        "Several recent lines are adjacent to our design. Claim- and entity-level verification is pursued by "
        "Chain-of-Verification [23] and by recent verifiers such as MedRAGChecker [35] and EAEV [36]; CGA-Agent differs "
        "in that verification is a gate inside the control loop and every surviving claim keeps a provenance-bound trace. "
        "Entropy- and utility-guided control, e.g. entropy-guided branching [37] and utility-guided orchestration [38], is "
        "conceptually related to our planning-entropy and tool-utility signals. PACMS [39] formalises token-budget "
        "allocation and submodular context selection, of which our slot allocator is a typed instance, and EvoGraph-Mem "
        "[40] maintains evidence-based graph memory complementary to our write-gate. These works are cited for positioning "
        "only; head-to-head comparisons are left to Sections 5.2 and 5.3.")
    log.append({"anchor": 23, "edit": "insert 1.2.5 (heading + 1 compact paragraph)"})

    # (2) 3.2 operational definitions / submodularity caveat
    clone_after(a_32, a_body_src,
        "Two clarifications delimit this derivation. The coverage gain G_j and the redundancy term R_j are not analytic: "
        "G_j is estimated by a coverage proxy over task-relevant key facts and R_j by pairwise semantic overlap, both using "
        "the retrieval encoder. The (1 - 1/e) guarantee presumes submodularity of the net gain, which we assume rather than "
        "prove, so Eq. (8) is a design target whose empirical satisfaction is not claimed here; a learned estimator and an "
        "empirical submodularity test are left to future work.")
    log.append({"anchor": 74, "edit": "insert 3.2 operational-definition caveat"})

    # (3) 3.5 information-gain estimation caveat
    clone_after(a_35, a_body_src,
        "The information-gain term of Eq. (12) is the least directly observable quantity here. It is approximated from "
        "historical statistics rather than computed exactly: a candidate is scored by a lightweight utility judge "
        "conditioned on the recent task stream and calibrated against observed reuse. We do not report an independent "
        "estimator for H(Y|M), nor the gate's sensitivity to this approximation; the gate is a heuristic quality filter, "
        "not a certified information-theoretic optimum.")
    log.append({"anchor": 95, "edit": "insert 3.5 information-gain caveat"})

    # (4) 3.7 claim-extraction quality caveat
    clone_after(a_37, a_body_src,
        "Claim-extraction quality is a precondition for every downstream trustworthiness metric and is not independently "
        "validated in this version. Because EC, UCR and MR are computed over the claims the extractor produces, extraction "
        "error propagates into them directly. We therefore report extraction fidelity as a known open item and plan a "
        "human-annotated audit of a stratified subset (Section 5.3).")
    log.append({"anchor": 120, "edit": "insert 3.7 claim-extraction-quality caveat"})

    # (5) 3.9 arbitration operational details
    clone_after(a_39, a_body_src,
        "Two operational details are worth stating. Dissent is detected as divergence in the per-expert entailment scores "
        "bound to the same claim: when weighted support and weighted opposition both exceed their activation thresholds, "
        "the claim is routed to arbitration rather than resolved by aggregation. Semantically equivalent but textually "
        "different claims are first merged by embedding similarity so that paraphrases do not cancel. Behaviour as a "
        "function of expert count N and of the reliability estimator is not characterised here.")
    log.append({"anchor": 133, "edit": "insert 3.9 arbitration operational details"})

    # (6) 4.1 CE-Bench construction / release note
    clone_after(a_41, a_body_src,
        "CE-Bench annotates a mixed set of multi-hop and tool-use items with the evidence spans necessary and sufficient "
        "for a correct answer, and pairs each item with the distractors used in Section 4.6. Full construction details, "
        "annotation guidelines and inter-annotator agreement are not reported here; releasing the dataset and its protocol "
        "is stated as future work (Section 5.3).")
    log.append({"anchor": 140, "edit": "insert 4.1 CE-Bench construction note"})

    # (7) 4.2 append explicit circularity disclosure
    append_run(a_42,
        " Because the same verifier both produces and scores this trace, the three metrics carry a circularity risk: they "
        "measure the guardrail's internal consistency rather than agreement with an external gold standard. We therefore "
        "treat them as process-evidence indicators, not as independent evidence of trustworthiness.")
    log.append({"anchor": 145, "edit": "append 4.2 circularity disclosure"})

    # (8) 5.2 additional evaluation-level limitations
    clone_after(a_52, a_body_src,
        "Two evaluation-level limitations qualify our conclusions. (a) Metric circularity: EC, UCR and MR derive from the "
        "guardrail's own trace, so part of the measured trustworthiness is a property of the verifier rather than of "
        "real-world reliability. (b) Baseline coverage: we compare against six capability-oriented systems but not against "
        "the closest verification-centric and control-theoretic baselines (CoVe [23], EAEV [36], MedRAGChecker [35], "
        "entropy-guided branching [37], PACMS [39]), which bounds how strongly the guardrail and structured context can be "
        "attributed. Both gaps are addressed in Section 5.3.")
    log.append({"anchor": 190, "edit": "insert 5.2 evaluation-level limitations"})

    # (9) 5.3 additional future work
    clone_after(a_53, a_body_src,
        "(vi) Human-audited metrics: a human audit on a stratified subset reporting claim-extraction precision and recall, "
        "provenance-decision correctness, and the induced change in EC/UCR/MR. (vii) Verification-centric baselines: under "
        "a shared evidence pool, compare the guardrail with CoVe [23] and a recent claim- or entity-level verifier "
        "(EAEV [36], MedRAGChecker [35]), and compare planning with entropy-guided branching [37]. (viii) CE-Bench release: "
        "publish the dataset, its necessary-evidence annotations, distractors and annotation protocol, with code.")
    log.append({"anchor": 193, "edit": "insert 5.3 additional future work"})

    # (10) new references [35]-[40]
    new_refs = [
        "[35] MedRAGChecker. arXiv:2601.06519, 2026.",
        "[36] EAEV: evidence-aligned entity verification. arXiv:2609.08267, 2026.",
        "[37] Entropy-guided branching (EGB). arXiv:2604.12126, 2026.",
        "[38] Utility-guided orchestration. arXiv:2603.19896, 2026.",
        "[39] PACMS: token-budget and submodular context selection. arXiv:2606.20047, 2026.",
        "[40] EvoGraph-Mem: evidence-based graph-level memory maintenance. arXiv:2608.11248, 2026.",
    ]
    anchor = a_ref
    for ref in new_refs:
        anchor = clone_after(anchor, ref_src, ref)
    log.append({"anchor": 237, "edit": "append references [35]-[40]"})

    doc.save(os.path.abspath(DOCX))

    with io.open(os.path.join(HERE, "revision_log.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=2)
    print("applied", len(log), "edit groups ->", os.path.abspath(DOCX))


if __name__ == "__main__":
    main()
