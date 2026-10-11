# xCloud UI Feature Map

## How to Use

UI hints for the code-map agent: which page a feature lives on and who may use it. **It drifts**: confirm
every path in `routes/web.php` before testing. Many server and site routes bind the **uuid**
(`/server/{server:uuid}/...`), older ones the integer id: `{uuid}` below is a placeholder, check the route. Test through the UI page when the feature has
one, then verify the effect on the server (`server_exec`, `site_http`); a CLI edit never replaces the UI action.

---

## Server Management Features

Navigate via the left sidebar after selecting a server. Base URL: `/server/{uuid}/`

### Settings & Utilities

| Feature | Menu Path | URL Pattern | Stack Conditions | Permission |
|---------|-----------|-------------|-----------------|------------|
| Server Settings | Settings > Server Settings | `/server/{uuid}/server-settings` | All stacks | `server:manage-settings` |
| Restart Services | Settings > Server Settings | `/server/{uuid}/server-settings` | All stacks (services vary by stack) | `server:manage-settings` |
| Archive Server | Settings > Server Settings | `/server/{uuid}/server-settings` | All stacks | `server:manage-settings` |
| Delete Server | Settings > Server Settings | `/server/{uuid}/server-settings` | All stacks | `server:manage-settings` |
| Command Runner | Settings > Commands | `/server/{uuid}/command-runner` | All stacks | `server:custom-command-runner` |
| Events | Events | `/server/{uuid}/events` | All stacks | `server:view-events` |
| Others (Timezone, Magic Login, Connection) | Others | `/server/{uuid}/others` | All stacks | `server:manage-settings` |

### Infrastructure Management

| Feature | Menu Path | URL Pattern | Stack Conditions | Permission |
|---------|-----------|-------------|-----------------|------------|
| Database Management | Database | `/server/{uuid}/database` | All stacks with MySQL | `server:manage-database` |
| PHP Configuration | PHP Configuration | `/server/{uuid}/php-configuration` | Nginx, OLS stacks (not Docker/OpenClaw) | `server:manage-php` |
| MySQL Configuration | MySQL Configuration | `/server/{uuid}/mysql-configuration` | All stacks with MySQL | `server:manage-mysql-configuration` |
| Node Configuration | Node Configuration | `/server/{uuid}/node-configuration` | All stacks | `server:manage-node` |
| Cron Jobs | Cron Job | `/server/{uuid}/cron-job` | All stacks (not Docker/OpenClaw) | `server:manage-cronjob` |
| Supervisor | Supervisor | `/server/{uuid}/supervisor` | All stacks (not Docker/OpenClaw) | `server:manage-supervisor` |

### Security & Network

| Feature | Menu Path | URL Pattern | Stack Conditions | Permission |
|---------|-----------|-------------|-----------------|------------|
| Firewall Management | Firewall Management | `/server/{uuid}/firewall-management` | All stacks (not OpenClaw) | `server:manage-firewall` |
| Sudo Users | Sudo | `/server/{uuid}/sudo` | All stacks (not Docker/OpenClaw) | `server:manage-sudo-user` |
| Vulnerability Settings | Vulnerability Settings | `/server/{uuid}/vulnerability-settings` | All stacks (not Docker/OpenClaw) | `server:manage-vulnerability` |
| Security Updates | Security Update | `/server/{uuid}/security-update` | All stacks (not Docker/OpenClaw) | `server:manage-security-update` |

### Monitoring & Logs

| Feature | Menu Path | URL Pattern | Stack Conditions | Permission |
|---------|-----------|-------------|-----------------|------------|
| Server Monitoring | Monitoring | `/server/{uuid}/monitoring` | All stacks | `server:view-monitoring` |
| Server Logs | Logs | `/server/{uuid}/logs` | Nginx, OLS stacks | `server:view-logs` |
| Backup | Backup | `/server/{uuid}/backup` | All stacks (not OpenClaw) | `server:manage-backup` |
| Migration | Migration | `/server/{uuid}/migration` | All stacks (not Docker/OpenClaw) | `server:manage-migration` |

### OpenClaw Server Routes (Different Menu)

OpenClaw servers have a completely different management interface. Do NOT look for standard server features on OpenClaw servers.

| Feature | URL Pattern | Description |
|---------|-------------|-------------|
| Status | `/server/{uuid}/openclaw/status` | Gateway and service health |
| Providers | `/server/{uuid}/openclaw/providers` | AI provider configuration |
| Channels | `/server/{uuid}/openclaw/channels` | Channel management |
| Configuration | `/server/{uuid}/openclaw/config` | Core gateway settings |
| Environment | `/server/{uuid}/openclaw/environment` | Environment variables |
| Updates | `/server/{uuid}/openclaw/updates` | Version management |
| Reset | `/server/{uuid}/openclaw/reset` | Reset gateway state |
| Logs | `/server/{uuid}/openclaw/logs` | Gateway logs |

---

## Site Management Features

Navigate via the left sidebar after selecting a site. Base URL: `/server/{uuid}/site/{uuid}/` (shortened to `/site/{uuid}/` below).

### Common Features (All Site Types)

These features are available for most site types unless noted otherwise.

| Feature | Menu Path | URL Pattern | Conditions | Permission |
|---------|-----------|-------------|------------|------------|
| Site Overview | Overview | `/site/{uuid}` | All types | `site:view` |
| Domain Management | Domain | `/site/{uuid}/domain` | All types | `site:manage-domain` |
| SSL/HTTPS | SSL | `/site/{uuid}/ssl` | All types | `site:manage-ssl` |
| Redirection Rules | Redirection | `/site/{uuid}/redirection` | All types (not Docker apps) | `site:manage-redirection` |
| Monitoring | Monitoring | `/site/{uuid}/monitoring` | All types | `site:view-monitoring` |
| Logs | Logs | `/site/{uuid}/logs` | All types | `site:view-logs` |
| Events | Events | `/site/{uuid}/events` | All types | `site:view-events` |
| PageSpeed | PageSpeed | `/site/{uuid}/pagespeed` | All types | `site:view-pagespeed` |
| Traffic Analytics | Traffic Analytics | `/site/{uuid}/traffic-analytics` | All types | `site:view-analytics` |
| PHP Analytics | PHP Analytics | `/site/{uuid}/php-analytics` | PHP-based types (not Node/Docker) | `site:view-analytics` |
| MySQL Analytics | MySQL Analytics | `/site/{uuid}/mysql-analytics` | Types with `has_database` | `site:view-analytics` |
| SSH/sFTP Access | SSH/sFTP | `/site/{uuid}/ssh-sftp` | All types (not Docker apps) | `site:manage-ssh` |
| Database Access | Database (Adminer/PHPMyAdmin) | `/site/{uuid}/database` | Types with `has_database` | `site:manage-database` |
| File Manager | File Manager | `/site/{uuid}/file-manager` | All types (not Docker apps) | `site:manage-files` |
| Basic Authentication | Basic Auth | `/site/{uuid}/basic-authentication` | All types (not Docker apps) | `site:manage-basic-auth` |
| IP Management | IP Management | `/site/{uuid}/ip-management` | All types | `site:manage-ip` |
| Commands | Commands | `/site/{uuid}/commands` | All types (not Docker apps) | `site:manage-commands` |
| Backups | Backup | `/site/{uuid}/backup` | WP, Laravel, PHP, Node | `site:manage-backup` |
| Git Integration | Git | `/site/{uuid}/git` | All types (not Docker apps) | `site:manage-git` |
| Site Settings | Settings | `/site/{uuid}/settings` | All types | `site:manage-settings` |

### WordPress-Specific Features

These features ONLY appear for WordPress sites. If testing a WordPress PR, check all of these.

| Feature | Menu Path | URL Pattern | Permission | Notes |
|---------|-----------|-------------|------------|-------|
| WP Debug | WP Debug | `/site/{uuid}/wp-debug` | `site:manage-wpconfig` | UI toggles for WP_DEBUG, WP_DEBUG_LOG, WP_DEBUG_DISPLAY |
| Updates | Updates | `/site/{uuid}/updates` | `site:manage-update` | Core, plugin, theme updates with rollback |
| WP Config Editor | WP Config | `/site/{uuid}/wp-config` | `site:manage-wpconfig` | Direct wp-config.php editing |
| Caching | Caching | `/site/{uuid}/caching` | `site:manage-cache` | Full page cache, object cache (Redis), Cloudflare edge cache, purge |
| Vulnerability Scan | Vulnerability Scan | `/site/{uuid}/vulnerability-scan` | `site:manage-vulnerability` | Patchstack scanning |
| Integrity Monitor | Integrity Monitor | `/site/{uuid}/integrity-monitor` | `site:manage-integrity` | Core/plugin/theme checksum monitoring |
| Site Snapshots | Snapshots | `/site/{uuid}/snapshots` | `site:manage-snapshot` | Save site as template |
| Staging Environment | Staging | `/site/{uuid}/staging_environment` | `site:manage-staging` | Create staging from production |
| Staging Management | Staging | `/site/{uuid}/staging-management` | `site:manage-staging` | Push/pull staging ↔ production |
| Email - Mail Delivery | Email > Mail Delivery | `/site/{uuid}/email-configuration/mail-delivery` | `site:manage-email` | SMTP configuration |
| Email - Mailboxes | Email > Mailboxes | `/site/{uuid}/email-configuration/mailboxes` | `site:manage-email` | Mailbox management |
| WP-Cron Toggle | Settings | `/site/{uuid}/settings` | `site:manage-settings` | Switch between WP-Cron and xCloud-Cron |
| Search Engine Visibility | Settings | `/site/{uuid}/settings` | `site:manage-settings` | Toggle noindex |
| Bulk WP Management | User menu | `/user/wordpress-management` | Team owner | Bulk update/activate/deactivate across sites |

### Laravel-Specific Features

These features ONLY appear for Laravel sites.

| Feature | Menu Path | URL Pattern | Permission | Notes |
|---------|-----------|-------------|------------|-------|
| Application | Application | `/site/{uuid}/application` | `site:manage-application` | Debug toggle, maintenance mode, environment selector, clear cache |
| Horizon | Application > Horizon | `/site/{uuid}/application` | `site:manage-application` | Start/stop/restart, output viewer, worker config |
| Scheduler | Application > Scheduler | `/site/{uuid}/application` | `site:manage-application` | Setup/stop scheduler |
| Queue Workers | Application > Queue | `/site/{uuid}/application` | `site:manage-application` | Start/stop/update supervisor-managed workers |
| Environment | Environment | `/site/{uuid}/environment` | `site:manage-environment` | .env file editor |

### Node.js-Specific Features

These features ONLY appear for Node.js sites.

| Feature | Menu Path | URL Pattern | Permission | Notes |
|---------|-----------|-------------|------------|-------|
| Environment | Environment | `/site/{uuid}/environment` | `site:manage-environment` | Environment variables editor |
| SSR Configuration | SSR Configuration | `/site/{uuid}/ssr-configuration` | `site:manage-ssr` | App port, start command, Node settings |

### Docker App Features

Docker apps (n8n, Ollama, Nextcloud, LibreChat, Docker Compose) have limited feature sets.

| App Type | Features | Unique URLs | Notes |
|----------|----------|-------------|-------|
| n8n | Environment + Updates | `/site/{uuid}/n8n-updates` | Version management via UI |
| Ollama | Environment + Model Management | `/site/{uuid}/ollama/management` | Download/delete AI models |
| Nextcloud | Configuration + Environment | `/site/{uuid}/nextcloud/configuration` | Nextcloud-specific settings |
| LibreChat | Environment + Ollama integration | `/site/{uuid}/environment` | Connect to Ollama instance |
| Docker Compose | Environment only | `/site/{uuid}/environment` | Custom compose apps |

### Web Server Security (Tools Section)

Available under the "Tools" or "Security" section in the site sidebar.

| Feature | Menu Path | URL Pattern | Conditions | Notes |
|---------|-----------|-------------|------------|-------|
| Nginx & Security / Security | Tools > Security | `/site/{uuid}/security` | All stacks (label varies) | Stack-dependent label |
| 7G/8G Firewall Rules | Tools > Security | `/site/{uuid}/security` | All stacks | Web application firewall |
| XML-RPC Toggle | Tools > Security | `/site/{uuid}/security` | WordPress only | Disable XML-RPC |
| X-Frame-Options | Tools > Security | `/site/{uuid}/security` | All stacks | Clickjacking protection |
| PHP Execution on Upload Dir | Tools > Security | `/site/{uuid}/security` | WordPress only | Block PHP in uploads |
| Nginx Customization | Nginx Customization | `/site/{uuid}/nginx-customization` | Nginx stack only | Custom Nginx directives |

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
