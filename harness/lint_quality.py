"""Code quality rule checker.

Checks file line counts, forbidden patterns, and naming conventions
based on rules from ARCHITECTURE.md quality block.
"""

import os
import re
import sys
from pathlib import Path
from typing import Any

from harness.config import parse_quality

SOURCE_EXTENSIONS = {
    ".go", ".py", ".ts", ".tsx", ".js", ".jsx",
    ".rs", ".java", ".php", ".rb", ".c", ".cpp", ".h",
}

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__",
    ".harness", "harness", "vendor", ".venv", "venv",
}


def _is_snake_case(name: str) -> bool:
    stem = Path(name).stem
    return bool(re.match(r"^[a-z][a-z0-9_]*$", stem))


def check_quality(
    project_root: str,
    quality: dict,
) -> list:
    """Check code quality rules across all source files.

    Args:
        project_root: path to project root
        quality: parsed quality config dict from config.parse_quality()

    Returns:
        List of violation dicts with keys: file, message, rule
    """
    max_lines = quality.get("max_file_lines", 500)
    forbidden = quality.get("forbidden_patterns", [])
    naming_files = quality.get("naming_files")
    violations = []

    for root, dirs, files in os.walk(project_root):
        # Skip hidden and excluded directories
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in SKIP_DIRS
        ]

        for fname in files:
            ext = os.path.splitext(fname)[1]
            if ext not in SOURCE_EXTENSIONS:
                continue

            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, project_root)

            # Check file naming
            if naming_files == "snake_case" and not _is_snake_case(fname):
                violations.append({
                    "file": fpath,
                    "message": (
                        f"{rel}: filename '{fname}' is not snake_case"
                    ),
                    "rule": "naming_files",
                })

            try:
                content = Path(fpath).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            lines = content.splitlines()

            # Check line count
            if len(lines) > max_lines:
                violations.append({
                    "file": fpath,
                    "message": (
                        f"{rel}: {len(lines)} lines "
                        f"(max {max_lines})"
                    ),
                    "rule": "max_file_lines",
                })

            # Check forbidden patterns
            for i, line in enumerate(lines, 1):
                for pattern in forbidden:
                    if pattern in line:
                        violations.append({
                            "file": fpath,
                            "message": (
                                f"{rel}:{i}: forbidden pattern "
                                f"'{pattern}' found"
                            ),
                            "rule": "forbidden_patterns",
                        })

    return violations


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check code quality rules")
    parser.add_argument(
        "project_root", nargs="?", default=".",
        help="Project root directory",
    )
    parser.add_argument(
        "--arch", default=None,
        help="Path to ARCHITECTURE.md",
    )
    args = parser.parse_args()

    root = os.path.abspath(args.project_root)
    arch = args.arch or os.path.join(root, "docs", "ARCHITECTURE.md")
    quality = parse_quality(arch)
    violations = check_quality(root, quality)

    if not violations:
        print("[lint-quality]  \u2713 passed")
        return 0

    print(f"[lint-quality]  \u2717 FAILED ({len(violations)} violation(s))\n")
    for v in violations:
        print(f"  {v['message']}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
