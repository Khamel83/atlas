#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import sqlite3
from pathlib import Path
from os import getenv

from vos.monitoring import queue_summary
from vos.search.whoosh_search import get_index
from vos.storage.database import get_connection

summary = queue_summary()
print('[mcp] queue summary:')
for k, v in summary.items():
    print(f'  {k}: {v}')

index_path = Path(getenv('WHOOSH_INDEX_PATH', 'data/search_index'))
ix = get_index(index_path)
with ix.searcher() as searcher:
    print('[mcp] whoosh total docs:', searcher.doc_count())

db_path = getenv('DATABASE_PATH', 'data/atlas_vos.db')
conn = get_connection(db_path)
cursor = conn.execute('SELECT COUNT(*) FROM content')
count = cursor.fetchone()[0]
print('[mcp] sqlite content rows:', count)
conn.close()
PY
