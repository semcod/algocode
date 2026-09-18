"""
Model Context Protocol (MCP) Server for algocode.
Implements stdio JSON-RPC 2.0 interface for AI coding assistants (Antigravity, Claude, Cursor, Windsurf).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

from algocode.nl_dsl_llm import InterfaceAdapters, NLDSLLLMBridge


class MCPServer:
    """Stdio JSON-RPC 2.0 server for Model Context Protocol."""

    def __init__(self, bridge: Optional[NLDSLLLMBridge] = None):
        self.bridge = bridge or NLDSLLLMBridge()

    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "algocode-mcp",
                        "version": "0.1.0"
                    }
                }
            }

        elif method == "notifications/initialized":
            # Client acknowledgment, no response required
            return None

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": InterfaceAdapters.mcp_tools_manifest()
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                content = InterfaceAdapters.handle_mcp_tool_call(self.bridge, tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": content
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {e}"}],
                        "isError": True
                    }
                }

        else:
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            return None

    def run_stdio(self) -> None:
        """Reads JSON-RPC messages from stdin and writes responses to stdout."""
        sys.stderr.write("Starting algocode MCP server on stdio...\n")
        sys.stderr.flush()

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError as err:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {err}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
                continue

            response = self.handle_message(msg)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
