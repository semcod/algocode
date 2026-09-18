"""
NL-DSL-LLM Bridge implementing wellmanifest/nl-dsl-llm standard.
Provides:
  Layer 1: Deterministic Multi-lingual Natural Language Pattern Parser (PL & EN)
  Layer 2: Canonical DSL Engine (Single Execution Boundary)
  Layer 3: LLM Translation Fallback
  Parity Adapters: CLI formatting and MCP tools.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Dict, List, Optional

from algocode.engine import CodeAnalysisEngine
from algocode.models import DSLCommand, DSLResult


class DSLExecutor:
    """Layer 2: Canonical domain DSL executor."""

    def __init__(self, engine: Optional[CodeAnalysisEngine] = None):
        self.engine = engine or CodeAnalysisEngine()
        self._handlers: Dict[str, Callable[[DSLCommand], Any]] = {}
        self._register_default_handlers()

    def register(self, entity: str, operation: str, handler: Callable[[DSLCommand], Any]) -> None:
        key = f"{entity.lower()}.{operation.lower()}"
        self._handlers[key] = handler

    def _register_default_handlers(self) -> None:
        # code.dedup
        def handle_code_dedup(cmd: DSLCommand) -> Any:
            path = cmd.get_param("path", ".")
            min_lines = int(cmd.get_param("min_lines", 5))
            return self.engine.scan_duplicates(target_path=path, min_lines=min_lines)

        # code.inspect
        def handle_code_inspect(cmd: DSLCommand) -> Any:
            file_path = cmd.get_param("file", cmd.get_param("path", ""))
            return self.engine.inspect_ast(file_path=file_path)

        # conflict.check
        def handle_conflict_check(cmd: DSLCommand) -> Any:
            path = cmd.get_param("path", ".")
            head = cmd.get_param("head", "HEAD")
            base = cmd.get_param("base", "main")
            return self.engine.check_conflicts(repo_path=path, head_ref=head, base_ref=base)

        # issue.triage
        def handle_issue_triage(cmd: DSLCommand) -> Any:
            path = cmd.get_param("path", ".")
            return self.engine.triage_issues(repo_path=path)

        # repo.status
        def handle_repo_status(cmd: DSLCommand) -> Any:
            path = cmd.get_param("path", ".")
            conflicts = self.engine.check_conflicts(repo_path=path)
            triage = self.engine.triage_issues(repo_path=path)
            return {
                "repository": path,
                "conflict_count": len(conflicts),
                "open_issues_triaged": len(triage),
                "has_blocking_conflicts": any(c.get("severity") == "BLOCKING" for c in conflicts),
            }

        self.register("code", "dedup", handle_code_dedup)
        self.register("code", "inspect", handle_code_inspect)
        self.register("conflict", "check", handle_conflict_check)
        self.register("issue", "triage", handle_issue_triage)
        self.register("repo", "status", handle_repo_status)

    def execute(self, command: DSLCommand, source_layer: str = "direct_dsl") -> DSLResult:
        key = f"{command.entity}.{command.operation}"
        if key not in self._handlers:
            return DSLResult(
                success=False,
                data=None,
                error=f"Unknown DSL command: '{key}'. Available: {list(self._handlers.keys())}",
                meta={"sourceLayer": source_layer, "command": command.to_canonical_string()}
            )

        try:
            start_t = time.perf_counter()
            result_data = self._handlers[key](command)
            elapsed = time.perf_counter() - start_t
            return DSLResult(
                success=True,
                data=result_data,
                meta={
                    "sourceLayer": source_layer,
                    "command": command.to_canonical_string(),
                    "elapsedSeconds": round(elapsed, 4)
                }
            )
        except Exception as err:
            return DSLResult(
                success=False,
                data=None,
                error=str(err),
                meta={"sourceLayer": source_layer, "command": command.to_canonical_string()}
            )


class NLPatternParser:
    """Layer 1: Deterministic natural language parser supporting Polish & English."""

    PATTERNS = [
        # Polish: Duplikaty kodu
        (
            r"^(?:znajd[zź]|wykryj|szukaj|sprawd[zź])\s+(?:duplikat[oy]|klony)(?:\s+w\s+(?P<path>\S+))?(?:\s+min[_-]?lines=(?P<min_lines>\d+))?",
            "code", "dedup"
        ),
        # English: Code duplicates
        (
            r"^(?:find|detect|scan|check)\s+(?:code\s+)?duplicates?(?:\s+(?:in|at)\s+(?P<path>\S+))?(?:\s+min[_-]?lines=(?P<min_lines>\d+))?",
            "code", "dedup"
        ),
        # Polish: Konflikty gałęzi / ścieżek
        (
            r"^(?:sprawd[zź]|wykryj|znajd[zź])\s+konflikt[oy](?:\s+w\s+(?P<path>\S+))?",
            "conflict", "check"
        ),
        # English: Conflicts
        (
            r"^(?:check|find|detect)\s+conflicts?(?:\s+(?:in|at)\s+(?P<path>\S+))?",
            "conflict", "check"
        ),
        # Polish: Triage zgłoszeń / issues
        (
            r"^(?:triage|uporz[aą]dkuj|przeanalizuj)\s+(?:zg[lł]osz(?:enia|enie|eń|eni[ae])?|issues|zada[nń]|zadania|bilet[yów]*)(?:\s+w\s+(?P<path>\S+))?",
            "issue", "triage"
        ),
        # English: Issue triage
        (
            r"^(?:triage|analyze|prioritize)\s+issues?(?:\s+(?:in|at)\s+(?P<path>\S+))?",
            "issue", "triage"
        ),
        # Polish: Zbadaj plik AST
        (
            r"^(?:zbadaj|przeanalizuj|inspekcja)\s+plik(?:u)?\s+(?P<file>\S+)",
            "code", "inspect"
        ),
        # English: Inspect file AST
        (
            r"^(?:inspect|analyze)\s+file\s+(?P<file>\S+)",
            "code", "inspect"
        ),
        # Polish: Status repozytorium
        (
            r"^(?:status|stan)\s+repo(?:zytorium)?(?:\s+(?P<path>\S+))?",
            "repo", "status"
        ),
        # English: Repo status
        (
            r"^(?:repo|repository)\s+status(?:\s+(?P<path>\S+))?",
            "repo", "status"
        ),
    ]

    @classmethod
    def parse(cls, text: str) -> Optional[DSLCommand]:
        clean_text = text.strip()
        for pattern_str, entity, op in cls.PATTERNS:
            match = re.search(pattern_str, clean_text, re.IGNORECASE)
            if match:
                groups = match.groupdict()
                args: Dict[str, Any] = {}
                for k, v in groups.items():
                    if v is not None:
                        args[k] = v
                return DSLCommand(entity=entity, operation=op, arguments=args, raw_dsl=clean_text)
        return None


class LLMFallbackCompiler:
    """Layer 3: Fallback translation when deterministic pattern parser fails."""

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode

    def compile(self, nl_query: str) -> Optional[DSLCommand]:
        q = nl_query.lower()
        if "duplikat" in q or "duplicate" in q or "clone" in q:
            return DSLCommand(entity="code", operation="dedup", arguments={"path": "."})
        if "konflikt" in q or "conflict" in q or "overlap" in q:
            return DSLCommand(entity="conflict", operation="check", arguments={"path": "."})
        if "issue" in q or "zgłoszen" in q or "triage" in q or "bilet" in q:
            return DSLCommand(entity="issue", operation="triage", arguments={"path": "."})
        if "status" in q or "stan" in q or "health" in q:
            return DSLCommand(entity="repo", operation="status", arguments={"path": "."})
        return None


class NLDSLLLMBridge:
    """Coordinates the 3 layers conforming to wellmanifest/nl-dsl-llm standard."""

    def __init__(
        self,
        executor: Optional[DSLExecutor] = None,
        llm_compiler: Optional[LLMFallbackCompiler] = None
    ):
        self.executor = executor or DSLExecutor()
        self.llm_compiler = llm_compiler or LLMFallbackCompiler()

    def handle_request(self, request_text: str, allow_llm_fallback: bool = True) -> DSLResult:
        clean = request_text.strip()
        if not clean:
            return DSLResult(success=False, data=None, error="Empty request")

        # 1. Direct DSL Check
        if "." in clean.split()[0] or clean.startswith("code.") or clean.startswith("issue.") or clean.startswith("conflict.") or clean.startswith("repo."):
            try:
                cmd = DSLCommand.from_text(clean)
                return self.executor.execute(cmd, source_layer="direct_dsl")
            except Exception:
                pass

        # 2. Layer 1: Deterministic Fast Path (PL & EN)
        cmd1 = NLPatternParser.parse(clean)
        if cmd1 is not None:
            return self.executor.execute(cmd1, source_layer="nl_fast_path")

        # 3. Layer 3: LLM Fallback
        if allow_llm_fallback:
            cmd3 = self.llm_compiler.compile(clean)
            if cmd3 is not None:
                return self.executor.execute(cmd3, source_layer="llm_fallback")

        return DSLResult(
            success=False,
            data=None,
            error=f"Could not translate query '{clean}' to a known DSL command.",
            meta={"sourceLayer": "unresolved"}
        )


class InterfaceAdapters:
    """Universal Interface Parity: CLI, REST formatting and Model Context Protocol (MCP)."""

    @staticmethod
    def cli_format(result: DSLResult, output_format: str = "text") -> str:
        if output_format == "json":
            return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)

        if not result.success:
            return f"Error ({result.meta.get('sourceLayer', 'unknown')}): {result.error}"

        if output_format == "markdown":
            lines = [f"### Algocode Result ({result.meta.get('sourceLayer', 'direct')})"]
            if isinstance(result.data, list):
                if not result.data:
                    lines.append("*(No findings)*")
                else:
                    lines.append(f"```json\n{json.dumps(result.data, indent=2, ensure_ascii=False)}\n```")
            elif isinstance(result.data, dict):
                lines.append(f"```json\n{json.dumps(result.data, indent=2, ensure_ascii=False)}\n```")
            else:
                lines.append(str(result.data))
            return "\n".join(lines)

        # Default text
        if isinstance(result.data, (list, dict)):
            return json.dumps(result.data, indent=2, ensure_ascii=False)
        return str(result.data)

    @staticmethod
    def mcp_tools_manifest() -> List[Dict[str, Any]]:
        """Declare standard MCP tools for agents conforming to wellmanifest/nl-dsl-llm."""
        return [
            {
                "name": "nl_ask",
                "description": "Natural language algorithmic analysis (Polish/English), e.g. 'znajdź duplikaty', 'sprawdź konflikty', 'triage issues'.",
                "inputSchema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Natural language query"}
                    }
                }
            },
            {
                "name": "execute_dsl",
                "description": "Execute an algocode DSL command directly (e.g. 'code.dedup path=src min_lines=6').",
                "inputSchema": {
                    "type": "object",
                    "required": ["dsl_command"],
                    "properties": {
                        "dsl_command": {"type": "string", "description": "Canonical DSL string"}
                    }
                }
            },
            {
                "name": "code_dedup",
                "description": "Algorithmic exact and structural AST code duplication detection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": ".", "description": "Target path to scan"},
                        "min_lines": {"type": "integer", "default": 5, "description": "Minimum duplicate block lines"}
                    }
                }
            },
            {
                "name": "conflict_check",
                "description": "Algorithmic conflict detection across active tickets, workstreams, and paths.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": ".", "description": "Repository path"}
                    }
                }
            },
            {
                "name": "issue_triage",
                "description": "Algorithmic triage of backlog issues against git commit history and duplicate clusters.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": ".", "description": "Repository path"}
                    }
                }
            },
            {
                "name": "code_inspect",
                "description": "Extract AST classes, functions, imports, and metrics from a source file.",
                "inputSchema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {
                        "file": {"type": "string", "description": "Source file to inspect"}
                    }
                }
            }
        ]

    @staticmethod
    def handle_mcp_tool_call(bridge: NLDSLLLMBridge, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch MCP tool execution."""
        if tool_name == "nl_ask":
            query = arguments.get("query", "")
            res = bridge.handle_request(query)
            return {"content": [{"type": "text", "text": json.dumps(res.to_dict(), indent=2, ensure_ascii=False)}]}
        elif tool_name == "execute_dsl":
            dsl_text = arguments.get("dsl_command", "")
            cmd = DSLCommand.from_text(dsl_text)
            res = bridge.executor.execute(cmd, source_layer="direct_dsl")
            return {"content": [{"type": "text", "text": json.dumps(res.to_dict(), indent=2, ensure_ascii=False)}]}
        elif tool_name == "code_dedup":
            cmd = DSLCommand(entity="code", operation="dedup", arguments=arguments)
            res = bridge.executor.execute(cmd, source_layer="direct_dsl")
            return {"content": [{"type": "text", "text": json.dumps(res.to_dict(), indent=2, ensure_ascii=False)}]}
        elif tool_name == "conflict_check":
            cmd = DSLCommand(entity="conflict", operation="check", arguments=arguments)
            res = bridge.executor.execute(cmd, source_layer="direct_dsl")
            return {"content": [{"type": "text", "text": json.dumps(res.to_dict(), indent=2, ensure_ascii=False)}]}
        elif tool_name == "issue_triage":
            cmd = DSLCommand(entity="issue", operation="triage", arguments=arguments)
            res = bridge.executor.execute(cmd, source_layer="direct_dsl")
            return {"content": [{"type": "text", "text": json.dumps(res.to_dict(), indent=2, ensure_ascii=False)}]}
        elif tool_name == "code_inspect":
            cmd = DSLCommand(entity="code", operation="inspect", arguments=arguments)
            res = bridge.executor.execute(cmd, source_layer="direct_dsl")
            return {"content": [{"type": "text", "text": json.dumps(res.to_dict(), indent=2, ensure_ascii=False)}]}
        else:
            raise ValueError(f"Unknown MCP tool: {tool_name}")
