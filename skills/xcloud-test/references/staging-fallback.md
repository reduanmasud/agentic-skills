# Fallback — a plain SSH staging server (no xcdev lab)

Use only when the lab is unreachable (`lab_list` fails and the user has no lab access). Everything in
SKILL.md still applies (spec before code, baseline, sentinel, evidence); only the tools change. Tell the user
up front what this path cannot do: no fresh servers per stack/release, no seeded roles, usually no `dev`
baseline next to the PR.

## Ask for (never assume)

Staging URL; SSH `user@host` and app path; which managed servers on that staging may be changed (never a
customer's); accounts for: team owner, a second team (cross-team checks), a member with a limited role.

## Deploy

```bash
python3 ~/.claude/skills/xcloud-test/scripts/deploy_to_staging.py --pr <N> --ssh <user@host> --path <app path>
```

It deploys the PR head commit (also for merged PRs), installs, migrates, builds, clears caches, restarts the
queue workers and verifies HEAD. Staging's served directory can differ from its git checkout (Forge deploys):
compare the deployed commit with the PR head before trusting results.

Baseline: if a second staging runs `dev`, use it; otherwise run the primary check **before** deploying the PR
(on whatever staging runs now, after confirming it is `dev`) and again after.

## Tool equivalents

| Lab tool | Fallback |
|---|---|
| `app_tinker` | `ssh <host> "cd <path> && php artisan tinker --execute=\"\$(cat f.php)\""` (file content, not a file argument) |
| `cp_exec` + `sentinel.sh` | `ssh <host> "cd <path> && MODE=before bash -s" < sentinel.sh` (set `APP=<path>`; DB access via `php artisan db` or the `.env` credentials, never printed) |
| `app_wait_tasks` / `task_log` | tinker: `Task::where('id','>',$max)->get(['id','name','status','exit_code'])` |
| `page_check` / `lab-flow.mjs` | `playwright-cli -s=<check-id> open <url>` then `goto`, `snapshot`, `click`, `fill`, `screenshot --filename <f>`, `console`, `requests`, `close` (scope the session; never `pkill chromium` while other agents run) |
| `server_exec` on a managed server | the dashboard's Server > Management > Commands, or SSH if you were given it |
| `site_http` | `curl -s -o /dev/null -w '%{http_code}'` against the site from a host that can reach it |

## Test data

Prefer the app's own flows to create servers and sites. When a record must be made with tinker, use the factory
(`Server::factory()->create([...])`) and the real enums: `Stack` (nginx, openlitespeed, docker_nginx, openclaw,
paperclip, hermes, deepseek_harness), `SiteType` (wordpress, laravel, custom-php, nodejs, docker-compose, ...),
`ServerStatus` (provisioned, ...). Sites have no `team_id`. A record without a real machine behind it is only good
for UI and policy checks: say so in the result. Clean up with the model's own `delete()` and confirm with
`withTrashed()` (soft deletes hide rows from `find()`).

## Screenshots

`python3 ~/.claude/skills/xcloud-test/scripts/upload_screenshots.py --dir <dir> --pr <N> --json` (Cloudinary,
credentials from the environment).
