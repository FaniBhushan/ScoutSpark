"""Machine-readable stage counts and shortfall reasons for one completed run."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, NonNegativeInt, PositiveInt

from .common import ContractModel


ShortfallStage = Literal[
    "scout_generation", "library_coverage", "critic_assessment",
    "finalist_selection", "proposal_verification",
]
ShortfallReason = Literal[
    "underproduction", "invalid_output", "duplicate_candidates",
    "unsupported_evidence", "provider_unavailable", "source_unavailable", "budget_exhausted",
    "timeout", "assessment_failure", "hard_gate_rejection",
    "drafting_failure", "verification_failure", "eligible_candidates_exhausted", "unknown",
]


class CountShortfall(ContractModel):
    """A requested stage target that the run did not reach."""

    stage: ShortfallStage
    requested: NonNegativeInt
    actual: NonNegativeInt
    reason_codes: list[ShortfallReason] = Field(min_length=1)


class RunDiagnostics(ContractModel):
    """Counts distinguish generation, evidence, assessment, and verified output."""

    requested_candidate_count: PositiveInt
    scout_generation_target_count: NonNegativeInt = 0
    generated_candidate_count: NonNegativeInt = 0
    accepted_candidate_count: NonNegativeInt = 0
    usable_library_source_count: NonNegativeInt = 0
    library_chunk_count: NonNegativeInt = 0
    assessed_candidate_count: NonNegativeInt = 0
    gate_passed_candidate_count: NonNegativeInt = 0
    requested_finalist_count: PositiveInt
    selected_finalist_count: NonNegativeInt = 0
    verified_proposal_count: NonNegativeInt = 0
    shortfalls: list[CountShortfall] = Field(default_factory=list)
