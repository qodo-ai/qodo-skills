---
name: pr-agent-pro-resolver
description: Autonomous bug-fix and feature-implementation agent for pr-agent-pro. Reads a Linear ticket or free-text task, implements the solution, tests via the /testing skill, opens a PR, and updates the ticket.
author: Qodo Git Code Review team
compatible_agents:
  - claude-code
  - cursor
  - codex
---

# pr-agent-pro-resolver

Autonomous end-to-end resolver for bugs and features in the pr-agent-pro repository. This skill orchestrates the full lifecycle: understand the task, implement a fix, validate with tests, and ship a PR.

## Input

Either:
- A **Linear ticket identifier** (e.g., `PROJ-123`)
- A **free-text description** of a bug or feature

## Progress Tracking

**Before starting work, create a todo list to track progress through the flow.** Use the agent's task/todo system (e.g., `TodoWrite` in Claude Code) to create one task per step. When building the list, follow the `/testing` skill's workflow and its **Double Gate 🌉 principle** — test planning is the first testing task of the work, and test verification is the closing gate:

1. "Understand the task" — fetch ticket or parse free-text, create branch
2. "Research & Plan" — 2.1: parallel research (Slack + PR history); 2.2: create todo list; 2.3: present plan and get user approval
3. "Implement the solution" — code the fix/feature
4. "Tests" — invoke `/testing` and follow its workflow
5. "Verify testing requirements" — ensure they were met per the testing skill's standards
6. "Ship" — commit, push, open PR, update Linear ticket

Mark each task as in-progress when you start it and completed when done. If an iteration loop sends you back to Step 3, update the existing tasks rather than creating new ones (e.g., mark Step 3 back to in-progress).

This gives the user visibility into where you are in the flow at all times.

## Flow

### Step 1: Understand the Task

1. **If a Linear ticket was provided:**
   - Invoke the `/linear` skill (`skills/linear/SKILL.md`) to fetch the ticket's title, description, comments, labels, and priority
   - Extract the core problem statement and any reproduction steps

2. **If free-text was provided:**
   - Parse the description to identify the problem, expected behavior, and any relevant context

3. **Create a new git branch from `main`:**
   - Linear ticket: `fix/PROJ-123-short-description` or `feat/PROJ-123-short-description`
   - Free-text: `fix/short-description` or `feat/short-description`

### Step 2: Research & Plan

Before writing any code, gather deep context and create an implementation plan. This step runs **two parallel research tasks**, then synthesizes findings into a plan for user approval.

#### 2.1: Parallel Research Tasks

Launch both tasks simultaneously:

| Task | Purpose | Method |
|------|---------|--------|
| **Slack Knowledge Mining** | Find hidden context from R&D-to-customer communications about this issue | Search Slack for discussions, escalations, workarounds, and known edge cases related to the problem. Look for threads where engineers explained the issue to customers or internal stakeholders. |
| **Component & PR History Analysis** | Understand how the relevant code evolved and what edge cases exist | Identify the components/modules involved in the issue. Use `/codebase-context` and git history to trace how the code changed over time. Find related PRs, understand why changes were made, and extract edge cases that previous developers handled. |

**Slack Knowledge Mining checklist:**
- Search for the ticket ID, error messages, or feature name in Slack
- Look for customer-facing explanations from R&D
- Identify workarounds or temporary fixes mentioned
- Note any "gotchas" or non-obvious behaviors discussed

**Component & PR History Analysis checklist:**
- Identify all files/modules touched by the issue
- Use `git log -p --follow` on key files to trace evolution
- Use `/pr-knowledge-query` to find related PRs
- Extract patterns: What edge cases did previous PRs handle? What broke before?
- Note any "TODO" comments or technical debt markers

#### 2.2: Create Todo List

Based on the research findings, create a structured todo list of implementation tasks:
- Break down the solution into discrete, testable units
- Order tasks by dependency (what must be done first)
- Flag any risks or unknowns discovered during research

#### 2.3: Present Plan to User

**Before proceeding to implementation, show the user:**

1. **Context Summary**: Key findings from Slack and PR history research
2. **Component Map**: Which files/modules will be modified
3. **Implementation Plan**: The ordered todo list with brief rationale for each task
4. **Risks & Edge Cases**: Known gotchas from research that the implementation must handle
5. **Estimated Scope**: Number of files, rough complexity assessment

**Wait for user approval before proceeding to Step 3.** The user may:
- Approve the plan as-is
- Request modifications to the approach
- Provide additional context or constraints

### Step 3: Implement the Solution

Write the fix or feature using standard coding tools. The agent has full discretion on approach, but **must follow the approved plan from Step 2**.

**Work through the todo list created in Step 2.2:**
- Mark each task as in-progress when you start it
- Mark as completed when done
- If you discover new requirements, add them to the todo list

**Internal documentation (`docs/qodo2/`):**
Use the `docs/qodo2/` directory as a primary data source. It contains detailed documentation on agents (issues, compliance, context, deduplicator, conversion, history-context, orchestrator, tools system), benchmarks, infrastructure, and usage guides. Ensure your implementation aligns with the existing architecture and patterns.

### Step 4: Tests

Invoke the `/testing` skill (`skills/testing/SKILL.md`) and follow its workflow. The skill owns all testing detail — test type selection, planning, writing, quantity, and the canonical example. Do not duplicate those internals here.

### Step 5: Verify Testing Requirements (Back Gate)

Ensure the testing requirements were met **according to the testing skill's standards** (its verification gate and final report). If they were not met, iterate on the implementation — go back to **Step 3**.

### Step 6: Ship

1. **Commit** all changes to the branch created in Step 1
2. **Push** the branch to remote
3. **Open a PR** with:
   - **Task summary**: What was the task (ticket link or description)
   - **Solution summary**: What was implemented and why
   - **Release-please label** (mandatory): Add exactly one of the following labels to the PR based on the nature of the change. These labels drive automated changelog generation and versioning:
     - `bug` — bug fix
     - `enhancement` — new feature or improvement to existing functionality
     - `breaking` — breaking change
     - `build` — build system or CI changes
     - `chore` — maintenance, refactoring, or other non-user-facing changes
4. **Update Linear ticket** (if applicable) by invoking the `/linear` skill:
   - Post a comment on the ticket with the PR link
   - Update ticket status to "In Review" (or equivalent)

## Iteration Logic

Steps 3 → 5 form an iterative loop. Step 2 (Research & Plan) does not iterate — if the plan needs changes, the user provides feedback during approval.

```
Step 2 (research & plan) → User Approval
                                ↓
Step 3 (implement) → Step 4 (tests) → Step 5 (verify per testing skill)
    ▲                                           │
    └───── if requirements not met ◄────────────┘
```

**Soft cap: 5 iterations** of the Step 3→5 loop. If the agent cannot resolve failures within 5 iterations, stop and report the current state to the user with:
- What was attempted
- Which testing requirements are still unmet and why
- Suggested next steps

## Sub-skill Reference

| Skill | Path | Step | Required |
|-------|------|------|----------|
| `/linear` | `skills/linear/SKILL.md` | 1, 6 | If ticket provided |
| `/slack-search` | (MCP or API) | 2.1 | Yes (parallel) |
| `/codebase-context` | `skills/codebase-context/SKILL.md` | 2.1 | Yes (parallel) |
| `/pr-knowledge-query` | `skills/pr-knowledge-query/SKILL.md` | 2.1 | Yes (parallel) |
| `/testing` | `skills/testing/SKILL.md` | 4, 5 | Yes |
