import unittest
import os
import tempfile
import shutil

from harness.validate import run_pipeline, PipelineResult


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestRunPipeline(unittest.TestCase):
    def setUp(self):
        # Create a minimal project with passing build/test
        self.tmpdir = tempfile.mkdtemp()
        docs = os.path.join(self.tmpdir, "docs")
        os.makedirs(docs)

        # ARCHITECTURE.md with layers and quality
        with open(os.path.join(docs, "ARCHITECTURE.md"), "w") as f:
            f.write("""# Arch

## Layers

```layers
Layer 0: lib/types/  -> Type definitions
Layer 1: lib/utils/  -> Utilities
```

## Quality

```quality
max_file_lines: 100
forbidden_patterns: FIXME
```
""")

        # DEVELOPMENT.md with commands that always pass
        with open(os.path.join(docs, "DEVELOPMENT.md"), "w") as f:
            f.write("""# Dev

## Build

```build
echo "build ok"
```

## Test

```test
echo "tests ok"
```
""")

        # A clean source file
        os.makedirs(os.path.join(self.tmpdir, "lib", "types"))
        with open(
            os.path.join(self.tmpdir, "lib", "types", "user.py"), "w"
        ) as f:
            f.write("class User:\n    pass\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_all_pass(self):
        result = run_pipeline(self.tmpdir)
        self.assertTrue(result.success)
        self.assertEqual(result.failed_stage, None)

    def test_build_failure_stops_pipeline(self):
        dev = os.path.join(self.tmpdir, "docs", "DEVELOPMENT.md")
        with open(dev, "w") as f:
            f.write('# Dev\n\n```build\nexit 1\n```\n\n```test\necho ok\n```\n')
        result = run_pipeline(self.tmpdir)
        self.assertFalse(result.success)
        self.assertEqual(result.failed_stage, "build")

    def test_lint_failure_stops_before_test(self):
        # Add a file with forbidden pattern
        with open(
            os.path.join(self.tmpdir, "lib", "types", "bad.py"), "w"
        ) as f:
            f.write("# FIXME: this is bad\n")
        result = run_pipeline(self.tmpdir)
        self.assertFalse(result.success)
        self.assertEqual(result.failed_stage, "lint")

    def test_stage_limit(self):
        result = run_pipeline(self.tmpdir, stop_after="build")
        self.assertTrue(result.success)
        # Only build ran, not lint/test/verify
        self.assertIn("build", result.stages_run)
        self.assertNotIn("test", result.stages_run)

    def test_verify_skipped_when_no_scripts(self):
        result = run_pipeline(self.tmpdir)
        self.assertTrue(result.success)
        self.assertIn("verify", result.stages_skipped)


if __name__ == "__main__":
    unittest.main()
