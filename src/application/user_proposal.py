"""Draft an explicitly requested exploratory proposal from a saved run."""

from __future__ import annotations

from datetime import datetime, timezone

from src.llm.prompt_call import call_prompt
from src.models import (
    ExploratoryProposalDraft,
    OrchestrationResult,
    RunBudgetUsage,
    UserRequestedProposal,
)
from src.runtime.budgets import BudgetedLLMClient, RunBudget


def visible_candidate_ids(result: OrchestrationResult) -> list[str]:
    """Match the scorecards and unscored ideas actually rendered in the UI."""
    count = (result.prepared_run.request.desired_candidate_count if result.prepared_run
             else len(result.scout.candidates))
    ranked = [row.candidate_id for row in result.score_ranking[:count]]
    scored = {item.candidate_id for item in result.score_evaluations}
    unscored = [item.candidate_id for item in result.scout.candidates
                if item.candidate_id not in scored]
    return list(dict.fromkeys([*ranked, *unscored]))


async def generate_user_proposal(
    result: OrchestrationResult,
    candidate_id: str,
    llm_client,
    *,
    tracer=None,
) -> OrchestrationResult:
    """Spend remaining run budget for a labeled draft without changing gate outcomes."""
    if result.prepared_run is None:
        raise ValueError("this saved result has no resolved run budget")
    if candidate_id not in visible_candidate_ids(result):
        raise ValueError("the selected candidate is not visible in this result")
    if any(item.candidate.candidate_id == candidate_id for item in result.user_proposals):
        raise ValueError("this candidate already has a user-requested proposal")

    candidates = {item.candidate_id: item for attempt in result.recovery_history
                  for item in attempt.previous_candidates}
    candidates.update({item.candidate_id: item for item in result.scout.candidates})
    candidate = candidates[candidate_id]
    evaluation = next((item for item in result.score_evaluations
                       if item.candidate_id == candidate_id), None)

    pricing = getattr(llm_client, "pricing", None)
    budget = RunBudget(result.prepared_run.budgets, pricing=pricing, tracer=tracer)
    if result.budget_usage is not None:
        budget.restore(result.budget_usage.model_dump(mode="json"))
    client = BudgetedLLMClient(llm_client, budget)

    sources = {item.source_id: item for item in result.source_manifest}
    chunks = {item.chunk_id: item for item in result.library.chunks
              if item.source_id in sources}
    cited = [reference.chunk_id for reference in candidate.evidence if reference.chunk_id]
    if evaluation is not None:
        cited.extend(reference.chunk_id for score in evaluation.criteria
                     for reference in score.evidence if reference.chunk_id)
        cited.extend(reference.chunk_id for gate in evaluation.hard_gates
                     for reference in gate.evidence if reference.chunk_id)
    rubric = (result.critic_reevaluations[-1].configuration if result.critic_reevaluations
              else result.prepared_run.evaluation)
    selected_ids = []
    tokens_used = 0
    for chunk_id in dict.fromkeys([*cited, *chunks]):
        chunk = chunks.get(chunk_id)
        if chunk is None:
            continue
        estimate = max(chunk.token_count or 0, max(1, len(chunk.text) // 4))
        if len(selected_ids) >= rubric.max_context_chunks:
            break
        if tokens_used + estimate > rubric.max_context_tokens:
            continue
        selected_ids.append(chunk_id)
        tokens_used += estimate
    selected_chunks = [chunks[chunk_id] for chunk_id in selected_ids]
    selected_sources = {chunk.source_id for chunk in selected_chunks}
    source_context = [sources[source_id].model_dump(
        mode="json", include={"source_id", "source_type", "title", "canonical_url",
                              "abstract_or_snippet", "license_access_note"}, exclude_none=True,
    ) for source_id in sorted(selected_sources)]
    chunk_context = [{"source_id": chunk.source_id, "chunk_id": chunk.chunk_id,
                      "text": chunk.text} for chunk in selected_chunks]

    draft = ExploratoryProposalDraft.model_validate(await call_prompt(
        client, "exploratory_proposal",
        {"REQUEST_JSON": result.prepared_run.request,
         "CANDIDATE_JSON": candidate,
         "EVALUATION_JSON": evaluation.model_dump(mode="json") if evaluation else None,
         "SOURCES_JSON": source_context,
         "CHUNKS_JSON": chunk_context},
        max_output_tokens=4000, tracer=tracer, task_id=candidate_id,
    ))
    # A model-authored access assumption cannot erase a recorded gate failure.
    unresolved = ([f"Unresolved {gate.gate_id.replace('_', ' ')}: {gate.rationale}"
                   for gate in evaluation.hard_gates if not gate.passed]
                  if evaluation else ["This idea was not scored; gate outcomes are unknown."])
    draft = ExploratoryProposalDraft.model_validate({
        **draft.model_dump(mode="python"),
        "unknowns": list(dict.fromkeys([*draft.unknowns, *unresolved])),
    })
    # Citation IDs are checked structurally; the draft is never called verified.
    for claim in draft.citations:
        for reference in claim.references:
            chunk = chunks.get(reference.chunk_id) if reference.chunk_id else None
            if (chunk is None or reference.chunk_id not in selected_ids
                    or chunk.source_id != reference.source_id):
                raise ValueError("exploratory proposal cites a chunk outside its supplied evidence")

    record = UserRequestedProposal(
        candidate=candidate, evaluation=evaluation,
        failed_gate_ids=([gate.gate_id for gate in evaluation.hard_gates if not gate.passed]
                         if evaluation else []),
        proposal=draft, created_at=datetime.now(timezone.utc),
    )
    data = result.model_dump(mode="python")
    data["user_proposals"] = [*result.user_proposals, record]
    data["budget_usage"] = RunBudgetUsage.model_validate(budget.snapshot())
    return OrchestrationResult.model_validate(data)
