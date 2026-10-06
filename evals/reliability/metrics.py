"""Aggregate repeated-run completion, count, integrity, and stability metrics."""

from __future__ import annotations

from itertools import combinations
from statistics import fmean, pstdev


def _rate(values: list[float | None]) -> dict:
    present = [float(value) for value in values if value is not None]
    return {
        "evaluated": len(present),
        "not_evaluated": len(values) - len(present),
        "mean": fmean(present) if present else None,
        "population_stddev": pstdev(present) if len(present) > 1 else 0.0 if present else None,
        "minimum": min(present) if present else None,
        "maximum": max(present) if present else None,
    }


def _spearman(left: list[str], right: list[str]) -> float | None:
    common = set(left) & set(right)
    if len(common) < 2:
        return None
    left_rank = {item: index for index, item in enumerate(left) if item in common}
    right_rank = {item: index for index, item in enumerate(right) if item in common}
    n = len(common)
    # Each list has unique candidate fingerprints, so no tied ranks occur.
    d_squared = sum((left_rank[item] - right_rank[item]) ** 2 for item in common)
    return 1 - (6 * d_squared) / (n * (n * n - 1))


def aggregate(records: list[dict], target: int, thresholds: dict,
              finalist_target: int | None = None) -> dict:
    """Calculate preregistered rates and candidate-set/rank stability."""
    count_values, finalist_values, shortfall_values = [], [], []
    for row in records:
        result = row.get("result") or {}
        proposals = result.get("final_proposals", [])
        scout_count = len(result.get("scout", {}).get("candidates", []))
        count_values.append(float(scout_count >= target))
        finalist_values.append(float(len(proposals) == (finalist_target or target)))
        requested = row.get("proposal_counts", {}).get("requested", target)
        reported = row.get("proposal_counts", {}).get("target_met")
        shortfall_values.append(float(reported is (len(proposals) == requested)))

    metrics = {
        "valid_result_completion_rate": _rate([float(row.get("outcome") == "passed") for row in records]),
        "candidate_count_target_rate": _rate(count_values),
        "finalist_count_target_rate": _rate(finalist_values),
        "citation_integrity_rate": _rate([
            _check_value(row, "citation_integrity") for row in records
        ]),
        "evidence_support_rate": _rate([_check_value(row, "proposal_verification") for row in records]),
        "score_consistency_rate": _rate([_check_value(row, "scoring_consistency") for row in records]),
        "ranking_consistency_rate": _rate([_check_value(row, "ranking_consistency") for row in records]),
        "shortfall_reporting_accuracy": _rate(shortfall_values),
    }
    lists = [row.get("candidate_fingerprints", []) for row in records]
    rank_lists = [row.get("ranked_fingerprints", []) for row in records]
    score_maps = [row.get("candidate_scores", {}) for row in records]
    set_overlaps, correlations = [], []
    for (index, left), (other_index, right) in combinations(enumerate(lists), 2):
        union = set(left) | set(right)
        set_overlaps.append(len(set(left) & set(right)) / len(union) if union else 1.0)
        rho = _spearman(rank_lists[index], rank_lists[other_index])
        if rho is not None:
            correlations.append(rho)
    score_differences = [
        abs(score_maps[index][fingerprint] - score_maps[other_index][fingerprint])
        for index, other_index in combinations(range(len(records)), 2)
        for fingerprint in score_maps[index].keys() & score_maps[other_index].keys()
    ]
    metrics["top_k_overlap_mean"] = _rate(set_overlaps)
    metrics["rank_spearman_mean"] = _rate(correlations)
    metrics["score_mae_mean"] = _rate(score_differences)

    minimum = thresholds["minimum_repeats"]
    evaluated = len(records)
    decision = "insufficient_sample" if evaluated < minimum else "pass"
    if evaluated >= minimum:
        for name, specification in thresholds["metrics"].items():
            value = metrics[name]["mean"]
            if value is None:
                decision = "fail"
            elif "minimum" in specification and value < specification["minimum"]:
                decision = "fail"
            elif "maximum" in specification and value > specification["maximum"]:
                decision = "fail"
    return {"sample_size": evaluated, "minimum_repeats": minimum,
            "metrics": metrics, "decision": decision}


def _check_value(row: dict, key: str) -> float | None:
    value = row.get("checks", {}).get(key)
    return None if value is None else float(value is True)
