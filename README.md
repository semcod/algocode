# algocode

**Algorithmic Code & Backlog Analysis Engine with NL-DSL-LLM Architecture and MCP Server.**

Adopts the [`wellmanifest/nl-dsl-llm`](https://github.com/wellmanifest/nl-dsl-llm) standard.

---

## Overview

`algocode` provides deterministic, algorithmic analysis of codebases, workstreams, and backlogs to replace manual ad-hoc inspection with reusable, zero-guesswork tools for developers and AI agents.

### Core Algorithmic Capabilities

1. **Exact & Structural Code Clone Detection**:
   - Exact block matching via sliding-window SHA-256 hashing.
   - Structural AST clone detection (abstracting variable, argument, and function names while matching the underlying syntax structure).
2. **Workstream & Path Conflict Analysis**:
   - Detects overlapping `allowedPaths` and `ownedPaths` between concurrent tickets and branches.
   - Enforces workstream concurrency limits to prevent merge collisions before code is written.
3. **Algorithmic Issue & Ticket Triage**:
   - Reconciles issues against recent git commits, detecting already resolved tasks.
   - Groups duplicate issues via token Jaccard similarity and shared file targets.
   - Emits recommended actions (`proceed_low_risk`, `close_as_reconciled`, `consolidate`).
4. **AST Symbol & Metric Extraction**:
   - Extracts classes, functions, decorators, imports, and structure metrics.

---

## Tripartite NL-DSL-LLM Architecture

Conforms to `wellmanifest/nl-dsl-llm`:

| Layer | Responsibility | Examples |
|---|---|---|
| **Layer 1: NL Fast-Path** | Zero-latency regex pattern matching for Polish and English | `"znajdź duplikaty w src/"`<br>`"sprawdź konflikty"`<br>`"triage zgłoszeń"`<br>`"detect duplicates in ."` |
| **Layer 2: Canonical DSL** | Deterministic domain verbs & execution boundary | `code.dedup path=src min_lines=5`<br>`conflict.check path=.`<br>`issue.triage path=.`<br>`code.inspect file=engine.py`<br>`repo.status path=.` |
| **Layer 3: LLM Fallback** | Adaptive fallback compiler for free-form queries | Translates unbounded prompts into constrained DSL statements |
| **Interface Parity** | Universal accessibility | CLI Shell, JSON API, and Model Context Protocol (MCP) |

---

## Model Context Protocol (MCP) Integration

AI coding assistants (Antigravity, Claude Code, Cursor, Windsurf) can connect to `algocode` via MCP stdio to run deterministic analyses automatically.

### Configuring in `.mcp.json` or Agent Settings

```json
{
  "mcpServers": {
    "algocode": {
      "command": "python3",
      "args": ["-m", "algocode.cli", "mcp"],
      "env": {
        "PYTHONPATH": "/home/tom/github/semcod/algocode/src"
      }
    }
  }
}
```

### Exposed MCP Tools

- `nl_ask`: Natural language query interface (Polish or English).
- `execute_dsl`: Direct DSL command execution.
- `code_dedup`: Scan repository for duplicate code and structural clones.
- `conflict_check`: Detect workstream and path conflicts between active tickets.
- `issue_triage`: Algorithmic backlog deduplication and git reconciliation.
- `code_inspect`: Inspect AST symbols, functions, and metrics in a source file.

---

## Quick Start (CLI)

```bash
# Natural language query (Polish)
algocode --nl "znajdź duplikaty w src/"

# Natural language query (English)
algocode --nl "check conflicts"

# Direct canonical DSL execution
algocode --dsl "code.dedup path=src min_lines=5"

# Subcommands
algocode dedup src/ --min-lines 5
algocode conflicts .
algocode triage .
algocode inspect src/algocode/engine.py

# Run MCP stdio server
algocode mcp

# Conformance self-test
algocode --self-test
```

---

## Testing

```bash
python3 -m unittest discover tests
```

---

## Governance & Standard Adoption

- Standard: `wellmanifest/nl-dsl-llm@0.1.0`
- Governance: `wellmanifest/new-project`
- License: Apache-2.0
