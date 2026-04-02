# Playwright MCP Browser Testing Guide

## Tool Inventory

Two Playwright MCP servers may be available. **Prefer the plugin version:**

| Priority | Prefix | When to use |
|----------|--------|-------------|
| 1st (preferred) | `mcp__plugin_playwright_playwright__` | Default — try this first |
| 2nd (fallback) | `mcp__playwright__` | If plugin version fails |

All tool names below use short names (e.g., `browser_navigate`). Prepend the active prefix. Available tools:

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Go to a URL |
| `browser_navigate_back` | Go back in history |
| `browser_snapshot` | Get page accessibility tree with element refs |
| `browser_click` | Click an element by ref |
| `browser_fill_form` | Fill text inputs by ref |
| `browser_type` | Type text character by character (for autocomplete, search) |
| `browser_press_key` | Press keyboard keys (Enter, Tab, Escape, etc.) |
| `browser_hover` | Hover over an element |
| `browser_select_option` | Select from dropdown/select elements |
| `browser_drag` | Drag and drop between elements |
| `browser_file_upload` | Upload files to file input elements |
| `browser_take_screenshot` | Capture screenshot to file |
| `browser_console_messages` | Get JavaScript console output |
| `browser_network_requests` | Get network request log |
| `browser_evaluate` | Run JavaScript in the page context |
| `browser_run_code` | Run Playwright code snippets |
| `browser_wait_for` | Wait for text, URL change, or network idle |
| `browser_handle_dialog` | Accept/dismiss alert/confirm/prompt dialogs |
| `browser_tabs` | List and switch between browser tabs |
| `browser_resize` | Resize the browser viewport |
| `browser_close` | Close the browser |
| `browser_install` | Install browser binaries |

## Core Workflow: Navigate -> Snapshot -> Interact -> Verify

**This cycle is mandatory.** You cannot interact with elements without first taking a snapshot.

```
1. browser_navigate  →  Load the page
2. browser_snapshot   →  Get accessibility tree with element [ref] IDs
3. browser_click / browser_fill_form  →  Interact using refs from snapshot
4. browser_snapshot   →  Re-snapshot to verify state changes
5. browser_take_screenshot  →  Capture visual evidence
```

**Why snapshots are required:** Element refs are ephemeral accessibility tree IDs, NOT CSS selectors. They are assigned when you snapshot and become invalid after any DOM mutation (page navigation, Inertia visit, AJAX response, modal open/close). Always re-snapshot after any interaction before the next one.

**Common mistake:** Trying to click a ref from a previous snapshot after the page has changed. If you get a "ref not found" error, take a new snapshot.

## Authentication Flow

### Login Steps (from xCloud e2e test patterns)

1. Navigate to `{staging-url}/login`
2. **Dismiss cookie banner** — look for "Accept All" button, click if visible (may not appear if cookies already accepted)
3. Fill email: find the email input ref from snapshot, use `browser_fill_form`
4. Fill password: find the password input ref, use `browser_fill_form`
5. Click the submit/login button ref
6. **Wait for Inertia redirect** — use `browser_wait_for` with URL change (URL should no longer contain `/login`)
7. Take a snapshot to verify you're on the dashboard

```
browser_navigate → {staging-url}/login
browser_snapshot → find cookie banner "Accept All" button
browser_click → dismiss cookie banner (if present)
browser_snapshot → find email input, password input, submit button refs
browser_fill_form → fill email field
browser_fill_form → fill password field
browser_click → click submit button
browser_wait_for → URL no longer contains "/login"
browser_snapshot → verify dashboard loaded
```

### Logout Flow

To log out of the current session:

1. **Click on the profile/avatar** — look for the user's name or avatar in the top-right corner of the page
2. `browser_snapshot` → find the profile menu element ref
3. `browser_click` → click the profile/avatar ref
4. `browser_snapshot` → find the "Log Out" or "Logout" option in the dropdown menu
5. `browser_click` → click the Logout ref
6. `browser_wait_for` → wait for URL to contain `/login` (redirect to login page)
7. `browser_snapshot` → verify you're on the login page

```
browser_snapshot → find profile/avatar ref in top-right
browser_click → click profile/avatar
browser_snapshot → find "Log Out" menu item
browser_click → click Log Out
browser_wait_for → URL contains "/login"
browser_snapshot → verify login page
```

### Multi-Account Testing

When switching between user roles, choose the appropriate method:

**Option A: Logout and re-login (preferred for testing logout behavior)**
1. Follow the **Logout Flow** above to log out
2. Authenticate as the new user on the login page
3. Track which screenshots belong to which role (include role in screenshot name)

**Option B: Close browser (guaranteed clean session)**
1. **Close the browser** with `browser_close`
2. Navigate to the login page fresh
3. Authenticate as the new user
4. Track which screenshots belong to which role (include role in screenshot name)

Use **Option A** when you need to verify logout works or want to test session cleanup. Use **Option B** when you need a guaranteed clean slate (clears cookies, localStorage, all session state).

**End-of-testing close:** The browser is also closed at the end of all testing (Step 6.7 in SKILL.md) before the report is written. This is separate from role-switching closes during testing.

## xCloud UI Patterns

### Inertia.js Page Transitions
- xCloud uses Inertia.js — page transitions do NOT trigger full page reloads
- After clicking a link, use `browser_wait_for` (text or URL change) instead of waiting for navigation
- Always re-snapshot after an Inertia visit — the entire DOM is replaced

### DataTableV2 Tables
- Tables use `DataTableV2` component with `XTh`, `XTr`, `XTd` sub-components
- Rows have clickable elements — snapshot to find the right refs
- Pagination links appear at the bottom if data spans multiple pages

### Modal Dialogs
- Modals overlay the page — after triggering a modal, snapshot to get the modal's element refs
- Confirmation modals typically have "Yes" / "Cancel" buttons
- Delete confirmations use `useFlash().deleteConfirmation()` pattern

### Toast Notifications
- Success/error messages appear as toast notifications
- After an action, snapshot to check for toast text in the accessibility tree
- Toasts auto-dismiss — capture quickly or check console/network instead

### Switch/Toggle Components
- Toggle switches render as clickable elements — use `browser_click` on the switch ref
- Check `:disabled` state in snapshot attributes
- Some toggles trigger immediate API calls, others require a save button

### Sidebar Navigation
- Main nav is in a sidebar — snapshot reveals all nav link refs
- Sub-navigation uses tabs within pages

## Screenshot Management

### Cloudinary Upload (Preferred When Available)

**Before taking any screenshots**, check if all 3 Cloudinary env vars are set:

```bash
# Check all 3 required Cloudinary env vars
echo "CLOUDINARY_CLOUD_NAME=${CLOUDINARY_CLOUD_NAME:-(not set)}"
echo "CLOUDINARY_API_KEY=${CLOUDINARY_API_KEY:-(not set)}"
echo "CLOUDINARY_API_SECRET=${CLOUDINARY_API_SECRET:-(not set)}"
```

If ALL three — `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` — are set, **upload every screenshot to Cloudinary** after capturing and use the returned URL in the report. This makes reports readable on GitHub without local file paths.

If any of the 3 vars is missing, fall back to local paths: `![alt](qa-screenshots/XX-description.png)`

**Upload command (run after each screenshot):**
```bash
curl -s -X POST "https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload" \
  -F "file=@qa-screenshots/XX-description.png" \
  -F "upload_preset=ml_default" \
  -F "folder=qa-reports" \
  -F "api_key=${CLOUDINARY_API_KEY}" \
  -F "timestamp=$(date +%s)" \
  -F "signature=$(echo -n "folder=qa-reports&timestamp=$(date +%s)&upload_preset=ml_default${CLOUDINARY_API_SECRET}" | shasum -a 256 | head -c 64)" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['secure_url'])"
```

**If signed upload fails**, fall back to unsigned upload:
```bash
curl -s -X POST "https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload" \
  -F "file=@qa-screenshots/XX-description.png" \
  -F "upload_preset=ml_default" \
  -F "folder=qa-reports" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['secure_url'])"
```

**In the report, use the Cloudinary URL:**
```markdown
![Dashboard smoke test](https://res.cloudinary.com/xxxx/image/upload/v1234/qa-reports/01-dashboard-smoke.png)
```

### Naming Convention

**Naming convention:** `qa-screenshots/XX-description.png`
- Sequential numbering: `01-`, `02-`, etc.
- Descriptive suffix: `01-dashboard-smoke-test.png`, `02-free-user-blocked.png`
- Include role when testing multiple accounts: `07-free-user-upgrade-prompt.png`

**When to capture:**
- Each major test step (evidence of PASS)
- Every bug found (before and after)
- Before/after comparisons for UI changes
- State transitions (installing → installed)
- Error messages and validation feedback

**Directory:** Always save to `qa-screenshots/` in the project root.

### Capturing Evidence, Not Pages

Screenshots are evidence — they must show the **specific element** that proves the bug or fix, not just the general page.

**Scroll to the evidence first.** If the relevant element (error message, key list, status badge, changed data) is below the viewport, scroll it into view before taking the screenshot:
```
browser_evaluate: document.querySelector('.ssh-keys-list').scrollIntoView({behavior: 'instant', block: 'center'})
browser_take_screenshot → now captures the actual evidence
```

**Capture at the right moment.** Transient elements like toast notifications auto-dismiss within seconds. Screenshot immediately after the action that triggers them — don't navigate or interact first:
```
browser_click → (triggers action)
browser_take_screenshot → capture toast/success message NOW
browser_snapshot → then continue testing
```

For state transitions, capture each state separately:
```
browser_take_screenshot → 04-php85-before-install.png (shows "Install" button)
browser_click → click Install
browser_take_screenshot → 05-php85-installing.png (shows "Installing" status)
browser_wait_for → wait for completion
browser_take_screenshot → 06-php85-installed.png (shows "Installed" badge)
```

**Before/after must be visually distinct.** If your "before" and "after" screenshots look identical, you captured the wrong area. The element that changed must be visible in both screenshots. If the change is in a list, table row, or section below the fold — scroll there before each capture.

**Bad example:** Two screenshots of the top of a page — SSH key list (the bug) is cut off below the viewport in both.
**Good example:** Both screenshots scrolled to the SSH key list — "before" shows unfiltered keys, "after" shows filtered keys.

## Waiting & Timing — Which Tool to Use

Choosing the wrong wait strategy is the most common source of flaky interactions. Use this table:

| Situation | Tool | Example |
|-----------|------|---------|
| Page navigation (full URL change) | `browser_wait_for` with URL | After clicking a nav link, wait for URL to contain `/dashboard` |
| Inertia page transition (no full reload) | `browser_wait_for` with text | After Inertia visit, wait for expected heading text to appear |
| Action completes with toast/message | `browser_take_screenshot` immediately | After clicking Submit, screenshot NOW before toast auto-dismisses |
| Element below viewport needs capturing | `browser_evaluate` scroll, then screenshot | `document.querySelector('.target').scrollIntoView({block:'center'})` |
| Need to interact with new DOM elements | `browser_snapshot` | After any DOM mutation, re-snapshot to get fresh refs |
| Async operation (install, deploy) | `browser_wait_for` with text + polling | Wait for status text to change from "Installing" to "Installed" |
| Page seems stuck or loading | `browser_wait_for` with network idle | Wait for all network requests to settle |
| Modal/dialog needs to open fully | `browser_snapshot` after a beat | Trigger the modal, then snapshot to get modal element refs |

**Key rule:** After every interaction that changes the DOM, you need a fresh `browser_snapshot` before the next interaction. Refs from the old snapshot are stale and will fail.

**Common mistake:** Using `browser_wait_for` when you should just `browser_snapshot`. If the page has already changed (you can tell because the interaction succeeded), just snapshot — don't wait for something that already happened.

## Error Detection Workflow

### After Every Page Load
1. Run `browser_console_messages` to check for JavaScript errors
2. Run `browser_network_requests` to check for failed API calls (4xx, 5xx)

### Known Pre-Existing Errors (Filter These Out)
These are known issues unrelated to any PR — do not report them as bugs:
- DuckDuckGo favicon 404 (`icons.duckduckgo.com`)
- WordPress.org plugin icon 404s (`ps.w.org`)
- ngrok CSP font-related errors (when using ngrok tunnels)

### Investigating Errors
- **Console error with stack trace:** Note the file and line number, cross-reference with the PR diff
- **Network 500 error:** Check server logs via SSH (`tail -n 200 {app-path}/storage/logs/laravel-$(date +%Y-%m-%d).log`)
- **Network 422 error:** Validation failure — check the response body for field-specific errors

## Form Testing Patterns

| Input Type | Tool | Notes |
|-----------|------|-------|
| Text input | `browser_fill_form` | Clears existing value and types new one |
| Password | `browser_fill_form` | Same as text input |
| Checkbox | `browser_click` | Click the checkbox ref to toggle |
| Toggle/Switch | `browser_click` | Click the switch ref |
| Select/Dropdown | `browser_select_option` | Pass the option value |
| File upload | `browser_file_upload` | Provide file path |
| Textarea | `browser_fill_form` | Same as text input |
| Search/autocomplete | `browser_type` | Type character by character to trigger suggestions |

### Validation Testing
1. Submit form with empty required fields — verify error messages appear
2. Submit with invalid formats (email, URL) — verify specific error text
3. Submit with boundary values (max length, special characters)
4. After fixing errors, verify error messages clear on resubmission

## Debugging Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| "ref not found" error | Stale refs from old snapshot | Take a new `browser_snapshot` |
| Can't click element | Element behind overlay/modal | Dismiss the overlay first, re-snapshot |
| Page seems stuck | Inertia request in flight | Use `browser_wait_for` with URL or text |
| Login redirects to unexpected page | Session timeout or billing redirect | Check URL, may need `force.payment` middleware redirect |
| Form submit doesn't respond | CSRF token expired | Close browser, start fresh session |
| Elements missing from snapshot | Page not fully loaded | Use `browser_wait_for` with expected text |
| Screenshot is blank/partial | Page still rendering | Add `browser_wait_for` before screenshot |
