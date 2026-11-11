"""Fix 1 — a guardrail on the action, in code (use case 3: injected recommendation).

The gap this closes. check_note's advice filter is eleven literal words
("buy", "price target", "we recommend", ...). The same instruction phrased in
desk vocabulary carries none of them and carries no number either, so not one
of check_note's five rules has a candidate to inspect:

    Microsoft shares appear attractively valued at current levels and
    warrant accumulation by long-term holders.

check_note returns ok=True with 0/0 numbers verified — reported as 100%. The
input guard allows the same text pasted into a request, and C2's compliance
critic collects claims only from lines that cite a passage, so an uncited
recommendation is never even an item. tests/security/test_injected_recommendation.py
pins all of that; docs_notfor_submission/security_summary.md records it as a gap.

The guardrail. Every sentence that takes a position on the *security* — rather
than reporting something about the business — must cite its evidence. A
sentence that takes a position and cites nothing is refused, and the write tool
never runs:

    sentence matches STANCE   and   sentence has no [fact:/calc:/growth:/diff:]
                                    tag and no passage id   ->   UNSOURCED_ADVICE

Enforce or warn. ADVICE_GUARD_MODE=warn turns the refusal into a warning that
rides back on the result — the write runs, and the finding is recorded rather
than acted on. It is there because this guardrail is author-blind, so a desk
still adopting the citation rule can run it as validation while it adapts.
enforce is the default and the reasoning for keeping it that way sits next to
mode(), below.

Two halves, and only the second is enforceable. STANCE is still a vocabulary,
wider than check_note's eleven words but finite, and the next phrasing can walk
around it — a keyword list cannot be completed. The sourcing requirement is the
part that holds: it is the desk's own house style turned into a refusal, and it
applies to any sentence the vocabulary does catch, whoever wrote it. This
guardrail narrows the gap; it does not claim to close it. The note gate remains
the control that catches a recommendation nobody anticipated.

Why a middleware and not another check_note rule. check_note advises the
writer: its issues are fed back and the draft is revised. A middleware refuses:
the tool does not run, and what comes back is a normal tool error the agent can
read. The lecture's point (L14) is exactly this — callbacks fail open, an
exception is logged and the call proceeds anyway, so a control that must stop
something belongs in the wrapper around the call, not in a callback beside it.

Shape. docs_notfor_submission/notes/wraptools.png shows langchain.agents.middleware.wrap_tool_call
wrapping create_agent's tool loop. This project has no langchain.agents — it is
LangGraph plus langchain-mcp-adapters — so the same onion is reproduced over the
two dispatchers it does have, and the guardrail body is written once:

    ToolCallGuard.interceptor        langchain-mcp-adapters' ToolCallInterceptor,
                                     installed by client.make_client() and so
                                     applied to every MCP tool the agents load
    ToolCallGuard.toolnode_wrapper   ToolNode's awrap_tool_call, the same shape
                                     agent/hooks.py already uses for C1

Both are async, because every tool dispatch in this project is. The lecture's
sample is sync only because create_agent's loop can be.

Layering: this module is imported by the servers, so it defines its own copies
of checks.py's source-tag patterns rather than importing the agent package
(servers must not depend on agent). test_injected_recommendation.py asserts the
two stay in step, so they cannot drift apart silently.
"""

# Fix for Module 4 - Security — this whole module is new in Module 4 (Fix 1).

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from typing import Any

from . import WRITE_TOOLS, signing
from .common import log

# Tools this guardrail stands in front of: every tool that changes the outside
# world. publish_note is the only one today; a second write tool is covered the
# day it is added to WRITE_TOOLS, without touching this file.
GUARDED_TOOLS = frozenset(WRITE_TOOLS)

# Argument names whose value is note prose. Anything else (an approval token,
# a ticker list) is not read.
PROSE_ARGS = ("title", "body")

# A sentence ends at . ! ? or a line break. Deliberately crude: the guardrail
# only has to decide "is there a source somewhere on this sentence", and a
# split that errs toward longer sentences errs toward allowing, never toward a
# spurious refusal.
SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")

# The same evidence check_note accepts, written here so the servers do not
# import the agent package. FACT_ID copied from agent/checks.py; the drift test
# in tests/security/test_injected_recommendation.py pins both against it.
_FACT_ID = r"[A-Za-z]+/\d{4}/\d{10}-\d{2}-\d{6}"
SOURCE = re.compile(
    rf"\[(?:fact|calc|growth|diff):\s*{_FACT_ID}[^\]]*\]"
    r"|\b[A-Z]{1,5}_\d{4}_item(?:1a|7)_\d{3}\b")

# A position on the security, rather than a report about the business. The
# first group is check_note's own eleven terms, so this is a strict superset of
# ADVICE and removing a word here cannot weaken that filter. The rest is the
# paraphrase vocabulary — valuation stance and position sizing — which is what
# the eleven words miss.
STANCE = re.compile(
    r"""\b(?:
        buy | sell | hold\s+rating | overweight | underweight |
        outperform | underperform | price\s+target | we\s+recommend |
        strong\s+buy | investors\s+should
      |
        recommend\w* | target\s+price | top\s+pick | conviction\s+(?:buy|list) |
        accumulat\w* | add\s+to\s+(?:the\s+)?positions? | build\s+a\s+position |
        take\s+profits? | reduce\s+exposure | exit\s+the\s+position |
        attractively\s+valued | attractive\s+valuation | compelling\s+valuation |
        under\s?valued | over\s?valued | worth\s+(?:buying|owning|holding) |
        warrants?\s+(?:accumulation|buying|adding|a\s+position)
    )\b(?!-)""",            # (?!-) so "sell-side" and "buy-side" are not a stance
    re.I | re.X)

CODE = "UNSOURCED_ADVICE"

# Enforce or warn. ADVICE_GUARD_MODE, and the default is the one that refuses.
#
#     enforce (default)  the write never runs; ok: false, UNSOURCED_ADVICE
#     warn               the write runs, and the same finding rides back on the
#                        result under "warnings", so the gate, the trace and the
#                        dashboards all still see it
#
# warn exists because this guardrail is author-blind — it cannot tell a sentence
# the analyst typed at the gate from one the writer produced — so a desk still
# adopting the citation rule can run it as validation while it adapts. It should
# not become the default: a guardrail that records and proceeds is exactly the
# callback L14 warns about, and in warn mode an injected recommendation reaches
# the portal. Nothing here rewrites a note to make it pass, in either mode:
# approval.sign binds the token to the exact bytes, so editing the text would
# invalidate the sign-off it was approved under.
MODES = ("enforce", "warn")
DEFAULT_MODE = "enforce"


def mode() -> str:
    """ADVICE_GUARD_MODE, read per call so a process can change it.

    An unset, empty or misspelt value enforces: a typo in a deployment variable
    must not be the thing that quietly turns a control off.
    """
    raw = (os.getenv("ADVICE_GUARD_MODE") or DEFAULT_MODE).strip().lower()
    if raw not in MODES:
        log.warning("ADVICE_GUARD_MODE=%r is not one of %s — enforcing", raw, MODES)
        return DEFAULT_MODE
    return raw


def sentences(text: str) -> list[str]:
    """The text split into sentences, blanks dropped."""
    return [s.strip() for s in SENTENCE.findall(text or "") if s.strip()]


def unsourced_advice(text: str) -> list[tuple[str, str]]:
    """(sentence, the stance term it used) for each sentence that takes a
    position on the security and cites nothing. Empty means nothing to refuse."""
    out = []
    for s in sentences(text):
        m = STANCE.search(s)
        if m and not SOURCE.search(s):
            out.append((s, m.group()))
    return out


def prose(args: dict[str, Any]) -> str:
    """The note text inside a tool call's arguments."""
    return "\n".join(str(args.get(k, "")) for k in PROSE_ARGS if args.get(k))


def _finding(offending: list[tuple[str, str]], verb: str) -> str:
    """The one sentence both modes report, differing only in what it says happened."""
    terms = ", ".join(sorted({repr(t) for _s, t in offending}))
    first = offending[0][0]
    return (f"{verb}: {len(offending)} sentence(s) take a position on the security "
            f"and cite nothing ({terms}). A note may not recommend; and any sentence "
            f"that does must carry a [fact:]/[calc:] tag or cite a passage on the same "
            f"line. First: {first!r}")


def denial(offending: list[tuple[str, str]]) -> dict:
    """The refusal, in the same envelope every tool returns (common.py): ok
    plus a stable code, so the agent reads it as a tool error and can adjust."""
    return {"ok": False, "error": {"code": CODE, "message": _finding(offending, "refused")}}


def warning(offending: list[tuple[str, str]]) -> dict:
    """The same finding, as something the result carries rather than something
    that stops it. `mode` is on the payload so a reader of a published note's
    trace can tell a warning apart from a refusal without knowing the config."""
    return {"code": CODE, "mode": "warn", "message": _finding(offending, "allowed in warn mode")}


# ── the middleware ───────────────────────────────────────────────────────────

@dataclass
class ToolCall:
    """One tool call, normalised across the two dispatchers."""
    name: str
    args: dict
    id: str | None = None
    server: str | None = None


@dataclass
class ToolCallGuard:
    """A (call, handler) function, bound to the onions this project has.

    .interceptor        langchain-mcp-adapters ToolCallInterceptor
    .toolnode_wrapper   LangGraph ToolNode awrap_tool_call
    """
    fn: Any

    async def decide(self, call: ToolCall, run) -> Any:
        """The guardrail body, with `run` executing the real call.

        No state is kept here on purpose: a refusal is already a tool event
        like any other, recorded by agent/hooks.py post and observability.
        """
        async def handler(c: ToolCall):
            return await run(c)
        return await self.fn(call, handler)

    @property
    def interceptor(self):
        """langchain-mcp-adapters: async (request, handler) -> MCPToolCallResult."""
        async def intercept(request, handler):
            call = ToolCall(name=request.name, args=dict(request.args or {}),
                            server=getattr(request, "server_name", None))

            async def run(c: ToolCall):
                return await handler(replace(request, name=c.name, args=c.args))

            out = await self.decide(call, run)
            return _as_call_tool_result(out) if isinstance(out, dict) else out
        return intercept

    @property
    def toolnode_wrapper(self):
        """LangGraph ToolNode: async (request, execute) -> ToolMessage."""
        async def wrapper(request, execute):
            tc = request.tool_call
            call = ToolCall(name=tc["name"], args=dict(tc.get("args") or {}), id=tc.get("id"))

            async def run(_c: ToolCall):
                return await execute(request)

            out = await self.decide(call, run)
            if isinstance(out, dict):
                from langchain_core.messages import ToolMessage
                return ToolMessage(json.dumps(out), tool_call_id=call.id, name=call.name)
            return out
        return wrapper


def _with_warning(text: str, payload: dict) -> str | None:
    """A tool's JSON result with `payload` appended to "warnings".

    None when the text is not a JSON object this can add a key to — in which
    case the caller logs the finding rather than dropping it.
    """
    try:
        body = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(body, dict):
        return None
    existing = body.get("warnings")
    body["warnings"] = ([*existing] if isinstance(existing, list) else []) + [payload]
    return json.dumps(body)


def annotated(result: Any, payload: dict) -> Any:
    """`result` from the real tool, carrying the warning.

    Both bindings hand back the tool's JSON as text in different wrappers, so
    the merge happens on the text and the wrapper is rebuilt around it. If that
    is not possible the result is returned untouched and the finding is logged:
    a warning nobody can see would be worse than a noisy log.
    """
    for attr, rebuild in (
        ("content", _rebuild_content),      # mcp CallToolResult: list of blocks
        ("text", _rebuild_text),            # a bare text block
    ):
        if hasattr(result, attr):
            out = rebuild(result, payload)
            if out is not None:
                return out
            break
    if isinstance(result, str):
        out = _with_warning(result, payload)
        if out is not None:
            return out
    if isinstance(result, dict):
        existing = result.get("warnings")
        return {**result,
                "warnings": ([*existing] if isinstance(existing, list) else []) + [payload]}
    log.warning("%s in warn mode, and a %s result cannot carry it: %s",
                CODE, type(result).__name__, payload["message"])
    return result


def _rebuild_content(result: Any, payload: dict):
    """A CallToolResult, or a ToolMessage whose content is a string."""
    content = result.content
    if isinstance(content, str):                      # langchain ToolMessage
        text = _with_warning(content, payload)
        return result.model_copy(update={"content": text}) if text is not None else None
    if isinstance(content, list):                     # mcp CallToolResult
        blocks = list(content)
        for i, block in enumerate(blocks):
            text = _with_warning(getattr(block, "text", None) or "", payload)
            if text is not None:
                blocks[i] = block.model_copy(update={"text": text})
                return result.model_copy(update={"content": blocks})
    return None


def _rebuild_text(result: Any, payload: dict):
    text = _with_warning(getattr(result, "text", None) or "", payload)
    return result.model_copy(update={"text": text}) if text is not None else None


def _as_call_tool_result(payload: dict):
    """A refusal, as an MCP result the adapter turns into ordinary tool text.

    isError stays False on purpose: the adapter raises ToolException on an MCP
    error, and "tools return, never raise" (common.py) is the contract the whole
    agent loop is written against.
    """
    from mcp.types import CallToolResult, TextContent
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(payload))],
                          isError=False)


def wrap_tool_call(fn) -> ToolCallGuard:
    """Decorator from the lecture sample, bound to this project's dispatchers."""
    return ToolCallGuard(fn)


# Fix 1 - use case 3 (injected recommendation): deck slides 3-4, fix slide 6.
@wrap_tool_call
async def block_unsourced_advice(call: ToolCall, handler):
    """Refuse a write whose text recommends without citing anything.

    Under ADVICE_GUARD_MODE=warn the write runs and the finding rides back on
    the result instead. mode() is read here, per call, not captured at import.
    """
    if call.name in GUARDED_TOOLS:
        offending = unsourced_advice(prose(call.args))
        if offending:
            if mode() == "warn":              # soft: it runs, and it is recorded
                return annotated(await handler(call), warning(offending))
            return denial(offending)          # the tool never runs
    return await handler(call)                # everything else runs


# Fix 2 - use case 2 (forced approval injection): deck slide 2, fix slide 7.
@wrap_tool_call
async def require_approver_signature(call: ToolCall, handler):
    """Refuse a write the named approver has not signed with their own key.

    The policy, the registry and the honest limit are all in signing.py; this
    is only the binding. check() returns None when no approver key is
    registered, which is the repo's default state.
    """
    if call.name in GUARDED_TOOLS:
        reason = signing.check(call.args)
        if reason:
            return signing.denial(reason)     # the tool never runs
    return await handler(call)                # everything else runs


def interceptors() -> list:
    """The interceptor list for client.make_client() / load_mcp_tools().

    Onion order, outermost first. Both refuse rather than annotate, so the
    order only decides which reason the agent is told about first.
    """
    return [require_approver_signature.interceptor,
            block_unsourced_advice.interceptor]
