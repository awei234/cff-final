# Initial Submission Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reviewable `Prototype` preliminary-round submission tree without modifying the source `feature` worktree or producing the final ZIP.

**Architecture:** Treat the original work copy as a read-only source and assemble an allowlisted package under `06_初赛提交包_待审核/Prototype`. A package-level verifier distinguishes review-stage readiness from final readiness, while evidence and source-state manifests preserve provenance.

**Tech Stack:** Python 3, pytest, Git, JSON, Markdown, SHA-256.

**Spec:** Conversation-approved submission layout and official preliminary-round directory screenshots.

## Global Constraints

- Never modify `01_比赛提交包`, `03_服务器源码快照`, or the original `feature` worktree.
- Do not create a final ZIP.
- Create empty `paper/` and `AgenticReviewer/` directories; the user will later provide `paper.pdf` and `paperReview-AccessToken.txt`.
- Exclude runtime state, API keys, sessions, virtual environments, dependencies, caches, logs, bytecode, and historical/smoke runs.
- Use `jit_comparison_v2_final` as the canonical four-arm, three-seed JIT evidence.

## Review Focus

- Empty required external-artifact directories must pass review stage but fail final stage.
- A real secret or runtime session copied into the package must fail validation.
- Stale v1 JIT or pending-review claims must not be presented as canonical results.
- Checksums must detect any post-assembly file change and must not self-hash.
- Source state must capture the feature HEAD and the selectively integrated dirty files.

---

### Task 1: Reproducible package assembler and stage verifier

Create tested allowlist/exclusion logic, review/final stage validation, and source-state capture.

### Task 2: Assemble source, evidence, and Harness assets

Build the review tree from the original work copy, retaining only selected current artifacts.

### Task 3: Complete submission documentation and manifests

Create contribution, resource, submission, README, architecture, module-call, innovation, and manifest material aligned to the official layout.

### Task 4: Full verification and review commit

Run project tests, authorized-release and JIT verification, secret/exclusion scans, checksum verification, and commit the review package on `codex/submission-review`.
