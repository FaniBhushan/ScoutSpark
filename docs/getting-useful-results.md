# Getting useful results

- Focus on one problem and one interest area. Name the people who experience it
  and the small outcome you want to explore.
- State the deadline, available skills, tools, data, and any topics or activities
  that are out of scope.
- Select only source types that can support this request. Start with a simpler
  search preset when broad coverage is unnecessary.
- Review the configuration preview before starting a live run. Set time, token,
  and cost limits that fit the work you want to authorize.

These are practical suggestions, not guarantees of quality, completeness, or cost.

## User-requested exploratory proposals

In a saved result, choose **Generate an exploratory proposal for any shown
idea** to request a detailed draft for a scored or unscored candidate. Review
the displayed gate failures and remaining budget, then approve the model call.
This reuses the run's evidence and does not search again. The draft is
unverified: it does not clear failed gates, establish data access, or count as a
verified proposal. Check its first feasibility test before committing to it.

The CLI equivalent previews the same action before spending:

```sh
python -m src.ui.cli --exploratory-proposal-result SAVED_RUN.json --candidate-id CANDIDATE_ID --offline-demo --preview-additional-work
python -m src.ui.cli --exploratory-proposal-result SAVED_RUN.json --candidate-id CANDIDATE_ID --offline-demo --confirm-additional-work --result-output UPDATED_RUN.json
```

For a live saved run, replace `--offline-demo` with `--model gpt-4o-mini` and
provide `--input-rate` and `--output-rate` when that run has a cost cap.
