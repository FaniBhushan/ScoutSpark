"""LLM-backed Scout query planning and candidate generation."""

from typing import cast

from pydantic import ValidationError

from src.guardrails.privacy import safe_validation_hints
from src.llm.client import LLMClient, ModelResponseError
from src.llm.prompt_call import call_prompt
from src.llm.query_planner import _LLMQueryPlanner

from src.models import (
    CandidateIdea,
    InputRequest,
    ScoutQuery,
    SourceRecord,
)
from src.observability import RunTracer


class LLMScoutQueryPlanner(_LLMQueryPlanner[ScoutQuery]):
    """Plan Scout queries using an injected LLM client."""

    def __init__(
        self, llm_client: LLMClient, *, max_output_tokens: int, tracer: RunTracer | None = None
    ) -> None:
        super().__init__(
            llm_client,
            prompt_name="scout_query_planner",
            max_output_tokens=max_output_tokens,
            tracer=tracer,
        )


class LLMCandidateGenerator:
    """Generate Scout candidates using an injected LLM client."""

    def __init__(
        self, llm_client: LLMClient, *, max_output_tokens: int, max_batches: int = 8,
        tracer: RunTracer | None = None
    ) -> None:
        if max_output_tokens <= 0 or max_batches <= 0:
            raise ValueError("max_output_tokens and max_batches must be positive")
        self.llm_client = llm_client
        self.max_output_tokens = max_output_tokens
        self.max_batches = max_batches
        self.tracer = tracer

    async def generate(
        self,
        request: InputRequest,
        sources: list[SourceRecord],
        *, recovery_feedback: dict | None = None,
    ) -> list[CandidateIdea]:
        candidates, _ = await self.generate_with_metrics(
            request, sources, recovery_feedback=recovery_feedback
        )
        return candidates

    async def generate_with_metrics(
        self,
        request: InputRequest,
        sources: list[SourceRecord],
        *,
        recovery_feedback: dict | None = None,
    ) -> tuple[list[CandidateIdea], dict[str, int]]:
        if not sources:
            return [], {"invalid_response_batches": 0, "duplicate_candidates": 0,
                        "correction_attempts": 0, "correction_succeeded": 0,
                        "generated_candidate_count": 0}

        compact_sources = [
            source.model_dump(
                mode="json",
                include={
                    "source_id",
                    "provider",
                    "source_type",
                    "title",
                    "published_at",
                    "canonical_url",
                    "abstract_or_snippet",
                    "license_access_note",
                },
                exclude_none=True,
            )
            for source in sources
        ]
        # One short captured passage can supply fields/permissions absent from
        # a search summary. Bound it per source instead of sending whole documents.
        for compact, source in zip(compact_sources, sources):
            excerpts = [chunk for chunk in source.evidence_chunks if len(chunk.text) <= 1200]
            if excerpts:
                compact["evidence_excerpt"] = {
                    "chunk_id": excerpts[0].chunk_id, "text": excerpts[0].text,
                }
                if len(excerpts) > 1:
                    compact["additional_evidence_excerpt"] = {
                        "chunk_id": excerpts[1].chunk_id, "text": excerpts[1].text,
                    }
        metrics: dict[str, int] = {}
        candidates = await generate_candidate_batches(
            self.llm_client, request, compact_sources,
            max_output_tokens=self.max_output_tokens, tracer=self.tracer,
            recovery_feedback=recovery_feedback, metrics=metrics,
            max_batches=self.max_batches,
        )
        # Synthetic ideas can influence subsequent batches, but never leave generation.
        return [item for item in candidates if item.origin != "synthetic"], metrics


async def generate_candidate_batches(
    client: LLMClient, request: InputRequest, sources: list[dict], *,
    max_output_tokens: int, tracer: RunTracer | None,
    recovery_feedback: dict | None = None,
    metrics: dict[str, int] | None = None,
    max_batches: int = 8,
) -> list[CandidateIdea]:
    """Bound generation output and retain valid ideas when a later batch is malformed.

    Use at most three ideas per response and allow one schema-correction attempt.
    Compact idea summaries prevent repeated ideas without resending full prior
    outputs. Shared run budgets remain authoritative; budget and transport
    failures still propagate.
    """

    from src.llm.candidate_batches import merge_candidates

    batch_size = min(3, max(1, max_output_tokens // 700))
    if max_batches <= 0:
        raise ValueError("max_batches must be positive")
    candidates: list[CandidateIdea] = []
    correction_used = False
    counters = metrics if metrics is not None else {}
    counters.setdefault("invalid_response_batches", 0)
    counters.setdefault("duplicate_candidates", 0)
    counters.setdefault("unsupported_candidates", 0)
    counters.setdefault("correction_attempts", 0)
    counters.setdefault("correction_succeeded", 0)
    counters.setdefault("generated_candidate_count", 0)
    counters.setdefault("batch_count", 0)
    active_recovery_feedback = dict(recovery_feedback or {})
    batch_index = 0
    max_attempts = max_batches
    while batch_index < max_attempts:
        if len(candidates) >= request.desired_candidate_count:
            break
        requested_count = min(batch_size, request.desired_candidate_count - len(candidates))
        counters["batch_count"] += 1
        active_recovery_feedback.update({
            "candidate_target": request.desired_candidate_count,
            "accepted_count": len(candidates),
            "remaining_count": request.desired_candidate_count - len(candidates),
            "invalid_response_batches": counters["invalid_response_batches"],
            "duplicates_rejected": counters["duplicate_candidates"],
            "unsupported_ideas_rejected": counters["unsupported_candidates"],
            "request_fit_reminder": "Each idea must meet the original user needs and constraints.",
        })
        # Preserve upstream recovery context while exposing local accepted work.
        # Detailed current-run ideas remain in BATCH_JSON.existing_ideas.
        if not active_recovery_feedback.get("previous_ideas"):
            active_recovery_feedback["previous_ideas"] = [item.title for item in candidates]
        context = {
            "REQUEST_JSON": request, "SOURCE_RECORDS_JSON": sources,
            "BATCH_JSON": {
                "requested_count": requested_count,
                "recovery_feedback": active_recovery_feedback or None,
                "existing_ideas": [
                    {"target_users": item.target_users, "problem_statement": item.problem_statement,
                     "proposed_outcome": item.proposed_outcome, "origin": item.origin}
                    for item in candidates
                ],
            },
        }
        try:
            batch = cast(list[CandidateIdea], await call_prompt(
                client, "scout_candidate_generator", context,
                max_output_tokens=max_output_tokens, tracer=tracer,
                task_id=f"batch-{batch_index + 1}", validation_retry_limit=0,
            ))
        except (ValidationError, ModelResponseError) as error:
            from src.runtime.budgets import StageAllowanceExceeded
            if isinstance(error, StageAllowanceExceeded):
                if tracer:
                    tracer.event("candidate_generation", "stage_allowance_reached", count=len(candidates))
                break
            if isinstance(error, ModelResponseError) and error.reply is None:
                raise
            if tracer:
                tracer.event("candidate_generation", "batch_response_failed", count=len(candidates))
            counters["invalid_response_batches"] += 1
            if isinstance(error, ValidationError):
                # Share only contract paths and Pydantic error codes—not rejected
                # output or message text—with the correction attempt.
                active_recovery_feedback["response_schema_issues"] = safe_validation_hints(error)
            else:
                active_recovery_feedback["previous_batch_issue"] = "invalid_or_truncated_response"
            if correction_used:
                break
            # Retry one malformed response with safe schema hints, retaining all
            # candidates accepted from earlier batches. The normal run client
            # charges this correction attempt to the same token/cost budget.
            correction_used = True
            counters["correction_attempts"] += 1
            batch_size = max(1, batch_size // 2)
            batch_index += 1
            continue
        counters["correction_succeeded"] = int(correction_used)
        counters["generated_candidate_count"] += sum(
            item.origin != "synthetic" for item in batch[:requested_count]
        )
        merged = merge_candidates(candidates, batch[:requested_count], sources, metrics=counters)
        if len(merged) == len(candidates):
            active_recovery_feedback["previous_batch_issue"] = "no_new_unique_supported_ideas"
            if candidates:
                # The next batch already received the measured deficit and
                # rejection counts. Keep valid work and avoid repeating an
                # unchanged answer through the rest of the attempt cap.
                break
            batch_index += 1
            continue
        candidates = merged
        if tracer:
            tracer.event("candidate_generation", "batch_retained", count=len(candidates))
        batch_index += 1
    return candidates
