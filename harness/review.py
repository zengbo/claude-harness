"""Cross-model code review prompt generator.

Generates a structured review prompt from a diff, task description,
and architecture rules. Does NOT call any API — outputs a prompt
string for the coordinator to pass to a Reviewer teammate.
"""

import os
import sys
from pathlib import Path


def _read_arch_rules(arch_md_path: str) -> str:
    """Extract layers and quality blocks from ARCHITECTURE.md."""
    try:
        text = Path(arch_md_path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return "(Architecture file not available)"

    # Extract everything between first ## and end, or return full text
    sections: list[str] = []
    in_relevant = False
    for line in text.splitlines():
        if "layer" in line.lower() or "quality" in line.lower():
            in_relevant = True
        if in_relevant:
            sections.append(line)

    return "\n".join(sections) if sections else text


def _format_single_prompt(diff: str, task: str, arch_rules: str) -> str:
    """Format the default combined review prompt."""
    return f"""Review the following code changes.

## Task Context
{task}

## Architecture Rules
{arch_rules}

## Review Checklist
Check the changes against each dimension:
1. **Logic correctness** — edge cases, off-by-one errors, nil/null handling, error paths
2. **Architecture consistency** — does the change respect the layer rules above?
3. **Naming clarity** — are names descriptive and consistent with existing code?
4. **Performance** — unnecessary allocations, N+1 queries, missing indexes, hot paths
5. **Security** — injection risks, auth bypass, sensitive data exposure, input validation

## Changes
```diff
{diff}
```

## Output
Respond with:
- **PASS** if no substantive issues found
- **NEEDS_CHANGE** with a list of issues, each containing:
  - File and line reference
  - What the problem is
  - Why it matters
  - Suggested fix

Focus on issues that linters and tests cannot catch. Do not flag style preferences.
"""


def _format_perspective_prompt(diff: str, task: str, perspective: str, checklist: str) -> str:
    """Format a focused review prompt for a single perspective."""
    return f"""Review the following code changes from a {perspective} perspective.

## Task Context
{task}

## {perspective.title()} Checklist
Focus on: {checklist}

## Changes
```diff
{diff}
```

## Output
Respond with:
- **PASS** if no substantive {perspective} issues found
- **NEEDS_CHANGE** with a list of {perspective} issues, each containing:
  - File and line reference
  - What the problem is
  - Why it matters
  - Suggested fix

Focus only on {perspective} concerns. Do not flag issues outside this perspective.
"""


def generate_review_prompt(
    diff: str,
    task: str,
    arch_md_path: str,
    perspective: str | None = None,
) -> "str | dict[str, str]":
    """Generate a structured review prompt.

    Args:
        diff: git diff content
        task: task description / context
        arch_md_path: path to ARCHITECTURE.md
        perspective: None for combined prompt, "all" for dict of per-perspective
                     prompts, or a specific perspective name like "security"

    Returns:
        str if perspective is None or a specific name,
        dict[str, str] if perspective="all"
    """
    if perspective is None:
        arch_rules = _read_arch_rules(arch_md_path)
        return _format_single_prompt(diff, task, arch_rules)

    from harness.config import parse_review_perspectives
    perspectives = parse_review_perspectives(arch_md_path)

    if perspective == "all":
        return {
            name: _format_perspective_prompt(diff, task, name, checklist)
            for name, checklist in perspectives.items()
        }

    # Single named perspective
    checklist = perspectives.get(perspective, f"Review {perspective} concerns")
    return _format_perspective_prompt(diff, task, perspective, checklist)


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a cross-model review prompt from a diff"
    )
    parser.add_argument(
        "--diff", required=True,
        help='Diff content (use --diff "$(git diff)")',
    )
    parser.add_argument(
        "--task", required=True,
        help="Task description for context",
    )
    parser.add_argument(
        "--arch", default=None,
        help="Path to ARCHITECTURE.md",
    )
    args = parser.parse_args()

    arch = args.arch or os.path.join("docs", "ARCHITECTURE.md")
    prompt = generate_review_prompt(args.diff, args.task, arch)
    print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
