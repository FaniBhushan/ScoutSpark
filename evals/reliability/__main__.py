"""Run repeated, matched end-to-end evaluations on frozen source snapshots."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.guardrails import safe_error_message
from src.llm.client import ModelPricing, OpenAITextClient
from src.models import RunBudgetLimits
from src.runtime.budgets import BudgetedLLMClient, RunBudget
from src.runtime.environment import load_local_environment
from src.testing.demo import OfflineDemoClient

from evals.end_to_end.cases import DEFAULT_CASES, ROOT, load_cases
from evals.end_to_end.runner import run_cases

from .metrics import aggregate


def _fingerprint(candidate: dict) -> str:
    identity = "\n".join(str(candidate.get(key, "")).strip().casefold()
                         for key in ("title", "problem_statement", "proposed_outcome"))
    return hashlib.sha256(identity.encode()).hexdigest()


def _decorate(record: dict, run_number: int) -> dict:
    result = record.get("result") or {}
    candidate_by_id = {row["candidate_id"]: _fingerprint(row)
                       for row in result.get("scout", {}).get("candidates", [])}
    record["repeat"] = run_number
    record["candidate_fingerprints"] = sorted(
        _fingerprint(row) for row in result.get("final_proposals", [])
    )
    record["ranked_fingerprints"] = [candidate_by_id[row["candidate_id"]]
                                     for row in result.get("ranking", [])
                                     if row["candidate_id"] in candidate_by_id]
    record["candidate_scores"] = {
        candidate_by_id[row["candidate_id"]]: row["total_score"]
        for row in result.get("critic", {}).get("evaluations", [])
        if row.get("candidate_id") in candidate_by_id
    }
    prepared = result.get("prepared_run") or {}
    record["configuration_sha256"] = prepared.get("configuration_checksum")
    return record


def _write(destination: Path, report: dict) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Repeated-run reliability report", "",
             f"Decision: **{report['evaluation']['decision']}**", "",
             "All runs use identical requests and frozen synthetic source snapshots. This isolates "
             "pipeline/model repeatability; live-search variation is excluded by design and was "
             "not measured.", "",
             ]
    evaluations = report["evaluation"].get("per_case") or {
        report["case_ids"][0]: report["evaluation"]
    }
    for case_id, evaluation in evaluations.items():
        lines += [f"## {case_id}", "",
                  f"Sample size: {evaluation['sample_size']} runs; preregistered minimum: "
                  f"{evaluation['minimum_repeats']}.", "",
                  "| Metric | Mean | Population SD | Evaluated / total | Threshold |",
                  "| --- | ---: | ---: | ---: | ---: |"]
        for name, result in evaluation["metrics"].items():
            specification = report["thresholds"]["metrics"].get(name, {})
            threshold = (f"≤ {specification['maximum']}" if "maximum" in specification
                         else f"≥ {specification['minimum']}" if "minimum" in specification else "—")
            mean = "—" if result["mean"] is None else f"{result['mean']:.3f}"
            deviation = "—" if result["population_stddev"] is None else f"{result['population_stddev']:.3f}"
            lines.append(f"| {name} | {mean} | {deviation} | {result['evaluated']} / "
                         f"{result['evaluated'] + result['not_evaluated']} | {threshold} |")
    errors = [row for row in report["runs"] if row["outcome"] == "error"]
    lines += ["", "## Failures by stage", ""]
    if errors:
        for row in errors:
            lines.append(f"- Repeat {row['repeat']}: {row.get('failure_stage') or 'unknown stage'} "
                         f"({row.get('error', {}).get('type', 'error')})")
    else:
        lines.append("No stage failures.")
    lines += ["", "Candidate wording and ranking are measured using normalized title, problem, "
              "and outcome fingerprints. These synthetic offline results are a repeatability "
              "smoke test, not evidence of live model quality or production reliability.", ""]
    (destination / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    execution = parser.add_mutually_exclusive_group(required=True)
    execution.add_argument("--offline-demo", action="store_true")
    execution.add_argument("--model")
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--mode", choices=["sequential", "parallel"], default="sequential")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-cost-usd", type=float)
    parser.add_argument("--input-rate", type=float)
    parser.add_argument("--output-rate", type=float)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    if args.model and any(value is None or value <= 0 for value in (
        args.max_cost_usd, args.input_rate, args.output_rate
    )):
        parser.error("paid mode requires positive --max-cost-usd, --input-rate and --output-rate")
    selected = load_cases(args.case_ids or [DEFAULT_CASES[0]])
    cases = [item[0] for item in selected]
    by_id = {case.case_id: fingerprint for case, fingerprint in selected}
    thresholds = json.loads((Path(__file__).parent / "thresholds.json").read_text())
    destination = args.output or ROOT / "reports" / f"reliability-{uuid4().hex}"
    if destination.exists():
        parser.error("output directory already exists; choose a new directory")
    pricing = ModelPricing(args.input_rate, args.output_rate) if args.model else None
    if args.model:
        load_local_environment()
        client = OpenAITextClient(args.model, pricing=pricing, max_retries=0)
        budget = RunBudget(RunBudgetLimits(max_elapsed_seconds=3600,
                                           max_model_tokens=2_000_000,
                                           max_estimated_cost_usd=args.max_cost_usd), pricing=pricing)
        run_client = BudgetedLLMClient(client, budget)
    else:
        client = run_client = OfflineDemoClient()

    async def execute() -> list[dict]:
        records = []
        try:
            for repeat in range(1, args.repeats + 1):
                for case in cases:
                    [record] = await run_cases([(case, by_id[case.case_id])], run_client,
                                               mode=args.mode, pricing=pricing)
                    record = _decorate(record, repeat)
                    records.append(record)
        finally:
            if args.model:
                await client.sdk_client.close()
        return records

    records = asyncio.run(execute())
    results = {}
    for case in cases:
        case_records = [row for row in records if row["case_id"] == case.case_id]
        results[case.case_id] = aggregate(
            case_records, case.expected_request.desired_candidate_count, thresholds,
            finalist_target=case.expected_request.finalist_count,
        )
    # A suite passes only if every selected matched request passes its registered thresholds.
    decision = ("insufficient_sample" if any(row["decision"] == "insufficient_sample" for row in results.values())
                else "pass" if all(row["decision"] == "pass" for row in results.values()) else "fail")
    report = {
        "schema_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "execution": "paid_model" if args.model else "offline_demo",
        "model": args.model or "offline-demo", "mode": args.mode,
        "resolved_models": sorted(client.resolved_models) if args.model else [],
        "source_snapshot_policy": "frozen synthetic snapshots; live-search variation excluded by design",
        "dataset_version": json.loads((ROOT / "manifest.json").read_text())["dataset_version"],
        "prompt_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted((ROOT.parent / "src/prompts").glob("*.md"))},
        "case_input_sha256": by_id, "repeats_per_case": args.repeats,
        "case_ids": [case.case_id for case in cases],
        "effective_configuration_sha256": sorted({row["configuration_sha256"] for row in records
                                                  if row["configuration_sha256"]}),
        "suite_budget_limits": ({"max_cost_usd": args.max_cost_usd,
                                 "max_elapsed_seconds": 3600,
                                 "max_model_tokens": 2_000_000} if args.model else None),
        "thresholds": thresholds, "evaluation": {"decision": decision, "per_case": results},
        "budget_usage": budget.snapshot() if args.model else None,
        "runs": records,
    }
    # Publish aggregate values for the single-case default and suite decision for multiple cases.
    if len(results) == 1:
        report["evaluation"] = next(iter(results.values()))
    else:
        report["evaluation"]["sample_size"] = args.repeats
        report["evaluation"]["minimum_repeats"] = thresholds["minimum_repeats"]
    _write(destination, report)
    print(f"Report: {destination / 'summary.md'}")
    print(f"Decision: {decision}")
    return 0 if decision == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(safe_error_message(error)) from None
