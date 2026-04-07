---
name: harness-validate
description: Run 4-layer validation pipeline and interpret results
---

## Steps

1. Run: `harness validate .`
2. If all stages pass:
   - Report: which stages ran, total time
3. If a stage fails:
   - Read the error output carefully
   - Identify the root cause:
     - **build** failure: check syntax errors, missing dependencies
     - **lint-deps** failure: layer dependency violation — quote the relevant rule from `docs/ARCHITECTURE.md`
     - **lint-quality** failure: identify which quality rule was violated (file size, forbidden pattern, naming)
     - **test** failure: read test output, identify failing test and expected vs actual
     - **verify** failure: check which verify script failed and why
   - Suggest a specific fix
4. After the user makes changes, re-run validation to confirm the fix worked

## Notes
- Do not skip stages. The pipeline is designed to fast-fail — fix the current stage before moving on.
- If lint-deps fails, always read `docs/ARCHITECTURE.md` layer rules before suggesting a fix.
