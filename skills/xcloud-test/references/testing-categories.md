# Testing Categories

Perform ALL applicable categories for every QA session. Skip a category only if it is genuinely irrelevant to the PR (e.g., no API endpoints → skip API testing).

## Evidence Requirement (Applies to ALL Categories)

**Every test case must produce evidence.** Use this format in the report:

| # | Test Case | Expected | Actual | Evidence | Verdict |
|---|-----------|----------|--------|----------|---------|
| 1 | Login page loads correctly | Login form visible | Form rendered | ![Login](qa-screenshots/01-login.png) | PASS |
| 2 | PHP packages installed on server | lsphp85 packages present | 14 packages found | SSH: `dpkg -l \| grep lsphp85` | PASS |
| 3 | Free user blocked from feature | Upgrade prompt shown | 500 error instead | ![500 error](qa-screenshots/05-error.png) | FAIL |

**Evidence types:** Screenshots, SSH/Command Runner output, Tinker query results, curl responses, browser console/network logs. Code review is NOT evidence.

## Test Case Generation

The checklists below are **starting points** — generate additional PR-specific test cases. For each changed file/feature, create test cases for: happy path, error path, edge cases, role variations, and regression of related features. See Step 4.0 in SKILL.md for minimum counts.

## 4.1 Smoke Testing

**Purpose:** Verify the application is stable and not broken by the PR.

**Checklist:**
- Login page loads, authentication works
- Dashboard loads without errors
- Key pages affected by the PR load correctly
- No HTTP 500 errors on any route
- Check `browser_console_messages` for JavaScript errors on every page
- Check `browser_network_requests` for failed API calls

**xCloud-specific:** After login, verify the dashboard shows servers, sites, and billing data. The sidebar navigation should load all links.

## 4.2 Sanity Testing

**Purpose:** Verify the specific feature or fix introduced by the PR works as intended.

**Checklist:**
- The intended behavior works as described in the PR description
- UI renders correctly (use snapshots to verify element states)
- Database changes are correct (verify via Tinker/SSH)
- API responses are correct (test via curl or Playwright network requests)
- Compare actual behavior against what the PR description claims

**Before/After context is required.** When reporting sanity test results, make it clear what was wrong before and what's working now. The reader should understand the improvement without having to read the PR diff.

```
### 4.2 Sanity Testing — PASS

**Previous behavior:** Free-plan users could access the PHP 8.5 installer via direct URL, bypassing the billing guard. No upgrade prompt was shown.

**After fix:** Free-plan users now see the upgrade prompt when navigating to the PHP version page. The billing guard middleware correctly blocks access.

![Free user sees upgrade prompt on PHP version page](qa-screenshots/04-free-user-upgrade-prompt.png)
```

**Tip:** Read the PR description carefully. Test exactly what it claims to fix or add — this catches cases where the fix is incomplete or addresses a different problem than described.

## 4.3 Regression Testing

**Purpose:** Verify the PR did NOT break existing functionality.

**Checklist:**
- Authentication flows (login, logout, session persistence)
- Dashboard widgets and data display
- Navigation — all sidebar links work
- CRUD operations on affected models
- Permission systems and validation rules
- Previously fixed bugs haven't returned

**xCloud-specific:** Test the pages and features that share code with the PR's changes (identified in Step 1.2 cross-feature analysis).

## 4.4 Scenario Testing

### Happy Path
Normal user workflow with valid inputs, successful submissions, expected navigation. This is the primary use case described in the PR.

### Unhappy Path
Invalid inputs and error conditions:
- Wrong email formats, missing required fields
- Invalid file types, wrong data formats
- Values outside allowed ranges
- Verify error messages are clear, specific, and user-friendly (not raw exceptions)

### Edge Cases
Boundary values and limits:
- Maximum character lengths for text fields
- Zero, negative, or extremely large numeric values
- Empty strings vs. null vs. whitespace
- Large file uploads near size limits
- Unicode, emoji, and special characters in text fields

### Corner Cases
Combined extremes:
- Maximum-length field with special characters
- Rapid form resubmission during processing
- Concurrent operations on the same resource
- Navigating away mid-operation and returning

### Monkey Testing
Random, unscripted interactions:
- Click buttons rapidly multiple times
- Enter unexpected characters: emojis, unicode, SQL fragments (`'; DROP TABLE--`), HTML tags
- Navigate back/forward mid-form
- Submit completely empty forms
- Paste extremely long strings

## 4.4a End-to-End Action Execution (MANDATORY)

**This is the most critical test.** Don't just verify the feature appears in the UI — **actually perform the core action** on staging and verify the full result chain.

The difference between "PHP 8.5 shows an Install button" and "PHP 8.5 was installed, and we verified 14 packages on the server" is the difference between superficial QA and real QA.

**Steps:**
1. **Execute the action:** Click Install, Submit, Create, Delete, Toggle — whatever the PR's primary feature enables
2. **Wait for completion:** Watch for status changes, loading indicators, success/error messages
3. **Verify UI state:** Screenshot the result — does the page reflect the completed action?
4. **Verify server-side state** (for server operations): Use SSH or Command Runner to confirm:
   - Packages installed/removed: `dpkg -l | grep <package>` or `apt list --installed`
   - Config files created/modified: `cat`, `grep` on expected config paths
   - Binaries functional: run the binary (e.g., `php -v`, `node -v`)
   - Services running: `systemctl status <service>`
   - File system changes: `ls -la <path>`, `find <dir> -name <pattern>`
5. **Verify database/meta state:** Use Tinker to confirm records, metadata, and flags are correct
6. **Test related features still work:** After the action, do related features (that depend on the same data) still behave correctly?

> Load `references/ssh-server-commands.md` for SSH verification patterns.

**Command Runner shortcut:** Navigate to Server > Management > Commands in xCloud to run verification commands through the UI without SSH.

## 4.5 API Testing

> Full methodology is in `references/security-testing.md` — load it for auth testing, content type testing, pagination edge cases, and enterprise API specifics.

If the PR introduces or modifies API endpoints, test:
- **Authentication:** Valid token, no token, invalid token
- **Validation:** Missing required fields, wrong types, boundary values
- **Content type handling:** Wrong content types should return 415 or 422
- **Pagination edge cases:** Negative page, huge per_page, page beyond range
- **Enterprise API:** If applicable, test enterprise-specific routes and response format

## 4.6 Security Testing

> Full methodology is in `references/security-testing.md` — load it for IDOR methodology, guard asymmetry testing, XSS payloads, CSRF verification, and policy testing via Tinker.

For every PR, check at minimum:
- **IDOR:** Can User B access User A's resources by changing IDs in URLs?
- **Guard asymmetry:** For every UI-disabled feature, does the backend API also block it?
- **Input sanitization:** Test XSS payloads in all text fields touched by the PR
- **Sensitive data exposure:** Check API responses don't leak passwords, tokens, or full keys
- **Authorization policies:** Verify policy methods via Tinker for affected models

## 4.7 xCloud-Specific Checks

Based on what the PR touches, verify these platform patterns:

### Billing Plan Guards
- Features gated by billing plan should block free users with a proper upgrade prompt (not a 500 error)
- Test with `$server->isFreePlan()` and `$server->team->isTrailMode()` via Tinker
- Verify `upgrade-plan.required` middleware is on relevant routes
- Free plan users should see upgrade prompts, not raw errors or blank pages

### Whitelabel Isolation
- Whitelabel users should only see their own reseller's branding and data
- Resources scoped to whitelabel should not leak across whitelabel boundaries
- Test with a whitelabel user account if the PR touches whitelabel-scoped features

### Enterprise Feature Exclusions
- Enterprise plans have `exclude_features` — verify sidebar hides restricted items
- Backend should return 403 for excluded features, not just hide the UI link
- Check `$team->getMeta('exclude_features', [])` via Tinker

### Team Permissions
- Actions requiring `hasTeamPermission()` should fail for team members without that permission
- Test with a non-owner team member if the PR adds or modifies permission checks
- Verify both UI disabling and backend enforcement

### Server Stack Checks
- Features that exclude certain server stacks (e.g., `docker_nginx`) should hide/disable correctly
- Verify the correct stack enum is checked: `$server->stack->isOpenLiteSpeed()`, `$server->stack->isNginx()`, etc.

### Site Type Handling
- Use `SiteType` enum values, not hardcoded strings
- Verify behavior across relevant site types (WordPress, Laravel, Custom PHP, etc.)

## 4.8 Usability Testing

**Checklist:**
- Broken layouts or misaligned elements
- Confusing navigation or missing breadcrumbs
- Unclear error messages (raw exception text vs. user-friendly message)
- Missing loading states or feedback after actions
- **Table sorting:** If a table has sortable columns, click **every** sortable column header to verify ascending/descending sort works correctly. Different data types (strings, dates, numbers, statuses) can have different sorting bugs — don't just check one column and move on
- Pagination: uses ellipsis for large page counts, correct page sizes
- Responsive behavior if applicable
- Accessibility: buttons have labels, form fields have labels

## 4.9 Performance Observations

**Checklist:**
- Page load times (note anything > 3 seconds)
- N+1 query indicators (check Laravel Debugbar if available, or `laravel.log` for slow queries)
- Heavy SSH script execution times
- Excessive API calls visible in `browser_network_requests`
- Large response payloads

## 4.10 Error Recovery / Failure Path Testing

xCloud runs scripts on remote servers — operations fail in production. Users expect clear feedback and a way to recover. Test what happens when things go wrong.

### General Failure Patterns

- **Mid-operation failure:** If applicable, simulate or observe what happens when a server operation fails. Does the status get stuck on "Installing" / "In progress", or does it correctly transition to "Failed"?
- **Retry behavior:** After a failure, can the user retry? Does it work correctly the second time, or does leftover state cause issues?
- **UI feedback on failure:** Does the user see a clear error message, or does the page just hang? Check for proper error toasts, status badge updates, and log entries.
- **Queue job failures:** Check the `failed_jobs` table via Tinker after operations:
  ```php
  DB::table('failed_jobs')->latest()->first();
  ```
- **Graceful degradation:** If the feature depends on an external service or server state, what happens when that dependency is unavailable?

### xCloud-Specific Failure Scenarios

These are the real-world failures xCloud users hit. If the PR touches any of these areas, test the failure path:

| Scenario | What to check | How to verify |
|----------|---------------|---------------|
| **SSH timeout during script execution** | Does the status get stuck, or does it timeout gracefully? Does the UI show a meaningful error? | Check `failed_jobs` table and `laravel.log` for timeout exceptions |
| **Partial script execution** | If a script installs packages but fails on config, is the state consistent? Can the user retry without duplicating what already succeeded? | SSH to check what was installed vs. what was configured; check model status in Tinker |
| **Queue job timeout** | Long-running jobs (package installs, backups) may exceed the queue timeout. Does the job get retried or marked as failed? | `DB::table('failed_jobs')->latest()->first()` — check the exception message for timeout |
| **Server provisioning failure** | If server creation fails partway, is the server record cleaned up or left in a stuck "creating" state? | Check `$server->status` in Tinker; verify the UI shows a clear failure state |
| **DNS propagation delays** | Site creation may succeed in the database but DNS isn't ready yet. Does the UI handle the interim state? | Navigate to the site immediately after creation — it should show a pending/propagating status, not a broken page |
| **SSL certificate failures** | Let's Encrypt rate limits, DNS not ready, or domain validation fails. Does the error surface clearly? | Check the SSL status in UI and `laravel.log` for certificate-related errors |
| **Concurrent operations on same server** | Two operations dispatched to the same server simultaneously. Does the queue handle ordering, or do scripts collide? | Trigger two actions quickly and check if both complete or if one fails with a lock/conflict error |
| **Disk space exhaustion** | Backup or log rotation fills the disk. Does the operation fail gracefully? | Check `df -h` on the server after heavy operations |

## 4.11 State Transition Testing

xCloud entities have status flows (server: `creating -> active -> suspended`, PHP version: `not_installed -> installing -> installed`, site: `creating -> active`). Invalid transitions cause data corruption and stuck states.

- **Duplicate action prevention:** Can you trigger the same action twice on a resource already in a transitional state? (e.g., click "Install" on a PHP version that's already "Installing")
- **Button/UI state during transitions:** Are action buttons correctly disabled while an operation is in progress?
- **Status consistency:** After an operation completes, does the status in the UI, database, and server meta all agree? Check via:
  - UI: Playwright snapshot of status badges/labels
  - Database: Tinker query on the model's status column
  - Server meta: `$server->getServerInfo(...)` or `$model->getMeta(...)`
- **Invalid state access:** Navigate directly to a URL that assumes a certain state (e.g., site settings page for a site still "creating") — does it handle gracefully?

## 4.12 Idempotency / Double-Submit Testing

Users double-click. Networks retry. Test that repeated actions don't cause duplicate side effects.

- **Rapid double-click:** Click the primary action button twice rapidly — does it dispatch two jobs, create two records, or run two scripts? Use Playwright to click, then immediately click again before the page updates.
- **Form resubmission:** Submit a form, use browser back, submit again — does it create a duplicate?
- **Script idempotency:** If the PR modifies a server script, would running it twice break anything? Check if the script uses guards like `if [ -f ... ]` or `dpkg -l | grep` before installing.
- **API replay:** Send the same API request twice in quick succession via curl — does the backend handle it correctly (idempotency key, duplicate check, or graceful no-op)?

**Real example (PR #4260):** The "Refresh All" button had triple protection: JS guard (`if (refreshing.value) return`), UI disabled (`:disabled="refreshing"`), and loading indicator (`:loading="refreshing"`). And the backend operation was inherently idempotent. Document all layers of protection you find.
