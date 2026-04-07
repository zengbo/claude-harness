import unittest
import os

from harness.config import parse_layers, parse_quality, parse_commands, parse_review_perspectives

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestParseLayers(unittest.TestCase):
    def setUp(self):
        self.layers = parse_layers(os.path.join(FIXTURES, "sample_arch.md"))

    def test_returns_dict_keyed_by_layer_number(self):
        self.assertEqual(set(self.layers.keys()), {0, 1, 2, 3, 4})

    def test_layer0_paths(self):
        self.assertEqual(
            self.layers[0]["paths"], ["internal/types/", "pkg/models/"]
        )

    def test_layer0_label(self):
        self.assertEqual(
            self.layers[0]["label"], "Pure type definitions, no internal imports"
        )

    def test_layer4_paths(self):
        self.assertEqual(
            self.layers[4]["paths"], ["cmd/", "api/handlers/"]
        )

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            parse_layers("/nonexistent/ARCHITECTURE.md")

    def test_no_layers_block_raises(self):
        with self.assertRaises(ValueError):
            parse_layers(os.path.join(FIXTURES, "sample_dev.md"))


class TestParseQuality(unittest.TestCase):
    def setUp(self):
        self.quality = parse_quality(os.path.join(FIXTURES, "sample_arch.md"))

    def test_max_file_lines(self):
        self.assertEqual(self.quality["max_file_lines"], 500)

    def test_forbidden_patterns(self):
        self.assertEqual(
            self.quality["forbidden_patterns"],
            ["fmt.Println", "console.log", "print("],
        )

    def test_naming_files(self):
        self.assertEqual(self.quality["naming_files"], "snake_case")

    def test_missing_quality_block_returns_defaults(self):
        quality = parse_quality(os.path.join(FIXTURES, "sample_dev.md"))
        self.assertEqual(quality["max_file_lines"], 500)
        self.assertEqual(quality["forbidden_patterns"], [])


class TestParseCommands(unittest.TestCase):
    def setUp(self):
        self.cmds = parse_commands(os.path.join(FIXTURES, "sample_dev.md"))

    def test_build_command(self):
        self.assertEqual(self.cmds["build"], "go build ./...")

    def test_test_command(self):
        self.assertEqual(self.cmds["test"], "go test ./...")

    def test_lint_command(self):
        self.assertEqual(self.cmds["lint"], "golangci-lint run")

    def test_missing_block_returns_none(self):
        cmds = parse_commands(os.path.join(FIXTURES, "sample_arch.md"))
        self.assertIsNone(cmds["build"])


class TestParseReviewPerspectives(unittest.TestCase):
    def test_parses_perspectives(self):
        arch = os.path.join(FIXTURES, "sample_arch_with_perspectives.md")
        perspectives = parse_review_perspectives(arch)
        self.assertEqual(len(perspectives), 3)
        self.assertIn("security", perspectives)
        self.assertIn("performance", perspectives)
        self.assertIn("Authentication", perspectives["security"])

    def test_missing_block_returns_defaults(self):
        perspectives = parse_review_perspectives(os.path.join(FIXTURES, "sample_arch.md"))
        self.assertEqual(len(perspectives), 4)
        self.assertIn("security", perspectives)
        self.assertIn("accessibility", perspectives)


class TestParseQualityLayerRules(unittest.TestCase):
    def test_per_layer_forbidden_patterns(self):
        arch = os.path.join(FIXTURES, "sample_arch_with_perspectives.md")
        quality = parse_quality(arch)
        self.assertIn("layer_rules", quality)
        self.assertIn(0, quality["layer_rules"])
        self.assertIn("import logging", quality["layer_rules"][0]["forbidden_patterns"])
        self.assertIn(3, quality["layer_rules"])
        self.assertIn("sys.exit", quality["layer_rules"][3]["forbidden_patterns"])

    def test_no_layer_rules_returns_empty(self):
        quality = parse_quality(os.path.join(FIXTURES, "sample_arch.md"))
        self.assertEqual(quality.get("layer_rules", {}), {})


if __name__ == "__main__":
    unittest.main()
