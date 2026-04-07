---
name: harness-do
description: Orchestrate the full development cycle for a task — assess complexity, delegate to coder/reviewer, record traces
---

## Auto-Routing

When you receive an implementation request (feature, bugfix, refactor), this skill orchestrates the full cycle.

## Steps

### 1. Parse Requirement
- If the input is a URL: fetch and read the content
- Extract the core task description

### 2. Query Memory
- Run: `harness memory query "<task keywords>"`
- If relevant procedural memory found: reference proven steps in your plan

### 3. Assess Complexity
- **Simple** (single sentence, no "and", affects 1-2 files): do it directly, skip to step 6
  - Examples: fix typo, rename variable, update config value
- **Medium** (multiple files, clear direction, no design decisions): proceed to step 4
  - Examples: add API endpoint, fix a bug across modules, add test coverage
- **Complex** (design decisions, architecture trade-offs, cross-cutting): proceed to step 4 + step 5
  - Examples: refactor module, add new subsystem, change auth strategy

### 4. Plan + Delegate to Coder
1. Read `docs/ARCHITECTURE.md` for layer rules
2. Break the task into subtasks
3. **[PAUSE]** Present plan to user for confirmation
4. After confirmation, create a Team and launch the **harness-coder** agent
5. For Complex tasks: run coder in a worktree for isolation
6. Coder must run `harness validate .` before marking task complete

### 5. Review (Complex tasks only)
1. Run: `harness review --diff "$(git diff)" --task "<description>" --perspective all`
2. Launch the **harness-reviewer** agent with the review prompt (use a different model if available)
3. If PASS → continue to step 6
4. If NEEDS_CHANGE → feed issues back to Coder
5. Maximum 3 rounds of Coder→Review→Fix. After 3 rounds, stop and report to user.

### 6. Record Trace
- On success: `harness trace success --task "<description>" --steps "<steps taken>"`
- On failure: `harness trace failure --task "<description>" --error "<error>" --root-cause "<cause>"`
- If a new lesson was learned: `harness memory save episodic --title "<lesson>" --content "<details>"`

### 7. Report
- Summarize what was done, which files changed, validation results
- If review was performed, include review verdict

## Rules
- You are the coordinator. For Medium+ tasks, do NOT write business code yourself — delegate to the Coder agent.
- Always run `harness validate .` before declaring success.
- Always record a trace (success or failure).
