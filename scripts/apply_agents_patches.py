#!/usr/bin/env python3
import pathlib

t = pathlib.Path("agents.md")
text = t.read_text(encoding="utf-8") if t.exists() else ""

def upsert(txt, name, body):
    name = name.strip().upper()
    begin = f"<!-- BEGIN: {name} -->"
    end   = f"<!-- END: {name} -->"
    block = f"{begin}\n{body.strip()}\n{end}\n"
    if begin in txt and end in txt:
        pre = txt.split(begin)[0]
        post = txt.split(end, 1)[1]
        if not pre.endswith("\n"): pre += "\n"
        return pre + block + post.lstrip("\n")
    sep = "\n" if txt and not txt.endswith("\n") else ""
    return txt + sep + block

SECTIONS = {
 "PRE_FLIGHT_HARD_CHECKS_EXTENDED":
    "- `scripts/preflight.sh` must pass (ensures `.env`, OpenRouter defaults, budgets, policy).\n" +
    "- Refresh index **before** changes: `CURRENT_TASK_ID=<ID> scripts/update_index.sh`.\n" +
    "- Budget gate (estimate): `python3 scripts/budget_guard.py check --cost <est_cost_usd> --task <ID>`.\n" +
    "- Then proceed with branch creation and task execution."
 ,

 "POST_MERGE_EXTENDED":
    "- Refresh index and commit:\n" +
    "  - `scripts/update_index.sh`\n" +
    "  - `git add AGENT_INDEX.* && git commit -m \"task(<ID>): refresh index\" && git push`\n" +
    "- Budget log (actual or estimate): `python3 scripts/budget_guard.py log --cost <actual_or_est> --task <ID>`. "
 ,

 "TASK_SELECTION_POLICY":
    "### Task Selection Policy (no user prompts)\n" +
    "- When you are about to ask “what next?”, run:\n" +
    "  - `python3 scripts/next_task.py pick` → JSON of the highest-priority **unblocked** task(s).\n" +
    "- For each selected task `<ID>` / `<slug>`:\n" +
    "  1) `scripts/preflight.sh`\n" +
    "  2) `CURRENT_TASK_ID=<ID> scripts/update_index.sh`\n" +
    "  3) Create branch: `git checkout -b task/<ID>-<slug>` from `main`\n" +
    "  4) Execute steps from `tasks.md`\n" +
    "  5) Verify gates (tests/lint/integration)\n" +
    "  6) Append `EXECUTION_LOG.md`\n" +
    "  7) Merge to `main` (no squash)\n" +
    "  8) Post-merge index + budget log per the anchored sections\n" +
    "- If `NO-READY-TASK`: rebuild index; if still none, create `PLAN-NEXT` task with concrete next steps and stop."
 ,

 "ID_BASED_ADDRESSING":
    "### ID-based addressing\n" +
    "- Prefer `fid` from `AGENT_INDEX.json` over filenames.\n" +
    "- To resolve:\n" +
    "  - `python3 scripts/resolve_id.py to-path <fid>` → path\n" +
    "  - `python3 scripts/resolve_id.py to-id <path>` → fid\n" +
    "- Always update the index before and after tasks to keep IDs accurate."
 ,

 "GRACEFUL_FAILURE_POLICY":
    "### Graceful failure policy\n" +
    "- `ON_ERROR=skip|halt|ask` (default `skip`).\n" +
    "  - **skip**: If non-blocking, open `FIX-<ID>-<slug>`, log details, continue.\n" +
    "  - **halt**: Stop immediately on failure; log and exit.\n" +
    "  - **ask**: Stop and emit: **\"come help me please user\"**.\n" +
    "- `STRICT_MODE=true` forces halt on ambiguity; otherwise create a small “clarify” task and continue."
 }

for k, v in SECTIONS.items():
    text = upsert(text, k, v)

t.write_text(text, encoding="utf-8")
print("Upserted:", ", ".join(SECTIONS.keys()))