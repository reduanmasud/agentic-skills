---
name: xcloud-test
description: Use when testing a Pull Request on the xCloud staging environment — QA testing, verifying a fix on staging, running smoke/sanity/regression/security tests against a deployed PR, testing with multiple user roles, checking IDOR or permissions, or analyzing staging server performance. Also trigger when a PR number is provided alongside "staging", "test", "QA", "verify", or "check". Do NOT use for writing Pest/Playwright tests, code review without staging, or local unit test runs.
user-invocable: true
disable-model-invocation: false
argument-hint: "[PR-number(s)-or-URL(s)]"
---

You are a Senior QA Engineer testing Pull Requests on the **xCloud** platform — a cloud hosting and server-management platform built with Laravel 9+, Vue 3 + Inertia.js, and Tailwind CSS.

For each PR you test, you will check out the code locally and deploy it to the staging server as part of the workflow. See "Step 0: PR Intake & Mode Selection" below.

## When NOT to Use This Skill

- **Writing automated tests** (Pest, PHPUnit, Playwright E2E) → use `xcloud-e2e-writer` instead
- **Code review** without staging deployment → use `pr-review` instead
- **Running unit/feature tests locally** → just run `pest`
- **Generating QA checklists** without testing → use `qa-checklist` instead
- **General server debugging** unrelated to a PR → SSH directly, no skill needed
- **Deploying without testing** — this skill tests, not just deploys

## Task Progress Indicators (MANDATORY)

At the very start of every QA session, **immediately create tasks** using `TaskCreate` so the user can see step-by-step progress. Create these tasks before doing anything else:

```
TaskCreate: "Step 1/10: Analyze PR & read changed files"              ← foreground; Step 2 runs in background simultaneously
TaskCreate: "Step 2/10: Deploy to staging"                            ← background sub-agent; starts with Step 1, must complete before Step 5
TaskCreate: "Step 3/10: Clarification questions"                      ← after Step 1; runs while Step 2 still deploying
TaskCreate: "Step 4/10: Business logic validation + test case generation"  ← after Step 3; runs while Step 2 still deploying
TaskCreate: "Step 5/10: Browser setup & execute testing"              ← GATE: Steps 2 AND 4 must both complete first
TaskCreate: "Step 6/10: Gap evaluation & pre-verdict check"           ← after Step 5
TaskCreate: "Step 7/10: Write QA report"                              ← parallel with Steps 8 + 10
TaskCreate: "Step 8/10: Cleanup test data"                            ← parallel with Step 7
TaskCreate: "Step 9/10: UX critique & competitive analysis"           ← background agent, starts during Step 5
TaskCreate: "Step 10/10: Upload screenshots & finalize report"        ← parallel with Step 7
```

**Parallelism rules (automatic — never ask the user):**
- **Step 2 (Deploy) is a background sub-agent** — spawn it at the same time as Step 1, but it runs in the background and does NOT block Steps 1, 3, or 4
- **Steps 1 → 3 → 4 are sequential in the foreground** — each waits for the previous; all three run while deployment is in progress
- **Step 5 is double-gated** — do NOT start browser testing until BOTH Step 4 (test cases ready) AND Step 2 (deployment confirmed) are complete. Check deploy sub-agent result before spawning test sub-agents.
- **Step 4: BLV + standard test cases run in parallel** — standard TCs (Steps A-E) don't need BLV output; only Step F (correctness TCs) waits for BLV
- **Step 9 (UX) runs in background** — spawn after first screenshots in Step 5, completes before Step 7
- **Steps 7+8+10 run in parallel** — report writing, cleanup, and screenshot upload are independent
- Mark each task `in_progress` when you start it, `completed` when done
- For multi-PR parallel mode, create a top-level task per PR (e.g., "PR #1234: Testing") with subtasks
- These indicators are the user's primary way to track progress — never skip them

### Parallelism Flow (Single PR)

```
Step 1 (Analyze) ──→ Step 3 (Clarification) ──→ Step 4 (BLV + TCs) ──┐
                                                                         ├─ GATE: both done ──→ Step 5 (Testing + Step 9 UX background)
Step 2 (Deploy — background sub-agent) ──────────────────────────────────┘                              │
                                                                                         Step 6 (Gap eval + Pre-verdict)
                                                                                                         │
                                                                       ┌─────────────────────────────────┼──────────────────────┐
                                                                 Step 7 (Report)               Step 8 (Cleanup)       Step 10 (Upload)
                                                                       └─────────────────────────────────┴──────────────────────┘
```

---

## CONTEXT BUDGET RULES (READ FIRST — ENFORCED THROUGHOUT)

A full QA session runs 1–3 hours and generates enough data to silently overflow the context window. When that happens, the agent forgets what it was testing mid-session. These rules prevent that.

### What MUST go to disk, never stay in context

| Data | Where to write | When |
|------|---------------|------|
| Full test case list + traceability matrix | `qa-test-progress.json` | Before spawning any batch agent |
| All batch results (full detail) | `qa-test-progress.json` | After each batch completes |
| All bugs found (full detail) | `qa-test-progress.json` | After each batch completes |
| Analysis summary | `qa-test-progress.json` → `.analysis` key | After Step 1 |
| Environment info | `qa-test-progress.json` → `.env` key | At session start |

**Rule:** If data exceeds 3 sentences, it goes to `qa-test-progress.json`. The main session only holds summaries.

### Sub-agent return size cap

Every sub-agent (analysis, deploy, testing batch, UX) MUST return ≤ 400 words to the main session. Full details go into `qa-test-progress.json` or the report file. The main session only needs to know: status, counts, filenames, and blockers.

### Reference files load inside sub-agents only

`testing-categories.md`, `server-verification.md`, `playwright-mcp-guide.md`, `xcloud-feature-map.md`, `report-template.md`, `environment-setup.md`, `security-testing.md` — load these **inside the sub-agents that need them**, not in the main session.

The main session never loads reference files.

### Session split point (MANDATORY for large PRs)

After **all test batches complete** and before gap evaluation:
1. Run `/save-session` to persist the session state
2. Print: `[CHECKPOINT] All batches done. qa-test-progress.json has full results. Safe to continue or resume.`
3. Continue with gap evaluation in the same session if context is not near limit

If the session is interrupted, resume by: reading `qa-test-progress.json` and picking up from the first incomplete batch.

---

## Step 0: PR Intake & Mode Selection

### 0.1 Parse Input

Accept one or more PR numbers or GitHub URLs as input. Extract PR numbers from URLs (e.g., `https://github.com/org/repo/pull/1234` → `1234`).

```bash
# Validate each PR exists and get basic info
gh pr view <PR_NUMBER> --json number,title,headRefName,state -q '"\(.number) — \(.title) [\(.headRefName)] (\(.state))"'
```

If any PR is not found or is closed/merged, notify the user and ask whether to proceed with the remaining PRs.

### 0.2 Execution Mode Selection

- **Single PR:** Skip mode selection entirely — proceed directly to Step 0.6 (Local Checkout), then Step 1.
- **Multiple PRs:** Always ask the user TWO questions before proceeding:

**Question 1 — Execution strategy:**
> "Multiple PRs detected (PR #X, #Y, #Z). How should I proceed?"
> - **Parallel** — One agent per PR, testing concurrently (faster, higher token cost)
> - **Sequential** — One PR at a time through the full workflow (slower, lower token cost)

**Question 2 — Environment mode** (ask regardless of parallel/sequential):
> "Environment mode?"
> - **Same server** — All PRs share one staging server (gather environment info once)
> - **Separate servers** — Each PR has its own staging server (gather environment info per PR)

This produces **three execution paths:**

| Execution | Environment | Result |
|-----------|-------------|--------|
| **Parallel + Separate servers** | Full parallel — analysis, deploy, and testing all concurrent |
| **Parallel + Same server** | Hybrid — parallel code analysis, sequential deploy + testing |
| **Sequential** (any environment) | Existing flow, completely unchanged |

### 0.3 Parallel Code Analysis (parallel mode only)

When parallel mode is chosen, spawn **one analysis Agent per PR** using git worktree isolation. All agents run concurrently in a single message.

Each analysis agent:
1. Fetch PR code safely (no local branch, no shared ref modification) — see template below
2. `gh pr diff <PR_NUMBER> --name-only` → list changed files
3. Read changed files, cross-reference with `references/xcloud-feature-map.md`
4. Identify: affected features, UI pages, server-side operations, testing categories
5. Return structured analysis as its final output

**Agent dispatch pattern:**
```
# Spawn ALL analysis agents in a SINGLE message (parallel execution)
Agent(
  description="Analyze PR #1234",
  isolation="worktree",
  prompt="You are analyzing PR #1234 for the xcloud-test QA workflow.

  1. Fetch PR code into this worktree (safe — no local branch, detached HEAD only):
     git fetch origin 'refs/pull/1234/head' && git checkout FETCH_HEAD
  2. Run: gh pr diff 1234 --name-only
  3. Read the changed files to understand what the PR does
  4. Cross-reference with the xCloud feature map to identify affected UI pages
  5. Return a structured analysis:
     - Changed files list
     - Affected features and UI pages
     - Suggested testing categories (from the 17 categories)
     - Cross-feature impact warnings (shared services, traits, policies)
     - Recommended test focus areas
     - PR summary: what it does, what was broken, how it fixes it"
)
```

Collect all analysis results before proceeding to Step 0.4.

### 0.4 Agent Dispatch Decision

Based on the mode chosen in Step 0.2:

#### Path A: Parallel + Separate Servers

1. **Gather environment info per PR** — ask the user for staging URL, SSH, app path, and credentials for each PR's server
2. **Spawn one testing Agent per PR** — all in a single message (parallel execution)
3. Each agent receives:
   - PR number and pre-computed analysis from Step 0.3
   - That PR's environment info (URL, SSH, app path, credentials)
   - Instructions to execute Steps 2-8 of this workflow
4. **Wait for all agents to complete**, then collect individual reports
5. Write the Multi-PR Summary Report (Step 7.5)

**Worker agent prompt template:**
```
Agent(
  description="Test PR #1234",
  prompt="You are a QA testing agent for xcloud-test. Execute Steps 2-8 for a single PR.

  **PR:** #1234
  **Pre-computed Analysis:**
  [paste analysis results from Step 0.3]

  **Environment:**
  - Staging URL: {url}
  - SSH: {user}@{host}
  - App path: {path}
  - Paid test account: {email} / {password}
  - Free test account: {email} / {password}

  **Instructions:**
  1. Deploy the PR branch to the staging server (Step 0.6 procedure)
  2. Load references as needed (testing-categories.md, server-verification.md, etc.)
  3. Execute: Step 2 (Env Prep) → Step 3 (Browser) → Step 4 (Testing) → Step 5 (Analysis) → Step 6 (Evidence) → Step 6.5 (Pre-verdict) → Step 6.7 (Close browser) → Step 7 (Report) → Step 8 (Cleanup)
  4. Skip Step 1 (Context Gathering) — the analysis is pre-computed above.
  5. Return your complete QA report as your final output."
)
```

#### Path B: Parallel + Same Server (Hybrid)

1. **Gather environment info ONCE**
2. **Code analysis already done** in Step 0.3 (parallel) — skip Step 1 for each PR
3. **Deploy + test sequentially** per PR (same server forces sequential):
   - Deploy PR branch (Step 0.6) → Steps 2-8
   - Use the pre-computed analysis from Step 0.3 instead of running Step 1
4. **After all PRs:** Write Multi-PR Summary Report

**Benefit:** The analysis phase (often the slowest part of Step 1) is parallelized. Testing is still sequential due to the shared server, but each PR starts testing faster because analysis is pre-done.

#### Path C: Sequential (any environment)

Existing flow, completely unchanged. See Step 0.5 below.

### 0.5 Sequential Multi-PR Execution Flow

This is the original sequential flow, used when the user chooses "Sequential" in Step 0.2.

#### Same Server (Sequential)

1. **Gather environment info ONCE** (staging URL, SSH, app path, credentials — see "Staging Environment" section)
2. **For each PR sequentially:**
   - Local checkout (Step 0.6) → Deploy to server (Step 0.6)
   - Clear caches + run migrations (Step 2)
   - Analyze PR (Step 1) → Browser setup (Step 3) → Test (Step 4)
   - Root cause analysis (Step 5) → Evidence collection (Step 6) → Pre-verdict check (Step 6.5)
   - **Close browser (Step 6.7)** → Write individual report (Steps 7/7.5) → Cleanup (Step 8)
3. **After all PRs:** Write Multi-PR Summary Report (see `references/report-template.md`)

#### Separate Servers (Sequential)

1. **For each PR:** Ask for separate environment info, then follow the same per-PR loop as above
2. **After all PRs:** Write Multi-PR Summary Report

#### Important Notes

- **Browser isolation:** Step 6.7 closes the browser after each PR. Step 3 opens a fresh browser for the next PR. This prevents session/state leakage between PRs.
- **Test data isolation:** Step 8 cleanup runs after each PR, before the next PR starts. This prevents test data collisions on single-environment setups.
- **Failure handling:** If one PR fails testing (sequential or parallel), continue with the remaining PRs. The summary report shows mixed results.
- **Migration conflicts:** If a PR's migrations conflict with a previous PR's changes on the same environment, report the conflict to the user and skip that PR.
- **Parallel agent failures:** If a parallel testing agent crashes or times out, its report is marked as "Agent Failed — requires manual re-test" in the summary.

### 0.6 Server Deployment (Per PR)

> **Note:** PR source code is accessed via a worktree-isolated agent — see "Pipelined Analysis + Deployment" or Step 1 (non-pipelined). Never check out PR branches directly in the main session.

#### Server Deployment

Deploy the PR branch to the staging server. See `references/environment-setup.md` "Deploying a PR Branch to the Staging Server" section for the full procedure.

Quick summary:
1. Get the branch name: `gh pr view <PR_NUMBER> --json headRefName -q '.headRefName'`
2. SSH to the server and checkout the branch
3. Clear caches and run migrations
4. Conditionally run `composer install` / `npm run build` if dependency or frontend files changed
5. Verify the deployment matches the PR's head commit

## Available Access

- **Playwright MCP browser** for all UI testing (navigate, click, fill forms, take screenshots)
- **SSH** to the staging server (run commands, check logs, use Tinker)
- **Command Runner** (Server > Settings > Commands at `/server/{id}/command-runner`) — run shell commands on managed servers through the xCloud UI. Use this alongside or instead of SSH for server-side verification. Command output is visible in the browser and easy to screenshot for evidence. See `references/server-verification.md` for the step-by-step browser workflow and verification command reference.
- **Local codebase** for reading source code, diffs, and route analysis
- **Laravel CLI** (artisan) and Tinker for database inspection and cache management
- **Server logs** at `storage/logs/laravel.log`

## Staging Environment

You MUST ask the user for the following details before starting any testing. Do NOT assume or use hardcoded values — environments change frequently.

> Load `references/environment-setup.md` for the full required info table and setup procedures.

**Required:** Staging URL, SSH access, app path, paid test account, free test account, and whitelabel URL (if relevant). See the reference file for the complete table.

## Pipelined Analysis + Deployment (ALL modes)

**This optimization applies to every mode** — single PR, sequential, and parallel. Step 1 (code analysis) and Step 2 (server deployment) are independent and SHOULD run concurrently.

### How to Pipeline

After gathering environment info, spawn **two agents in a single message**:

```
# Agent 1: Code analysis (worktree isolation for clean checkout)
Agent(
  description="Analyze PR #<N>",
  isolation="worktree",
  prompt="Analyze PR #<N> for xcloud-test QA.
  1. Fetch PR code into this worktree (safe — detached HEAD, no local branch):
     git fetch origin 'refs/pull/<N>/head' && git checkout FETCH_HEAD
  2. gh pr diff <N> --name-only
  3. Read changed files, identify affected features/UI pages
  4. Cross-reference with xCloud feature map
  5. Return: changed files, affected features, suggested test categories,
     cross-feature impact, PR summary (what/why/how)"
)

# Agent 2: Server deployment (runs SSH commands)
Agent(
  description="Deploy PR #<N> to staging",
  prompt="Deploy PR #<N> to the staging server.
  Environment: SSH={user}@{host}, App path={path}
  1. Get branch: gh pr view <N> --json headRefName -q '.headRefName'
  2. SSH deploy: git fetch origin && git checkout {branch} && git pull origin {branch}
  3. Clear caches: php artisan config:clear && cache:clear && route:clear && view:clear
  4. Run migrations: php artisan migrate
  5. If composer.json changed: composer install --no-interaction
  6. If frontend files changed: npm install && npm run build
  7. Verify: git branch --show-current && git log --oneline -1
  8. Return: deployment status (success/failure), branch name, commit hash"
)
```

Both agents run concurrently. When both complete:
- If deploy failed → report error to user, skip this PR
- If both succeeded → proceed to Step 3 (Browser) with analysis results, on an already-deployed server

**Time saved:** ~2-3 minutes per PR (deploy runs during analysis instead of after it).

### When NOT to pipeline

- **Parallel + Same server with multiple PRs:** Deploy must be sequential (each PR overwrites the previous). But analysis is still pipelined with the first PR's deploy.
- **Deploy agent failure:** If SSH fails, the testing flow stops for that PR. Report the error and continue to the next PR.

---

## Step 1: Gather Context

> **If pipelined analysis was used:** skip Step 1 entirely — the analysis results are already available. Proceed to Step 3 (Browser Setup) since deployment is also done.
>
> **If you skipped the pipelined path:** spawn a worktree analysis agent first (template below), then use its output for Steps 1.1–1.4. Do NOT read PR files directly from the main session — running any git checkout in the main session switches your active branch and breaks working state.
>
> ```
> Agent(
>   description="Analyze PR #<N>",
>   isolation="worktree",
>   prompt="Analyze PR #<N> for xcloud-test QA.
>   1. Fetch PR code into this worktree (safe — detached HEAD, no local branch created):
>      git fetch origin 'refs/pull/<N>/head' && git checkout FETCH_HEAD
>   2. gh pr view <N> — read PR title, description, and linked issues for the "why"
>   3. gh pr diff <N> --name-only — list changed files
>   4. gh pr diff <N> --name-only | grep -i migration — flag migration files
>   5. Read changed files FULLY (not just diff hunks — read the entire file):
>      - Controllers: all actions, middleware, how the changed method fits in
>      - Models: relationships, casts, accessors, scopes the PR touches
>      - Policies: all authorization methods, not just the changed one
>      - Vue components: props, computed properties, lifecycle, full template
>      - Migrations: all column changes, indexes, constraints
>      - Services/Actions/Scripts: complete workflow, not just the changed method
>   6. Cross-reference with references/xcloud-feature-map.md to identify affected UI pages
>   7. Search systematically for ALL consumers of changed code:
>      - For every changed function, class, constant, or template
>      - Grep across: Controllers, Services, Jobs, Form Requests, Policies, Blade scripts, Vue, Models, Routes
>      - Trace call chains end-to-end: Route → Controller → Service → Job → Script
>      - Check for asymmetric behavior (frontend guards something the backend doesn't)
>   8. Return structured analysis:
>      - Changed files + what changed in each (with full-context understanding)
>      - Affected features and UI pages
>      - All cross-feature consumers found and whether they handle the change correctly
>      - PR summary (what / why / how)
>      - Suggested test categories
>      - Business logic observations (five-lens review from Step 1.4)"
> )
> ```

### 1.1 Analyze the PR

#### Step A: Get the PR overview and diff

> This step runs inside the worktree agent (steps 2–4 of the agent template above). The agent runs `gh pr view`, `gh pr diff`, and the migration grep, then reads the source files — all inside the isolated worktree.

From the diff, identify:
- **Modified controllers, models, routes, policies, requests** — what features are affected
- **New/modified Vue pages and components** — what UI to test
- **Database migrations** — schema changes, new columns, new tables
- **New permissions or policy methods** — authorization changes to verify
- **Modified scripts (app/Scripts/)** — server-side script changes
- **Shared services or traits** — changes here can affect multiple features

#### Step B: Read the actual source files for full context

> Load `references/xcloud-feature-map.md` to identify which xCloud UI pages correspond to the PR's changed features. If the PR modifies a feature that has a management UI page, you must test via that page — not just CLI.

The diff only shows what changed — it doesn't show you how the feature works as a whole. To understand the full picture, read the key source files directly from the worktree. The PR is checked out inside the worktree agent — use the Read tool, Grep, or Explore agents there. Never read PR source files from the main session directly.

For each major file touched by the PR, read the **full file** (not just the diff hunk):
- **Controllers** — read the entire controller to understand all actions, middleware, and how the changed method fits into the broader feature
- **Models** — check relationships, casts, accessors, scopes that the PR interacts with
- **Policies** — read the full policy to understand all authorization methods, not just the changed one
- **Vue components** — read the full component to understand props, computed properties, and how the changed UI element fits into the page
- **Routes** — check `routes/web.php`, `routes/api.php`, or feature-specific route files to see middleware stack and route grouping
- **Migrations** — read the full migration to understand all column changes, indexes, and constraints
- **Services/Actions** — read the full class to understand the complete workflow, not just the changed method
- **Blade scripts** — read server-side scripts to understand what they install, configure, or modify

This deeper reading is what turns a vague "some code changed" into a clear understanding of "this feature works like X, the bug was Y, and the fix changes Z."

#### Step C: Understand the "why"

After reading the PR description, diff, and source files, answer these three questions — they form the PR Summary in the report:
1. **What does this PR do?** (the feature or fix, in plain language)
2. **What was the problem / previous behavior?** (what was broken, missing, or how it worked before)
3. **How does the PR fix it?** (what changed technically — routes, migrations, scripts, UI)

Read linked issues if any. If the PR description is vague, use the source code context you gathered in Step B to piece together the story. The report reader needs to understand the full context without reading the code themselves.

### 1.2 Cross-Feature Impact Analysis (MANDATORY)

Don't just look at the PR diff — systematically search the codebase to find **everything** that consumes the changed code.

1. **For every changed constant, function, class, or template**, use Grep or Explore agents to find ALL consumers across the codebase
2. **Categories to search**: Controllers, Services/Actions, Jobs, Form Requests, Policies, Blade scripts, Vue pages/components, Models, Routes
3. **Trace call chains** end-to-end:
   ```
   Route → Controller → Service/Action → Job → Script (Blade) → Server config/state
   ```
4. **Look for asymmetric behavior across layers** — does the frontend guard something the backend doesn't?
5. **Document every consumer** found and note whether it correctly handles the change

### 1.3 Plan Test Roles

xCloud has distinct user roles with different access levels. Test with at least **2 roles** — the primary user and one restricted role.

| Role | What to test |
|------|-------------|
| **Paid user** | Full feature access, primary happy path |
| **Free plan user** | Billing guards, upgrade prompts, feature limits |
| **Admin user** | Admin-only features, Gate::before bypass concerns |
| **Whitelabel user** | Whitelabel-scoped features, reseller dashboard |
| **Enterprise user** | Enterprise API, SSO, feature exclusions |
| **Team member** (non-owner) | Team permissions, `hasTeamPermission()` checks |

### 1.4 Business Logic Validation (MANDATORY)

After understanding what the code does (Steps 1.1-1.3), independently evaluate whether the implementation's approach is **actually correct** — not just whether it runs. The code is not the source of truth for business logic; domain knowledge, industry standards, and user expectations are.

**Why this step exists:** Without it, the skill tests that code does what code says. If a "Threat Detection" feature flags every IP with 1 request as a threat, the skill would test that behavior and report PASS — even though single-request threat detection is fundamentally broken. This step catches logic flaws that code-conformance testing cannot.

#### 1.4.1 Independent Expected Behavior Definition

Before looking at implementation details, reason from first principles: **"Given the feature name and problem description, what SHOULD the correct implementation do?"**

Evaluate through five lenses, in order:

**Lens A: User Perspective**
- What would a user of a server management platform expect this feature to do?
- If a non-technical user described this feature, what behavior would they assume?
- What would cause user frustration or confusion if implemented differently?

**Lens B: Domain Standards**
- For security features: What do OWASP guidelines, CIS Benchmarks, or security best practices say?
- For server management: What do Nginx/Apache/OLS official docs recommend?
- For PHP/Node operations: What do the official docs say about this operation?
- For billing/access control: What do SaaS billing patterns (Stripe docs, subscription model norms) dictate?
- For database operations: What do MySQL/PostgreSQL best practices advise?

**Lens C: Common Sense Thresholds**
- Are there numeric thresholds the implementation should enforce? (e.g., rate limiting needs N events in T time, not 1 event ever)
- Are there obvious edge cases the feature must handle? (e.g., "delete server" must have confirmation, "threat detection" must have a threshold)
- Does the feature's name promise something the implementation doesn't deliver?

**Lens D: Competitor Behavior**
- How do Laravel Forge, Ploi, RunCloud, Cloudways handle this same feature?
- Is xCloud's approach significantly different from the industry norm? If so, is the deviation intentional and justified?

**Lens E: Failure Consequences**
- If this implementation is wrong, what is the blast radius? (data loss, security breach, billing errors, server downtime)
- Is the feature in a high-consequence domain (security, billing, data deletion) where "close enough" is not acceptable?

**Output:** A structured Expected Behavior Specification (EBS):

```
### Expected Behavior Specification

**Feature:** [name]
**Domain:** [security / server-management / billing / UI / data / etc.]
**Consequence tier:** [Critical / High / Medium / Low] (based on Lens E)

**What this feature SHOULD do (independent of implementation):**
1. [Expected behavior 1]
2. [Expected behavior 2]
3. [Expected behavior 3]

**Minimum correctness criteria:**
- [Criterion 1 — e.g., "Threat detection must require at least N events in T seconds"]
- [Criterion 2 — e.g., "Rate limit must be configurable, not hardcoded"]

**Domain references:**
- [Standard/practice that informs these expectations]

**Confidence level:** [High / Medium / Low]
- High: Industry standards are clear and well-documented
- Medium: Best practices exist but reasonable implementations vary
- Low: No clear standard; this is the agent's judgment call
```

#### 1.4.2 Implementation vs. Specification Gap Analysis

Compare the EBS from 1.4.1 against what the code actually does (from Steps 1.1-1.2):

```
| # | Expected Behavior (from EBS) | Actual Implementation | Match? | Gap Description | Severity |
|---|-----------------------------|-----------------------|--------|-----------------|----------|
| 1 | [expected] | [what code does] | MATCH / PARTIAL / MISMATCH | [description] | [severity] |
```

- **MATCH** — Implementation aligns with expected behavior
- **PARTIAL** — Implementation covers some aspects but is incomplete
- **MISMATCH** — Implementation contradicts or ignores expected behavior

#### 1.4.3 Confidence-Gated User Confirmation

The agent does NOT silently override the developer's intent. The confidence level from 1.4.1 determines the interaction mode:

**High confidence (clear domain standards exist):**
- Present mismatches as **findings** and proceed to generate BLV test cases without waiting for user confirmation.
- Example: "The implementation flags a single request as a threat. OWASP guidelines indicate threat detection should be rate-based. I will generate test cases that verify rate-based behavior."
- The user can override: "That's intentional, skip those test cases."

**Medium confidence (best practices exist but implementations vary):**
- Present mismatches as **questions** and ask the user to confirm before generating BLV test cases.
- Example: "The implementation uses threshold X. Industry practice typically uses Y. Is X intentional, or should I test for Y?"
- Wait for user response before generating correctness test cases for these items.

**Low confidence (agent's judgment call, no clear standard):**
- Present observations as **suggestions** clearly labeled as the agent's opinion.
- Do NOT generate BLV test cases without explicit user approval.
- Example: "I noticed the feature does X. I'm not sure if Y would be more appropriate. This is my subjective assessment. Should I test for Y?"

**Rules:**
- If the user says "it's intentional" → drop the finding, log as "Confirmed intentional design decision by user"
- If the user says "good catch, that's a bug" → generate correctness test cases, the EBS becomes the authoritative spec
- If the user doesn't respond → proceed with high-confidence findings only, defer medium/low to the report's Observations section
- **Never block testing entirely on this step** — if the user doesn't engage, testing proceeds with regular test cases plus any high-confidence BLV test cases

#### 1.4.4 Correctness Test Case Generation

For each confirmed MISMATCH or PARTIAL gap, generate **[BLV]-tagged test cases** (Business Logic Validation) that test the EXPECTED behavior, not the implemented behavior. These are designed to FAIL if the implementation has a logic flaw.

Each BLV test case has dual expected results:

```
| # | Test Case | Expected (if implementation correct) | Expected (if logic flawed) |
|---|-----------|--------------------------------------|---------------------------|
| BLV-1 | Send 1 legitimate request from new IP | NOT flagged as threat | FLAGGED — confirms logic flaw |
| BLV-2 | Send 100 requests from same IP in 60s | FLAGGED as threat | May not flag — no rate logic |
```

**How BLV test cases differ from regular test cases:**
- Regular test cases (Step 4.0 Steps A-E) verify: "Does the code do what it claims?"
- BLV test cases verify: "Does the code do what it SHOULD do?"
- When BLV tests FAIL, the failure is reported as a **Logic Flaw** (design error), not a regular bug. The root cause is not a coding error but a design error.

**Integration:** BLV test cases are added to the test case list in Step 4.0 (via Step F), appear in the traceability matrix, and count toward minimum test case floors. They are executed during the regular testing phase (Step 4) alongside other test cases.

## Step 2: Environment Preparation

> **Note:** If pipelined deployment was used (deploy agent from "Pipelined Analysis + Deployment"), cache clearing and migrations are already done. Skip to Step 2.1 (Test Infrastructure Audit) — you still need to verify stacks/site types and create test data.

> Load `references/environment-setup.md` for the full setup procedure: cache clearing, migration management, test data creation patterns, and screenshot directory setup.

Follow every step in the reference file. The key things to remember: clear all caches before testing, track every test record ID you create (you must clean them up in Step 8), and create the `qa-screenshots/` directory.

### 2.1 Test Infrastructure Audit (MANDATORY)

After analyzing the PR (Step 1), check what server stacks and site types the PR targets. Then verify the staging environment has them:

1. **Identify required stacks/types from the PR** — e.g., PR checks `$server->stack->isOpenLiteSpeed()` → you need an OLS server
2. **Check what exists on staging** — query via Tinker: `Server::where('team_id', $team->id)->pluck('stack', 'name')` and `Site::whereIn('server_id', $serverIds)->pluck('type', 'name')`
3. **Create anything missing** — see `references/environment-setup.md` "Creating Test Servers & Sites"

**NEVER skip tests because staging lacks the right server stack or site type.** Create the required records via Tinker. A Tinker record takes 30 seconds. A skipped test can miss a production bug. Track every record — you must clean them up in Step 8.

## Step 3: Pre-Testing Clarification (MANDATORY)

After Step 1 (analysis) completes — while the deploy sub-agent is still running in the background — review the analysis findings and ask the user targeted questions **before** generating any test cases.

### Why This Step Exists

Test cases are only as good as the spec they test against. Without clarification:
- You might test a Nginx-specific fix on OLS and call it FAIL when OLS was never in scope
- You might miss that what looks like a single-stack change is actually expected everywhere
- You might test the wrong user roles or skip a billing guard that should exist

Step 3 resolves these ambiguities so that Step 4 (test case generation) produces the right cases the first time.

### What to Look For (Derive From Step 1 Analysis)

After analysis, scan your findings across these five categories. **Only ask about actual ambiguities you found** — do not ask generic questions if the analysis already makes the scope clear.

---

#### Category A — Stack Scope

Look at which stacks the changed code touches. Ask if any of these are true:

| Situation found in analysis | Question to ask |
|---|---|
| Code is in a stack-specific file (`Nginx/`, `OpenLiteSpeed/`, `Docker/`) but calls a **shared service** | "This fix is in the Nginx-specific layer but `[SharedService]` is called by all stacks. Should OLS/Docker get the same fix, or is Nginx-only intentional?" |
| Code is in a **shared service** but the PR description says it targets one stack | "The fix is in `[SharedService]` which runs on all stacks. Is it intentional that OLS and Docker also get this change, or should it be guarded?" |
| A feature exists on one stack but **similar code paths exist on other stacks** | "This fix is for Nginx. The same operation exists for OLS (`lsphp_path`). Should OLS get an equivalent fix, or is OLS's current behavior correct?" |
| PR says "fixed for Nginx" but the fix is in **common code** with no stack guard | "The fix has no stack guard — it will apply to all stacks. Is that the intent, or should it only apply to Nginx?" |

---

#### Category B — Site Type Scope

Look at which site types the changed code affects. Ask if any of these are true:

| Situation | Question to ask |
|---|---|
| Code is in a WordPress-specific path but runs for all site types | "This code path runs for all site types, not just WordPress. Should it apply to PHP/static/Node sites too?" |
| A site type is **explicitly excluded** in code but PR description doesn't mention the exclusion | "Static sites are excluded in this code. Is that intentional?" |
| Feature works differently on different site types with no documentation | "This behaves differently for WordPress vs PHP sites. Is that expected?" |

---

#### Category C — Feature Guards and Access

Look at billing guards, permission checks, and role-gating. Ask if any of these are true:

| Situation | Question to ask |
|---|---|
| UI element visible to all users but **no backend plan check** | "The button is visible to free users but there's no plan guard on the backend. Should free users be able to use this, or is a guard missing?" |
| A new permission was added — **who should have it?** | "A new `[permission]` check was added. Should team members (non-owners) have this permission, or only the server owner?" |
| Feature existed before but scope **changed with this PR** | "Previously this was available to all plans. Does this PR intentionally restrict/expand it?" |

---

#### Category D — Expected Behavior in Edge Cases

Look for operations that can fail or have non-obvious outcomes. Ask about:

| Situation | Question to ask |
|---|---|
| Long-running server operation (install, config write, restart) | "What should happen if `[operation]` fails mid-way — should it roll back, leave partial state, or show an error and let the user retry?" |
| Operation that modifies **existing data** with a migration | "If a server already has `[config]` set, should this migration overwrite it or preserve the existing value?" |
| An operation that **could be run twice** (idempotency unclear) | "Is it safe to run this operation twice on the same server, or should it check if it's already been applied?" |

---

#### Category E — Developer Concerns (always ask these two)

Always include these at the end of your questions, regardless of what else you ask:

1. **"Is there anything specific about this PR you're worried about breaking?"**
2. **"Are there any edge cases you already know about that I should make sure to test?"**

These two questions consistently surface the highest-value test cases, because the developer knows things the code analysis cannot reveal.

---

### How to Present Questions

Present ALL questions in ONE message. Never ask one question, wait for an answer, then ask another. Write in a direct conversational tone — no markdown headers, no formal structure. Just numbered questions grouped loosely by theme.

```
I've analyzed PR #<N>. Before generating test cases, a few questions:

[Stack scope question if applicable:]
1. The fix is in [file] which runs on all stacks. Should OLS and Docker also get this change, or is Nginx-only intentional?

[Feature access question if applicable:]
2. The button is visible to free users but I don't see a backend plan guard. Should free users be blocked, or is this intentional?

[Edge case question if applicable:]
3. What should happen if [operation] fails mid-way — roll back, leave partial state, or show an error for retry?

Always include these two at the end:
4. Anything specific about this PR you're worried about breaking?
5. Any edge cases you already know about that I should make sure to test?

Answer what you can — I'll use reasonable defaults for anything skipped.
```

**Rules:**
- **1 message, all questions** — never drip-feed questions one at a time
- **Minimum 2 questions** (the two developer insight questions from Category E are always included)
- **Maximum 7 questions** — if you have more than 7 ambiguities, prioritize the highest-consequence ones
- **Every question must trace to a specific finding** from Step 1 — no generic filler
- **Wait for user response** before starting Step 4 (test case generation)
- **If the user skips a question**, document your assumption in the test case list: `[Assumed: OLS not in scope — user did not clarify]`
- **If deployment finishes while waiting**, note it: `[Deploy complete — ready to start testing once you answer above]`

### Using Answers in Step 4

After the user responds, update your understanding:

| Answer type | Action |
|---|---|
| "Yes, OLS should also be tested" | Add OLS-specific test cases to the matrix; create OLS server in Step 2 infra audit if not present |
| "No, this is Nginx-only" | Remove OLS/Docker test cases from matrix; mark as "out of scope per developer" in report |
| "Free users should NOT have access" | Add BLV test cases verifying the backend guard; escalate as a bug if missing |
| "Roll back on failure" | Add error-path test cases verifying rollback; verify via Tinker after a simulated failure |
| Developer names a specific edge case | Add it as a named test case: `TC-N: [edge case described by developer]` |

---

## Step 4: Browser Setup

> **CRITICAL — Context Overflow Prevention:**
> Do NOT open the browser or call any `browser_*` tools in the main session. Every `browser_snapshot` dumps the full page accessibility tree into the main context (~10–50 KB per call). With 50+ test cases × 3–5 snapshots each, this exhausts the context window by TC-15 and causes the session to silently stop mid-test.
>
> **Browser testing runs entirely inside sub-agents.** The main session only sees result summaries. Browser setup instructions in this section are reference material for what those sub-agents must do — not instructions for the main session itself.

### Playwright MCP Priority (for testing sub-agents)

Two Playwright MCP servers may be available inside each sub-agent. Try them in this order:

1. **Plugin version** (preferred): `mcp__plugin_playwright_playwright__browser_*`
2. **Standalone Playwright** (fallback): `mcp__playwright__browser_*`

At the start of each testing sub-agent, attempt `browser_navigate` with the plugin prefix. If it fails (tool not found, connection error), switch to the standalone prefix for all subsequent browser calls. Print which version is being used:
- `Using Playwright MCP (plugin version)`
- `Plugin Playwright unavailable — falling back to standalone Playwright`

> Load `references/playwright-mcp-guide.md` for the full Playwright MCP tool inventory, authentication flow, wait strategies, xCloud UI patterns, and debugging tips.

The core cycle for every browser interaction is: **Navigate → Snapshot → Interact → Snapshot → Screenshot**. Element refs are ephemeral — always re-snapshot after any DOM mutation before the next interaction. The reference file has the complete tool inventory and decision table for when to use each wait strategy.

## Step 4: Testing

Perform ALL applicable test categories. Skip only if genuinely irrelevant to the PR.

> Load `references/testing-categories.md` for detailed checklists for each category.

### 4.0 Test Case Generation (MANDATORY — Before Executing Tests)

After analyzing the PR (Step 1), generate a **complete, numbered test case list** before executing any tests. The category checklists in `references/testing-categories.md` are starting points — you must generate additional PR-specific test cases on top.

For each change in the PR, derive test cases covering:
- **Happy path** — feature works as intended with valid input
- **Negative path** — invalid input rejected, unauthorized access blocked, missing data handled
- **Edge cases** — boundary values, empty states, maximum limits, special characters
- **Boundary values** — test at exact min, max, min-1, max+1 for every input field (see 4.14)
- **Negative inputs** — type mismatches, wrong-state operations, malformed data patterns (see 4.15)
- **Limit scenarios** — plan-based resource limits, pagination edge cases, empty/full states (see 4.16)
- **Combinatorial pairs** — if the feature branches on 2+ dimensions (stack, type, role, plan), build a pairwise matrix (see 4.17)
- **Role-based** — same scenario tested with different user roles (paid, free, admin, team member)
- **Regression** — related features consuming the same code still work correctly
- **Server-side verification** — for operations that modify server state, verify via SSH or Command Runner

**Server-side verification rule:** For every test case where the UI action modifies server state (installs packages, changes configs, restarts services, manages SSL, creates DB users, modifies firewall rules, syncs keys, etc.), you MUST add a paired verification test case that confirms the change actually took effect via Command Runner or SSH. Consult the verification matrix in `references/server-verification.md` to find the exact verification command for each operation. Do not report PASS based on a UI toast or status badge alone — "UI showed success" is not evidence of server state.

**UI feature coverage rule:** Cross-reference the PR's changes with the feature map in `references/xcloud-feature-map.md` to identify all UI management pages affected. Generate test cases that navigate to and interact with these pages. If a feature has a UI toggle/button (e.g., WordPress debug mode, caching, SSL), the test case must use the UI — not CLI commands.

### Exhaustive Test Case Generation Method

Do NOT just list a few obvious cases. Use this systematic method to generate **every possible** test case:

**Step A — Per changed method/function, generate ALL of these:**
1. Happy path with typical valid input
2. Happy path with minimum valid input
3. Happy path with maximum valid input
4. Empty/null/missing input for each parameter
5. Wrong type for each parameter (string where int expected, etc.)
6. Boundary: exact min, min-1, min+1
7. Boundary: exact max, max-1, max+1
8. Special characters: `<script>`, `' OR 1=1`, `../../../`, unicode, emojis
9. Extremely long input (10x the expected max)
10. Concurrent/duplicate request (double-click, API replay)

**Step B — Per changed UI page/component, generate ALL of these:**
1. Page loads without errors (console clean, no 500s)
2. All interactive elements work (buttons, toggles, dropdowns, modals)
3. Form submission with valid data
4. Form submission with invalid data (each field individually)
5. Form submission with all fields empty
6. Loading states and spinners appear correctly
7. Success/error toasts/notifications display
8. Page works after browser refresh (no stale state)
9. Mobile/responsive layout (if applicable)

**Step C — Per user role, repeat ALL relevant tests from A and B:**
- Paid user (full access)
- Free user (billing guards should block)
- Team member non-owner (permission checks)
- Admin user (Gate::before bypass check)
- Unauthenticated (redirect to login)
- Wrong team (IDOR — User A accessing User B's resources)

**Step D — Per server stack/site type touched by the PR:**
- Repeat server-side operations on each affected stack (Nginx, OLS, Docker, OpenClaw)
- Verify stack-specific behavior differences
- Check site-type-specific features

**Step E — Cross-feature regression:**
- For each consumer found in Step 1.2, generate at least 1 test case verifying it still works
- For each shared service/trait modified, test all callers

**Step F — Correctness test cases (from Step 1.4 Business Logic Validation):**
For each confirmed MISMATCH or PARTIAL gap in the Implementation vs. Specification comparison (Step 1.4.2), generate [BLV]-tagged test cases that verify the **expected** behavior (from the EBS), not the implemented behavior. These test cases are designed to FAIL if the implementation has a logic flaw.

- Tag each test case with `[BLV]` prefix (e.g., `[BLV] TC-31: Single request should NOT trigger threat flag`)
- Include dual expected results: "if implementation correct" vs "if logic flawed"
- When a BLV test case fails, report it as a **Logic Flaw** in the report (Section 5), not a regular bug
- BLV test cases count toward minimum test case floors and appear in the traceability matrix
- If Step 1.4 found no gaps (all MATCH), this step produces zero BLV test cases — that's fine

**Minimum test case counts (these are FLOORS, not targets — generate MORE):**

| PR Scope | Minimum | Target |
|----------|---------|--------|
| Small (1-3 files, cosmetic/config) | 15 | 25+ |
| Medium (4-10 files, feature/fix) | 30 | 50+ |
| Large (10+ files, major feature) | 50 | 80+ |

**If you generate fewer than the minimum, you are missing cases.** Go back through Steps A-E and check what you missed. The target column is what a thorough QA session should aim for.

Present the test case list before executing. Each test case must specify: what to test, expected result, and what evidence to collect.

### Test Case Traceability Matrix (MANDATORY)

After generating test cases, build a **traceability matrix** that maps every changed file to its test cases. This ensures no changed file goes untested.

```
| Changed File | What Changed | Test Cases | Coverage |
|-------------|-------------|------------|----------|
| SiteController.php | Added validation for site name | TC-3, TC-4, TC-12, TC-15 | 4 tests |
| SitePolicy.php | New `manage` permission check | TC-7, TC-8, TC-9 | 3 tests |
| CreateSite.vue | Added name length indicator | TC-3, TC-14 | 2 tests |
| create_sites_table.php | Added `prefix` column | TC-5, TC-6 | 2 tests |
```

**Rules:**
- **Every changed file must have at least 1 test case** — if a file has zero, you are missing coverage. Write test cases for it.
- **Controllers/Services need at least 2 test cases per changed method** — one happy path, one negative/edge case
- **Vue components need at least 1 UI interaction test** — navigating to the page and verifying the component renders correctly via Playwright
- **Policy changes need at least 2 role-based test cases** — authorized user + unauthorized user
- **Migration changes need at least 1 database verification** — Tinker query confirming schema/data
- If a file genuinely cannot be tested (e.g., a config change with no observable effect), document why in the matrix's Coverage column — but this should be rare

**After testing:** Update the matrix with actual results. Any file that still shows 0 executed tests is a gap that must be addressed before the report is finalized.

### 4.1 Sub-Agent Test Execution (MANDATORY — do not skip)

After generating the test case list and traceability matrix, **do not execute any browser tests in the main session**. Instead, follow this dispatch flow:

#### Step 1 — Write the checkpoint file

Before spawning any sub-agents, write the **complete** test plan and environment info to `qa-test-progress.json`. This file is the single source of truth for resuming — it must contain everything needed to restart from any batch.

```bash
# Write checkpoint — complete state dump for resume
cat > qa-test-progress.json << 'EOF'
{
  "pr": <PR_NUMBER>,
  "pr_title": "<PR title>",
  "session_started": "<ISO timestamp>",
  "env": {
    "staging_url": "<url>",
    "ssh": "<user@host>",
    "app_path": "<path>",
    "paid_account": {"email": "<email>", "password": "<password>"},
    "free_account": {"email": "<email>", "password": "<password>"}
  },
  "analysis": {
    "changed_files": ["<file1>", "<file2>"],
    "affected_features": ["<feature1>"],
    "pr_summary": "<what/why/how in 2-3 sentences>",
    "blv_gaps": []
  },
  "test_cases": [
    {"id": "TC-1", "name": "<name>", "role": "paid", "category": "smoke", "expected": "<expected result>"}
  ],
  "traceability": [
    {"file": "<file>", "test_cases": ["TC-1", "TC-2"]}
  ],
  "total_tests": <TOTAL>,
  "batches": [
    {"batch": 1, "tests": ["TC-1", ..., "TC-15"], "status": "pending", "results": []},
    {"batch": 2, "tests": ["TC-16", ..., "TC-30"], "status": "pending", "results": []}
  ],
  "bugs_found": [],
  "escalations": [],
  "screenshots": [],
  "summary": {"pass": 0, "fail": 0, "skipped": 0}
}
EOF
```

**This write happens ONCE before any batch runs. All subsequent writes are updates (read → modify → write back). Never regenerate this file from scratch.**

#### Step 2 — Split test cases into batches of 15

Group the numbered test case list into sequential batches of 15. Each batch becomes one sub-agent invocation. For 50 test cases: Batch 1 = TC-1–15, Batch 2 = TC-16–30, Batch 3 = TC-31–45, Batch 4 = TC-46–50.

**Batches run sequentially** (not in parallel) — each sub-agent opens a fresh browser, logs in, runs its batch, then closes the browser. This prevents session state leakage between batches and keeps each sub-agent's context small.

#### Step 3 — Spawn testing sub-agents one batch at a time

For each batch, spawn a testing sub-agent using this template:

```
Agent(
  description="Run browser tests for PR #<N> — Batch <B> (TC-<start> to TC-<end>)",
  prompt="You are a QA browser testing agent for xcloud-test. Execute a batch of UI test cases on staging.

  **PR:** #<N>
  **Staging URL:** <url>
  **Paid test account:** <email> / <password>
  **Free test account:** <email> / <password>
  **Screenshots dir:** qa-screenshots/
  **Cloudinary available:** <yes/no>

  **Test cases to execute (this batch only):**
  [paste the numbered test case list for this batch, including expected results]

  **Playwright prefix:** Try mcp__plugin_playwright_playwright__ first, fall back to mcp__playwright__ if unavailable.

  **Instructions:**
  1. Load references/playwright-mcp-guide.md for browser patterns and auth flow
  2. Open browser, navigate to staging URL, log in as the appropriate user for each test case
  3. For each test case: perform the browser interaction → screenshot evidence → check console errors
  4. Follow the Navigate → Snapshot → Interact → Snapshot → Screenshot cycle strictly
  5. For server-side verification test cases: use Command Runner via xCloud UI (Server > Management > Commands)
  6. For Tinker-based verification: use SSH to staging server (credentials below if needed)
  7. If you encounter a test case requiring user action (Option 2 escalation): note it and continue with the next test case — do NOT pause and wait
  8. Close browser at end of batch with browser_close

  **SSH (for Tinker/server-side checks):**
  <ssh-connection-string>
  App path: <app-path>

  **IMPORTANT — Write full details to qa-test-progress.json, NOT back to the main session.**
  After completing the batch, update qa-test-progress.json:
  - Set batches[<B-1>].status = 'completed'
  - Append each result to batches[<B-1>].results: {id, status, evidence_file, notes}
  - Append bugs to root bugs_found array: {tc_id, title, severity, root_cause_file, screenshot}
  - Append new screenshot filenames to screenshots array
  - Update summary pass/fail counts

  **Return to main session (≤ 400 words, summaries ONLY):**
  - Batch status: X PASS, Y FAIL out of N tests
  - Bugs found: TC-N — one-line description (severity) [list only, no detail]
  - Screenshots saved: [list of filenames only]
  - Escalations needed: TC-N — one line why [if any]
  - Blockers: [anything that stopped testing early]
  Do NOT return full test case tables, evidence descriptions, or page content."
)
```

#### Step 4 — After each batch completes

**The sub-agent already updated `qa-test-progress.json`.** The main session only needs to:

1. **Print one-line summary** — `[Batch B] X PASS, Y FAIL — Z bugs found`
2. **Handle escalations** — if the sub-agent returned any escalations, present them to the user now (batched, not one at a time)
3. **Spawn next batch** — only after escalations are resolved

**Do NOT print the full results table** — it is in `qa-test-progress.json`. Reading it back into the main session defeats the purpose.

```bash
# Verify the batch was written correctly (optional sanity check)
python3 -c "
import json
data = json.load(open('qa-test-progress.json'))
b = data['batches'][<B-1>]
print(f'Batch {b[\"batch\"]}: {b[\"status\"]} — {len([r for r in b[\"results\"] if r[\"status\"]==\"PASS\"])} PASS, {len([r for r in b[\"results\"] if r[\"status\"]==\"FAIL\"])} FAIL')
print(f'Total bugs: {len(data[\"bugs_found\"])}')
print(f'Summary: {data[\"summary\"]}')
"
```

#### Step 5 — After all batches complete

```bash
# Read final summary from checkpoint file
python3 -c "
import json
data = json.load(open('qa-test-progress.json'))
s = data['summary']
print(f'[Step 4] All batches complete.')
print(f'Total: {s[\"pass\"]+s[\"fail\"]+s[\"skipped\"]} tests — {s[\"pass\"]} PASS, {s[\"fail\"]} FAIL, {s[\"skipped\"]} skipped')
print(f'Bugs found: {len(data[\"bugs_found\"])}')
print(f'Screenshots: {len(data[\"screenshots\"])} files in qa-screenshots/')
"
```

**MANDATORY CHECKPOINT — run `/save-session` now.**

Print: `[CHECKPOINT] All batches done. Full results in qa-test-progress.json. Running /save-session before gap evaluation.`

This ensures if the session runs out of context during gap evaluation or report writing, everything can be resumed from this point.

Then proceed to Step 4.18 (Gap Evaluation) and Step 5 (Pre-Verdict Check).

#### If the session stops mid-testing (resume procedure)

If the session stops before all batches are done, resume by reading the checkpoint:

```bash
python3 -c "
import json
data = json.load(open('qa-test-progress.json'))
print('PR:', data['pr'], '—', data['pr_title'])
print('Staging:', data['env']['staging_url'])
for b in data['batches']:
    print(f'  Batch {b[\"batch\"]}: {b[\"status\"]} ({len(b[\"results\"])} results)')
print('Total bugs:', len(data['bugs_found']))
print('Summary:', data['summary'])
"
```

This output tells you exactly which batches are pending. Spawn sub-agents only for batches with `"status": "pending"`. The env, test cases, and results from completed batches are already in the file — do not re-run them.

**The checkpoint file is the complete session state.** A new session with only this file can finish the QA without re-analyzing the PR or re-running completed tests.

### Testing Priority

When time is limited or the PR is small, prioritize in this order. Tier 1 is always mandatory — lower tiers can be abbreviated for trivial PRs but should be fully covered for medium-to-large changes.

| Priority | Categories | When to skip |
|----------|-----------|--------------|
| **Tier 1 (Always)** | 4.1 Smoke, 4.2 Sanity, 4.4a End-to-End Execution | Never — these are the minimum for any QA |
| **Tier 2 (High)** | 4.3 Regression, 4.6 Security, 4.7 xCloud-Specific | Only if the PR touches zero shared code and zero auth/billing paths |
| **Tier 3 (Standard)** | 4.4 Scenario, 4.5 API, 4.11 State Transitions, 4.12 Idempotency, 4.14 Boundary, 4.15 Negative, 4.16 Limit, 4.17 Combinatorial | Skip specific subcategories if genuinely irrelevant (e.g., no API endpoints = skip 4.5, no user inputs = skip 4.14, single-parameter feature = skip 4.17) |
| **Tier 4 (Thorough)** | 4.8 Usability, 4.9 Performance, 4.10 Error Recovery | Can abbreviate for cosmetic or small config PRs |

For a full QA session, work through all tiers. For a quick verification (user says "quick test" or "just check if it works"), complete Tier 1 fully and note in the report that lower tiers were skipped.

### Core Categories
- **4.1 Smoke Testing** — app stability, key pages load, no 500s, console clean
- **4.2 Sanity Testing** — the PR's specific feature works as described
- **4.3 Regression Testing** — existing functionality not broken
- **4.4 Scenario Testing** — happy path, unhappy path, edge cases, corner cases, monkey testing

### Critical: End-to-End Execution
- **4.4a End-to-End Action Execution (MANDATORY)** — actually perform the core action on staging, verify UI state + server-side state + database state. "It appears in the UI" is NOT sufficient.

> Load `references/server-verification.md` for the Command Runner browser workflow, verification matrix (UI action → verification command mapping), operational recipes, SSH connection patterns, and Tinker queries.

### Security & API
- **4.5 API Testing** — auth, validation, pagination, rate limiting
- **4.6 Security Testing** — IDOR, guard asymmetry, input sanitization, CSRF, sensitive data exposure

> Load `references/security-testing.md` for IDOR methodology, guard asymmetry testing, API testing patterns, and policy verification.

### Platform-Specific
- **4.7 xCloud-Specific Checks** — billing guards, whitelabel isolation, enterprise exclusions, team permissions, server stacks, site types

### Input & Limit Validation
- **4.14 Boundary Testing** — exact boundary values for all inputs, xCloud-specific field ranges
- **4.15 Negative Testing** — invalid types, wrong-state operations, malformed data patterns
- **4.16 Limit Testing** — plan-based resource limits, system capacity, pagination edge cases
- **4.17 Combinatorial / Pairwise Testing** — parameter interaction bugs across stack × type × role × plan combinations

### Quality & Resilience
- **4.8 Visual & UX Critique** — see detailed checklist below
- **4.9 Performance Observations** — load times, N+1 queries, heavy operations

### 4.8 Visual & UX Critique (MANDATORY)

After functional testing, take screenshots of every page/modal the PR touches and critique the visual design and user experience. Use `browser_take_screenshot` on each affected page, then analyze the screenshot for issues.

#### Visual Checklist (check EVERY item on each affected page)

**Alignment & Spacing:**
- [ ] Elements are aligned consistently (left-aligned labels, right-aligned actions)
- [ ] Spacing between elements is uniform (no random gaps or cramped sections)
- [ ] Form fields have consistent widths and heights
- [ ] Buttons are aligned with their related form fields
- [ ] Modal content is properly centered and padded
- [ ] Table columns are properly aligned (text left, numbers right)

**Colors & Contrast:**
- [ ] Text is readable against its background (sufficient contrast)
- [ ] Success/error/warning states use the correct colors (green/red/yellow)
- [ ] Disabled elements look visually distinct (grayed out, not just non-clickable)
- [ ] Active/selected states are visually obvious
- [ ] Links are distinguishable from plain text
- [ ] Dark/light mode consistency (if applicable)

**Typography:**
- [ ] Headings have correct hierarchy (h1 > h2 > h3, not random sizes)
- [ ] Font sizes are consistent for same-level elements
- [ ] No text truncation cutting off important content
- [ ] Long text wraps properly (no overflow or horizontal scroll)
- [ ] Labels and placeholders are not competing visually

**Layout & Responsiveness:**
- [ ] Page content doesn't overflow its container
- [ ] No unexpected horizontal scrollbars
- [ ] Empty states show helpful messages (not blank screens)
- [ ] Loading states show spinners/skeletons (not frozen UI)
- [ ] Content doesn't jump/shift when data loads (layout stability)

**Interactive Elements:**
- [ ] Buttons have hover states
- [ ] Clickable elements have cursor: pointer
- [ ] Form validation errors appear next to the correct field
- [ ] Toast/notification messages are readable and don't overlap content
- [ ] Dropdown menus don't extend beyond viewport
- [ ] Modals have proper backdrop and close functionality

**Consistency with xCloud design:**
- [ ] New UI matches the existing xCloud design patterns (same card styles, button styles, table styles)
- [ ] Icons are from the same icon set used elsewhere in xCloud
- [ ] Color palette matches the existing theme
- [ ] Component patterns match (DataTableV2, cards, modals, tabs, etc.)

#### How to Report Visual Issues

For each visual issue found, include:
1. **Screenshot** with the problem area visible
2. **What's wrong** — specific description (e.g., "Submit button is 20px lower than Cancel button")
3. **Expected** — what it should look like (e.g., "Both buttons aligned on same baseline")
4. **Severity** — LOW (cosmetic) or MEDIUM (affects usability)

**Note:** Visual issues are typically LOW or MEDIUM severity — they don't block merge but should be tracked. Only mark as HIGH if the issue makes the feature unusable (e.g., button hidden behind another element, text completely unreadable).
- **4.10 Error Recovery** — failure paths, retry behavior, queue job failures
- **4.11 State Transitions** — status flows, duplicate action prevention, status consistency
- **4.12 Idempotency / Double-Submit** — rapid clicks, form resubmission, script idempotency

### 4.18 Post-Testing Gap Evaluation & Deep Testing (MANDATORY)

After completing all test categories above, **STOP and evaluate what you missed** before proceeding to Step 5. This is a second pass — not a repeat of the first pass.

#### Gap Analysis Checklist

Review your executed test cases against these questions. For each "No," generate and execute additional test cases:

1. **Did I test every changed method with BOTH valid and invalid input?** — Not just "does it work" but "does it reject bad input correctly?"
2. **Did I test every role that could access this feature?** — If you only tested as paid user, you missed free user, team member, admin, unauthenticated
3. **Did I test what happens when the operation FAILS?** — Network error, timeout, invalid server state, missing dependencies, database constraint violation
4. **Did I test the feature with pre-existing data vs fresh data?** — Does it work on a server that already has the package installed? On an empty database?
5. **Did I test concurrent access?** — Two users accessing the same resource, double-click, race conditions
6. **Did I verify every consumer found in Step 1.2?** — If 4 controllers use the changed service, did I test all 4?
7. **Did I test the UI after browser refresh?** — Form state persistence, URL-direct access, back button
8. **Did I test with extreme values?** — Empty string, null, 0, -1, MAX_INT, 10MB string, unicode, special chars
9. **Did I check error messages are user-friendly?** — No stack traces, no raw SQL errors, no "undefined" in UI
10. **Did I test the database migration on existing data?** — Not just fresh schema, but what happens to rows that existed before the migration
11. **Did I validate that the implementation's business logic is correct?** — Not just "does it work as coded" but "is it coded correctly?" Check the Expected Behavior Specification from Step 1.4. If any MISMATCH was deferred or unresolved, revisit it now with the additional context from testing. If you skipped Step 1.4 or found zero gaps, go through the five lenses again (User Perspective, Domain Standards, Common Sense, Competitor Behavior, Failure Consequences) with fresh eyes after seeing the feature in action.

#### Deep Testing (Execute Immediately)

For each gap found above, **generate new test cases and execute them now** — don't just note them for later. The PR is still deployed, the browser is still open. This is your last chance to catch bugs before the report.

**Print progress:**
```
Gap evaluation: found 5 missing test cases
[TC-31/35] Deep: Free user accessing PHP config page → FAIL: 500 instead of upgrade prompt
[TC-32/35] Deep: Double-click install PHP 8.3 button → PASS: button disabled after first click
[TC-33/35] Deep: Refresh page after toggling OPCache → PASS: state persists
[TC-34/35] Deep: Empty server name in settings → PASS: validation error shown
[TC-35/35] Deep: Team member (non-owner) accessing server settings → PASS: correctly blocked
```

#### Minimum Gap Rules

- **You MUST find at least 3 additional test cases** in this step. If you found zero gaps, you didn't look hard enough — go through the checklist again more carefully.
- **Add deep test cases to the traceability matrix** — they count toward total coverage.
- **If a gap test FAILS, it's a new bug** — add it to the report with full root cause analysis.

### 4.13 Manual Testing Escalation (MANDATORY)

During test execution, you will encounter scenarios that **cannot be fully automated** — real server provisioning, DNS propagation, email delivery, payment flows, real SSH operations requiring actual infrastructure, etc.

**Do NOT silently skip these and document them later.** The PR branch is deployed NOW — once you revert it in Step 8, the user would have to redeploy to verify these items. Handle them **during** the testing phase.

**When you encounter a test case you cannot fully automate**, your DEFAULT action is **Option 1: attempt partial testing**. Do NOT skip to Option 3.

### Option Priority (MANDATORY ORDER)

**Option 1 (DEFAULT — always attempt first):** Generate test data via Tinker and test everything you CAN — UI rendering, policy behavior, API responses, database state, script content review. Note in the report: "Tested via Tinker-generated data — server-side execution not verified." This is STILL real testing — you are verifying UI behavior, authorization, validation, and database state on staging.

**Option 2 (when Option 1 is insufficient):** Present the user with exact manual test steps. Provide numbered steps with exact URLs, expected results, and what evidence to collect (screenshot, command output). Wait for the user's response before continuing. Include their findings in the report with "Verified by user" attribution.

**Option 3 (LAST RESORT — requires user approval):** You may NOT choose Option 3 yourself. If you believe a test genuinely cannot be tested even partially, present it to the user and ask: "Should I skip this test? I could not find a way to test it even partially." Only skip if the user explicitly approves.

### Hard Cap on Skipped Tests

**Maximum 3 items in "Areas Not Fully Tested" per report.** If you hit 3 skipped items, you MUST go back and find a way to partially test additional items via Option 1 or escalate to the user via Option 2. A report with 5+ untested areas is an incomplete QA session, not a thorough one.

### Escalation Format

**Batch related manual items** — present them together in one prompt, not one at a time:

```
I cannot fully automate the following tests. Here's my plan:

OPTION 1 (I will attempt these — partial testing via Tinker/UI):
  - [Test case] — I'll create test data and verify UI rendering + DB state
  - [Test case] — I'll verify the script content is correct + policy blocks unauthorized users

OPTION 2 (Need your help — requires real infrastructure):
  - [Test case] — exact steps you'd need to perform + what to observe

OPTION 3 (Cannot test even partially — requesting your approval to skip):
  - [Test case] — reason why even partial testing is impossible

Proceeding with Option 1 items now. Please let me know about Option 2 and 3 items.
```

### Rules
- **Option 1 is NOT "skipping"** — testing UI + DB + policies via Tinker-generated data is real testing that catches real bugs. The only thing you're not testing is actual server-side execution.
- **Option 2 (user tests):** Wait for the user's response before continuing. Include their findings in the report with "Verified by user" attribution.
- **Option 3 requires explicit user approval** — never self-approve a skip. The user decides what's acceptable to leave untested.

**Common scenarios requiring escalation:**

| Scenario | Why it can't be automated | Option 1 viable? |
|----------|--------------------------|-------------------|
| Real server provisioning | Requires cloud provider API | Partially — test UI + DB, not actual provisioning |
| DNS propagation | Requires real domain + time | No — user must verify |
| SSL certificate issuance | Requires real domain + Let's Encrypt | No — user must verify |
| Email/notification delivery | Requires real mailbox access | Partially — check `jobs`/`notifications` table |
| Payment processing | Requires real payment method | No — user must verify |
| Real package install/removal | Requires actual server with correct stack | Partially — test UI + script content, not execution |
| Webhook/callback reception | Requires external service to call back | Partially — test endpoint exists and handler logic |
| Multi-browser compatibility | Only one browser available | No — user must verify |

**Timing:** Run all automated tests first, then batch all manual items into one escalation prompt. This minimizes interruptions while the PR is still deployed.

## Step 5: Root Cause Analysis

When you find a bug, trace it to the source code:

1. **Identify the controller/service** handling the failed request (check routes, middleware)
2. **Read the relevant code** — controllers, policies, form requests, models
3. **Check git history** if it seems like a regression:
   ```bash
   git log --oneline -20 -- path/to/file.php
   ```
4. **Verify in Tinker** — check database state, model attributes, policy results
5. **Include root cause file and line** in your bug report

### 5.2 Logic Flaw Root Cause (for BLV test failures)

When a [BLV] test case fails, the root cause is not a coding error — it's a design decision that contradicts domain best practices or expected behavior. Document differently from regular bugs:

1. **Identify the design decision** — what choice did the developer make? (e.g., "chose threshold of 1 request")
2. **Explain why it's problematic** — reference domain standards or user expectations from the Expected Behavior Specification (Step 1.4.1)
3. **Propose the correct approach** — what should the implementation do instead? Be concrete and specific.
4. **Assess severity** — based on the consequence tier from the EBS (Critical/High/Medium/Low)
5. **Note user confirmation status** — if the user was asked in Step 1.4.3 and said "it's intentional," this becomes an Observation, not a Bug/Logic Flaw

## Step 6: Evidence Collection

**Every test case — PASS or FAIL — must have evidence.** A test result without evidence is an opinion, not a test result.

### What Counts as Test Evidence (REQUIRED)
- **Screenshots** from Playwright showing the UI state (scrolled to the relevant element)
- **SSH command output** verifying server-side state (e.g., `dpkg -l | grep package`, `systemctl status service`)
- **Command Runner output** — run verification commands via Server > Management > Commands in xCloud UI, then screenshot the result
- **Tinker query results** confirming database/meta state
- **curl response output** for API endpoint testing
- **Browser console/network logs** for error detection

### What Does NOT Count as Evidence (NEVER USE)
- Reading source code and concluding "the code looks correct"
- Reviewing the PR diff and saying "the fix addresses the issue"
- Describing code logic without running it on staging
- Writing "verified" without showing how

**Test evidence = output from actually performing the test on staging.** If you didn't run it, you didn't test it.

### Cloudinary Screenshot Upload

**Before taking any screenshots**, check if all 3 Cloudinary env vars are set (run this Bash command once at the start of testing):

```bash
echo "CLOUDINARY_CLOUD_NAME=${CLOUDINARY_CLOUD_NAME:-(not set)}"
echo "CLOUDINARY_API_KEY=${CLOUDINARY_API_KEY:-(not set)}"
echo "CLOUDINARY_API_SECRET=${CLOUDINARY_API_SECRET:-(not set)}"
```

- **If all 3 are set:** Capture screenshots locally to `qa-screenshots/`, then **batch upload after all screenshots are captured** (Step 9) by running the skill's upload script — one command, no loops:
  ```bash
  python3 ~/.claude/skills/xcloud-test/scripts/upload_screenshots.py --dir qa-screenshots --pr <PR_NUMBER>
  ```
  The script handles every file in the directory, prints each URL, and outputs a ready-to-paste markdown table. Use the returned Cloudinary URLs in the report, **not** local paths.

- **If any var is missing:** Fall back to local paths in the report: `![alt text](qa-screenshots/XX-description.png)`

> **MANDATORY — Upload via script only:**
> The upload script at `~/.claude/skills/xcloud-test/scripts/upload_screenshots.py` is the ONLY permitted upload method.
> - **NEVER** write a for loop to iterate over screenshot files
> - **NEVER** use curl, wget, or requests to upload files manually
> - **NEVER** write custom Python/Bash upload code of any kind
> - **NEVER** upload files one at a time with separate Bash commands
>
> **Wrong:**
> ```bash
> # ❌ Do NOT do this
> for f in qa-screenshots/*.png; do
>   curl -X POST "https://api.cloudinary.com/..." -F "file=@$f"
> done
> ```
> **Right:**
> ```bash
> # ✅ Always do this — one command
> python3 ~/.claude/skills/xcloud-test/scripts/upload_screenshots.py --dir qa-screenshots --pr <PR_NUMBER>
> ```

### Evidence to Collect
- **Screenshots** saved to `qa-screenshots/` then uploaded to Cloudinary (if available) — scroll to the specific element that shows the bug or fix before capturing. Before/after screenshots must be visually distinct. Capture toasts/notifications immediately before they auto-dismiss.
- **Browser console errors** via `browser_console_messages`
- **Network errors** via `browser_network_requests`
- **Server logs** via SSH after any 500 error
- **Database state** via Tinker queries
- **Server-side state** via SSH or Command Runner (packages, configs, services, binaries)

## Step 5: Gap Evaluation + Pre-Verdict Completeness Check (MANDATORY — merged step)

Before writing the final verdict, verify you've completed every mandatory step. If any item is unchecked, **go back and complete it** before proceeding to the report.

- [ ] **Core action executed end-to-end** — actually performed the PR's primary feature on staging (not just verified it appears in the UI)
- [ ] **Server-side state verified** — after every server-modifying operation, ran the specific verification command from `references/server-verification.md` verification matrix via Command Runner or SSH and screenshotted the output. "UI showed success" without a Command Runner/SSH check is incomplete.
- [ ] **All code consumers searched** — used Grep/Explore to find every consumer of the changed code and verified each handles the change correctly (Section 1.2)
- [ ] **Frontend/backend guard consistency checked** — for any UI-disabled/hidden feature, verified the backend API also blocks it (Section 4.6)
- [ ] **Database/meta state verified** — used Tinker to confirm records, flags, and metadata are correct after actions
- [ ] **At least 2 user roles tested** — tested with the primary user and at least one restricted role
- [ ] **Console errors checked** — ran `browser_console_messages` on every page visited
- [ ] **Server logs checked** — checked `laravel.log` after any unexpected error or 500 response
- [ ] **Failure paths considered** — tested or reasoned about what happens when the operation fails, and verified status doesn't get stuck
- [ ] **Double-submit checked** — verified rapid clicks or form resubmission don't cause duplicate actions
- [ ] **Business logic validated** — confirmed that the feature's algorithm/approach matches domain best practices and the Expected Behavior Specification from Step 1.4. Any MISMATCH gaps are either confirmed as logic flaws (with evidence), confirmed as intentional by the user, or documented in observations.

### Coverage Gate (MANDATORY)

Before writing the verdict, calculate your coverage:

1. **Traceability check:** Review the traceability matrix from Step 4.0. Every changed file must have at least 1 executed test case with evidence from staging. If any file has 0 executed tests, go back and test it.

2. **Skip count check:** Count items in "Areas Not Fully Tested." If more than 3, go back and convert skips to partial tests (Option 1) or user-assisted tests (Option 2). Maximum 3 skipped areas per report.

3. **Evidence audit — scan every test case for code-review-as-evidence:**
   Look at the Evidence column of every test case table. Flag any row where the evidence is:
   - "Code review confirms..." or "The code handles..."
   - "Verified by reading the controller/policy/migration"
   - "The diff shows that..." or "The PR addresses this by..."
   - "Based on the implementation..." or "The logic correctly..."
   - Any description of what the code does instead of what you observed on staging

   **If you find any of these:** That test case is NOT tested. Replace the evidence with actual staging evidence — screenshot, Tinker output, SSH command output, curl response, or browser console log. If you cannot get staging evidence, move the test case to "Areas Not Fully Tested" (subject to the 3-item cap).

4. **Coverage percentage:** Calculate `(test cases with staging evidence) / (total test cases) × 100`. If below **80%**, the report is incomplete — go back and fill gaps. Target is **90%+**.

A PASS verdict without completing all items is incomplete QA.

## Close Browser (after Step 5, before Step 6)

After all testing and evidence collection is complete, **close the browser using the Playwright MCP `browser_close` tool** before writing the report. This is a mandatory tool call — not a conceptual step:

Use the `browser_close` tool (the exact MCP tool name depends on which Playwright plugin is active — use `mcp__playwright__browser_close` or `mcp__plugin_playwright_playwright__browser_close`, whichever is available in the current session).

All screenshots have been captured, console messages checked, and network requests logged — the browser is no longer needed. Closing it frees resources, prevents accidental interactions during report writing, and ensures a fresh session if testing multiple PRs sequentially.

## Step 6: Final Report (parallel with Step 7 cleanup + Step 9 screenshot upload)

> **Report writing runs in a sub-agent.** Do NOT write the report in the main session — the report content is large and loading reference files alongside it would overflow the main context.

**Spawn a report-writing sub-agent:**

```
Agent(
  description="Write QA report for PR #<N>",
  prompt="You are a QA report writer. Write the final QA report based on completed test results.

  **Data source:** Read qa-test-progress.json for all test results, bugs, screenshots, and analysis.
  **UX analysis:** [paste the 400-word summary returned by the UX background agent]
  **Cloudinary URLs:** [paste screenshot URL table if upload was done, else use local paths]

  **Instructions:**
  1. Load references/report-template.md for the mandatory report structure (13 sections)
  2. Read qa-test-progress.json completely — this is your only data source
  3. Write the report to QA-Report-PR-<N>.md in the project root
  4. Embed all screenshots inline using ![alt text](path) syntax — never bare filenames
  5. Every bug must have Root Cause: file + line number
  6. Every test category section must end with — PASS or — FAIL
  7. Run the Post-Report Validation Checklist from report-template.md before returning
  8. Return: report file path, section count, bug count, any validation failures found"
)
```

The main session only needs the confirmation that the file was written. Do not read the report back into the main session.

If testing multiple PRs, also generate the Multi-PR Summary Report — see `references/report-template.md` "Multi-PR Summary Report Template" section.

## Step 6.5: Report Validation (MANDATORY)

After writing the report, run through the **Post-Report Validation Checklist** in `references/report-template.md`. This catches format drift, missing sections, and bare filenames before the report is finalized.

Quick self-check — scan the report for these red flags:
1. Any line containing `qa-screenshots/` that is NOT inside a `![...](...)` — means an image is not embedded
2. Any bug without a `**Root Cause:**` line — means root cause analysis is missing
3. Any test category heading without "— PASS" or "— FAIL" — means verdict is missing
4. The Screenshots table has no rows — means evidence summary is empty

If any check fails, fix it before delivering the report.

## Step 7: Cleanup (parallel with Step 6 report writing)

> Load `references/environment-setup.md` for cleanup procedures and verification queries.

Delete ALL test records created during testing. Clean up in reverse order (child records first for FK constraints). Track everything in the report's "Test Data Cleanup" table.

## Step 8: UX Critique, Improvement Suggestions & Competitive Analysis (BACKGROUND AGENT)

This step runs as a **background agent in parallel with testing** (Step 4). Spawn it automatically after first screenshots are captured during Step 4. Its output is **included in the main QA report** (Step 6), not a separate document.

### How to Run

After Step 3 (browser open) and first page screenshots are captured, spawn a parallel agent in the background:

```
Agent(
  description="UX & Product Analysis for PR #<N>",
  prompt="You are a product analyst reviewing the UX and competitive positioning
  of the feature in PR #<N> on the xCloud platform.

  **PR Summary:** [paste from Step 1]
  **Screenshots:** [list screenshot paths captured during testing]
  **Feature:** [what the PR adds/changes]

  Produce a Product Improvement Addendum with these sections:
  1. UX Critique (with severity)
  2. Human Interaction Review
  3. Improvement Suggestions
  4. Competitive Analysis
  5. Feature Enhancement Ideas

  Use the detailed instructions below for each section."
)
```

### 9.1 UX Critique (Go Beyond Visual Checklist)

Step 4.8 catches visual bugs (alignment, colors). This step goes deeper — **critique the user experience as a real user would experience it.**

**Workflow friction:**
- How many clicks does it take to complete the core action? Could it be fewer?
- Are there unnecessary confirmation dialogs or intermediate steps?
- Is the user forced to leave the current page to complete a related task?
- Does the feature have a clear "done" state, or is the user left wondering if it worked?

**Information architecture:**
- Is the feature discoverable? Would a new user find it without being told where it is?
- Does the menu placement make sense? (e.g., is a security feature under "Settings" or under "Security"?)
- Are related features grouped together or scattered across different pages?

**Error UX:**
- When something fails, does the error message tell the user WHAT went wrong and HOW to fix it?
- Are error messages specific (`"Server name must be 3-50 characters"`) or generic (`"Validation failed"`)?
- Does the UI recover gracefully from errors, or does it get stuck in a broken state?

**Cognitive load:**
- Are there too many options/fields on one page?
- Is the terminology consistent? (Same concept called different names in different places?)
- Would a first-time user understand what each option does without documentation?

### 9.2 Human Interaction Review

**Present findings to the user and ask for their input:**

```
I've completed QA testing. Before finalizing, I'd like your input on a few UX observations:

1. [Observation] — The feature requires 5 clicks to complete. Possible to reduce to 3?
2. [Observation] — The error message says "Invalid input" without specifying which field.
3. [Observation] — The loading state shows a blank page for 2-3 seconds before content appears.

Questions for you:
- Are any of these intentional design choices?
- Should I add these as improvement suggestions in the report?
- Is there anything about this feature's UX that bothers you as a user?
```

**Wait for user response.** Incorporate their feedback into the Product Improvement Addendum.

### 9.3 Improvement Suggestions

For each issue found in 9.1, propose a **concrete, actionable improvement:**

```markdown
| # | Current Behavior | Suggested Improvement | Effort | Impact |
|---|-----------------|----------------------|--------|--------|
| 1 | 5 clicks to install PHP | Add "Quick Install" button on PHP list page | Low | High |
| 2 | Generic "Validation failed" error | Show field-specific errors inline | Medium | High |
| 3 | Blank loading state | Add skeleton loader matching page layout | Low | Medium |
| 4 | SSL status only shows "Active"/"Inactive" | Show expiry date + auto-renew status | Low | Medium |
```

**Effort scale:** Low (CSS/copy change), Medium (component change), High (new feature/refactor)
**Impact scale:** Low (cosmetic), Medium (usability), High (user retention/conversion)

### 9.4 Competitive Analysis

Research how **competing platforms** handle the same feature. Use web search if available, otherwise use training knowledge.

**Competitors to compare against:**
- **Laravel Forge** — Laravel server management
- **Ploi** — Server management for PHP
- **ServerPilot** — PHP hosting platform
- **RunCloud** — Cloud server management
- **Cloudways** — Managed cloud hosting
- **DigitalOcean App Platform** — PaaS comparison

**For each competitor, note:**

```markdown
### Competitive Analysis: [Feature Name]

| Platform | Has this feature? | How they implement it | What xCloud does better | What they do better |
|----------|------------------|----------------------|------------------------|---------------------|
| Laravel Forge | Yes | One-click PHP install with progress bar | xCloud has multi-stack support | Forge shows real-time install progress |
| Ploi | Yes | Inline PHP version selector | xCloud has OPCache UI toggle | Ploi's UI is cleaner/simpler |
| RunCloud | No | — | xCloud offers this feature | — |
```

### 9.5 Feature Enhancement Ideas

Based on the competitive analysis and UX critique, propose **2-3 feature enhancements** that would make xCloud's implementation best-in-class:

```markdown
### Enhancement Ideas

1. **Real-time operation progress** (inspired by Forge)
   - Current: Toast says "Installing..." then "Installed" with no progress
   - Proposed: WebSocket-driven progress bar showing actual install steps
   - Why: Reduces user anxiety during long operations (30-60 seconds)

2. **Smart defaults** (inspired by Ploi)
   - Current: User must choose PHP version, extensions, settings manually
   - Proposed: Detect framework (Laravel/WordPress) and pre-select optimal defaults
   - Why: Reduces setup time from 5 minutes to 1 minute for common stacks
```

### Report Integration

The parallel agent's output is **included as Section 12 in the main QA report** (before the Final Verdict). When the agent completes, merge its findings into the report:

```markdown
## 12. Product & UX Analysis

### UX Critique
[findings from 6.8.1]

### User Feedback
[findings from 6.8.2 human interaction]

### Improvement Suggestions
| # | Current Behavior | Suggested Improvement | Effort | Impact |
[table from 6.8.3]

### Competitive Analysis
[table from 6.8.4]

### Feature Enhancement Ideas
[proposals from 6.8.5]
```

**Timing:** The background agent MUST complete before Step 6 (report writing) starts. If it hasn't finished, wait for it — the report needs this section. Since it runs in background during Step 4 (testing), it should complete around the same time or earlier.

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| **Running browser tests in the main session** | Each `browser_snapshot` dumps ~10–50 KB of accessibility tree into the main context. By TC-15 the context is full and the session silently stops. | Browser testing MUST run inside testing sub-agents (Section 4.1). Main session only sees result summaries. |
| **Writing a for loop to upload screenshots** | Claude may write `for f in qa-screenshots/*.png; do curl ...` or a Python loop thinking it's "custom code". This is explicitly forbidden. | Run ONE command: `python3 ~/.claude/skills/xcloud-test/scripts/upload_screenshots.py --dir qa-screenshots --pr <N>` — no loops, no curl, no custom code of any kind. |
| **Reporting PASS without evidence** | "Login works" with no screenshot is not a test result | Every PASS needs a screenshot, command output, or Tinker result |
| **Reading code instead of testing** | "The controller checks permissions" is code review, not QA | Actually log in as the wrong user and try to access the resource |
| **Testing only happy path** | Missing negative tests, edge cases, and role variations | Generate test cases for error paths, boundary values, and unauthorized access |
| **Skipping server-side verification** | "UI shows Installed" doesn't prove packages are on the server | SSH or Command Runner to verify actual server state |
| **Not testing with multiple roles** | Only testing as the admin/paid user | Always test with at least 2 roles — paid and free/restricted |
| **Generic test cases** | "Check if feature works" is not a test case | Be specific: "Enter email with 256 chars, submit, verify validation error shown" |
| **Missing regression tests** | Only testing the changed feature, ignoring consumers | Use Step 1.2 cross-feature analysis to find all consumers and test each |
| **Skipping Command Runner** | Only using SSH when Command Runner is available | Use Command Runner for server-side verification — output is easy to screenshot |
| **Skipping tests due to missing infrastructure** | "Staging doesn't have an OLS server so I'll skip OLS tests" | Create the required server/site via Tinker (Step 2.1). Takes 30 seconds. Never skip. |
| **Trusting UI toast as server proof** | "Restarted" toast ≠ service running. "Installed" badge ≠ packages on disk. | Run the verification command from `references/server-verification.md` via Command Runner and screenshot the output |
| **Not knowing operational commands** | Agent skips checks because it doesn't know how to verify service health, check SSL, or inspect configs | Load `references/server-verification.md` operational recipes section for stack-aware commands |
| **Using wrong commands for stack** | Running `service nginx restart` on an OpenLiteSpeed server | Check the server's stack first, then use the stack-specific command from the verification matrix |
| **Wrong Tinker field values** | Using `'status' => 'active'`, `'stack' => 'ols'`, `'ip' => '...'` | Use actual enum values: `'provisioned'`, `'openlitespeed'`, `'public_ip'`. See environment-setup.md |
| **Creating sites on wrong stack** | Docker app on Nginx server, or WordPress on OpenClaw | Check the stack-site compatibility matrix in environment-setup.md before creating |
| **Using CLI instead of UI** | Agent uses `sed` to toggle debug mode when xCloud has a UI toggle at Settings | Check `references/xcloud-feature-map.md` — if a feature has a UI page, test via the UI |
| **Missing site-type features** | Agent tests only common features, missing WordPress-specific pages like Caching, Updates, Integrity Monitor | Check the site type matrix in `references/xcloud-feature-map.md` for type-specific features to test |
| **Not checking feature availability by stack** | Testing PHP Analytics on a Docker server where it's not available | Check stack conditions in the feature map — Docker and OpenClaw servers have restricted feature sets |
| **"Code looks correct" as evidence** | Writing "the controller validates input correctly" based on reading code | Log in, submit invalid input, screenshot the error response. Code analysis is not QA evidence. |
| **"Verified by reviewing the diff"** | Writing "the PR fixes the null check" without testing on staging | Actually trigger the null case on staging and verify the fix works. Reading code = code review, not testing. |
| **Skipping UI test because Tinker confirms DB state** | "Tinker shows the record exists so the feature works" | Navigate to the UI page, interact with the feature, screenshot the result. DB state ≠ UI behavior. |
| **Too many "Areas Not Fully Tested"** | Report has 5+ untested areas, treated as acceptable | Maximum 3 skipped areas per report. Convert skips to partial tests (Option 1) or user-assisted tests (Option 2). |
| **Self-approving Option 3 (skip)** | Agent decides to skip a test without asking the user | Option 3 requires explicit user approval. Always attempt Option 1 (partial testing) first. |
| **Vague test cases** | "Verify the feature works for different roles" — no specific scenario | Be specific: "Log in as free user (email), navigate to /servers/5/php, click Install PHP 8.3, verify upgrade prompt shown" |
| **Testing only the implementation's behavior** | "Code says 1 request = threat, test confirms it" — you validated the wrong thing. If the algorithm is wrong, code-conformance tests pass while users suffer. | Define expected behavior independently using the five lenses in Step 1.4. Generate [BLV] test cases that test CORRECT behavior, not implemented behavior. When BLV tests fail, you found a logic flaw the regular tests would never catch. |

## Progress Reporting (MANDATORY)

Long silent periods make it impossible for the user to tell if work is happening or if the agent is stuck. **Output a short status message at every checkpoint** listed below. These are plain text messages — not tool calls, not comments in code. Just print them so the user sees activity.

### Checkpoint Messages

Print these at the indicated moments. Keep each message to **one line**.

**Step 1 (Analyze) + Step 2 (Deploy background sub-agent) — spawn simultaneously:**
- `[Step 1+2] Spawning analysis agent (foreground) + deploy sub-agent (background)...`
- `[Step 1] Analyzing PR #<N>... reading diff (<X> files changed)`
- `[Step 1] Cross-feature impact: found <N> consumers of changed code`
- `[Step 2] Deploy sub-agent running in background — proceeding with Steps 3+4 in parallel`
- `[Step 2] Deploy complete — branch <name>, commit <hash>` *(printed when sub-agent returns)*

**Step 3 (Clarification Questions) — after Step 1, while deploy runs:**
- `[Step 3] Analysis complete. Preparing clarification questions...`
- `[Step 3] Found <N> scope/behavior ambiguities — asking user now`
- `[Step 3] Waiting for user response...`
- `[Step 3] Answers received — updating test scope` *(after user responds)*

**Step 4 (BLV + Test Cases) — after Step 3 answers, while deploy may still run:**
- `[Step 4] Running BLV + generating standard test cases in parallel...`
- `[Step 4] BLV: found <N> potential logic gaps (confidence: <high/medium/low>)`
- `[Step 4] Generated <N> test cases (<N> standard + <N> BLV)`
- `[Step 4] Checking deploy status before starting browser testing...`
- `[Step 5 GATE] Deploy confirmed ✓ + test cases ready ✓ — spawning test sub-agents`

**Step 4 (Browser + Testing) — sub-agent dispatch (main session prints these):**
- `[Step 4] Writing checkpoint to qa-test-progress.json...`
- `[Step 4] <N> test cases split into <M> batches of 15`
- `[Step 4] Spawning UX agent in background...`
- `[Step 4] Spawning Batch <B>/<M>: TC-<start> to TC-<end>...`
- `[Step 4] Batch <B> complete: <N> PASS, <N> FAIL — <N> bugs found`
- `[Step 4] Batch <B> escalation: TC-<N> needs user action — <description>`
- `[Step 4] All batches complete: <N>/<total> tests done`

**Inside each testing sub-agent (sub-agent prints these):**
- `[Batch <B>] Opening browser → <staging-url>...`
- `[Batch <B>] Logging in as <role> (<email>)...`
- `[TC-<N>/<batch-total>] <category>: <test case name>...`
- `[TC-<N>/<batch-total>] → PASS` or `[TC-<N>/<batch-total>] → FAIL: <one-line reason>`
- `[Batch <B>] Switching to <role> account for role-based tests...`
- `[Batch <B>] Running server-side verification via Command Runner...`
- `[Batch <B>] Closing browser...`

**Step 6 (Gap Eval + Pre-verdict):**
- `[Step 6] Gap evaluation: found <N> missing test cases`
- `[Step 6] Pre-verdict check: <N>/11 items verified`
- `Bug found — tracing root cause in <file>...`

**Steps 6+7+9 (Report + Cleanup + Upload) — run in parallel:**
- `[Step 6+7+9] Starting report, cleanup, and screenshot upload in parallel...`
- `[Step 9] Uploading <N> screenshots to Cloudinary...`
- `[Step 7] Cleaning up test data: deleting <N> records...`
- `[Step 6] Writing QA report... section <N>/13: <section name>`
- `[Step 7] Cleanup verified — all test records removed`
- `[Step 9] Screenshots uploaded — URLs inserted into report`

### Rules

- **Never go more than 60 seconds without printing a status message.** If a tool call takes longer (e.g., slow SSH, large file read), print a "still working on..." message before the tool call.
- **Test case progress is the most important feedback.** The user needs to see `[TC-5/20]` ticking up to know testing is progressing. Never run multiple test cases without printing progress between them.
- **Errors get immediate output.** If SSH fails, browser crashes, or a test case unexpectedly errors — print it immediately, don't batch it for the report.

## Verdict Rules (MANDATORY)

> Load `references/business-logic-validation.md` for the full decision tree and examples.
> Load `references/test-case-template.md` for test case formats and verdict rules.

**A business logic flaw in the PR's core feature is a FAIL verdict, not a PASS with observations.**

| Condition | Verdict |
|-----------|---------|
| All tests pass, logic is correct | **PASS** |
| Tests pass, minor edge-case observations | **PASS** (with observations) |
| Tests pass but core feature logic is flawed (false positives, misleading output, wrong thresholds) | **FAIL** (logic flaw) |
| User explicitly confirms flawed logic is intentional | **CONDITIONAL PASS** (document confirmation) |
| Any critical/high bug found | **FAIL** |

**Never downgrade a core logic flaw to "observation."** If the feature produces misleading results for users, the feature is broken — regardless of whether the code runs without errors.

## Server Architecture Awareness

xCloud manages **two types of servers** — never confuse them:

| Server | What it is | How to access |
|--------|-----------|---------------|
| **xCloud app server** | Hosts the xCloud platform itself (staging.tmp1.dev) | SSH via credentials provided by user |
| **Managed server** | Servers owned by users, managed BY xCloud (e.g., OLS Server at 107.175.2.40) | **Command Runner** in xCloud UI (Server > Management > Commands) |

**CRITICAL:** Scripts like `PullSecurityAnalytics` run on the **managed server**, not the app server. To verify server-side state on managed servers:
- Use **Command Runner** through the xCloud UI — NOT direct SSH to the app server
- Command Runner executes commands on the managed server and shows output in the browser
- Screenshots of Command Runner output serve as server-side evidence

**Deploy script** (`scripts/deploy_to_staging.py`) deploys code to the **app server** only.

## Behavior Rules

These principles guide every QA session. The specific procedures are in the steps above and reference files — these rules are about mindset.

- **Assume bugs exist until proven otherwise** — be systematic and skeptical, not confirmatory
- **Evidence for every claim** — screenshot it, log it, or query it. No claim without proof.
- **Root cause, not symptoms** — every bug report must trace to a source file and line number
- **End-to-end, not surface-level** — "it appears in the UI" is not verification. Perform the action and check UI + API + server state + database
- **Logic correctness, not just code correctness** — "the code does what it says" is not enough. Ask: "does the code do what it SHOULD do?" A feature that misleads users is broken even if the code runs cleanly.
- **Cross-reference previous QA reports** — if a prior report exists for related features, check for known issues before starting
- **PR source code is accessed via worktree agents only** — never run `gh pr checkout` or any git checkout in the main session. Even inside an `isolation="worktree"` agent, avoid `gh pr checkout` — it modifies the shared `.git` directory (tracking refs, config) which can affect the main session's working state. Instead, use `git fetch origin 'refs/pull/<N>/head' && git checkout FETCH_HEAD` inside the worktree agent (detached HEAD, no shared ref modification).
