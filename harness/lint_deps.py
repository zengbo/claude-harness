"""Multi-language layer dependency checker.

Parses import statements from source files and checks them against
layer dependency rules defined in ARCHITECTURE.md.
"""

import re


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
