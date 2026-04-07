import unittest
import os
import json
import tempfile
import shutil

from harness.critic import analyze_failures, find_compilable_patterns, suggest_lint_rules
from harness.trace import record_failure, record_success
from harness.memory import save_memory


class TestAnalyzeFailures(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_empty_returns_no_patterns(self):
        patterns = analyze_failures(self.harness_dir)
        self.assertEqual(patterns, [])

    def test_single_failure_no_pattern(self):
        record_failure(self.harness_dir, "task1", "step1",
                       error="Layer 0 imports Layer 3",
                       root_cause="wrong layer")
        patterns = analyze_failures(self.harness_dir)
        self.assertEqual(patterns, [])

    def test_repeated_error_detected(self):
        for i in range(3):
            record_failure(
                self.harness_dir,
                f"task {i}",
                "create type -> add import -> lint fail",
                error="Layer 0 imports Layer 3",
                root_cause="types/ file importing services/",
            )
        patterns = analyze_failures(self.harness_dir)
        self.assertGreater(len(patterns), 0)
        self.assertGreaterEqual(patterns[0]["count"], 2)

    def test_pattern_has_suggestion(self):
        for i in range(3):
            record_failure(
                self.harness_dir, f"task {i}", "steps",
                error="Layer 0 imports Layer 3",
                root_cause="same root cause",
            )
        patterns = analyze_failures(self.harness_dir)
        self.assertIn("suggestion", patterns[0])

    def test_different_errors_separate_patterns(self):
        record_failure(self.harness_dir, "t1", "s1",
                       error="Layer 0 imports Layer 3")
        record_failure(self.harness_dir, "t2", "s2",
                       error="Layer 0 imports Layer 3")
        record_failure(self.harness_dir, "t3", "s3",
                       error="file too long 600 lines")
        record_failure(self.harness_dir, "t4", "s4",
                       error="file too long 800 lines")
        patterns = analyze_failures(self.harness_dir)
        # Should find at least the layer import pattern (2 occurrences)
        self.assertGreaterEqual(len(patterns), 1)


class TestFindCompilablePatterns(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_procedural_returns_empty(self):
        result = find_compilable_patterns(self.harness_dir)
        self.assertEqual(result, [])

    def test_low_success_rate_not_compilable(self):
        save_memory(self.harness_dir, "procedural",
                    "Add endpoint", steps="s1 -> s2",
                    success_rate="1/3")
        result = find_compilable_patterns(self.harness_dir)
        self.assertEqual(result, [])

    def test_high_success_rate_compilable(self):
        save_memory(self.harness_dir, "procedural",
                    "Add Go API endpoint",
                    steps="create type -> write service -> add handler -> register route -> write test",
                    success_rate="5/5",
                    language="go", project_type="web-api")
        result = find_compilable_patterns(self.harness_dir)
        self.assertEqual(len(result), 1)
        self.assertIn("Add Go API endpoint", result[0]["title"])

    def test_compilable_has_suggested_script_name(self):
        save_memory(self.harness_dir, "procedural",
                    "Add Go API endpoint", steps="s1 -> s2",
                    success_rate="4/4")
        result = find_compilable_patterns(self.harness_dir)
        self.assertIn("script_name", result[0])


class TestSuggestLintRules(unittest.TestCase):
    def test_layer_import_failure_suggests_forbidden_pattern(self):
        patterns = [{
            "error_pattern": "layer # importing config module",
            "count": 3,
            "examples": [
                {"task": "add user type", "error": "Layer 0 importing config module"},
                {"task": "add model", "error": "Layer 0 importing config module"},
                {"task": "update types", "error": "Layer 0 importing config module"},
            ],
            "root_cause": "types/ files importing config package",
            "suggestion": "",
        }]
        suggestions = suggest_lint_rules(patterns)
        self.assertTrue(len(suggestions) > 0)
        self.assertEqual(suggestions[0]["type"], "forbidden_pattern")
        self.assertIn("layer:0", suggestions[0]["target"])

    def test_file_size_failure_suggests_max_lines(self):
        patterns = [{
            "error_pattern": "file too long: # lines (max #)",
            "count": 4,
            "examples": [{"task": "x", "error": "file too long: 600 lines (max 500)"}],
            "root_cause": None,
            "suggestion": "",
        }]
        suggestions = suggest_lint_rules(patterns)
        self.assertTrue(len(suggestions) > 0)
        self.assertEqual(suggestions[0]["type"], "max_file_lines")

    def test_non_lint_pattern_returns_empty(self):
        patterns = [{
            "error_pattern": "timeout after # seconds",
            "count": 2,
            "examples": [{"task": "x", "error": "timeout after 30 seconds"}],
            "root_cause": None,
            "suggestion": "",
        }]
        suggestions = suggest_lint_rules(patterns)
        self.assertEqual(len(suggestions), 0)

    def test_naming_failure_suggests_naming_rule(self):
        patterns = [{
            "error_pattern": "naming case violation",
            "count": 3,
            "examples": [{"task": "x", "error": "naming case violation in file"}],
            "root_cause": None,
            "suggestion": "",
        }]
        suggestions = suggest_lint_rules(patterns)
        self.assertTrue(len(suggestions) > 0)
        self.assertEqual(suggestions[0]["type"], "naming")

    def test_empty_patterns_returns_empty(self):
        suggestions = suggest_lint_rules([])
        self.assertEqual(suggestions, [])


if __name__ == "__main__":
    unittest.main()
