# SSH & Server-Side Verification

## Connection Patterns

```bash
# Run a single command
ssh {user}@{host} "cd {app-path} && <command>"

# Run artisan commands
ssh {user}@{host} "cd {app-path} && php artisan <command>"

# Interactive Tinker session
ssh {user}@{host} "cd {app-path} && php artisan tinker"

# Check today's logs
ssh {user}@{host} "tail -n 200 {app-path}/storage/logs/laravel-$(date +%Y-%m-%d).log"

# Check yesterday's logs
ssh {user}@{host} "tail -n 200 {app-path}/storage/logs/laravel-$(date -d yesterday +%Y-%m-%d).log"
```

Replace `{user}@{host}` and `{app-path}` with the values gathered from the user in the staging environment setup.

## Laravel Artisan Commands

| Command | Purpose |
|---------|---------|
| `php artisan config:clear` | Clear config cache |
| `php artisan cache:clear` | Clear application cache |
| `php artisan route:clear` | Clear route cache |
| `php artisan view:clear` | Clear compiled views |
| `php artisan migrate:status` | Check pending migrations |
| `php artisan migrate` | Run pending migrations |
| `php artisan route:list --path=api` | List API routes |
| `php artisan route:list --name=server` | List routes matching name |
| `php artisan tinker` | Interactive PHP REPL |
| `php artisan queue:failed` | List failed queue jobs |

### Cache Clearing (All at Once)

```bash
ssh {user}@{host} "cd {app-path} && php artisan config:clear && php artisan cache:clear && php artisan route:clear && php artisan view:clear"
```

## Tinker Patterns for xCloud

### Finding Users and Teams

```php
// Find user by email
$user = User::where('email', 'user@example.com')->first();
$user->id;           // User ID
$user->current_team_id;  // Active team

// Get user's teams
$user->allTeams()->pluck('name', 'id');

// Find team
$team = Team::find($teamId);
$team->owner;        // Team owner
$team->users;        // Team members
```

### Checking Team Permissions

```php
// Check if user has a specific team permission
$user->hasTeamPermission($team, 'site:manage');
$user->hasTeamPermission($team, 'server:manage');

// List all permissions for user on team
$user->teamPermissions($team);

// Check team role
$user->teamRole($team)->key;  // 'admin', 'editor', etc.
```

### Inspecting Server Meta

```php
$server = Server::find($serverId);

// Get server info (nested meta)
$server->getServerInfo('php_settings');
$server->getServerInfo('installed_packages');

// Get/set arbitrary meta
$server->getMeta('key');
$server->saveMeta('key', $value);

// Server details
$server->stack;       // ServerStack enum
$server->ubuntu_version;
$server->billing_service;
$server->team_id;
```

### Checking Billing Plans

```php
$team = Team::find($teamId);
$team->active_plan_id;
$team->isTrailMode();  // On trial?

$server->isFreePlan();  // Free plan server?

// Check billing service
$server->billing_service;  // BillingServices enum
```

### Policy Verification

```php
// Check if a policy allows an action
$user = User::find($userId);
$server = Server::find($serverId);

(new \App\Policies\ServerPolicy)->view($user, $server);
(new \App\Policies\SitePolicy)->manage($user, $site);

// Check Gate::before bypass (admin users)
$user->isAdmin();  // If true, Gate::before may bypass policies
```

### Route Middleware Inspection

```php
// Find route and check its middleware
$route = app('router')->getRoutes()->getByName('server.show');
$route->middleware();

// Or find by URL pattern
collect(app('router')->getRoutes())->filter(fn($r) => str_contains($r->uri(), 'php/opcache'));
```

### Checking Failed Jobs

```php
// Most recent failed job
DB::table('failed_jobs')->latest()->first();

// Count recent failures
DB::table('failed_jobs')->where('failed_at', '>=', now()->subHours(1))->count();

// Failed jobs for a specific queue
DB::table('failed_jobs')->where('queue', 'server-operations')->latest()->get();
```

## Server-Side Verification

After any operation that installs, configures, or modifies something on a server, verify the actual state.

### Package Verification

```bash
# Check if specific packages are installed
dpkg -l | grep <package-name>

# List installed packages matching a pattern
apt list --installed 2>/dev/null | grep <pattern>

# Example: verify PHP 8.5 packages
dpkg -l | grep lsphp85
```

### Service Status

```bash
# Check service status
systemctl status <service-name>

# Examples
systemctl status nginx
systemctl status mysql
systemctl status lsws        # OpenLiteSpeed
systemctl status supervisor
```

### Binary Verification

```bash
# Verify binary versions
php -v
node -v
nginx -t          # Also validates config syntax
composer --version

# OpenLiteSpeed PHP binaries
/usr/local/lsws/lsphp85/bin/php -v
```

### Config File Inspection

```bash
# Check if config file exists
ls -la /path/to/config.file

# Search for specific setting in config
grep -r "setting_name" /path/to/config/directory/

# Example: check OPCache config
grep -r opcache /usr/local/lsws/lsphp85/etc/
```

### File System Checks

```bash
# Check file/directory existence and permissions
ls -la /path/to/file

# Find files matching a pattern
find /var/www/site-name -name "*.conf" -type f

# Check disk usage
df -h /var/www/
```

## Command Runner (xCloud UI)

> For the complete Command Runner guide — including step-by-step Playwright browser workflow, the verification matrix mapping UI operations to verification commands, and operational recipes — load `references/server-verification.md`.

**Quick reference:** Navigate to `/server/{id}/command-runner` (Server > Settings > Commands). Requires `server:custom-command-runner` permission. Output displays in browser and is easy to screenshot for QA evidence.

## Log Analysis

### Daily Log Pattern

Laravel logs rotate daily: `storage/logs/laravel-YYYY-MM-DD.log`

```bash
# View recent errors
ssh {user}@{host} "grep -i 'error\|exception\|fatal' {app-path}/storage/logs/laravel-$(date +%Y-%m-%d).log | tail -50"

# View logs around a specific time
ssh {user}@{host} "grep '2026-03-15 14:' {app-path}/storage/logs/laravel-$(date +%Y-%m-%d).log"

# Count errors today
ssh {user}@{host} "grep -c 'ERROR' {app-path}/storage/logs/laravel-$(date +%Y-%m-%d).log"
```

### After Any 500 Error

1. Note the approximate time of the error
2. Check the Laravel log for stack traces around that time
3. Cross-reference the error file/line with the PR diff
4. Include the log excerpt in your bug report
