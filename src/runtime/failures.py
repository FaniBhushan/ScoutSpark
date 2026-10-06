"""Stable failure categories for callers, traces, and persisted run metadata."""


class RetryableFailure(RuntimeError):
    """A transient failure with an optional provider-requested delay."""

    retry_after = None


class StageFailure(RuntimeError):
    """A safe, structured failure raised by one named application stage."""

    def __init__(self, stage: str, error: BaseException) -> None:
        self.stage = stage
        self.code = failure_code(error)
        self.error_type = type(error).__name__
        super().__init__(f"{stage} stage failed ({self.code}).")


def failure_code(error: BaseException) -> str:
    """Classify safely without storing exception messages or provider bodies."""
    explicit = getattr(error, "code", None)
    if explicit:
        return explicit
    names = {
        "BudgetExceeded": "budget_exhausted", "ValidationError": "invalid_output",
        "TimeoutError": "timeout", "CancelledError": "cancelled",
        "ModelResponseError": "invalid_model_response",
        "ModelRateLimitError": "provider_rate_limited",
        "ModelTransportError": "provider_unavailable",
        "SourceUnavailableError": "provider_unavailable",
        "SourceAdapterError": "provider_error",
        "CheckpointError": "checkpoint_invalid",
        "ProposalCoverageError": "insufficient_coverage",
    }
    for error_type in type(error).__mro__:
        if error_type.__name__ in names:
            return names[error_type.__name__]
    return "stage_failure"


def failure_details(error: BaseException, *, stage_hint: str = "research") -> dict[str, object]:
    """Return the same bounded stage/code/message shape for UI and CLI errors."""

    from src.guardrails import safe_error_message

    stage = getattr(error, "stage", None) or stage_hint
    code = failure_code(error)
    cause = getattr(error, "error", None) or error.__cause__
    if stage == "research" and code == "checkpoint_invalid":
        stage = "checkpoint"
    return {
        "stage": str(stage),
        "code": code,
        "retryable": (
            isinstance(error, RetryableFailure) or isinstance(cause, RetryableFailure)
        ),
        "message": safe_error_message(error if isinstance(error, Exception) else RuntimeError(str(error))),
    }
