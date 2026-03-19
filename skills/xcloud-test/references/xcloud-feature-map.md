# xCloud UI Feature Map

## How to Use

This reference maps all xCloud UI management features to their URL patterns, menu paths, and availability conditions. Use it during QA to:

1. **PR analysis (Step 1):** Cross-reference changed files with this map to identify which UI pages the PR affects
2. **Test case generation (Step 4.0):** Ensure test cases navigate to the correct UI pages for each feature
3. **Test execution (Step 4):** Use the URL patterns and workflows below instead of CLI workarounds

**Rule:** If a feature has a UI management page listed here, you MUST test via that UI page — not CLI commands like `sed`, `echo`, or direct file editing. CLI verification comes AFTER the UI action, not instead of it.

---

## Server Management Features

Navigate via the left sidebar after selecting a server. Base URL: `/server/{id}/`

### Settings & Utilities

| Feature | Menu Path | URL Pattern | Stack Conditions | Permission |
|---------|-----------|-------------|-----------------|------------|
| Server Settings | Settings > Server Settings | `/server/{id}/server-settings` | All stacks | `server:manage-settings` |
| Restart Services | Settings > Server Settings | `/server/{id}/server-settings` | All stacks (services vary by stack) | `server:manage-settings` |
| Archive Server | Settings > Server Settings | `/server/{id}/server-settings` | All stacks | `server:manage-settings` |
| Delete Server | Settings > Server Settings | `/server/{id}/server-settings` | All stacks | `server:manage-settings` |
| Command Runner | Settings > Commands | `/server/{id}/command-runner` | All stacks | `server:custom-command-runner` |
| Events | Events | `/server/{id}/events` | All stacks | `server:view-events` |
| Others (Timezone, Magic Login, Connection) | Others | `/server/{id}/others` | All stacks | `server:manage-settings` |

### Infrastructure Management

| Feature | Menu Path | URL Pattern | Stack Conditions | Permission |
|---------|-----------|-------------|-----------------|------------|
| Database Management | Database | `/server/{id}/database` | All stacks with MySQL | `server:manage-database` |
| PHP Configuration | PHP Configuration | `/server/{id}/php-configuration` | Nginx, OLS stacks (not Docker/OpenClaw) | `server:manage-php` |
| MySQL Configuration | MySQL Configuration | `/server/{id}/mysql-configuration` | All stacks with MySQL | `server:manage-mysql-configuration` |
| Node Configuration | Node Configuration | `/server/{id}/node-configuration` | All stacks | `server:manage-node` |
| Cron Jobs | Cron Job | `/server/{id}/cron-job` | All stacks (not Docker/OpenClaw) | `server:manage-cronjob` |
| Supervisor | Supervisor | `/server/{id}/supervisor` | All stacks (not Docker/OpenClaw) | `server:manage-supervisor` |

### Security & Network

| Feature | Menu Path | URL Pattern | Stack Conditions | Permission |
|---------|-----------|-------------|-----------------|------------|
| Firewall Management | Firewall Management | `/server/{id}/firewall-management` | All stacks (not OpenClaw) | `server:manage-firewall` |
| Sudo Users | Sudo | `/server/{id}/sudo` | All stacks (not Docker/OpenClaw) | `server:manage-sudo-user` |
| Vulnerability Settings | Vulnerability Settings | `/server/{id}/vulnerability-settings` | All stacks (not Docker/OpenClaw) | `server:manage-vulnerability` |
| Security Updates | Security Update | `/server/{id}/security-update` | All stacks (not Docker/OpenClaw) | `server:manage-security-update` |

### Monitoring & Logs

| Feature | Menu Path | URL Pattern | Stack Conditions | Permission |
|---------|-----------|-------------|-----------------|------------|
| Server Monitoring | Monitoring | `/server/{id}/monitoring` | All stacks | `server:view-monitoring` |
| Server Logs | Logs | `/server/{id}/logs` | Nginx, OLS stacks | `server:view-logs` |
| Backup | Backup | `/server/{id}/backup` | All stacks (not OpenClaw) | `server:manage-backup` |
| Migration | Migration | `/server/{id}/migration` | All stacks (not Docker/OpenClaw) | `server:manage-migration` |

### OpenClaw Server Routes (Different Menu)

OpenClaw servers have a completely different management interface. Do NOT look for standard server features on OpenClaw servers.

| Feature | URL Pattern | Description |
|---------|-------------|-------------|
| Status | `/server/{id}/openclaw/status` | Gateway and service health |
| Providers | `/server/{id}/openclaw/providers` | AI provider configuration |
| Channels | `/server/{id}/openclaw/channels` | Channel management |
| Configuration | `/server/{id}/openclaw/config` | Core gateway settings |
| Environment | `/server/{id}/openclaw/environment` | Environment variables |
| Updates | `/server/{id}/openclaw/updates` | Version management |
| Reset | `/server/{id}/openclaw/reset` | Reset gateway state |
| Logs | `/server/{id}/openclaw/logs` | Gateway logs |

---

## Site Management Features

Navigate via the left sidebar after selecting a site. Base URL: `/server/{id}/site/{id}/` (shortened to `/site/{id}/` below).

### Common Features (All Site Types)

These features are available for most site types unless noted otherwise.

| Feature | Menu Path | URL Pattern | Conditions | Permission |
|---------|-----------|-------------|------------|------------|
| Site Overview | Overview | `/site/{id}` | All types | `site:view` |
| Domain Management | Domain | `/site/{id}/domain` | All types | `site:manage-domain` |
| SSL/HTTPS | SSL | `/site/{id}/ssl` | All types | `site:manage-ssl` |
| Redirection Rules | Redirection | `/site/{id}/redirection` | All types (not Docker apps) | `site:manage-redirection` |
| Monitoring | Monitoring | `/site/{id}/monitoring` | All types | `site:view-monitoring` |
| Logs | Logs | `/site/{id}/logs` | All types | `site:view-logs` |
| Events | Events | `/site/{id}/events` | All types | `site:view-events` |
| PageSpeed | PageSpeed | `/site/{id}/pagespeed` | All types | `site:view-pagespeed` |
| Traffic Analytics | Traffic Analytics | `/site/{id}/traffic-analytics` | All types | `site:view-analytics` |
| PHP Analytics | PHP Analytics | `/site/{id}/php-analytics` | PHP-based types (not Node/Docker) | `site:view-analytics` |
| MySQL Analytics | MySQL Analytics | `/site/{id}/mysql-analytics` | Types with `has_database` | `site:view-analytics` |
| SSH/sFTP Access | SSH/sFTP | `/site/{id}/ssh-sftp` | All types (not Docker apps) | `site:manage-ssh` |
| Database Access | Database (Adminer/PHPMyAdmin) | `/site/{id}/database` | Types with `has_database` | `site:manage-database` |
| File Manager | File Manager | `/site/{id}/file-manager` | All types (not Docker apps) | `site:manage-files` |
| Basic Authentication | Basic Auth | `/site/{id}/basic-authentication` | All types (not Docker apps) | `site:manage-basic-auth` |
| IP Management | IP Management | `/site/{id}/ip-management` | All types | `site:manage-ip` |
| Commands | Commands | `/site/{id}/commands` | All types (not Docker apps) | `site:manage-commands` |
| Backups | Backup | `/site/{id}/backup` | WP, Laravel, PHP, Node | `site:manage-backup` |
| Git Integration | Git | `/site/{id}/git` | All types (not Docker apps) | `site:manage-git` |
| Site Settings | Settings | `/site/{id}/settings` | All types | `site:manage-settings` |

### WordPress-Specific Features

These features ONLY appear for WordPress sites. If testing a WordPress PR, check all of these.

| Feature | Menu Path | URL Pattern | Permission | Notes |
|---------|-----------|-------------|------------|-------|
| WP Debug | WP Debug | `/site/{id}/wp-debug` | `site:manage-wpconfig` | UI toggles for WP_DEBUG, WP_DEBUG_LOG, WP_DEBUG_DISPLAY |
| Updates | Updates | `/site/{id}/updates` | `site:manage-update` | Core, plugin, theme updates with rollback |
| WP Config Editor | WP Config | `/site/{id}/wp-config` | `site:manage-wpconfig` | Direct wp-config.php editing |
| Caching | Caching | `/site/{id}/caching` | `site:manage-cache` | Full page cache, object cache (Redis), Cloudflare edge cache, purge |
| Vulnerability Scan | Vulnerability Scan | `/site/{id}/vulnerability-scan` | `site:manage-vulnerability` | Patchstack scanning |
| Integrity Monitor | Integrity Monitor | `/site/{id}/integrity-monitor` | `site:manage-integrity` | Core/plugin/theme checksum monitoring |
| Site Snapshots | Snapshots | `/site/{id}/snapshots` | `site:manage-snapshot` | Save site as template |
| Staging Environment | Staging | `/site/{id}/staging_environment` | `site:manage-staging` | Create staging from production |
| Staging Management | Staging | `/site/{id}/staging-management` | `site:manage-staging` | Push/pull staging ↔ production |
| Email - Mail Delivery | Email > Mail Delivery | `/site/{id}/email-configuration/mail-delivery` | `site:manage-email` | SMTP configuration |
| Email - Mailboxes | Email > Mailboxes | `/site/{id}/email-configuration/mailboxes` | `site:manage-email` | Mailbox management |
| WP-Cron Toggle | Settings | `/site/{id}/settings` | `site:manage-settings` | Switch between WP-Cron and xCloud-Cron |
| Search Engine Visibility | Settings | `/site/{id}/settings` | `site:manage-settings` | Toggle noindex |
| Bulk WP Management | User menu | `/user/wordpress-management` | Team owner | Bulk update/activate/deactivate across sites |

### Laravel-Specific Features

These features ONLY appear for Laravel sites.

| Feature | Menu Path | URL Pattern | Permission | Notes |
|---------|-----------|-------------|------------|-------|
| Application | Application | `/site/{id}/application` | `site:manage-application` | Debug toggle, maintenance mode, environment selector, clear cache |
| Horizon | Application > Horizon | `/site/{id}/application` | `site:manage-application` | Start/stop/restart, output viewer, worker config |
| Scheduler | Application > Scheduler | `/site/{id}/application` | `site:manage-application` | Setup/stop scheduler |
| Queue Workers | Application > Queue | `/site/{id}/application` | `site:manage-application` | Start/stop/update supervisor-managed workers |
| Environment | Environment | `/site/{id}/environment` | `site:manage-environment` | .env file editor |

### Node.js-Specific Features

These features ONLY appear for Node.js sites.

| Feature | Menu Path | URL Pattern | Permission | Notes |
|---------|-----------|-------------|------------|-------|
| Environment | Environment | `/site/{id}/environment` | `site:manage-environment` | Environment variables editor |
| SSR Configuration | SSR Configuration | `/site/{id}/ssr-configuration` | `site:manage-ssr` | App port, start command, Node settings |

### Docker App Features

Docker apps (n8n, Ollama, Nextcloud, LibreChat, Docker Compose) have limited feature sets.

| App Type | Features | Unique URLs | Notes |
|----------|----------|-------------|-------|
| n8n | Environment + Updates | `/site/{id}/n8n-updates` | Version management via UI |
| Ollama | Environment + Model Management | `/site/{id}/ollama/management` | Download/delete AI models |
| Nextcloud | Configuration + Environment | `/site/{id}/nextcloud/configuration` | Nextcloud-specific settings |
| LibreChat | Environment + Ollama integration | `/site/{id}/environment` | Connect to Ollama instance |
| Docker Compose | Environment only | `/site/{id}/environment` | Custom compose apps |

### Web Server Security (Tools Section)

Available under the "Tools" or "Security" section in the site sidebar.

| Feature | Menu Path | URL Pattern | Conditions | Notes |
|---------|-----------|-------------|------------|-------|
| Nginx & Security / Security | Tools > Security | `/site/{id}/security` | All stacks (label varies) | Stack-dependent label |
| 7G/8G Firewall Rules | Tools > Security | `/site/{id}/security` | All stacks | Web application firewall |
| XML-RPC Toggle | Tools > Security | `/site/{id}/security` | WordPress only | Disable XML-RPC |
| X-Frame-Options | Tools > Security | `/site/{id}/security` | All stacks | Clickjacking protection |
| PHP Execution on Upload Dir | Tools > Security | `/site/{id}/security` | WordPress only | Block PHP in uploads |
| Nginx Customization | Nginx Customization | `/site/{id}/nginx-customization` | Nginx stack only | Custom Nginx directives |

---

## Site Type Feature Matrix

Quick lookup: which feature categories apply to which site types.

| Feature Category | WP | Laravel | PHP | Node | n8n | Ollama | Docker Compose |
|-----------------|:--:|:-------:|:---:|:----:|:---:|:------:|:--------------:|
| Updates/Rollback | ✓ | | | | ✓ | | |
| WP Config / .env Editor | ✓ | ✓ | | | | | |
| Debug Mode UI | ✓ | ✓ | | | | | |
| Caching | ✓ | | | | | | |
| Vulnerability Scan | ✓ | | | | | | |
| Integrity Monitor | ✓ | | | | | | |
| Horizon/Scheduler | | ✓ | | | | | |
| Queue Workers | | ✓ | | | | | |
| SSR Configuration | | | | ✓ | | | |
| Model Management | | | | | | ✓ | |
| Staging Environment | ✓ | | | | | | |
| Email Configuration | ✓ | | | | | | |
| Site Snapshots | ✓ | | | | | | |
| Backups | ✓ | ✓ | ✓ | ✓ | | | |
| PHP Analytics | ✓ | ✓ | ✓ | | | | |
| MySQL Analytics | ✓ | ✓ | ✓ | | | | |
| Traffic Analytics | ✓ | ✓ | ✓ | ✓ | | | |
| Redirection Rules | ✓ | ✓ | ✓ | ✓ | | | |
| Git Integration | ✓ | ✓ | ✓ | ✓ | | | |
| Basic Authentication | ✓ | ✓ | ✓ | ✓ | | | |
| Nginx Customization | ✓* | ✓* | ✓* | ✓* | | | |

`*` = Nginx stack only

---

## Key UI Workflows Agents Commonly Miss

Step-by-step Playwright workflows for features agents tend to test via CLI instead of UI. Each workflow follows the pattern: navigate → snapshot → interact → verify → screenshot.

### 1. WordPress Debug Mode

**Wrong approach:** `sed -i 's/WP_DEBUG=false/WP_DEBUG=true/' .env` via SSH
**Correct approach:** Use the xCloud UI

```
1. browser_navigate → /server/{server_id}/site/{site_id}/wp-debug
2. browser_snapshot → identify WP_DEBUG toggle switch
3. browser_click → toggle WP_DEBUG to enabled
4. browser_wait_for → toast notification confirming change
5. browser_snapshot → verify toggle shows enabled state
6. browser_take_screenshot → qa-screenshots/XX-wp-debug-enabled.png
7. (Optional) Toggle WP_DEBUG_LOG and WP_DEBUG_DISPLAY similarly
8. CLI verification: grep "WP_DEBUG" {site-path}/wp-config.php
```

### 2. Laravel Debug Mode

**Wrong approach:** `sed -i 's/APP_DEBUG=false/APP_DEBUG=true/' .env` via SSH
**Correct approach:** Use the xCloud UI

```
1. browser_navigate → /server/{server_id}/site/{site_id}/application
2. browser_snapshot → identify debug mode toggle
3. browser_click → toggle debug mode to enabled
4. browser_wait_for → toast notification confirming change
5. browser_snapshot → verify toggle shows enabled state
6. browser_take_screenshot → qa-screenshots/XX-laravel-debug-enabled.png
7. CLI verification: grep "APP_DEBUG" {site-path}/.env
```

### 3. PHP Version Install/Switch

```
1. browser_navigate → /server/{server_id}/php-configuration
2. browser_snapshot → identify available PHP versions and their status
3. browser_click → click "Install" next to the desired PHP version
4. browser_wait_for → installation progress/completion (may take 30-60s)
5. browser_snapshot → verify "Installed" badge appears
6. browser_take_screenshot → qa-screenshots/XX-php-version-installed.png
7. CLI verification: php{VER} -v && dpkg -l | grep php{VER} | wc -l
```

### 4. Caching Management (WordPress)

```
1. browser_navigate → /server/{server_id}/site/{site_id}/caching
2. browser_snapshot → identify cache type toggles (full page, object cache, edge cache)
3. browser_click → enable/disable the target cache type
4. browser_wait_for → toast notification confirming change
5. browser_snapshot → verify cache status updated
6. browser_take_screenshot → qa-screenshots/XX-caching-status.png
7. To purge: browser_click → "Purge Cache" button → wait for confirmation
```

### 5. SSL Certificate Management

```
1. browser_navigate → /server/{server_id}/site/{site_id}/ssl
2. browser_snapshot → identify current SSL status and available actions
3. browser_click → "Issue Certificate" or "Renew" button
4. browser_wait_for → certificate issuance/renewal (may take 15-30s)
5. browser_snapshot → verify "Active" / "Secured" status
6. browser_take_screenshot → qa-screenshots/XX-ssl-status.png
7. CLI verification: echo | openssl s_client -servername {domain} -connect {domain}:443 2>/dev/null | openssl x509 -noout -dates -subject
```

### 6. Database User Management

```
1. browser_navigate → /server/{server_id}/database
2. browser_snapshot → identify "Create User" button and existing users list
3. browser_click → "Create User" button
4. browser_snapshot → identify the creation form fields
5. browser_fill_form → enter username and password
6. browser_click → "Create" / "Submit" button
7. browser_wait_for → toast notification or user appearing in list
8. browser_snapshot → verify new user in the list
9. browser_take_screenshot → qa-screenshots/XX-db-user-created.png
10. CLI verification: mysql -e "SELECT user, host FROM mysql.user WHERE user='{username}';"
```

### 7. Firewall Rule Management

```
1. browser_navigate → /server/{server_id}/firewall-management
2. browser_snapshot → identify "Add Rule" button and existing rules
3. browser_click → "Add Rule" button
4. browser_snapshot → identify the rule form fields
5. browser_fill_form → enter port, protocol, IP range
6. browser_click → "Add" / "Submit" button
7. browser_wait_for → toast notification or rule appearing in list
8. browser_snapshot → verify new rule in the list
9. browser_take_screenshot → qa-screenshots/XX-firewall-rule-added.png
10. CLI verification: ufw status numbered | grep {port}
```

### 8. Service Restart

```
1. browser_navigate → /server/{server_id}/server-settings
2. browser_snapshot → identify service restart buttons (Nginx, MySQL, PHP-FPM, etc.)
3. browser_click → click restart button for the target service
4. browser_wait_for → toast notification confirming restart
5. browser_snapshot → verify service status indicator
6. browser_take_screenshot → qa-screenshots/XX-service-restarted.png
7. CLI verification (via Command Runner):
   - Nginx: systemctl is-active nginx && systemctl show nginx --property=ActiveEnterTimestamp
   - MySQL: systemctl is-active mysql && systemctl show mysql --property=ActiveEnterTimestamp
   - PHP-FPM: systemctl is-active php{VER}-fpm
```

### 9. Supervisor / Queue Workers (Laravel)

```
1. For server-level: browser_navigate → /server/{server_id}/supervisor
   For Laravel site: browser_navigate → /server/{server_id}/site/{site_id}/application
2. browser_snapshot → identify worker list and status
3. browser_click → start/stop/restart worker button
4. browser_wait_for → status change confirmation
5. browser_snapshot → verify worker status updated
6. browser_take_screenshot → qa-screenshots/XX-supervisor-workers.png
7. CLI verification: supervisorctl status
```
