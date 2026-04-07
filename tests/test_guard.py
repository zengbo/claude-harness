import unittest
import os

from harness.guard import ActionContext, Verdict, GuardConfig, load_guard_config

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestGuardDataclasses(unittest.TestCase):
    def test_action_context_bash(self):
        ctx = ActionContext(
            action_type="bash",
            command="git push --force",
            file_path=None,
            content=None,
            project_root="/tmp/proj",
        )
        self.assertEqual(ctx.action_type, "bash")
        self.assertEqual(ctx.command, "git push --force")

    def test_action_context_write(self):
        ctx = ActionContext(
            action_type="write",
            command=None,
            file_path="src/main.py",
            content="print('hello')",
            project_root="/tmp/proj",
        )
        self.assertEqual(ctx.file_path, "src/main.py")

    def test_verdict_deny(self):
        v = Verdict(action="deny", rule_id="R03_force_push", message="blocked")
        self.assertEqual(v.action, "deny")

    def test_guard_config_from_yaml(self):
        cfg = load_guard_config(os.path.join(FIXTURES, "sample_guard.yaml"))
        self.assertTrue(cfg.rules["R03_force_push"])
        self.assertIn(".env*", cfg.protected_paths)
        self.assertEqual(len(cfg.secret_patterns), 3)

    def test_guard_config_missing_file_uses_defaults(self):
        cfg = load_guard_config("/nonexistent/guard.yaml")
        self.assertTrue(cfg.rules["R01_layer_violation"])
        self.assertTrue(len(cfg.rules) == 8)

    def test_guard_config_partial_rules(self):
        cfg = load_guard_config(os.path.join(FIXTURES, "sample_guard.yaml"))
        for rule_id in cfg.rules:
            self.assertIsInstance(cfg.rules[rule_id], bool)
