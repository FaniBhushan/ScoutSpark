"""Create one evidence-verified detailed proposal for a reviewed non-finalist."""

from __future__ import annotations

from src.application.finalization import finalize_proposals
from src.llm.proposal_llm import LLMProposalWriter
from src.llm.proposal_verifier import LLMProposalVerifier
from src.models import (
    AdditionalProposalRecord,
    CriticResult,
    OrchestrationResult,
    RankedCandidate,
    RunBudgetUsage,
    evaluation_configuration_sha256,
)
from src.runtime.budgets import BudgetedLLMClient, RunBudget


async def generate_nonfinalist_proposal(
    result: OrchestrationResult,
    candidate_id: str,
    llm_client,
    *,
    tracer=None,
) -> OrchestrationResult:
    """Draft only a gate-passing, non-finalist candidate from retained evidence."""
    if result.prepared_run is None:
        raise ValueError("this saved result has no resolved run budget")
    if candidate_id in result.score_finalist_candidate_ids:
        raise ValueError("the selected candidate is already in the default finalist set")
    if any(item.proposal.candidate_id == candidate_id for item in result.additional_proposals):
        raise ValueError("this candidate already has an additional proposal")
    active_critic = CriticResult(evaluations=result.score_evaluations)
    evaluation = next((item for item in active_critic.evaluations
                       if item.candidate_id == candidate_id), None)
    if evaluation is None:
        raise ValueError("the selected candidate has no retained Critic assessment")
    if not evaluation.gate_passed:
        raise ValueError("the selected candidate failed a hard gate and is not proposal-eligible")
    candidate_ids = {item.candidate_id for item in result.scout.candidates}
    candidate_ids.update(candidate.candidate_id for attempt in result.recovery_history
                          for candidate in attempt.previous_candidates)
    if candidate_id not in candidate_ids:
        raise ValueError("the selected candidate is not part of this run")
    if not result.library.chunks:
        raise ValueError("the run has no retained evidence passages for proposal writing")

    pricing = getattr(llm_client, "pricing", None)
    budget = RunBudget(result.prepared_run.budgets, pricing=pricing, tracer=tracer)
    if result.budget_usage is not None:
        budget.restore(result.budget_usage.model_dump(mode="json"))
    client = BudgetedLLMClient(llm_client, budget)
    writer = LLMProposalWriter(client, max_output_tokens=4000, tracer=tracer)
    verifier = LLMProposalVerifier(client, max_output_tokens=2000, tracer=tracer)

    active_ranking = result.score_ranking
    active_configuration = (result.critic_reevaluations[-1].configuration
                            if result.critic_reevaluations else result.prepared_run.evaluation)
    version = len(result.critic_reevaluations)
    # Finalization's strict result validator ties every proposal to one assessment
    # and ranking. Build a temporary snapshot of the selected assessment version;
    # the persisted original result and finalist proposals remain untouched.
    candidates = {item.candidate_id: item for attempt in result.recovery_history
                  for item in attempt.previous_candidates}
    candidates.update({item.candidate_id: item for item in result.scout.candidates})
    data = result.model_dump(mode="python")
    data.update({
        "scout": result.scout.model_copy(update={"candidates": list(candidates.values())}),
        "critic": active_critic,
        "ranking": [RankedCandidate.model_validate(item.model_dump()) for item in active_ranking],
        "critic_reevaluations": [],
        "final_proposals": [],
        "finalist_candidate_ids": [],
        "additional_proposals": [],
        "proposal_failures": {},
        "proposal_failure_codes": {},
        "review_decisions": [],
        "recovery_history": [],
    })
    snapshot = OrchestrationResult.model_validate(data)
    temporary = await finalize_proposals(
        result.prepared_run.request.model_copy(update={"finalist_count": 1}),
        snapshot, writer, verifier,
        allow_provisional_narrative=active_configuration.allow_provisional_narrative,
        tracer=tracer, selected_candidate_ids=[candidate_id],
    )
    data = result.model_dump(mode="python")
    data["budget_usage"] = RunBudgetUsage.model_validate(budget.snapshot())
    if temporary.final_proposals:
        data["additional_proposals"] = [
            *result.additional_proposals,
            AdditionalProposalRecord(
                assessment_version=version,
                assessment_configuration_sha256=evaluation_configuration_sha256(active_configuration),
                evaluation=evaluation,
                proposal=temporary.final_proposals[0],
            ),
        ]
        failures = dict(result.proposal_failures)
        failures.pop(candidate_id, None)
        data["proposal_failures"] = failures
        failure_codes = dict(result.proposal_failure_codes)
        failure_codes.pop(candidate_id, None)
        data["proposal_failure_codes"] = failure_codes
    else:
        data["proposal_failures"] = {**result.proposal_failures, **temporary.proposal_failures}
        data["proposal_failure_codes"] = {
            **result.proposal_failure_codes, **temporary.proposal_failure_codes,
        }
        data["warnings"] = list(dict.fromkeys([*result.warnings, *temporary.warnings]))
    return OrchestrationResult.model_validate(data)
