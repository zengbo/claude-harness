import unittest
import os

from harness.verify_action import verify_action

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ARCH = os.path.join(FIXTURES, "sample_arch.md")


class TestVerifyAction(unittest.TestCase):
    def test_create_file_in_valid_layer(self):
        result = verify_action(
            "create file internal/types/user.go", ARCH
        )
        self.assertTrue(result["valid"])

    def test_create_file_naming_ok(self):
        result = verify_action(
            "create file internal/utils/string_helper.go", ARCH
        )
        self.assertTrue(result["valid"])

    def test_import_lower_layer_valid(self):
        result = verify_action(
            "add import internal/types in internal/services/user.go", ARCH
        )
        self.assertTrue(result["valid"])

    def test_import_higher_layer_invalid(self):
        result = verify_action(
            "add import internal/services in internal/types/user.go", ARCH
        )
        self.assertFalse(result["valid"])
        self.assertIn("Layer 0", result["message"])
        self.assertIn("Layer 3", result["message"])

    def test_import_mutual_top_layer_invalid(self):
        result = verify_action(
            "add import cmd in api/handlers/user.go", ARCH
        )
        self.assertFalse(result["valid"])

    def test_unknown_action_returns_unknown(self):
        result = verify_action("refactor everything", ARCH)
        self.assertTrue(result["valid"])  # unknown actions pass through
        self.assertIn("unknown", result["message"].lower())


if __name__ == "__main__":
    unittest.main()
