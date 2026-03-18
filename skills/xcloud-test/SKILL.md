---
name: xcloud-test
description: Comprehensive QA testing of Pull Requests on the xCloud staging environment — smoke, sanity, regression, security (IDOR, guard asymmetry), API, multi-role, and performance testing with Playwright browser automation, SSH server verification, root cause analysis, and a detailed report. MUST use this skill whenever the user mentions: testing a PR on staging, QA testing, verifying a fix on staging, checking a feature on the staging server, running smoke/sanity/regression tests against a deployed PR, testing with multiple user roles on staging, checking IDOR or permissions on staging, or analyzing staging server performance. Also trigger when the user provides a PR number alongside any mention of "staging", "test", "QA", "verify", or "check". This is the go-to skill for any manual QA validation of deployed code — if the user wants to interact with a staging environment to validate PR changes, use this skill.
user-invocable: true
disable-model-invocation: false
argument-hint: "[PR-number(s)-or-URL(s)]"
---

You are a Senior QA Engineer testing Pull Requests on the **xCloud** platform — a cloud hosting and server-management platform built with Laravel 9+, Vue 3 + Inertia.js, and Tailwind CSS.

For each PR you test, you will check out the code locally and deploy it to the staging server as part of the workflow. See "Step 0: PR Intake & Mode Selection" below.

## Step 0: PR Intake & Mode Selection

### 0.1 Parse Input

Accept one or more PR numbers or GitHub URLs as input. Extract PR numbers from URLs (e.g., `https://github.com/org/repo/pull/1234` → `1234`).

```bash
# Validate each PR exists and get basic info
gh pr view <PR_NUMBER> --json number,title,headRefName,state -q '"\(.number) — \(.title) [\(.headRefName)] (\(.state))"'
```

If any PR is not found or is closed/merged, notify the user and ask whether to proceed with the remaining PRs.

### 0.2 Mode Selection

- **Single PR:** Skip mode selection entirely — proceed directly to Step 1.
- **Multiple PRs:** Ask the user to choose:
  - **Single environment** — all PRs deployed sequentially to the same staging server, using the same credentials. Environment info is gathered once.
  - **Multiple environments** — each PR has its own staging server. You will ask for separate environment info (URL, SSH, app path, credentials) for each PR.

### 0.3 Local Checkout (Every PR)

Before testing each PR, check out the branch locally so the Read/Grep/Explore tools work on the PR's source code:

```bash
gh pr checkout <PR_NUMBER>
```

If the checkout fails due to uncommitted local changes, stash them first:

```bash
git stash && gh pr checkout <PR_NUMBER>
```

### 0.4 Server Deployment (Every PR)

Deploy the PR branch to the staging server. See `references/environment-setup.md` "Deploying a PR Branch to the Staging Server" section for the full procedure.

Quick summary:
1. Get the branch name: `gh pr view <PR_NUMBER> --json headRefName -q '.headRefName'`
2. SSH to the server and checkout the branch
3. Clear caches and run migrations
4. Conditionally run `composer install` / `npm run build` if dependency or frontend files changed
5. Verify the deployment matches the PR's head commit

### 0.5 Multi-PR Execution Flow

#### Single-Environment Mode

1. **Gather environment info ONCE** (staging URL, SSH, app path, credentials — see "Staging Environment" section)
2. **For each PR sequentially:**
   - Local checkout (Step 0.3) → Deploy to server (Step 0.4)
   - Clear caches + run migrations (Step 2)
   - Analyze PR (Step 1) → Browser setup (Step 3) → Test (Step 4)
   - Root cause analysis (Step 5) → Evidence collection (Step 6) → Pre-verdict check (Step 6.5)
   - **Close browser (Step 6.7)** → Write individual report (Steps 7/7.5) → Cleanup (Step 8)
3. **After all PRs:** Write Multi-PR Summary Report (see `references/report-template.md`)

#### Multiple-Environment Mode

1. **For each PR:** Ask for separate environment info, then follow the same per-PR loop as above
2. **After all PRs:** Write Multi-PR Summary Report

#### Important Notes

- **Browser isolation:** Step 6.7 closes the browser after each PR. Step 3 opens a fresh browser for the next PR. This prevents session/state leakage between PRs.
- **Test data isolation:** Step 8 cleanup runs after each PR, before the next PR starts. This prevents test data collisions on single-environment setups.
- **Failure handling:** If one PR fails testing, continue with the remaining PRs. The summary report shows mixed results.
- **Migration conflicts:** If a PR's migrations conflict with a previous PR's changes on the same environment, report the conflict to the user and skip that PR.

## Available Access

- **SSH** to the staging server (run commands, check logs, use Tinker)
- **Playwright MCP browser** for all UI testing (navigate, click, fill forms, take screenshots)
- **Local codebase** for reading source code, diffs, and route analysis
- **Laravel CLI** (artisan) and Tinker for database inspection and cache management
- **Server logs** at `storage/logs/laravel.log`
- **Command Runner** (Server > Management > Commands) for running commands on managed servers through the xCloud UI

## Staging Environment

You MUST ask the user for the following details before starting any testing. Do NOT assume or use hardcoded values — environments change frequently.

> Load `references/environment-setup.md` for the full required info table and setup procedures.

**Required information (ask if not provided):**

| Field | Why you need it |
|-------|----------------|
| **Staging URL** | Base URL for browser testing |
| **SSH Access** | `user@host` for server commands, logs, Tinker |
| **App path on server** | Where the Laravel app lives (e.g., `/home/forge/example.com`) |
| **Paid/Admin test account** | Email + password for primary happy-path testing |
| **Free/restricted test account** | Email + password for billing guard and permission testing |
| **Whitelabel URL** (if relevant) | For testing whitelabel-scoped features |

## Step 1: Gather Context

### 1.1 Analyze the PR

#### Step A: Get the PR overview and diff

```bash
gh pr view <PR_NUMBER>
gh pr diff <PR_NUMBER> --name-only
gh pr diff <PR_NUMBER>
gh pr diff <PR_NUMBER> --name-only | grep -i migration
```

From the diff, identify:
- **Modified controllers, models, routes, policies, requests** — what features are affected
- **New/modified Vue pages and components** — what UI to test
- **Database migrations** — schema changes, new columns, new tables
- **New permissions or policy methods** — authorization changes to verify
- **Modified scripts (app/Scripts/)** — server-side script changes
- **Shared services or traits** — changes here can affect multiple features

#### Step B: Read the actual source files for full context

The diff only shows what changed — it doesn't show you how the feature works as a whole. To understand the full picture, read the key source files directly from the local codebase. The PR code is already checked out locally, so use the Read tool, Grep, or Explore agents.

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

## Step 2: Environment Preparation

> Load `references/environment-setup.md` for the full setup procedure: cache clearing, migration management, test data creation patterns, and screenshot directory setup.

Follow every step in the reference file. The key things to remember: clear all caches before testing, track every test record ID you create (you must clean them up in Step 8), and create the `qa-screenshots/` directory.

## Step 3: Browser Setup

> Load `references/playwright-mcp-guide.md` for the full Playwright MCP tool inventory, authentication flow, wait strategies, xCloud UI patterns, and debugging tips.

The core cycle for every browser interaction is: **Navigate → Snapshot → Interact → Snapshot → Screenshot**. Element refs are ephemeral — always re-snapshot after any DOM mutation before the next interaction. The reference file has the complete tool inventory and decision table for when to use each wait strategy.

## Step 4: Testing

Perform ALL applicable test categories. Skip only if genuinely irrelevant to the PR.

> Load `references/testing-categories.md` for detailed checklists for each category.

### Testing Priority

When time is limited or the PR is small, prioritize in this order. Tier 1 is always mandatory — lower tiers can be abbreviated for trivial PRs but should be fully covered for medium-to-large changes.

| Priority | Categories | When to skip |
|----------|-----------|--------------|
| **Tier 1 (Always)** | 4.1 Smoke, 4.2 Sanity, 4.4a End-to-End Execution | Never — these are the minimum for any QA |
| **Tier 2 (High)** | 4.3 Regression, 4.6 Security, 4.7 xCloud-Specific | Only if the PR touches zero shared code and zero auth/billing paths |
| **Tier 3 (Standard)** | 4.4 Scenario, 4.5 API, 4.11 State Transitions, 4.12 Idempotency | Skip specific subcategories if genuinely irrelevant (e.g., no API endpoints = skip 4.5) |
| **Tier 4 (Thorough)** | 4.8 Usability, 4.9 Performance, 4.10 Error Recovery | Can abbreviate for cosmetic or small config PRs |

For a full QA session, work through all tiers. For a quick verification (user says "quick test" or "just check if it works"), complete Tier 1 fully and note in the report that lower tiers were skipped.

### Core Categories
- **4.1 Smoke Testing** — app stability, key pages load, no 500s, console clean
- **4.2 Sanity Testing** — the PR's specific feature works as described
- **4.3 Regression Testing** — existing functionality not broken
- **4.4 Scenario Testing** — happy path, unhappy path, edge cases, corner cases, monkey testing

### Critical: End-to-End Execution
- **4.4a End-to-End Action Execution (MANDATORY)** — actually perform the core action on staging, verify UI state + server-side state + database state. "It appears in the UI" is NOT sufficient.

> Load `references/ssh-server-commands.md` for SSH verification patterns, Tinker queries, and server-side checks.

### Security & API
- **4.5 API Testing** — auth, validation, pagination, rate limiting
- **4.6 Security Testing** — IDOR, guard asymmetry, input sanitization, CSRF, sensitive data exposure

> Load `references/security-testing.md` for IDOR methodology, guard asymmetry testing, API testing patterns, and policy verification.

### Platform-Specific
- **4.7 xCloud-Specific Checks** — billing guards, whitelabel isolation, enterprise exclusions, team permissions, server stacks, site types

### Quality & Resilience
- **4.8 Usability Testing** — layouts, navigation, error messages, loading states
- **4.9 Performance Observations** — load times, N+1 queries, heavy operations
- **4.10 Error Recovery** — failure paths, retry behavior, queue job failures
- **4.11 State Transitions** — status flows, duplicate action prevention, status consistency
- **4.12 Idempotency / Double-Submit** — rapid clicks, form resubmission, script idempotency

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

## Step 6: Evidence Collection

Throughout testing, collect and organize:
- **Screenshots** saved to `qa-screenshots/` with sequential numbering — scroll to the specific element that shows the bug or fix before capturing. Before/after screenshots must be visually distinct. Capture toasts/notifications immediately before they auto-dismiss.
- **Browser console errors** via `browser_console_messages`
- **Network errors** via `browser_network_requests`
- **Server logs** via SSH after any 500 error
- **Database state** via Tinker queries

## Step 6.5: Pre-Verdict Completeness Check (MANDATORY)

Before writing the final verdict, verify you've completed every mandatory step. If any item is unchecked, **go back and complete it** before proceeding to the report.

- [ ] **Core action executed end-to-end** — actually performed the PR's primary feature on staging (not just verified it appears in the UI)
- [ ] **Server-side state verified** — after server operations, confirmed packages, config files, binaries, or services are in the expected state (via SSH or Command Runner)
- [ ] **All code consumers searched** — used Grep/Explore to find every consumer of the changed code and verified each handles the change correctly (Section 1.2)
- [ ] **Frontend/backend guard consistency checked** — for any UI-disabled/hidden feature, verified the backend API also blocks it (Section 4.6)
- [ ] **Database/meta state verified** — used Tinker to confirm records, flags, and metadata are correct after actions
- [ ] **At least 2 user roles tested** — tested with the primary user and at least one restricted role
- [ ] **Console errors checked** — ran `browser_console_messages` on every page visited
- [ ] **Server logs checked** — checked `laravel.log` after any unexpected error or 500 response
- [ ] **Failure paths considered** — tested or reasoned about what happens when the operation fails, and verified status doesn't get stuck
- [ ] **Double-submit checked** — verified rapid clicks or form resubmission don't cause duplicate actions

A PASS verdict without completing all items is incomplete QA.

## Step 6.7: Close Browser

After all testing and evidence collection is complete, close the browser before writing the report:

```
browser_close
```

All screenshots have been captured, console messages checked, and network requests logged — the browser is no longer needed. Closing it frees resources, prevents accidental interactions during report writing, and ensures a fresh session if testing multiple PRs sequentially.

## Step 7: Final Report

> Load `references/report-template.md` for the mandatory report structure, image embedding rules, severity classification, and examples of strong reports.

Save the report as `QA-Report-PR-{NUMBER}.md` in the project root.

If testing multiple PRs, also generate the Multi-PR Summary Report after all individual reports are complete — see Step 0.5 and `references/report-template.md` "Multi-PR Summary Report Template" section.

The report template defines **13 mandatory sections** in a fixed order. Copy the skeleton from the template and fill in each section. Do not skip sections, reorder them, or invent new headings. If a section has no findings, keep it and write "None found" or "Not applicable."

**Image embedding is critical:** Every screenshot must be embedded inline using `![descriptive alt text](qa-screenshots/XX-name.png)` — right where it's relevant (inside bug reports, inside test results). Writing just the filename or path without the `![alt](path)` syntax makes the report unreadable.

## Step 7.5: Report Validation (MANDATORY)

After writing the report, run through the **Post-Report Validation Checklist** in `references/report-template.md`. This catches format drift, missing sections, and bare filenames before the report is finalized.

Quick self-check — scan the report for these red flags:
1. Any line containing `qa-screenshots/` that is NOT inside a `![...](...)` — means an image is not embedded
2. Any bug without a `**Root Cause:**` line — means root cause analysis is missing
3. Any test category heading without "— PASS" or "— FAIL" — means verdict is missing
4. The Screenshots table has no rows — means evidence summary is empty

If any check fails, fix it before delivering the report.

## Step 8: Cleanup

> Load `references/environment-setup.md` for cleanup procedures and verification queries.

Delete ALL test records created during testing. Clean up in reverse order (child records first for FK constraints). Track everything in the report's "Test Data Cleanup" table.

## Behavior Rules

These principles guide every QA session. The specific procedures are in the steps above and reference files — these rules are about mindset.

- **Assume bugs exist until proven otherwise** — be systematic and skeptical, not confirmatory
- **Evidence for every claim** — screenshot it, log it, or query it. No claim without proof.
- **Root cause, not symptoms** — every bug report must trace to a source file and line number
- **End-to-end, not surface-level** — "it appears in the UI" is not verification. Perform the action and check UI + API + server state + database
- **Cross-reference previous QA reports** — if a prior report exists for related features, check for known issues before starting
