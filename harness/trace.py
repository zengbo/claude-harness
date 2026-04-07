"""Execution trace recorder.

Records success/failure/checkpoint traces as JSON files in .harness/trace/.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower().strip())
    return slug.strip("_")[:80]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_trace(directory: str, data: dict[str, Any]) -> str:
    """Write a trace record to a JSON file. Returns the file path."""
    _ensure_dir(directory)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = _slugify(data.get("task", "unknown"))
    # Avoid collisions with a counter
    base = f"{timestamp}_{slug}"
    path = os.path.join(directory, f"{base}.json")
    counter = 1
    while os.path.exists(path):
        path = os.path.join(directory, f"{base}_{counter}.json")
        counter += 1

    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def record_success(
    harness_dir: str,
    task: str,
    steps: str,
    files_changed: str | None = None,
    validation: str | None = None,
    review: str | None = None,
) -> str:
    """Record a successful task execution trace."""
    data = {
        "type": "success",
        "task": task,
        "steps": steps,
        "files_changed": files_changed,
        "validation": validation,
        "review": review,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    directory = os.path.join(harness_dir, "trace", "successes")
    return _write_trace(directory, data)


def record_failure(
    harness_dir: str,
    task: str,
    steps: str,
    error: str,
    root_cause: str | None = None,
    resolution: str | None = None,
) -> str:
    """Record a failed task execution trace."""
    data = {
        "type": "failure",
        "task": task,
        "steps": steps,
        "error": error,
        "root_cause": root_cause,
        "resolution": resolution,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    directory = os.path.join(harness_dir, "trace", "failures")
    return _write_trace(directory, data)


def record_checkpoint(
    harness_dir: str,
    task: str,
    stage: str,
    decisions: str,
    next_step: str | None = None,
) -> str:
    """Record a checkpoint for a long-running task."""
    data = {
        "type": "checkpoint",
        "task": task,
        "stage": stage,
        "decisions": decisions,
        "next_step": next_step,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    directory = os.path.join(harness_dir, "trace", "checkpoints")
    return _write_trace(directory, data)


def list_traces(harness_dir: str) -> dict[str, list[dict]]:
    """List all traces grouped by type."""
    result: dict[str, list[dict]] = {
        "successes": [],
        "failures": [],
        "checkpoints": [],
    }
    for category in result:
        cat_dir = os.path.join(harness_dir, "trace", category)
        if not os.path.isdir(cat_dir):
            continue
        for fname in sorted(os.listdir(cat_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(cat_dir, fname)
            try:
                data = json.loads(Path(fpath).read_text(encoding="utf-8"))
                data["_file"] = fname
                result[category].append(data)
            except (json.JSONDecodeError, OSError):
                continue
    return result


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Record execution traces")
    sub = parser.add_subparsers(dest="command", required=True)

    # success
    p_success = sub.add_parser("success", help="Record a successful trace")
    p_success.add_argument("--task", required=True)
    p_success.add_argument("--steps", required=True)
    p_success.add_argument("--files-changed", default=None)
    p_success.add_argument("--validation", default=None)
    p_success.add_argument("--review", default=None)

    # failure
    p_failure = sub.add_parser("failure", help="Record a failure trace")
    p_failure.add_argument("--task", required=True)
    p_failure.add_argument("--steps", required=True)
    p_failure.add_argument("--error", required=True)
    p_failure.add_argument("--root-cause", default=None)
    p_failure.add_argument("--resolution", default=None)

    # checkpoint
    p_cp = sub.add_parser("checkpoint", help="Record a checkpoint")
    p_cp.add_argument("--task", required=True)
    p_cp.add_argument("--stage", required=True)
    p_cp.add_argument("--decisions", required=True)
    p_cp.add_argument("--next", default=None)

    # list
    sub.add_parser("list", help="List all traces")

    parser.add_argument(
        "--harness-dir", default=".harness",
        help="Path to .harness directory",
    )

    args = parser.parse_args()
    hdir = args.harness_dir

    if args.command == "success":
        path = record_success(
            hdir, args.task, args.steps,
            args.files_changed, args.validation, args.review,
        )
        print(f"Recorded success trace: {path}")
    elif args.command == "failure":
        path = record_failure(
            hdir, args.task, args.steps, args.error,
            args.root_cause, args.resolution,
        )
        print(f"Recorded failure trace: {path}")
    elif args.command == "checkpoint":
        path = record_checkpoint(
            hdir, args.task, args.stage, args.decisions, getattr(args, "next", None),
        )
        print(f"Recorded checkpoint: {path}")
    elif args.command == "list":
        traces = list_traces(hdir)
        for cat, items in traces.items():
            print(f"\n{cat} ({len(items)}):")
            for item in items:
                print(f"  [{item.get('timestamp', '?')[:10]}] {item.get('task', '?')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
