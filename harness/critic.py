"""Failure pattern analyzer and trajectory compilation advisor.

Analyzes .harness/trace/failures/ for recurring patterns.
Scans .harness/memory/procedural/ for compilable success patterns.
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from harness.memory import _load_all_memories
from harness.trace import list_traces


def _normalize_error(error: str) -> str:
    """Normalize an error string for clustering.

    Strips numbers, paths, and variable parts to find the pattern.
    """
    # Replace specific numbers with #
    normalized = re.sub(r"\b\d+\b", "#", error)
    # Replace quoted strings with "..."
    normalized = re.sub(r'"[^"]*"', '"..."', normalized)
    normalized = re.sub(r"'[^']*'", "'...'", normalized)
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.lower()


def analyze_failures(
    harness_dir: str,
    min_count: int = 2,
) -> list[dict[str, Any]]:
    """Analyze failure traces for recurring patterns.

    Groups failures by normalized error message. Patterns appearing
    min_count or more times are returned with suggestions.

    Returns list of pattern dicts: error_pattern, count, examples, suggestion.
    """
    traces = list_traces(harness_dir)
    failures = traces.get("failures", [])

    if not failures:
        return []

    # Group by normalized error
    groups: dict[str, list[dict]] = defaultdict(list)
    for f in failures:
        error = f.get("error", "")
        if not error:
            continue
        key = _normalize_error(error)
        groups[key].append(f)

    # Filter to patterns meeting threshold
    patterns: list[dict[str, Any]] = []
    for normalized, items in groups.items():
        if len(items) < min_count:
            continue

        # Collect root causes
        root_causes = [
            item["root_cause"]
            for item in items
            if item.get("root_cause")
        ]
        common_cause = root_causes[0] if root_causes else None

        # Generate suggestion
        sample_error = items[0].get("error", "")
        suggestion = _generate_suggestion(sample_error, common_cause)

        patterns.append({
            "error_pattern": normalized,
            "count": len(items),
            "examples": [
                {"task": item.get("task"), "error": item.get("error")}
                for item in items[:3]
            ],
            "root_cause": common_cause,
            "suggestion": suggestion,
        })

    patterns.sort(key=lambda x: x["count"], reverse=True)
    return patterns


def _generate_suggestion(error: str, root_cause: str | None) -> str:
    """Generate an actionable suggestion for a failure pattern."""
    error_lower = error.lower()

    if "layer" in error_lower and "import" in error_lower:
        return (
            "Layer dependency violations are recurring. Consider: "
            "(1) Add verify_action.py check for import statements, "
            "(2) Improve lint_deps.py error messages to be more instructive, "
            "(3) Add this pattern to failure memory for future Agent reference."
        )
    if "too long" in error_lower or "lines" in error_lower:
        return (
            "File size violations are recurring. Consider: "
            "(1) Lower max_file_lines in ARCHITECTURE.md, "
            "(2) Add lint_quality.py warning at 80% threshold before hard limit."
        )
    if "timeout" in error_lower:
        return (
            "Timeout errors are recurring. Consider: "
            "(1) Add timeout configuration to verify scripts, "
            "(2) Break long-running verify scripts into smaller units."
        )

    base = "This error pattern recurs frequently."
    if root_cause:
        base += f" Root cause: {root_cause}."
    base += " Consider encoding a preventive check in lint rules or verify_action.py."
    return base


def _parse_success_rate(rate_str: str) -> tuple[int, int]:
    """Parse 'N/M' format. Returns (successes, total)."""
    m = re.match(r"(\d+)/(\d+)", str(rate_str))
    if not m:
        return 0, 0
    return int(m.group(1)), int(m.group(2))


def find_compilable_patterns(
    harness_dir: str,
    min_successes: int = 3,
) -> list[dict[str, Any]]:
    """Find procedural memories that can be compiled into scripts.

    A pattern is compilable when success_rate >= min_successes
    and numerator == denominator (100% success).

    Returns list of compilable pattern dicts.
    """
    memories = _load_all_memories(harness_dir)
    procedural = [m for m in memories if m.get("type") == "procedural"]

    compilable: list[dict[str, Any]] = []
    for mem in procedural:
        rate_str = mem.get("success_rate", "0/0")
        successes, total = _parse_success_rate(rate_str)

        if successes < min_successes or successes != total:
            continue

        title = mem.get("title", "unknown")
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower().strip()).strip("_")

        compilable.append({
            "title": title,
            "steps": mem.get("steps", ""),
            "success_rate": rate_str,
            "language": mem.get("language"),
            "project_type": mem.get("project_type"),
            "script_name": f"scripts/recipes/{slug}.sh",
        })

    return compilable


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze failure patterns and find compilable trajectories"
    )
    parser.add_argument(
        "--harness-dir", default=".harness",
        help="Path to .harness directory",
    )
    parser.add_argument(
        "--min-count", type=int, default=2,
        help="Minimum occurrences for a failure pattern (default: 2)",
    )
    parser.add_argument(
        "--min-successes", type=int, default=3,
        help="Minimum successes for compilable pattern (default: 3)",
    )
    args = parser.parse_args()

    hdir = args.harness_dir

    # Analyze failures
    print("[critic] Analyzing failure traces...\n")
    patterns = analyze_failures(hdir, args.min_count)
    if patterns:
        print(f"Found {len(patterns)} recurring pattern(s):\n")
        for i, p in enumerate(patterns, 1):
            print(f"  {i}. \"{p['error_pattern']}\" (x{p['count']})")
            if p.get("root_cause"):
                print(f"     Root cause: {p['root_cause']}")
            print(f"     -> {p['suggestion']}")
            print()
    else:
        print("No recurring failure patterns found.\n")

    # Find compilable patterns
    print("[critic] Scanning for compilable patterns...\n")
    compilable = find_compilable_patterns(hdir, args.min_successes)
    if compilable:
        print(f"Found {len(compilable)} compilable pattern(s):\n")
        for c in compilable:
            print(f"  \"{c['title']}\" ({c['success_rate']} success)")
            print(f"    Steps: {c['steps']}")
            print(f"    -> Suggest compile to: {c['script_name']}")
            print()
    else:
        print("No compilable patterns found.\n")

    # Save report
    report_path = os.path.join(hdir, "critic_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    report = {
        "failure_patterns": patterns,
        "compilable_patterns": compilable,
    }
    Path(report_path).write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Report saved to {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
