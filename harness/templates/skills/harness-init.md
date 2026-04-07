---
name: harness-init
description: Initialize harness infrastructure for a new or existing project
---

## Steps

1. Check if the current project has source files
   - If yes → existing project mode: run `harness setup .`
   - If no → new project mode: ask for project name, language, type, then run `harness init . --name "<name>" --lang <lang> --type <type>`
2. After scaffold is created, launch the **harness-setup** agent to analyze the codebase and generate documentation:
   - `docs/ARCHITECTURE.md` — layer rules based on actual code structure
   - `docs/DEVELOPMENT.md` — build/test/lint commands
   - `CLAUDE.md` — agent work rules
3. Run `harness validate .` to verify the setup works
4. Report what was created and any issues found
