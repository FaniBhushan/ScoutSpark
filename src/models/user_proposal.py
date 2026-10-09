"""User-requested exploratory drafts remain separate from verified proposals."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .candidate_idea import CandidateIdea
from .common import ClaimEvidence, ContractModel, Identifier
from .evaluation_result import EvaluationResult
from .proposal_draft import ProposalDraft


class ExploratoryProposalDraft(ProposalDraft):
    """A detailed plan may have no supportable citation when evidence is absent."""

    citations: list[ClaimEvidence] = Field(default_factory=list)


class UserRequestedProposal(ContractModel):
    """Keep explicit user choice and the original assessment with an unverified draft."""

    candidate: CandidateIdea
    evaluation: EvaluationResult | None = None
    failed_gate_ids: list[Identifier] = Field(default_factory=list)
    proposal: ExploratoryProposalDraft
    verification_status: Literal["unverified"] = "unverified"
    user_approved: Literal[True] = True
    created_at: datetime

    @model_validator(mode="after")
    def validate_gate_snapshot(self) -> "UserRequestedProposal":
        if self.evaluation is not None and self.evaluation.candidate_id != self.candidate.candidate_id:
            raise ValueError("exploratory proposal assessment must match its candidate")
        expected = ([gate.gate_id for gate in self.evaluation.hard_gates if not gate.passed]
                    if self.evaluation else [])
        if self.failed_gate_ids != expected:
            raise ValueError("exploratory proposal must preserve failed gate IDs")
        return self
