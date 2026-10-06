"""User-requested Critic reruns over the evidence already collected for a run."""

from __future__ import annotations

from datetime import datetime, timezone

from src.models import (
    CriticReevaluationRecord,
    CriticReevaluationRequest,
    CriticResult,
    CriterionDefinition,
    EvaluationConfiguration,
    OrchestrationResult,
    ReevaluationRankedCandidate,
    RunBudgetUsage,
    evaluation_configuration_sha256,
)
from src.guardrails import check_privacy
from src.orchestration.coordinator import Orchestrator
from src.retrieval import HybridInMemoryRetriever, load_retrieval_index_configuration
from src.runtime.budgets import BudgetedLLMClient, RunBudget
from src.workers.critic_worker import CriticWorker
from src.llm.critic_llm import LLMCandidateJudge


def resolve_reevaluation_configuration(
    base: EvaluationConfiguration, request: CriticReevaluationRequest | dict,
) -> EvaluationConfiguration:
    """Resolve reviewed weights and additive project gates, preserving base gates."""
    change = CriticReevaluationRequest.validate_against(request, base)
    check_privacy(change)
    criteria = dict(base.criteria)
    if change.weights is not None:
        criteria = {
            key: CriterionDefinition.model_validate({
                **definition.model_dump(), "weight": change.weights[key],
            })
            for key, definition in base.criteria.items()
        }
    gates = {**base.hard_gates, **change.additional_project_gates}
    return EvaluationConfiguration.model_validate({
        **base.model_dump(mode="python"), "criteria": criteria, "hard_gates": gates,
    })


async def reevaluate_existing_candidates(
    result: OrchestrationResult,
    llm_client,
    changes: CriticReevaluationRequest | dict,
    *,
    tracer=None,
) -> OrchestrationResult:
    """Re-score all retained candidates using saved Library chunks and remaining run budget."""
    if result.prepared_run is None:
        raise ValueError("this saved result has no resolved configuration for re-evaluation")
    if not result.library.chunks:
        raise ValueError("this run has no retained evidence chunks to re-evaluate against")
    configuration = resolve_reevaluation_configuration(result.prepared_run.evaluation, changes)
    candidates_by_id = {}
    for recovery in result.recovery_history:
        for candidate in recovery.previous_candidates:
            candidates_by_id.setdefault(candidate.candidate_id, candidate)
    candidates_by_id.update({candidate.candidate_id: candidate for candidate in result.scout.candidates})
    candidates = list(candidates_by_id.values())
    if not candidates:
        raise ValueError("this run has no retained candidates to re-evaluate")

    pricing = getattr(llm_client, "pricing", None)
    budget = RunBudget(result.prepared_run.budgets, pricing=pricing, tracer=tracer)
    if result.budget_usage is not None:
        budget.restore(result.budget_usage.model_dump(mode="json"))
    client = BudgetedLLMClient(llm_client, budget)
    retrieval = HybridInMemoryRetriever(
        result.library.chunks, load_retrieval_index_configuration()
    )
    worker = CriticWorker(
        retrieval,
        LLMCandidateJudge(client, max_output_tokens=2000, tracer=tracer),
        tracer=tracer,
    )
    request = result.prepared_run.request.model_copy(deep=True)
    critic = CriticResult.model_validate(await worker.run(
        request, candidates, result.library, configuration,
    ))
    ranking = Orchestrator._rank(candidates, critic)
    record = CriticReevaluationRecord(
        version=len(result.critic_reevaluations) + 1,
        configuration=configuration,
        configuration_sha256=evaluation_configuration_sha256(configuration),
        critic=critic,
        ranking=[ReevaluationRankedCandidate.model_validate(row.model_dump()) for row in ranking],
        created_at=datetime.now(timezone.utc),
    )
    data = result.model_dump(mode="python")
    data["critic_reevaluations"] = [*result.critic_reevaluations, record]
    data["budget_usage"] = RunBudgetUsage.model_validate(budget.snapshot())
    return OrchestrationResult.model_validate(data)
