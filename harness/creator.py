"""Project scaffold generator.

New project mode: interactive questionnaire -> generate full infrastructure.
"""

import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Language + project type presets
LANGUAGE_PRESETS: dict[str, dict[str, Any]] = {
    "go": {
        "layers": (
            "Layer 0: internal/types/, pkg/models/        "
            "-> Pure type definitions, no internal imports\n"
            "Layer 1: internal/utils/, pkg/helpers/        "
            "-> Utility functions, depends on Layer 0 only\n"
            "Layer 2: internal/config/                     "
            "-> Configuration, depends on Layer 0-1\n"
            "Layer 3: internal/services/, internal/core/   "
            "-> Business logic, depends on Layer 0-2\n"
            "Layer 4: cmd/, api/handlers/                  "
            "-> Interface layer, depends on Layer 0-3, no mutual imports"
        ),
        "build_cmd": "go build ./...",
        "test_cmd": "go test ./...",
        "lint_cmd": "golangci-lint run",
        "forbidden_patterns": "fmt.Println",
    },
    "python": {
        "layers": (
            "Layer 0: src/models/, src/types/              "
            "-> Pure data models, no internal imports\n"
            "Layer 1: src/utils/                           "
            "-> Utility functions, depends on Layer 0 only\n"
            "Layer 2: src/config/                          "
            "-> Configuration, depends on Layer 0-1\n"
            "Layer 3: src/services/, src/core/             "
            "-> Business logic, depends on Layer 0-2\n"
            "Layer 4: src/api/, src/cli/                   "
            "-> Interface layer, depends on Layer 0-3, no mutual imports"
        ),
        "build_cmd": "python3 -m py_compile src/**/*.py",
        "test_cmd": "python3 -m unittest discover -s tests -v",
        "lint_cmd": "ruff check src/",
        "forbidden_patterns": "print(, breakpoint()",
    },
    "typescript": {
        "layers": (
            "Layer 0: src/types/, src/models/              "
            "-> Pure type definitions, no internal imports\n"
            "Layer 1: src/utils/, src/helpers/             "
            "-> Utility functions, depends on Layer 0 only\n"
            "Layer 2: src/config/                          "
            "-> Configuration, depends on Layer 0-1\n"
            "Layer 3: src/services/, src/core/             "
            "-> Business logic, depends on Layer 0-2\n"
            "Layer 4: src/api/, src/cli/, src/routes/      "
            "-> Interface layer, depends on Layer 0-3, no mutual imports"
        ),
        "build_cmd": "npx tsc --noEmit",
        "test_cmd": "npx vitest run",
        "lint_cmd": "npx eslint src/",
        "forbidden_patterns": "console.log",
    },
    "php": {
        "layers": (
            "Layer 0: src/Models/, src/DTOs/               "
            "-> Pure data objects, no internal imports\n"
            "Layer 1: src/Utils/, src/Helpers/             "
            "-> Utility functions, depends on Layer 0 only\n"
            "Layer 2: src/Config/                          "
            "-> Configuration, depends on Layer 0-1\n"
            "Layer 3: src/Services/, src/Core/             "
            "-> Business logic, depends on Layer 0-2\n"
            "Layer 4: src/Http/, src/Console/              "
            "-> Interface layer, depends on Layer 0-3, no mutual imports"
        ),
        "build_cmd": "php -l src/**/*.php",
        "test_cmd": "vendor/bin/phpunit",
        "lint_cmd": "vendor/bin/phpstan analyse src/",
        "forbidden_patterns": "var_dump(, print_r(, dd(",
    },
    "rust": {
        "layers": (
            "Layer 0: src/types/, src/models/              "
            "-> Pure type definitions\n"
            "Layer 1: src/utils/                           "
            "-> Utility functions, depends on Layer 0 only\n"
            "Layer 2: src/config/                          "
            "-> Configuration, depends on Layer 0-1\n"
            "Layer 3: src/services/, src/core/             "
            "-> Business logic, depends on Layer 0-2\n"
            "Layer 4: src/api/, src/cli/                   "
            "-> Interface layer, depends on Layer 0-3, no mutual imports"
        ),
        "build_cmd": "cargo build",
        "test_cmd": "cargo test",
        "lint_cmd": "cargo clippy",
        "forbidden_patterns": "println!, dbg!",
    },
    "java": {
        "layers": (
            "Layer 0: src/main/java/**/model/              "
            "-> Pure data models\n"
            "Layer 1: src/main/java/**/util/               "
            "-> Utility classes, depends on Layer 0 only\n"
            "Layer 2: src/main/java/**/config/             "
            "-> Configuration, depends on Layer 0-1\n"
            "Layer 3: src/main/java/**/service/            "
            "-> Business logic, depends on Layer 0-2\n"
            "Layer 4: src/main/java/**/controller/         "
            "-> Interface layer, depends on Layer 0-3, no mutual imports"
        ),
        "build_cmd": "mvn compile",
        "test_cmd": "mvn test",
        "lint_cmd": "mvn checkstyle:check",
        "forbidden_patterns": "System.out.println",
    },
}


def _load_template(name: str) -> str:
    path = os.path.join(TEMPLATES_DIR, name)
    return Path(path).read_text(encoding="utf-8")


def _write_if_not_exists(path: str, content: str) -> bool:
    """Write file only if it doesn't exist. Returns True if written."""
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")
    return True


def generate_scaffold(
    target_dir: str,
    project_name: str,
    language: str,
    project_type: str,
) -> list[str]:
    """Generate harness infrastructure in target directory.

    Returns list of created file paths (skips existing files).
    """
    preset = LANGUAGE_PRESETS.get(language, LANGUAGE_PRESETS["python"])
    created: list[str] = []

    # --- CLAUDE.md ---
    tmpl = _load_template("CLAUDE.md.tmpl")
    content = tmpl.replace("{{PROJECT_NAME}}", project_name)
    path = os.path.join(target_dir, "CLAUDE.md")
    if _write_if_not_exists(path, content):
        created.append(path)

    # --- docs/ARCHITECTURE.md ---
    tmpl = _load_template("ARCHITECTURE.md.tmpl")
    layers_block = f"```layers\n{preset['layers']}\n```"
    content = (
        tmpl.replace("{{PROJECT_NAME}}", project_name)
        .replace("{{LAYERS_BLOCK}}", layers_block)
        .replace("{{FORBIDDEN_PATTERNS}}", preset["forbidden_patterns"])
    )
    path = os.path.join(target_dir, "docs", "ARCHITECTURE.md")
    if _write_if_not_exists(path, content):
        created.append(path)

    # --- docs/DEVELOPMENT.md ---
    tmpl = _load_template("DEVELOPMENT.md.tmpl")
    content = (
        tmpl.replace("{{PROJECT_NAME}}", project_name)
        .replace("{{BUILD_CMD}}", preset["build_cmd"])
        .replace("{{TEST_CMD}}", preset["test_cmd"])
        .replace("{{LINT_CMD}}", preset["lint_cmd"])
    )
    path = os.path.join(target_dir, "docs", "DEVELOPMENT.md")
    if _write_if_not_exists(path, content):
        created.append(path)

    # --- harness/ package (copy from this package) ---
    harness_src = os.path.dirname(__file__)
    harness_dst = os.path.join(target_dir, "harness")
    if not os.path.exists(harness_dst):
        shutil.copytree(harness_src, harness_dst)
        created.append(harness_dst)
    elif not os.path.exists(os.path.join(harness_dst, "__init__.py")):
        # harness dir exists but no __init__.py -- partial state, add it
        Path(os.path.join(harness_dst, "__init__.py")).write_text(
            '"""claude-harness."""\n'
        )
        created.append(os.path.join(harness_dst, "__init__.py"))

    # --- scripts/validate.sh ---
    path = os.path.join(target_dir, "scripts", "validate.sh")
    if _write_if_not_exists(path, (
        "#!/usr/bin/env bash\n"
        "# Thin wrapper for CI -- delegates to Python pipeline.\n"
        'set -euo pipefail\n'
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        'PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"\n'
        'exec python3 "$PROJECT_ROOT/harness/validate.py" '
        '"$PROJECT_ROOT" "$@"\n'
    )):
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        created.append(path)

    # --- scripts/verify/ ---
    verify_dir = os.path.join(target_dir, "scripts", "verify")
    os.makedirs(verify_dir, exist_ok=True)
    gitkeep = os.path.join(verify_dir, ".gitkeep")
    if _write_if_not_exists(gitkeep, ""):
        created.append(gitkeep)

    # --- .harness/ runtime directories ---
    for subdir in [
        ".harness/trace/successes",
        ".harness/trace/failures",
        ".harness/trace/checkpoints",
        ".harness/memory/episodic",
        ".harness/memory/procedural",
        ".harness/memory/failure",
    ]:
        dirpath = os.path.join(target_dir, subdir)
        os.makedirs(dirpath, exist_ok=True)
        gk = os.path.join(dirpath, ".gitkeep")
        if _write_if_not_exists(gk, ""):
            created.append(gk)

    # --- .gitignore addition for .harness ---
    gitignore = os.path.join(target_dir, ".gitignore")
    harness_ignore = "\n# Harness runtime data (optional: remove to share team memory)\n.harness/\n"
    if os.path.exists(gitignore):
        existing = Path(gitignore).read_text(encoding="utf-8")
        if ".harness/" not in existing:
            with open(gitignore, "a") as f:
                f.write(harness_ignore)
            created.append(gitignore + " (appended)")
    else:
        _write_if_not_exists(gitignore, harness_ignore.lstrip())
        created.append(gitignore)

    return created


def main() -> int:
    """CLI entry point -- interactive questionnaire."""
    print("[harness-creator] Scanning project...\n")

    # Detect if there are source files
    cwd = os.getcwd()
    source_exts = {".go", ".py", ".ts", ".tsx", ".js", ".rs", ".java", ".php"}
    has_source = False
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
        for f in files:
            if os.path.splitext(f)[1] in source_exts:
                has_source = True
                break
        if has_source:
            break

    if has_source:
        print("Source files detected. Existing project scanning is not yet implemented.")
        print("Use Phase 2 creator for existing projects.")
        print("Falling back to new project mode.\n")

    # Interactive questionnaire
    project_name = input("Project name: ").strip()
    if not project_name:
        print("Error: project name is required")
        return 1

    langs = list(LANGUAGE_PRESETS.keys())
    print(f"Language ({'/'.join(langs)}): ", end="")
    language = input().strip().lower()
    if language not in LANGUAGE_PRESETS:
        print(f"Warning: unknown language '{language}', using python defaults")
        language = "python"

    print("Project type (cli/web-api/library/monorepo): ", end="")
    project_type = input().strip().lower() or "library"

    print(f"\nGenerating scaffold for '{project_name}' ({language}/{project_type})...\n")

    created = generate_scaffold(cwd, project_name, language, project_type)

    if created:
        print(f"\u2713 Created {len(created)} files/directories:")
        for p in created:
            rel = os.path.relpath(p, cwd) if not p.endswith("(appended)") else p
            print(f"  {rel}")
    else:
        print("All files already exist. Nothing to generate.")

    print(f"\nNext: review docs/ARCHITECTURE.md and adjust layer rules to match your project.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
