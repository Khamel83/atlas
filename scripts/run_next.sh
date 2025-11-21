#!/usr/bin/env bash
set -euo pipefail
N="${1:-1}"
PICKS="$(python3 scripts/next_task.py pick "$N")"
if [[ -z "$PICKS" || "$PICKS" == "NO-READY-TASK" ]]; then
  echo "[next] no ready tasks"; exit 0
fi
python3 - <<'PY' "$PICKS"
import os,sys,json,subprocess
picks=json.loads(sys.argv[1])
for t in picks:
  tid=t["id"]; slug=t["slug"]
  # Preflight & index
  subprocess.check_call(["bash","scripts/preflight.sh"])
  env=os.environ.copy(); env["CURRENT_TASK_ID"]=tid
  subprocess.check_call(["bash","scripts/update_index.sh"], env=env)
  # Branch
  subprocess.check_call(["git","checkout","-b",f"task/{tid}-{slug}"])
  print(f"==> READY: Execute task {tid} ({t['title']}). Follow agents.md lifecycle.")
PY