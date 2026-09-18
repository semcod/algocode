"""
Tests for algocode Model Context Protocol (MCP) server.
"""

from __future__ import annotations

import json
import unittest

from algocode.mcp_server import MCPServer
from algocode.nl_dsl_llm import NLDSLLLMBridge


class MCPServerTests(unittest.TestCase):
    def setUp(self):
        self.bridge = NLDSLLLMBridge()
        self.server = MCPServer(self.bridge)

    def test_mcp_initialize(self):
        """Verify standard MCP initialize handshake."""
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        }
        res = self.server.handle_message(req)
        self.assertIsNotNone(res)
        self.assertEqual(res["id"], 1)
        self.assertEqual(res["result"]["serverInfo"]["name"], "algocode-mcp")
        self.assertIn("tools", res["result"]["capabilities"])

    def test_mcp_tools_list(self):
        """Verify MCP tools/list returns declared tools."""
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        res = self.server.handle_message(req)
        self.assertIsNotNone(res)
        tools = res["result"]["tools"]
        tool_names = {t["name"] for t in tools}
        self.assertIn("nl_ask", tool_names)
        self.assertIn("execute_dsl", tool_names)
        self.assertIn("code_dedup", tool_names)
        self.assertIn("conflict_check", tool_names)
        self.assertIn("issue_triage", tool_names)
        self.assertIn("code_inspect", tool_names)

    def test_mcp_tool_call_nl_ask(self):
        """Verify MCP tools/call executing nl_ask."""
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "nl_ask",
                "arguments": {"query": "sprawdź konflikty"}
            }
        }
        res = self.server.handle_message(req)
        self.assertIsNotNone(res)
        self.assertEqual(res["id"], 3)
        content = res["result"]["content"]
        payload = json.loads(content[0]["text"])
        self.assertTrue(payload["success"])
        self.assertEqual(payload["meta"]["sourceLayer"], "nl_fast_path")

    def test_mcp_tool_call_direct_dedup(self):
        """Verify MCP tools/call executing code_dedup."""
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "code_dedup",
                "arguments": {"path": "src", "min_lines": 5}
            }
        }
        res = self.server.handle_message(req)
        self.assertIsNotNone(res)
        self.assertEqual(res["id"], 4)
        content = res["result"]["content"]
        payload = json.loads(content[0]["text"])
        self.assertTrue(payload["success"])


if __name__ == "__main__":
    unittest.main()
