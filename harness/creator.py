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

    # --- .claude/agents/ templates ---
    agents_src = os.path.join(TEMPLATES_DIR, "agents")
    agents_dst = os.path.join(target_dir, ".claude", "agents")
    if os.path.isdir(agents_src):
        os.makedirs(agents_dst, exist_ok=True)
        for fname in os.listdir(agents_src):
            src = os.path.join(agents_src, fname)
            dst = os.path.join(agents_dst, fname)
            if os.path.isfile(src) and _write_if_not_exists(dst, Path(src).read_text(encoding="utf-8")):
                created.append(dst)

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


def scan_project(project_root: str) -> dict[str, Any]:
    """Scan an existing project and analyze its structure.

    Returns dict with: language, source_file_count, test_file_count,
    build_systems, directories, inferred_layers, existing_lint, module_name.
    """
    root = os.path.abspath(project_root)

    # Count files by extension
    ext_counts: dict[str, int] = {}
    test_count = 0
    source_count = 0
    source_exts = {".go", ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".java", ".php"}
    test_patterns = {"_test.go", "test_", ".test.", ".spec."}

    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in {
                "node_modules", "vendor", "venv", ".venv", "__pycache__",
            }
        ]
        for fname in files:
            ext = os.path.splitext(fname)[1]
            if ext in source_exts:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
                source_count += 1
                if any(p in fname for p in test_patterns):
                    test_count += 1

    # Detect primary language
    lang_map = {
        ".go": "go", ".py": "python", ".ts": "typescript",
        ".tsx": "typescript", ".js": "javascript", ".jsx": "javascript",
        ".rs": "rust", ".java": "java", ".php": "php",
    }
    language = "unknown"
    if ext_counts:
        top_ext = max(ext_counts, key=ext_counts.get)
        language = lang_map.get(top_ext, "unknown")

    # Detect build systems
    build_systems: list[str] = []
    build_files = {
        "Makefile": "Makefile", "go.mod": "go.mod",
        "package.json": "package.json", "Cargo.toml": "Cargo.toml",
        "composer.json": "composer.json", "pom.xml": "pom.xml",
        "build.gradle": "build.gradle", "pyproject.toml": "pyproject.toml",
    }
    for bfile, name in build_files.items():
        if os.path.exists(os.path.join(root, bfile)):
            build_systems.append(name)

    # Detect top-level directories
    directories: list[str] = []
    for entry in sorted(os.listdir(root)):
        fpath = os.path.join(root, entry)
        if os.path.isdir(fpath) and not entry.startswith("."):
            directories.append(entry + "/")

    # Detect existing lint config
    existing_lint: list[str] = []
    lint_files = [
        ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
        ".golangci.yml", ".golangci.yaml",
        "pyproject.toml", ".flake8", ".ruff.toml",
        "phpstan.neon", "phpcs.xml",
    ]
    for lf in lint_files:
        if os.path.exists(os.path.join(root, lf)):
            existing_lint.append(lf)

    # Infer layers from directory structure
    inferred_layers = _infer_layers(root, language, directories)

    # Detect module name
    module_name = _detect_module_name(root)

    return {
        "language": language,
        "source_file_count": source_count,
        "test_file_count": test_count,
        "build_systems": build_systems,
        "directories": directories,
        "inferred_layers": inferred_layers,
        "existing_lint": existing_lint,
        "module_name": module_name,
    }


def _detect_module_name(root: str) -> str | None:
    """Detect the module/package name from build config."""
    go_mod = os.path.join(root, "go.mod")
    if os.path.exists(go_mod):
        for line in Path(go_mod).read_text(encoding="utf-8").splitlines():
            if line.startswith("module "):
                return line.split()[1]

    pkg_json = os.path.join(root, "package.json")
    if os.path.exists(pkg_json):
        import json as _json
        try:
            data = _json.loads(Path(pkg_json).read_text(encoding="utf-8"))
            return data.get("name")
        except (ValueError, KeyError):
            pass

    return None


def _infer_layers(
    root: str, language: str, directories: list[str]
) -> dict[int, dict[str, Any]]:
    """Infer layer assignments from directory names."""
    layer_hints: dict[str, int] = {
        # Layer 0: types/models
        "types": 0, "models": 0, "dto": 0, "dtos": 0, "entities": 0,
        # Layer 1: utils/helpers
        "utils": 1, "helpers": 1, "util": 1, "helper": 1, "lib": 1, "pkg": 1,
        # Layer 2: config
        "config": 2, "configuration": 2, "settings": 2,
        # Layer 3: services/core/domain
        "services": 3, "service": 3, "core": 3, "domain": 3, "logic": 3,
        # Layer 4: api/cmd/cli/handlers/controllers/routes
        "api": 4, "cmd": 4, "cli": 4, "handlers": 4, "handler": 4,
        "controllers": 4, "controller": 4, "routes": 4, "http": 4,
        "ui": 4, "web": 4, "console": 4,
    }

    layers: dict[int, dict[str, Any]] = {}

    def _scan_dir(base: str, prefix: str):
        for entry in sorted(os.listdir(base)):
            fpath = os.path.join(base, entry)
            if not os.path.isdir(fpath) or entry.startswith("."):
                continue
            rel = prefix + entry
            low = entry.lower()
            if low in layer_hints:
                layer_num = layer_hints[low]
                if layer_num not in layers:
                    layers[layer_num] = {"paths": [], "label": ""}
                layers[layer_num]["paths"].append(rel + "/")

    # Scan top-level and one level deep (e.g. internal/types)
    _scan_dir(root, "")
    for d in directories:
        subdir = os.path.join(root, d.rstrip("/"))
        if os.path.isdir(subdir):
            _scan_dir(subdir, d)

    # Add labels
    label_map = {
        0: "Pure type definitions",
        1: "Utility functions",
        2: "Configuration",
        3: "Business logic",
        4: "Interface layer (no mutual imports)",
    }
    for num, info in layers.items():
        info["label"] = label_map.get(num, f"Layer {num}")

    return layers


def setup_project(project_root: str) -> list[str]:
    """Set up harness scaffolding for an existing project.

    Creates .harness/ directories, agent templates, and .gitignore entry.
    Does NOT generate docs — that's delegated to the harness-setup agent
    which can read the actual codebase and produce accurate documentation.

    Returns list of created file paths (skips existing files).
    """
    root = os.path.abspath(project_root)
    created: list[str] = []

    # --- docs/ directory ---
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)

    # --- .harness/ runtime directories ---
    for subdir in [
        ".harness/trace/successes",
        ".harness/trace/failures",
        ".harness/trace/checkpoints",
        ".harness/memory/episodic",
        ".harness/memory/procedural",
        ".harness/memory/failure",
    ]:
        dirpath = os.path.join(root, subdir)
        os.makedirs(dirpath, exist_ok=True)
        gk = os.path.join(dirpath, ".gitkeep")
        if _write_if_not_exists(gk, ""):
            created.append(gk)

    # --- .claude/agents/ templates ---
    agents_src = os.path.join(TEMPLATES_DIR, "agents")
    agents_dst = os.path.join(root, ".claude", "agents")
    if os.path.isdir(agents_src):
        os.makedirs(agents_dst, exist_ok=True)
        for fname in os.listdir(agents_src):
            src = os.path.join(agents_src, fname)
            dst = os.path.join(agents_dst, fname)
            if os.path.isfile(src) and _write_if_not_exists(dst, Path(src).read_text(encoding="utf-8")):
                created.append(dst)

    # --- .gitignore for .harness ---
    gitignore = os.path.join(root, ".gitignore")
    harness_ignore = "\n# Harness runtime data\n.harness/\n"
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


def _has_block(filepath: str, tag: str) -> bool:
    """Check if a markdown file contains a ```tag``` code block."""
    if not os.path.exists(filepath):
        return False
    import re
    text = Path(filepath).read_text(encoding="utf-8")
    return bool(re.search(rf"```{re.escape(tag)}\s*\n", text))


def score_project(
    scan: dict[str, Any], project_root: str
) -> dict[str, int]:
    """Score a project's harness readiness (0-100).

    Checks for harness configuration in markdown docs, not local Python files.
    Dimensions: documentation (30), lint_rules (30),
    test_coverage (20), validation_pipeline (20).
    """
    root = os.path.abspath(project_root)
    arch_path = os.path.join(root, "docs", "ARCHITECTURE.md")
    dev_path = os.path.join(root, "docs", "DEVELOPMENT.md")

    # Documentation (max 30)
    doc_score = 0
    if os.path.exists(os.path.join(root, "CLAUDE.md")) or os.path.exists(
        os.path.join(root, "AGENTS.md")
    ):
        doc_score += 15
    if os.path.exists(arch_path):
        doc_score += 10
    elif os.path.exists(os.path.join(root, "README.md")):
        doc_score += 5
    if os.path.exists(dev_path):
        doc_score += 5

    # Lint rules (max 30) — check for config blocks in ARCHITECTURE.md
    lint_score = 0
    if _has_block(arch_path, "layers"):
        lint_score += 15
    if _has_block(arch_path, "quality"):
        lint_score += 10
    if scan["existing_lint"]:
        lint_score += 5
    lint_score = min(lint_score, 30)

    # Test coverage (max 20)
    test_score = 0
    if _has_block(dev_path, "test"):
        test_score += 10
    if scan["source_file_count"] > 0:
        ratio = scan["test_file_count"] / scan["source_file_count"]
        test_score += min(10, int(ratio * 20))
    test_score = min(test_score, 20)

    # Validation pipeline (max 20) — check for build/lint blocks in DEVELOPMENT.md
    pipeline_score = 0
    if _has_block(dev_path, "build"):
        pipeline_score += 10
    if _has_block(dev_path, "lint"):
        pipeline_score += 5
    if scan["build_systems"]:
        pipeline_score += 5
    pipeline_score = min(pipeline_score, 20)

    total = doc_score + lint_score + test_score + pipeline_score

    return {
        "total": total,
        "documentation": doc_score,
        "lint_rules": lint_score,
        "test_coverage": test_score,
        "validation_pipeline": pipeline_score,
    }


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
