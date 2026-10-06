# Independent Library, Critic, and proposal review

This workflow reads a saved held-out `OrchestrationResult`; it makes no provider
or model calls. `prepare` exports a blind CSV, `audit` records structural checks,
and `score` accepts completed independent labels. Reviewers should use the
request, source receipts, and captured passages in `context_json`, without
looking at Critic assessments, ranks, or verifier outcomes. The output is a
synthetic offline evaluation, not a live quality claim.

The current saved runs and review sheets are listed in
[the dated report](heldout_v2_2026-10-05.md). For a new held-out run:

```sh
python -m evals.worker_quality prepare --stage library --result SAVED_RUN.json --case-id mathematics-optimization-01 --output NEW_LIBRARY_REVIEW.csv
python -m evals.worker_quality audit --stage library --result SAVED_RUN.json --case-id mathematics-optimization-01 --output NEW_LIBRARY_AUDIT.json
python -m evals.worker_quality score --stage library --result SAVED_RUN.json --case-id mathematics-optimization-01 --review COMPLETED_LIBRARY_REVIEW.csv --review-type human --output NEW_LIBRARY_SUMMARY.json
```

Use `--stage critic` or `--stage proposal` for the other sheets. Give every row
a reviewer ID. Use `yes` or `no` for applicable judgments. Library source rows
need relevance, metadata, and citation judgments; its coverage row needs only
`gap_report_accurate`. Critic rows need a 0–100 reference score, a reference
gate decision, evidence relevance, and citation validity. Proposal rows need
completeness, actionability, explicit unknowns, idea alignment, support, and
counts of all claims reviewed and unsupported claims. Include claims in prose,
not only citation entries. Add notes for adverse judgments. Use
`--review-type reference` for curated reference labels, and retain their
provenance; never label an AI judgment as human.

The scorer rejects missing ratings, changed evidence/context, duplicate rows,
and reviews against a different saved run. Summaries include sample sizes,
Library source and coverage metrics, Critic score error and gate confusion,
and proposal unsupported-claim rate alongside verifier acceptance. A worker's
own verdict is shown only in the comparison report, never in the blind sheet.

For consistency across two runs with the same request, rubric, captured
evidence, and candidate content:

```sh
python -m evals.worker_quality compare-critic --stage critic --result FIRST.json --comparison-result SECOND.json --case-id mathematics-optimization-01 --output NEW_CONSISTENCY.json
```

For the held-out provider-failure scenario, the command injects a synthetic
`SourceUnavailableError` into the Library worker, recording whether its
required branch stops:

```sh
python -m evals.worker_quality audit-provider-failure --stage library --result SAVED_RUN.json --case-id mathematics-optimization-01 --output NEW_PROVIDER_FAILURE.json
```

The provider-failure replay does not contact a live provider or rate source
relevance. It is a separate fault sample, not an extra quality review.
