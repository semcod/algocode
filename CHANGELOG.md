# Changelog

All notable changes to `algocode` will be documented in this file.

## [0.2.0] - 2026-09-19

### Added
- Polyglot structural clone detection (Type-2 AST normalization):
  - TypeScript & JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`).
  - Go (`.go`).
  - Rust (`.rs`).
  - PHP (`.php`).
- Brace block extractor `_extract_brace_blocks` with brace balance tracking for C-family function/method spans.
- Universal structural normalizer `_structural_normalize_generic` abstracting identifiers to generic tokens (`_v1`, `_v2`) and literals to `_str`/`_num` while preserving language-specific keywords.
- Unit test coverage for polyglot structural clone detection in TypeScript, Go, and Rust (17 unit tests passing).

## [0.1.0] - 2026-09-18

### Added
- Core algorithmic analysis engine:
  - Exact sliding-window SHA-256 code block duplicate detection.
  - Structural AST clone detection with identifier abstraction.
  - Workstream & path collision analysis across tickets and branches.
  - Algorithmic issue & backlog triage with git reconciliation and Jaccard duplicate clustering.
  - AST symbol, function, and import metric extraction.
- Tripartite `wellmanifest/nl-dsl-llm` standard adoption:
  - Layer 1: Polish & English deterministic natural language pattern matching.
  - Layer 2: Canonical DSL domain verbs (`code.dedup`, `conflict.check`, `issue.triage`, `code.inspect`, `repo.status`).
  - Layer 3: Adaptive LLM fallback compiler.
- Model Context Protocol (MCP) server over stdio with full JSON-RPC 2.0 interface.
- CLI interface supporting `--nl`, `--dsl`, subcommands, and `--self-test`.
- Conformance test suite with 14 unit tests covering all components.
