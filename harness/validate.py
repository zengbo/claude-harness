"""4-layer validation pipeline orchestrator.

Pipeline: build -> lint (deps + quality) -> test -> verify
Each layer fails fast — no continuing on failure.
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness.config import parse_commands, parse_layers, parse_quality
from harness.lint_deps import check_layer_violations
from harness.lint_quality import check_quality


@dataclass
class PipelineResult:
    success: bool = True
    failed_stage: str | None = None
    stages_run: list[str] = field(default_factory=list)
    stages_skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


STAGE_ORDER = ["build", "lint", "test", "verify"]


def _run_cmd(cmd: str, cwd: str) -> tuple[int, str]:
    """Run a shell command, return (exit_code, combined output)."""
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=300,
        )
        output = proc.stdout + proc.stderr
        return proc.returncode, output.strip()
    except subprocess.TimeoutExpired:
        return 1, "Command timed out after 300s"
    except Exception as e:
        return 1, str(e)


def _print_stage(name: str, passed: bool, duration: float, detail: str = ""):
    symbol = "\u2713" if passed else "\u2717"
    status = "passed" if passed else "FAILED"
    print(f"[{name}]  {symbol} {status} ({duration:.1f}s)")
    if detail:
        for line in detail.splitlines():
            print(f"  {line}")
        print()


def run_pipeline(
    project_root: str,
    stop_after: str | None = None,
    affected_only: bool = False,
) -> PipelineResult:
    """Run the validation pipeline.

    Args:
        project_root: path to project root
        stop_after: stop after this stage (build/lint/test/verify)
        affected_only: if True, pass --affected-only hint to test stage
    """
    root = os.path.abspath(project_root)
    arch_path = os.path.join(root, "docs", "ARCHITECTURE.md")
    dev_path = os.path.join(root, "docs", "DEVELOPMENT.md")
    result = PipelineResult()

    # Parse configs (soft fail if files missing)
    commands: dict[str, str | None] = {"build": None, "test": None, "lint": None}
    if os.path.exists(dev_path):
        commands = parse_commands(dev_path)

    layers: dict = {}
    quality: dict[str, Any] = {
        "max_file_lines": 500, "forbidden_patterns": [],
        "naming_files": None, "naming_types": None,
    }
    if os.path.exists(arch_path):
        try:
            layers = parse_layers(arch_path)
        except ValueError:
            pass
        quality = parse_quality(arch_path)

    stop_index = STAGE_ORDER.index(stop_after) if stop_after in STAGE_ORDER else len(STAGE_ORDER) - 1

    # --- Stage 1: Build ---
    if 0 <= stop_index:
        t0 = time.time()
        if commands.get("build"):
            code, output = _run_cmd(commands["build"], root)
            duration = time.time() - t0
            passed = code == 0
            _print_stage("build", passed, duration, output if not passed else "")
            result.stages_run.append("build")
            if not passed:
                result.success = False
                result.failed_stage = "build"
                result.errors.append(output)
                return result
        else:
            _print_stage("build", True, 0, "no build command configured")
            result.stages_run.append("build")

    # --- Stage 2: Lint ---
    if 1 <= stop_index:
        t0 = time.time()
        lint_errors: list[str] = []

        # lint-deps
        if layers:
            violations = check_layer_violations(root, arch_path)
            for v in violations:
                lint_errors.append(f"{v['message']}\n  -> {v['fix']}")

        # lint-quality
        qv = check_quality(root, quality)
        for v in qv:
            lint_errors.append(v["message"])

        # External lint tool
        if commands.get("lint"):
            code, output = _run_cmd(commands["lint"], root)
            if code != 0:
                lint_errors.append(f"[external lint] {output}")

        duration = time.time() - t0
        passed = len(lint_errors) == 0
        detail = "\n".join(lint_errors) if lint_errors else ""
        _print_stage("lint", passed, duration, detail)
        result.stages_run.append("lint")
        if not passed:
            result.success = False
            result.failed_stage = "lint"
            result.errors = lint_errors
            return result

    # --- Stage 3: Test ---
    if 2 <= stop_index:
        t0 = time.time()
        if commands.get("test"):
            code, output = _run_cmd(commands["test"], root)
            duration = time.time() - t0
            passed = code == 0
            _print_stage("test", passed, duration, output if not passed else "")
            result.stages_run.append("test")
            if not passed:
                result.success = False
                result.failed_stage = "test"
                result.errors.append(output)
                return result
        else:
            _print_stage("test", True, 0, "no test command configured")
            result.stages_run.append("test")

    # --- Stage 4: Verify ---
    if 3 <= stop_index:
        verify_dir = os.path.join(root, "scripts", "verify")
        if os.path.isdir(verify_dir):
            scripts = sorted(
                f for f in os.listdir(verify_dir)
                if os.path.isfile(os.path.join(verify_dir, f))
                and not f.startswith(".")
            )
            if scripts:
                t0 = time.time()
                verify_errors: list[str] = []
                for script in scripts:
                    spath = os.path.join(verify_dir, script)
                    code, output = _run_cmd(f"bash {spath}", root)
                    if code != 0:
                        verify_errors.append(f"[{script}] {output}")

                duration = time.time() - t0
                passed = len(verify_errors) == 0
                detail = "\n".join(verify_errors) if verify_errors else ""
                _print_stage("verify", passed, duration, detail)
                result.stages_run.append("verify")
                if not passed:
                    result.success = False
                    result.failed_stage = "verify"
                    result.errors = verify_errors
                    return result
            else:
                result.stages_skipped.append("verify")
                print("[verify]  \u2298 skipped (no scripts)")
        else:
            result.stages_skipped.append("verify")
            print("[verify]  \u2298 skipped (no scripts/verify/ directory)")

    if result.success:
        print("\nAll stages passed.")

    return result


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run validation pipeline")
    parser.add_argument(
        "project_root", nargs="?", default=".",
        help="Project root directory",
    )
    parser.add_argument(
        "--stage", choices=STAGE_ORDER, default=None,
        help="Stop after this stage",
    )
    parser.add_argument(
        "--affected-only", action="store_true",
        help="Only test affected packages",
    )
    args = parser.parse_args()

    result = run_pipeline(
        args.project_root,
        stop_after=args.stage,
        affected_only=args.affected_only,
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
