import unittest
import os
import tempfile
import shutil

from harness.lint_quality import check_quality


class TestCheckQuality(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create a quality config dict (same shape as parse_quality output)
        self.quality = {
            "max_file_lines": 10,
            "forbidden_patterns": ["fmt.Println", "console.log"],
            "naming_files": "snake_case",
            "naming_types": None,
        }

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write(self, rel_path: str, content: str):
        fpath = os.path.join(self.tmpdir, rel_path)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w") as f:
            f.write(content)

    def test_clean_file_no_violations(self):
        self._write("src/user.go", "package user\n\ntype User struct{}\n")
        violations = check_quality(self.tmpdir, self.quality)
        self.assertEqual(violations, [])

    def test_file_too_long(self):
        self._write("src/big.go", "\n".join(f"line {i}" for i in range(20)))
        violations = check_quality(self.tmpdir, self.quality)
        msgs = [v["message"] for v in violations]
        self.assertTrue(any("20 lines" in m and "big.go" in m for m in msgs))

    def test_forbidden_pattern_detected(self):
        self._write("src/debug.go", 'package main\nfmt.Println("debug")\n')
        violations = check_quality(self.tmpdir, self.quality)
        msgs = [v["message"] for v in violations]
        self.assertTrue(any("fmt.Println" in m for m in msgs))

    def test_naming_violation(self):
        self._write("src/MyFile.go", "package main\n")
        violations = check_quality(self.tmpdir, self.quality)
        msgs = [v["message"] for v in violations]
        self.assertTrue(any("MyFile.go" in m and "snake_case" in m for m in msgs))

    def test_ignores_hidden_dirs(self):
        self._write(".git/objects/abc.go", "\n".join(f"line {i}" for i in range(20)))
        violations = check_quality(self.tmpdir, self.quality)
        self.assertEqual(violations, [])

    def test_ignores_harness_dir(self):
        self._write(
            "harness/config.py",
            "\n".join(f"line {i}" for i in range(20)),
        )
        violations = check_quality(self.tmpdir, self.quality)
        self.assertEqual(violations, [])


class TestNamingConventions(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.quality = {
            "max_file_lines": 500,
            "forbidden_patterns": [],
            "naming_files": "snake_case",
            "naming_types": "PascalCase",
        }

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write(self, rel_path: str, content: str):
        fpath = os.path.join(self.tmpdir, rel_path)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w") as f:
            f.write(content)

    def test_go_pascal_type_ok(self):
        self._write("src/types.go", "type UserProfile struct {}\n")
        violations = check_quality(self.tmpdir, self.quality)
        naming_violations = [v for v in violations if v["rule"] == "naming_types"]
        self.assertEqual(naming_violations, [])

    def test_go_lowercase_type_violation(self):
        self._write("src/types.go", "type userProfile struct {}\n")
        violations = check_quality(self.tmpdir, self.quality)
        naming_violations = [v for v in violations if v["rule"] == "naming_types"]
        self.assertEqual(len(naming_violations), 1)
        self.assertIn("userProfile", naming_violations[0]["message"])

    def test_python_class_ok(self):
        self._write("src/models.py", "class UserProfile:\n    pass\n")
        violations = check_quality(self.tmpdir, self.quality)
        naming_violations = [v for v in violations if v["rule"] == "naming_types"]
        self.assertEqual(naming_violations, [])

    def test_python_class_snake_case_violation(self):
        self._write("src/models.py", "class user_profile:\n    pass\n")
        violations = check_quality(self.tmpdir, self.quality)
        naming_violations = [v for v in violations if v["rule"] == "naming_types"]
        self.assertEqual(len(naming_violations), 1)

    def test_ts_interface_ok(self):
        self._write("src/types.ts", "interface UserProfile {}\n")
        violations = check_quality(self.tmpdir, self.quality)
        naming_violations = [v for v in violations if v["rule"] == "naming_types"]
        self.assertEqual(naming_violations, [])

    def test_ts_interface_lowercase_violation(self):
        self._write("src/types.ts", "interface userProfile {}\n")
        violations = check_quality(self.tmpdir, self.quality)
        naming_violations = [v for v in violations if v["rule"] == "naming_types"]
        self.assertEqual(len(naming_violations), 1)

    def test_no_check_when_naming_types_none(self):
        self.quality["naming_types"] = None
        self._write("src/types.go", "type badName struct {}\n")
        violations = check_quality(self.tmpdir, self.quality)
        naming_violations = [v for v in violations if v["rule"] == "naming_types"]
        self.assertEqual(naming_violations, [])


if __name__ == "__main__":
    unittest.main()
