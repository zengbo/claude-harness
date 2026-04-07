"""Parse tagged code blocks from ARCHITECTURE.md and DEVELOPMENT.md."""

import re
from pathlib import Path
from typing import Any


def _read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return p.read_text(encoding="utf-8")


def _extract_block(text: str, tag: str) -> str | None:
    """Extract content from a fenced code block with the given tag.

    Matches ```tag ... ``` blocks in markdown.
    """
    pattern = rf"```{re.escape(tag)}\s*\n(.*?)```"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else None


def parse_layers(arch_md_path: str) -> dict[int, dict[str, Any]]:
    """Parse layer definitions from ARCHITECTURE.md.

    Expected format inside ```layers block:
        Layer 0: path1/, path2/  -> Description text
    """
    text = _read_file(arch_md_path)
    block = _extract_block(text, "layers")
    if block is None:
        raise ValueError(f"No ```layers``` block found in {arch_md_path}")

    layers: dict[int, dict[str, Any]] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(
            r"Layer\s+(\d+)\s*:\s*(.+?)\s*->\s*(.+)", line
        )
        if not m:
            continue
        num = int(m.group(1))
        paths = [p.strip() for p in m.group(2).split(",") if p.strip()]
        label = m.group(3).strip()
        layers[num] = {"paths": paths, "label": label}

    return layers


def parse_quality(arch_md_path: str) -> dict[str, Any]:
    """Parse quality rules from ARCHITECTURE.md.

    Returns defaults if no ```quality``` block found.
    """
    defaults: dict[str, Any] = {
        "max_file_lines": 500,
        "forbidden_patterns": [],
        "naming_files": None,
        "naming_types": None,
    }

    text = _read_file(arch_md_path)
    block = _extract_block(text, "quality")
    if block is None:
        return defaults

    result = dict(defaults)
    for line in block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if key == "max_file_lines":
            result["max_file_lines"] = int(value)
        elif key == "forbidden_patterns":
            result["forbidden_patterns"] = [
                p.strip() for p in value.split(",") if p.strip()
            ]
        elif key.startswith("naming_"):
            result[key] = value

    return result


def parse_commands(dev_md_path: str) -> dict[str, str | None]:
    """Parse build/test/lint commands from DEVELOPMENT.md."""
    text = _read_file(dev_md_path)
    result: dict[str, str | None] = {}
    for tag in ("build", "test", "lint"):
        block = _extract_block(text, tag)
        result[tag] = block.strip() if block else None
    return result
