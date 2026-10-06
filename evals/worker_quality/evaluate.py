"""Prepare blind review sheets and score them against saved held-out runs.

The review columns are filled by a person or an independently curated reference.
Worker scores, gate decisions, and verifier verdicts are never copied into them.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean

from src.configuration.loader import load_source_configuration
from src.adapters.http_json import SourceUnavailableError
from src.guardrails import check_privacy
from src.llm.library_llm import LLMLibraryQueryPlanner
from src.models import InputRequest, OrchestrationResult
from src.testing.demo import OfflineDemoClient
from src.workers.library_worker import LibraryWorker


ROOT = Path(__file__).resolve().parents[1]
STAGES = ("library", "critic", "proposal")
COMMON = ("review_id", "run_sha256", "context_json", "reviewer_id", "notes")
LABELS = {
    "library": ("relevant", "metadata_accurate", "citation_valid", "gap_report_accurate"),
    "critic": ("reference_score", "reference_gate_passed", "evidence_relevant",
               "citations_valid"),
    "proposal": ("complete", "actionable", "unknowns_explicit", "idea_aligned",
                 "supported", "reviewed_claims", "unsupported_claims"),
}
YES_NO = {"yes", "no"}


def _held_out_case(case_id: str) -> dict:
    """Load reference expectations from the reserved held-out split."""
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    cases = [json.loads((ROOT / relative).read_text(encoding="utf-8"))
             for relative in manifest["held_out_cases"]]
    case = next((item for item in cases if item["case_id"] == case_id), None)
    if case is None:
        raise ValueError("case_id must name a held-out case")
    return case


def _load_result(path: Path, case_id: str) -> tuple[OrchestrationResult, str]:
    """Match a saved result to the exact held-out request before review."""
    raw = path.read_bytes()
    payload = json.loads(raw)
    if isinstance(payload.get("cases"), list):
        record = next((item for item in payload["cases"] if item.get("case_id") == case_id), None)
        if record is None or not isinstance(record.get("result"), dict):
            raise ValueError("report has no completed result for this case")
        payload = record["result"]
    elif isinstance(payload.get("result"), dict):
        payload = payload["result"]
    result = OrchestrationResult.model_validate(payload)
    if result.prepared_run is None:
        raise ValueError("saved result has no prepared request")
    case = _held_out_case(case_id)
    expected_request = InputRequest.model_validate(case["expected_request"])
    if result.prepared_run.request != expected_request:
        raise ValueError("saved run request does not match the held-out case")
    return result, hashlib.sha256(raw).hexdigest()


def _base(review_id: str, digest: str, context: dict) -> dict:
    return {"review_id": review_id, "run_sha256": digest,
            "context_json": json.dumps(context, ensure_ascii=False, separators=(",", ":"))}


def _rows(stage: str, result: OrchestrationResult, digest: str) -> list[dict]:
    """Expose only inputs needed by an independent stage reviewer."""
    request = result.prepared_run.request.model_dump(mode="json")
    search = result.prepared_run.search.model_dump(mode="json")
    sources = {item.source_id: item for item in result.source_manifest}
    chunks = {item.chunk_id: item for item in result.library.chunks}
    if stage == "library":
        rows = []
        for source in result.library.sources:
            context = {"kind": "source", "request": request,
                       "source": source.model_dump(mode="json", exclude_none=True)}
            rows.append(_base(f"source:{source.source_id}", digest, context))
        coverage = {"kind": "coverage", "request": request,
                    "required_source_types": search["required_source_types"],
                    "minimum_usable_sources": search["minimum_source_count"],
                    "requested_evidence_tiers": [item.value for item in
                                                 result.prepared_run.submitted.search.evidence_tiers],
                    "source_type_tiers": {key: value.evidence_tier.value for key, value in
                                          load_source_configuration().source_types.items()},
                    "observed_source_types": sorted({item.source_type for item in result.library.sources
                                                     if item.retrieval_status.value in ("success", "partial")}),
                    "observed_usable_count": sum(item.retrieval_status.value in ("success", "partial")
                                                 for item in result.library.sources)}
        rows.append(_base("coverage", digest, coverage))
        return rows
    if stage == "critic":
        candidates = {item.candidate_id: item for item in result.scout.candidates}
        for attempt in result.recovery_history:
            candidates.update({item.candidate_id: item for item in attempt.previous_candidates})
        rows = []
        for evaluation in result.score_evaluations:
            candidate = candidates.get(evaluation.candidate_id)
            if candidate is None:
                raise ValueError("Critic assessment has no retained candidate")
            context = {"request": request, "candidate": candidate.model_dump(mode="json"),
                       "evidence": [chunk.model_dump(mode="json") for chunk in chunks.values()],
                       "source_receipts": [item.model_dump(mode="json", exclude_none=True)
                                           for item in sources.values()]}
            rows.append(_base(f"candidate:{evaluation.candidate_id}", digest, context))
        return rows
    rows = []
    for proposal in [*result.final_proposals,
                     *(item.proposal for item in result.additional_proposals)]:
        context = {"request": request,
                   "proposal": proposal.model_dump(mode="json", exclude={
                       "rank", "total_score", "criterion_scores", "evidence_audit"}),
                   "evidence": [chunk.model_dump(mode="json") for chunk in chunks.values()],
                   "source_receipts": [item.model_dump(mode="json", exclude_none=True)
                                       for item in sources.values()]}
        rows.append(_base(f"proposal:{proposal.proposal_id}", digest, context))
    return rows


def prepare(stage: str, result_path: Path, case_id: str, output: Path) -> int:
    """Write an immutable, unscored review sheet for one saved result."""
    result, digest = _load_result(result_path, case_id)
    rows = _rows(stage, result, digest)
    check_privacy(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[*COMMON, *LABELS[stage]])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _yes_no(value: str, field: str) -> bool:
    if value not in YES_NO:
        raise ValueError(f"{field} must be yes or no")
    return value == "yes"


def _ratings(stage: str, rows: list[dict]) -> list[dict]:
    scores = []
    for row in rows:
        if not row.get("reviewer_id", "").strip():
            raise ValueError("every reviewed row needs a reviewer_id")
        kind = json.loads(row["context_json"]).get("kind")
        rating = {"review_id": row["review_id"]}
        for field in LABELS[stage]:
            raw = row.get(field, "").strip().lower()
            applicable = (stage != "library" or
                          (field == "gap_report_accurate") == (kind == "coverage"))
            if not applicable:
                if raw:
                    raise ValueError(f"{field} does not apply to {row['review_id']}")
                continue
            if field in ("reference_score", "reviewed_claims", "unsupported_claims"):
                try:
                    number = float(raw) if field == "reference_score" else int(raw)
                except ValueError:
                    raise ValueError(f"{field} requires a numeric review") from None
                if field == "reference_score" and not 0 <= number <= 100:
                    raise ValueError("reference_score must be between 0 and 100")
                if field == "reviewed_claims" and number < 1:
                    raise ValueError("reviewed_claims must be positive")
                if field == "unsupported_claims" and number < 0:
                    raise ValueError("unsupported_claims cannot be negative")
                rating[field] = number
            else:
                rating[field] = _yes_no(raw, field)
        scores.append(rating)
    return scores


def _mechanical(stage: str, result: OrchestrationResult, case_id: str) -> dict:
    """Calculate structural checks without treating worker verdicts as truth."""
    if stage == "library":
        sources = result.library.sources
        usable = [item for item in sources if item.retrieval_status.value in ("success", "partial")]
        required = set(result.prepared_run.search.required_source_types)
        observed = {item.source_type for item in usable}
        reference = _held_out_case(case_id).get("expected", {})
        expected_types = set(reference.get("required_source_types", []))
        expected_ids = set(reference.get("relevant_source_ids", []))
        fixture_set = _held_out_case(case_id).get("fixture_set")
        fixture_records = (json.loads((ROOT / "frozen_sources" / fixture_set / "sources.json")
                                      .read_text(encoding="utf-8")) if fixture_set else [])
        fixture_sources = {item["source_id"]: item for item in fixture_records}
        metadata_fields = ("source_type", "title", "canonical_url", "content_hash")
        metadata_matches = sum(
            all(getattr(item, field) == fixture_sources[item.source_id].get(field)
                if field != "canonical_url" else
                (str(item.canonical_url) if item.canonical_url else None)
                == fixture_sources[item.source_id].get(field)
                for field in metadata_fields)
            for item in sources if item.source_id in fixture_sources
        )
        tier_definitions = load_source_configuration().source_types
        observed_tiers = {tier_definitions[item.source_type].evidence_tier.value for item in usable
                          if item.source_type in tier_definitions}
        requested_tiers = {item.value for item in result.prepared_run.submitted.search.evidence_tiers}
        urls = [str(item.canonical_url) for item in sources if item.canonical_url]
        chunk_ids = {item.chunk_id for item in result.library.chunks}
        source_ids = {item.source_id for item in sources}
        return {"source_count": len(sources), "usable_source_count": len(usable),
                "required_type_count": len(required), "required_types_covered": len(required & observed),
                "required_types_missing": sorted(required - observed),
                "held_out_expected_types_missing": sorted(expected_types - observed),
                "held_out_relevant_ids_found": len(expected_ids & {item.source_id for item in usable}),
                "held_out_relevant_ids_expected": len(expected_ids),
                "fixture_metadata_matches": metadata_matches,
                "requested_tiers_missing": sorted(requested_tiers - observed_tiers),
                "duplicate_source_ids": len(sources) - len(source_ids),
                "duplicate_urls": len(urls) - len(set(urls)),
                "chunk_links_valid": all(item.source_id in source_ids for item in result.library.chunks)
                                     and len(chunk_ids) == len(result.library.chunks),
                "reported_gap_matches": (set(result.library.missing_required_source_types)
                                         == required - observed),
                "recovery_queries": result.library.recovery_query_count,
                "reason_codes": result.library.reason_codes}
    if stage == "critic":
        evaluations = result.score_evaluations
        chunk_sources = {item.chunk_id: item.source_id for item in result.library.chunks}
        source_ids = {item.source_id for item in result.source_manifest}
        citations = [ref for evaluation in evaluations for part in
                     [*evaluation.criteria, *evaluation.hard_gates] for ref in part.evidence]
        valid = sum(ref.source_id in source_ids and
                    (ref.chunk_id is None or chunk_sources.get(ref.chunk_id) == ref.source_id)
                    for ref in citations)
        return {"assessment_count": len(evaluations), "citation_count": len(citations),
                "valid_citation_count": valid, "invalid_citation_count": len(citations) - valid,
                "ranked_count": len(result.score_ranking)}
    proposals = [*result.final_proposals, *(item.proposal for item in result.additional_proposals)]
    return {"proposal_count": len(proposals),
            "cited_claim_count": sum(len(item.citations) for item in proposals),
            "verifier_accepted_count": sum(bool(item.evidence_audit and item.evidence_audit.accepted)
                                           for item in proposals),
            "verification_failure_count": len(result.proposal_failures)}


def audit(stage: str, result_path: Path, case_id: str, output: Path) -> dict:
    """Publish mechanical findings while keeping independent ratings pending."""
    result, digest = _load_result(result_path, case_id)
    report = {"stage": stage, "case_id": case_id, "split": "held_out",
              "run_sha256": digest, "review_status": "pending",
              "review_rows_prepared": len(_rows(stage, result, digest)),
              "mechanical": _mechanical(stage, result, case_id),
              "limitations": "Synthetic offline run; semantic quality requires independent review."}
    check_privacy(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")
    return report


def compare_critic(result_path: Path, comparison_path: Path, case_id: str,
                   output: Path) -> dict:
    """Compare repeat assessments only when request, evidence, and rubric match."""
    first, first_hash = _load_result(result_path, case_id)
    second, second_hash = _load_result(comparison_path, case_id)
    if first.prepared_run.evaluation != second.prepared_run.evaluation:
        raise ValueError("Critic comparison requires the same evaluation configuration")
    first_sources = {(item.source_id, item.content_hash) for item in first.source_manifest}
    second_sources = {(item.source_id, item.content_hash) for item in second.source_manifest}
    first_chunks = {(item.chunk_id, item.content_hash) for item in first.library.chunks}
    second_chunks = {(item.chunk_id, item.content_hash) for item in second.library.chunks}
    if first_sources != second_sources or first_chunks != second_chunks:
        raise ValueError("Critic comparison requires identical captured evidence")
    left = {item.candidate_id: item for item in first.score_evaluations}
    right = {item.candidate_id: item for item in second.score_evaluations}
    common = sorted(left.keys() & right.keys())
    first_candidates = {item.candidate_id: item for item in first.scout.candidates}
    second_candidates = {item.candidate_id: item for item in second.scout.candidates}
    if any(first_candidates.get(key) != second_candidates.get(key) for key in common):
        raise ValueError("Critic comparison requires matching candidate content")
    deviations = [abs(left[key].total_score - right[key].total_score) for key in common]
    report = {"stage": "critic_consistency", "case_id": case_id,
              "run_sha256": [first_hash, second_hash],
              "first_assessment_count": len(left), "second_assessment_count": len(right),
              "matched_candidate_count": len(common),
              "mean_absolute_score_difference": round(mean(deviations), 3) if deviations else None,
              "gate_agreement_count": sum(left[key].gate_passed == right[key].gate_passed
                                          for key in common),
              "limitations": "Only matching candidate IDs on identical saved evidence are comparable."}
    check_privacy(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")
    return report


async def audit_library_provider_failure(result_path: Path, case_id: str, output: Path) -> dict:
    """Replay a held-out Library request with an explicit failing fixture provider."""
    result, digest = _load_result(result_path, case_id)

    class FailingAdapter:
        async def search(self, query):
            raise SourceUnavailableError(query.provider_id, "synthetic provider outage")

    adapters = {provider.provider_id: FailingAdapter()
                for provider in result.prepared_run.search.providers}
    planner = LLMLibraryQueryPlanner(OfflineDemoClient(), max_output_tokens=1000)
    worker = LibraryWorker(adapters, planner)
    failure = None
    try:
        await worker.run(result.prepared_run.request, result.prepared_run.search)
    except SourceUnavailableError as error:
        failure = type(error).__name__
    report = {"stage": "library_provider_failure", "case_id": case_id,
              "split": "held_out", "base_run_sha256": digest,
              "failure_injected": "SourceUnavailableError", "observed_failure": failure,
              "required_branch_stopped": failure is not None,
              "limitations": "Synthetic fault injection; no live provider was contacted."}
    check_privacy(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")
    return report


def score(stage: str, result_path: Path, case_id: str, review_path: Path, output: Path, *,
          review_type: str) -> dict:
    """Score only completed independent labels bound to this exact saved run."""
    if stage not in STAGES or review_type not in ("human", "reference"):
        raise ValueError("stage and review_type must name supported evaluation modes")
    result, digest = _load_result(result_path, case_id)
    expected = {row["review_id"]: row for row in _rows(stage, result, digest)}
    with review_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not set([*COMMON, *LABELS[stage]]) <= set(reader.fieldnames):
            raise ValueError("review CSV is missing required columns")
        rows = list(reader)
    ids = [row.get("review_id") for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError("review rows must exactly match the saved stage outputs")
    for row in rows:
        baseline = expected[row["review_id"]]
        if any(row.get(key) != baseline[key] for key in ("run_sha256", "context_json")):
            raise ValueError("review context or run checksum was changed")
    ratings = _ratings(stage, rows)
    mechanical = _mechanical(stage, result, case_id)
    summary: dict = {"stage": stage, "case_id": case_id, "split": "held_out",
                     "run_sha256": digest, "review_count": len(ratings),
                     "reviewer_ids": sorted({row["reviewer_id"].strip() for row in rows}),
                     "mechanical": mechanical,
                     "review_status": "complete" if ratings else "not_evaluated",
                     "review_type": review_type,
                     "limitations": "Reviewed saved synthetic run; labels are independent of worker verdicts."}
    if stage == "library":
        source = [row for row in ratings if row["review_id"].startswith("source:")]
        summary["source_metrics"] = {field: {"passing": sum(row[field] for row in source),
                                             "total": len(source)} for field in LABELS[stage][:-1]}
        summary["gap_report_accurate"] = next(row["gap_report_accurate"] for row in ratings
                                               if row["review_id"] == "coverage")
    elif stage == "critic":
        judgments = {f"candidate:{item.candidate_id}": item for item in result.score_evaluations}
        comparisons = [(row, judgments[row["review_id"]]) for row in ratings]
        summary["score_mean_absolute_error"] = (round(mean(abs(row["reference_score"] - item.total_score)
                                                            for row, item in comparisons), 3)
                                                 if comparisons else None)
        summary["gate_confusion"] = {
            "true_accept": sum(row["reference_gate_passed"] and item.gate_passed for row, item in comparisons),
            "false_accept": sum(not row["reference_gate_passed"] and item.gate_passed for row, item in comparisons),
            "false_reject": sum(row["reference_gate_passed"] and not item.gate_passed for row, item in comparisons),
            "true_reject": sum(not row["reference_gate_passed"] and not item.gate_passed for row, item in comparisons),
        }
        summary["evidence_relevant_count"] = sum(row["evidence_relevant"] for row in ratings)
        summary["citations_valid_count"] = sum(row["citations_valid"] for row in ratings)
    else:
        for field in LABELS[stage][:-2]:
            summary[f"{field}_count"] = sum(row[field] for row in ratings)
        unsupported = sum(row["unsupported_claims"] for row in ratings)
        claims = sum(row["reviewed_claims"] for row in ratings)
        if any(row["unsupported_claims"] > row["reviewed_claims"] for row in ratings):
            raise ValueError("unsupported claim count exceeds independently reviewed claims")
        summary["reviewed_claims"] = claims
        summary["unsupported_claims"] = unsupported
        summary["unsupported_claim_rate"] = unsupported / claims if claims else None
        proposals = {f"proposal:{item.proposal_id}": item for item in
                     [*result.final_proposals,
                      *(record.proposal for record in result.additional_proposals)]}
        summary["verifier_false_accept_count"] = sum(
            (row["unsupported_claims"] > 0 or not row["supported"])
            and bool(proposals[row["review_id"]].evidence_audit
                     and proposals[row["review_id"]].evidence_audit.accepted)
            for row in ratings
        )
        summary["unreviewed_rejections"] = len(result.proposal_failures)
    check_privacy(summary)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)
        file.write("\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "score", "audit", "compare-critic", "audit-provider-failure"):
        command = commands.add_parser(name)
        command.add_argument("--stage", choices=STAGES, required=True)
        command.add_argument("--result", type=Path, required=True)
        command.add_argument("--case-id", required=True)
        command.add_argument("--output", type=Path, required=True)
        if name == "score":
            command.add_argument("--review", type=Path, required=True)
            command.add_argument("--review-type", choices=("human", "reference"), required=True)
        if name == "compare-critic":
            command.add_argument("--comparison-result", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        print(f"Prepared {prepare(args.stage, args.result, args.case_id, args.output)} review rows")
    elif args.command == "score":
        report = score(args.stage, args.result, args.case_id, args.review, args.output,
                       review_type=args.review_type)
        print(f"Scored {report['review_count']} review rows")
    elif args.command == "audit":
        report = audit(args.stage, args.result, args.case_id, args.output)
        print(f"Audited {report['review_rows_prepared']} outputs; independent review pending")
    else:
        if args.command == "compare-critic":
            if args.stage != "critic":
                parser.error("compare-critic requires --stage critic")
            report = compare_critic(args.result, args.comparison_result, args.case_id, args.output)
            print(f"Compared {report['matched_candidate_count']} matching assessments")
        else:
            if args.stage != "library":
                parser.error("audit-provider-failure requires --stage library")
            report = asyncio.run(audit_library_provider_failure(
                args.result, args.case_id, args.output
            ))
            print(f"Provider failure stopped required Library branch: {report['required_branch_stopped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
