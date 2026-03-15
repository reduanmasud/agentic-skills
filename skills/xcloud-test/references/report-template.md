# QA Report Template & Severity Classification

## File Naming

- PR-specific: `QA-Report-PR-{NUMBER}.md` in the project root
- Feature-specific: `QA-Report-{Feature-Name}.md` in the project root

## Report Template

```markdown
# QA Report: PR #{NUMBER} — {PR Title}

## PR Summary
Brief explanation of what the PR changes. Include key technical details:
routes added, permissions introduced, database changes, billing guards.

## Test Environment
| Field | Detail |
|-------|--------|
| **Staging URL** | https://... |
| **SSH Access** | user@host |
| **Branch** | branch-name (commit hash) |
| **Paid User** | email (User ID, Team ID, Server IDs) |
| **Free User** | email (User ID, Team ID, Server ID) |
| **Date** | YYYY-MM-DD |

## Tests Performed
### 4.1 Smoke Testing — PASS/FAIL
(Results in table or list format)

### 4.2 Sanity Testing — PASS/FAIL
...continue for all test categories performed (4.3 through 4.12)...

## Bugs Found

### Bug #N: {Descriptive Title}

**Severity:** Critical / High / Medium / Low

**Summary:** One-sentence description of the bug.

**Root Cause:** `path/to/file.php` (line N) — brief explanation of what's wrong in the code and why it causes this behavior.

**Steps to Reproduce:**
1. Log in as {user email} (role: paid/free/admin)
2. Navigate to {exact URL, e.g., `https://s5.staging.example.com/site/841/caching`}
3. {Exact action — "Enter `$host` in the 'Cache Exclusion HTTP URL Rules' textarea"}
4. {Exact action — "Click the 'Save Changes' button"}
5. Observe: {what happens — "A validation error appears: '...'"}

> **Tool used:** {Playwright UI / curl / Tinker / SSH}
> **Exact input:** {the literal value entered, command run, or request sent}

**Expected Result:** {What should happen}

**Actual Result:** {What actually happened — include exact error messages, HTTP status codes, or UI behavior}

**Screenshot:** (must show the specific element demonstrating the bug — scroll to the evidence if below viewport)

![XX-description](qa-screenshots/XX-description.png)

## Regression Issues
Previously working functionality that broke, or "No regression issues found."

## Performance Observations
Slow pages, heavy queries, or "All pages load within acceptable times."

## Security Concerns
Summary table of any security findings with severity and recommended action.

## Areas Not Fully Tested
List anything you could not test and why (e.g., "Server provisioning —
requires real cloud provider API call", "Rate limiting — requires sustained
load testing").

## Screenshots
| # | Description | What It Proves | Preview |
|---|-------------|----------------|---------|
| 1 | Description | What this screenshot demonstrates as evidence | ![01-name](qa-screenshots/01-name.png) |

## Test Data Cleanup
| Item | Action | Status |
|------|--------|--------|
| User ID X (email) | Deleted via Tinker | Cleaned |

## Final Verdict
### PASS / PASS WITH MINOR ISSUES / FAIL

**Reasoning:** Explain why, referencing specific bugs and their severity.

If FAIL, include a checklist of items that must be fixed before merge:
- [ ] Fix item 1
- [ ] Fix item 2
```

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

### Observations Section
Document pre-existing issues separately from PR bugs. Use "Observation" label with a note that it's not a regression:
```markdown
### Observation #1: {Title}
**Severity:** Low (informational)
**Location:** `file.vue` line N
{Description of pre-existing behavior, why it's not a bug in this PR}
```

### Areas Not Fully Tested
Be honest about what you couldn't test and why:
```markdown
| Area | Reason |
|------|--------|
| ARM server testing | No ARM server available on staging |
| Rate limiting | Requires sustained load testing |
```

### Bug Reports
Include root cause with file and line:
```markdown
**Root Cause:** `app/Http/Controllers/API/PHPVersionController.php` (line 139) — `toggleOpcache()` has no version-specific guard. The method accepts any valid PHP version and dispatches the toggle script.
```
