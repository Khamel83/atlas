import glob
import os

from meilisearch import Client

MEILI_URL = os.getenv("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "")
client = Client(MEILI_URL, MEILI_KEY)
index = client.index("atlas")

docs = []
for path in glob.glob("output/**/*.md", recursive=True):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    docs.append({"id": path, "content": content})

if docs:
    index.add_documents(docs)
    print(f"Indexed {len(docs)} documents into MeiliSearch.")
else:
    print("No documents found to index.")
