# ScoutSpark task tracker

This is the single source of truth for every pending and future task. The
[V2 requirements](cross-domain-multi-agent-capstone-orchestrator-v2.md) retain
product context and safeguards; dated reports retain evidence and measurements.

## V2 release milestone

The [limited preview note](docs/v2-limited-preview-2026-10-08.md) explains the
current scope and gaps. The [8 October release check](docs/v2-release-check-2026-10-08.md)
keeps the measured results and pending reviews together. Independent and broader
evaluations follow the preview at the user's direction; the V2 release milestone
remains open.
One capped `gpt-4o-mini` frozen-source run accepted 18/12 requested robotics
candidates, so the offline demo's 5/12 result did not reproduce with that model.
A one-request Tavily live pilot found eight usable web articles but produced no
verified proposal after Critic citation losses and failed gates. Both samples
and their cost/limit details are in the [release check](docs/v2-release-check-2026-10-08.md).

- Result labels, hard-gate treatment, and preregistered first-run targets — agree
  before a release decision.
- Measured loss points and repeat-run/live-source checks — resolve the identified
  gaps and record the results before release.
- Release note — complete with actual results and limits after review.

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
- Human review of controlled proposals and short demo recording are tracked as
  V2-21 and V2-22 below.

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
The GUI and CLI also support an explicit, budgeted exploratory proposal for
any displayed idea, including failed-gate and unscored ideas. It is saved as
unverified with its original gate outcomes and never counted as a verified
final proposal.

### Completed in this implementation

- [x] V2-10 — Scout over-generates to `ceil(1.5 × requested count)`.
- [x] V2-11 — Scout corrects measured candidate shortfalls within bounded batches.
- [x] V2-12 — Library retries evidence collection for missing coverage within shared limits.
- [x] V2-13 — Critic shows the configured number of scored results when available.
- [x] V2-18 — GUI and CLI support versioned Critic re-evaluation.
- [x] V2-19 — GUI and CLI can request a verified non-finalist proposal.
- [x] V2-20 — UI and help docs include practical result and cost guidance.
- [x] Add user-requested exploratory proposals for displayed candidates without
      weakening automatic hard gates or verified-proposal rules.

## Pending and future work

The task IDs and acceptance criteria below are canonical. Complete a task only
when its evidence is recorded. These items are intentionally kept together;
supporting reports may describe pending reviews but do not maintain separate
task checklists.

### Release readiness

- Independent release reviews — complete the Scout, Library, Critic, proposal,
  and verifier reviews with independent human/reference ratings, sample sizes,
  and limitations recorded. V2-06–V2-09 cover the worker and proposal reviews;
  V2-14 covers verifier accuracy.
- Release checks — fix measured loss points and pass the repeat-run and limited
  live-source checks before deciding to release.

### Evaluation and reliability

- **V2-06 — Scout:** Score held-out outputs for request/constraint fit, valid
  structure, uniqueness/diversity, evidence support, and count/shortfall
  accuracy. Complete the five-candidate human review and record its summary;
  artifacts and blind review sheets are in `evals/scout_quality/`.
- **V2-07 — Library:** Assess source relevance, required type/tier coverage,
  metadata and citation integrity, deduplication, and gap reporting. Include
  provider-failure cases, per-metric outcomes, and sample sizes; do not use
  Library's own completion message as its sole quality score.
- **V2-08 — Critic:** Measure score consistency, evidence relevance, gate
  decisions, citation validity, and calibration against blinded human/reference
  judgments. Report false acceptances/rejections and sample sizes; an LLM judge
  is supplementary only.
- **V2-09 — Proposal writing:** Blindly assess completeness, actionability,
  factual support, explicit unknowns, and consistency with the selected idea and
  verified evidence. Report human/reference review separately from verifier
  outcomes, including sample size and unsupported-claim rates.
- **V2-14 — Verifier accuracy:** Expand held-out and adversarial evaluation;
  human-review false rejections and unsupported claims, including data/access
  assumptions. Report false acceptance/rejection counts and adjudication using
  an appropriate confusion analysis. Base any policy change on evidence and
  continue to describe model verification as a safeguard.
- **V2-15 — Critic evidence and citation policy:** Trace Scout claims through
  Library chunks, Critic context/citations, drafting, and final audit. Compare
  rejecting an assessment with preserving a caveated score for invalid/missing
  citations. Test whether bounded retrieve-more-and-reassess fixes observed gaps
  enough to justify its cost. Record the decision and frozen-case results for
  citation integrity, unsupported claims, false rejection, cost, and both run
  modes before implementation.
- **V2-16 — Verified proposal yield:** Find loss points across discovery,
  sources, assessment, gates, data suitability, drafting, citations, and
  verification. Improve yield without weakening evidence, privacy, or user
  constraints. Use a dated matched comparison and report stage counts, failure
  reasons, latency, token use, and estimated cost; make no universal claim from
  a small sample.
- **V2-21 — Human review of controlled proposals:** Score the saved sequential
  and parallel proposals using existing sheets and blind-review protocol.
  Record sheets, supported agreement analysis, sample size, results, and
  limitations in the evaluation report. Never present LLM-judge scores as human
  scores. Sheets: `evals/reports/2026-09-27-controlled-sequential/human_scores.csv`
  and `evals/reports/2026-09-27-controlled-parallel/human_scores.csv`.
- **V2-22 — Short demo recording:** Follow `docs/demo_recording_guide.md`; show
  the real workflow with the synthetic-data label visible. Save recording and
  notes; present measured yield and sample sizes with limitations.

### Future product and infrastructure work

- **V2-17 — User-approved bounded feedback:** Show proposed extra work and
  budget impact, then ask before spending. Preserve earlier results and assess
  alternatives with the same evidence, rubric, and gates. Cover approve/decline,
  exhaustion, duplicate alternatives, and preservation of prior results; a
  declined round changes nothing.
- **V2-23 — GitHub GraphQL evaluation:** Compare with REST on identical fixed
  repository queries. Measure unique usable sources, request/point use, latency,
  response size, and rate-limit/time-out failures. Record a reproducible
  decision using current official guidance; retain REST fallback and rate-aware
  backoff unless evidence supports a change. Keep credentials out of reports.
- **V2-24 — Semantic retrieval evaluation:** Compare embeddings only if held-out
  evaluation finds relevant evidence missed by the lexical/TF-IDF baseline.
  Record retrieval quality, latency, token use, and embedding cost; adopt only
  when measured gains justify cost and complexity.
- **V2-25 — Request-specific Critic criteria:** Keep the demo rubric stable.
  Design user-reviewed, versioned criteria and test consistency against the
  fixed rubric. Before enabling, document schema, precedence, and held-out
  results; weights must not weaken hard gates or citation rules.
- **V2-26 — Cohesive module boundaries:** Refactor only for a concrete
  maintenance need; avoid circular imports and broad rename/signature churn.
  Record a narrow rationale, cover behavior, and update public imports/docs.
- **V2-27 — Useful code comments and docs:** Add concise public API docstrings
  and comments for non-obvious invariants, fallbacks, and trade-offs. Keep docs
  accurate and avoid comments that only restate code.
- **V2-28 — Budget-aware model router:** Choose models per stage from task needs,
  configured quality/cost preferences, and remaining run budget. Keep choices
  inspectable and offer fixed-model mode. Compare quality, latency, and cost
  with a fixed-model baseline; never exceed user limits and record model and
  rationale without sensitive prompt content.
- **V2-29 — Pluggable LLM providers and models:** Replace OpenAI-specific
  application wiring with a stable provider interface and configurable model
  IDs while preserving structured validation, retries, usage accounting, and
  budgets. Require at least two adapters to pass the same contract suite;
  document provider differences, keep selection explicit, and keep secrets out
  of logs and traces.
- **V2-30 — Streamlit UI redesign:** Improve the app's visual hierarchy,
  spacing, typography, navigation, and result presentation so the research flow
  feels clear and polished. Keep setup understandable for local users, preserve
  the existing review and budget safeguards, and check the main screens at
  desktop and narrow widths before considering the redesign complete.

Frozen fixtures are synthetic and live adapters may not provide every source
type required by every case. See dated reports under `evals/` before making
quality or coverage claims.
