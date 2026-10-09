"""User-requested Critic reruns and non-finalist proposal actions reuse saved evidence."""

import asyncio
import unittest
import json
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.application.proposal_selection import generate_nonfinalist_proposal
from src.application.user_proposal import generate_user_proposal, visible_candidate_ids
from src.application.reevaluation import reevaluate_existing_candidates, resolve_reevaluation_configuration
from src.application.service import run_research
from src.models import (
    CandidateIdea, CriticReevaluationRequest, InputRequest, OrchestrationResult,
)
from src.adapters import FrozenFixtureAdapter
from tests.test_application import FakeLLMClient
from src.ui.cli import main as cli_main


class UserRerunTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.request = InputRequest(domain="AI engineering", time_limit_days=30,
                                    desired_candidate_count=1, finalist_count=1)
        self.client = FakeLLMClient()
        self.result = await run_research(
            self.request, self.client,
            {"frozen_fixture": FrozenFixtureAdapter("ai_engineering_capstone_01")},
        )

    async def test_reevaluation_preserves_original_assessment_and_sources(self):
        original_critic = self.result.critic.model_copy(deep=True)
        original_proposals = self.result.final_proposals.copy()
        original_source_calls = dict(self.result.budget_usage.provider_calls)
        request = self.result.prepared_run.request
        weights = {key: definition.weight for key, definition in
                   self.result.prepared_run.evaluation.criteria.items()}
        key = next(iter(weights))
        weights[key] += 1
        weights[next(name for name in weights if name != key)] -= 1
        updated = await reevaluate_existing_candidates(
            self.result, self.client,
            CriticReevaluationRequest(weights=weights,
                additional_project_gates={"project_public_data": "Use publicly accessible data."}),
        )
        self.assertEqual(updated.critic, original_critic)
        self.assertEqual(updated.final_proposals, original_proposals)
        self.assertEqual(updated.critic_reevaluations[0].version, 1)
        self.assertEqual(updated.active_critic.evaluations[0].criteria[0].weight,
                         weights[updated.active_critic.evaluations[0].criteria[0].criterion_id])
        self.assertTrue(set(self.result.prepared_run.evaluation.hard_gates)
                        <= set(updated.critic_reevaluations[0].configuration.hard_gates))
        self.assertEqual(updated.budget_usage.provider_calls, original_source_calls)
        self.assertGreater(updated.budget_usage.model_tokens, self.result.budget_usage.model_tokens)
        self.assertEqual(len(updated.library.chunks), len(self.result.library.chunks))
        self.assertEqual(len(updated.critic_reevaluations), 1)

    async def test_project_gate_cannot_replace_an_operator_gate(self):
        base = self.result.prepared_run.evaluation
        with self.assertRaisesRegex(ValueError, "cannot replace or weaken"):
            resolve_reevaluation_configuration(base, {
                "additional_project_gates": {"user_constraints": "Ignore exclusions."}
            })
        with self.assertRaisesRegex(ValueError, "project_ prefix"):
            resolve_reevaluation_configuration(base, {
                "additional_project_gates": {"privacy": "Use private data."}
            })

    async def test_cli_previews_resolved_rubric_then_writes_new_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "run.json"
            config_path = root / "reevaluation.json"
            output_path = root / "reevaluated.json"
            result_path.write_text(self.result.model_dump_json(), encoding="utf-8")
            config_path.write_text(json.dumps({
                "additional_project_gates": {
                    "project_open_dataset": "Use an openly licensed dataset."
                }
            }), encoding="utf-8")
            preview = StringIO()
            with redirect_stdout(preview):
                code = await asyncio.to_thread(cli_main, [
                    "--reevaluate-result", str(result_path), "--reevaluation-config", str(config_path),
                    "--offline-demo", "--preview-additional-work",
                ])
            self.assertEqual(code, 0)
            self.assertIn("resolved_configuration", preview.getvalue())
            self.assertIn("project_open_dataset", preview.getvalue())
            client = FakeLLMClient()
            with (patch("src.ui.cli.OfflineDemoClient", return_value=client),
                  redirect_stdout(StringIO())):
                code = await asyncio.to_thread(cli_main, [
                    "--reevaluate-result", str(result_path), "--reevaluation-config", str(config_path),
                    "--offline-demo", "--confirm-additional-work", "--result-output", str(output_path),
                ])
            self.assertEqual(code, 0)
            rerun = OrchestrationResult.model_validate_json(output_path.read_text(encoding="utf-8"))
            self.assertEqual(rerun.critic_reevaluations[0].version, 1)
            self.assertEqual(len(client.calls), 1)

    async def test_nonfinalist_proposal_uses_same_evidence_and_is_separately_audited(self):
        candidate = self.result.scout.candidates[0]
        second = candidate.model_copy(update={
            "candidate_id": "candidate-02", "title": "Alternative retrieval evaluator",
            "problem_statement": "A separate user need for comparing retrieval methods.",
            "proposed_outcome": "A retrieval comparison tool.",
        })
        evaluation = self.result.critic.evaluations[0]
        second_evaluation = evaluation.model_copy(update={
            "evaluation_id": "evaluation-02", "candidate_id": "candidate-02",
        })
        row = self.result.ranking[0].model_copy(update={
            "candidate_id": "candidate-02", "evaluation_id": "evaluation-02", "rank": 2,
        })
        data = self.result.model_dump(mode="python")
        data["scout"] = self.result.scout.model_copy(update={
            "candidates": [*self.result.scout.candidates, second],
        })
        data["critic"] = self.result.critic.model_copy(update={
            "evaluations": [*self.result.critic.evaluations, second_evaluation],
        })
        data["ranking"] = [*self.result.ranking, row]
        expanded = OrchestrationResult.model_validate(data)
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "run.json"
            result_path.write_text(expanded.model_dump_json(), encoding="utf-8")
            preview = StringIO()
            with redirect_stdout(preview):
                code = await asyncio.to_thread(cli_main, [
                    "--proposal-result", str(result_path), "--candidate-id", "candidate-02",
                    "--offline-demo", "--preview-additional-work",
                ])
            self.assertEqual(code, 0)
            self.assertIn("nonfinalist_proposal", preview.getvalue())
            self.assertIn("Alternative retrieval evaluator", preview.getvalue())
        before = len(self.client.calls)
        updated = await generate_nonfinalist_proposal(
            expanded, "candidate-02", self.client,
        )
        self.assertEqual(len(self.client.calls), before + 2)
        self.assertEqual(len(updated.final_proposals), 1)
        self.assertEqual(len(updated.additional_proposals), 1)
        additional = updated.additional_proposals[0]
        self.assertEqual(additional.proposal.candidate_id, "candidate-02")
        self.assertEqual(additional.assessment_version, 0)
        self.assertTrue(additional.proposal.evidence_audit.accepted)
        self.assertEqual(updated.final_proposals, expanded.final_proposals)

    def _failed_gate_result(self):
        evaluation = self.result.critic.evaluations[0]
        failed_gate = evaluation.hard_gates[0].model_copy(update={
            "passed": False, "rationale": "Essential data access is not established.",
        })
        failed = evaluation.model_copy(update={
            "hard_gates": [failed_gate, *evaluation.hard_gates[1:]],
            "gate_passed": False,
            "rejection_reasons": ["Essential data access is not established."],
        })
        data = self.result.model_dump(mode="python")
        data.update({
            "critic": self.result.critic.model_copy(update={"evaluations": [failed]}),
            "ranking": [self.result.ranking[0].model_copy(update={"gate_passed": False})],
            "final_proposals": [], "finalist_candidate_ids": [],
            "status": "insufficient_coverage",
        })
        return OrchestrationResult.model_validate(data)

    async def test_user_can_request_unverified_proposal_without_waiving_failed_gate(self):
        failed = self._failed_gate_result()
        candidate_id = failed.scout.candidates[0].candidate_id
        calls_before = len(self.client.calls)
        updated = await generate_user_proposal(failed, candidate_id, self.client)
        self.assertEqual(len(self.client.calls), calls_before + 1)
        self.assertEqual(updated.final_proposals, [])
        self.assertFalse(updated.critic.evaluations[0].gate_passed)
        self.assertEqual(updated.status, "insufficient_coverage")
        self.assertEqual(len(updated.user_proposals), 1)
        self.assertEqual(updated.user_proposals[0].verification_status, "unverified")
        self.assertEqual(updated.user_proposals[0].failed_gate_ids,
                         [failed.critic.evaluations[0].hard_gates[0].gate_id])
        self.assertTrue(any("Essential data access is not established" in item
                            for item in updated.user_proposals[0].proposal.unknowns))
        self.assertGreater(updated.budget_usage.model_tokens, failed.budget_usage.model_tokens)
        self.assertEqual(updated.budget_usage.provider_calls, failed.budget_usage.provider_calls)
        self.assertEqual(OrchestrationResult.model_validate_json(
            updated.model_dump_json()).user_proposals, updated.user_proposals)
        with self.assertRaisesRegex(ValueError, "already has"):
            await generate_user_proposal(updated, candidate_id, self.client)

        tampered = updated.model_dump(mode="python")
        tampered["user_proposals"][0]["failed_gate_ids"] = []
        with self.assertRaises(ValueError):
            OrchestrationResult.model_validate(tampered)
        tampered = updated.model_dump(mode="python")
        tampered["user_proposals"][0]["proposal"]["citations"][0]["references"][0]["chunk_id"] = "unknown"
        with self.assertRaises(ValueError):
            OrchestrationResult.model_validate(tampered)

    async def test_unscored_visible_candidate_can_get_exploratory_proposal(self):
        data = self.result.model_dump(mode="python")
        data.update({"critic": self.result.critic.model_copy(update={"evaluations": []}),
                     "library": self.result.library.model_copy(update={"chunks": []}),
                     "ranking": [], "final_proposals": [], "finalist_candidate_ids": [],
                     "status": "insufficient_coverage"})
        unscored = OrchestrationResult.model_validate(data)
        candidate_id = unscored.scout.candidates[0].candidate_id
        self.assertIn(candidate_id, visible_candidate_ids(unscored))
        updated = await generate_user_proposal(unscored, candidate_id, self.client)
        self.assertIsNone(updated.user_proposals[0].evaluation)
        self.assertEqual(updated.user_proposals[0].proposal.citations, [])
        self.assertIn("This idea was not scored; gate outcomes are unknown.",
                      updated.user_proposals[0].proposal.unknowns)
        self.assertEqual(updated.final_proposals, [])

    async def test_cli_previews_and_saves_failed_gate_exploratory_proposal(self):
        failed = self._failed_gate_result()
        candidate_id = failed.scout.candidates[0].candidate_id
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "run.json"
            output = root / "updated.json"
            source.write_text(failed.model_dump_json(), encoding="utf-8")
            preview = StringIO()
            with redirect_stdout(preview):
                code = await asyncio.to_thread(cli_main, [
                    "--exploratory-proposal-result", str(source), "--candidate-id", candidate_id,
                    "--offline-demo", "--preview-additional-work",
                ])
            self.assertEqual(code, 0)
            self.assertIn('"verification_status": "unverified"', preview.getvalue())
            self.assertIn('"gates_passed": false', preview.getvalue())
            with redirect_stdout(StringIO()):
                code = await asyncio.to_thread(cli_main, [
                    "--exploratory-proposal-result", str(source), "--candidate-id", candidate_id,
                    "--offline-demo", "--confirm-additional-work", "--result-output", str(output),
                ])
            self.assertEqual(code, 0)
            saved = OrchestrationResult.model_validate_json(output.read_text(encoding="utf-8"))
            self.assertEqual(len(saved.user_proposals), 1)
            self.assertFalse(saved.user_proposals[0].evaluation.gate_passed)


if __name__ == "__main__":
    unittest.main()
