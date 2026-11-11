"""MCP servers and which agent may use which tool (L7 least privilege).

SERVERS maps each server to its module (run with `python -m <module>` over
stdio). AGENT_TOOLS is the single source of truth for permissions: each
agent is given only these tools when the graph is built (Phase 4/6), and the
pre-tool hook (Phase 6) checks every call against it again.

publish_note is the only write tool; only the publisher has it, and the
portal server still refuses it without an analyst approval token.
"""

SERVERS = {
    "filings-kb": "analystdesk.servers.filings_kb",
    "edgar": "analystdesk.servers.edgar_server",
    "python-sandbox": "analystdesk.servers.sandbox",
    "research-portal": "analystdesk.servers.portal",
}

WRITE_TOOLS = {"publish_note"}

AGENT_TOOLS = {
    # C1: one agent with every research tool, still no write tool
    "single_agent": {"search_filings", "get_passage", "list_filings", "get_financials",
                     "get_fact", "run_python", "get_past_notes"},
    # C2: the team, each with only what its job needs
    "planner":    {"list_filings"},
    "researcher": {"search_filings", "get_passage"},
    "quant":      {"get_financials", "get_fact", "run_python"},
    "risk_diff":  {"search_filings", "get_passage", "get_past_notes"},
    "critic":     {"get_fact", "get_passage"},
    "writer":     set(),             # drafts from hand-off messages only
    "publisher":  {"publish_note"},
}
