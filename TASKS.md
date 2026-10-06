# ScoutSpark task tracker

This file tracks current demo readiness and MVP progress. The forward-looking
requirements and prioritized work are in
[cross-domain-multi-agent-capstone-orchestrator-v2.md](cross-domain-multi-agent-capstone-orchestrator-v2.md).
Detailed implementation history and measurements are linked below.

## Demo submission — 27 September 2026

- [x] Show five candidate ideas by default and two configurable score finalists.
      Rank by weighted score; show failed-gate reasons and compact scorecards for
      other ideas. A finalist scorecard is not a claim that its detailed proposal
      passed gates or evidence verification.
- [x] Verify the offline UI and pipeline. The default three-domain offline suite
      passed 3/3 cases and returned 9/9 synthetic proposals; 223 unit tests passed.
- [x] Replay the score-selection policy against six saved model-evaluated cases:
      two score finalists appeared in all six; four of twelve selections had gate
      warnings. This replay made no model or search calls and does not assess
      proposal quality.
- [x] Record controlled quantitative and blind LLM-judge results in
      `evals/demo_submission_2026-09-27.md`.
- [ ] Independently human-score the three saved controlled proposals. Fill the
      two review sheets below, then run the agreement analysis described in the
      evaluation report. Do not infer human scores from the LLM judge.
      - `evals/reports/2026-09-27-controlled-sequential/human_scores.csv`
      - `evals/reports/2026-09-27-controlled-parallel/human_scores.csv`
- [ ] Record the short demo using `docs/demo_recording_guide.md`. Label frozen
      evidence and offline model responses as synthetic; present the measured
      pipeline yield and small judge sample with their limitations.

The matched paid runs returned 1/9 proposals sequentially and 2/9 in parallel.
The blind LLM judge scored three proposals (n=3); human ratings are still
pending. See the [submission report](evals/demo_submission_2026-09-27.md) for
metrics, costs, reproduction commands, and limitations. No new paid experiment
is needed to complete the listed human-review task.

## Completed implementation

- Validated contracts and the Scout, Library, Critic, orchestration, retrieval,
  source adapters, proposal writing, citations, and run-scoped budgets.
- Shared preflight configuration, prompt interpretation, Simple and Advanced UI,
  editable preview, CLI, upload handling, and privacy/input-output guardrails.
- Run tracing, checkpoints, recovery, frozen-source evaluations, quantitative
  pipeline metrics, and an opt-in LLM-as-judge evaluator.
- Deadline scorecards and deterministic offline evaluation. See
  [orchestration](docs/orchestration.md), [candidate scoring](docs/candidate_scoring.md),
  and the [decision log](docs/decision_log.md).

## Current MVP reliability implementation

V2-01 through V2-05 and V2-10 through V2-13, V2-18 through V2-20 are implemented
with focused offline coverage. V2-01 enforces
the single-area boundary at Pydantic request validation, GUI preview, CLI
configuration, and prepared-run revalidation before providers execute. V2-02 adds
preregistered thresholds and a repeatable frozen-source reliability runner. Its
10-run offline report is `evals/reports/reliability-v2-02-final/summary.md`: it
reports perfect repeatability for most checks but fails candidate-count attainment
(1 returned against 5 requested). This is a synthetic harness result, not a live
reliability claim. The full test suite passes (261 tests), and evaluation fixtures
validate successfully. V2-06 has two
held-out offline runs and blind review sheets prepared, but its candidate-level
human ratings are still pending; see
`evals/scout_quality/heldout_v2_2026-10-05.md`.

V2-06–V2-09 now have current held-out offline runs, mechanical audits, blind
review sheets, and independent scoring commands. Library also has an injected
provider-failure replay; Critic has a matched sequential/parallel consistency
comparison. Their human/reference quality ratings remain pending, so these
four evaluation tasks are not marked complete. See
`evals/worker_quality/heldout_v2_2026-10-05.md`.

V2-10–V2-13 add bounded Scout over-generation and correction, Library evidence
coverage recovery and accounting, and configured-count Critic scorecards.
V2-18–V2-19 add previewed, versioned Critic re-evaluation and user-selected
non-finalist proposals in the GUI and CLI. V2-20 adds result-quality and cost
guidance in the UI and [help docs](docs/getting-useful-results.md). V2-14–V2-17
remain pending.

### Completed in this implementation

- [x] V2-10 — Scout over-generates to `ceil(1.5 × requested count)`.
- [x] V2-11 — Scout corrects measured candidate shortfalls within bounded batches.
- [x] V2-12 — Library retries evidence collection for missing coverage within shared limits.
- [x] V2-13 — Critic shows the configured number of scored results when available.
- [x] V2-18 — GUI and CLI support versioned Critic re-evaluation.
- [x] V2-19 — GUI and CLI can request a verified non-finalist proposal.
- [x] V2-20 — UI and help docs include practical result and cost guidance.

## Further improvements

- [x] Add concise, practical “getting the best results” guidance to the UI or
      help docs. Suggest focused requests (for example, one interest area per
      run, with a clear problem and constraints) and explain cost controls such
      as selecting only relevant sources, using a simpler search preset, and
      previewing the configuration before a live run. Present these as useful
      tips, not guarantees of quality or cost.
- [ ] Improve verified proposal yield across domains. Current runs do not prove
      that every domain can produce a gate-passing, evidence-verified proposal.
      Preserve explicit failure reasons; never invent evidence to fill a slot.
- [ ] Add a user-triggered, bounded feedback round within the same run. Preserve
      earlier results, ask before spending more of the shared budget, and score
      alternatives with the same rubric and evidence rules.
- [ ] Improve verifier accuracy with larger held-out and adversarial evaluations;
      review false rejections and unsupported claims with human ratings.
- [ ] Review the Critic evidence-and-assessment design. Trace how Scout ideas,
      Library's run-scoped in-memory chunks, Critic context selection, and
      source/chunk citations fit together. Compare safer ways to ground judgments
      and validate citations; determine whether invalid or missing citations
      should invalidate a whole assessment or instead be treated as unsupported
      evidence while preserving a clearly caveated score. Evaluate whether a
      bounded retrieve-more-and-reassess loop addresses actual retrieval gaps or
      would only add cost without fixing citation mismatches. Record the design
      decision and validate it on frozen cases before implementation.
- [ ] Make recovery-first behavior consistent across interpretation, planning,
      adapters, workers, orchestration, and UI. Cover optional failures,
      adapter over-returns, UI resume, and cross-stage fault recovery.
- [x] Add a bounded Scout response-correction loop for schema-invalid model
      output. The current smaller-batch retry can receive safe field/type hints;
      extend this into one explicit correction attempt, keep any valid candidates
      already produced, and report a useful partial result if correction still
      fails. Keep raw model output out of traces/UI, charge retries to the same
      run budget, and stop after the configured attempt limit.
- [ ] Evaluate a GitHub GraphQL adapter against the current REST repository
      search. On identical queries, measure unique usable repositories,
      request/point consumption, latency, response size, and rate-limit errors.
      GraphQL has a separate point budget and may reduce calls through precise
      field selection, but it does not bypass GitHub's primary or secondary
      limits. Retain REST fallback and rate-limit-aware backoff.
- [ ] Compare semantic embeddings with the lexical/TF-IDF baseline only if held-out
      retrieval evaluation shows missed relevant evidence. Measure quality,
      latency, and embedding cost before adopting a vector index.
- [ ] Design request-specific Critic criteria behind user review, versioned run
      configuration, and consistency evaluation. Keep the current demo rubric
      static; user-configured weights remain supported.
- [ ] Modularize source code around clear responsibilities as the project grows;
      keep package boundaries cohesive, avoid circular dependencies, and update
      imports, tests, and docs with any future moves.
- [ ] Apply maintainability best practices in future changes: add concise
      docstrings for public APIs and comments only where they explain a non-obvious
      invariant, fallback, or trade-off. Keep documentation accurate and avoid
      comments that merely repeat the code.

Frozen fixtures are synthetic and live adapters may not provide every source
type required by every case. See dated reports under `evals/` before making
quality or coverage claims.
