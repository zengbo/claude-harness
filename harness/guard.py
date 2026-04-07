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
