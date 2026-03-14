# Playwright MCP Browser Testing Guide

## Tool Inventory

All browser interactions use the `mcp__plugin_playwright_playwright__` prefix. Available tools:

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

### Multi-Account Testing

When switching between user roles:
1. **Close the browser** with `browser_close`
2. Navigate to the login page fresh
3. Authenticate as the new user
4. Track which screenshots belong to which role (include role in screenshot name)

Do NOT try to log out and log back in — closing the browser ensures a clean session.

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

**Naming convention:** `qa-screenshots/XX-description.png`
- Sequential numbering: `01-`, `02-`, etc.
- Descriptive suffix: `01-dashboard-smoke-test.png`, `02-free-user-blocked.png`
- Include role when testing multiple accounts: `07-free-user-upgrade-prompt.png`

**When to capture:**
- Each major test step (evidence of PASS)
- Every bug found (before and after if applicable)
- Before/after comparisons for UI changes
- State transitions (installing → installed)
- Error messages and validation feedback

**Directory:** Always save to `qa-screenshots/` in the project root.

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
