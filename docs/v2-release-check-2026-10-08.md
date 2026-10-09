# V2 release check — 8 October 2026

**Decision: limited preview; hold the V2 release milestone.** The registered
candidate-count target failed. First-run usefulness, factual support, and false
rejection have not received independent review. One saved live-source pilot is
recorded below; it is too small to establish general live quality. This is a
status record, not a quality claim. The user deferred broader evaluations until
after the [limited preview](v2-limited-preview-2026-10-08.md).

## Frozen-source repeatability

The ten-repeat offline demo used one robotics request and the same frozen
synthetic sources, prompts, rubric, and limits in every run. The current report is
`evals/reports/reliability-v2-2026-10-08-corrected/summary.md` (generated locally; reports
are ignored by Git). The earlier
[failed report](../evals/reports/reliability-v2-02-final/summary.md) remains the
historical baseline. The report records case and configuration hashes, per-run
stage counts, duration, model tokens, and shortfall reasons.

| Measure | Result | Registered target |
| --- | ---: | ---: |
| Completed with valid automated checks | 10 / 10 | ≥ 90% |
| Requested candidate count reached | 0 / 10 | ≥ 90% |
| Requested scorecard count reached | 10 / 10 | ≥ 80% |
| Requested verified proposal count reached | 10 / 10 | ≥ 80% |

Each run requested 12 candidates, generated and accepted 5, scored and showed
5, passed all 5 through the gates, and produced 3 of 3 requested proposals.
The saved shortfall reason is `scout_generation: underproduction`. The synthetic
offline client used 2,400 model tokens per run; estimated cost is unavailable
without configured pricing. The report's automated citation and verification
checks passed. They do not establish that a person would find the ideas useful
or the claims factually supported.

The existing `finalist_count_target_rate` incorrectly measured proposal count.
The new report has separate `scorecard_count_target_rate` and
`verified_proposal_count_target_rate`, both with the prior 80% threshold. All
runs, including no-result runs, remain in the count denominators. Candidate-set
overlap now fingerprints all Scout ideas instead of only completed proposals;
rank correlation uses contiguous positions among ideas shared by both runs.
The earlier report in `reliability-v2-2026-10-08/` remains an intermediate
measurement with the old overlap calculation.

## Checks and open decisions

- Unit suite: 263 tests passed using `.venv/bin/python`.
- Evaluation fixture validation and `git diff --check`: passed.
- Independent Scout, Library, Critic, and proposal sheets: pending. The prepared
  sheets and scoring commands are in the [worker review report](../evals/worker_quality/heldout_v2_2026-10-05.md).
- Held-out and adversarial verifier review, including false support and false
  rejection: pending.
- Three result-screen wording review with a fresh user: pending. No gate-label
  policy change was made; the five hard gates and saved outcomes remain intact.
- First-run useful-result pass target and sample size: awaiting registration
  before human ratings are collected. No human usefulness rate is reported.
- Live-source pilot: one Tavily/GitHub request was run with a $1 estimated
  OpenAI model-cost cap; results and limitations are below.

The measured candidate loss is in Scout generation for this frozen case. The
offline client's limited output cannot establish the same failure rate for a
live model, so no generation or gate rule was changed to make this report pass.

## `gpt-4o-mini` and live-source follow-up

The one-request paid run on the same frozen synthetic robotics sources is saved
locally under `evals/reports/v2-mini-shortfall-2026-10-08-network/`. Scout
generated 19 candidates and accepted 18, exceeding the 12 requested. Critic
assessed 16; 12 passed gates; 2 of 3 requested proposals passed final
verification. The run took 361 seconds, used 171,904 model tokens, and recorded
an estimated $0.04195 in OpenAI model cost. This identifies the prior five-idea
shortfall as an offline-demo artifact for this matched request, not a measured
`gpt-4o-mini` Scout failure. It does not establish repeatability from one run.

The distinct live pilot used
`evals/live_requests/ai_engineering_web_article.json` and is saved locally under
`evals/reports/v2-live-mini-2026-10-08/`. Scout made two Tavily searches and
accepted nine initial candidates against six requested. Library made two more
Tavily searches. The final source manifest contains eight usable `web_article`
receipts from Tavily. Both optional GitHub attempts failed and were skipped;
no repository evidence was counted. All eight titles mention RAG; six also
mention evaluation. This title check does not establish passage relevance or
claim support. Critic retained three of the nine initial
assessments; trace events show invalid citation references caused several
skips. No initial proposal passed. One bounded recovery generated three more
candidates; its three assessments passed no hard gates. The final status is
`insufficient_coverage` with zero verified proposals. The pilot took 184
seconds, used 84,026 model tokens, and recorded an estimated $0.02040 in
OpenAI model cost. The live source sample is one request; source relevance and
claim support still need independent review. Tavily's own service charges, if
any, are outside the OpenAI model-cost estimate.

The two completed paid runs recorded about $0.06235 in settled estimated OpenAI
model cost, below their separate $1 caps and the user's stated $4.91 credit.
An initial sandboxed attempt stopped with a model connection error before
settling token usage; it is not counted as a completed model run.
The V2 milestone remains open pending reviewed targets and samples, independent
ratings, a dated before-and-after result for any focused fix, and repeatable
live-source checks. This preview check does not declare the V2 milestone ready.
