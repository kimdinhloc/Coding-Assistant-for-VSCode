import asyncio
import tempfile
from pathlib import Path

from app.parsing.tree_sitter_manager import TreeSitterManager
from app.retrieval.lancedb_store import LanceDBStore


def test_multilanguage_symbol_extraction_and_incremental_cache():
    mgr = TreeSitterManager()
    src = "class A:\n    def run(self):\n        value = 1\n"
    first = mgr.parse("a.py", src, "python")
    second = mgr.parse("a.py", src, "python")
    assert any(s["kind"] == "class" for s in first["symbols"])
    assert any(s["kind"] == "function" for s in first["symbols"])
    assert second["incremental"] is True


def test_repo_indexing_and_semantic_search():
    store = LanceDBStore()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "main.py"
        path.write_text("def add(a, b):\n    return a + b\n")
        asyncio.run(store.index_repository(tmp))
        result = asyncio.run(store.search("add function", "python", k=3))
        assert len(result) >= 1
        assert "add" in result[0]["text"]
