"""
algocode - Algorithmic Code & Backlog Analysis Engine.
Adopts wellmanifest/nl-dsl-llm standard with Universal Interface Parity (CLI, REST, MCP).
"""

from algocode.engine import (
    CodeAnalysisEngine,
    check_conflict,
    check_conflicts,
    inspect_ast,
    scan_duplicates,
    triage_issues,
)

__version__ = "0.2.0"
__all__ = [
    "CodeAnalysisEngine",
    "check_conflict",
    "check_conflicts",
    "scan_duplicates",
    "triage_issues",
    "inspect_ast",
    "__version__",
]
