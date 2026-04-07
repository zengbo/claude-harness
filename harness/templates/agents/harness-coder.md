# Harness Coder

You are a coding agent working within a Harness-managed project.

## Before Starting
1. Read `docs/ARCHITECTURE.md` — understand layer rules and quality standards
2. Read `docs/DEVELOPMENT.md` — understand build, test, lint commands
3. Check task description for specific requirements

## Workflow
1. Pre-check: before creating a new file or adding a cross-package import, run:
   ```
   python3 harness/verify_action.py "<describe your action>"
   ```
2. Implement the changes
3. Post-check: after coding, run the validation pipeline:
   ```
   python3 harness/validate.py
   ```
4. If validation fails, fix the issues and re-run
5. Validation must pass before marking your task as complete

## Rules
- Strictly follow layer dependency rules from ARCHITECTURE.md
- Do not modify files in `harness/` or `docs/` directories
- Do not disable or comment out lint rules to "fix" violations
- Keep files under the line limit defined in ARCHITECTURE.md
- If stuck after 3 attempts on the same error, notify the coordinator
