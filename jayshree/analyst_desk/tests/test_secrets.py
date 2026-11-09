"""Least privilege for secrets, not just tools (L7).

Each server process is started with only the secrets it needs
(`servers/client.py:_SECRET_ENV`): the model key reaches no server, and
APPROVAL_SECRET reaches only research-portal, which is the one that verifies
tokens.

compose.yaml enforces the same split for the HTTP deployment: APPROVAL_SECRET
appears in the research-portal service's environment and in no other.

Secrets at rest (the generated signing key, the SQLite files) are outside the
MCP server layer — see "Known gaps" in docs/security_summary.md.
"""

import os
import unittest
from unittest.mock import patch

from analystdesk.servers import client


class SecretScopeTests(unittest.TestCase):
    def _stdio(self) -> dict:
        """The stdio connections, i.e. the ones we hand an environment to."""
        return {name: c for name, c in client.connections().items()
                if c["transport"] == "stdio"}

    def test_model_key_reaches_no_server(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-should-not-leak"}):
            conns = self._stdio()
        self.assertTrue(conns, "no stdio connections — is MCP_URL_* set in the environment?")
        for name, conn in conns.items():
            with self.subTest(server=name):
                self.assertNotIn("OPENROUTER_API_KEY", conn["env"])

    def test_approval_secret_reaches_only_the_portal(self):
        with patch.dict(os.environ, {"APPROVAL_SECRET": "s3cret"}):
            conns = self._stdio()
        for name, conn in conns.items():
            with self.subTest(server=name):
                if name == "research-portal":
                    self.assertEqual(conn["env"].get("APPROVAL_SECRET"), "s3cret")
                else:
                    self.assertNotIn("APPROVAL_SECRET", conn["env"])

    def test_ordinary_config_is_still_passed(self):
        """Only secrets are scoped; normal knobs still reach every server."""
        with patch.dict(os.environ, {"SANDBOX_MODE": "local"}):
            conns = self._stdio()
        for name, conn in conns.items():
            with self.subTest(server=name):
                self.assertEqual(conn["env"].get("SANDBOX_MODE"), "local")


if __name__ == "__main__":
    unittest.main()
