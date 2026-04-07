import unittest
import os

from harness.guard import (
    ActionContext, Verdict, GuardConfig, load_guard_config,
    evaluate, DEFAULT_RULES, DEFAULT_PROTECTED_PATHS, DEFAULT_SECRET_PATTERNS,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _default_config():
    return GuardConfig(
        rules=dict(DEFAULT_RULES),
        protected_paths=list(DEFAULT_PROTECTED_PATHS),
        secret_patterns=list(DEFAULT_SECRET_PATTERNS),
    )


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


class TestR03ForcePush(unittest.TestCase):
    def _ctx(self, command):
        return ActionContext(
            action_type="bash",
            command=command,
            file_path=None,
            content=None,
            project_root="/tmp/proj",
        )

    def test_force_push_long_flag_denied(self):
        v = evaluate(self._ctx("git push --force"), _default_config())
        self.assertEqual(v.action, "deny")
        self.assertEqual(v.rule_id, "R03_force_push")

    def test_force_push_short_flag_denied(self):
        v = evaluate(self._ctx("git push -f"), _default_config())
        self.assertEqual(v.action, "deny")
        self.assertEqual(v.rule_id, "R03_force_push")

    def test_normal_push_not_r03(self):
        v = evaluate(self._ctx("git push origin main"), _default_config())
        self.assertNotEqual(v.rule_id, "R03_force_push")


class TestR04PushMain(unittest.TestCase):
    def _ctx(self, command):
        return ActionContext(
            action_type="bash",
            command=command,
            file_path=None,
            content=None,
            project_root="/tmp/proj",
        )

    def test_push_main_warns(self):
        v = evaluate(self._ctx("git push origin main"), _default_config())
        self.assertEqual(v.action, "warn")
        self.assertEqual(v.rule_id, "R04_push_main")

    def test_push_master_warns(self):
        v = evaluate(self._ctx("git push origin master"), _default_config())
        self.assertEqual(v.action, "warn")
        self.assertEqual(v.rule_id, "R04_push_main")

    def test_push_feature_branch_allows(self):
        v = evaluate(self._ctx("git push origin feat/auth"), _default_config())
        self.assertEqual(v.action, "allow")


class TestR05DestructiveGit(unittest.TestCase):
    def _ctx(self, command):
        return ActionContext(
            action_type="bash",
            command=command,
            file_path=None,
            content=None,
            project_root="/tmp/proj",
        )

    def test_reset_hard_warns(self):
        v = evaluate(self._ctx("git reset --hard"), _default_config())
        self.assertEqual(v.action, "warn")
        self.assertEqual(v.rule_id, "R05_destructive_git")

    def test_checkout_dot_warns(self):
        v = evaluate(self._ctx("git checkout ."), _default_config())
        self.assertEqual(v.action, "warn")
        self.assertEqual(v.rule_id, "R05_destructive_git")

    def test_clean_f_warns(self):
        v = evaluate(self._ctx("git clean -f"), _default_config())
        self.assertEqual(v.action, "warn")
        self.assertEqual(v.rule_id, "R05_destructive_git")


class TestR06ProtectedFiles(unittest.TestCase):
    def _ctx(self, file_path):
        return ActionContext(
            action_type="write",
            command=None,
            file_path=file_path,
            content="some content",
            project_root="/tmp/proj",
        )

    def test_env_file_denied(self):
        v = evaluate(self._ctx(".env"), _default_config())
        self.assertEqual(v.action, "deny")
        self.assertEqual(v.rule_id, "R06_protected_files")

    def test_env_local_denied(self):
        v = evaluate(self._ctx(".env.local"), _default_config())
        self.assertEqual(v.action, "deny")
        self.assertEqual(v.rule_id, "R06_protected_files")

    def test_git_hooks_denied(self):
        v = evaluate(self._ctx(".git/hooks/pre-commit"), _default_config())
        self.assertEqual(v.action, "deny")
        self.assertEqual(v.rule_id, "R06_protected_files")

    def test_harness_file_denied(self):
        v = evaluate(self._ctx("harness/guard.py"), _default_config())
        self.assertEqual(v.action, "deny")
        self.assertEqual(v.rule_id, "R06_protected_files")

    def test_src_main_allowed(self):
        v = evaluate(self._ctx("src/main.py"), _default_config())
        self.assertEqual(v.action, "allow")


class TestR07Sudo(unittest.TestCase):
    def _ctx(self, command):
        return ActionContext(
            action_type="bash",
            command=command,
            file_path=None,
            content=None,
            project_root="/tmp/proj",
        )

    def test_sudo_denied(self):
        v = evaluate(self._ctx("sudo rm -rf /"), _default_config())
        self.assertEqual(v.action, "deny")
        self.assertEqual(v.rule_id, "R07_sudo")

    def test_regular_rm_not_r07(self):
        v = evaluate(self._ctx("rm -rf ./build"), _default_config())
        self.assertNotEqual(v.rule_id, "R07_sudo")


class TestR08SecretPattern(unittest.TestCase):
    def _ctx(self, content):
        return ActionContext(
            action_type="write",
            command=None,
            file_path="config.txt",
            content=content,
            project_root="/tmp/proj",
        )

    def test_aws_key_warns(self):
        v = evaluate(self._ctx("aws_access_key = AKIAIOSFODNN7EXAMPLE"), _default_config())
        self.assertEqual(v.action, "warn")
        self.assertEqual(v.rule_id, "R08_secret_pattern")

    def test_github_pat_warns(self):
        v = evaluate(self._ctx("token = ghp_" + "a" * 36), _default_config())
        self.assertEqual(v.action, "warn")
        self.assertEqual(v.rule_id, "R08_secret_pattern")

    def test_normal_content_allows(self):
        v = evaluate(self._ctx("print('hello world')"), _default_config())
        self.assertEqual(v.action, "allow")


class TestR02ImportViolation(unittest.TestCase):
    def setUp(self):
        self.cfg = _default_config()
        self.arch = os.path.join(FIXTURES, "sample_arch.md")

    def test_import_higher_layer_denied(self):
        # File in layer 0 (internal/types/) imports from layer 3 (internal/services/)
        content = 'import "internal/services/user"'
        ctx = ActionContext("write", None, "internal/types/user.go", content, "/tmp")
        v = evaluate(ctx, self.cfg, arch_md_path=self.arch)
        self.assertEqual(v.action, "deny")
        self.assertEqual(v.rule_id, "R02_import_violation")

    def test_import_lower_layer_ok(self):
        content = 'import "internal/types/user"'
        ctx = ActionContext("write", None, "internal/services/svc.go", content, "/tmp")
        v = evaluate(ctx, self.cfg, arch_md_path=self.arch)
        self.assertEqual(v.action, "allow")

    def test_no_arch_skips_r02(self):
        content = 'import "internal/services/user"'
        ctx = ActionContext("write", None, "internal/types/user.go", content, "/tmp")
        v = evaluate(ctx, self.cfg)  # no arch_md_path
        self.assertEqual(v.action, "allow")

    def test_python_import_violation(self):
        content = 'from internal.services import user_service'
        ctx = ActionContext("write", None, "internal/types/user.py", content, "/tmp")
        v = evaluate(ctx, self.cfg, arch_md_path=self.arch)
        self.assertEqual(v.action, "deny")


class TestRuleToggling(unittest.TestCase):
    def test_disabled_r07_skips_sudo(self):
        cfg = _default_config()
        cfg.rules["R07_sudo"] = False
        ctx = ActionContext(
            action_type="bash",
            command="sudo apt-get install vim",
            file_path=None,
            content=None,
            project_root="/tmp/proj",
        )
        v = evaluate(ctx, cfg)
        self.assertNotEqual(v.rule_id, "R07_sudo")

    def test_deny_beats_warn_on_merge(self):
        # sudo (deny) + push main (warn) → deny wins
        cfg = _default_config()
        ctx = ActionContext(
            action_type="bash",
            command="sudo git push origin main",
            file_path=None,
            content=None,
            project_root="/tmp/proj",
        )
        v = evaluate(ctx, cfg)
        self.assertEqual(v.action, "deny")
