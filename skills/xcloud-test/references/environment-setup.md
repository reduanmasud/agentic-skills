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
    'password' => bcrypt('<TEST_PASSWORD>'),
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
    'password' => bcrypt('<TEST_PASSWORD>'),
    'white_label_id' => $whiteLabelId,
]);

// Assign a billing plan to a team
$team->update(['active_plan_id' => $billingPlanId]);
```

### Creating Test Servers & Sites (MANDATORY — NEVER Skip Tests)

**RULE: If staging lacks the server stack, site type, or user role needed to test the PR, CREATE it via Tinker. NEVER skip tests because the right infrastructure doesn't exist on staging.**

Missing test infrastructure is the #1 cause of incomplete QA. If a PR targets OLS and staging only has Nginx — create an OLS server record. If a PR touches Docker apps and staging has no DockerNginx server — create one. The cost of creating a Tinker record is 30 seconds. The cost of skipping a test is a missed bug in production.

Tinker-created records exist only in the database — they are not real servers. Use them for:
- UI rendering, navigation, and policy behavior testing
- Billing guard and permission verification
- Form validation and API response testing
- Testing how features handle different server stacks or site types

For tests requiring **actual server-side execution** (script installs, SSH commands, service checks), use the existing real staging server.

#### Step 1: Get the Existing User and Team

Before creating servers/sites, get references to your test account:

```php
$user = User::where('email', 'your-paid-test@email.com')->first();
$team = Team::find($user->current_team_id);
```

#### Step 2: Create Servers by Stack

All 4 server stacks share the same base fields. Only `stack` differs:

```php
// Base template — copy and change 'name' and 'stack' as needed
$server = Server::create([
    'name' => 'qa-nginx-server',       // Unique name per server
    'user_id' => $user->id,
    'team_id' => $team->id,
    'status' => 'provisioned',         // NOT 'active' — use enum value
    'stack' => 'nginx',                // See stack values below
    'is_connected' => true,
    'is_provisioned' => true,
    'public_ip' => '10.0.0.1',        // NOT 'ip' — use 'public_ip'
    'private_ip' => '10.0.0.1',
    'ssh_port' => 22,
    'ssh_username' => 'root',
    'sudo_password' => '<SUDO_PASSWORD>',
    'database_type' => 'mysql_8',
    'database_name' => 'xcloud',
    'database_password' => '<DB_PASSWORD>',
    'next_site_prefix_id' => 1,
    'ubuntu_version' => '24.04',
]);
```

**Stack values** (use exactly these strings):

| Stack | Value | Use For |
|-------|-------|---------|
| Nginx | `'nginx'` | PHP sites, WordPress, Laravel, Custom PHP, Node.js |
| OpenLiteSpeed | `'openlitespeed'` | Same as Nginx but with LiteSpeed Cache. **NOT** `'ols'` |
| Docker + Nginx | `'docker_nginx'` | Containerized apps: Nextcloud, Supabase, Ollama, etc. |
| OpenClaw | `'openclaw'` | OpenClaw (Clawdbot) sites only |

**Change the IP** for each server to avoid confusion (10.0.0.1, 10.0.0.2, etc.).

#### Step 3: Set Server Meta (If PR Checks It)

```php
// PHP version info
$server->saveMeta('php_version', '8.2');

// Server info (checked by many features)
$server->saveMeta('server_info', [
    'php_settings' => ['opcache' => true],
    'installed_packages' => [],
]);

// PHP versions array (checked by PHP management features)
$server->update(['php_versions' => json_encode(['8.1', '8.2', '8.3'])]);
```

#### Step 4: Create Sites by Type

**Minimum required fields for any site:**

```php
$site = Site::create([
    'name' => 'qa-wordpress.test',     // Must be a valid domain-like name
    'server_id' => $server->id,        // FK to the server created above
    'type' => 'wordpress',             // See type values below
    'status' => 'provisioned',         // NOT 'active'
    'site_user' => 'xcloud',           // Default unix user
    'php_version' => '8.2',            // Required for PHP-based sites
]);
```

**Do NOT include** `team_id`, `path`, or `ip` — these don't exist on the sites table or are derived from the server.

#### Stack-Site Compatibility Matrix

**This is critical.** Not all site types work on all stacks. Creating a site on the wrong stack causes broken UI and misleading test results.

| Stack | Allowed Site Types |
|-------|-------------------|
| **Nginx** | `wordpress`, `laravel`, `custom-php`, `nodejs`, `lovable`, `phpmyadmin`, `n8n`, `uptime-kuma`, `mautic` |
| **OpenLiteSpeed** | Same as Nginx |
| **DockerNginx** | `docker-compose`, `nextcloud`, `librechat`, `openwebui`, `ollama`, `umami`, `supabase`, `wireguard` |
| **OpenClaw** | `openclaw` only |

**If the PR touches a containerized app** (Nextcloud, Supabase, Ollama, etc.), you MUST create a `docker_nginx` server first.

**If the PR touches OpenClaw**, you MUST create an `openclaw` server.

#### Site Type Quick Reference

**PHP-based sites** (need `php_version`):

| Type Value | Display Name | Notes |
|-----------|-------------|-------|
| `'wordpress'` | WordPress | Most common |
| `'laravel'` | Laravel | |
| `'custom-php'` | Custom PHP | |
| `'phpmyadmin'` | PHPMyAdmin | One per server |
| `'mautic'` | Mautic | PHP 8.1–8.3 only |

**Node.js-based sites** (no `php_version` needed):

| Type Value | Display Name | Notes |
|-----------|-------------|-------|
| `'nodejs'` | Node.js | Nginx/OLS only |
| `'n8n'` | n8n | Nginx/OLS only |
| `'uptime-kuma'` | Uptime Kuma | Nginx/OLS only |
| `'lovable'` | Lovable | Nginx/OLS only |

**Containerized apps** (DockerNginx server only):

| Type Value | Display Name | Notes |
|-----------|-------------|-------|
| `'docker-compose'` | Custom Docker | |
| `'nextcloud'` | Nextcloud | |
| `'supabase'` | Supabase | One per server |
| `'ollama'` | Ollama | One per server |
| `'openwebui'` | OpenWebUI | |
| `'librechat'` | LibreChat | |
| `'umami'` | Umami | |
| `'wireguard'` | WireGuard | One per server |

**OpenClaw stack only:**

| Type Value | Display Name | Notes |
|-----------|-------------|-------|
| `'openclaw'` | OpenClaw (Clawdbot) | OpenClaw server required |

#### Example: Creating a Full Test Environment

When a PR touches multiple stacks or site types, create everything you need:

```php
// Get existing user/team
$user = User::where('email', 'paid@test.com')->first();
$team = Team::find($user->current_team_id);

// Nginx server with WordPress + Laravel sites
$nginxServer = Server::create([
    'name' => 'qa-nginx', 'user_id' => $user->id, 'team_id' => $team->id,
    'status' => 'provisioned', 'stack' => 'nginx', 'is_connected' => true,
    'is_provisioned' => true, 'public_ip' => '10.0.0.1', 'private_ip' => '10.0.0.1',
    'ssh_port' => 22, 'ssh_username' => 'root', 'sudo_password' => '<SUDO_PASSWORD>',
    'database_type' => 'mysql_8', 'database_name' => 'xcloud',
    'database_password' => '<DB_PASSWORD>', 'next_site_prefix_id' => 1,
]);

$wpSite = Site::create([
    'name' => 'qa-wp.test', 'server_id' => $nginxServer->id,
    'type' => 'wordpress', 'status' => 'provisioned',
    'site_user' => 'xcloud', 'php_version' => '8.2',
]);

$laravelSite = Site::create([
    'name' => 'qa-laravel.test', 'server_id' => $nginxServer->id,
    'type' => 'laravel', 'status' => 'provisioned',
    'site_user' => 'xcloud', 'php_version' => '8.2',
]);

// Docker server with Nextcloud
$dockerServer = Server::create([
    'name' => 'qa-docker', 'user_id' => $user->id, 'team_id' => $team->id,
    'status' => 'provisioned', 'stack' => 'docker_nginx', 'is_connected' => true,
    'is_provisioned' => true, 'public_ip' => '10.0.0.2', 'private_ip' => '10.0.0.2',
    'ssh_port' => 22, 'ssh_username' => 'root', 'sudo_password' => '<SUDO_PASSWORD>',
    'database_type' => 'mysql_8', 'database_name' => 'xcloud',
    'database_password' => '<DB_PASSWORD>', 'next_site_prefix_id' => 1,
]);

$nextcloudSite = Site::create([
    'name' => 'qa-nextcloud.test', 'server_id' => $dockerServer->id,
    'type' => 'nextcloud', 'status' => 'provisioned', 'site_user' => 'xcloud',
]);

// Record ALL IDs for cleanup
// Servers: $nginxServer->id, $dockerServer->id
// Sites: $wpSite->id, $laravelSite->id, $nextcloudSite->id
```

#### When to Create Test Infrastructure

| PR Changes | What to Create |
|-----------|---------------|
| Targets a specific server stack (OLS, Docker, OpenClaw) | Server with matching `stack` value |
| Targets a specific site type | Site with matching `type` on compatible stack server |
| Adds/modifies billing guards or plan checks | Free plan team (see "Billing Setup" below) |
| Modifies team permissions | Team member with limited role |
| Touches whitelabel features | User with `white_label_id` set |
| Changes enterprise exclusions | Team with `exclude_features` meta |
| Checks `$server->stack->isOpenLiteSpeed()` | OLS server record |
| Checks `$server->stack->isDockerNginx()` | DockerNginx server record |
| Checks `$site->type->isWordPress()` or similar | Site with that type |
| Checks PHP version specifics | Server with `php_versions` meta set |

**When in doubt, create it.** A Tinker record takes 30 seconds. A skipped test can miss a production bug.

#### Billing & Team Setup

**Free plan team** (for testing billing guards):

```php
// Find or create a free-plan team
$freeUser = User::where('email', 'your-free-test@email.com')->first();
$freeTeam = Team::find($freeUser->current_team_id);

// Remove active plan to simulate free tier
$freeTeam->update(['active_plan_id' => null]);
```

**Team member with limited permissions:**

```php
// Add a user as a team member with limited role
$memberUser = User::where('email', 'member@test.com')->first();
$team->users()->attach($memberUser, ['role' => 'editor']); // or 'viewer'
```

**Whitelabel user:**

```php
$wlUser = User::create([
    'first_name' => 'QA', 'last_name' => 'WL User',
    'email' => 'qa-wl@staging.example.com',
    'password' => bcrypt('<TEST_PASSWORD>'),
    'white_label_id' => $whiteLabelId,  // Get from existing whitelabel
]);
```

**Enterprise feature exclusions:**

```php
$team->saveMeta('exclude_features', ['feature_key_1', 'feature_key_2']);
```

#### Verify Created Records

After creating test data, verify the records are valid:

```php
// Server: check status and stack
$server->fresh();  // Reload from DB
echo "Server #{$server->id}: {$server->name} | stack={$server->stack->value} | status={$server->status->value}";

// Site: check type and server relationship
$site->fresh();
echo "Site #{$site->id}: {$site->name} | type={$site->type->value} | server={$site->server->name}";

// Verify site shows in server's sites list
$server->sites()->pluck('name', 'id');
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

// 2. Delete test servers (may have multiple stacks: nginx, ols, docker, openclaw)
Server::whereIn('id', [/* IDs you created */])->each(fn($s) => $s->forceDelete());

// 3. Detach team members added during testing
$team->users()->detach([$memberUserId]); // If you attached team members

// 4. Revert team meta changes
$team->saveMeta('exclude_features', []); // If you set enterprise exclusions
// $freeTeam->update(['active_plan_id' => $originalPlanId]); // If you changed billing plan

// 5. Delete test teams (only if you CREATED new teams)
Team::whereIn('id', [/* IDs you created */])->each(fn($t) => $t->forceDelete());

// 6. Delete test users last
User::whereIn('email', ['qa-test@staging.example.com', 'qa-wl@staging.example.com'])
    ->each(fn($u) => $u->forceDelete());

// 7. Delete any test products, tokens, or other records
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
