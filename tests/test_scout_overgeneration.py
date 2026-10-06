"""Scout uses a separate bounded internal target without changing user counts."""

import unittest
from datetime import datetime, timezone

from src.models import CandidateIdea, InputRequest, ResolvedSearchConfiguration, ScoutQuery, SourceRecord
from src.models.source_record import RetrievalStatus
from src.orchestration.coordinator import Orchestrator, OrchestrationError
from src.workers.scout_worker import ScoutWorker


class FixedPlanner:
    async def plan(self, request, search):
        return [ScoutQuery(query_id="scout-q-01", provider_id="fixture", text="research",
                           source_types=["dataset"], content_types=["text"], max_results=1)]


class FixedAdapter:
    async def search(self, query):
        return [SourceRecord(
            source_id="source-1", provider="fixture", source_type="dataset",
            title="Evidence", captured_at=datetime.now(timezone.utc), query_id=query.query_id,
            content_hash="evidence", retrieval_status=RetrievalStatus.SUCCESS,
            abstract_or_snippet="Evidence for user need.",
        )]


class EmptyAdapter:
    async def search(self, query):
        return []


class TargetGenerator:
    def __init__(self, count=None):
        self.request = None
        self.count = count

    async def generate_with_metrics(self, request, sources):
        self.request = request
        count = self.count if self.count is not None else request.desired_candidate_count
        ideas = [CandidateIdea(
            candidate_id=f"raw-{index}", title=f"Idea {index}",
            problem_statement=f"Problem {index}", target_users=["Students"],
            proposed_outcome=f"Outcome {index}", why_it_matters="A testable hypothesis.",
            evidence=[{"source_id": "source-1"}],
        ) for index in range(count)]
        return ideas, {"generated_candidate_count": count, "batch_count": 3}


class ScoutOvergenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.request = InputRequest(domain="AI engineering", time_limit_days=30,
                                    desired_candidate_count=5, finalist_count=2)
        self.search = ResolvedSearchConfiguration(
            domain="AI engineering", providers=[{"provider_id": "fixture",
            "source_types": ["dataset"], "content_types": ["text"]}],
            content_types=["text"], max_queries=4, max_results_per_query=3,
            max_sources=4, minimum_source_count=1,
        )

    async def test_target_is_ceil_one_point_five_and_preserves_user_request(self):
        generator = TargetGenerator()
        result = await ScoutWorker({"fixture": FixedAdapter()}, FixedPlanner(), generator).run(
            self.request, self.search
        )
        self.assertEqual(generator.request.desired_candidate_count, 8)
        self.assertEqual(self.request.desired_candidate_count, 5)
        self.assertEqual(len(result.candidates), 8)
        self.assertEqual(result.generation_target_count, 8)
        self.assertEqual(result.generation_batch_count, 3)
        Orchestrator._validate_branch_results(self.request, result,
            type("Library", (), {"sources": [], "chunks": []})())

    async def test_partial_internal_target_is_measured_and_never_filled(self):
        generator = TargetGenerator(count=3)
        result = await ScoutWorker({"fixture": FixedAdapter()}, FixedPlanner(), generator).run(
            self.request, self.search
        )
        self.assertEqual(len(result.candidates), 3)
        self.assertIn("underproduction", result.reason_codes)
        self.assertTrue(any("3 of 8" in warning for warning in result.warnings))

    async def test_unavailable_sources_still_record_internal_target(self):
        result = await ScoutWorker({"fixture": EmptyAdapter()}, FixedPlanner(),
                                   TargetGenerator()).run(self.request, self.search)
        self.assertEqual(result.candidates, [])
        self.assertEqual(result.generation_target_count, 8)
        self.assertIn("source_unavailable", result.reason_codes)

    def test_join_rejects_candidates_above_internal_overgeneration_target(self):
        candidates = [CandidateIdea(
            candidate_id=f"candidate-{index}", title=f"Idea {index}",
            problem_statement=f"Problem {index}", target_users=["Students"],
            proposed_outcome=f"Outcome {index}", why_it_matters="A testable hypothesis.",
            evidence=[{"source_id": "source-1"}],
        ) for index in range(9)]
        scout = type("Scout", (), {"candidates": candidates})()
        library = type("Library", (), {"sources": [], "chunks": []})()
        with self.assertRaises(OrchestrationError):
            Orchestrator._validate_branch_results(self.request, scout, library)


if __name__ == "__main__":
    unittest.main()
