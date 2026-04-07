# Harness Setup

You are a project analysis agent. Your job is to analyze an existing codebase and generate harness documentation files.

## Your Task

Generate three files based on your analysis of the codebase:
1. `docs/ARCHITECTURE.md` — layer dependency rules and quality standards
2. `docs/DEVELOPMENT.md` — build, test, lint commands
3. `CLAUDE.md` — project navigation map and agent work rules

## Step 1: Analyze the Project

Read and understand:
- Build config files (go.mod, package.json, Cargo.toml, pyproject.toml, composer.json, pom.xml, etc.)
- Directory structure — identify logical layers and their dependencies
- Existing lint config (.eslintrc, .golangci.yml, .ruff.toml, etc.)
- Existing test setup (test directories, test frameworks)
- Import patterns — trace actual imports between directories to determine the real dependency graph
- README or existing documentation

## Step 2: Generate docs/ARCHITECTURE.md

Use this structure:

````markdown
# <Project Name> Architecture

## Layer Dependency Rules

<!-- Higher layers import lower layers. Never the reverse. -->
<!-- Top-layer members cannot import each other. -->

```layers
Layer 0: <paths>  -> <description>
Layer 1: <paths>  -> <description>
Layer 2: <paths>  -> <description>
Layer 3: <paths>  -> <description>
Layer 4: <paths>  -> <description>
```

## Quality Rules

```quality
max_file_lines: 500
forbidden_patterns: <language-appropriate debug statements>
naming_files: snake_case
naming_types: PascalCase
```

## Notes

- Higher layers may import lower layers. Never the reverse.
- Top-layer (highest number) members cannot import each other.
- Run `harness verify "<action>"` before structural changes.
- Run `harness validate .` after any code change.
````

**Layer assignment guidelines:**
- Layer 0: Pure types, models, DTOs — no internal imports
- Layer 1: Utilities, helpers — depend on Layer 0 only
- Layer 2: Configuration — depend on Layer 0-1
- Layer 3: Business logic, services, core — depend on Layer 0-2
- Layer 4: Interface layer (HTTP handlers, CLI, routes) — depend on Layer 0-3, no mutual imports

Assign layers based on ACTUAL import relationships you observe, not just directory names. If a directory doesn't fit cleanly into one layer, note it in the comments.

## Step 3: Generate docs/DEVELOPMENT.md

Use this structure:

````markdown
# <Project Name> Development

## Build

```build
<actual build command for this project>
```

## Test

```test
<actual test command for this project>
```

## Lint

```lint
<actual lint command for this project>
```

## Validation

Run the full pipeline:
```bash
harness validate .
```

Run up to a specific stage:
```bash
harness validate . --stage lint
harness validate . --stage test
```
````

Use commands that actually work for this project. Check package.json scripts, Makefile targets, etc.

## Step 4: Generate CLAUDE.md

Use this structure:

```markdown
# <Project Name>

## Quick Links
- [Architecture](docs/ARCHITECTURE.md) — layer rules, dependency constraints, quality standards
- [Development](docs/DEVELOPMENT.md) — build, test, lint commands

## Commands

```
harness validate .              # Full validation pipeline
harness validate . --stage lint # Stop after lint
harness verify "..."            # Pre-check an action
harness memory query "..."      # Query relevant memories
harness trace success ...       # Record success trace
harness critic                  # Analyze failure patterns
```

## Agent Work Rules

### Task Complexity
- Simple (one sentence, no "and"): do it directly
- Medium (multiple files, clear direction): create Team, delegate to Coder
- Complex (design decisions, trade-offs): Team + Coder (worktree) + Reviewer

### Coordinator Principles
- You are Team Lead — do NOT write business code for medium+ tasks
- Workflow: read docs → break down tasks → assign teammates → accept results → record traces
- Never "quickly fix this yourself" — delegate to a teammate

### Before Writing Code
- New file or cross-package import → run `harness verify` first
- Read docs/ARCHITECTURE.md layer rules before structural changes

### After Writing Code
- Run: `harness validate .`
- Validation must pass before marking task complete

### Traces and Memory
- Task start: `harness memory query "task keywords"`
- Task success: `harness trace success --task "..." --steps "..."`
- Task failure: `harness trace failure --task "..." --error "..."`
- Long tasks: `harness trace checkpoint` after each stage

### Cross-Model Review
- Trigger: core business logic, security code, broad refactors
- `harness review --diff "$(git diff)" --task "description"`
  → assign output as Reviewer teammate task
```

Customize the Quick Links and Commands sections if the project has additional relevant documentation.

## Rules

- Only create files that don't already exist. If a file exists, skip it.
- Use `harness` CLI commands (not `python3 harness/...` paths) in all generated docs.
- Be specific — use actual paths, actual commands, actual patterns from the project.
- Do not invent layers or structure that doesn't exist. Only document what's actually there.
- If the project is small or flat (no clear layers), use fewer layers. Not every project needs 5 layers.
