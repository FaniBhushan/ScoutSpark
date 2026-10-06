"""Independent review sheets stay blind and bind labels to saved evidence."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.adapters import FrozenFixtureAdapter
from src.application.service import run_research
from src.models import InputRequest
from src.testing.demo import OfflineDemoClient
from evals.worker_quality.evaluate import (
    audit_library_provider_failure, compare_critic, prepare, score,
)


class WorkerQualityEvaluationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        case = json.loads(Path("evals/cases/held_out/mathematics_optimization_01.json").read_text())
        request = InputRequest.model_validate(case["expected_request"])
        adapters = {"frozen_fixture": FrozenFixtureAdapter(case["fixture_set"])}
        result = await run_research(request, OfflineDemoClient(), adapters)
        self.saved = self.root / "result.json"
        self.saved.write_text(result.model_dump_json(), encoding="utf-8")
        self.case_id = case["case_id"]

    def _review(self, stage, labels):
        review = self.root / f"{stage}.csv"
        prepare(stage, self.saved, self.case_id, review)
        with review.open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
            fields = list(rows[0])
        for row in rows:
            row["reviewer_id"] = "synthetic-test-reference"
            for field, value in labels.items():
                if stage != "library" or (field == "gap_report_accurate") == (
                    row["review_id"] == "coverage"
                ):
                    row[field] = str(value)
        with review.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return review, rows

    async def test_blind_critic_review_reports_reference_gate_errors(self):
        review, rows = self._review("critic", {
            "reference_score": 60, "reference_gate_passed": "no",
            "evidence_relevant": "yes", "citations_valid": "yes",
        })
        context = json.loads(rows[0]["context_json"])
        self.assertNotIn("total_score", context)
        self.assertNotIn("hard_gates", context)
        report = score("critic", self.saved, self.case_id, review,
                       self.root / "critic-summary.json", review_type="reference")
        self.assertEqual(report["review_count"], len(rows))
        self.assertEqual(report["gate_confusion"]["false_accept"], len(rows))

    async def test_proposal_review_is_separate_from_verifier_and_rejects_tampering(self):
        review, rows = self._review("proposal", {
            "complete": "yes", "actionable": "yes", "unknowns_explicit": "yes",
            "idea_aligned": "yes", "supported": "no",
            "reviewed_claims": 2, "unsupported_claims": 1,
        })
        context = json.loads(rows[0]["context_json"])
        self.assertNotIn("evidence_audit", context["proposal"])
        report = score("proposal", self.saved, self.case_id, review,
                       self.root / "proposal-summary.json", review_type="reference")
        self.assertEqual(report["unsupported_claim_rate"], 0.5)
        self.assertEqual(report["verifier_false_accept_count"], len(rows))
        with review.open("a", encoding="utf-8") as file:
            file.write("\n")
        # The source hash binds all review rows to the exact saved run.
        self.saved.write_text(self.saved.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum"):
            score("proposal", self.saved, self.case_id, review,
                  self.root / "tampered-summary.json", review_type="reference")

    async def test_library_coverage_and_required_provider_failure_are_recorded(self):
        review, rows = self._review("library", {
            "relevant": "yes", "metadata_accurate": "yes",
            "citation_valid": "yes", "gap_report_accurate": "yes",
        })
        report = score("library", self.saved, self.case_id, review,
                       self.root / "library-summary.json", review_type="reference")
        self.assertEqual(report["source_metrics"]["relevant"]["total"], len(rows) - 1)
        failure = await audit_library_provider_failure(
            self.saved, self.case_id, self.root / "provider-failure.json"
        )
        self.assertTrue(failure["required_branch_stopped"])
        comparison = compare_critic(self.saved, self.saved, self.case_id,
                                    self.root / "comparison.json")
        self.assertEqual(comparison["mean_absolute_score_difference"], 0)
