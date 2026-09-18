# AGENTS.md — algocode

Guidelines for Human and AI agent collaboration on `semcod/algocode`.

## Principles

1. **Deterministic by Default**: Use algorithmic matching, AST inspection, and hash verification before invoking LLMs.
2. **NL-DSL-LLM Standard Compliance**: Maintain parity across Natural Language (Polish/English), canonical DSL verbs, and MCP interface.
3. **Model Context Protocol (MCP)**: AI agents should leverage `algocode mcp` tools rather than running ad-hoc shell commands when analyzing codebases.
4. **No Regressions**: All changes must pass `python3 -m unittest discover tests` with 0 failures.
