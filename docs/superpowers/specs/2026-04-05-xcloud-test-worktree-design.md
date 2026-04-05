# Design: xcloud-test — Worktree Isolation for PR Code Analysis

**Date:** 2026-04-05
**Scope:** `~/.claude/skills/xcloud-test/SKILL.md`
**Problem:** Direct `gh pr checkout` in the main session switches the active branch, disrupting in-progress work regardless of which directory Claude Code is running from.

---

## Problem Statement

When `xcloud-test` needs to read PR source files (not just the diff), Step 0.6 instructs running `gh pr checkout <PR_NUMBER>` directly in the main session. This causes two problems:

1. **Wrong directory:** When invoked from `agentic-skills` instead of the xCloud project, `gh pr checkout` operates on the wrong repo or fails entirely.
2. **Branch switching:** Even from within the xCloud project, `gh pr checkout` switches the active branch, disrupting whatever work is in progress.

The pipelined path (Steps 1+2 parallel) already solves this correctly using `isolation="worktree"` on the analysis agent. The non-pipelined fallback and Step 0.6 do not.

---

## Solution: Approach A — Worktree Agent Mandatory for ALL Code Reading

All PR source code access happens inside a worktree-isolated agent, never in the main session. Both the pipelined and non-pipelined paths use agents; only the timing differs (parallel vs. sequential).

---

## Changes

### 1. Global Rule (Behavior Rules section)

Add to the "Behavior Rules" section:

> **PR source code is always accessed via a worktree-isolated agent — never directly in the main session.** Running `gh pr checkout` in the main session switches the active branch and breaks working state regardless of which directory Claude Code is running from.

### 2. Step 0.6 — Remove "Local Checkout" subsection

- **Rename** section from "Local Checkout & Server Deployment" → "Server Deployment (Per PR)"
- **Remove** the "Local Checkout" subsection (the `gh pr checkout` and `git stash` commands)
- **Add** a one-line note at the top:

  > **Note:** PR source code is accessed via a worktree-isolated agent — see "Pipelined Analysis + Deployment" or Step 1 (non-pipelined). Never check out PR branches directly in the main session.

- Server Deployment subsection is unchanged (SSH commands run on a remote server).

### 3. Step 1 — Non-Pipelined Fallback

Replace the current note ("If pipelined analysis was used, skip Step 1") with:

> **If pipelined analysis was used:** skip Step 1 entirely — analysis results are already available. Proceed to Step 3 (Browser Setup).
>
> **If you skipped the pipelined path:** spawn a worktree analysis agent first (template below), then use its output for Steps 1.1–1.4. Do NOT read PR files directly from the main session.

Add agent template:

```
Agent(
  description="Analyze PR #<N>",
  isolation="worktree",
  prompt="Analyze PR #<N> for xcloud-test QA.
  1. gh pr checkout <N>
  2. gh pr diff <N> --name-only
  3. Read changed files fully (controllers, models, policies, Vue, migrations)
  4. Cross-reference with references/xcloud-feature-map.md
  5. Run cross-feature impact search (grep all consumers of changed code)
  6. Return structured analysis:
     - Changed files + what changed in each
     - Affected features and UI pages
     - Cross-feature consumers found
     - PR summary (what / why / how)
     - Suggested test categories
     - Business logic observations (five-lens review from Step 1.4)"
)
```

Steps 1.1–1.4 remain as-is — they serve as the checklist the agent follows internally.

---

## What Does NOT Change

- The pipelined analysis agent (already correct — uses `isolation="worktree"`)
- Server Deployment in Step 0.6 (SSH commands are fine)
- Steps 1.1–1.4 content (used as agent instructions, not removed)
- All other steps

---

## Success Criteria

- `gh pr checkout` never appears as a direct command outside of an agent prompt
- Non-pipelined Step 1 always spawns a worktree agent before reading any files
- The skill works correctly whether Claude Code is invoked from the xCloud directory or any other directory
