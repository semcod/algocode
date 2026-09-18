"""
Data models for algocode and NL-DSL-LLM contracts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DSLCommand:
    """Canonical representation of a domain command in algocode."""
    entity: str
    operation: str
    custom_operation: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None
    raw_dsl: Optional[str] = None

    def get_param(self, key: str, default: Any = None) -> Any:
        if key in self.filters:
            return self.filters[key]
        return self.arguments.get(key, default)

    def to_canonical_string(self) -> str:
        op = self.custom_operation if self.operation == "custom" and self.custom_operation else self.operation
        parts = [f"{self.entity}.{op}"]
        for k, v in sorted(self.filters.items()):
            parts.append(f"filter:{k}={json.dumps(v) if isinstance(v, (dict, list)) else v}")
        for k, v in sorted(self.arguments.items()):
            parts.append(f"{k}={json.dumps(v) if isinstance(v, (dict, list)) else v}")
        return " ".join(parts)

    @classmethod
    def from_text(cls, text: str) -> DSLCommand:
        text = text.strip()
        tokens = text.split()
        if not tokens:
            raise ValueError("Empty DSL string")

        first = tokens[0]
        if "." in first:
            entity, operation = first.split(".", 1)
            arg_tokens = tokens[1:]
        elif len(tokens) >= 2 and not any("=" in t for t in tokens[:2]):
            operation, entity = tokens[0], tokens[1]
            arg_tokens = tokens[2:]
        else:
            parts = first.split(".", 1)
            entity = parts[0]
            operation = parts[1] if len(parts) > 1 else "inspect"
            arg_tokens = tokens[1:]

        arguments: Dict[str, Any] = {}
        filters: Dict[str, Any] = {}
        for token in arg_tokens:
            if "=" in token:
                k, v = token.split("=", 1)
                # Parse JSON value if applicable
                try:
                    val = json.loads(v)
                except Exception:
                    val = v
                if k.startswith("filter:"):
                    filters[k[7:]] = val
                else:
                    arguments[k] = val

        return cls(
            entity=entity.lower(),
            operation=operation.lower(),
            arguments=arguments,
            filters=filters,
            raw_dsl=text
        )


@dataclass
class DSLResult:
    """Canonical result of executing an algocode command."""
    success: bool
    data: Any
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodeClone:
    """Represents a detected duplicate or structural clone."""
    file_a: str
    lines_a: tuple[int, int]
    file_b: str
    lines_b: tuple[int, int]
    clone_type: str  # 'exact' or 'structural'
    line_count: int
    similarity: float
    snippet: str


@dataclass
class ConflictFinding:
    """Represents an active conflict between workstreams, tickets, or branches."""
    severity: str  # 'BLOCKING', 'WARNING', 'SAFE'
    kind: str  # 'path_overlap', 'workstream_limit', 'dirty_overlap', 'unassigned_delta'
    resource: str
    description: str
    colliding_entities: List[str]


@dataclass
class IssueTriageRecord:
    """Algorithmic triage assessment for an issue/ticket."""
    number_or_id: str
    title: str
    status: str
    classification: str  # 'ACTIONABLE', 'DUPLICATE', 'ALREADY_RESOLVED', 'CONSOLIDATED', 'CONFLICT'
    confidence: float
    reason: str
    related_items: List[str] = field(default_factory=list)
    suggested_action: str = ""
