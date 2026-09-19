"""
Tests for algocode.engine: deduplication, conflicts, triage, and AST inspection.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from algocode.engine import CodeAnalysisEngine


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="algocode-engine-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.engine = CodeAnalysisEngine()

    def test_exact_duplicate_detection(self):
        """Verify exact block duplicate detection via SHA-256 sliding window."""
        file1 = self.root / "file1.py"
        file2 = self.root / "file2.py"

        code_block = """
def calculate_metrics(items):
    total = 0
    for x in items:
        total += x * 2
    return total
"""
        file1.write_text(code_block, encoding="utf-8")
        file2.write_text(code_block, encoding="utf-8")

        clones = self.engine.scan_duplicates(target_path=str(self.root), min_lines=5)
        self.assertGreaterEqual(len(clones), 1)
        self.assertEqual(clones[0]["clone_type"], "exact")
        self.assertEqual(clones[0]["similarity"], 1.0)

    def test_structural_clone_detection(self):
        """Verify structural AST clone detection (different variable names, same AST)."""
        file1 = self.root / "struct1.py"
        file2 = self.root / "struct2.py"

        # Same AST shape, completely different variable names
        code1 = """
def process_alpha(values):
    accum = 0
    for val in values:
        accum += val * 3
    return accum
"""
        code2 = """
def process_beta(elements):
    result = 0
    for elem in elements:
        result += elem * 3
    return result
"""
        file1.write_text(code1, encoding="utf-8")
        file2.write_text(code2, encoding="utf-8")

        clones = self.engine.scan_duplicates(target_path=str(self.root), min_lines=5)
        self.assertGreaterEqual(len(clones), 1)
        # Should identify clone
        clone_types = {c["clone_type"] for c in clones}
        self.assertTrue("structural" in clone_types or "exact" in clone_types)

    def test_conflict_detection_workstream_and_paths(self):
        """Verify path collision detection between active tickets."""
        project_dir = self.root / "project"
        project_dir.mkdir()

        t1 = project_dir / "ticket-100"
        t1.mkdir()
        (t1 / "README.md").write_text("- **Status**: IN_PROGRESS\n", encoding="utf-8")
        (t1 / "intent.json").write_text('{"workstream": "ws1", "allowedPaths": ["src/core.py"]}', encoding="utf-8")

        t2 = project_dir / "ticket-101"
        t2.mkdir()
        (t2 / "README.md").write_text("- **Status**: IN_PROGRESS\n", encoding="utf-8")
        (t2 / "intent.json").write_text('{"workstream": "ws1", "allowedPaths": ["src/core.py"]}', encoding="utf-8")

        conflicts = self.engine.check_conflicts(repo_path=str(self.root))
        self.assertGreaterEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["severity"], "BLOCKING")
        self.assertEqual(conflicts[0]["kind"], "path_overlap")

    def test_issue_triage_algorithmic(self):
        """Verify algorithmic triage classifies duplicate and actionable issues."""
        mock_issues = [
            {"number": 1, "title": "Add preflight cache to governance check", "body": "Need cache to speed up checks", "state": "OPEN"},
            {"number": 2, "title": "Add preflight cache to governance check", "body": "Need cache to speed up checks", "state": "OPEN"},
            {"number": 3, "title": "Implement docker image validator", "body": "Validate docker container references", "state": "OPEN"},
        ]
        triage = self.engine.triage_issues(repo_path=str(self.root), issues=mock_issues)
        self.assertEqual(len(triage), 3)

        classifications = {item["number_or_id"]: item["classification"] for item in triage}
        self.assertEqual(classifications["1"], "DUPLICATE")
        self.assertEqual(classifications["3"], "ACTIONABLE")

    def test_ast_inspector(self):
        """Verify AST parsing and metric extraction."""
        test_file = self.root / "sample.py"
        test_file.write_text("""
import os
from pathlib import Path

class Greeter:
    def greet(self, name: str) -> str:
        return f"Hello, {name}"

async def fetch_data():
    pass
""", encoding="utf-8")

        res = self.engine.inspect_ast(str(test_file))
        self.assertEqual(res["summary"]["class_count"], 1)
        self.assertEqual(res["summary"]["function_count"], 2)
        self.assertIn("os", res["imports"])
        self.assertIn("pathlib.Path", res["imports"])

    def test_polyglot_structural_clone_typescript(self):
        """Verify structural clone detection across TypeScript files."""
        f1 = self.root / "orders.ts"
        f2 = self.root / "invoices.ts"

        code1 = """
function calculateOrderTotal(items: number[]): number {
    let sum = 0;
    for (const item of items) {
        sum += item * 2;
    }
    return sum;
}
"""
        code2 = """
function aggregateInvoicePrices(entries: number[]): number {
    let result = 0;
    for (const entry of entries) {
        result += entry * 2;
    }
    return result;
}
"""
        f1.write_text(code1, encoding="utf-8")
        f2.write_text(code2, encoding="utf-8")

        clones = self.engine.scan_duplicates(target_path=str(self.root), min_lines=5)
        self.assertGreaterEqual(len(clones), 1)
        clone_types = {c["clone_type"] for c in clones}
        self.assertIn("structural", clone_types)

    def test_polyglot_structural_clone_golang(self):
        """Verify structural clone detection across Go files."""
        f1 = self.root / "math1.go"
        f2 = self.root / "math2.go"

        code1 = """
func computeTotal(vals []int) int {
    total := 0
    for _, val := range vals {
        total += val * 2
    }
    return total
}
"""
        code2 = """
func aggregateNumbers(entries []int) int {
    res := 0
    for _, entry := range entries {
        res += entry * 2
    }
    return res
}
"""
        f1.write_text(code1, encoding="utf-8")
        f2.write_text(code2, encoding="utf-8")

        clones = self.engine.scan_duplicates(target_path=str(self.root), min_lines=5)
        self.assertGreaterEqual(len(clones), 1)
        clone_types = {c["clone_type"] for c in clones}
        self.assertIn("structural", clone_types)

    def test_polyglot_structural_clone_rust(self):
        """Verify structural clone detection across Rust files."""
        f1 = self.root / "calc1.rs"
        f2 = self.root / "calc2.rs"

        code1 = """
fn calculate_sum(data: &[i32]) -> i32 {
    let mut total = 0;
    for x in data {
        total += x * 2;
    }
    total
}
"""
        code2 = """
fn aggregate_numbers(records: &[i32]) -> i32 {
    let mut accumulator = 0;
    for r in records {
        accumulator += r * 2;
    }
    accumulator
}
"""
        f1.write_text(code1, encoding="utf-8")
        f2.write_text(code2, encoding="utf-8")

        clones = self.engine.scan_duplicates(target_path=str(self.root), min_lines=5)
        self.assertGreaterEqual(len(clones), 1)
        clone_types = {c["clone_type"] for c in clones}
        self.assertIn("structural", clone_types)


if __name__ == "__main__":
    unittest.main()
