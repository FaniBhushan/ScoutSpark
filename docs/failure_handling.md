# Failure handling and partial-result policy

This matrix defines how one research run behaves when a stage cannot complete.
The same stable `stage` and `code` fields are used in CLI error JSON, UI run
errors, and checkpoint events. Error messages are sanitized; rejected model text
and provider response bodies are not shown or recorded.

| Stage | Failure | Run behavior | User-visible record |
|---|---|---|---|
| Interpretation | Invalid or unsafe model reply | No search starts. The user may correct fields or draft again. | `interpretation` with a stable failure code and safe message. |
| Preflight | Invalid request, unavailable required provider, or invalid configuration | Fail before provider/model work. Do not silently change the request or source policy. | `preflight` error in UI; CLI error JSON includes stage and code. |
| Source adapter | Optional provider fails and policy permits skipping it | Continue with other approved providers; preserve the skip warning and reason code. | Warning and `provider_unavailable` shortfall reason when relevant. |
| Source adapter | Required provider fails, provider budget is exhausted, or adapter returns more than its limit | Fail the responsible worker/join stage. Never truncate an over-return and treat it as a valid response. | Stage failure with a stable code; no fabricated source or candidate count. |
| Scout generation | One response fails schema validation | Send one bounded correction request containing only safe field paths and validation codes. Keep prior valid unique ideas. Charge the correction to the normal run budget. | Correction attempt/success counters; `invalid_output` reason when generation remains short. |
| Scout or Library branch | Required branch fails in parallel mode | Cancel and drain the sibling branch. In sequential mode, stop before starting later required stages. | `scout` or `library` stage failure; checkpoint records the failure code. |
| Join | Duplicate IDs, invalid source references, conflicting source identity, or contract violation | Fail the join; do not repair ambiguous identity or accept invalid references. | `join` stage failure. |
| Critic | Some candidates cannot be retrieved or assessed | Keep valid assessments; return a partial result and explain which stage/count is short. | `critic_assessment` count and reason codes. |
| Finalization | A proposal cannot be drafted or verified | Keep other verified proposals and record the candidate-specific failure. If every eligible candidate is exhausted, report that separately from gate failures. | Proposal failure plus verified-proposal count; gates remain separate. |
| Budget or deadline | A shared run limit is reached | Stop new work, preserve completed work when the current contract allows a partial result, and do not retry outside the shared budget. | `budget_exhausted` or `timeout`; actual stage counts when a result exists. |
| Checkpoint/resume | Identity/checksum mismatch, expiry, lock conflict, or missing frozen stage | Stop; never reuse data from a different request/configuration or claim an incomplete frozen replay succeeded. | `checkpoint` stage and `checkpoint_invalid` code. |
| UI/result export | Local history save fails after successful research | Keep the completed result in session state and offer JSON download. | Save warning; do not relabel research as failed. |

Optional-provider fallback is explicit in the resolved configuration and run
warnings. Required-source and hard-gate failures are not candidate-generation
failures. `OrchestrationResult.diagnostics` reports targets, observed counts,
and typed shortfall causes for completed or partial results. A fatal run error
uses the same stage/code vocabulary but does not pretend to have a completed
result-count summary.

| Stable code | Meaning |
|---|---|
| `invalid_output` / `invalid_model_response` | Model output could not be parsed or validated. |
| `provider_unavailable` / `provider_timeout` / `provider_rate_limit` / `provider_rate_limited` / `provider_invalid_payload` / `provider_error` | Source or model provider failure; whether work may continue depends on configured policy and required coverage. |
| `budget_exhausted` / `timeout` | A run-wide budget or deadline stopped additional work. |
| `checkpoint_invalid` | A checkpoint cannot safely be resumed or replayed. |
| `insufficient_coverage` | Required evidence coverage was not obtained. |
| `stage_failure` | A failure has no more specific safe classification. |
