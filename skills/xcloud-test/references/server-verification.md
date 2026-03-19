# Server-Side Verification Reference

## Section A: Command Runner Workflow

### What Is Command Runner?

Command Runner is xCloud's built-in UI for executing shell commands on managed servers. It lives at `/server/{id}/command-runner` (Server > Settings > Commands) and requires the `server:custom-command-runner` permission.

### When to Use Command Runner vs SSH

| Use Command Runner | Use SSH |
|--------------------|---------|
| Quick verification checks (1-3 commands) | Long interactive sessions (Tinker, debugging) |
| When you need easy-to-screenshot evidence | Multi-step debugging with log analysis |
| When SSH credentials aren't available | When you need persistent shell state |
| Single command with immediate output | When chaining many commands with pipes |

### Step-by-Step Playwright Interaction

1. **Navigate** to `/server/{id}/command-runner`:
   ```
   browser_navigate → https://{staging-url}/server/{id}/command-runner
   ```
2. **Snapshot** the page to find the command input area:
   ```
   browser_snapshot
   ```
3. **Click** the command editor/input field (identify from snapshot refs)
4. **Type** the verification command:
   ```
   browser_type → text: "systemctl is-active nginx"
   ```
5. **Click** the Execute/Run button
6. **Wait** for command output to appear:
   ```
   browser_wait_for → text or network idle
   ```
7. **Snapshot** to read the output text and confirm result
8. **Screenshot** for evidence:
   ```
   browser_take_screenshot → qa-screenshots/XX-cmdrunner-{description}.png
   ```

### Screenshot Naming Convention

```
qa-screenshots/XX-cmdrunner-{operation}-{detail}.png
```

Examples:
- `05-cmdrunner-nginx-status.png`
- `06-cmdrunner-php82-version.png`
- `07-cmdrunner-ssl-cert-check.png`

### Batch Verification Pattern

For operations requiring multiple verification commands, run them sequentially in Command Runner:

1. Run the primary verification command → snapshot + screenshot
2. Run supplementary checks → snapshot + screenshot
3. Combine evidence in the test report

Example for PHP install verification:
```
Command 1: php8.2 -v
Command 2: dpkg -l | grep php8.2 | wc -l
Command 3: php8.2 -m | grep -i opcache
```

---

## Section B: Verification Matrix

**Rule:** For every UI action that modifies server state, find the matching row below and run the verification command via Command Runner or SSH. A UI toast or status badge alone is NOT evidence of server state.

### Service Operations

| Operation | UI Shows | Verification Command | Confirms Success | Stack Notes |
|-----------|----------|---------------------|-----------------|-------------|
| Restart Nginx | "Restarted" toast | `systemctl is-active nginx && systemctl show nginx --property=ActiveEnterTimestamp` | Service active + recent restart timestamp | Nginx stack only |
| Restart MySQL | "Restarted" toast | `systemctl is-active mysql && systemctl show mysql --property=ActiveEnterTimestamp` | Service active + recent restart timestamp | All stacks with MySQL |
| Restart Redis | "Restarted" toast | `systemctl is-active redis-server && redis-cli ping` | Service active + PONG response | All stacks |
| Restart PHP-FPM | "Restarted" toast | `systemctl is-active php{VER}-fpm && systemctl show php{VER}-fpm --property=ActiveEnterTimestamp` | Service active + recent restart timestamp | Nginx stack only |
| Restart OpenLiteSpeed | "Restarted" toast | `systemctl is-active lsws && /usr/local/lsws/bin/lswsctrl status` | Service active + running confirmation | OLS stack only |
| Restart Docker containers | "Restarted" toast | `docker ps --format '{{.Names}} {{.Status}}' \| grep {container}` | Container "Up" with recent start time | Docker stack only |
| Restart Supervisor | "Restarted" toast | `supervisorctl status` | All managed processes RUNNING | All stacks |
| Restart OpenClaw gateway | "Restarted" toast | `openclaw gateway status` | Gateway running | OpenClaw stack only |

### Package & Software Installation

| Operation | UI Shows | Verification Command | Confirms Success | Stack Notes |
|-----------|----------|---------------------|-----------------|-------------|
| Install PHP version (Nginx) | "Installed" badge | `php{VER} -v && dpkg -l \| grep php{VER} \| wc -l` | Version string + package count > 0 | Nginx stack — uses system PHP |
| Install PHP version (OLS) | "Installed" badge | `/usr/local/lsws/lsphp{VER2}/bin/php -v && dpkg -l \| grep lsphp{VER2} \| wc -l` | Version string + package count > 0 | OLS stack — uses lsphp binaries (VER2 = no dot, e.g., 82) |
| Install PHP extension | "Installed" | `php{VER} -m \| grep -i {ext}` or `/usr/local/lsws/lsphp{VER2}/bin/php -m \| grep -i {ext}` | Extension listed in modules | Check stack for correct binary path |
| Install apt package | "Installed" | `dpkg -l \| grep {package}` or `which {binary}` | Package listed or binary found | All stacks |
| Install Composer packages | "Success" | `cd {site-path} && composer show \| grep {package}` | Package listed in vendor | All PHP stacks |
| Install Node.js | "Installed" | `node -v && npm -v` | Version strings match expected | All stacks |
| Remove PHP version | "Removed" | `dpkg -l \| grep php{VER} \| wc -l` | Package count = 0 | Check stack-specific path too |

### Configuration Changes

| Operation | UI Shows | Verification Command | Confirms Success | Stack Notes |
|-----------|----------|---------------------|-----------------|-------------|
| Change PHP setting (php.ini) | "Updated" toast | `php{VER} -i \| grep "{setting}"` | Runtime value matches expected | File check: `grep "{setting}" /etc/php/{VER}/fpm/php.ini` |
| Change PHP setting (OLS) | "Updated" toast | `/usr/local/lsws/lsphp{VER2}/bin/php -i \| grep "{setting}"` | Runtime value matches expected | File check: `grep "{setting}" /usr/local/lsws/lsphp{VER2}/etc/php/{VER}/litespeed/php.ini` |
| Change MySQL config | "Updated" toast | `mysql -e "SHOW VARIABLES LIKE '{setting}';"` | Variable value matches expected | Also check: `grep "{setting}" /etc/mysql/mysql.conf.d/mysqld.cnf` |
| Update Nginx config | "Updated" toast | `nginx -t` (syntax valid) + `grep "{directive}" /etc/nginx/sites-available/{site}` | Syntax OK + directive present | Nginx stack only |
| Update OLS config | "Updated" toast | `/usr/local/lsws/bin/lswsctrl restart` + check httpd_config.conf | Restart succeeds + config present | OLS stack only |
| Update .env value | "Updated" toast | `grep "{KEY}" {site-path}/.env` | Key=Value matches expected | All stacks |
| Toggle OPCache | "Enabled"/"Disabled" | `php{VER} -i \| grep "opcache.enable "` | `opcache.enable => On/Off` | Also: `php{VER} -m \| grep -i opcache` |

### SSL & Domain Operations

| Operation | UI Shows | Verification Command | Confirms Success | Stack Notes |
|-----------|----------|---------------------|-----------------|-------------|
| Install SSL certificate | "Active" / "Secured" | `echo \| openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null \| openssl x509 -noout -dates -subject` | Valid dates + correct subject | All stacks |
| Renew SSL certificate | "Renewed" | `certbot certificates --domain {domain}` or openssl check (above) | Expiry date extended | All stacks |
| Force HTTPS redirect | "Enabled" | `curl -sI http://{domain} \| grep -i location` | 301/302 redirect to https:// | All stacks |

### Database Operations

| Operation | UI Shows | Verification Command | Confirms Success | Stack Notes |
|-----------|----------|---------------------|-----------------|-------------|
| Create DB user | "Created" | `mysql -e "SELECT user, host FROM mysql.user WHERE user='{username}';"` | User row exists | All stacks |
| Create database | "Created" | `mysql -e "SHOW DATABASES LIKE '{dbname}';"` | Database listed | All stacks |
| Grant permissions | "Updated" | `mysql -e "SHOW GRANTS FOR '{username}'@'{host}';"` | Expected grants present | All stacks |
| Delete DB user | "Deleted" | `mysql -e "SELECT user FROM mysql.user WHERE user='{username}';"` | Empty result (user gone) | All stacks |

### Security & Network

| Operation | UI Shows | Verification Command | Confirms Success | Stack Notes |
|-----------|----------|---------------------|-----------------|-------------|
| Add firewall rule | "Added" | `ufw status numbered \| grep {port}` | Rule present for port/IP | All stacks |
| Remove firewall rule | "Removed" | `ufw status numbered \| grep {port}` | Rule absent | All stacks |
| Sync SSH keys | "Synced" | `cat ~/.ssh/authorized_keys \| grep "{key-fragment}"` or `wc -l ~/.ssh/authorized_keys` | Key present or count matches | All stacks |
| Change SSH port | "Updated" | `grep "^Port" /etc/ssh/sshd_config` | Port matches expected value | All stacks |

### Cache & Queue Operations

| Operation | UI Shows | Verification Command | Confirms Success | Stack Notes |
|-----------|----------|---------------------|-----------------|-------------|
| Clear application cache | "Cleared" toast | `redis-cli DBSIZE` (before/after count) | DB size decreased | All stacks with Redis |
| Clear OPCache | "Cleared" toast | `php{VER} -r "var_dump(opcache_get_status()['opcache_statistics']['num_cached_scripts']);"` | Cached scripts = 0 or reduced | All PHP stacks |
| Restart queue workers | "Restarted" | `supervisorctl status \| grep {queue-worker}` | Workers RUNNING with recent uptime | All stacks |
| Process failed jobs | "Retried" | `cd {app-path} && php artisan queue:failed --no-interaction` | Failed jobs count decreased | All stacks |

---

## Section C: Operational Recipes

Practical, copy-pasteable commands for common verification scenarios. Choose the commands matching the server's stack.

### Service Health Checks (Stack-Aware)

**Nginx stack:**
```bash
systemctl is-active nginx mysql redis-server php{VER}-fpm supervisor
```

**OpenLiteSpeed stack:**
```bash
systemctl is-active lsws mysql redis-server supervisor
/usr/local/lsws/bin/lswsctrl status
```

**Docker stack:**
```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
systemctl is-active docker
```

**OpenClaw stack:**
```bash
openclaw gateway status
openclaw services list
systemctl is-active mysql redis-server
```

### Enable/Disable Debug Mode

**WordPress sites — use the UI:**
Navigate to `/server/{id}/site/{id}/wp-debug` (Settings menu). Toggle WP_DEBUG, WP_DEBUG_LOG, and WP_DEBUG_DISPLAY via the UI controls. Screenshot the page for evidence.

**Laravel sites — use the UI:**
Navigate to `/server/{id}/site/{id}/application`. Toggle the debug mode switch. Screenshot the page for evidence.

**CLI verification (after UI toggle or for other site types):**
```bash
# Verify debug mode is active
grep "APP_DEBUG" {site-path}/.env
cd {app-path} && php artisan tinker --execute="echo config('app.debug') ? 'DEBUG ON' : 'DEBUG OFF';"
```

**CLI fallback (when UI is unavailable):**
```bash
sed -i 's/APP_DEBUG=false/APP_DEBUG=true/' {site-path}/.env
cd {app-path} && php artisan config:clear

# ALWAYS disable after debugging
sed -i 's/APP_DEBUG=true/APP_DEBUG=false/' {site-path}/.env
cd {app-path} && php artisan config:clear
```

### Log Inspection

**Laravel application logs:**
```bash
# Recent errors (today)
grep -i 'error\|exception\|fatal' {app-path}/storage/logs/laravel-$(date +%Y-%m-%d).log | tail -50

# Errors in last 10 minutes
awk -v d="$(date -d '10 minutes ago' '+%Y-%m-%d %H:%M')" '$0 >= d' {app-path}/storage/logs/laravel-$(date +%Y-%m-%d).log | grep -i error
```

**Nginx logs:**
```bash
# Error log
tail -50 /var/log/nginx/error.log

# Access log for specific domain
tail -50 /var/log/nginx/{domain}-access.log
grep "500\|502\|503" /var/log/nginx/{domain}-access.log | tail -20
```

**OpenLiteSpeed logs:**
```bash
tail -50 /usr/local/lsws/logs/error.log
tail -50 /usr/local/lsws/logs/access.log
```

**MySQL logs:**
```bash
tail -50 /var/log/mysql/error.log
```

**Systemd journal per service:**
```bash
journalctl -u nginx --since "10 minutes ago" --no-pager
journalctl -u mysql --since "10 minutes ago" --no-pager
journalctl -u lsws --since "10 minutes ago" --no-pager
```

### Disk Space

```bash
# Overall disk usage
df -h

# Key directories
du -sh /var/www/ /var/log/ /tmp/ /var/lib/mysql/ 2>/dev/null

# Largest files in a site directory
du -ah {site-path} | sort -rh | head -20
```

### Queue Management

```bash
# Check failed jobs count
cd {app-path} && php artisan queue:failed --no-interaction | wc -l

# Retry all failed jobs
cd {app-path} && php artisan queue:retry all

# Flush all failed jobs
cd {app-path} && php artisan queue:flush

# Check Horizon status (if using Horizon)
cd {app-path} && php artisan horizon:status

# Check supervisor workers
supervisorctl status
supervisorctl status | grep RUNNING | wc -l
```

### PHP Inspection

**Nginx stack:**
```bash
# Installed PHP versions
ls /etc/php/ | sort -V

# PHP version and modules
php{VER} -v
php{VER} -m

# Specific ini setting
php{VER} -i | grep "memory_limit\|upload_max_filesize\|post_max_size\|max_execution_time"

# OPCache status
php{VER} -i | grep "opcache.enable"
php{VER} -r "var_dump(opcache_get_status());" 2>/dev/null | head -20

# PHP-FPM pool config
cat /etc/php/{VER}/fpm/pool.d/www.conf | grep -E "^(pm\.|listen)"
```

**OpenLiteSpeed stack:**
```bash
# Installed lsphp versions
ls /usr/local/lsws/ | grep lsphp

# PHP version and modules
/usr/local/lsws/lsphp{VER2}/bin/php -v
/usr/local/lsws/lsphp{VER2}/bin/php -m

# Specific ini setting
/usr/local/lsws/lsphp{VER2}/bin/php -i | grep "memory_limit\|upload_max_filesize\|post_max_size"

# PHP ini file location
/usr/local/lsws/lsphp{VER2}/bin/php --ini
```

### Database Users & Permissions

```bash
# List all database users
mysql -e "SELECT user, host FROM mysql.user ORDER BY user;"

# Show grants for a specific user
mysql -e "SHOW GRANTS FOR '{username}'@'localhost';"

# Test authentication for a user
mysql -u {username} -p{password} -e "SELECT 1;" 2>&1

# List databases
mysql -e "SHOW DATABASES;"

# Check database size
mysql -e "SELECT table_schema AS 'Database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' FROM information_schema.tables GROUP BY table_schema;"
```

### SSL Certificate Status

```bash
# Check certificate details for a domain
echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null | openssl x509 -noout -dates -subject -issuer

# Check certificate expiry only
echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null | openssl x509 -noout -enddate

# List certbot certificates
certbot certificates 2>/dev/null

# Test HTTPS with curl
curl -sI https://{domain} | head -5

# Check if HTTP redirects to HTTPS
curl -sI http://{domain} | grep -i "location\|HTTP"
```

### Firewall Rules

```bash
# UFW status with rules
ufw status verbose

# UFW status with rule numbers (for removal reference)
ufw status numbered

# Check if specific port is open
ufw status | grep {port}

# Check iptables directly (if ufw is not used)
iptables -L -n --line-numbers | head -30
```

### Supervisor Processes

```bash
# Status of all managed processes
supervisorctl status

# Status of specific worker
supervisorctl status {worker-name}

# Restart a specific worker
supervisorctl restart {worker-name}

# Check supervisor config files
ls /etc/supervisor/conf.d/

# View worker log
tail -50 /var/log/supervisor/{worker-name}.log

# Count running vs total workers
echo "Running: $(supervisorctl status | grep RUNNING | wc -l) / Total: $(supervisorctl status | wc -l)"
```
