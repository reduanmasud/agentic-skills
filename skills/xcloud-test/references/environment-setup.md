# Environment Setup & Cleanup

## Required Information (Gather Before Testing)

Ask the user for ALL of these before starting. Do NOT assume or hardcode values.

| Field | Why You Need It |
|-------|----------------|
| **Staging URL** | Base URL for browser testing |
| **SSH Access** | `user@host` for server commands, logs, Tinker |
| **App path on server** | Where the Laravel app lives (e.g., `/home/forge/example.com`) |
| **Paid/Admin test account** | Email + password for primary happy-path testing |
| **Free/restricted test account** | Email + password for billing guard and permission testing |
| **Whitelabel URL** (if relevant) | For testing whitelabel-scoped features |

## Single vs. Multi-Environment Setup

When testing multiple PRs, environment info can be gathered in two ways:

| Mode | When to use | How it works |
|------|------------|--------------|
| **Single environment** | All PRs deploy to the same staging server | Gather environment info (URL, SSH, app path, credentials) once and reuse for every PR |
| **Multiple environments** | Each PR has its own staging server | Ask for separate environment info per PR before testing it |
| **Single PR** (default) | Only one PR to test | No special handling — gather info once and proceed |

For single-environment multi-PR testing, be aware that:
- Each PR deployment overwrites the previous one on the same server
- Migrations from one PR may affect subsequent PRs
- Test data cleanup (Step 8) must run between PRs to avoid collisions

## Cache Clearing

Run before starting any testing to ensure you're testing the latest deployed code:

```bash
ssh {user}@{host} "cd {app-path} && php artisan config:clear && php artisan cache:clear && php artisan route:clear && php artisan view:clear"
```

## Deploying a PR Branch to the Staging Server

After local checkout (`gh pr checkout <PR_NUMBER>`), deploy the branch to the staging server:

### 1. Get the Branch Name

```bash
gh pr view <PR_NUMBER> --json headRefName -q '.headRefName'
```

### 2. Deploy via SSH

```bash
ssh {user}@{host} "cd {app-path} && git fetch origin && git checkout {branch} && git pull origin {branch}"
```

If the server has uncommitted changes:
```bash
ssh {user}@{host} "cd {app-path} && git stash && git fetch origin && git checkout {branch} && git pull origin {branch}"
```

If the branch checkout fails due to merge conflicts, report the conflict to the user and skip this PR.

### 3. Post-Deploy Steps

After checking out the branch, run these in order:

```bash
# Always: clear all caches
ssh {user}@{host} "cd {app-path} && php artisan config:clear && php artisan cache:clear && php artisan route:clear && php artisan view:clear"

# Always: run pending migrations
ssh {user}@{host} "cd {app-path} && php artisan migrate"
```

Conditionally run these based on which files the PR changed:

```bash
# Check what files changed
gh pr diff <PR_NUMBER> --name-only
```

| Files changed | Action |
|--------------|--------|
| `composer.json` or `composer.lock` | `ssh {user}@{host} "cd {app-path} && composer install --no-interaction"` |
| Any file in `resources/js/`, `resources/css/`, `package.json`, or `package-lock.json` | `ssh {user}@{host} "cd {app-path} && npm install && npm run build"` |
| Neither | Skip — no dependency or frontend changes |

### 4. Verify Deployment

```bash
# Confirm the correct branch and commit are deployed
ssh {user}@{host} "cd {app-path} && git branch --show-current && git log --oneline -1"

# Compare with the PR's head commit
gh pr view <PR_NUMBER> --json headRefName,headRefOid -q '"\(.headRefName) \(.headRefOid)"'
```

The branch name and commit hash should match. If they don't, the deployment failed — investigate before proceeding.

## Migration Management

Check for and run pending migrations:

```bash
# Check status
ssh {user}@{host} "cd {app-path} && php artisan migrate:status"

# Run pending migrations (if any)
ssh {user}@{host} "cd {app-path} && php artisan migrate"
```

## Test Data Creation

If existing accounts are insufficient, create test data via Tinker. **Track every record you create** — you MUST clean them up after testing.

```bash
ssh {user}@{host} "cd {app-path} && php artisan tinker"
```

### Common Patterns

```php
// Create a test user
$user = User::create([
    'name' => 'QA Test User',
    'email' => 'qa-test@staging.example.com',
    'password' => bcrypt('password123'),
]);

// Create a team for the user
$team = Team::forceCreate([
    'name' => "QA Test Team",
    'user_id' => $user->id,
    'personal_team' => true,
]);
$user->update(['current_team_id' => $team->id]);

// Create a whitelabel test user
$wlUser = User::create([
    'name' => 'QA WL User',
    'email' => 'qa-wl@staging.example.com',
    'password' => bcrypt('password123'),
    'white_label_id' => $whiteLabelId,
]);

// Assign a billing plan to a team
$team->update(['active_plan_id' => $billingPlanId]);
```

**Keep a running list** of every ID you create (users, teams, sites, servers, products). You will need these for cleanup.

## Screenshot Directory

```bash
# Create the screenshot directory if it doesn't exist
mkdir -p qa-screenshots
```

Naming convention: `qa-screenshots/XX-description.png` (e.g., `01-dashboard-smoke-test.png`)

## Test Data Cleanup (MANDATORY)

Delete ALL test records after testing. This is mandatory — do not skip it.

### Cleanup Order

Clean up in **reverse order** (child records first to avoid foreign key constraint violations):

```php
// 1. Delete test sites first (child of server)
Site::whereIn('id', [/* IDs you created */])->each(fn($s) => $s->forceDelete());

// 2. Delete test servers
Server::whereIn('id', [/* IDs you created */])->each(fn($s) => $s->forceDelete());

// 3. Delete test teams
Team::whereIn('id', [/* IDs you created */])->each(fn($t) => $t->forceDelete());

// 4. Delete test users last
User::whereIn('email', ['qa-test@staging.example.com', 'qa-wl@staging.example.com'])
    ->each(fn($u) => $u->forceDelete());

// 5. Delete any test products, tokens, or other records
// Product::whereIn('id', [...])->each(fn($p) => $p->forceDelete());
```

### Verify Cleanup

```php
User::where('email', 'like', 'qa-%@staging.example.com')->count(); // Should be 0
```

### Cleanup Tracking Table

Document in the report:

```markdown
## Test Data Cleanup
| Item | Action | Status |
|------|--------|--------|
| User ID 123 (qa-test@staging.example.com) | Deleted via Tinker | Cleaned |
| Team ID 456 (QA Test Team) | Deleted via Tinker | Cleaned |
```

If no test data was created, note: "No test data was created during this QA session."
