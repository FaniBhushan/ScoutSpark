# ScoutSpark V2 — Product context and safeguards

**Version:** 2.0 · **Updated:** 9 October 2026 · **Status:** Preview under owner review
**Single task tracker:** [`TASKS.md`](TASKS.md) contains every pending and future task, including acceptance criteria. Do not maintain task status in this document.
**Background requirements:** [`cross-domain-multi-agent-capstone-orchestrator.md`](cross-domain-multi-agent-capstone-orchestrator.md)
**Evidence and decisions:** dated reports under `evals/`, [`docs/orchestration.md`](docs/orchestration.md), and [`docs/decision_log.md`](docs/decision_log.md).

This document keeps product context, result-count definitions, and safeguards. The preview is for review and feedback; it is not the release announcement. The owner will review the local changes before deciding whether and when to release.

## Product goal

Build a dependable research workflow for external feedback. Prioritize valid, evidence-supported results and clear recovery from failures before adding workflow options. Comparable runs should have stable behavior and result contracts; live search is allowed to return different ideas.

## Current baseline

ScoutSpark already has the main research workflow, Simple and Advanced configuration, preview-before-run, sequential and parallel modes, scoring and hard gates, citation checks, budgets, tracing, checkpoints, bounded recovery, and an offline demo. Defaults are five requested candidates and two displayed score finalists.

Offline results use synthetic sources and simulated model behavior. They do not establish live research quality. Real-model evaluations are small and have shown proposal-yield limitations. Human review of the controlled proposals and the short demo recording remain pending. Use dated reports for exact measurements and limitations.

## Keep these counts separate

| Count | Meaning | Can a hard gate lower it? |
|---|---|---|
| Generated candidates | Ideas Scout returns before validation and deduplication | No |
| Accepted candidates | Unique, valid ideas kept after validation and join checks | No |
| Scored candidates | Accepted ideas assessed by Critic | No |
| Score finalists | Highest weighted-score ideas shown for review; a finalist may have failed a gate | No |
| Verified proposals | Detailed proposals that pass applicable gates and evidence checks | Yes |

A hard gate can explain why fewer **verified proposals** are available. It must not be used to explain why Scout generated too few candidates. When any requested count is missed, keep completed work, report actual counts by stage, and explain known causes without fabricating an explanation or weakening safeguards.

For Scout's 50% over-generation target, the reference count is the requested number of user-facing candidate scorecards (`desired_candidate_count`), not the smaller number of featured score finalists (`finalist_count`). The extra candidates form an internal pool for validation, deduplication, and ranking; they do not increase the number shown by default.

## Safeguards for every task

- Hard gates and mandatory user constraints remain in force; scores cannot offset a failed gate.
- Candidate count, score-finalist count, and verified-proposal count remain separate.
- Preserve useful partial results and report actual counts and reasons.
- Treat retrieved content as untrusted; never execute it. Keep credentials out of prompts, traces, logs, fixtures, reports, and generated artifacts.
- Charge retries, corrections, recovery, and feedback to the same configured budgets.
- Label synthetic fixtures and exclude them from claims about real-world research quality.
- Keep sequential/parallel comparisons controlled: same requests, source snapshots, prompts, models, rubric, and limits.
- Do not run paid-provider experiments just to fill a report. Define the question and budget before a paid run.

## Completion standard

Release readiness requires agreed reliability thresholds on repeatable evaluations, traceable count shortfalls, independent evaluation of agent outputs and recovery, and no critical failure mode that silently produces misleading results. Later features and optional provider, retrieval, or rubric changes follow only when their corresponding evaluation supports them.

Offline completion rates, small paid samples, high scores, and model-verifier verdicts alone do not establish reliable real-world proposal quality. The complete pending and future work list is maintained in [`TASKS.md`](TASKS.md).
