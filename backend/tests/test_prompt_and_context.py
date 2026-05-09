import asyncio

from app.prompting.fim_prompt import build_fim_prompt, compress_code
from app.services.context_engine import build_context


def test_fim_prompt_format_and_cache():
    context = {
        "language": "python",
        "scope": "nested",
        "retrieved_count": 1,
        "imports": ["import os"],
        "symbols": [{"name": "f", "kind": "function", "line": 1}],
        "compressed_context": "ctx",
    }
    first = build_fim_prompt("a=1", "print(a)", context, "python")
    second = build_fim_prompt("a=1", "print(a)", context, "python")
    assert "<fim_prefix>" in first["prompt"]
    assert "<fim_suffix>" in first["prompt"]
    assert "<fim_middle>" in first["prompt"]
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True


def test_context_budget_and_signal_extraction():
    prefix = "import os\n\nclass A:\n    pass\n" + ("x" * 5000)
    suffix = "y" * 3000
    retrieved = [{"text": "useful chunk", "score": 0.9, "recency": 0.5}]
    context = asyncio.run(build_context(prefix, suffix, "python", retrieved_chunks=retrieved))
    assert context["char_budget"] == 7000
    assert len(context["prefix_tail"]) == 3500
    assert len(context["suffix_head"]) == 1200
    assert "import os" in context["imports"]


def test_prompt_compression_removes_comments_and_duplicates():
    text = "# one\nvalue = 1\nvalue = 1\n// js\n"
    compressed = compress_code(text)
    assert "# one" not in compressed
    assert "// js" not in compressed
    assert compressed.count("value = 1") == 1
