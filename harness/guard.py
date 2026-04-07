"""Guard rule engine for runtime enforcement.

Evaluates proposed actions against configurable safety rules.
Each rule is a standalone function returning Verdict or None.
"""

import fnmatch
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ActionContext:
    action_type: str          # "bash", "write", "edit"
    command: str | None       # for bash actions
    file_path: str | None     # for write/edit actions
    content: str | None       # file content or command output
    project_root: str         # project root path


@dataclass
class Verdict:
    action: str               # "allow", "deny", "warn"
    rule_id: str              # e.g. "R03_force_push"
    message: str              # human-readable explanation


@dataclass
class GuardConfig:
    rules: dict[str, bool] = field(default_factory=dict)
    protected_paths: list[str] = field(default_factory=list)
    secret_patterns: list[str] = field(default_factory=list)


DEFAULT_RULES = {
    "R01_layer_violation": True,
    "R02_import_violation": True,
    "R03_force_push": True,
    "R04_push_main": True,
    "R05_destructive_git": True,
    "R06_protected_files": True,
    "R07_sudo": True,
    "R08_secret_pattern": True,
}

DEFAULT_PROTECTED_PATHS = [".env*", ".git/", "harness/"]

DEFAULT_SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",
    r"sk-[a-zA-Z0-9]{20,}",
    r"ghp_[a-zA-Z0-9]{36}",
]


def _check_R03_force_push(ctx: ActionContext, cfg: GuardConfig) -> Verdict | None:
    """Return Verdict if triggered, None if not applicable."""
    if ctx.action_type != "bash" or not ctx.command:
        return None
    cmd = ctx.command
    if "--force" in cmd or re.search(r"\s-f(\s|$)", cmd):
        if "git push" in cmd:
            return Verdict("deny", "R03_force_push", f"Force push blocked: {cmd!r}")
    return None


def _check_R04_push_main(ctx: ActionContext, cfg: GuardConfig) -> Verdict | None:
    """Return Verdict if triggered, None if not applicable."""
    if ctx.action_type != "bash" or not ctx.command:
        return None
    if re.search(r"git push\s+\S+\s+(main|master)\b", ctx.command):
        return Verdict("warn", "R04_push_main", f"Pushing to protected branch: {ctx.command!r}")
    return None


def _check_R05_destructive_git(ctx: ActionContext, cfg: GuardConfig) -> Verdict | None:
    """Return Verdict if triggered, None if not applicable."""
    if ctx.action_type != "bash" or not ctx.command:
        return None
    cmd = ctx.command
    patterns = [
        r"git\s+reset\s+--hard",
        r"git\s+checkout\s+\.",
        r"git\s+clean\s+.*-f",
    ]
    for pat in patterns:
        if re.search(pat, cmd):
            return Verdict("warn", "R05_destructive_git", f"Destructive git command: {cmd!r}")
    return None


def _check_R06_protected_files(ctx: ActionContext, cfg: GuardConfig) -> Verdict | None:
    """Return Verdict if triggered, None if not applicable."""
    if ctx.action_type not in ("write", "edit") or not ctx.file_path:
        return None
    path = ctx.file_path
    for pattern in cfg.protected_paths:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return Verdict("deny", "R06_protected_files", f"Write to protected path {path!r} blocked")
        else:
            basename = os.path.basename(path)
            if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(path, pattern):
                return Verdict("deny", "R06_protected_files", f"Write to protected path {path!r} blocked")
    return None


def _check_R07_sudo(ctx: ActionContext, cfg: GuardConfig) -> Verdict | None:
    """Return Verdict if triggered, None if not applicable."""
    if ctx.action_type != "bash" or not ctx.command:
        return None
    if re.search(r"\bsudo\b", ctx.command):
        return Verdict("deny", "R07_sudo", f"sudo usage blocked: {ctx.command!r}")
    return None


def _check_R08_secret_pattern(ctx: ActionContext, cfg: GuardConfig) -> Verdict | None:
    """Return Verdict if triggered, None if not applicable."""
    if not ctx.content:
        return None
    for pattern in cfg.secret_patterns:
        if re.search(pattern, ctx.content):
            return Verdict("warn", "R08_secret_pattern", f"Secret pattern {pattern!r} detected in content")
    return None


RULES: dict[str, Callable[[ActionContext, GuardConfig], Verdict | None]] = {
    "R03_force_push": _check_R03_force_push,
    "R04_push_main": _check_R04_push_main,
    "R05_destructive_git": _check_R05_destructive_git,
    "R06_protected_files": _check_R06_protected_files,
    "R07_sudo": _check_R07_sudo,
    "R08_secret_pattern": _check_R08_secret_pattern,
}


def evaluate(ctx: ActionContext, cfg: GuardConfig) -> Verdict:
    """Run all enabled rules, return merged verdict. deny > warn > allow."""
    triggered: list[Verdict] = []
    for rule_id, fn in RULES.items():
        if cfg.rules.get(rule_id) is False:
            continue
        result = fn(ctx, cfg)
        if result is not None:
            triggered.append(result)

    for v in triggered:
        if v.action == "deny":
            return v
    for v in triggered:
        if v.action == "warn":
            return v

    return Verdict("allow", "", "No rules triggered")


def load_guard_config(config_path: str) -> GuardConfig:
    """Load guard config from YAML file. Falls back to defaults if missing."""
    rules = dict(DEFAULT_RULES)
    protected = list(DEFAULT_PROTECTED_PATHS)
    secrets = list(DEFAULT_SECRET_PATTERNS)

    try:
        with open(config_path, encoding="utf-8") as f:
            text = f.read()
    except (FileNotFoundError, OSError):
        return GuardConfig(rules=rules, protected_paths=protected, secret_patterns=secrets)

    section = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "rules:":
            section = "rules"
            continue
        elif stripped == "protected_paths:":
            section = "protected_paths"
            protected = []
            continue
        elif stripped == "secret_patterns:":
            section = "secret_patterns"
            secrets = []
            continue

        if section == "rules" and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().lower()
            if key in rules:
                rules[key] = val == "true"
        elif section == "protected_paths" and stripped.startswith("- "):
            val = stripped[2:].strip().strip('"').strip("'")
            protected.append(val)
        elif section == "secret_patterns" and stripped.startswith("- "):
            val = stripped[2:].strip().strip('"').strip("'")
            secrets.append(val)

    return GuardConfig(rules=rules, protected_paths=protected, secret_patterns=secrets)
