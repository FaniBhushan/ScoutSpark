"""Versioned Critic reruns and proposals tied to the assessment that produced them."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from pydantic import Field, PositiveInt, model_validator

from .common import ContractModel, Identifier, NonEmptyText
from .critic_result import CriticResult
from .evaluation_configuration import EvaluationConfiguration
from .evaluation_result import EvaluationResult
from .final_proposal import FinalProposal
from .evaluation_configuration import Percentage


def evaluation_configuration_sha256(configuration: EvaluationConfiguration) -> str:
    """Hash the exact resolved criteria and gates used for one assessment version."""
    payload = json.dumps(configuration.model_dump(mode="json"), sort_keys=True,
                         separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CriticReevaluationRecord(ContractModel):
    version: PositiveInt
    configuration: EvaluationConfiguration
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    critic: CriticResult
    ranking: list["ReevaluationRankedCandidate"]
    created_at: datetime

    @model_validator(mode="after")
    def validate_ranked_assessments(self):
        evaluations = {item.candidate_id: item for item in self.critic.evaluations}
        if len(evaluations) != len(self.critic.evaluations):
            raise ValueError("Critic re-evaluation candidate IDs must be unique")
        if {row.candidate_id for row in self.ranking} != set(evaluations):
            raise ValueError("Critic re-evaluation ranking must include each assessed candidate")
        expected = sorted(evaluations.values(), key=lambda item: (-item.total_score, item.candidate_id))
        for rank, (row, evaluation) in enumerate(zip(self.ranking, expected), 1):
            if (row.candidate_id != evaluation.candidate_id or row.rank != rank
                    or row.evaluation_id != evaluation.evaluation_id
                    or row.total_score != evaluation.total_score
                    or row.gate_passed != evaluation.gate_passed):
                raise ValueError("Critic re-evaluation ranking is inconsistent with its scores")
        return self


class ReevaluationRankedCandidate(ContractModel):
    candidate_id: Identifier
    evaluation_id: Identifier
    rank: PositiveInt
    total_score: float = Field(ge=0, le=100)
    gate_passed: bool


class AdditionalProposalRecord(ContractModel):
    assessment_version: int = Field(ge=0)
    assessment_configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluation: EvaluationResult
    proposal: FinalProposal

    @model_validator(mode="after")
    def validate_assessment_link(self):
        if self.proposal.candidate_id != self.evaluation.candidate_id:
            raise ValueError("additional proposal and assessment must refer to the same candidate")
        return self


class CriticReevaluationRequest(ContractModel):
    """User changes weights and adds project constraints without weakening base gates."""

    weights: dict[Identifier, Percentage] | None = None
    additional_project_gates: dict[Identifier, NonEmptyText] = Field(default_factory=dict, max_length=5)

    @classmethod
    def validate_against(cls, value, base_configuration: EvaluationConfiguration):
        request = cls.model_validate(value)
        if request.weights is not None:
            if set(request.weights) != set(base_configuration.criteria):
                raise ValueError("re-evaluation weights must retain every configured criterion")
            if sum(request.weights.values()) != 100:
                raise ValueError("re-evaluation weights must total 100")
        collisions = set(request.additional_project_gates) & set(base_configuration.hard_gates)
        if collisions:
            raise ValueError("project gates cannot replace or weaken configured hard gates")
        if any(not gate_id.startswith("project_") for gate_id in request.additional_project_gates):
            raise ValueError("additional gate IDs must use the project_ prefix")
        return request
