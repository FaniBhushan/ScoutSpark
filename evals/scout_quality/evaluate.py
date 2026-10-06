"""Prepare blind Scout reviews and summarize completed human annotations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean

from src.guardrails import check_privacy
from src.models import InputRequest, OrchestrationResult

EVALS_ROOT = Path(__file__).resolve().parents[1]


SCORE_FIELDS = (
    "request_fit", "constraint_compliance", "distinctiveness", "evidence_support",
)
REVIEW_FIELDS = (
    "candidate_id", "request_json", "title", "problem_statement", "target_users",
    "proposed_outcome", "evidence_source_ids", "evidence_receipts_json", "request_fit",
    "constraint_compliance", "distinctiveness", "evidence_support", "reviewer_id", "notes",
)


def _load_result(path: Path, case_id: str) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value.get("result"), dict):
        value = value["result"]
    if not isinstance(value.get("scout"), dict):
        raise ValueError("input must be a saved OrchestrationResult or end-to-end case result")
    saved_result = OrchestrationResult.model_validate(value)
    manifest = json.loads((EVALS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    expected_request = None
    for relative in manifest["held_out_cases"]:
        case = json.loads((EVALS_ROOT / relative).read_text(encoding="utf-8"))
        if case.get("case_id") == case_id:
            expected_request = case.get("expected_request")
            break
    if expected_request is None:
        raise ValueError("case_id must name a held-out Scout evaluation case")
    expected_request = InputRequest.model_validate(expected_request).model_dump(mode="json")
    if saved_result.prepared_run is None:
        raise ValueError("saved result has no resolved request for held-out matching")
    actual_request = saved_result.prepared_run.request.model_dump(mode="json")
    if actual_request != expected_request:
        raise ValueError("saved run request does not match the selected held-out case")
    return value


def prepare_review(result_path: Path, case_id: str, output_path: Path) -> None:
    """Create one blank human-review row per returned Scout candidate."""

    result = _load_result(result_path, case_id)
    scout = result["scout"]
    source_records = {item["source_id"]: item for item in scout.get("sources", [])}
    sources = set(source_records)
    request = result.get("prepared_run", {}).get("request", {})
    rows = []
    for candidate in scout.get("candidates", []):
        evidence = candidate.get("evidence", [])
        cited_ids = sorted({ref["source_id"] for ref in evidence})
        receipts = [{
            key: source_records[source_id].get(key)
            for key in ("source_id", "source_type", "title", "canonical_url",
                        "abstract_or_snippet", "excerpts")
            if source_records[source_id].get(key) is not None
        } for source_id in cited_ids if source_id in source_records]
        rows.append({
            "candidate_id": candidate["candidate_id"],
            "request_json": json.dumps(request, ensure_ascii=False, separators=(",", ":")),
            "title": candidate["title"],
            "problem_statement": candidate["problem_statement"],
            "target_users": "; ".join(candidate.get("target_users", [])),
            "proposed_outcome": candidate["proposed_outcome"],
            "evidence_source_ids": "; ".join(cited_ids),
            "evidence_receipts_json": json.dumps(receipts, ensure_ascii=False, separators=(",", ":")),
        })
    report = {"rows": rows, "source_ids": sorted(sources)}
    check_privacy(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def score_review(
    result_path: Path, case_id: str, review_path: Path, output_path: Path, *,
    shortfall_reason_accurate: str,
) -> None:
    """Validate human scores and combine them with deterministic contract checks."""

    result = _load_result(result_path, case_id)
    scout = result["scout"]
    diagnostics = result.get("diagnostics") or {}
    candidates = scout.get("candidates", [])
    requested = (result.get("prepared_run", {}).get("request", {})
                 .get("desired_candidate_count"))
    if requested is None:
        raise ValueError("saved result does not contain the resolved request target")
    ids = [item.get("candidate_id") for item in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("Scout returned duplicate candidate IDs")
    source_ids = {item["source_id"] for item in scout.get("sources", [])}
    references_valid = all(
        ref.get("source_id") in source_ids
        for candidate in candidates for ref in candidate.get("evidence", [])
    )
    actual = len(candidates)
    generation_target = scout.get("generation_target_count") or requested
    should_report_shortfall = actual < generation_target
    reported_shortfall = any(
        item.get("stage") == "scout_generation"
        for item in diagnostics.get("shortfalls", [])
    )
    reason_codes = [
        code for item in diagnostics.get("shortfalls", [])
        if item.get("stage") == "scout_generation"
        for code in item.get("reason_codes", [])
    ]
    diagnostics_count_matches = (
        diagnostics.get("requested_candidate_count") == requested
        and diagnostics.get("accepted_candidate_count") == actual
        and diagnostics.get("generated_candidate_count", actual) >= actual
    )
    ratings = []
    with review_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not set(REVIEW_FIELDS).issubset(reader.fieldnames):
            raise ValueError("review CSV is missing required columns")
        reviewed = list(reader)
    reviewed_ids = [row.get("candidate_id") for row in reviewed]
    if len(reviewed_ids) != len(set(reviewed_ids)) or set(reviewed_ids) != set(ids):
        raise ValueError("review CSV candidate IDs do not match this Scout result")
    for row in reviewed:
        if not row.get("reviewer_id", "").strip():
            raise ValueError("every reviewed candidate needs a reviewer_id")
        score_row = {}
        for field in SCORE_FIELDS:
            try:
                score = int(row[field])
            except (TypeError, ValueError):
                raise ValueError(f"review score {field} must be an integer from 1 to 5") from None
            if score < 1 or score > 5:
                raise ValueError(f"review score {field} must be an integer from 1 to 5")
            score_row[field] = score
        ratings.append(score_row)
    report = {
        "evaluation": "independent_scout_review",
        "case_id": case_id,
        "split": "held_out",
        "run_id": result.get("run_id"),
        "requested_candidate_count": requested,
        "generation_target_count": generation_target,
        "returned_candidate_count": actual,
        "candidate_count_attained": actual >= requested,
        "diagnostics_count_matches": diagnostics_count_matches,
        "candidate_ids_unique": len(ids) == len(set(ids)),
        "evidence_source_references_valid": references_valid,
        "shortfall_expected": should_report_shortfall,
        "shortfall_reported": reported_shortfall,
        "shortfall_presence_accurate": should_report_shortfall == reported_shortfall,
        "shortfall_reason_accurate": shortfall_reason_accurate,
        "shortfall_reason_codes": reason_codes,
        "hard_gate_reasons_excluded_from_scout": "hard_gate_rejection" not in reason_codes,
        "human_review_count": len(ratings),
        "human_reviewer_ids": sorted({row["reviewer_id"].strip() for row in reviewed}),
        "human_score_means": {
            field: round(mean(row[field] for row in ratings), 3) if ratings else None
            for field in SCORE_FIELDS
        },
        "sample_limitations": (
            "Human judgments apply only to this reviewed run and do not establish general quality."
        ),
    }
    check_privacy(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as file:
        file.write(json.dumps(report, indent=2) + "\n")


def audit_review(result_path: Path, case_id: str, output_path: Path) -> None:
    """Record Scout's contract/count checks without supplying human quality labels."""
    result = _load_result(result_path, case_id)
    scout = result["scout"]
    candidates = scout.get("candidates", [])
    target = (result.get("prepared_run", {}).get("request", {})
              .get("desired_candidate_count"))
    if target is None:
        raise ValueError("saved result has no requested candidate count")
    generation_target = scout.get("generation_target_count") or target
    ids = [item["candidate_id"] for item in candidates]
    source_ids = {item["source_id"] for item in scout.get("sources", [])}
    shortfalls = [item for item in (result.get("diagnostics") or {}).get("shortfalls", [])
                  if item.get("stage") == "scout_generation"]
    report = {"evaluation": "scout_contract_audit", "case_id": case_id,
              "split": "held_out", "run_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
              "requested_candidate_count": target, "generation_target_count": generation_target,
              "returned_candidate_count": len(candidates),
              "candidate_ids_unique": len(ids) == len(set(ids)),
              "evidence_references_valid": all(
                  ref.get("source_id") in source_ids for item in candidates
                  for ref in item.get("evidence", [])),
              "shortfall_expected": len(candidates) < generation_target,
              "shortfall_reported": bool(shortfalls),
              "shortfall_reason_codes": sorted({code for item in shortfalls
                                                 for code in item.get("reason_codes", [])}),
              "human_review_status": "pending" if candidates else "not_applicable",
              "limitations": "Synthetic offline run; candidate quality needs independent review."}
    check_privacy(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as file:
        file.write(json.dumps(report, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="make a blank independent review CSV")
    prepare.add_argument("--result", type=Path, required=True)
    prepare.add_argument("--case-id", required=True, help="case ID from the held-out split")
    prepare.add_argument("--output", type=Path, required=True)
    score = commands.add_parser("score", help="summarize a completed human review")
    score.add_argument("--result", type=Path, required=True)
    score.add_argument("--case-id", required=True, help="case ID from the held-out split")
    score.add_argument("--review", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    score.add_argument("--shortfall-reason-accurate", choices=("yes", "no", "not_applicable"),
                       required=True)
    audit = commands.add_parser("audit", help="record mechanical checks without human scores")
    audit.add_argument("--result", type=Path, required=True)
    audit.add_argument("--case-id", required=True)
    audit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        prepare_review(args.result, args.case_id, args.output)
    elif args.command == "score":
        score_review(args.result, args.case_id, args.review, args.output,
                     shortfall_reason_accurate=args.shortfall_reason_accurate)
    else:
        audit_review(args.result, args.case_id, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
