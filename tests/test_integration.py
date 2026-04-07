"""Integration test: scaffold a project, introduce violations, validate."""

import unittest
import os
import tempfile
import shutil
import subprocess


class TestFullWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Copy harness package into temp project
        harness_src = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "harness"
        )
        harness_dst = os.path.join(self.tmpdir, "harness")
        shutil.copytree(harness_src, harness_dst)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _run(self, cmd: str) -> tuple[int, str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = self.tmpdir
        proc = subprocess.run(
            cmd, shell=True, cwd=self.tmpdir,
            capture_output=True, text=True, env=env,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def _scaffold(self, language: str = "go"):
        """Generate scaffold without interactive input."""
        from harness.creator import generate_scaffold
        generate_scaffold(self.tmpdir, "test-project", language, "web-api")

    def _override_dev_md(self):
        """Replace build/test commands with simple echo so tests don't need real toolchain."""
        dev_path = os.path.join(self.tmpdir, "docs", "DEVELOPMENT.md")
        with open(dev_path, "w") as f:
            f.write('# Dev\n\n```build\necho "build ok"\n```\n\n```test\necho "tests ok"\n```\n')

    def test_scaffold_then_validate_passes(self):
        self._scaffold("go")
        self._override_dev_md()
        code, output = self._run(
            "python3 harness/validate.py ."
        )
        self.assertEqual(code, 0, f"Expected pass, got:\n{output}")

    def test_scaffold_then_add_violation(self):
        self._scaffold("go")
        self._override_dev_md()
        # Create a Layer 0 file that imports Layer 3
        types_dir = os.path.join(self.tmpdir, "internal", "types")
        os.makedirs(types_dir, exist_ok=True)
        with open(os.path.join(types_dir, "bad.go"), "w") as f:
            f.write('package types\n\nimport "internal/services"\n\nvar _ = services.X\n')

        code, output = self._run(
            "python3 harness/validate.py . --stage lint"
        )
        self.assertNotEqual(code, 0)
        self.assertIn("Layer 0", output)

    def test_verify_action_valid(self):
        self._scaffold("go")
        code, output = self._run(
            'python3 harness/verify_action.py '
            '"create file internal/types/user.go" '
            '--arch docs/ARCHITECTURE.md'
        )
        self.assertEqual(code, 0)
        self.assertIn("VALID", output)

    def test_verify_action_invalid(self):
        self._scaffold("go")
        code, output = self._run(
            'python3 harness/verify_action.py '
            '"add import internal/services in internal/types/user.go" '
            '--arch docs/ARCHITECTURE.md'
        )
        self.assertNotEqual(code, 0)
        self.assertIn("INVALID", output)


if __name__ == "__main__":
    unittest.main()
