# Playwright CLI Browser Testing Guide

## Tool Inventory

All browser interactions use **playwright-cli via Bash** — NOT the MCP plugin tools.
Each command is a separate Bash call. The CLI maintains browser session state between commands automatically.

| Command | Purpose |
|---------|---------|
| `playwright-cli navigate <url>` | Navigate to a URL |
| `playwright-cli snapshot` | Compact YAML listing element refs (e.g. e21) — read output to determine next action |
| `playwright-cli click <ref-or-selector>` | Click element by ref (e21) or text/CSS selector |
| `playwright-cli fill "<selector>" "<value>"` | Fill a text input field |
| `playwright-cli select "<selector>" "<value>"` | Choose a dropdown option |
| `playwright-cli press "<key>"` | Press a keyboard key (Enter, Tab, Escape, etc.) |
| `playwright-cli screenshot --path <file>` | Save screenshot to disk — NOT injected into context |
| `playwright-cli evaluate "<js>"` | Run JavaScript in the page context |
| `playwright-cli wait-for-text "<text>"` | Wait until text appears on the page |
| `playwright-cli close && pkill -f chromium 2>/dev/null \|\| true` | Close browser and force-kill any residual process — MANDATORY at journey end |

## Core Workflow: navigate → snapshot → interact → snapshot → screenshot

**This cycle is mandatory.** Always snapshot after navigating or after any DOM change to get fresh element refs.

```
1. playwright-cli navigate <url>            # load the page
2. playwright-cli snapshot                  # read YAML output — find element refs
3. playwright-cli click <ref>               # interact using refs from snapshot
4. playwright-cli snapshot                  # re-snapshot to verify state changed
5. playwright-cli screenshot --path <file>  # save visual evidence to disk
```

**Why snapshots are required:** Element refs (e.g. `e21`) are ephemeral — they are assigned on each snapshot and become invalid after any DOM mutation (navigation, Inertia visit, AJAX response, modal open/close). Always re-snapshot after any interaction before the next one.

**Common mistake:** Using a ref from an old snapshot after the page has changed. If a click fails, take a fresh snapshot and use the new ref.

## Authentication Flow

### Login Steps

```bash
playwright-cli navigate {staging-url}/login
playwright-cli snapshot                          # find cookie banner if present
playwright-cli click "Accept All"                # dismiss cookie banner (skip if not found)
playwright-cli snapshot                          # find email input, password input, submit button
playwright-cli fill "[name=email]" "<email>"
playwright-cli fill "[name=password]" "<password>"
playwright-cli click "[type=submit]"
playwright-cli wait-for-text "Dashboard"         # wait for redirect away from /login
playwright-cli snapshot                          # verify authenticated state
```

### Logout Flow

```bash
playwright-cli snapshot                          # find profile/avatar in top-right
playwright-cli click "<profile-ref>"             # click avatar
playwright-cli snapshot                          # find Log Out menu item
playwright-cli click "Log Out"
playwright-cli wait-for-text "Login"             # wait for redirect to login page
playwright-cli snapshot                          # verify on login page
```

### Multi-Account Testing (Switching Roles)

**Option A — logout and re-login** (when testing logout behavior):
1. Follow logout flow above
2. Login as new user

**Option B — fresh browser** (guaranteed clean session, clears all cookies and localStorage):
```bash
playwright-cli close && pkill -f chromium 2>/dev/null || true
playwright-cli navigate {staging-url}/login
# login as new user
```

Use **Option B** when you need a guaranteed clean slate between roles.

## xCloud UI Patterns

### Inertia.js Page Transitions
- xCloud uses Inertia.js — page transitions do **not** trigger full page reloads
- After clicking a nav link: `playwright-cli wait-for-text "<expected heading>"` instead of waiting for navigation
- Always re-snapshot after an Inertia visit — the entire DOM is replaced

### DataTableV2 Tables
- Tables use `DataTableV2` with `XTh`, `XTr`, `XTd` sub-components
- Rows have clickable elements — snapshot to find the correct refs
- Pagination appears at the bottom if data spans multiple pages

### Modal Dialogs
- Modals overlay the page — after triggering a modal, snapshot to get the modal's element refs
- Confirmation modals typically have "Yes" / "Cancel" buttons
- Delete confirmations use `useFlash().deleteConfirmation()` pattern

### Toast Notifications
- Success/error toasts appear and auto-dismiss within seconds
- After an action: `playwright-cli screenshot --path <file>` immediately before taking another action
- Check snapshot YAML for toast text — it appears as a text node in the accessibility tree

### Switch/Toggle Components
- Toggle switches are clickable elements — `playwright-cli click <switch-ref>`
- Check snapshot YAML for `:disabled` attribute before clicking
- Some toggles trigger immediate API calls; others require a save button

### Sidebar Navigation
- Main nav is a sidebar — snapshot reveals all nav link refs
- Sub-navigation uses tabs within pages

## Screenshot Management

### Directory and Naming

Save all screenshots to `qa-screenshots/pr<N>/` with sequential naming:
```
qa-screenshots/pr42/01-login.png
qa-screenshots/pr42/02-php-install-before.png
qa-screenshots/pr42/03-php-install-after.png
qa-screenshots/pr42/04-free-user-blocked.png
```

**Naming convention:** `<NN>-<descriptor>[-<role>].png`
- Include role when testing multiple accounts: `07-free-user-upgrade-prompt.png`
- Be specific: `06-php83-installed-badge.png` not `06-result.png`

### Capturing Evidence, Not Pages

Screenshots are evidence — they must show the **specific element** that proves the bug or fix.

**Scroll to the evidence first** if the relevant element is below the viewport:
```bash
playwright-cli evaluate "document.querySelector('.ssh-keys-list').scrollIntoView({behavior:'instant',block:'center'})"
playwright-cli screenshot --path qa-screenshots/pr<N>/evidence.png
```

**Capture transient elements immediately** — toasts auto-dismiss within seconds:
```bash
playwright-cli click "<submit-ref>"              # triggers action
playwright-cli screenshot --path <file>          # capture toast NOW — before next action
playwright-cli snapshot                          # then continue
```

**For state transitions, capture each state:**
```bash
playwright-cli screenshot --path 04-php83-before-install.png   # shows Install button
playwright-cli click "<install-ref>"
playwright-cli screenshot --path 05-php83-installing.png        # shows Installing status
playwright-cli wait-for-text "Installed"
playwright-cli screenshot --path 06-php83-installed.png         # shows Installed badge
```

## Waiting & Timing

| Situation | Command |
|-----------|---------|
| Page navigation (URL change) | `playwright-cli wait-for-text "<heading on new page>"` |
| Inertia transition (no full reload) | `playwright-cli wait-for-text "<expected text>"` |
| Async operation (install, deploy) | `playwright-cli wait-for-text "Installed"` (or expected completion text) |
| Need fresh element refs after DOM change | `playwright-cli snapshot` |
| Element below viewport | `playwright-cli evaluate "document.querySelector(…).scrollIntoView(…)"` |

**Key rule:** After every interaction that changes the DOM, run `playwright-cli snapshot` before the next interaction. Refs from a prior snapshot are stale and will fail.

## Error Detection

### After Every Page Load
```bash
playwright-cli snapshot    # check YAML output for error text, alert banners, or validation messages
```

### Known Pre-Existing Errors (Do Not Report)
- DuckDuckGo favicon 404 (`icons.duckduckgo.com`)
- WordPress.org plugin icon 404s (`ps.w.org`)
- ngrok CSP font-related errors (when using ngrok tunnels)

## Form Testing Patterns

| Input Type | Command |
|------------|---------|
| Text input | `playwright-cli fill "<selector>" "<value>"` |
| Password | `playwright-cli fill "[name=password]" "<value>"` |
| Checkbox | `playwright-cli click "<checkbox-ref>"` |
| Toggle/Switch | `playwright-cli click "<switch-ref>"` |
| Select/Dropdown | `playwright-cli select "<selector>" "<option-value>"` |
| Textarea | `playwright-cli fill "<selector>" "<value>"` |
| Search/autocomplete | `playwright-cli fill "<selector>" "<partial-text>"` then snapshot to find suggestion refs |

### Validation Testing
1. Submit form with empty required fields — snapshot to verify error messages appear in YAML
2. Submit with invalid formats — snapshot to verify specific error text
3. Submit at boundary values (max length, special characters)
4. After fixing errors, re-submit and verify error messages are gone

## Debugging Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Ref not found | Stale ref from old snapshot | Run `playwright-cli snapshot` and use new ref |
| Can't click element | Element behind modal or overlay | Dismiss the overlay, then re-snapshot |
| Page seems stuck | Inertia request in flight | `playwright-cli wait-for-text "<expected>"` |
| Login redirects unexpectedly | Billing redirect or session issue | Check snapshot for redirect destination |
| Form submit doesn't respond | CSRF token expired | Close browser, start fresh session |
| Toast captured blank | Screenshot taken too late | Screenshot immediately after the action, before next interaction |
