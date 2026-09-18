"""
Tests for algocode NL-DSL-LLM tripartite bridge adopting wellmanifest/nl-dsl-llm standard.
"""

from __future__ import annotations

import json
import unittest

from algocode.models import DSLCommand
from algocode.nl_dsl_llm import InterfaceAdapters, NLDSLLLMBridge, NLPatternParser


class NLDSLLLMTests(unittest.TestCase):
    def setUp(self):
        self.bridge = NLDSLLLMBridge()

    def test_layer_1_polish_pattern_matching(self):
        """Verify Layer 1 Polish natural language queries map to canonical DSL verbs."""
        # Duplikaty
        cmd1 = NLPatternParser.parse("znajdź duplikaty w src/")
        self.assertIsNotNone(cmd1)
        self.assertEqual(cmd1.entity, "code")
        self.assertEqual(cmd1.operation, "dedup")
        self.assertEqual(cmd1.arguments.get("path"), "src/")

        # Konflikty
        cmd2 = NLPatternParser.parse("sprawdź konflikty")
        self.assertIsNotNone(cmd2)
        self.assertEqual(cmd2.entity, "conflict")
        self.assertEqual(cmd2.operation, "check")

        # Triage
        cmd3 = NLPatternParser.parse("triage zgłoszeń w repo")
        self.assertIsNotNone(cmd3)
        self.assertEqual(cmd3.entity, "issue")
        self.assertEqual(cmd3.operation, "triage")

    def test_layer_1_english_pattern_matching(self):
        """Verify Layer 1 English natural language queries map to canonical DSL verbs."""
        cmd1 = NLPatternParser.parse("detect duplicates in .")
        self.assertIsNotNone(cmd1)
        self.assertEqual(cmd1.entity, "code")
        self.assertEqual(cmd1.operation, "dedup")

        cmd2 = NLPatternParser.parse("check conflicts")
        self.assertIsNotNone(cmd2)
        self.assertEqual(cmd2.entity, "conflict")
        self.assertEqual(cmd2.operation, "check")

        cmd3 = NLPatternParser.parse("triage issues")
        self.assertIsNotNone(cmd3)
        self.assertEqual(cmd3.entity, "issue")
        self.assertEqual(cmd3.operation, "triage")

    def test_layer_2_direct_dsl_execution(self):
        """Verify direct DSL execution."""
        res = self.bridge.handle_request("conflict.check path=.")
        self.assertTrue(res.success)
        self.assertEqual(res.meta["sourceLayer"], "direct_dsl")

    def test_layer_3_fallback(self):
        """Verify Layer 3 adaptive fallback when exact regex fails."""
        res = self.bridge.handle_request("proszę o analizę potencjalnych duplikatów kodu")
        self.assertTrue(res.success)
        self.assertEqual(res.meta["sourceLayer"], "llm_fallback")

    def test_interface_parity_cli_formatting(self):
        """Verify CLI formatting in markdown and json."""
        res = self.bridge.handle_request("repo.status path=.")
        self.assertTrue(res.success)

        md = InterfaceAdapters.cli_format(res, output_format="markdown")
        self.assertIn("### Algocode Result", md)
        self.assertIn("```json", md)

        js = InterfaceAdapters.cli_format(res, output_format="json")
        data = json.loads(js)
        self.assertTrue(data["success"])


if __name__ == "__main__":
    unittest.main()
