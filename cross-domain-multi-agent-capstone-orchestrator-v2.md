# ScoutSpark V2 — Tasks from Here Onward

**Version:** 2.0 · **Updated:** 5 October 2026 · **Status:** Working backlog  
**V2 task status:** use the checkbox column in this document; `TASKS.md` retains the demo-era checklist.  
**Background requirements:** [`cross-domain-multi-agent-capstone-orchestrator.md`](cross-domain-multi-agent-capstone-orchestrator.md)  
**Evidence and decisions:** dated reports under `evals/`, [`docs/orchestration.md`](docs/orchestration.md), and [`docs/decision_log.md`](docs/decision_log.md).

This document lists the remaining work based on the implemented MVP and current evaluations. Mark a task complete only after its “Done when” evidence is recorded. The original requirements document remains useful for product history; this V2 backlog governs forward work when the two differ.

## MVP release goal and priority

The capstone phase is over. The next goal is a dependable MVP release for external feedback. Prioritize consistent, valid, evidence-supported results and clear recovery from failures before adding workflow options. Consistency means stable behavior and result contracts for comparable runs; it does not require live search to return identical ideas every time.

| Release priority | Work | Tasks |
|---|---|---|
| 1. Establish the release boundary | Restrict each run to one interest area; define and measure end-to-end reliability on repeated, matched requests. | V2-01, V2-02 |
| 2a. Make failures visible and contained | Consistent failure handling, accurate stage counts and shortfall reasons, and bounded recovery. | V2-03, V2-04, V2-05 |
| 2b. Independently evaluate Scout | Measure request fit, structure, uniqueness, evidence support, and count accuracy. | V2-06 |
| 2c. Independently evaluate Library | Measure evidence relevance and coverage, citation integrity, deduplication, and gap reporting. | V2-07 |
| 2d. Independently evaluate Critic | Measure scoring consistency, evidence relevance, gate decisions, citation validity, and calibration. | V2-08 |
| 2e. Independently evaluate proposal writing | Measure completeness, actionability, factual support, unknowns, and alignment to verified evidence. | V2-09 |
| 3. Improve result completeness and evidence | Scout over-generation and correction loops, Library evidence coverage, Critic scoring counts, verifier accuracy, and Critic evidence policy. | V2-10–V2-13, V2-14, V2-15 |
| 4. Improve yield using measured evidence | Find and address the biggest observed loss points without weakening gates or evidence requirements. | V2-16 |
| 5. Expand user options after reliability is demonstrated | User-approved feedback, Critic re-evaluation, non-finalist proposals, and usage guidance. | V2-17, V2-18, V2-19, V2-20 |

This release sequence supersedes the earlier P1 order below. The capstone demo and human-review tasks are retained as follow-up evidence work, not MVP release blockers.

## Current baseline

ScoutSpark already has the main research workflow, Simple and Advanced configuration, preview-before-run, sequential and parallel modes, scoring and hard gates, citation checks, budgets, tracing, checkpoints, bounded recovery, and an offline demo. Defaults are five requested candidates and two displayed score finalists.

Offline results use synthetic sources and simulated model behavior. They do not establish live research quality. Real-model evaluations are small and have shown proposal-yield limitations. Human review of the controlled proposals remains pending; the capstone demo is recorded. Use dated reports for exact measurements and limitations.

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

## Follow-up — Capstone evidence work (not MVP release blockers)

| Status | ID | Task | Done when |
|---|---|---|---|
| [ ] | V2-21 | **Complete independent human review.** Score the controlled proposals using the existing sequential and parallel review sheets. Follow the blind-review protocol where specified. | Review sheets are complete; agreement is calculated only when the sample supports it; results, sample size, and limitations are added to the evaluation report. LLM-judge scores are not presented as human scores. |
| [X] | V2-22 | **Record the MVP demo.** Follow `docs/demo_recording_guide.md`; show the real workflow and keep the synthetic-data label visible. | Recording and notes are saved. Measured yield and sample sizes are presented with their limitations, and synthetic demo content is not represented as live evidence. |

## P1 — Improve reliability and explain shortfalls

Task IDs follow the MVP release priority sequence above.

| Status | ID | Task | Done when |
|---|---|---|---|
| [X] | V2-01 | **Limit each run to one interest area.** Accept at most one interest area per run across GUI, CLI, request/configuration models, and resume flows. Users who want to explore multiple areas can run them separately. | Inputs containing multiple interest areas are rejected with a clear message before provider calls begin. Single-area inputs pass through unchanged; validation behavior is consistent across GUI, CLI, and resumed runs. |
| [X] | V2-02 | **Measure end-to-end reliability for comparable runs.** Establish a repeatable evaluation using fixed requests, source snapshots, configuration, model/prompt versions, and budgets. Measure valid-result completion, count accuracy, citation/evidence support, score/rank stability, and clear shortfall reporting across repeated runs. | A report defines release thresholds before measuring, includes sample sizes and variance, separates expected live-search variation from defects, and records failures by stage. The same evaluation can be rerun after changes; no reliability claim rests on a single successful run. |
| [X] | V2-03 | **Make failure handling consistent.** Cover interpretation, preflight, adapters, workers, orchestration, finalization, checkpoint/resume, and UI. Include optional-provider failure, adapter over-returns, required-branch failure, and UI resume. | `docs/failure_handling.md` records stage behavior. Offline fault tests cover required-branch cancellation, optional-provider failure, adapter over-return, both scheduling modes, sanitized failure details, checkpoint resume against an uninterrupted run, and frozen replay. Focused tests pass. |
| [X] | V2-04 | **Explain count shortfalls by stage.** Add machine-readable and user-readable counts, requested targets, and observed reason codes. Cover model underproduction, invalid output, deduplication, missing sources, provider/branch failures, budgets/time, assessment failures, gates, drafting/verification failures, and exhausted eligible candidates. Allow multiple causes; report unknown when the trace cannot establish one. | Diagnostics preserve stage-specific counts and multiple supported causes. Offline tests cover the shortfall categories, UI rendering matches serialized counts, and a hard-gate regression proves gate rejection is not reported as Scout-generation failure. |
| [X] | V2-05 | **Correct invalid Scout output once.** Send safe field/type hints for one bounded correction attempt. Retain valid unique ideas already received; count the correction against the same budget; do not reveal raw invalid output. | Focused tests cover malformed output, safe schema hints, valid work retained, duplicate and unsupported candidates, successful/failed one-shot correction, budget exhaustion, and output counters. A failed correction returns a measured partial result. |
| [X] | V2-10 | **Over-generate candidates in Scout.** Target 50% more unique, valid candidate ideas than the user-facing candidate-result count: `ceil(1.5 × requested count)`. For a request to show five candidate results, Scout's internal target is eight. Keep the visible result count unchanged; keep it distinct from `finalist_count`. | Implemented internal `ceil(1.5 × requested)` target and bounded batches; requests remain unchanged and actual target/shortfall are recorded. Covered for exact target, partial target and hard cap. |
| [X] | V2-11 | **Make Scout generation self-correcting.** After each batch, identify the measured deficit (too few valid ideas, invalid fields, duplicates, weak request fit, or missing supporting sources) and use safe, concise feedback for the next bounded batch. | Implemented safe deficit/rejection feedback, preserves valid ideas, one malformed-response correction, retry on empty/invalid batches and early stop after repeated no progress. Shared budgets and `max_batches` bound attempts; invalid raw output is not surfaced. |
| [X] | V2-12 | **Make Library evidence collection self-correcting.** Compare collected evidence with configured minimum counts, required source types/tiers, and coverage needs. Run another targeted collection pass only while useful and within remaining shared limits. | Implemented bounded targeted recovery queries, query accounting, usable-source/type counts, and explicit missing-coverage warnings. Source-coverage tests cover recovery, unavailable coverage and exhausted query caps. |
| [X] | V2-13 | **Return the configured number of Critic results when available.** Assess all accepted candidates in the internal pool, rank deterministically, and return the requested number of user-facing scored results when the pool supports it. If fewer valid candidates or assessments exist, return the available results with a shortfall reason. | Critic retains the full internal ranking; GUI scorecards show up to the requested result count and explain shortfalls. Stable ties and per-candidate assessment failures are covered; gate state remains visible and separate from proposal eligibility. |
| [ ] | V2-14 | **Measure verifier accuracy.** Expand held-out and adversarial evaluation; human-review false rejections and unsupported claims, including data/access assumptions. | A report separates false acceptance from false rejection, gives sample counts and adjudication, and uses an appropriate confusion analysis. Any policy change has an evidence-based decision; model verification is still described as a safeguard. |
| [ ] | V2-15 | **Review Critic evidence and citation policy.** Trace Scout claims through Library chunks, Critic context and citations, drafting, and final audit. Compare rejecting an assessment with preserving a caveated score when citations are invalid or missing. Test whether bounded retrieve-more-and-reassess fixes observed gaps enough to justify cost. | A decision is recorded in `docs/decision_log.md`, supported by frozen-case results for citation integrity, unsupported claims, false rejection, token/cost impact, and both scheduling modes. Implement only after the decision. |
| [ ] | V2-16 | **Improve verified-proposal yield across domains.** Find where ideas are lost: discovery, sources, assessment, gates, data suitability, drafting, citations, or verification. Improve yield without relaxing evidence, privacy, or user constraints. | A dated, reproducible comparison uses matched requests, snapshots, prompts, models, rubrics, and limits. It reports all stage counts, failure reasons, latency, token use, and estimated cost. No universal-quality claim is made from a small sample. |
| [ ] | V2-17 | **Add user-approved bounded feedback.** Show the proposed extra work and budget impact, then ask before spending. Preserve earlier results; assess alternatives under the same evidence, rubric, and gates. | UI tests cover approve/decline. Offline cases cover budget exhaustion, duplicate alternatives, and preservation of prior results. A declined round changes nothing; any live evaluation accounts for extra calls, time, and cost. |
| [X] | V2-18 | **Allow user-requested Critic re-evaluation.** Let the user review changed scoring criteria and configurable project gates, then re-evaluate and rerank existing candidates against the recorded evidence. Version each configuration and result so the previous assessment remains auditable. | GUI and CLI previews show resolved criteria/gates and bounded remaining budget before explicit execution. Versioned records preserve original assessments and citations; project gates are additive and operator/privacy/safety gates remain immutable. |
| [X] | V2-19 | **Offer proposals for non-finalist candidates.** Add a GUI action and CLI selection option to generate a detailed proposal for an idea outside the default finalist set (for example, the other three ideas when five scorecards are shown and two are featured). | GUI/CLI selected proposals use existing evidence, gate checks, shared remaining budgets and proposal verification. A failed verification is retained with its reason; failed-gate ideas are ineligible. |
| [X] | V2-20 | **Add “getting useful results” guidance.** Give practical examples of focused requests, relevant source selection, simpler search presets, cost controls, and configuration preview. Present tips as suggestions, not quality or cost guarantees. | Added UI tips and help documentation reflecting existing request/source/preset/preview controls without promising results. |

## Evaluation tasks and optional improvements

| Status | ID | Task | Done when |
|---|---|---|---|
| [ ] | V2-06 | **Independently evaluate Scout.** Score held-out Scout outputs for request/constraint fit, valid structure, uniqueness/diversity, evidence support, and count/shortfall accuracy. | Held-out offline run artifacts and blind review sheets are prepared in `evals/scout_quality/heldout_v2_2026-10-05.md`. Complete the five-candidate human review and record its summary before marking done. |
| [ ] | V2-07 | **Independently evaluate Library.** Assess source relevance, coverage of required types/tiers, metadata and citation integrity, deduplication, and whether reported evidence gaps are accurate. | Held-out cases include domains and provider failures. Results report per-metric outcomes and sample sizes; Library's own completion message is not used as its sole quality score. |
| [ ] | V2-08 | **Independently evaluate Critic.** Measure score consistency, evidence relevance, gate decisions, citation validity, and calibration against blinded human/reference judgments. | A reproducible held-out evaluation reports false acceptances/rejections and sample sizes. Critic does not grade its own assessments; an LLM judge is supplementary only. |
| [ ] | V2-09 | **Independently evaluate proposal writing.** Assess completeness, actionability, support for factual claims, explicit unknowns, and consistency with the selected idea and verified evidence. | Blind human/reference review is reported separately from model-verifier outcomes, with sample size and unsupported-claim rates. Writing and verification are measured as separate stages. |
| [ ] | V2-23 | **Compare GitHub GraphQL with REST.** Use identical fixed repository queries. Measure usable unique sources, request/point use, latency, response size, and rate-limit/time-out failures. GraphQL is not a rate-limit bypass. | Reproducible results and a decision note use current official GitHub guidance. REST fallback and rate-aware backoff remain unless evidence supports a change. Credentials are absent from reports. |
| [ ] | V2-24 | **Evaluate semantic retrieval only if the baseline misses relevant evidence.** Start with held-out misses under the current lexical/TF-IDF hybrid; compare embeddings only when misses show semantic mismatch. | A decision records retrieval quality, latency, token use, and embedding cost. Adopt only if measured quality gain justifies added cost and complexity; otherwise retain the current baseline. |
| [ ] | V2-25 | **Design request-specific Critic criteria.** Keep the demo rubric stable while designing user-reviewed, versioned request-specific criteria and testing consistency against the fixed rubric. | Reviewed design, versioned schema and precedence rules, and held-out consistency results exist before enabling the feature. Weights never weaken hard gates or citation rules. |

V2-06–V2-09 evaluation code, current held-out offline runs, mechanical reports,
and blind review sheets are prepared; see
`evals/worker_quality/heldout_v2_2026-10-05.md`. The independent human or
reference ratings required by their acceptance criteria are still pending, so
these four status boxes remain open.

## P3 — Ongoing maintainability

| Status | ID | Task | Done when |
|---|---|---|---|
| [ ] | V2-26 | **Keep module boundaries cohesive.** Refactor only to address a concrete maintenance need. Avoid circular imports and broad rename/signature churn. | A narrow rationale is recorded, behavior is covered, public imports/docs are updated, and repository checks pass. |
| [ ] | V2-27 | **Keep code comments and docs useful.** Add concise public API docstrings and comments for non-obvious invariants, fallbacks, and trade-offs. | Relevant documentation matches actual behavior, adds no unsupported claims, and avoids comments that merely repeat code. |
| [ ] | V2-28 | **Add budget-aware model routing.** Choose a model per stage using task needs, configured quality/cost preferences, and the run's remaining budget. Keep routing decisions inspectable and allow fixed-model mode for reproducible comparisons. | Controlled evaluations compare quality, latency, and cost against a fixed-model baseline. Routing never exceeds user limits, records selected model and rationale without sensitive prompt content, and can be disabled or overridden. |
| [ ] | V2-29 | **Support pluggable LLM providers and models.** Replace OpenAI-specific assumptions in application assembly with a stable provider interface and configurable model IDs, while preserving structured-output validation, retries, usage accounting, and budget enforcement. | At least two provider adapters pass the same contract suite for valid/invalid responses, errors, usage, and budget stops. Provider-specific differences are documented; provider selection is explicit and secrets stay out of logs and traces. |

## Safeguards for every task

- Hard gates and mandatory user constraints remain in force; scores cannot offset a failed gate.
- Candidate count, score-finalist count, and verified-proposal count remain separate.
- Preserve useful partial results and report actual counts and reasons.
- Treat retrieved content as untrusted; never execute it. Keep credentials out of prompts, traces, logs, fixtures, reports, and generated artifacts.
- Charge retries, corrections, recovery, and feedback to the same configured budgets.
- Label synthetic fixtures and exclude them from claims about real-world research quality.
- Keep sequential/parallel comparisons controlled: same requests, source snapshots, prompts, models, rubric, and limits.
- Do not run paid-provider experiments just to fill a report. Define the question and budget before a paid run.

## V2 completion

The MVP release priorities are complete when agreed reliability thresholds are met on repeatable evaluations; count shortfalls can be traced without confusing hard gates and candidate generation; agent output and recovery are independently evaluated; and no critical failure mode silently produces misleading results. Later feature work and optional provider, retrieval, or rubric changes can follow with controlled evidence. P3 practices continue as normal maintenance.

Offline completion rates, small paid samples, high scores, and model-verifier verdicts alone do not establish reliable real-world proposal quality.
