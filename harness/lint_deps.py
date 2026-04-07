"""Multi-language layer dependency checker.

Parses import statements from source files and checks them against
layer dependency rules defined in ARCHITECTURE.md.
"""

import os
import re
import sys
from pathlib import Path
from typing import Any

from harness.config import parse_layers


def parse_imports_go(code: str) -> list[str]:
    """Extract import paths from Go source code."""
    imports: list[str] = []

    # Grouped imports: import ( "path" \n "path" )
    for block in re.finditer(r"import\s*\((.*?)\)", code, re.DOTALL):
        for m in re.finditer(r'"([^"]+)"', block.group(1)):
            imports.append(m.group(1))

    # Single imports: import "path" or import name "path"
    for m in re.finditer(r'import\s+(?:[\w.]+\s+)?"([^"]+)"', code):
        if m.group(1) not in imports:
            imports.append(m.group(1))

    return imports


def parse_imports_python(code: str) -> list[str]:
    """Extract imported module paths from Python source code.

    Ignores relative imports (from . import x).
    """
    imports: list[str] = []

    for line in code.splitlines():
        line = line.strip()

        # from x.y import z (skip relative: from . / from .. )
        m = re.match(r"from\s+((?!\.)[a-zA-Z_][\w.]*)\s+import", line)
        if m:
            imports.append(m.group(1))
            continue

        # import x.y
        m = re.match(r"import\s+([a-zA-Z_][\w.]*)", line)
        if m:
            imports.append(m.group(1))

    return imports


def parse_imports_ts(code: str) -> list[str]:
    """Extract import paths from TypeScript/JavaScript source code.

    Handles ESM imports and CommonJS require().
    """
    imports: list[str] = []

    # ESM: import ... from 'path' or import 'path'
    for m in re.finditer(r"""import\s+.*?from\s+['"]([^'"]+)['"]""", code):
        imports.append(m.group(1))
    for m in re.finditer(r"""import\s+['"]([^'"]+)['"]""", code):
        if m.group(1) not in imports:
            imports.append(m.group(1))

    # CJS: require('path')
    for m in re.finditer(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", code):
        if m.group(1) not in imports:
            imports.append(m.group(1))

    return imports


def parse_imports_php(code: str) -> list[str]:
    """Extract use statements from PHP source code.

    Handles: use X\\Y\\Z, use X\\Y as Alias, use X\\Y\\{A, B, C}.
    Ignores: namespace declarations, closure use ($var).
    """
    imports: list[str] = []

    for line in code.splitlines():
        line = line.strip()

        # Skip namespace declarations
        if line.startswith("namespace "):
            continue

        # Grouped use: use App\Models\{User, Post}
        m = re.match(
            r"use\s+([\w\\]+)\\{([^}]+)}", line
        )
        if m:
            base = m.group(1)
            for name in m.group(2).split(","):
                name = name.strip()
                if name:
                    imports.append(f"{base}\\{name}")
            continue

        # Single use: use App\Models\User or use App\Models\User as Alias
        m = re.match(
            r"use\s+([\w\\]{2,}[\w])\s*(?:as\s+\w+)?;", line
        )
        if m:
            imports.append(m.group(1))

    return imports


def parse_imports_rust(code: str) -> list[str]:
    """Extract use and mod statements from Rust source code.

    Handles: use crate::x::y, use crate::x::{A, B}, use crate::x::*, mod x.
    """
    imports: list[str] = []

    for line in code.splitlines():
        line = line.strip()

        # Grouped use: use crate::models::{User, Post}
        m = re.match(r"use\s+([\w:]+)::\{([^}]+)\};", line)
        if m:
            base = m.group(1)
            for name in m.group(2).split(","):
                name = name.strip()
                if name:
                    imports.append(f"{base}::{name}")
            continue

        # Glob use: use crate::config::*
        m = re.match(r"use\s+([\w:]+)::\*;", line)
        if m:
            imports.append(m.group(1))
            continue

        # Simple use: use crate::types::User
        m = re.match(r"use\s+([\w:]+);", line)
        if m:
            imports.append(m.group(1))
            continue

        # mod declaration: mod types;
        m = re.match(r"mod\s+(\w+);", line)
        if m:
            imports.append(m.group(1))

    return imports


# Map file extensions to parser functions
PARSERS = {
    ".go": parse_imports_go,
    ".py": parse_imports_python,
    ".ts": parse_imports_ts,
    ".tsx": parse_imports_ts,
    ".js": parse_imports_ts,
    ".jsx": parse_imports_ts,
    ".php": parse_imports_php,
    ".rs": parse_imports_rust,
}


def _resolve_layer(file_path: str, project_root: str, layers: dict) -> int | None:
    """Determine which layer a file belongs to based on its path."""
    rel = os.path.relpath(file_path, project_root)
    # Normalize separators
    rel = rel.replace(os.sep, "/")
    for layer_num, info in sorted(layers.items()):
        for prefix in info["paths"]:
            if rel.startswith(prefix):
                return layer_num
    return None


def _resolve_import_layer(
    import_path: str, layers: dict
) -> int | None:
    """Determine which layer an import target belongs to."""
    # Normalize: dots to slashes for Python imports
    normalized = import_path.replace(".", "/")
    # Add trailing slash for prefix matching
    if not normalized.endswith("/"):
        normalized_dir = normalized + "/"
    else:
        normalized_dir = normalized

    for layer_num, info in sorted(layers.items()):
        for prefix in info["paths"]:
            if normalized.startswith(prefix) or normalized_dir.startswith(prefix):
                return layer_num
            # Also check if import matches directory without trailing slash
            prefix_trimmed = prefix.rstrip("/")
            if normalized.startswith(prefix_trimmed):
                return layer_num
    return None


def _max_layer(layers: dict) -> int:
    return max(layers.keys()) if layers else 0


def check_layer_violations(
    project_root: str, arch_md_path: str
) -> list[dict[str, Any]]:
    """Scan source files and check import layer violations.

    Returns list of violation dicts with keys:
        file, message, source_layer, target_layer, import_path, fix
    """
    layers = parse_layers(arch_md_path)
    top_layer = _max_layer(layers)
    violations: list[dict[str, Any]] = []

    for root, _dirs, files in os.walk(project_root):
        for fname in files:
            ext = os.path.splitext(fname)[1]
            parser = PARSERS.get(ext)
            if not parser:
                continue

            fpath = os.path.join(root, fname)
            src_layer = _resolve_layer(fpath, project_root, layers)
            if src_layer is None:
                continue

            code = Path(fpath).read_text(encoding="utf-8", errors="ignore")
            imports = parser(code)

            for imp in imports:
                tgt_layer = _resolve_import_layer(imp, layers)
                if tgt_layer is None:
                    continue  # External or stdlib import — skip

                rel_path = os.path.relpath(fpath, project_root)

                # Rule 1: Cannot import higher layer
                if tgt_layer > src_layer:
                    src_info = layers[src_layer]
                    tgt_info = layers[tgt_layer]
                    violations.append({
                        "file": fpath,
                        "message": (
                            f"{rel_path} imports {imp} "
                            f"(Layer {src_layer} -> Layer {tgt_layer})"
                        ),
                        "source_layer": src_layer,
                        "target_layer": tgt_layer,
                        "import_path": imp,
                        "fix": (
                            f"Layer {src_layer} ({src_info['label']}) cannot "
                            f"import Layer {tgt_layer} ({tgt_info['label']}). "
                            f"Move this dependency to a higher layer, or "
                            f"pass the needed value as a parameter."
                        ),
                    })

                # Rule 2: Top-layer members cannot import each other
                elif src_layer == top_layer and tgt_layer == top_layer:
                    # Check if they are in DIFFERENT paths within the same layer
                    src_prefix = None
                    tgt_prefix = None
                    for p in layers[top_layer]["paths"]:
                        if os.path.relpath(fpath, project_root).replace(
                            os.sep, "/"
                        ).startswith(p):
                            src_prefix = p
                        normalized_imp = imp.replace(".", "/")
                        if normalized_imp.startswith(
                            p.rstrip("/")
                        ):
                            tgt_prefix = p

                    if (
                        src_prefix
                        and tgt_prefix
                        and src_prefix != tgt_prefix
                    ):
                        violations.append({
                            "file": fpath,
                            "message": (
                                f"{rel_path} imports {imp} "
                                f"(Layer {top_layer} mutual import)"
                            ),
                            "source_layer": top_layer,
                            "target_layer": top_layer,
                            "import_path": imp,
                            "fix": (
                                f"Top-layer (Layer {top_layer}) members "
                                f"cannot import each other. "
                                f"Extract shared logic to Layer "
                                f"{top_layer - 1} or below."
                            ),
                        })

    return violations


def main() -> int:
    """CLI entry point: python3 harness/lint_deps.py [project_root] [arch_md]"""
    import argparse

    parser = argparse.ArgumentParser(description="Check layer dependency violations")
    parser.add_argument(
        "project_root", nargs="?", default=".",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--arch", default=None,
        help="Path to ARCHITECTURE.md (default: <root>/docs/ARCHITECTURE.md)"
    )
    args = parser.parse_args()

    root = os.path.abspath(args.project_root)
    arch = args.arch or os.path.join(root, "docs", "ARCHITECTURE.md")

    violations = check_layer_violations(root, arch)

    if not violations:
        print("[lint-deps]  \u2713 passed")
        return 0

    print(f"[lint-deps]  \u2717 FAILED ({len(violations)} violation(s))\n")
    for v in violations:
        print(f"  {v['message']}")
        print(f"  -> {v['fix']}")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
