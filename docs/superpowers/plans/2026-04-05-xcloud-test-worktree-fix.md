# xcloud-test Worktree Isolation Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all direct `gh pr checkout` usage from the main session in `xcloud-test/SKILL.md`, replacing with worktree-agent patterns so PR code analysis never disrupts the active branch.

**Architecture:** Three targeted edits to one file. No new files. No tests (markdown skill file). Each task is a single `Edit` call followed by a verification read and commit.

**Tech Stack:** Markdown, Edit tool, git

---

## File Structure

| File | Action | What changes |
|------|--------|--------------|
| `~/.claude/skills/xcloud-test/SKILL.md` | Modify (3 edits) | Step 0.6 rename + remove Local Checkout subsection; Step 1 note replaced with worktree agent template; Behavior Rules gets new rule |

---

### Task 1: Remove "Local Checkout" from Step 0.6

**Files:**
- Modify: `~/.claude/skills/xcloud-test/SKILL.md` lines 215–230

- [ ] **Step 1: Apply the edit**

Replace this block (lines 215–230):

```
### 0.6 Local Checkout & Server Deployment (Per PR)

#### Local Checkout

Before testing each PR, check out the branch locally so the Read/Grep/Explore tools work on the PR's source code:

```bash
gh pr checkout <PR_NUMBER>
```

If the checkout fails due to uncommitted local changes, stash them first:

```bash
git stash && gh pr checkout <PR_NUMBER>
```

#### Server Deployment
```

With:

```
### 0.6 Server Deployment (Per PR)

> **Note:** PR source code is accessed via a worktree-isolated agent — see "Pipelined Analysis + Deployment" or Step 1 (non-pipelined). Never check out PR branches directly in the main session.

#### Server Deployment
```

- [ ] **Step 2: Verify the edit**

Read lines 215–235 of the file and confirm:
- Section title is "0.6 Server Deployment (Per PR)" (no "Local Checkout &")
- The note about worktree-isolated agents is present
- The `gh pr checkout` bash blocks are gone
- "#### Server Deployment" follows immediately after the note

- [ ] **Step 3: Commit**

```bash
git add ~/.claude/skills/xcloud-test/SKILL.md
git commit -m "fix: remove direct gh pr checkout from Step 0.6 in xcloud-test"
```

---

### Task 2: Fix Step 1 — Add Worktree Agent Template for Non-Pipelined Fallback

**Files:**
- Modify: `~/.claude/skills/xcloud-test/SKILL.md` line 312

- [ ] **Step 1: Apply the edit**

Replace this single line (line 312):

```
> **Note:** If pipelined analysis was used (agent from the section above), skip Step 1 entirely — the analysis results are already available. Proceed to Step 3 (Browser Setup) since deployment is also done.
```

With:

```
> **If pipelined analysis was used:** skip Step 1 entirely — the analysis results are already available. Proceed to Step 3 (Browser Setup) since deployment is also done.
>
> **If you skipped the pipelined path:** spawn a worktree analysis agent first (template below), then use its output for Steps 1.1–1.4. Do NOT read PR files directly from the main session — `gh pr checkout` in the main session switches your active branch.
>
> ```
> Agent(
>   description="Analyze PR #<N>",
>   isolation="worktree",
>   prompt="Analyze PR #<N> for xcloud-test QA.
>   1. gh pr checkout <N>
>   2. gh pr diff <N> --name-only
>   3. Read changed files fully (controllers, models, policies, Vue, migrations)
>   4. Cross-reference with references/xcloud-feature-map.md
>   5. Search for all consumers of changed code (grep controllers, services, jobs, policies, Vue)
>   6. Return structured analysis:
>      - Changed files + what changed in each
>      - Affected features and UI pages
>      - Cross-feature consumers found
>      - PR summary (what / why / how)
>      - Suggested test categories
>      - Business logic observations (five-lens review from Step 1.4)"
> )
> ```
```

- [ ] **Step 2: Verify the edit**

Read lines 310–335 of the file and confirm:
- "If pipelined analysis was used" path is present and says to skip Step 1
- "If you skipped the pipelined path" path is present with the worktree agent template
- The agent template includes `isolation="worktree"` and `gh pr checkout <N>` inside the prompt string
- `gh pr checkout` does NOT appear as a bare bash command outside of the agent prompt

- [ ] **Step 3: Commit**

```bash
git add ~/.claude/skills/xcloud-test/SKILL.md
git commit -m "fix: add worktree agent template to Step 1 non-pipelined fallback"
```

---

### Task 3: Add Global Rule to Behavior Rules Section

**Files:**
- Modify: `~/.claude/skills/xcloud-test/SKILL.md` lines 1282–1287

- [ ] **Step 1: Apply the edit**

In the Behavior Rules section, add a new bullet after the existing last rule (after "Cross-reference previous QA reports"):

Append to the bullet list (after line 1287):

```
- **PR source code is accessed via worktree agents only** — never run `gh pr checkout` in the main session. Direct checkout switches the active branch and breaks working state regardless of which directory Claude Code is running from. All PR file reading happens inside an `isolation="worktree"` agent.
```

- [ ] **Step 2: Verify the edit**

Read lines 1278–1295 of the file and confirm:
- The new bullet is present at the end of the Behavior Rules list
- It contains the phrase "never run `gh pr checkout` in the main session"
- No other bullets were accidentally removed or duplicated

- [ ] **Step 3: Confirm no stray `gh pr checkout` remains outside agent prompt blocks**

Run this search across the skill file:

```bash
grep -n "gh pr checkout" ~/.claude/skills/xcloud-test/SKILL.md
```

Expected output: every matching line should be inside an agent `prompt=` string (indented with spaces inside a code block). Any bare `gh pr checkout` line at column 0 or in a bash block outside an agent prompt is a bug — fix it before committing.

- [ ] **Step 4: Commit**

```bash
git add ~/.claude/skills/xcloud-test/SKILL.md
git commit -m "fix: add worktree-only rule to Behavior Rules in xcloud-test"
```

---

### Task 4: Sync to Working Copy

The skill is maintained in both `~/.claude/skills/xcloud-test/` and the `agentic-skills` repo. Sync the edited file.

- [ ] **Step 1: Copy the updated SKILL.md to the repo**

```bash
cp ~/.claude/skills/xcloud-test/SKILL.md \
   /Users/reduanmasud/Documents/Projects/agentic-skills/skills/xcloud-test/SKILL.md
```

- [ ] **Step 2: Verify the copy matches**

```bash
diff ~/.claude/skills/xcloud-test/SKILL.md \
     /Users/reduanmasud/Documents/Projects/agentic-skills/skills/xcloud-test/SKILL.md
```

Expected: no output (files identical).

- [ ] **Step 3: Commit the sync**

```bash
cd /Users/reduanmasud/Documents/Projects/agentic-skills
git add skills/xcloud-test/SKILL.md
git commit -m "chore: sync xcloud-test SKILL.md — worktree isolation fix"
```
