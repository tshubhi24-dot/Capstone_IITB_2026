"""Only fixed validation reasons may enter public run diagnostics."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from desk.reasoning import ReasoningError
from desk.reasoning_diagnostics import checkpoint_diagnostic, validation_diagnostic
from test_live_workflow import content_failure
from test_workflow import fixture


REASON = "Repeat citations cannot stand in for separate evidence."


def test_known_reason_and_checkpoint_have_the_same_safe_code_and_stage():
    expected = {"code": "duplicate_source_citation", "stage": "risk", "message": REASON}
    assert validation_diagnostic(ReasoningError(REASON), "risk") == expected
    assert checkpoint_diagnostic([SimpleNamespace(name="risk", error=repr(ReasoningError(REASON)))]) == expected


@pytest.mark.parametrize("error", [ReasoningError("private-provider-value"),
    ReasoningError(REASON + " private-provider-value"), ReasoningError(REASON, "private-provider-value"),
    ValueError(REASON), ReasoningError({"input": "private-provider-value"})])
def test_unknown_or_input_bearing_exceptions_are_not_public_diagnostics(error):
    assert validation_diagnostic(error, "risk") is None


def test_no_exception_stringification_or_checkpoint_substring_matching():
    class UnsafeError(ReasoningError):
        def __str__(self):
            raise AssertionError("must not stringify an arbitrary exception")
    assert validation_diagnostic(UnsafeError("private-value")) is None
    assert validation_diagnostic(ReasoningError(REASON), "private-value")["stage"] == "research"
    for value in ["prefix " + repr(ReasoningError(REASON)), repr(ReasoningError(REASON)) + " private-value", REASON]:
        assert validation_diagnostic(value, "risk", checkpoint=True) is None


def test_live_failure_view_explains_fixed_reason_without_retry_or_state_changes(fixture):
    engine, store, _, _, _, _ = fixture
    _, failed = content_failure(engine, store)
    assert failed["validation_error"]["code"] == "risk_citation_scope"
    assert failed["validation_error"]["stage"] == "risk"
    assert failed["continuation"]["available"] is True
    stored = store.get_run(failed["id"])
    # Simulate a legacy record whose durable checkpoint has the safe reason.
    stored.pop("validation_error")
    stored["error"] = "ReasoningError: research stopped; inspect service diagnostics"
    store.save_run(stored)
    before = deepcopy(store.get_run(failed["id"]))
    calls = len(engine.model_client.calls)
    viewed = engine.view(failed["id"])
    assert viewed["validation_error"]["code"] == "risk_citation_scope"
    assert viewed["continuation"]["available"] is True
    assert store.get_run(failed["id"]) == before and len(engine.model_client.calls) == calls
