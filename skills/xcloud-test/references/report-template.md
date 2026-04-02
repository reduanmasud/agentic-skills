# QA Report Template & Severity Classification

## File Naming

- PR-specific: `QA-Report-PR-{NUMBER}.md` in the project root
- Feature-specific: `QA-Report-{Feature-Name}.md` in the project root

## Image Embedding Rules

Screenshots are useless if readers have to go hunting for them in a folder. Embed every screenshot inline using markdown image syntax — right where it's relevant, not just as a filename or path.

**Correct — Cloudinary URL (preferred when `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` are all set):**
```markdown
![Login page showing error banner](https://res.cloudinary.com/xxxx/image/upload/v1234/qa-reports/03-login-error.png)
```

**Correct — local path (fallback when Cloudinary is not available):**
```markdown
![Login page showing error banner](qa-screenshots/03-login-error.png)
```

**Wrong (just a filename — never do this):**
```markdown
Screenshot: qa-screenshots/03-login-error.png
```
```markdown
See: 03-login-error.png
```

Embed images in these places:
- **Inside each bug report** — right after "Actual Result", embed the screenshot that proves the bug
- **Inside test results** — when a test result is visual, embed the screenshot inline with the result
- **In the Screenshots summary table** — the Preview column uses `![alt](path)` too

Every `![alt](path)` must use a descriptive alt text (not just the filename) so the report reads well even without images loading.

---

## Mandatory Report Structure

The report must follow this exact structure, in this exact order. Do not skip sections, reorder them, or invent new ones. If a section has no findings, write a one-line "None found" or "Not applicable" — do not omit it.

Copy this skeleton and fill in each section. The headings, table formats, and field labels below are not suggestions — they are the required format.

---

### Section 1: Title

```
# QA Report: PR #{NUMBER} — {PR Title}
```

### Section 2: PR Summary

The reader of this report may not have read the PR or the code. Write the summary so that someone with zero context can understand what this PR is about, why it exists, and what changed.

Include these subsections:

```
## PR Summary

### What this PR does
One or two sentences describing the feature or fix in plain language.
Example: "Adds PHP 8.5 support to the server management panel, allowing users to install, switch to, and configure PHP 8.5 on their servers."

### Problem / Previous behavior
What was broken, missing, or insufficient before this PR? Be specific.
Example: "PHP 8.5 was not available in the version selector. Users on PHP 8.4 had no upgrade path to 8.5. The OPCache toggle did not account for PHP 8.5's built-in OPCache."

### How it was fixed
What the PR actually changes — routes, controllers, migrations, UI components, scripts. Keep it brief but technical enough to understand the scope.
Example: "Added PHP 8.5 to the PhpVersion enum, created install/uninstall Blade scripts, added a migration for the php85 column on server_metas, and updated the PHP version selector Vue component."

### Key technical details
- Routes added/modified: ...
- Permissions or policies changed: ...
- Database migrations: ...
- Billing guards affected: ...
- Scripts modified: ...
```

### Section 3: Test Environment

Use this exact table format:

```
## Test Environment
| Field | Detail |
|-------|--------|
| **Staging URL** | https://... |
| **SSH Access** | user@host |
| **Branch** | branch-name (commit hash) |
| **Paid User** | email (User ID, Team ID, Server IDs) |
| **Free User** | email (User ID, Team ID, Server ID) |
| **Date** | YYYY-MM-DD |
```

### Section 4: Tests Performed

Each test category must include a **test case table** with evidence for every test case. Bullet lists without evidence are incomplete — every PASS and FAIL needs proof from staging.

```
## Tests Performed

### 4.1 Smoke Testing — PASS

| # | Test Case | Expected | Actual | Evidence | Verdict |
|---|-----------|----------|--------|----------|---------|
| 1 | Login page loads | Login form visible | Form rendered correctly | ![Login](qa-screenshots/01-login.png) | PASS |
| 2 | Dashboard loads | Shows servers and sites | All data visible | ![Dashboard](qa-screenshots/02-dashboard.png) | PASS |
| 3 | No console errors | Clean console | 0 errors | `browser_console_messages`: clean | PASS |

### 4.2 Sanity Testing — PASS

| # | Test Case | Expected | Actual | Evidence | Verdict |
|---|-----------|----------|--------|----------|---------|
| 1 | Feature works as described | [per PR] | [result] | [screenshot/SSH output] | PASS |
```

**Evidence types by test category:**

| Category | Primary Evidence |
|----------|-----------------|
| Smoke/Sanity | Screenshots + console checks |
| Regression | Screenshots of related features still working |
| Security (IDOR) | curl response showing 403 + screenshot of blocked access |
| End-to-End | Screenshots + SSH/Command Runner output + Tinker queries |
| API | curl response bodies with HTTP status codes |
| Performance | Network request timing from `browser_network_requests` |

Continue for every category tested (4.1 through 4.17). For categories skipped as irrelevant, do not include a subsection — just note them in "Areas Not Fully Tested" later.

### Section 5: Bugs Found

If no bugs found, write: `## Bugs Found` followed by "No bugs found."

For each bug, use this exact structure — every field is required:

```
## Bugs Found

### Bug #1: {Descriptive Title}

**Severity:** Critical / High / Medium / Low

**Summary:** One-sentence description of the bug.

**Root Cause:** `path/to/file.php` (line N) — brief explanation of what's wrong in the code and why it causes this behavior.

**Steps to Reproduce:**
1. Log in as {user email} (role: paid/free/admin)
2. Navigate to {exact URL}
3. {Exact action}
4. {Exact action}
5. Observe: {what happens}

> **Tool used:** {Playwright UI / curl / Tinker / SSH}
> **Exact input:** {the literal value entered, command run, or request sent}

**Expected Result:** {What should happen}

**Actual Result:** {What actually happened — include exact error messages, HTTP status codes, or UI behavior}

![Descriptive alt text showing the bug](qa-screenshots/XX-description.png)
```

The screenshot must be embedded inline using `![alt](path)` right after "Actual Result". Scroll to the specific element demonstrating the bug before capturing. Never write just the filename.

### Section 5.5: Logic Flaws (Business Logic Validation)

If Step 1.4 generated [BLV] test cases and any of them failed, report the logic flaws here. Logic flaws are distinct from regular bugs — they are design decisions that contradict domain best practices or expected behavior, not coding errors. If no BLV test cases were generated, or all passed, write: "No logic flaws identified."

For each logic flaw:

```
### Logic Flaw #1: {Descriptive Title}

**Severity:** Critical / High / Medium / Low (from consequence tier in EBS)
**Confidence:** High / Medium / Low (from Expected Behavior Specification)

**Expected behavior:** {What the feature SHOULD do, based on domain standards/user expectations}

**Actual behavior:** {What the implementation does instead}

**Domain basis:** {Why the expected behavior is correct — reference standards, practices, competitor behavior}

**Evidence:** {BLV test case results that confirmed the flaw — screenshots, SSH output, Tinker queries}

![Evidence screenshot](qa-screenshots/XX-blv-evidence.png)

**Suggested fix:** {Concrete recommendation for what the code should do instead}

**Developer response:** {If asked in Step 1.4.3: "Confirmed as intentional" / "Acknowledged as oversight" / "Not asked (high confidence)"}
```

**Severity guidelines for logic flaws:**
- **Critical:** Security feature with wrong logic (e.g., threat detection that flags legitimate traffic), billing calculation errors, data loss scenarios
- **High:** Feature that works but produces incorrect results, missing threshold/rate logic, incomplete algorithm
- **Medium:** Feature that mostly works but misses edge cases the domain requires, missing configuration for hardcoded values
- **Low:** Minor deviation from industry norm with low user impact

### Section 6: Observations (Pre-existing Issues)

Document pre-existing issues separately from PR bugs. If none, write "No pre-existing issues observed."

```
## Observations

### Observation #1: {Title}
**Severity:** Low (informational)
**Location:** `file.vue` line N
{Description of pre-existing behavior, why it's not a bug in this PR}
```

### Section 7: Regression Issues

Previously working functionality that broke, or "No regression issues found."

### Section 8: Performance Observations

Slow pages, heavy queries, or "All pages load within acceptable times."

### Section 9: Security Concerns

Summary table of any security findings with severity and recommended action, or "No security concerns found."

### Section 10: Areas Not Fully Tested

List anything you could not test and why. Use a table:

```
## Areas Not Fully Tested
| Area | Reason |
|------|--------|
| Server provisioning | Requires real cloud provider API call |
| Rate limiting | Requires sustained load testing |
```

### Section 11: Screenshots Summary

A summary table of all screenshots taken during the test session. Every screenshot must use `![alt](path)` in the Preview column.

```
## Screenshots
| # | Description | What It Proves | Preview |
|---|-------------|----------------|---------|
| 1 | Dashboard smoke test | Application loads correctly after PR merge | ![Dashboard smoke test](qa-screenshots/01-dashboard-smoke.png) |
| 2 | Free user upgrade prompt | Billing guard blocks free users properly | ![Free user upgrade prompt](qa-screenshots/02-free-user-blocked.png) |
```

### Section 12: Test Data Cleanup

Track every test record created and its cleanup status. If no test data was created, write: "No test data was created during this QA session."

```
## Test Data Cleanup
| Item | Action | Status |
|------|--------|--------|
| User ID 123 (qa-test@staging.example.com) | Deleted via Tinker | Cleaned |
| Team ID 456 (QA Test Team) | Deleted via Tinker | Cleaned |
```

### Section 13: Final Verdict

```
## Final Verdict
### PASS / PASS WITH MINOR ISSUES / FAIL

**Reasoning:** Explain why, referencing specific bugs and their severity.
```

If FAIL, include a checklist of items that must be fixed before merge:
```
- [ ] Fix item 1
- [ ] Fix item 2
```

---

## Post-Report Validation Checklist

Before saving the report, verify every item below. If any item fails, go back and fix the report.

- [ ] **All 13 sections present** — Title, PR Summary, Test Environment, Tests Performed, Bugs Found, Observations, Regression Issues, Performance Observations, Security Concerns, Areas Not Fully Tested, Screenshots, Test Data Cleanup, Final Verdict
- [ ] **Every screenshot embedded with `![alt](path)`** — search the report for any bare filenames like `qa-screenshots/...` that aren't inside `![]()`
- [ ] **Every bug has all required fields** — Severity, Summary, Root Cause (file + line), Steps to Reproduce, Tool used, Expected Result, Actual Result, embedded Screenshot
- [ ] **Every bug has a root cause** — file path and line number, not just "something is wrong"
- [ ] **Screenshots table is populated** — every screenshot taken during testing appears in the summary table with `![alt](path)` in Preview
- [ ] **Every test case has evidence** — each row in the test case tables has an Evidence column with a screenshot, SSH/Command Runner output, or Tinker query result — not code review
- [ ] **Test category verdicts are present** — every tested category heading ends with "— PASS" or "— FAIL"
- [ ] **Cleanup table is filled** — either cleanup records or "No test data was created"
- [ ] **Final verdict has reasoning** — not just "PASS" but why, referencing specific findings
- [ ] **Logic flaws reported if applicable** — if Step 1.4 generated BLV test cases, their results appear in the test case tables and any failed BLV tests are reported in Section 5.5 (Logic Flaws)

---

## Severity Classification

| Severity | Definition | Examples |
|----------|-----------|----------|
| **Critical** | Data loss, security breach, complete feature failure, blocks users entirely | IDOR allowing cross-user data access, server deletion by unauthorized user, 500 on login |
| **High** | Major feature broken but workaround exists, security risk without active exploitation | Billing guard missing on a feature, stored XSS, enterprise restrictions not enforced |
| **Medium** | Feature partially broken, UX significantly degraded, non-critical data issue | Wrong redirect losing context, API returning wrong error code, first user created without team |
| **Low** | Cosmetic, minor UX, doesn't affect functionality | Wrong page title, pagination showing all page numbers, misaligned icon |

## What Makes a Strong Report

Lessons from real QA reports (PR #3693, PR #4260):

### Evidence Depth
- **PR #3693:** Verified 14 lsphp85 packages via `dpkg -l`, confirmed OPCache binary version, traced frontend/backend guard asymmetry on OPCache toggle
- **PR #4260:** Documented triple-layer double-click protection (JS guard, UI disabled, loading state), verified backend idempotency

### Bug Reports
Include root cause with file and line:
```markdown
**Root Cause:** `app/Http/Controllers/API/PHPVersionController.php` (line 139) — `toggleOpcache()` has no version-specific guard. The method accepts any valid PHP version and dispatches the toggle script.
```

---

## Multi-PR Summary Report Template

When testing multiple PRs in a single session, generate this summary report **after** all individual PR reports are complete. Save it as `QA-Summary-Multi-PR.md` in the project root.

---

```markdown
# Multi-PR QA Summary Report

**Date:** YYYY-MM-DD
**Tester:** Claude (AI QA Engineer)
**Environment Mode:** Single environment / Multiple environments

## PRs Tested

| # | PR | Title | Branch | Verdict | Individual Report |
|---|-----|-------|--------|---------|-------------------|
| 1 | #1234 | Add PHP 8.5 support | feature/php85 | PASS | [QA-Report-PR-1234.md](QA-Report-PR-1234.md) |
| 2 | #1235 | Fix billing guard | fix/billing-guard | FAIL | [QA-Report-PR-1235.md](QA-Report-PR-1235.md) |

## Overall Summary

- **Total PRs tested:** N
- **Passed:** N
- **Failed:** N
- **Passed with minor issues:** N

{One paragraph summarizing the overall QA session — were the PRs related? Did they interact? Any patterns across PRs?}

## Cross-PR Observations

{Document any interactions, dependencies, or conflicts observed between PRs during testing. If PRs were independent and no cross-PR effects were observed, write: "No cross-PR interactions observed — each PR was tested independently."}

Examples of cross-PR observations:
- PR #1234 adds a new migration that conflicts with PR #1235's migration
- PR #1234 modifies a shared service that PR #1235 also depends on
- Both PRs modify the same Vue component, causing UI inconsistencies when deployed together

## Bugs Summary (All PRs)

| # | PR | Bug | Severity | Root Cause File |
|---|-----|-----|----------|-----------------|
| 1 | #1234 | OPCache toggle missing guard | Medium | `PHPVersionController.php:139` |
| 2 | #1235 | Billing guard bypass via API | High | `BillingMiddleware.php:42` |

If no bugs were found across any PR, write: "No bugs found across all tested PRs."

## Deployment Notes

{Document any deployment issues encountered during the session:}
- Merge conflicts, stash operations, failed checkouts
- Migration errors or conflicts between PRs
- Dependency installation issues (`composer install` / `npm run build` failures)
- Server state issues (uncommitted changes, wrong branch)

If deployment was smooth for all PRs, write: "All PRs deployed successfully without issues."

## Session Timeline

| Time | Action | PR | Notes |
|------|--------|----|-------|
| Start | Begin QA session | — | Environment info gathered |
| ... | Deployed PR #1234 | #1234 | Branch: feature/php85 |
| ... | Completed testing PR #1234 | #1234 | Verdict: PASS |
| ... | Cleanup PR #1234 test data | #1234 | All test data removed |
| ... | Deployed PR #1235 | #1235 | Branch: fix/billing-guard |
| ... | Completed testing PR #1235 | #1235 | Verdict: FAIL |
| End | Session complete | — | Summary report written |
```

---

### Multi-PR Summary Validation Checklist

Before saving the summary report, verify:

- [ ] **Every PR from the input appears in the "PRs Tested" table** — no PR is missing
- [ ] **Every PR has a link to its individual report** — and the linked file exists
- [ ] **Every bug from individual reports appears in "Bugs Summary"** — cross-check each individual report's bugs section
- [ ] **Verdicts match** — the verdict in the summary table matches the verdict in each individual report
- [ ] **Cross-PR observations are documented** — either specific interactions or "none observed"
- [ ] **Deployment notes cover all PRs** — any issues during deployment are logged
- [ ] **Session timeline is chronological** — actions are in the order they occurred
