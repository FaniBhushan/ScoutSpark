"""Review and result views for the Streamlit interface."""

from __future__ import annotations

import asyncio

import streamlit as st

from src.guardrails import SensitiveContentError, check_privacy, safe_error_message
from src.models import PromptInterpretationDraft
from src.application.proposal_selection import generate_nonfinalist_proposal
from src.application.reevaluation import reevaluate_existing_candidates, resolve_reevaluation_configuration
from src.models import CriticReevaluationRequest
from src.runtime.failures import failure_details
from .candidate_review import candidate_review_view
from .evaluation_guide import render_criteria_guide
from .scorecards import render_scorecards
from .run_history import save_run_result


def show_failure(error: Exception, *, stage_hint: str = "research") -> None:
    """Render a consistent safe message plus stable stage and failure code."""

    details = failure_details(error, stage_hint=stage_hint)
    st.error(details["message"])
    retry = " · retryable" if details["retryable"] else ""
    st.caption(f"Stage: {details['stage']} · Code: {details['code']}{retry}")


def _show_draft(draft: PromptInterpretationDraft, prompt: str) -> None:
    if draft.original_prompt != prompt:
        st.warning("The prompt changed. Draft it again before previewing.")
        return
    st.subheader("Review proposed fields")
    for warning in draft.warnings:
        st.warning(warning)
    suggestions = draft.suggestions
    for section in ("request", "search", "evaluation"):
        for field, value in getattr(suggestions, section).model_dump(
            mode="json", exclude_unset=True, exclude_none=True
        ).items():
            path = f"{section}.{field}"
            unsupported = any(issue.kind == "unsupported" and issue.path == path for issue in draft.issues)
            uncertain = path in suggestions.uncertain_paths
            st.checkbox(
                f"{path}: {value}", key=f"accept:{path}",
                disabled=unsupported or uncertain or path == "search.allow_other_domain",
                help="Uncertain or unsupported values must be entered explicitly in the controls."
                if unsupported or uncertain else None,
            )
    for index, issue in enumerate(draft.issues):
        st.warning(f"{issue.kind}: {issue.message}")
        st.checkbox("I reviewed this issue", key=f"ack:{index}")
    st.caption("Unchecked suggestions are ignored. Edited controls override accepted suggestions.")


def _result_view(result, *, action_client_factory=None) -> None:
    try:
        for warning in check_privacy(result):
            st.warning(warning)
    except SensitiveContentError as error:
        st.error(safe_error_message(error))
        return
    st.subheader("Run result")
    st.write(f"Detailed proposal status: {result.status} · Mode: {result.mode} · Run ID: {result.run_id}")
    render_criteria_guide(title="Understand the evaluation scores")
    st.json(result.budget_usage.model_dump(mode="json") if result.budget_usage else {})
    for warning in result.warnings:
        st.warning(warning)
    if result.diagnostics is not None:
        with st.expander("Result counts and shortfalls", expanded=bool(result.diagnostics.shortfalls)):
            counts = result.diagnostics
            st.markdown(
                f"**Scout:** {counts.accepted_candidate_count} accepted of "
                f"{counts.scout_generation_target_count} internal target "
                f"({counts.requested_candidate_count} user-requested results) "
                f"({counts.generated_candidate_count} generated)."
            )
            st.markdown(
                f"**Evidence:** {counts.usable_library_source_count} usable sources, "
                f"{counts.library_chunk_count} chunks. Critic assessed "
                f"{counts.assessed_candidate_count}; "
                f"{counts.gate_passed_candidate_count} passed gates."
            )
            st.caption(
                f"Library coverage: {result.library.usable_source_count}/"
                f"{result.library.requested_usable_source_count} usable sources; "
                f"{result.library.recovery_query_count} bounded recovery searches."
            )
            if result.library.missing_required_source_types:
                st.caption("Still missing: " + ", ".join(result.library.missing_required_source_types))
            st.markdown(
                f"**Scorecards:** {counts.selected_finalist_count} of "
                f"{counts.requested_finalist_count}. Verified proposals: "
                f"{counts.verified_proposal_count}."
            )
            if counts.shortfalls:
                st.dataframe([
                    {
                        "Stage": item.stage,
                        "Requested": item.requested,
                        "Actual": item.actual,
                        "Reason codes": ", ".join(item.reason_codes),
                    }
                    for item in counts.shortfalls
                ], hide_index=True)
    render_scorecards(result)
    if action_client_factory is not None:
        _render_reevaluation_action(result, action_client_factory)
        _render_nonfinalist_proposal_action(result, action_client_factory)
    result = candidate_review_view(result)
    with st.expander("Selected source receipts", expanded=False):
        st.dataframe([
            {
                "source_id": source.source_id,
                "provider": source.provider,
                "source_type": source.source_type,
                "title": source.title,
                "url": str(source.canonical_url) if source.canonical_url else "",
            }
            for source in result.source_manifest
        ], hide_index=True)
    with st.expander("Configuration and provenance"):
        st.json(result.prepared_run.model_dump(mode="json") if result.prepared_run else {})
    st.download_button("Download run JSON", result.model_dump_json(indent=2),
                       file_name=f"scoutspark-{result.run_id}.json", mime="application/json")


def _render_reevaluation_action(result, client_factory) -> None:
    """Preview a versioned criteria/gate change, then spend only remaining run budget."""
    if result.prepared_run is None:
        return
    from src.models import evaluation_configuration_sha256

    with st.expander("Re-evaluate candidates with reviewed criteria and project gates"):
        base = result.critic_reevaluations[-1].configuration if result.critic_reevaluations else result.prepared_run.evaluation
        if st.button("Edit re-evaluation criteria", key=f"reeval-edit:{result.run_id}"):
            st.session_state[f"reeval-editing:{result.run_id}"] = True
        editing = st.session_state.get(f"reeval-editing:{result.run_id}", False)
        if editing:
            with st.form(f"reeval-form:{result.run_id}"):
                weights = {}
                columns = st.columns(2)
                for index, (key, definition) in enumerate(base.criteria.items()):
                    with columns[index % 2]:
                        weights[key] = st.number_input(
                            definition.label, min_value=0, max_value=100,
                            value=definition.weight, key=f"reeval-weight:{result.run_id}:{key}",
                        )
                project_gate_id = st.text_input(
                    "Additional project gate ID (optional)", value="project_",
                    key=f"reeval-gate-id:{result.run_id}",
                )
                project_gate = st.text_area(
                    "Additional project gate", key=f"reeval-gate:{result.run_id}",
                    help="Adds a gate. Existing operator, privacy, and safety gates remain unchanged.",
                )
                preview_clicked = st.form_submit_button("Preview resolved re-evaluation")
            if preview_clicked:
                try:
                    change = CriticReevaluationRequest(
                        weights=weights,
                        additional_project_gates=({project_gate_id: project_gate}
                                                  if project_gate.strip() else {}),
                    )
                    resolved = resolve_reevaluation_configuration(base, change)
                    st.session_state[f"reeval-preview:{result.run_id}"] = {
                        "change": change.model_dump(mode="json"),
                        "configuration": resolved.model_dump(mode="json"),
                        "sha256": evaluation_configuration_sha256(resolved),
                    }
                except ValueError as error:
                    st.error(str(error))
        preview = st.session_state.get(f"reeval-preview:{result.run_id}")
        if preview:
            st.markdown("**Resolved assessment version**")
            st.json(preview["configuration"])
            budget = result.prepared_run.budgets
            used = result.budget_usage.model_tokens if result.budget_usage else 0
            remaining = max(0, budget.max_model_tokens - used)
            candidates = len({item.candidate_id for item in result.scout.candidates})
            st.caption(
                f"This will score {candidates} retained candidates against saved evidence; "
                f"it starts no searches. The shared run budget has {remaining} model tokens "
                f"remaining and a {budget.max_elapsed_seconds:g}s elapsed-time limit. "
                "Actual use depends on response length and stops at the existing limits."
            )
            if st.button("Run reviewed re-evaluation", key=f"reeval-run:{result.run_id}"):
                try:
                    updated = asyncio.run(reevaluate_existing_candidates(
                        result, client_factory(), preview["change"],
                    ))
                    st.session_state.result = updated
                    save_run_result(updated)
                    st.session_state.pop(f"reeval-preview:{result.run_id}", None)
                    st.session_state.pop(f"reeval-editing:{result.run_id}", None)
                    st.success(f"Saved Critic assessment version {len(updated.critic_reevaluations)}.")
                    st.rerun()
                except Exception as error:
                    st.error(safe_error_message(error))


def _render_nonfinalist_proposal_action(result, client_factory) -> None:
    """Offer an explicit, bounded action for gate-passing non-finalists in view."""
    if result.prepared_run is None:
        return
    candidates = {item.candidate_id: item for attempt in result.recovery_history
                  for item in attempt.previous_candidates}
    candidates.update({item.candidate_id: item for item in result.scout.candidates})
    evaluations = {item.candidate_id: item for item in result.score_evaluations}
    top = set(result.score_finalist_candidate_ids)
    visible_count = result.prepared_run.request.desired_candidate_count
    visible_ids = {row.candidate_id for row in result.score_ranking[:visible_count]}
    existing = {item.candidate_id for item in result.final_proposals}
    existing.update(item.proposal.candidate_id for item in result.additional_proposals)
    available = [candidate_id for candidate_id in visible_ids - top - existing
                 if candidate_id in candidates and candidate_id in evaluations
                 and evaluations[candidate_id].gate_passed]
    if not available:
        return
    with st.expander("Generate a detailed proposal for another scored idea"):
        labels = {candidate_id: candidates[candidate_id].title for candidate_id in available}
        selected = st.selectbox(
            "Gate-passing non-finalist", available,
            format_func=lambda candidate_id: f"{labels[candidate_id]} ({candidate_id})",
            key=f"extra-proposal-choice:{result.run_id}",
        )
        budget = result.prepared_run.budgets
        usage = result.budget_usage
        tokens_used = usage.model_tokens if usage else 0
        tokens_remaining = max(0, budget.max_model_tokens - tokens_used)
        cost_used = usage.estimated_cost_usd or 0.0 if usage else 0.0
        cost_remaining = (max(0.0, budget.max_estimated_cost_usd - cost_used)
                          if budget.max_estimated_cost_usd is not None else None)
        st.caption(
            f"This reuses collected sources and the selected idea's scored evidence. "
            f"It may use remaining proposal-writing and verification calls; no new search runs. "
            f"Remaining budget: {tokens_remaining} model tokens"
            + (f", about ${cost_remaining:.4f} estimated cost" if cost_remaining is not None else "")
            + "."
        )
        approved = st.checkbox(
            "I approve using this run's remaining budget for this proposal",
            key=f"extra-proposal-approve:{result.run_id}:{selected}",
        )
        if st.button("Generate selected proposal", disabled=not approved,
                     key=f"extra-proposal-run:{result.run_id}:{selected}"):
            try:
                updated = asyncio.run(generate_nonfinalist_proposal(
                    result, selected, client_factory(),
                ))
                st.session_state.result = updated
                save_run_result(updated)
                st.rerun()
            except Exception as error:
                st.error(safe_error_message(error))
