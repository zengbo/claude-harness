"""Three-type memory manager.

Manages episodic (lessons), procedural (proven steps), and failure
(patterns to avoid) memories as JSON files in .harness/memory/.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MEMORY_TYPES = {"episodic", "procedural", "failure"}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower().strip())
    return slug.strip("_")[:80]


def save_memory(
    harness_dir: str,
    memory_type: str,
    title: str,
    **kwargs: Any,
) -> str:
    """Save a memory record.

    Args:
        harness_dir: path to .harness directory
        memory_type: one of 'episodic', 'procedural', 'failure'
        title: memory title (used for querying)
        **kwargs: additional fields depending on type:
            episodic: content, context
            procedural: steps, success_rate, language, project_type
            failure: pattern, frequency, fix

    Returns: path to the created file
    """
    if memory_type not in MEMORY_TYPES:
        raise ValueError(
            f"Invalid memory type '{memory_type}'. Must be one of: {MEMORY_TYPES}"
        )

    data: dict[str, Any] = {
        "type": memory_type,
        "title": title,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    data.update(kwargs)

    directory = os.path.join(harness_dir, "memory", memory_type)
    os.makedirs(directory, exist_ok=True)

    slug = _slugify(title)
    path = os.path.join(directory, f"{slug}.json")
    counter = 1
    while os.path.exists(path):
        path = os.path.join(directory, f"{slug}_{counter}.json")
        counter += 1

    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _load_all_memories(harness_dir: str) -> list[dict[str, Any]]:
    """Load all memory records from all types."""
    memories: list[dict[str, Any]] = []
    memory_root = os.path.join(harness_dir, "memory")
    if not os.path.isdir(memory_root):
        return memories

    for mtype in MEMORY_TYPES:
        type_dir = os.path.join(memory_root, mtype)
        if not os.path.isdir(type_dir):
            continue
        for fname in sorted(os.listdir(type_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(type_dir, fname)
            try:
                data = json.loads(Path(fpath).read_text(encoding="utf-8"))
                data["_file"] = fpath
                memories.append(data)
            except (json.JSONDecodeError, OSError):
                continue

    return memories


def query_memory(
    harness_dir: str,
    query: str,
) -> list[dict[str, Any]]:
    """Search memories by keyword matching on title and content fields.

    Returns matching memories sorted by relevance (number of keyword hits).
    """
    memories = _load_all_memories(harness_dir)
    if not memories or not query.strip():
        return []

    keywords = query.lower().split()
    scored: list[tuple[int, dict]] = []

    for mem in memories:
        # Build searchable text from all string fields
        searchable_parts: list[str] = []
        for key, val in mem.items():
            if key.startswith("_"):
                continue
            if isinstance(val, str):
                searchable_parts.append(val.lower())

        searchable = " ".join(searchable_parts)
        score = sum(1 for kw in keywords if kw in searchable)
        if score > 0:
            scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [mem for _, mem in scored]


def list_memory(harness_dir: str) -> dict[str, list[dict]]:
    """List all memories grouped by type."""
    result: dict[str, list[dict]] = {t: [] for t in MEMORY_TYPES}
    memories = _load_all_memories(harness_dir)
    for mem in memories:
        mtype = mem.get("type", "")
        if mtype in result:
            result[mtype].append(mem)
    return result


def delete_memory(file_path: str) -> None:
    """Delete a memory file by path."""
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage harness memories")
    sub = parser.add_subparsers(dest="command", required=True)

    # save
    p_save = sub.add_parser("save", help="Save a memory")
    p_save.add_argument("memory_type", choices=sorted(MEMORY_TYPES))
    p_save.add_argument("--title", required=True)
    p_save.add_argument("--content", default=None)
    p_save.add_argument("--context", default=None)
    p_save.add_argument("--steps", default=None)
    p_save.add_argument("--success-rate", default=None)
    p_save.add_argument("--language", default=None)
    p_save.add_argument("--project-type", default=None)
    p_save.add_argument("--pattern", default=None)
    p_save.add_argument("--frequency", type=int, default=None)
    p_save.add_argument("--fix", default=None)

    # query
    p_query = sub.add_parser("query", help="Query memories")
    p_query.add_argument("query", help="Search keywords")

    # list
    sub.add_parser("list", help="List all memories")

    parser.add_argument(
        "--harness-dir", default=".harness",
        help="Path to .harness directory",
    )

    args = parser.parse_args()
    hdir = args.harness_dir

    if args.command == "save":
        kwargs = {}
        for field in ["content", "context", "steps", "success_rate",
                       "language", "project_type", "pattern", "frequency", "fix"]:
            val = getattr(args, field.replace("-", "_"), None)
            if val is not None:
                kwargs[field] = val
        path = save_memory(hdir, args.memory_type, args.title, **kwargs)
        print(f"Saved {args.memory_type} memory: {path}")

    elif args.command == "query":
        results = query_memory(hdir, args.query)
        if not results:
            print("No matching memories found.")
        else:
            for mem in results:
                mtype = mem.get("type", "?")
                title = mem.get("title", "?")
                print(f"  [{mtype}] {title}")
                # Print key details
                for key in ["content", "steps", "pattern", "fix"]:
                    if mem.get(key):
                        print(f"    {key}: {mem[key]}")

    elif args.command == "list":
        all_mem = list_memory(hdir)
        for mtype, items in all_mem.items():
            print(f"\n{mtype} ({len(items)}):")
            for mem in items:
                print(f"  - {mem.get('title', '?')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
