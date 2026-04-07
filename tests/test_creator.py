import unittest
import os
import tempfile
import shutil

from harness.creator import generate_scaffold, LANGUAGE_PRESETS


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


if __name__ == "__main__":
    unittest.main()
