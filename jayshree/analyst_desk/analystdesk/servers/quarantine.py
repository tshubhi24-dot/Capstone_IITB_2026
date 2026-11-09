"""Fix 3 — only typed fields cross the hand-off (use cases 3 and 4).

The laundering step. A specialist reads untrusted text — filing passages, or
whatever `run_python` chose to return — and hands the research lead
`findings: str`, up to 6,000 characters of its own prose. Everything it read is
therefore free to arrive at the writer **in the specialist's voice**, which the
writer has every reason to treat as verified research. An injected instruction
does not have to survive as a quote; it only has to be obeyed once, by an agent
whose summary nobody checks.

That is the channel this closes. After Fix 3 the hand-off carries:

    text readers (researcher, risk_diff)   spans copied verbatim out of a
                                           passage they cite, each checked by
                                           code against that passage's text
    the quant                              fact_ids only — code looks up every
                                           value, so the model writes no number

and nothing else. **No sentence written by a specialist reaches the writer.**
The model's job becomes selection; code decides what the words are. That is
rule 1 applied to prose, where it had only ever been applied to figures
(`figures.py` does exactly this for the KEY FIGURES table, which is why the
quant does not need to hand numbers across at all).

This is the pattern in docs/notes/quarantine-text.png: the untrusted text is
read on one side of a boundary and only typed fields cross it. It is not the
whole pattern — here the reader still holds tools, because it is the reader
that has to fetch — so what Fix 3 removes is the *re-voicing*, not the reading.

**What it does not claim**, in the order the questions get asked:

1. **Selection is still the model's.** It can pick a misleading span, or leave
   out the one that mattered. Omission is untouched by this and by everything
   else in the project.
2. **An injection that is genuinely in a filing can still cross**, as a quote.
   It arrives attributed to a passage id and visible as a quotation rather than
   as a finding, and Fix 1 refuses advisory wording at the write — but arbitrary
   framing still gets through.
3. **The writer still composes freely.** It can distort quoted material in its
   own prose; `check_note` checks numbers and citations, not faithfulness.
4. **C2 only.** C1 pours raw tool output into the writer's prompt
   (`agent/graph.py:296-298`), so none of this applies there.

**Shape in the schema, everything else in verification.** The models below
constrain the *shape* of a hand-off and nothing more: two lists, a string and
an id. Every rule about content — is the quote verbatim, is it a sensible
length, are there too many claims — is checked in verify_passages and
verify_facts, one claim at a time, so a claim that breaks a rule costs that
claim and nothing else. The bounds used to sit on the fields, where pydantic
rejects the whole object: one 9-character quote among nine good ones, or a
thirteenth claim, raised ValidationError, run_specialist recorded "hand-off
could not be typed" and the entire hand-off was lost. That failed in the safe
direction, so it was never a hole — but it cost a specialist's whole
contribution for a mistake it was never told how to avoid, and the limits are
in ASK now as well.

Verification needs passage text, which is injected the way `check_note` takes
it — never `filings_kb.get_passage`, which would drag the Chroma index and
torch into a path that only needs a dict of strings.
"""

# Fix for Module 4 - Security — this whole module is new in Module 4 (Fix 3).

from __future__ import annotations

import re
from typing import Callable

from pydantic import BaseModel, Field

# Which specialists hand back which kind of claim. A specialist in neither set
# hands back nothing, which is the safe default for one added later.
TEXT_READERS = frozenset({"researcher", "risk_diff"})
NUMBER_READERS = frozenset({"quant"})

# Checked in verify_*, not on the fields: see the docstring. ASK quotes all
# three at the model, built from these names so prompt and code cannot drift.
MAX_CLAIMS = 12
MIN_QUOTE = 10
MAX_QUOTE = 300
_WS = re.compile(r"\s+")
_FACT_ID = re.compile(r"^[A-Za-z]+/\d{4}/\d{10}-\d{2}-\d{6}$")


class PassageClaim(BaseModel):
    """One finding, as a span of the filing it is quoted from.

    The length bounds are described here, for the model to read, and enforced
    in verify_passages, so breaking one drops this claim rather than the
    message it arrived in.
    """
    passage_id: str = Field(description="Id of the passage this is quoted from, "
                                        "e.g. MSFT_2024_item7_017")
    quote: str = Field(description="Text copied character-for-character out of that passage. "
                                   "Not a paraphrase and not a summary; between "
                                   f"{MIN_QUOTE} and {MAX_QUOTE} characters")


class FactClaim(BaseModel):
    """One XBRL fact worth reporting. Deliberately carries no value: the model
    names the fact, code looks up what it says."""
    fact_id: str = Field(description="concept/fiscal_year/accession, exactly as a tool "
                                     "result gave it")


class Handoff(BaseModel):
    """Everything a specialist may hand back. Two lists of ids and spans, and
    no free-text field — not even a confidence word, which code computes from
    what survived verification rather than taking the model's opinion of it."""
    claims: list[PassageClaim] = Field(default_factory=list)
    facts: list[FactClaim] = Field(default_factory=list)


# What the specialist is asked for on its final turn, in place of a summary.
ASK = {
    "text": ("Now hand your findings to the research lead. For each point, copy the exact "
             "sentence from the passage that supports it, character for character, and give "
             "that passage's id. Do not paraphrase, shorten or join sentences: code checks "
             "every quote against the passage it cites and drops any that is not verbatim, "
             "so a paraphrase reaches nobody. "
             f"Hand back at most {MAX_CLAIMS} points, each quote between {MIN_QUOTE} and "
             f"{MAX_QUOTE} characters. A point outside that is dropped on its own; the rest "
             "still cross, so send the ones you have rather than nothing."),
    "number": ("Now hand your findings to the research lead. List the fact_ids you used, "
               "exactly as the tool results gave them. Do not write any numbers: code looks "
               "up every value from its fact_id, so a number you type reaches nobody. "
               f"At most {MAX_CLAIMS} fact_ids; any beyond that are not read."),
}


def ask_for(agent: str) -> str | None:
    """The hand-off question for this specialist, or None if it hands back nothing."""
    if agent in TEXT_READERS:
        return ASK["text"]
    if agent in NUMBER_READERS:
        return ASK["number"]
    return None


def _flat(text: str) -> str:
    """Whitespace-normalised and lowered: a quote must match the passage's words,
    not its line breaks or its table padding."""
    return _WS.sub(" ", text or "").strip().lower()


def _default_passage_text(passage_id: str) -> str | None:
    global _PASSAGES
    if _PASSAGES is None:
        from ..ingest import load_passages
        _PASSAGES = {p["passage_id"]: p["text"] for p in load_passages()}
    return _PASSAGES.get(passage_id)


_PASSAGES: dict[str, str] | None = None


def _within_cap(claims, kind: str):
    """(the first MAX_CLAIMS claims, a counted reason for any past it).

    The cap bounds what one specialist can put in front of the writer, and —
    for facts — how many XBRL lookups one hand-off can cause. Applied here
    rather than by the schema so a thirteenth claim costs the thirteenth claim.
    """
    claims = list(claims)
    if len(claims) <= MAX_CLAIMS:
        return claims, []
    extra = len(claims) - MAX_CLAIMS
    return claims[:MAX_CLAIMS], [f"{extra} further {kind}{'' if extra == 1 else 's'} not read: "
                                 f"{MAX_CLAIMS} is the limit for one hand-off"]


def verify_passages(claims, passage_text: Callable[[str], str | None] | None = None):
    """(kept, dropped). A claim survives only if it is within the length bounds
    and its quote really occurs in the passage it cites.

    Length is checked before the passage is looked up: it is the cheaper test
    and the more useful reason to report.
    """
    lookup = passage_text or _default_passage_text
    kept, dropped = [], []
    claims, past_cap = _within_cap(claims, "quote")
    for c in claims:
        pid = (c.passage_id or "").strip()
        quote = (c.quote or "").strip()
        where = pid or "(no id)"
        if len(quote) < MIN_QUOTE:
            dropped.append(f"{where}: quote is under {MIN_QUOTE} characters")
            continue
        if len(quote) > MAX_QUOTE:
            dropped.append(f"{where}: quote is over {MAX_QUOTE} characters "
                           f"({len(quote)}) — quote one sentence, not a passage")
            continue
        source = lookup(pid)        # only now: the default lookup loads every passage
        if source is None:
            dropped.append(f"{where}: cited passage does not exist")
        elif _flat(quote) not in _flat(source):
            dropped.append(f"{pid}: quote is not in that passage (paraphrased or invented)")
        else:
            kept.append(PassageClaim(passage_id=pid, quote=quote))
    return kept, dropped + past_cap


def verify_facts(claims, fact_value: Callable[[str], float | None] | None = None):
    """(kept, dropped) where kept is [(fact_id, value_usd)] — the value read by
    code from XBRL, never from the model."""
    lookup = fact_value or _default_fact_value
    kept, dropped = [], []
    claims, past_cap = _within_cap(claims, "fact_id")
    for c in claims:
        fid = (c.fact_id or "").strip()
        if not _FACT_ID.match(fid):
            dropped.append(f"{fid or '(no id)'}: not a fact_id "
                           "(Concept/YYYY/0000000000-00-000000)")
            continue
        value = lookup(fid)
        if value is None:
            dropped.append(f"{fid}: does not resolve to an XBRL fact")
        else:
            kept.append((fid, value))
    return kept, dropped + past_cap


def _default_fact_value(fact_id: str) -> float | None:
    from .edgar_server import get_fact
    r = get_fact(fact_id)
    return r.fact.value_usd if r.ok and r.fact else None


def render(handoff: dict) -> str:
    """One dumped HandoffMessage, as the writer sees it.

    Dropped claims are counted, never shown: the writer must not be handed the
    text code has just refused, and the count is what belongs in the trace and
    in front of the analyst at the gate.
    """
    claims = handoff.get("claims") or []
    facts = handoff.get("facts") or []
    dropped = handoff.get("dropped") or []
    company = handoff.get("company")
    who = f"{handoff.get('agent', '?')}/{company}" if company else handoff.get("agent", "?")

    counts = [f"{len(claims)} verified quote{'' if len(claims) == 1 else 's'}" if claims else "",
              f"{len(facts)} fact{'' if len(facts) == 1 else 's'}" if facts else "",
              f"{len(dropped)} dropped" if dropped else ""]
    head = f"[{who}] ({'; '.join(c for c in counts if c) or 'nothing verified'})"

    lines = [f'- "{c["quote"]}" [{c["passage_id"]}]' for c in claims]
    for f in facts:
        concept, year = f["fact_id"].split("/")[0], f["fact_id"].split("/")[1]
        lines.append(f"- {concept} {year}: ${f['value_usd'] / 1e6:,.1f}M [fact: {f['fact_id']}]")
    return "\n".join([head, *lines]) if lines else head + "\n- (nothing survived verification)"
