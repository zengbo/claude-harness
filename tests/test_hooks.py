import json
import unittest
from harness.hooks import parse_tool_input, generate_hooks_config


class TestParseToolInput(unittest.TestCase):
    def test_parse_bash_input(self):
        tool_json = json.dumps({"command": "git push --force origin main"})
        ctx = parse_tool_input("bash", tool_json, "/tmp/proj")
        self.assertEqual(ctx.action_type, "bash")
        self.assertEqual(ctx.command, "git push --force origin main")

    def test_parse_write_input(self):
        tool_json = json.dumps({"file_path": "/tmp/proj/src/main.py", "content": "x=1"})
        ctx = parse_tool_input("write", tool_json, "/tmp/proj")
        self.assertEqual(ctx.action_type, "write")
        self.assertEqual(ctx.file_path, "src/main.py")
        self.assertEqual(ctx.content, "x=1")

    def test_parse_edit_input(self):
        tool_json = json.dumps({"file_path": "/tmp/proj/.env", "old_string": "OLD", "new_string": "NEW"})
        ctx = parse_tool_input("edit", tool_json, "/tmp/proj")
        self.assertEqual(ctx.action_type, "edit")
        self.assertEqual(ctx.file_path, ".env")
        self.assertEqual(ctx.content, "NEW")

    def test_parse_invalid_json(self):
        ctx = parse_tool_input("bash", "not json", "/tmp")
        self.assertIsNone(ctx)


class TestGenerateHooksConfig(unittest.TestCase):
    def test_generates_valid_structure(self):
        config = generate_hooks_config()
        self.assertIn("hooks", config)
        self.assertIn("PreToolUse", config["hooks"])
        matchers = [h["matcher"] for h in config["hooks"]["PreToolUse"]]
        self.assertIn("Bash", matchers)
        self.assertIn("Write", matchers)
        self.assertIn("Edit", matchers)

    def test_commands_reference_hooks_py(self):
        config = generate_hooks_config()
        for hook in config["hooks"]["PreToolUse"]:
            self.assertIn("harness/hooks.py", hook["command"])
