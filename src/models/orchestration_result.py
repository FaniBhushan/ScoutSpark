"""Auditable output of one sequential or parallel coordinator run."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, PositiveInt, model_validator

from .common import ContractModel, EvidenceStance, Identifier, NonEmptyText
from .critic_result import CriticResult
from .final_proposal import FinalProposal
from .evaluation_result import EvaluationResult
from .library_result import LibraryResult
from .run_configuration import PreparedRun
from .run_budget import RunBudgetUsage
from .scout_result import ScoutResult
from .source_record import SourceRecord
from .candidate_review import CandidateReviewDecision, assessment_fingerprint
from .candidate_idea import CandidateIdea
from .run_diagnostics import RunDiagnostics
from .reevaluation import (
    AdditionalProposalRecord,
    CriticReevaluationRecord,
    evaluation_configuration_sha256,
)


class RankedCandidate(ContractModel):
    candidate_id: Identifier
    evaluation_id: Identifier
    rank: int = Field(ge=1)
    total_score: float = Field(ge=0, le=100)
    gate_passed: bool


class RetrievalIndexInfo(ContractModel):
    """Auditable settings for the temporary index used by one run."""

    index_id: Identifier
    backend: Literal["hybrid_tfidf_in_memory"] = "hybrid_tfidf_in_memory"
    backend_version: Literal["1"] = "1"
    embedding_model: Literal["local_tfidf"] = "local_tfidf"
    embedding_version: Literal["1"] = "1"
    indexed_chunk_count: PositiveInt
    corpus_chars: PositiveInt
    index_bytes_estimate: PositiveInt
    chunk_size_chars: PositiveInt
    chunk_overlap_chars: int = Field(ge=0)
    max_corpus_chars: PositiveInt
    max_chunks: PositiveInt
    max_index_bytes: PositiveInt
    retrieval_top_k: PositiveInt
    max_context_chunks: PositiveInt
    max_context_tokens: PositiveInt
    retention: Literal["run_only"] = "run_only"


class RecoveryRecord(ContractModel):
    """Earlier assessments remain visible when recovery replaces a failed pool."""

    previous_candidate_ids: list[Identifier] = Field(default_factory=list)
    previous_candidates: list[CandidateIdea] = Field(default_factory=list)
    previous_evaluations: list["EvaluationResult"] = Field(default_factory=list)
    proposal_failures: dict[Identifier, NonEmptyText] = Field(default_factory=dict)
    replacement_candidate_ids: list[Identifier] = Field(default_factory=list)
    outcome: Literal["started", "completed", "exhausted", "failed"] = "started"
    reason: str | None = None


class OrchestrationResult(ContractModel):
    requested_finalist_count: PositiveInt = 2
    budget_exhausted: bool = False
    diagnostics: RunDiagnostics | None = None
    schema_version: Literal["1.0"] = "1.0"
    run_id: Identifier
    mode: Literal["sequential", "parallel"]
    status: Literal["completed", "partial", "insufficient_coverage"]
    scout: ScoutResult
    library: LibraryResult
    critic: CriticResult
    retrieval_index: RetrievalIndexInfo | None = None
    prepared_run: PreparedRun | None = None
    budget_usage: RunBudgetUsage | None = None
    final_proposals: list[FinalProposal] = Field(default_factory=list)
    proposal_failures: dict[Identifier, NonEmptyText] = Field(default_factory=dict)
    proposal_failure_codes: dict[Identifier, Literal[
        "source_unavailable", "drafting_failure", "verification_failure", "budget_exhausted",
    ]] = Field(default_factory=dict)
    recovery_history: list[RecoveryRecord] = Field(default_factory=list)
    source_manifest: list[SourceRecord] = Field(default_factory=list)
    ranking: list[RankedCandidate] = Field(default_factory=list)
    finalist_candidate_ids: list[Identifier] = Field(default_factory=list)
    review_decisions: list[CandidateReviewDecision] = Field(default_factory=list)
    critic_reevaluations: list[CriticReevaluationRecord] = Field(default_factory=list)
    additional_proposals: list[AdditionalProposalRecord] = Field(default_factory=list)
    warnings: list[NonEmptyText] = Field(default_factory=list)
    completed_at: datetime

    @property
    def score_ranking(self) -> list[RankedCandidate]:
        """Include earlier assessed ideas when a recovery round replaced the pool."""
        if self.critic_reevaluations:
            return [RankedCandidate.model_validate(item.model_dump())
                    for item in self.critic_reevaluations[-1].ranking]
        rows = {}
        for attempt in self.recovery_history:
            for item in attempt.previous_evaluations:
                rows[item.candidate_id] = RankedCandidate(
                    candidate_id=item.candidate_id, evaluation_id=item.evaluation_id,
                    rank=1, total_score=item.total_score, gate_passed=item.gate_passed,
                )
        rows.update({row.candidate_id: row for row in self.ranking})
        ordered = sorted(rows.values(), key=lambda row: (-row.total_score, row.candidate_id))
        return [row.model_copy(update={"rank": rank}) for rank, row in enumerate(ordered, 1)]

    @property
    def active_critic(self) -> CriticResult:
        """Return the latest audited re-evaluation, or the original Critic result."""
        return self.critic_reevaluations[-1].critic if self.critic_reevaluations else self.critic

    @property
    def score_evaluations(self) -> list[EvaluationResult]:
        """Return the assessment version used by the current displayed ranking."""
        if self.critic_reevaluations:
            return list(self.critic_reevaluations[-1].critic.evaluations)
        evaluations = {item.candidate_id: item for attempt in self.recovery_history
                       for item in attempt.previous_evaluations}
        evaluations.update({item.candidate_id: item for item in self.critic.evaluations})
        return list(evaluations.values())

    @property
    def score_finalist_candidate_ids(self) -> list[str]:
        """Score selections remain visible even when a detailed draft is withheld."""
        count = (self.prepared_run.request.finalist_count if self.prepared_run
                 else self.requested_finalist_count)
        return [row.candidate_id for row in self.score_ranking[:count]]

    @model_validator(mode="after")
    def validate_review_decisions(self) -> "OrchestrationResult":
        """A review never turns a failed gate into an automatic recommendation."""

        if not self.review_decisions:
            return self
        candidates = {item.candidate_id: item for item in self.scout.candidates}
        evaluations = {item.candidate_id: item for item in self.critic.evaluations}
        for review in self.review_decisions:
            candidate = candidates.get(review.candidate_id)
            evaluation = evaluations.get(review.candidate_id)
            if review.run_id != self.run_id or candidate is None or evaluation is None:
                raise ValueError("review must reference a candidate assessed in this run")
            if not evaluation.can_accept_evidence_risk:
                raise ValueError("only an isolated evidence gap is eligible for user review")
            if (review.evaluation_id != evaluation.evaluation_id or
                    review.assessment_sha256 != assessment_fingerprint(candidate, evaluation)):
                raise ValueError("review does not match the current candidate assessment")
            expected_caveats = list(dict.fromkeys([
                *evaluation.rejection_reasons, *evaluation.uncertainty,
            ]))
            if review.caveats != expected_caveats:
                raise ValueError("review must retain all assessment caveats")
            if review.candidate_id in self.finalist_candidate_ids:
                raise ValueError("user-reviewed candidates cannot become automatic finalists")
        return self

    @model_validator(mode="after")
    def validate_proposals(self) -> "OrchestrationResult":
        """Keep serialized proposals tied to this run's ranking and evidence."""

        if self.retrieval_index is not None and self.retrieval_index.index_id != f"{self.run_id}:library":
            raise ValueError("retrieval index ID must belong to this run")
        if self.final_proposals:
            proposal_ids = [proposal.candidate_id for proposal in self.final_proposals]
            if proposal_ids != self.finalist_candidate_ids:
                raise ValueError("final proposals must match selected finalists in order")
        rows = {row.candidate_id: row for row in self.ranking}
        evaluations = {item.candidate_id: item for item in self.critic.evaluations}
        source_ids = {source.source_id for source in self.source_manifest}
        chunk_sources = {chunk.chunk_id: chunk.source_id for chunk in self.library.chunks}
        for expected_version, version in enumerate(self.critic_reevaluations, 1):
            if version.configuration_sha256 != evaluation_configuration_sha256(version.configuration):
                raise ValueError("Critic re-evaluation configuration checksum is invalid")
            if version.version != expected_version:
                raise ValueError("Critic re-evaluation versions must be consecutive")
        for proposal in [*self.final_proposals]:
            if proposal.evidence_audit is not None:
                audit = proposal.evidence_audit
                if (not audit.accepted or sorted(item.claim_index for item in audit.claims)
                        != list(range(len(proposal.citations)))):
                    raise ValueError("proposal evidence audit must pass for every citation claim")
                if audit.caveated_fields:
                    from src.guardrails.proposal_policy import HYPOTHESIS_PREFIX
                    if any(not getattr(proposal, field).startswith(HYPOTHESIS_PREFIX)
                           for field in audit.caveated_fields):
                        raise ValueError("provisional narrative must be explicitly qualified")
            row = rows.get(proposal.candidate_id)
            evaluation = evaluations.get(proposal.candidate_id)
            if row is None or evaluation is None:
                raise ValueError("final proposal has no selected ranking and evaluation")
            if not evaluation.gate_passed or proposal.candidate_id in self.proposal_failures:
                raise ValueError("failed candidates cannot appear as final proposals")
            if proposal.rank != row.rank or abs(proposal.total_score - row.total_score) > 0.01:
                raise ValueError("final proposal rank and score must match the ranking")
            if proposal.criterion_scores != evaluation.criteria:
                raise ValueError("final proposal criterion scores must match Critic")
            _validate_proposal_citations(proposal, source_ids, chunk_sources)
        for additional in self.additional_proposals:
            if additional.assessment_version == 0:
                version_configuration = self.prepared_run.evaluation if self.prepared_run else None
                version_critic = self.critic
                version_ranking = self.ranking
            elif additional.assessment_version <= len(self.critic_reevaluations):
                record = self.critic_reevaluations[additional.assessment_version - 1]
                version_configuration = record.configuration
                version_critic = record.critic
                version_ranking = record.ranking
            else:
                raise ValueError("additional proposal references an unknown assessment version")
            if version_configuration is None or additional.assessment_configuration_sha256 != evaluation_configuration_sha256(version_configuration):
                raise ValueError("additional proposal configuration does not match its assessment")
            recorded_assessment = next((item for item in version_critic.evaluations
                                        if item.evaluation_id == additional.evaluation.evaluation_id), None)
            if recorded_assessment != additional.evaluation:
                raise ValueError("additional proposal assessment is not retained in its version")
            row = next((item for item in version_ranking
                        if item.candidate_id == additional.proposal.candidate_id), None)
            if (row is None or not additional.evaluation.gate_passed
                    or row.evaluation_id != additional.evaluation.evaluation_id
                    or additional.proposal.rank != row.rank
                    or abs(additional.proposal.total_score - row.total_score) > 0.01
                    or additional.proposal.criterion_scores != additional.evaluation.criteria):
                raise ValueError("additional proposal must match its passing assessment and rank")
            if additional.proposal.candidate_id in self.proposal_failures:
                raise ValueError("failed additional proposals cannot be retained as successful")
            if additional.proposal.evidence_audit is not None and not additional.proposal.evidence_audit.accepted:
                raise ValueError("additional proposal evidence audit must pass")
            _validate_proposal_citations(additional.proposal, source_ids, chunk_sources)
        return self


def _validate_proposal_citations(proposal, source_ids, chunk_sources):
    """Check every proposal's source/chunk integrity, including additional drafts."""
    supporting_chunk = False
    for claim in proposal.citations:
        for reference in claim.references:
            if reference.source_id not in source_ids:
                raise ValueError("proposal cites a source outside the manifest")
            if reference.chunk_id is not None:
                if chunk_sources.get(reference.chunk_id) != reference.source_id:
                    raise ValueError("proposal cites an unknown or mismatched chunk")
                if reference.stance == EvidenceStance.SUPPORTING:
                    supporting_chunk = True
    if not supporting_chunk:
        raise ValueError("proposal needs a supporting chunk citation")
