import unittest
import os

from harness.lint_deps import parse_imports_go, parse_imports_python, parse_imports_ts
from harness.lint_deps import check_layer_violations

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
PROJECT = os.path.join(FIXTURES, "sample_project")


class TestGoImportParser(unittest.TestCase):
    def test_single_import(self):
        code = 'import "internal/types"'
        self.assertEqual(parse_imports_go(code), ["internal/types"])

    def test_grouped_imports(self):
        code = '''import (
    "fmt"
    "internal/types"
    "internal/config"
)'''
        result = parse_imports_go(code)
        self.assertIn("internal/types", result)
        self.assertIn("internal/config", result)

    def test_ignores_stdlib(self):
        code = '''import (
    "fmt"
    "os"
    "internal/types"
)'''
        # parse_imports_go returns ALL imports; filtering is caller's job
        result = parse_imports_go(code)
        self.assertIn("fmt", result)
        self.assertIn("internal/types", result)

    def test_named_import(self):
        code = 'import cfg "internal/config"'
        self.assertEqual(parse_imports_go(code), ["internal/config"])

    def test_dot_import(self):
        code = 'import . "internal/types"'
        self.assertEqual(parse_imports_go(code), ["internal/types"])

    def test_no_imports(self):
        code = "package main\n\nfunc main() {}"
        self.assertEqual(parse_imports_go(code), [])


class TestPythonImportParser(unittest.TestCase):
    def test_import_module(self):
        code = "import internal.types"
        self.assertEqual(parse_imports_python(code), ["internal.types"])

    def test_from_import(self):
        code = "from internal.config import Settings"
        self.assertEqual(parse_imports_python(code), ["internal.config"])

    def test_relative_import_ignored(self):
        code = "from . import utils"
        self.assertEqual(parse_imports_python(code), [])

    def test_multiple_imports(self):
        code = "import os\nimport internal.types\nfrom internal.services import UserService"
        result = parse_imports_python(code)
        self.assertIn("os", result)
        self.assertIn("internal.types", result)
        self.assertIn("internal.services", result)

    def test_no_imports(self):
        code = "x = 1\nprint(x)"
        self.assertEqual(parse_imports_python(code), [])


class TestTypeScriptImportParser(unittest.TestCase):
    def test_esm_import(self):
        code = "import { User } from '../types/user';"
        self.assertEqual(parse_imports_ts(code), ["../types/user"])

    def test_esm_default_import(self):
        code = "import Config from '../config';"
        self.assertEqual(parse_imports_ts(code), ["../config"])

    def test_require(self):
        code = "const utils = require('../utils/helper');"
        self.assertEqual(parse_imports_ts(code), ["../utils/helper"])

    def test_side_effect_import(self):
        code = "import '../styles/global.css';"
        self.assertEqual(parse_imports_ts(code), ["../styles/global.css"])

    def test_multiple(self):
        code = """import { User } from '../types/user';
import { Config } from '../config';
const helper = require('../utils/helper');"""
        result = parse_imports_ts(code)
        self.assertEqual(len(result), 3)

    def test_no_imports(self):
        code = "const x = 1;\nconsole.log(x);"
        self.assertEqual(parse_imports_ts(code), [])


class TestCheckLayerViolations(unittest.TestCase):
    def setUp(self):
        arch_path = os.path.join(PROJECT, "docs", "ARCHITECTURE.md")
        self.violations = check_layer_violations(PROJECT, arch_path)

    def test_finds_violations(self):
        self.assertGreater(len(self.violations), 0)

    def test_detects_layer3_importing_layer4(self):
        msgs = [v["message"] for v in self.violations]
        found = any("user_service.go" in m and "cmd" in m for m in msgs)
        self.assertTrue(found, f"Expected violation in user_service.go, got: {msgs}")

    def test_detects_layer4_mutual_import(self):
        msgs = [v["message"] for v in self.violations]
        found = any("user_handler.go" in m and "cmd" in m for m in msgs)
        self.assertTrue(found, f"Expected mutual import violation, got: {msgs}")

    def test_no_false_positives_on_clean_files(self):
        violating_files = {v["file"] for v in self.violations}
        self.assertNotIn(
            os.path.join(PROJECT, "internal", "types", "user.go"),
            violating_files,
        )
        self.assertNotIn(
            os.path.join(PROJECT, "internal", "utils", "helper.go"),
            violating_files,
        )

    def test_violation_has_fix_suggestion(self):
        for v in self.violations:
            self.assertIn("fix", v)
            self.assertTrue(len(v["fix"]) > 0)

    def test_violation_has_layer_info(self):
        for v in self.violations:
            self.assertIn("source_layer", v)
            self.assertIn("target_layer", v)


if __name__ == "__main__":
    unittest.main()
