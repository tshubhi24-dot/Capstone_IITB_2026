"""One or more tests per MCP tool (L7 minimum bar), called through a real
MCP client connected in memory — the same protocol path an agent uses.
"""

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastmcp import Client

from analystdesk import approval
from analystdesk.servers import AGENT_TOOLS, SERVERS, WRITE_TOOLS
from analystdesk.servers import edgar_server, filings_kb, portal, sandbox


def call(server, tool, **args):
    async def go():
        async with Client(server.mcp) as client:
            return (await client.call_tool(tool, args, raise_on_error=False)).structured_content
    return asyncio.run(go())


def list_tools(server):
    async def go():
        async with Client(server.mcp) as client:
            return await client.list_tools()
    return asyncio.run(go())


# ── filings-kb ────────────────────────────────────────────────────────────────

PASSAGES = [
    {"passage_id": "MSFT_2024_item7_020", "company": "MSFT", "fiscal_year": 2024, "item": "item7",
     "kind": "table", "accession": "0000950170-24-087843", "text": "Intelligent Cloud | $105,362"},
    {"passage_id": "MSFT_2024_item1a_007", "company": "MSFT", "fiscal_year": 2024, "item": "item1a",
     "kind": "text", "accession": "0000950170-24-087843", "text": "We are investing in AI"},
]


class FakeRetriever:
    """Stands in for HybridRetriever: these tests check the tool contract,
    retrieval quality is measured by scripts/eval_retrieval.py."""
    pid_to_passage = {p["passage_id"]: p for p in PASSAGES}

    def __init__(self):
        self.calls = []

    def search(self, query, top_k=5, company=None, year=None, item=None, **_):
        self.calls.append(dict(query=query, company=company, year=year, item=item))
        return [{**p, "score": 1.0} for p in PASSAGES
                if (not company or p["company"] == company)
                and (not year or p["fiscal_year"] == year)
                and (not item or p["item"] == item)][:top_k]


class FilingsKbTests(unittest.TestCase):
    def setUp(self):
        self.retriever = FakeRetriever()
        filings_kb.set_retriever(self.retriever)
        self.addCleanup(filings_kb.set_retriever, None)

    def test_search_filings_with_filters(self):
        r = call(filings_kb, "search_filings", query="cloud revenue", company="msft",
                 fiscal_year=2024, item="item7")
        self.assertTrue(r["ok"])
        self.assertEqual([p["passage_id"] for p in r["passages"]], ["MSFT_2024_item7_020"])
        self.assertEqual(self.retriever.calls[-1]["company"], "MSFT")

    def test_search_filings_decomposes_without_filters(self):
        call(filings_kb, "search_filings", query="Microsoft AI risks in 2024")
        self.assertEqual((self.retriever.calls[-1]["company"], self.retriever.calls[-1]["year"]),
                         ("MSFT", 2024))

    def test_search_filings_out_of_coverage_is_an_error_result(self):
        r = call(filings_kb, "search_filings", query="x", company="TSLA")
        self.assertEqual((r["ok"], r["error"]["code"]), (False, "NOT_IN_COVERAGE"))
        r = call(filings_kb, "search_filings", query="x", fiscal_year=2019)
        self.assertEqual(r["error"]["code"], "NOT_IN_COVERAGE")

    def test_get_passage(self):
        r = call(filings_kb, "get_passage", passage_id="MSFT_2024_item1a_007")
        self.assertEqual(r["passage"]["text"], "We are investing in AI")
        r = call(filings_kb, "get_passage", passage_id="NOPE_1")
        self.assertEqual(r["error"]["code"], "NOT_FOUND")


# ── edgar (reads the committed EDGAR cache) ──────────────────────────────────

class EdgarTests(unittest.TestCase):
    def test_list_filings(self):
        r = call(edgar_server, "list_filings", ticker="MSFT")
        years = {f["fiscal_year"] for f in r["filings"] if f["form"] == "10-K"}
        self.assertTrue({2022, 2023, 2024} <= years)

    def test_get_financials(self):
        r = call(edgar_server, "get_financials", ticker="MSFT", fiscal_year=2024)
        self.assertEqual(r["margin_basis"], "operating")
        self.assertEqual(r["revenue"]["value_usd"], 245_122_000_000)
        self.assertEqual(r["operating_income"]["fact_id"],
                         "OperatingIncomeLoss/2024/0000950170-24-087843")
        self.assertEqual(r["revenue"]["eligibility"], "unverified")
        self.assertTrue(r["revenue"]["versions"])
        self.assertTrue(any("non-reliance" in warning for warning in r["warnings"]))

    def test_get_financials_bank_and_restatement(self):
        r = call(edgar_server, "get_financials", ticker="BAC", fiscal_year=2024)
        self.assertEqual(r["margin_basis"], "pretax")
        self.assertEqual(r["revenue"]["value_usd"], 101_887_000_000)   # as reported
        self.assertEqual(r["revenue"]["restated_value_usd"], 105_856_000_000)
        self.assertTrue(r["warnings"])

    def test_get_financials_out_of_coverage(self):
        r = call(edgar_server, "get_financials", ticker="MSFT", fiscal_year=2019)
        self.assertEqual(r["error"]["code"], "NOT_IN_COVERAGE")

    def test_get_fact_verifies_exact_filing(self):
        r = call(edgar_server, "get_fact", fact_id="OperatingIncomeLoss/2024/0000950170-24-087843")
        self.assertEqual((r["ticker"], r["fact"]["value_usd"]), ("MSFT", 109_433_000_000))
        r = call(edgar_server, "get_fact", fact_id="OperatingIncomeLoss/2024/0000000000-00-000000")
        self.assertEqual(r["error"]["code"], "NOT_FOUND")
        r = call(edgar_server, "get_fact", fact_id="operating income 2024")
        self.assertEqual(r["error"]["code"], "BAD_INPUT")

    def test_get_fact_rejects_non_annual_or_ineligible_form(self):
        entry = {"accn": "0000789019-24-000001", "start": "2023-01-01", "end": "2024-06-30",
                 "fp": "FY", "form": "10-K", "filed": "2024-08-01", "val": 100}
        fact_id = "Revenues/2024/0000789019-24-000001"
        for item in (entry, {**entry, "start": "2023-07-01", "form": "10-Q"}):
            data = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [item]}}}}}
            with self.subTest(item=item), patch("analystdesk.edgar.fetch_company_facts", return_value=data):
                result = call(edgar_server, "get_fact", fact_id=fact_id)
            self.assertEqual(result["error"]["code"], "NOT_FOUND")


# ── python-sandbox (local mode; Docker mode tested when available) ───────────

class SandboxTests(unittest.TestCase):
    mode = "local"

    def setUp(self):
        patcher = patch.dict(os.environ, {"SANDBOX_MODE": self.mode})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_run_python_calculates(self):
        r = call(sandbox, "run_python", code="result = round(data['op'] / data['rev'] * 100, 2)",
                 data={"op": 109433, "rev": 245122})
        self.assertEqual((r["ok"], r["result"], r["sandbox_mode"]), (True, 44.64, self.mode))

    def test_run_python_blocks_network_and_files(self):
        for code in ("import socket", "result = pd.read_csv('http://example.com/a.csv')",
                     "pd.DataFrame({'a': [1]}).to_csv('x.csv')"):
            with self.subTest(code=code):
                r = call(sandbox, "run_python", code=code)
                self.assertEqual(r["error"]["code"], "BLOCKED")

    def test_run_python_reports_errors_and_timeouts(self):
        self.assertEqual(call(sandbox, "run_python", code="result = 1/0")["error"]["code"], "EXEC_ERROR")
        r = call(sandbox, "run_python", code="while True: pass", timeout_s=2)
        self.assertEqual(r["error"]["code"], "TIMEOUT")

    def test_run_python_sees_no_secrets(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-secret"}):
            r = call(sandbox, "run_python", code="result = str(data)", data=None)
        self.assertNotIn("sk-secret", str(r))


@unittest.skipUnless(sandbox.docker_available(), "Docker or the analystdesk-sandbox image is not available")
class DockerSandboxTests(SandboxTests):
    mode = "docker"


# ── research-portal ──────────────────────────────────────────────────────────

class PortalTests(unittest.TestCase):
    NOTE = dict(title="MSFT vs GOOGL margins", body="MSFT 44.64% [fact ...]", tickers=["MSFT", "GOOGL"])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {"PORTAL_DB": str(Path(tmp.name) / "portal.db"),
                                      "APPROVAL_SECRET": "test-secret"})
        env.start()
        self.addCleanup(env.stop)

    def _token(self, **note):
        n = {**self.NOTE, **note}
        return approval.sign(n["title"], n["body"], n["tickers"], approver="analyst")

    def test_publish_note_with_valid_approval(self):
        r = call(portal, "publish_note", **self.NOTE, approval_token=self._token())
        self.assertTrue(r["ok"], r)
        again = call(portal, "publish_note", **self.NOTE, approval_token=self._token())
        self.assertEqual(again["error"]["code"], "ALREADY_EXISTS")

    def test_edit_after_approval_invalidates_it(self):
        token = self._token()
        edited = {**self.NOTE, "body": self.NOTE["body"] + " Buy MSFT."}
        r = call(portal, "publish_note", **edited, approval_token=token)
        self.assertEqual(r["error"]["code"], "APPROVAL_INVALID")
        self.assertIn("approved again", r["error"]["message"])

    def test_forged_token_is_refused(self):
        token = self._token()
        payload, _ = token.split(".")
        r = call(portal, "publish_note", **self.NOTE, approval_token=payload + ".forged")
        self.assertEqual(r["error"]["code"], "APPROVAL_INVALID")
        with patch.dict(os.environ, {"APPROVAL_SECRET": "attacker-guess"}):
            forged = self._token()
        r = call(portal, "publish_note", **self.NOTE, approval_token=forged)
        self.assertEqual(r["error"]["code"], "APPROVAL_INVALID")

    def test_get_past_notes(self):
        call(portal, "publish_note", **self.NOTE, approval_token=self._token())
        r = call(portal, "get_past_notes", ticker="googl")
        self.assertEqual([n["title"] for n in r["notes"]], [self.NOTE["title"]])
        self.assertEqual(call(portal, "get_past_notes", ticker="AAPL")["notes"], [])

    def test_signed_review_context_is_persisted_without_exposing_it_to_past_notes(self):
        context = {"version": 1, "request": "private request", "plan": {"companies": ["MSFT"]},
                   "check": {"ok": True}}
        token = approval.sign(self.NOTE["title"], self.NOTE["body"], self.NOTE["tickers"],
                              "analyst", context=context)
        result = call(portal, "publish_note", **self.NOTE, approval_token=token)
        self.assertTrue(result["ok"])
        with portal._connect() as con:
            row = con.execute("SELECT context_json FROM approval_context WHERE note_id = ?",
                              (result["note_id"],)).fetchone()
        self.assertEqual(json.loads(row["context_json"]), context)
        self.assertNotIn("private request", json.dumps(call(portal, "get_past_notes", ticker="MSFT")))

    def test_tampering_with_signed_review_context_invalidates_token(self):
        context = {"version": 1, "plan": {"companies": ["MSFT"]}, "check": {"ok": True}}
        token = approval.sign(self.NOTE["title"], self.NOTE["body"], self.NOTE["tickers"],
                              "analyst", context=context)
        payload, signature = token.split(".")
        claims = json.loads(approval._unb64(payload))
        claims["review_context"]["check"]["ok"] = False
        forged = approval._b64(json.dumps(claims, sort_keys=True).encode()) + "." + signature
        result = call(portal, "publish_note", **self.NOTE, approval_token=forged)
        self.assertEqual(result["error"]["code"], "APPROVAL_INVALID")

    def test_graph_review_context_requires_passing_check_and_bound_snapshot(self):
        digest = approval.note_hash(self.NOTE["title"], self.NOTE["body"], self.NOTE["tickers"])
        snapshot = {"version": 1, "note_sha256": digest, "facts": {}, "passages": {},
                    "policy_sha256": "a" * 64}
        for check, evidence in (({"ok": False}, snapshot), ({"ok": True}, None),
                                ({"ok": True}, {**snapshot, "note_sha256": "wrong"})):
            with self.subTest(check=check, evidence=evidence):
                context = {"version": 2, "check": check, "evidence_snapshot": evidence}
                token = approval.sign(self.NOTE["title"], self.NOTE["body"], self.NOTE["tickers"],
                                      "analyst", context=context)
                result = call(portal, "publish_note", **self.NOTE, approval_token=token)
                self.assertEqual(result["error"]["code"], "APPROVAL_INVALID")

    def test_withdrawal_preserves_audit_and_hides_note_from_retrieval(self):
        published = call(portal, "publish_note", **self.NOTE, approval_token=self._token())
        note_id = published["note_id"]
        portal.change_lifecycle(note_id, "withdraw", "Incorrect data", "analyst")
        self.assertEqual(call(portal, "get_past_notes", ticker="MSFT")["notes"], [])
        with portal._connect() as con:
            self.assertEqual(con.execute("SELECT title FROM notes WHERE id = ?", (note_id,)).fetchone()[0],
                             self.NOTE["title"])
            self.assertEqual(con.execute("SELECT action, reason FROM note_lifecycle").fetchone()[0], "withdraw")
        with self.assertRaisesRegex(portal.LifecycleError, "already"):
            portal.change_lifecycle(note_id, "withdraw", "Again", "analyst")

    def test_supersession_requires_new_reviewed_active_same_ticker_note(self):
        old = call(portal, "publish_note", **self.NOTE, approval_token=self._token())["note_id"]
        replacement = {**self.NOTE, "body": "Corrected body."}
        legacy = approval.sign(replacement["title"], replacement["body"], replacement["tickers"], "analyst")
        new = call(portal, "publish_note", **replacement, approval_token=legacy)["note_id"]
        with self.assertRaisesRegex(portal.LifecycleError, "fresh graph approval"):
            portal.change_lifecycle(old, "supersede", "Correction", "analyst", new)
        reviewed = {**replacement, "body": "Another corrected body."}
        token = approval.sign(reviewed["title"], reviewed["body"], reviewed["tickers"], "analyst",
                              context={"version": 1, "check": {"ok": True}})
        new = call(portal, "publish_note", **reviewed, approval_token=token)["note_id"]
        portal.change_lifecycle(old, "supersede", "Correction", "analyst", new)
        ids = [note["note_id"] for note in call(portal, "get_past_notes", ticker="MSFT")["notes"]]
        self.assertNotIn(old, ids)
        self.assertIn(new, ids)
        with self.assertRaisesRegex(portal.LifecycleError, "already"):
            portal.change_lifecycle(old, "supersede", "Correction again", "analyst", new)

    def test_registered_key_enforces_signature_on_lifecycle_digest(self):
        from analystdesk.servers import signing
        note_id = call(portal, "publish_note", **self.NOTE, approval_token=self._token())["note_id"]
        with patch.object(signing, "enabled", return_value=True), \
             patch.object(signing, "verify", side_effect=signing.SignatureError("signature required")):
            with self.assertRaisesRegex(portal.LifecycleError, "signature required"):
                portal.change_lifecycle(note_id, "withdraw", "incorrect", "analyst")
        with patch.object(signing, "enabled", return_value=True), patch.object(signing, "verify") as verify:
            portal.change_lifecycle(note_id, "withdraw", "incorrect", "analyst", signature="signed")
        verify.assert_called_once_with("analyst", "signed",
                                       portal.lifecycle_digest(note_id, "withdraw", None, "incorrect", "analyst"))

    def test_real_signature_binds_lifecycle_fields(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from analystdesk.servers import signing
        note_id = call(portal, "publish_note", **self.NOTE, approval_token=self._token())["note_id"]
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        with tempfile.TemporaryDirectory() as keys, patch.dict(os.environ, {"APPROVER_KEYS_DIR": keys}):
            (Path(keys) / "analyst.pub").write_text(signing._b64(public), encoding="utf-8")
            digest = portal.lifecycle_digest(note_id, "withdraw", None, "incorrect", "analyst")
            signature = signing._b64(private.sign(digest.encode("ascii")))
            with self.assertRaises(portal.LifecycleError):
                portal.change_lifecycle(note_id, "withdraw", "different reason", "analyst", signature=signature)
            with self.assertRaises(portal.LifecycleError):
                portal.change_lifecycle(note_id, "withdraw", "incorrect", "unknown", signature=signature)
            with self.assertRaises(portal.LifecycleError):
                portal.change_lifecycle(note_id, "withdraw", "incorrect", "analyst", signature="forged")
            portal.change_lifecycle(note_id, "withdraw", "incorrect", "analyst", signature=signature)

    def test_publication_rejects_context_if_lifecycle_changes_after_approval(self):
        old = call(portal, "publish_note", **self.NOTE, approval_token=self._token())["note_id"]
        draft = {**self.NOTE, "body": "New note with stale review context."}
        token = approval.sign(draft["title"], draft["body"], draft["tickers"], "analyst",
                              context={"check": {"ok": True}, "memory_on": True, "lifecycle_epoch": 0})
        portal.change_lifecycle(old, "withdraw", "incorrect", "analyst")
        result = call(portal, "publish_note", **draft, approval_token=token)
        self.assertEqual(result["error"]["code"], "APPROVAL_INVALID")
        self.assertIn("fresh run", result["error"]["message"])


# ── schemas and permissions ──────────────────────────────────────────────────

class RegistryTests(unittest.TestCase):
    MODULES = {"filings-kb": filings_kb, "edgar": edgar_server,
               "python-sandbox": sandbox, "research-portal": portal}

    def test_every_tool_is_typed_and_marked_read_or_write(self):
        seen = set()
        for name, module in self.MODULES.items():
            for tool in list_tools(module):
                seen.add(tool.name)
                with self.subTest(tool=tool.name):
                    self.assertTrue(tool.outputSchema, "output must be typed")
                    self.assertTrue(tool.description)
                    read_only = tool.annotations.readOnlyHint
                    self.assertEqual(read_only, tool.name not in WRITE_TOOLS)
        self.assertEqual(len(seen), 8)
        self.assertEqual(set(self.MODULES), set(SERVERS))

    def test_only_publisher_can_write(self):
        for agent, tools in AGENT_TOOLS.items():
            if agent != "publisher":
                self.assertFalse(tools & WRITE_TOOLS, agent)
        self.assertEqual(AGENT_TOOLS["publisher"], WRITE_TOOLS)


if __name__ == "__main__":
    unittest.main()
