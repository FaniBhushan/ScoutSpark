"""Reliability aggregation uses all repeated runs and registered thresholds."""

import unittest

from evals.reliability.metrics import _spearman, aggregate
from evals.reliability.__main__ import _decorate


class ReliabilityMetricTests(unittest.TestCase):
    def test_candidate_fingerprints_include_ideas_without_proposals(self):
        record = {"result": {"scout": {"candidates": [
            {"candidate_id": "idea-a", "title": "A"},
            {"candidate_id": "idea-b", "title": "B"},
        ]}, "final_proposals": [{"candidate_id": "idea-a", "title": "A"}]}}
        decorated = _decorate(record, 1, 2)
        self.assertEqual(len(decorated["candidate_fingerprints"]), 2)

    def test_rank_correlation_ignores_unmatched_positions(self):
        self.assertEqual(_spearman(["a", "extra", "b"], ["a", "b"]), 1.0)

    def test_sample_below_preregistered_minimum_is_not_a_pass(self):
        summary = aggregate([], target=2, thresholds={"minimum_repeats": 10, "metrics": {}})
        self.assertEqual(summary["decision"], "insufficient_sample")
        self.assertEqual(summary["sample_size"], 0)

    def test_rates_include_variance_and_shortfall_accuracy(self):
        checks = {key: True for key in (
            "citation_integrity", "proposal_verification", "scoring_consistency", "ranking_consistency"
        )}
        records = [
            {"outcome": "passed", "checks": checks,
             "proposal_counts": {"requested": 2, "returned": 2, "target_met": True},
             "result": {"scout": {"candidates": [{}, {}]}, "ranking": [{}, {}],
                        "final_proposals": [{}, {}]},
             "candidate_fingerprints": ["a", "b"], "ranked_fingerprints": ["a", "b"],
             "candidate_scores": {"a": 4.0, "b": 3.0}},
            {"outcome": "error", "checks": {},
             "proposal_counts": {"requested": 2, "returned": 1, "target_met": False},
             "result": {"scout": {"candidates": [{}]}, "ranking": [{}, {}],
                        "final_proposals": [{}]},
             "candidate_fingerprints": ["a"], "ranked_fingerprints": ["a"],
             "candidate_scores": {"a": 3.5}},
        ]
        thresholds = {"minimum_repeats": 2, "metrics": {}}
        summary = aggregate(records, target=2, thresholds=thresholds)
        self.assertEqual(summary["metrics"]["valid_result_completion_rate"]["mean"], 0.5)
        self.assertEqual(summary["metrics"]["valid_result_completion_rate"]["population_stddev"], 0.5)
        self.assertEqual(summary["metrics"]["shortfall_reporting_accuracy"]["mean"], 1.0)
        self.assertEqual(summary["metrics"]["scorecard_count_target_rate"]["mean"], 1.0)
        self.assertEqual(summary["metrics"]["verified_proposal_count_target_rate"]["mean"], 0.5)
        self.assertEqual(summary["metrics"]["top_k_overlap_mean"]["mean"], 0.5)
        self.assertEqual(summary["metrics"]["score_mae_mean"]["mean"], 0.5)

    def test_registered_threshold_failure_is_reported(self):
        record = {"outcome": "error", "checks": {}, "proposal_counts": {"requested": 1,
                  "returned": 0, "target_met": False}, "result": {},
                  "candidate_fingerprints": [], "ranked_fingerprints": []}
        thresholds = {"minimum_repeats": 1,
                      "metrics": {"valid_result_completion_rate": {"minimum": 0.9}}}
        summary = aggregate([record], 1, thresholds)
        self.assertEqual(summary["decision"], "fail")
        self.assertEqual(summary["metrics"]["scorecard_count_target_rate"]["mean"], 0.0)
        self.assertEqual(summary["metrics"]["verified_proposal_count_target_rate"]["mean"], 0.0)


if __name__ == "__main__":
    unittest.main()
