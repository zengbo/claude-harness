"""Bridge between Claude Code hooks and the guard engine.

Parses tool input from Claude Code PreToolUse hooks and evaluates
proposed actions against the configured guard rules.
"""

import json
import os
import sys


def parse_tool_input(tool_type: str, tool_json: str, project_root: str):
    """Parse Claude Code tool JSON into an ActionContext.

    Args:
        tool_type: "bash", "write", or "edit"
        tool_json: JSON string from stdin
        project_root: absolute path to the project root (for relativizing paths)

    Returns:
        ActionContext if parsing succeeds, None if JSON is invalid.
    """
    from harness.guard import ActionContext

    try:
        data = json.loads(tool_json)
    except (json.JSONDecodeError, ValueError):
        return None

    if tool_type == "bash":
        command = data.get("command")
        return ActionContext(
            action_type="bash",
            command=command,
            file_path=None,
            content=command,
            project_root=project_root,
        )

    if tool_type == "write":
        raw_path = data.get("file_path", "")
        content = data.get("content", "")
        try:
            rel_path = os.path.relpath(raw_path, project_root)
        except ValueError:
            rel_path = raw_path
        return ActionContext(
            action_type="write",
            command=None,
            file_path=rel_path,
            content=content,
            project_root=project_root,
        )

    if tool_type == "edit":
        raw_path = data.get("file_path", "")
        new_string = data.get("new_string", "")
        try:
            rel_path = os.path.relpath(raw_path, project_root)
        except ValueError:
            rel_path = raw_path
        return ActionContext(
            action_type="edit",
            command=None,
            file_path=rel_path,
            content=new_string,
            project_root=project_root,
        )

    return None


def generate_hooks_config() -> dict:
    """Return a dict suitable for .claude/settings.json hooks configuration."""
    return {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "command": "python3 harness/hooks.py bash"},
                {"matcher": "Write", "command": "python3 harness/hooks.py write"},
                {"matcher": "Edit", "command": "python3 harness/hooks.py edit"},
            ]
        }
    }


def main():
    """CLI entry point for Claude Code PreToolUse hooks."""
    from harness.guard import evaluate, load_guard_config

    if len(sys.argv) < 2:
        print("[hooks] Usage: hooks.py <bash|write|edit>", file=sys.stderr)
        sys.exit(1)

    tool_type = sys.argv[1]
    tool_json = sys.stdin.read()

    project_root = os.getcwd()
    ctx = parse_tool_input(tool_type, tool_json, project_root)

    if ctx is None:
        # Invalid JSON — let the tool proceed (fail safe)
        sys.exit(0)

    config_path = os.path.join(project_root, ".harness", "guard.yaml")
    cfg = load_guard_config(config_path)

    verdict = evaluate(ctx, cfg)

    if verdict.action == "deny":
        print(f"[guard] DENIED ({verdict.rule_id}): {verdict.message}", file=sys.stderr)
        sys.exit(2)
    elif verdict.action == "warn":
        print(f"[guard] WARNING ({verdict.rule_id}): {verdict.message}", file=sys.stderr)
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
