"""Build end-to-end counts after finalization without conflating gates and yield."""

from src.models import CountShortfall, OrchestrationResult, RunDiagnostics
from src.models.source_record import RetrievalStatus


def build_run_diagnostics(result: OrchestrationResult, request, search) -> RunDiagnostics:
    """Summarize completed work and attach only causes supported by run data."""

    scout = result.scout
    library = result.library
    critic = result.critic
    accepted = len(scout.candidates)
    generated = max(scout.generated_candidate_count, accepted)
    usable_sources = sum(
        source.retrieval_status in (RetrievalStatus.SUCCESS, RetrievalStatus.PARTIAL)
        for source in library.sources
    )
    assessed = len(critic.evaluations)
    gate_passed = sum(item.gate_passed for item in critic.evaluations)
    selected = len(result.score_finalist_candidate_ids)
    verified = len(result.final_proposals)
    shortfalls: list[CountShortfall] = []

    generation_target = scout.generation_target_count or request.desired_candidate_count
    if accepted < generation_target:
        causes = list(scout.reason_codes)
        if not causes:
            causes = ["underproduction"]
        shortfalls.append(CountShortfall(
            stage="scout_generation", requested=generation_target,
            actual=accepted, reason_codes=list(dict.fromkeys(causes)),
        ))

    required_types = set(search.required_source_types) | set(request.source_policy.required_types)
    missing_types = required_types - {
        source.source_type for source in library.sources
        if source.retrieval_status in (RetrievalStatus.SUCCESS, RetrievalStatus.PARTIAL)
    }
    if usable_sources < search.minimum_source_count:
        shortfalls.append(CountShortfall(
            stage="library_coverage", requested=search.minimum_source_count,
            actual=usable_sources,
            reason_codes=(library.reason_codes or ["source_unavailable"]),
        ))
    elif missing_types:
        shortfalls.append(CountShortfall(
            stage="library_coverage", requested=len(required_types),
            actual=len(required_types) - len(missing_types),
            reason_codes=(library.reason_codes or ["source_unavailable"]),
        ))

    if assessed < accepted:
        shortfalls.append(CountShortfall(
            stage="critic_assessment", requested=accepted, actual=assessed,
            reason_codes=(critic.reason_codes or ["assessment_failure"]),
        ))

    if selected < request.finalist_count:
        reasons = []
        if (gate_passed < request.finalist_count and assessed == accepted
                and accepted >= request.finalist_count):
            reasons.append("hard_gate_rejection")
        if accepted < request.desired_candidate_count:
            reasons.extend(scout.reason_codes or ["unknown"])
        if assessed < accepted:
            reasons.extend(critic.reason_codes or ["assessment_failure"])
        shortfalls.append(CountShortfall(
            stage="finalist_selection", requested=request.finalist_count,
            actual=selected, reason_codes=list(dict.fromkeys(reasons or ["unknown"])),
        ))

    proposal_target = request.finalist_count
    if verified < proposal_target:
        reasons = []
        if (gate_passed < request.finalist_count and assessed == accepted
                and accepted >= request.finalist_count):
            reasons.append("hard_gate_rejection")
        if accepted < request.desired_candidate_count:
            reasons.extend(scout.reason_codes or ["unknown"])
        if result.proposal_failure_codes:
            reasons.extend(result.proposal_failure_codes.values())
        if result.proposal_failures and not result.budget_exhausted:
            reasons.append("eligible_candidates_exhausted")
        if result.budget_exhausted:
            reasons.append("budget_exhausted")
        if not reasons:
            reasons.append("unknown")
        shortfalls.append(CountShortfall(
            stage="proposal_verification", requested=proposal_target,
            actual=verified, reason_codes=reasons,
        ))

    return RunDiagnostics(
        requested_candidate_count=request.desired_candidate_count,
        scout_generation_target_count=generation_target,
        generated_candidate_count=generated,
        accepted_candidate_count=accepted,
        usable_library_source_count=usable_sources,
        library_chunk_count=len(library.chunks),
        assessed_candidate_count=assessed,
        gate_passed_candidate_count=gate_passed,
        requested_finalist_count=request.finalist_count,
        selected_finalist_count=selected,
        verified_proposal_count=verified,
        shortfalls=shortfalls,
    )
