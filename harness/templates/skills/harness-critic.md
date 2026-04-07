---
name: harness-critic
description: Analyze failure patterns, suggest lint rules and compilable recipes
---

## Steps

1. Run: `harness critic`
2. Review the output:
   - **Recurring failure patterns**: errors that keep happening
   - **Compilable patterns**: successful procedures that can become scripts
   - **Lint rule suggestions**: failures that can be prevented by new lint rules
3. For each suggestion:
   - Show what would change (which file, what rule)
   - Ask user if they want to adopt it
4. If user approves a lint rule suggestion:
   - Show the proposed change to `docs/ARCHITECTURE.md`
   - Apply after user confirmation
5. If user approves a compilable pattern:
   - Generate the recipe script draft to `scripts/recipes/`
   - User reviews and adjusts the script

## Notes
- Critic needs trace data to work. Run tasks and record traces first.
- Lint rule suggestions are conservative — they only suggest what the data supports.
- Always preview changes before applying. Human decides whether to adopt.
