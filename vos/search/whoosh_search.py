from pathlib import Path

from whoosh.fields import ID, TEXT, Schema
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import QueryParser

SCHEMA = Schema(id=ID(stored=True), title=TEXT(stored=True), body=TEXT)


def get_index(index_dir: Path):
    index_dir.mkdir(parents=True, exist_ok=True)
    if exists_in(index_dir):
        return open_dir(index_dir)
    return create_in(index_dir, SCHEMA)


def index_document(index_dir: Path, doc: dict):
    ix = get_index(index_dir)
    with ix.writer() as writer:
        writer.update_document(
            id=doc["id"],
            title=doc.get("title", ""),
            body=doc.get("body", ""),
        )


def search(index_dir: Path, query: str, limit: int = 10):
    ix = get_index(index_dir)
    parser = QueryParser("body", ix.schema)
    parsed = parser.parse(query)
    with ix.searcher() as searcher:
        results = searcher.search(parsed, limit=limit)
        return [{"id": hit["id"], "title": hit["title"]} for hit in results]
