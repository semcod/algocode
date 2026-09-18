"""
Algorithmic Analysis Engine.
Implements deterministic code deduplication, structural clone detection,
workstream & path conflict analysis, and issue/backlog triage.
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from algocode.models import CodeClone, ConflictFinding, IssueTriageRecord


class CodeAnalysisEngine:
    """Core algorithmic analysis engine."""

    # ---------------------------------------------------------------------------
    # 1. Algorithmic Duplicate & Structural Clone Detection
    # ---------------------------------------------------------------------------

    @staticmethod
    def _normalize_line(line: str) -> str:
        """Strips whitespace and trailing comments."""
        line = line.strip()
        if line.startswith("#") or line.startswith("//"):
            return ""
        return re.sub(r"\s+", " ", line)

    @classmethod
    def _structural_normalize_python(cls, code_snippet: str) -> Optional[str]:
        """Normalizes Python AST, abstracting variable/function names to generic tokens."""
        try:
            tree = ast.parse(code_snippet)
        except SyntaxError:
            return None

        class ASTNormalizer(ast.NodeTransformer):
            def __init__(self):
                self.var_map: Dict[str, str] = {}
                self.counter = 0

            def _get_id(self, original: str) -> str:
                if original.startswith("__") and original.endswith("__"):
                    return original
                if original not in self.var_map:
                    self.counter += 1
                    self.var_map[original] = f"_v{self.counter}"
                return self.var_map[original]

            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
                self.generic_visit(node)
                node.name = "_func"
                return node

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
                self.generic_visit(node)
                node.name = "_func"
                return node

            def visit_Name(self, node: ast.Name) -> ast.AST:
                return ast.copy_location(
                    ast.Name(id=self._get_id(node.id), ctx=node.ctx),
                    node
                )

            def visit_arg(self, node: ast.arg) -> ast.AST:
                return ast.copy_location(
                    ast.arg(arg=self._get_id(node.arg), annotation=node.annotation),
                    node
                )

        normalizer = ASTNormalizer()
        normalized_tree = normalizer.visit(tree)
        try:
            return ast.unparse(normalized_tree)
        except Exception:
            return ast.dump(normalized_tree)

    def scan_duplicates(
        self,
        target_path: str,
        min_lines: int = 5,
        extensions: Optional[List[str]] = None,
        max_files: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Scans files in target_path for exact and structural block duplicates.
        Uses sliding window hashing for exact matches and AST normalizer for structural clones.
        """
        root = Path(target_path).resolve()
        if not root.exists():
            return []

        if extensions is None:
            extensions = [".py", ".sh", ".js", ".ts", ".json"]

        file_paths: List[Path] = []
        if root.is_file():
            file_paths = [root]
        else:
            for p in root.rglob("*"):
                if len(file_paths) >= max_files:
                    break
                if p.is_file() and p.suffix in extensions:
                    # Skip common ignore directories
                    parts = set(p.parts)
                    if any(part in parts for part in (".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build")):
                        continue
                    file_paths.append(p)

        # Map block hashes to occurrences: hash -> list of (file, start_line, end_line, raw_snippet)
        exact_blocks: Dict[str, List[Tuple[str, int, int, str]]] = {}
        structural_blocks: Dict[str, List[Tuple[str, int, int, str]]] = {}

        for file_path in file_paths:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            lines = content.splitlines()
            if len(lines) < min_lines:
                continue

            rel_file = str(file_path.relative_to(root) if root.is_dir() else file_path.name)

            for i in range(len(lines) - min_lines + 1):
                window = lines[i : i + min_lines]
                normalized_window = [self._normalize_line(l) for l in window]
                normalized_window = [l for l in normalized_window if l]
                if len(normalized_window) < 3:
                    continue

                raw_snippet = "\n".join(window)
                block_key = hashlib.sha256("\n".join(normalized_window).encode("utf-8")).hexdigest()
                exact_blocks.setdefault(block_key, []).append((rel_file, i + 1, i + min_lines, raw_snippet))

            # Function-level structural AST clone detection for Python
            if file_path.suffix == ".py":
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            end_line = getattr(node, "end_lineno", None) or (node.lineno + min_lines)
                            fn_lines = end_line - node.lineno + 1
                            if fn_lines >= min_lines:
                                fn_code = ast.unparse(node)
                                norm_fn = self._structural_normalize_python(fn_code)
                                if norm_fn:
                                    s_key = hashlib.sha256(norm_fn.encode("utf-8")).hexdigest()
                                    structural_blocks.setdefault(s_key, []).append((rel_file, node.lineno, end_line, fn_code))
                except Exception:
                    pass

        clones: List[CodeClone] = []
        seen_pairs: Set[Tuple[str, int, str, int]] = set()

        # Collect exact duplicates
        for key, occurrences in exact_blocks.items():
            if len(occurrences) > 1:
                base = occurrences[0]
                for other in occurrences[1:]:
                    pair_key = (base[0], base[1], other[0], other[1])
                    if pair_key not in seen_pairs and (base[0] != other[0] or abs(base[1] - other[1]) >= min_lines):
                        seen_pairs.add(pair_key)
                        clones.append(CodeClone(
                            file_a=base[0],
                            lines_a=(base[1], base[2]),
                            file_b=other[0],
                            lines_b=(other[1], other[2]),
                            clone_type="exact",
                            line_count=min_lines,
                            similarity=1.0,
                            snippet=base[3][:200]
                        ))

        # Collect structural clones that are not already exact duplicates
        for key, occurrences in structural_blocks.items():
            if len(occurrences) > 1:
                base = occurrences[0]
                for other in occurrences[1:]:
                    pair_key = (base[0], base[1], other[0], other[1])
                    if pair_key not in seen_pairs and (base[0] != other[0] or abs(base[1] - other[1]) >= min_lines):
                        seen_pairs.add(pair_key)
                        clones.append(CodeClone(
                            file_a=base[0],
                            lines_a=(base[1], base[2]),
                            file_b=other[0],
                            lines_b=(other[1], other[2]),
                            clone_type="structural",
                            line_count=min_lines,
                            similarity=0.9,
                            snippet=base[3][:200]
                        ))

        return [asdict(c) for c in clones[:100]]

    # ---------------------------------------------------------------------------
    # 2. Workstream & Path Conflict Analysis
    # ---------------------------------------------------------------------------

    def check_conflicts(
        self,
        repo_path: str = ".",
        head_ref: str = "HEAD",
        base_ref: str = "main",
    ) -> List[Dict[str, Any]]:
        """
        Algorithmic conflict detection across active tickets, workstreams, and dirty files.
        Checks for path overlap against declared intent.json in project/ticket-*.
        """
        root = Path(repo_path).resolve()
        findings: List[ConflictFinding] = []

        # 1. Read manifest coordination settings if present
        manifest_paths = [
            root / ".governance" / "manifest.json",
            root / "governance" / "manifest.hub.json",
        ]
        manifest_data: Optional[Dict[str, Any]] = None
        for mp in manifest_paths:
            if mp.is_file():
                try:
                    manifest_data = json.loads(mp.read_text(encoding="utf-8"))
                    break
                except Exception:
                    pass

        # 2. Read active tickets in project/ticket-*
        project_dir = root / "project"
        active_tickets: List[Dict[str, Any]] = []
        if project_dir.is_dir():
            for t_dir in sorted(project_dir.iterdir()):
                if t_dir.is_dir() and re.match(r"^ticket-[0-9]{3,}$", t_dir.name):
                    readme_path = t_dir / "README.md"
                    intent_path = t_dir / "intent.json"
                    status = "UNKNOWN"
                    if readme_path.is_file():
                        m = re.search(r"\*\*Status\*\*:\s*([A-Z_]+)", readme_path.read_text(encoding="utf-8", errors="replace"))
                        if m:
                            status = m.group(1)

                    if status in ("IN_PROGRESS", "ACTIVE", "EDIT", "VALIDATION"):
                        intent = {}
                        if intent_path.is_file():
                            try:
                                intent = json.loads(intent_path.read_text(encoding="utf-8"))
                            except Exception:
                                pass
                        active_tickets.append({
                            "ticket": t_dir.name,
                            "status": status,
                            "intent": intent,
                            "allowedPaths": intent.get("allowedPaths", []),
                            "workstream": intent.get("workstream", "default")
                        })

        # Check workstream concurrency limit
        if manifest_data and "coordination" in manifest_data:
            coord = manifest_data["coordination"]
            max_active = coord.get("maxActiveTicketsPerWorkstream", 1)
            by_ws: Dict[str, List[str]] = {}
            for t in active_tickets:
                ws = t["workstream"]
                by_ws.setdefault(ws, []).append(t["ticket"])
            for ws, t_list in by_ws.items():
                if len(t_list) > max_active:
                    findings.append(ConflictFinding(
                        severity="BLOCKING",
                        kind="workstream_limit",
                        resource=f"workstream:{ws}",
                        description=f"Workstream '{ws}' exceeds concurrency limit ({len(t_list)} > {max_active})",
                        colliding_entities=t_list
                    ))

        # Check allowedPaths overlap between active tickets
        for i in range(len(active_tickets)):
            for j in range(i + 1, len(active_tickets)):
                t1 = active_tickets[i]
                t2 = active_tickets[j]
                overlap = self._paths_overlap(t1["allowedPaths"], t2["allowedPaths"])
                if overlap:
                    findings.append(ConflictFinding(
                        severity="BLOCKING",
                        kind="path_overlap",
                        resource=", ".join(overlap),
                        description=f"Path collision between active tickets {t1['ticket']} and {t2['ticket']}",
                        colliding_entities=[t1["ticket"], t2["ticket"]]
                    ))

        return [asdict(f) for f in findings]

    @staticmethod
    def _paths_overlap(patterns_a: List[str], patterns_b: List[str]) -> List[str]:
        overlaps: List[str] = []
        for a in patterns_a:
            # Ignore ticket's own directory
            if re.match(r"^project/ticket-[0-9]{3,}/", a):
                continue
            for b in patterns_b:
                if re.match(r"^project/ticket-[0-9]{3,}/", b):
                    continue
                if a == b or fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
                    overlaps.append(f"{a} ∩ {b}")
        return overlaps

    # ---------------------------------------------------------------------------
    # 3. Algorithmic Issue & Ticket Triage
    # ---------------------------------------------------------------------------

    def triage_issues(
        self,
        repo_path: str = ".",
        issues: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Algorithmic triage of issues against git commit history and mutual similarity.
        Detects already merged tickets, duplicate issues, and consolidations.
        """
        root = Path(repo_path).resolve()
        findings: List[IssueTriageRecord] = []

        if issues is None:
            # Try fetching from GitHub CLI if available
            try:
                proc = subprocess.run(
                    ["gh", "issue", "list", "--json", "number,title,body,state,labels", "--limit", "50"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                issues = json.loads(proc.stdout)
            except Exception:
                issues = []

        # Read recent git log commit messages to check for reconciled issues
        recent_commits: List[str] = []
        try:
            proc = subprocess.run(
                ["git", "log", "-n", "100", "--pretty=format:%B---COMMIT---"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False
            )
            recent_commits = proc.stdout.split("---COMMIT---")
        except Exception:
            pass

        reconciled_numbers: Set[str] = set()
        for msg in recent_commits:
            # Search for closes #123, fixed #123, ticket-123
            for m in re.finditer(r"(?:closes|fixes|closed|fixed)\s+#([0-9]+)", msg, re.IGNORECASE):
                reconciled_numbers.add(m.group(1))
            for m in re.finditer(r"\bticket-([0-9]+)\b", msg, re.IGNORECASE):
                reconciled_numbers.add(m.group(1))

        # Tokenize issues for duplicate detection
        tokenized_issues: List[Tuple[Dict[str, Any], Set[str]]] = []
        for iss in issues:
            num = str(iss.get("number", iss.get("id", "")))
            title = iss.get("title", "")
            body = iss.get("body", "")
            tokens = set(re.findall(r"[a-zA-Z0-9_\-]{4,}", (title + " " + body).lower()))
            tokenized_issues.append((iss, tokens))

        for idx, (iss, tokens) in enumerate(tokenized_issues):
            num = str(iss.get("number", iss.get("id", "")))
            title = iss.get("title", "")
            state = iss.get("state", "OPEN")

            # Check if already reconciled by commit history
            if num in reconciled_numbers:
                findings.append(IssueTriageRecord(
                    number_or_id=num,
                    title=title,
                    status=state,
                    classification="ALREADY_RESOLVED",
                    confidence=0.95,
                    reason=f"Found explicit closure or commit referencing #{num} in recent git log",
                    suggested_action=f"gh issue close {num} --comment 'Reconciled in recent git commit.'"
                ))
                continue

            # Check for mutual similarity / duplicates with other open issues
            matched_duplicate = False
            for other_idx in range(idx + 1, len(tokenized_issues)):
                other_iss, other_tokens = tokenized_issues[other_idx]
                other_num = str(other_iss.get("number", other_iss.get("id", "")))

                intersection = len(tokens & other_tokens)
                union = len(tokens | other_tokens)
                jaccard = (intersection / union) if union > 0 else 0.0

                if jaccard > 0.45 or (intersection > 15 and jaccard > 0.35):
                    findings.append(IssueTriageRecord(
                        number_or_id=num,
                        title=title,
                        status=state,
                        classification="DUPLICATE",
                        confidence=round(jaccard, 2),
                        reason=f"High token overlap ({round(jaccard*100)}%) with issue #{other_num}",
                        related_items=[f"#{other_num}"],
                        suggested_action=f"Consolidate #{num} into #{other_num} or close as duplicate."
                    ))
                    matched_duplicate = True
                    break

            if not matched_duplicate:
                findings.append(IssueTriageRecord(
                    number_or_id=num,
                    title=title,
                    status=state,
                    classification="ACTIONABLE",
                    confidence=0.9,
                    reason="No duplicate or prior resolution found in git history",
                    suggested_action=f"Allocate ticket and implement according to acceptance criteria."
                ))

        return [asdict(f) for f in findings]

    # ---------------------------------------------------------------------------
    # 4. AST Symbol & Structure Inspector
    # ---------------------------------------------------------------------------

    def inspect_ast(self, file_path: str) -> Dict[str, Any]:
        """Parses a Python source file, returning classes, functions, metrics, and docstrings."""
        p = Path(file_path).resolve()
        if not p.is_file():
            return {"error": f"File not found: {file_path}"}

        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}"}

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                    "docstring": ast.get_docstring(node) or ""
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "args": [a.arg for a in node.args.args],
                    "docstring": ast.get_docstring(node) or ""
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}")

        return {
            "file": p.name,
            "classes": classes,
            "functions": functions,
            "imports": sorted(set(imports)),
            "summary": {
                "class_count": len(classes),
                "function_count": len(functions),
                "import_count": len(imports)
            }
        }
