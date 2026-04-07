import unittest
import os
import tempfile
import shutil

from harness.review import generate_review_prompt

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestGenerateReviewPrompt(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        docs = os.path.join(self.tmpdir, "docs")
        os.makedirs(docs)
        with open(os.path.join(docs, "ARCHITECTURE.md"), "w") as f:
            f.write("""# Arch

```layers
Layer 0: src/types/  -> Pure type definitions
Layer 3: src/services/  -> Business logic
```

```quality
max_file_lines: 500
```
""")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_returns_string(self):
        prompt = generate_review_prompt(
            diff="+ new line",
            task="Add user endpoint",
            arch_md_path=os.path.join(self.tmpdir, "docs", "ARCHITECTURE.md"),
        )
        self.assertIsInstance(prompt, str)

    def test_contains_diff(self):
        prompt = generate_review_prompt(
            diff="+ def get_user(id):",
            task="Add user endpoint",
            arch_md_path=os.path.join(self.tmpdir, "docs", "ARCHITECTURE.md"),
        )
        self.assertIn("get_user", prompt)

    def test_contains_task_description(self):
        prompt = generate_review_prompt(
            diff="+ code",
            task="Refactor auth middleware",
            arch_md_path=os.path.join(self.tmpdir, "docs", "ARCHITECTURE.md"),
        )
        self.assertIn("Refactor auth middleware", prompt)

    def test_contains_architecture_rules(self):
        prompt = generate_review_prompt(
            diff="+ code",
            task="test task",
            arch_md_path=os.path.join(self.tmpdir, "docs", "ARCHITECTURE.md"),
        )
        self.assertIn("Layer 0", prompt)
        self.assertIn("Layer 3", prompt)

    def test_contains_review_checklist(self):
        prompt = generate_review_prompt(
            diff="+ code",
            task="test task",
            arch_md_path=os.path.join(self.tmpdir, "docs", "ARCHITECTURE.md"),
        )
        self.assertIn("Logic correctness", prompt)
        self.assertIn("Security", prompt)

    def test_contains_output_instruction(self):
        prompt = generate_review_prompt(
            diff="+ code",
            task="test task",
            arch_md_path=os.path.join(self.tmpdir, "docs", "ARCHITECTURE.md"),
        )
        self.assertIn("PASS", prompt)
        self.assertIn("NEEDS_CHANGE", prompt)

    def test_missing_arch_graceful(self):
        prompt = generate_review_prompt(
            diff="+ code",
            task="test task",
            arch_md_path="/nonexistent/ARCHITECTURE.md",
        )
        self.assertIsInstance(prompt, str)
        self.assertIn("+ code", prompt)


class TestReviewPerspectives(unittest.TestCase):
    def setUp(self):
        self.arch = os.path.join(FIXTURES, "sample_arch_with_perspectives.md")

    def test_single_perspective(self):
        from harness.review import generate_review_prompt
        prompt = generate_review_prompt("diff here", "fix auth", self.arch, perspective="security")
        self.assertIsInstance(prompt, str)
        self.assertIn("security", prompt.lower())
        self.assertIn("diff here", prompt)

    def test_all_perspectives(self):
        from harness.review import generate_review_prompt
        result = generate_review_prompt("diff here", "refactor", self.arch, perspective="all")
        self.assertIsInstance(result, dict)
        self.assertIn("security", result)
        self.assertIn("performance", result)
        self.assertIn("diff here", result["security"])

    def test_no_perspective_backward_compatible(self):
        from harness.review import generate_review_prompt
        prompt = generate_review_prompt("diff here", "fix bug", self.arch)
        self.assertIsInstance(prompt, str)
        self.assertIn("diff here", prompt)


if __name__ == "__main__":
    unittest.main()
