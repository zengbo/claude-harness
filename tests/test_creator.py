import unittest
import os
import tempfile
import shutil

from harness.creator import generate_scaffold, LANGUAGE_PRESETS

try:
    from harness.creator import scan_project, score_project
except ImportError:
    scan_project = None
    score_project = None

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
EXISTING = os.path.join(FIXTURES, "existing_project")


class TestLanguagePresets(unittest.TestCase):
    def test_go_preset_exists(self):
        self.assertIn("go", LANGUAGE_PRESETS)

    def test_python_preset_exists(self):
        self.assertIn("python", LANGUAGE_PRESETS)

    def test_typescript_preset_exists(self):
        self.assertIn("typescript", LANGUAGE_PRESETS)

    def test_preset_has_required_keys(self):
        for lang, preset in LANGUAGE_PRESETS.items():
            self.assertIn("layers", preset, f"{lang} missing layers")
            self.assertIn("build_cmd", preset, f"{lang} missing build_cmd")
            self.assertIn("test_cmd", preset, f"{lang} missing test_cmd")
            self.assertIn("forbidden_patterns", preset)


class TestGenerateScaffold(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_generates_claude_md(self):
        generate_scaffold(self.tmpdir, "test-project", "go", "web-api")
        self.assertTrue(
            os.path.exists(os.path.join(self.tmpdir, "CLAUDE.md"))
        )

    def test_generates_architecture_md(self):
        generate_scaffold(self.tmpdir, "test-project", "go", "web-api")
        arch = os.path.join(self.tmpdir, "docs", "ARCHITECTURE.md")
        self.assertTrue(os.path.exists(arch))
        content = open(arch).read()
        self.assertIn("```layers", content)
        self.assertIn("```quality", content)

    def test_generates_development_md(self):
        generate_scaffold(self.tmpdir, "test-project", "go", "web-api")
        dev = os.path.join(self.tmpdir, "docs", "DEVELOPMENT.md")
        self.assertTrue(os.path.exists(dev))
        content = open(dev).read()
        self.assertIn("```build", content)
        self.assertIn("```test", content)

    def test_generates_harness_dir(self):
        generate_scaffold(self.tmpdir, "test-project", "go", "web-api")
        self.assertTrue(
            os.path.exists(os.path.join(self.tmpdir, "harness", "__init__.py"))
        )

    def test_generates_validate_sh(self):
        generate_scaffold(self.tmpdir, "test-project", "go", "web-api")
        sh = os.path.join(self.tmpdir, "scripts", "validate.sh")
        self.assertTrue(os.path.exists(sh))
        self.assertTrue(os.access(sh, os.X_OK))

    def test_generates_dotharness(self):
        generate_scaffold(self.tmpdir, "test-project", "go", "web-api")
        self.assertTrue(
            os.path.isdir(os.path.join(self.tmpdir, ".harness", "trace", "successes"))
        )
        self.assertTrue(
            os.path.isdir(os.path.join(self.tmpdir, ".harness", "memory", "episodic"))
        )

    def test_does_not_overwrite_existing(self):
        claude_md = os.path.join(self.tmpdir, "CLAUDE.md")
        with open(claude_md, "w") as f:
            f.write("# Existing content")
        generate_scaffold(self.tmpdir, "test-project", "go", "web-api")
        with open(claude_md) as f:
            self.assertEqual(f.read(), "# Existing content")

    def test_project_name_in_output(self):
        generate_scaffold(self.tmpdir, "my-api", "go", "web-api")
        with open(os.path.join(self.tmpdir, "CLAUDE.md")) as f:
            self.assertIn("my-api", f.read())

    def test_generates_agent_templates(self):
        generate_scaffold(self.tmpdir, "test-project", "go", "web-api")
        coder_path = os.path.join(
            self.tmpdir, ".claude", "agents", "harness-coder.md"
        )
        reviewer_path = os.path.join(
            self.tmpdir, ".claude", "agents", "harness-reviewer.md"
        )
        self.assertTrue(os.path.exists(coder_path))
        self.assertTrue(os.path.exists(reviewer_path))
        with open(coder_path) as f:
            self.assertIn("Harness Coder", f.read())
        with open(reviewer_path) as f:
            self.assertIn("Harness Reviewer", f.read())


@unittest.skipIf(scan_project is None, "scan_project not yet implemented")
class TestScanProject(unittest.TestCase):
    def setUp(self):
        self.scan = scan_project(EXISTING)

    def test_detects_language(self):
        self.assertEqual(self.scan["language"], "go")

    def test_counts_source_files(self):
        self.assertGreaterEqual(self.scan["source_file_count"], 5)

    def test_detects_build_system(self):
        self.assertIn("Makefile", self.scan["build_systems"])

    def test_detects_directories(self):
        self.assertIn("internal/", self.scan["directories"])
        self.assertIn("cmd/", self.scan["directories"])

    def test_infers_layers(self):
        layers = self.scan["inferred_layers"]
        self.assertIsInstance(layers, dict)
        self.assertGreater(len(layers), 0)

    def test_detects_existing_tests(self):
        # No test files in fixture
        self.assertEqual(self.scan["test_file_count"], 0)


@unittest.skipIf(score_project is None, "score_project not yet implemented")
class TestScoreProject(unittest.TestCase):
    def setUp(self):
        self.scan = scan_project(EXISTING)
        self.score = score_project(self.scan, EXISTING)

    def test_returns_total_score(self):
        self.assertIsInstance(self.score["total"], int)
        self.assertGreaterEqual(self.score["total"], 0)
        self.assertLessEqual(self.score["total"], 100)

    def test_has_dimension_scores(self):
        self.assertIn("documentation", self.score)
        self.assertIn("lint_rules", self.score)
        self.assertIn("test_coverage", self.score)
        self.assertIn("validation_pipeline", self.score)

    def test_low_score_for_no_docs(self):
        # Fixture has no CLAUDE.md or docs/
        self.assertLessEqual(self.score["documentation"], 10)

    def test_low_score_for_no_harness(self):
        self.assertLessEqual(self.score["validation_pipeline"], 5)


class TestSetupProjectV2(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_setup_copies_skills(self):
        from harness.creator import setup_project
        setup_project(self.tmpdir)
        skills_dir = os.path.join(self.tmpdir, ".claude", "skills")
        self.assertTrue(os.path.isdir(skills_dir))
        expected = ["harness-init", "harness-do", "harness-validate",
                    "harness-review", "harness-critic"]
        for skill in expected:
            skill_file = os.path.join(skills_dir, skill, "SKILL.md")
            self.assertTrue(os.path.exists(skill_file), f"Missing: {skill}/SKILL.md")

    def test_setup_creates_guard_yaml(self):
        from harness.creator import setup_project
        setup_project(self.tmpdir)
        path = os.path.join(self.tmpdir, ".harness", "guard.yaml")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn("R01_layer_violation", content)
        self.assertIn("protected_paths", content)

    def test_setup_creates_hooks_settings(self):
        from harness.creator import setup_project
        import json
        setup_project(self.tmpdir)
        path = os.path.join(self.tmpdir, ".claude", "settings.json")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertIn("hooks", data)
        matchers = [h["matcher"] for h in data["hooks"]["PreToolUse"]]
        self.assertIn("Bash", matchers)

    def test_init_also_copies_skills(self):
        from harness.creator import generate_scaffold
        generate_scaffold(self.tmpdir, "testproj", "python", "library")
        skills_dir = os.path.join(self.tmpdir, ".claude", "skills")
        self.assertTrue(os.path.isdir(skills_dir))
        self.assertTrue(os.path.exists(os.path.join(skills_dir, "harness-do", "SKILL.md")))


if __name__ == "__main__":
    unittest.main()
