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

## Cache Clearing

Run before starting any testing to ensure you're testing the latest deployed code:

```bash
ssh {user}@{host} "cd {app-path} && php artisan config:clear && php artisan cache:clear && php artisan route:clear && php artisan view:clear"
```

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
