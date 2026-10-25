"""Public content-check diagnostics from fixed messages, never model output."""
from .reasoning import ReasoningError


_REASONS = {
    "Repeat citations cannot stand in for separate evidence.": "duplicate_source_citation",
    "A citation is unknown or its quote is not in the supplied source.": "citation_provenance",
    "A model selected an unknown or repeated quotation identifier.": "invalid_quote_selection",
    "A risk comparison must cite its own issuer and both required years.": "comparison_scope",
    "A risk finding selected a quotation outside its required issuer/year slot.": "risk_citation_scope",
    "An across-year claim needs evidence from both periods.": "comparison_periods",
    "The model changed, omitted or repeated a comparison period.": "comparison_periods",
    "The comparison status does not match its cited findings.": "comparison_status",
    "Numerical or marked-up narrative is outside this live slice.": "narrative_number",
    "A narrative quantity needs a code-verified financial assertion.": "narrative_quantity",
    "A claim needs bounded, single-line prose.": "narrative_shape",
    "Selected excerpts cannot establish new, removed or absent risks.": "unsupported_risk_absence",
    "Recommendations, promised returns and external links are not allowed.": "prohibited_recommendation",
    "The writer omitted or invented a provisional risk claim revision key.": "writer_revision_scope",
    "A writer revision selected a quotation outside its required issuer/year slot.": "writer_citation_scope",
    **{f"Invalid structured model output for {stage}.": "output_schema"
       for stage in ("planner", "researcher", "risk", "writer", "critic")},
}
_STAGES = {"plan": "planner", "planner": "planner", "research_company": "researcher",
           "researcher": "researcher", "risk": "risk", "draft": "writer",
           "writer": "writer", "critic": "critic"}


def validation_diagnostic(error, stage="research", *, checkpoint=False):
    """Match exact code-owned reasons; do not stringify arbitrary exceptions."""
    if checkpoint:
        if type(error) is not str:
            return None
        reason = next((text for text in _REASONS if error == f"ReasoningError({text!r})"), None)
    else:
        if not isinstance(error, ReasoningError) or len(error.args) != 1 or type(error.args[0]) is not str:
            return None
        reason = error.args[0] if error.args[0] in _REASONS else None
    if reason is None:
        return None
    return {"code": _REASONS[reason], "stage": _STAGES.get(stage, "research"), "message": reason}


def checkpoint_diagnostic(tasks):
    """Read legacy durable failures without altering a saved run or retrying it."""
    for task in tasks:
        diagnostic = validation_diagnostic(getattr(task, "error", None),
                                           getattr(task, "name", "research"), checkpoint=True)
        if diagnostic is not None:
            return diagnostic
    return None
