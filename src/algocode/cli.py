"""
Command-line interface for algocode.
Exposes CLI commands, interactive NL queries, direct DSL execution, and the MCP server.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from algocode.mcp_server import MCPServer
from algocode.nl_dsl_llm import InterfaceAdapters, NLDSLLLMBridge


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="algocode: Algorithmic Code & Backlog Analysis Engine with NL-DSL-LLM & MCP"
    )
    parser.add_argument(
        "--nl",
        help="Execute natural language query (Polish or English), e.g. 'znajdź duplikaty w src/'",
    )
    parser.add_argument(
        "--dsl",
        help="Execute canonical DSL command directly, e.g. 'code.dedup path=src min_lines=5'",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Execute conformance self-test suite",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommands")

    # mcp subcommand
    subparsers.add_parser("mcp", help="Run Model Context Protocol (MCP) server over stdio")

    # dedup subcommand
    p_dedup = subparsers.add_parser("dedup", help="Scan for code duplicates and structural clones")
    p_dedup.add_argument("path", nargs="?", default=".", help="Target path to scan")
    p_dedup.add_argument("--min-lines", type=int, default=5, help="Minimum duplicate lines")

    # conflicts subcommand
    p_conf = subparsers.add_parser("conflicts", help="Detect workstream and path conflicts")
    p_conf.add_argument("path", nargs="?", default=".", help="Repository root")

    # triage subcommand
    p_triage = subparsers.add_parser("triage", help="Algorithmic backlog and issue triage")
    p_triage.add_argument("path", nargs="?", default=".", help="Repository root")

    # inspect subcommand
    p_insp = subparsers.add_parser("inspect", help="Inspect AST classes and functions")
    p_insp.add_argument("file", help="Python source file to inspect")

    args = parser.parse_args(argv or sys.argv[1:])

    bridge = NLDSLLLMBridge()

    if args.subcommand == "mcp":
        server = MCPServer(bridge)
        server.run_stdio()
        return 0

    if args.self_test:
        from algocode.nl_dsl_llm import NLPatternParser
        print("Running algocode self-test...")
        # Check NL matching
        cmd = NLPatternParser.parse("znajdź duplikaty w .")
        assert cmd is not None and cmd.entity == "code" and cmd.operation == "dedup"
        res = bridge.handle_request("znajdź duplikaty w .")
        assert res.success is True
        print("✓ Layer 1 NL Pattern Parser (Polish) verified")

        cmd_en = NLPatternParser.parse("check conflicts")
        assert cmd_en is not None and cmd_en.entity == "conflict" and cmd_en.operation == "check"
        res_en = bridge.handle_request("check conflicts")
        assert res_en.success is True
        print("✓ Layer 1 NL Pattern Parser (English) verified")

        res_dsl = bridge.handle_request("code.inspect file=src/algocode/models.py")
        assert res_dsl.success is True
        print("✓ Layer 2 Direct DSL execution verified")

        # Test MCP manifest
        manifest = InterfaceAdapters.mcp_tools_manifest()
        assert len(manifest) >= 5
        print(f"✓ Layer 4 MCP parity verified ({len(manifest)} tools exposed)")

        print("\nALL ALGOCODE SELF-TESTS PASSED.")
        return 0

    # Handle --nl
    if args.nl:
        res = bridge.handle_request(args.nl)
        print(InterfaceAdapters.cli_format(res, output_format=args.format))
        return 0 if res.success else 1

    # Handle --dsl
    if args.dsl:
        res = bridge.handle_request(args.dsl)
        print(InterfaceAdapters.cli_format(res, output_format=args.format))
        return 0 if res.success else 1

    # Handle subcommands
    if args.subcommand == "dedup":
        res = bridge.handle_request(f"code.dedup path={args.path} min_lines={args.min_lines}")
        print(InterfaceAdapters.cli_format(res, output_format=args.format))
        return 0 if res.success else 1

    if args.subcommand == "conflicts":
        res = bridge.handle_request(f"conflict.check path={args.path}")
        print(InterfaceAdapters.cli_format(res, output_format=args.format))
        return 0 if res.success else 1

    if args.subcommand == "triage":
        res = bridge.handle_request(f"issue.triage path={args.path}")
        print(InterfaceAdapters.cli_format(res, output_format=args.format))
        return 0 if res.success else 1

    if args.subcommand == "inspect":
        res = bridge.handle_request(f"code.inspect file={args.file}")
        print(InterfaceAdapters.cli_format(res, output_format=args.format))
        return 0 if res.success else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
