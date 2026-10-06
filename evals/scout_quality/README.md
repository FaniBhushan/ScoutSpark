# Independent Scout evaluation

This evaluation separates mechanical contract checks from independent human
judgments. It does not use Scout to grade Scout and does not make a model call.
Use held-out cases for release evidence; do not tune against them.

The current held-out run and pending human review are summarized in
[`heldout_v2_2026-10-05.md`](heldout_v2_2026-10-05.md).

Prepare a blank review sheet from a saved run result:

```sh
python -m evals.scout_quality prepare --result PATH_TO_RESULT.json --case-id mathematics-optimization-01 --output NEW_REVIEW.csv
```

Have an independent reviewer score each returned candidate from 1 (poor) to 5
(excellent) for request fit, constraint compliance, distinctiveness, and support
from its cited evidence. A 3 means acceptable with material weaknesses. Record
short reasons for scores of 1 or 5. The sheet includes the resolved request and
receipts cited by each idea. Reviewers should not see Critic scores, rankings,
or proposal outcomes.

After completing the CSV, create a new summary file:

```sh
python -m evals.scout_quality score --result PATH_TO_RESULT.json --case-id mathematics-optimization-01 --review COMPLETED_REVIEW.csv --output NEW_SUMMARY.json --shortfall-reason-accurate yes
```

Use `no` when the reported cause is wrong, or `not_applicable` when Scout met
the requested count. Outputs are write-once. The summary checks candidate count,
ID uniqueness, evidence source references, whether a shortfall was reported when
one existed, and mean human scores by dimension. Preserve the request, model and
prompt versions, source snapshot, mode, sample size, and any reviewer disagreement
in the evaluation report. One run is not evidence of general reliability.
