# claude-harness

A portable Python toolkit that turns any project repository into an "operating system" for Claude Code.

## Requirements

- Python 3.8+
- No external dependencies

## Quick Start

```bash
# Scaffold a new project
python3 harness/creator.py

# Validate your code
python3 harness/validate.py

# Check an action before doing it
python3 harness/verify_action.py "create file internal/types/user.go"
```

## Spec

See `docs/superpowers/specs/2026-04-07-claude-harness-design.md` in the workspace root.
