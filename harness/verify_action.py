"""Pre-action legality checker.

Validates whether a proposed action (create file, add import) is
consistent with layer dependency rules before the Agent does it.
"""

import os
import re
import sys
from typing import Any

from harness.config import parse_layers


def _resolve_layer(
    file_path: str, layers: dict,
) -> int | None:
    """Resolve which layer a file path belongs to."""
    normalized = file_path.replace(os.sep, "/")
    for layer_num, info in sorted(layers.items()):
        for prefix in info["paths"]:
            if normalized.startswith(prefix):
                return layer_num
    return None


def _resolve_import_layer(
    import_path: str, layers: dict,
) -> int | None:
    """Resolve which layer an import path targets."""
    normalized = import_path.replace(".", "/")
    for layer_num, info in sorted(layers.items()):
        for prefix in info["paths"]:
            prefix_trimmed = prefix.rstrip("/")
            if normalized.startswith(prefix_trimmed):
                return layer_num
    return None


def verify_action(
    action: str, arch_md_path: str,
) -> dict:
    """Verify whether a proposed action is allowed.

    Understands two action types:
      - "create file <path>": checks if path is in a known layer
      - "add import <import_path> in <file_path>": checks layer dependency

    Returns dict with keys: valid (bool), message (str)
    """
    layers = parse_layers(arch_md_path)
    top_layer = max(layers.keys()) if layers else 0

    # Pattern: "create file <path>"
    m = re.match(r"create\s+file\s+(.+)", action, re.IGNORECASE)
    if m:
        fpath = m.group(1).strip()
        layer = _resolve_layer(fpath, layers)
        if layer is not None:
            return {
                "valid": True,
                "message": (
                    f"VALID: {fpath} is in Layer {layer} "
                    f"({layers[layer]['label']})"
                ),
            }
        return {
            "valid": True,
            "message": (
                f"VALID: {fpath} is not in any defined layer "
                f"(no constraints apply)"
            ),
        }

    # Pattern: "add import <import> in <file>"
    m = re.match(
        r"add\s+import\s+(\S+)\s+in\s+(.+)", action, re.IGNORECASE,
    )
    if m:
        import_path = m.group(1).strip()
        file_path = m.group(2).strip()
        src_layer = _resolve_layer(file_path, layers)
        tgt_layer = _resolve_import_layer(import_path, layers)

        if src_layer is None or tgt_layer is None:
            return {
                "valid": True,
                "message": (
                    "VALID: cannot determine layers — no constraints apply"
                ),
            }

        # Rule: cannot import higher layer
        if tgt_layer > src_layer:
            return {
                "valid": False,
                "message": (
                    f"INVALID: {file_path} is Layer {src_layer} "
                    f"({layers[src_layer]['label']}), "
                    f"cannot import {import_path} which is Layer {tgt_layer} "
                    f"({layers[tgt_layer]['label']}). "
                    f"Move this logic to Layer {tgt_layer} or higher, "
                    f"or pass the dependency as a parameter."
                ),
            }

        # Rule: top-layer mutual imports
        if src_layer == top_layer and tgt_layer == top_layer:
            src_prefix = None
            tgt_prefix = None
            for p in layers[top_layer]["paths"]:
                if file_path.replace(os.sep, "/").startswith(p):
                    src_prefix = p
                imp_norm = import_path.replace(".", "/")
                if imp_norm.startswith(p.rstrip("/")):
                    tgt_prefix = p
            if src_prefix and tgt_prefix and src_prefix != tgt_prefix:
                return {
                    "valid": False,
                    "message": (
                        f"INVALID: {file_path} and {import_path} are both "
                        f"Layer {top_layer} but in different paths. "
                        f"Top-layer members cannot import each other. "
                        f"Extract shared logic to Layer {top_layer - 1} "
                        f"or below."
                    ),
                }

        return {
            "valid": True,
            "message": (
                f"VALID: Layer {src_layer} can import "
                f"Layer {tgt_layer}"
            ),
        }

    # Unknown action type — pass through
    return {
        "valid": True,
        "message": "UNKNOWN action type — no constraints checked",
    }


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify if an action is allowed by layer rules",
    )
    parser.add_argument(
        "action",
        help='Action to verify, e.g. "create file src/foo.go"',
    )
    parser.add_argument(
        "--arch", default=None,
        help="Path to ARCHITECTURE.md",
    )
    args = parser.parse_args()

    arch = args.arch or os.path.join("docs", "ARCHITECTURE.md")
    result = verify_action(args.action, arch)

    symbol = "\u2713" if result["valid"] else "\u2717"
    print(f"{symbol} {result['message']}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
