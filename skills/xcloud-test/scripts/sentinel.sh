#!/bin/bash
# Silent-failure sentinel for an xcdev environment's control plane. Run it through MCP cp_exec:
# read this file and pass its text as `script`, with the variables below set on the first lines.
#
#   MODE=before                       -> prints one JSON line: {"log_lines":N,"failed_max":N,"task_max":N}
#   MODE=after LOG_LINES=N FAILED_MAX=N TASK_MAX=N [SERVER_ID=N] [SITE_ID=N]
#                                     -> prints JSON: new log errors, new failed jobs, new tasks since `before`
#
# A check whose UI or HTTP answer looks fine but whose `after` shows a new ERROR, failed job or a task with a
# non-zero exit code is not a PASS. Output is trimmed and never includes payloads or stack traces.
set -u
MODE="${MODE:-before}"
APP="${APP:-/workspace/xcloud}"            # fallback staging: APP=<app path>
LOG="$APP/storage/logs/laravel.log"
MYSQL="${MYSQL:-mysql xcloud}"             # fallback staging: MYSQL="mysql -u<user> <db>" (creds from ~/.my.cnf)
q() { $MYSQL -N -B -e "$1" 2>/dev/null; }

log_lines() { [ -f "$LOG" ] && wc -l < "$LOG" | tr -d ' ' || echo 0; }
failed_max() { q "select coalesce(max(id),0) from failed_jobs"; }
task_max() { q "select coalesce(max(id),0) from tasks"; }

if [ "$MODE" = "before" ]; then
  printf '{"log_lines":%s,"failed_max":%s,"task_max":%s}\n' "$(log_lines)" "$(failed_max)" "$(task_max)"
  exit 0
fi

: "${LOG_LINES:?set LOG_LINES from the before snapshot}" "${FAILED_MAX:?}" "${TASK_MAX:?}"
FILTER=""
[ -n "${SERVER_ID:-}" ] && FILTER="$FILTER and server_id=${SERVER_ID}"
[ -n "${SITE_ID:-}" ] && FILTER="$FILTER and site_id=${SITE_ID}"

python3 - "$LOG" "$LOG_LINES" <<'PY' > /tmp/sentinel-log.json
import json, re, sys
path, start = sys.argv[1], int(sys.argv[2])
errors = []
try:
    with open(path, errors="replace") as f:
        for i, line in enumerate(f):
            if i < start:
                continue
            m = re.match(r"^\[([^\]]+)\] \w+\.(ERROR|CRITICAL|ALERT|EMERGENCY|WARNING): (.*)", line)
            if m:
                msg = re.sub(r"\s*\{\"exception\".*", "", m.group(3)).strip()
                errors.append({"at": m.group(1), "level": m.group(2), "message": msg[:300]})
except FileNotFoundError:
    pass
# log rotation: fewer lines than before means a new file; report that instead of nothing
print(json.dumps({"errors": [e for e in errors if e["level"] != "WARNING"][-20:],
                  "warnings": [e for e in errors if e["level"] == "WARNING"][-10:]}))
PY

FAILED=$(q "select id, queue, failed_at, substring_index(exception, '\n', 1) from failed_jobs where id > ${FAILED_MAX} order by id limit 20")
TASKS=$(q "select id, coalesce(server_id,''), coalesce(site_id,''), name, status, coalesce(exit_code,'') from tasks where id > ${TASK_MAX} ${FILTER} order by id limit 50")

python3 - "$FAILED" "$TASKS" <<'PY'
import json, sys
log = json.load(open("/tmp/sentinel-log.json"))
failed = [dict(zip(["id", "queue", "failed_at", "exception"], r.split("\t"))) for r in sys.argv[1].splitlines() if r]
for f in failed:
    f["exception"] = f["exception"][:300]
tasks = [dict(zip(["id", "server_id", "site_id", "name", "status", "exit_code"], r.split("\t"))) for r in sys.argv[2].splitlines() if r]
bad_tasks = [t for t in tasks if t["exit_code"] not in ("", "0") or t["status"] in ("failed", "timeout", "killed")]
running = [t for t in tasks if t["status"] in ("running", "queued")]
print(json.dumps({
    "clean": not log["errors"] and not failed and not bad_tasks,
    "new_errors": log["errors"], "new_warnings": log["warnings"],
    "new_failed_jobs": failed, "tasks": tasks, "failed_tasks": bad_tasks,
    "still_running": [t["id"] for t in running],
}, indent=1))
PY
