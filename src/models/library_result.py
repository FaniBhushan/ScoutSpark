"""Evidence landscape collected independently by the Library worker."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import ContractModel, NonEmptyText
from .source_record import SourceChunk, SourceRecord
from .run_diagnostics import ShortfallReason


class LibraryResult(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    sources: list[SourceRecord] = Field(default_factory=list)
    chunks: list[SourceChunk] = Field(default_factory=list)
    warnings: list[NonEmptyText] = Field(default_factory=list)
    reason_codes: list[ShortfallReason] = Field(default_factory=list)
    requested_usable_source_count: int = Field(default=0, ge=0)
    usable_source_count: int = Field(default=0, ge=0)
    missing_required_source_types: list[str] = Field(default_factory=list)
    recovery_query_count: int = Field(default=0, ge=0)
