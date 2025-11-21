#!/usr/bin/env python3
import os, json, hashlib, subprocess, time, gzip, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_JSON = ROOT / 'AGENT_INDEX.json'
INDEX_GZ   = ROOT / 'AGENT_INDEX.json.gz'
INDEX_MD   = ROOT / 'AGENT_INDEX.md'

# Behavior flags (env-driven)
INCLUDE_UNTRACKED = os.getenv("INCLUDE_UNTRACKED", "0") == "1"
INDEX_INCLUDE_DIRS = set(filter(None, os.getenv("INDEX_INCLUDE_DIRS","").split(",")))  # e.g., "src,scripts"
INCLUDE_SHA256 = os.getenv("INCLUDE_SHA256","0") == "1"
WRITE_JSON = os.getenv("WRITE_JSON","0") == "1"          # default off; we always write .gz
INDEX_MAX_JSON_MB = float(os.getenv("INDEX_MAX_JSON_MB","50"))  # hard cap if WRITE_JSON=1

EXT_TAGS = {
    '.py':['code','python'], '.md':['doc','markdown'], '.json':['data','json'],
    '.yaml':['config','yaml'], '.yml':['config','yaml'], '.sh':['script','bash'],
    '.ipynb':['notebook'], '.txt':['text'], '.csv':['data','csv']
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def tags_for(path: Path): return EXT_TAGS.get(path.suffix.lower(), ['other'])

def last_commit_for(path: Path) -> str:
    return ""  # Skip git log for performance

def tracked_paths():
    out = subprocess.check_output(['git','ls-files','-z'], cwd=ROOT)
    items = [p for p in out.decode('utf-8', 'ignore').split('\x00') if p]
    return [Path(p) for p in items if Path(ROOT / p).is_file()]

def extra_untracked():
    if not INCLUDE_UNTRACKED or not INDEX_INCLUDE_DIRS: return []
    extras = []
    for top in INDEX_INCLUDE_DIRS:
        base = ROOT / top
        if not base.exists(): continue
        for dp, dn, fn in os.walk(base):
            for name in fn:
                p = Path(dp)/name
                if p.is_file(): extras.append(p.relative_to(ROOT))
    return extras

def main():
    files = tracked_paths() + extra_untracked()
    # De-dup and normalize
    seen = set(); norm = []
    for p in files:
        s = str(p).replace('\\','/')
        if s in seen: continue
        if s in {'AGENT_INDEX.md','AGENT_INDEX.json','AGENT_INDEX.json.gz'}: continue
        seen.add(s); norm.append(Path(s))
    entries=[]
    for p in norm:
        abspath = ROOT / p
        try: st = abspath.stat()
        except FileNotFoundError: continue
        digest = sha256(abspath) if INCLUDE_SHA256 else ""
        fid = (digest[:8] if digest else hashlib.sha1(str(p).encode()).hexdigest()[:8])
        entries.append({
            "fid": fid,
            "path": str(p),
            "size": st.st_size,
            "mtime": int(st.st_mtime),
            **({"sha256": digest} if INCLUDE_SHA256 else {}),
            "tags": tags_for(p),
            "last_commit": last_commit_for(p)
        })
    entries.sort(key=lambda e: (e["path"]))
    idx = {"generated_at": int(time.time()), "count": len(entries), "entries": entries}

    # Write gz (always, minified)
    with gzip.open(INDEX_GZ, 'wt', encoding='utf-8') as f:
        json.dump(idx, f, separators=(',',':'))

    # Write MD summary (small)
    lines = []
    lines.append("# Agentic File Index")
    lines.append("")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(idx['generated_at']))} UTC")
    lines.append(f"Count: {idx['count']}")
    lines.append("")
    lines.append("| fid | path | size | tags | last_commit |")
    lines.append("|---|---|---:|---|---|")
    for e in idx['entries'][:2000]:  # cap rows for readability
        tags=",".join(e['tags'])
        lines.append(f"| `{e['fid']}` | `{e['path']}` | {e['size']} | {tags} | `{e['last_commit'][:8]}` |")
    INDEX_MD.write_text("\n".join(lines)+"\n", encoding='utf-8')

    # Optionally write plain JSON if small and explicitly enabled
    if WRITE_JSON:
        tmp = ROOT/'._tmp_index.json'
        tmp.write_text(json.dumps(idx, separators=(',',':')), encoding='utf-8')
        mb = tmp.stat().st_size/1_000_000
        if mb <= INDEX_MAX_JSON_MB:
            tmp.replace(INDEX_JSON)
            print(f"[index] wrote AGENT_INDEX.json ({mb:.1f}MB)")
        else:
            tmp.unlink(missing_ok=True)
            print(f"[index] skipped plain JSON: would be {mb:.1f}MB > cap {INDEX_MAX_JSON_MB}MB")
    print(f"[index] wrote {INDEX_GZ} and {INDEX_MD} (tracked-files-only: {len(entries)} entries)")
if __name__ == "__main__":
    main()