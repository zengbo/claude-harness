"""Unified CLI entry point for claude-harness."""

import argparse
import sys


def cmd_validate(args):
    from harness.validate import run_pipeline

    result = run_pipeline(
        args.project_root,
        stop_after=args.stage,
        affected_only=args.affected_only,
    )
    return 0 if result.success else 1


def cmd_init(args):
    from harness.creator import generate_scaffold

    generate_scaffold(args.project_root, args.name, args.lang, args.type)
    return 0


def cmd_setup(args):
    from harness.creator import setup_project
    import os

    root = os.path.abspath(args.project_root)
    print(f"[harness] Setting up {root} ...")
    created = setup_project(root)

    if created:
        print(f"\n\u2713 Created {len(created)} files:")
        for p in created:
            rel = os.path.relpath(p, root) if not p.endswith("(appended)") else p
            print(f"  {rel}")
    else:
        print("\nAll scaffold files already exist.")

    print("\n[harness] Scaffold ready. Now generate docs with Claude Code:")
    print('  In Claude Code, say: "Use the harness-setup agent to generate docs"')
    print("  It will analyze your codebase and create:")
    print("    - CLAUDE.md")
    print("    - docs/ARCHITECTURE.md")
    print("    - docs/DEVELOPMENT.md")
    return 0


def cmd_scan(args):
    from harness.creator import scan_project

    report = scan_project(args.project_root)
    for key, val in report.items():
        print(f"  {key}: {val}")
    return 0


def cmd_score(args):
    from harness.creator import scan_project, score_project

    scan = scan_project(args.project_root)
    result = score_project(scan, args.project_root)
    print(f"  Total: {result['total']}/100")
    for key, val in result.items():
        if key != "total":
            print(f"  {key}: {val}")
    return 0


def cmd_verify(args):
    from harness.verify_action import verify_action

    arch = args.arch or "docs/ARCHITECTURE.md"
    result = verify_action(args.action, arch)
    symbol = "\u2705" if result["valid"] else "\u274c"
    print(f"{symbol} {result['message']}")
    return 0 if result["valid"] else 1


def cmd_lint_deps(args):
    from harness.lint_deps import check_layer_violations
    from harness.config import parse_layers
    import os

    root = args.project_root
    arch = args.arch or os.path.join(root, "docs", "ARCHITECTURE.md")
    layers = parse_layers(arch)
    violations = check_layer_violations(root, layers)
    if violations:
        for v in violations:
            print(f"  \u274c {v}")
        return 1
    print("  \u2705 No layer violations found.")
    return 0


def cmd_lint_quality(args):
    from harness.lint_quality import check_quality
    from harness.config import parse_quality
    import os

    root = args.project_root
    arch = args.arch or os.path.join(root, "docs", "ARCHITECTURE.md")
    quality = parse_quality(arch)
    violations = check_quality(root, quality)
    if violations:
        for v in violations:
            print(f"  \u274c {v}")
        return 1
    print("  \u2705 No quality violations found.")
    return 0


def cmd_review(args):
    from harness.review import generate_review_prompt

    arch = args.arch or "docs/ARCHITECTURE.md"
    prompt = generate_review_prompt(args.diff, args.task, arch)
    print(prompt)
    return 0


def cmd_trace(args):
    from harness.trace import record_success, record_failure, record_checkpoint, list_traces

    hdir = args.harness_dir
    sub = args.trace_command

    if sub == "success":
        record_success(hdir, args.task, args.steps, args.files_changed, args.validation, args.review)
    elif sub == "failure":
        record_failure(hdir, args.task, args.steps, args.error, args.root_cause, args.resolution)
    elif sub == "checkpoint":
        record_checkpoint(hdir, args.task, args.stage, args.decisions, args.next_step)
    elif sub == "list":
        list_traces(hdir)
    return 0


def cmd_memory(args):
    from harness.memory import save_memory, query_memory, list_memory, delete_memory

    hdir = args.harness_dir
    sub = args.memory_command

    if sub == "save":
        kwargs = {}
        for key in ("content", "context", "steps", "success_rate", "language",
                     "project_type", "pattern", "frequency", "fix"):
            val = getattr(args, key, None)
            if val is not None:
                kwargs[key] = val
        save_memory(hdir, args.memory_type, args.title, **kwargs)
    elif sub == "query":
        results = query_memory(hdir, args.query)
        for m in results:
            print(f"  [{m['type']}] {m['title']}")
    elif sub == "list":
        memories = list_memory(hdir)
        for m in memories:
            print(f"  [{m['type']}] {m['title']}")
    elif sub == "delete":
        delete_memory(hdir, args.memory_id)
    return 0


def cmd_critic(args):
    from harness.critic import analyze_failures, find_compilable_patterns

    hdir = args.harness_dir
    failures = analyze_failures(hdir, args.min_count)
    compilable = find_compilable_patterns(hdir, args.min_successes)

    if failures:
        print("Failure clusters:")
        for f in failures:
            print(f"  [{f['count']}x] {f['pattern']}")
    if compilable:
        print("Compilable patterns:")
        for c in compilable:
            print(f"  \u2705 {c['title']} (success rate: {c['success_rate']})")
    if not failures and not compilable:
        print("  No patterns found. Need more trace data.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="harness", description="Claude Code harness engineering toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- validate ---
    p = sub.add_parser("validate", help="Run 4-layer validation pipeline")
    p.add_argument("project_root", nargs="?", default=".")
    p.add_argument("--stage", choices=["build", "lint", "test", "verify"])
    p.add_argument("--affected-only", action="store_true")

    # --- setup ---
    p = sub.add_parser("setup", help="Set up harness for an existing project (auto-detect)")
    p.add_argument("project_root", nargs="?", default=".")

    # --- init ---
    p = sub.add_parser("init", help="Scaffold harness for a new project (from template)")
    p.add_argument("project_root", nargs="?", default=".")
    p.add_argument("--name", required=True, help="Project name")
    p.add_argument("--lang", default="python", help="Language (go/python/typescript/php/rust/java)")
    p.add_argument("--type", default="library", help="Project type (library/service/cli)")

    # --- scan ---
    p = sub.add_parser("scan", help="Scan existing project for harness readiness")
    p.add_argument("project_root", nargs="?", default=".")

    # --- score ---
    p = sub.add_parser("score", help="Score project harness readiness (0-100)")
    p.add_argument("project_root", nargs="?", default=".")

    # --- verify ---
    p = sub.add_parser("verify", help="Check if an action is legal before executing")
    p.add_argument("action", help='e.g. "create file src/foo.go"')
    p.add_argument("--arch", help="Path to ARCHITECTURE.md")

    # --- lint-deps ---
    p = sub.add_parser("lint-deps", help="Check layer dependency violations")
    p.add_argument("project_root", nargs="?", default=".")
    p.add_argument("--arch", help="Path to ARCHITECTURE.md")

    # --- lint-quality ---
    p = sub.add_parser("lint-quality", help="Check code quality rules")
    p.add_argument("project_root", nargs="?", default=".")
    p.add_argument("--arch", help="Path to ARCHITECTURE.md")

    # --- review ---
    p = sub.add_parser("review", help="Generate cross-model review prompt")
    p.add_argument("--diff", required=True, help="Diff content")
    p.add_argument("--task", required=True, help="Task description")
    p.add_argument("--arch", help="Path to ARCHITECTURE.md")

    # --- trace ---
    p = sub.add_parser("trace", help="Record execution traces")
    p.add_argument("--harness-dir", default=".harness")
    tsub = p.add_subparsers(dest="trace_command", required=True)

    t = tsub.add_parser("success")
    t.add_argument("--task", required=True)
    t.add_argument("--steps", required=True)
    t.add_argument("--files-changed")
    t.add_argument("--validation")
    t.add_argument("--review")

    t = tsub.add_parser("failure")
    t.add_argument("--task", required=True)
    t.add_argument("--steps", required=True)
    t.add_argument("--error", required=True)
    t.add_argument("--root-cause")
    t.add_argument("--resolution")

    t = tsub.add_parser("checkpoint")
    t.add_argument("--task", required=True)
    t.add_argument("--stage", required=True)
    t.add_argument("--decisions", required=True)
    t.add_argument("--next", dest="next_step")

    tsub.add_parser("list")

    # --- memory ---
    p = sub.add_parser("memory", help="Manage experiential memory")
    p.add_argument("--harness-dir", default=".harness")
    msub = p.add_subparsers(dest="memory_command", required=True)

    m = msub.add_parser("save")
    m.add_argument("memory_type", choices=["episodic", "failure", "procedural"])
    m.add_argument("--title", required=True)
    m.add_argument("--content")
    m.add_argument("--context")
    m.add_argument("--steps")
    m.add_argument("--success-rate")
    m.add_argument("--language")
    m.add_argument("--project-type")
    m.add_argument("--pattern")
    m.add_argument("--frequency", type=int)
    m.add_argument("--fix")

    m = msub.add_parser("query")
    m.add_argument("query")

    msub.add_parser("list")

    m = msub.add_parser("delete")
    m.add_argument("memory_id")

    # --- critic ---
    p = sub.add_parser("critic", help="Analyze failure patterns and find compilable successes")
    p.add_argument("--harness-dir", default=".harness")
    p.add_argument("--min-count", type=int, default=2)
    p.add_argument("--min-successes", type=int, default=3)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "validate": cmd_validate,
        "setup": cmd_setup,
        "init": cmd_init,
        "scan": cmd_scan,
        "score": cmd_score,
        "verify": cmd_verify,
        "lint-deps": cmd_lint_deps,
        "lint-quality": cmd_lint_quality,
        "review": cmd_review,
        "trace": cmd_trace,
        "memory": cmd_memory,
        "critic": cmd_critic,
    }

    handler = handlers[args.command]
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
