from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.parsing.tree_sitter_manager import TreeSitterManager


@dataclass(slots=True)
class ContextConfig:
    max_prefix_chars: int = 3500
    max_suffix_chars: int = 1200
    max_total_chars: int = 7000
    max_open_tabs: int = 3
    max_recent_edits: int = 8


def _compress(value: str, max_chars: int, keep_tail: bool) -> str:
    value = "\n".join(line.rstrip() for line in value.splitlines())
    if len(value) <= max_chars:
        return value
    return value[-max_chars:] if keep_tail else value[:max_chars]


def _dedupe_lines(text: str) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and stripped in seen:
            continue
        if stripped:
            seen.add(stripped)
        out.append(line)
    return "\n".join(out)


def _score_chunk(chunk: dict[str, Any], query_tokens: set[str]) -> float:
    text = str(chunk.get("text", ""))
    overlap = len(query_tokens.intersection(text.lower().split()))
    semantic = float(chunk.get("score", 0.0))
    recency = float(chunk.get("recency", 0.0))
    return (0.55 * overlap) + (0.35 * semantic) + (0.10 * recency)


def _rank_chunks(chunks: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_tokens = set(query.lower().split())
    return sorted(chunks, key=lambda chunk: _score_chunk(chunk, query_tokens), reverse=True)


def _extract_imports(source: str) -> list[str]:
    imports: list[str] = []
    for line in source.splitlines():
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            imports.append(s)
    return imports


async def build_context(
    prefix: str,
    suffix: str,
    language: str,
    retrieved_chunks: list[dict[str, Any]] | None = None,
    open_tabs: list[dict[str, str]] | None = None,
    recent_edits: list[str] | None = None,
    config: ContextConfig | None = None,
) -> dict[str, Any]:
    cfg = config or ContextConfig()
    parser = TreeSitterManager()

    prefix_tail = _compress(prefix, cfg.max_prefix_chars, keep_tail=True)
    suffix_head = _compress(suffix, cfg.max_suffix_chars, keep_tail=False)

    imports = _extract_imports(prefix)
    ast = parser.parse("active_buffer", prefix_tail, language)
    ranked = _rank_chunks(retrieved_chunks or [], prefix_tail)[:5]

    tab_snippets = []
    for tab in (open_tabs or [])[: cfg.max_open_tabs]:
        tab_text = _compress(tab.get("content", ""), 400, keep_tail=True)
        tab_snippets.append(f"[{tab.get('path', 'untitled')}]\n{tab_text}")

    edits = "\n".join((recent_edits or [])[-cfg.max_recent_edits :])
    retrieved_text = "\n\n".join(str(item.get("text", "")) for item in ranked)

    fusion = _dedupe_lines(
        "\n\n".join(
            [
                "# imports\n" + "\n".join(imports),
                "# open_tabs\n" + "\n\n".join(tab_snippets),
                "# recent_edits\n" + edits,
                "# retrieval\n" + retrieved_text,
            ]
        )
    )

    remaining = max(cfg.max_total_chars - len(prefix_tail) - len(suffix_head), 0)
    compressed = _compress(fusion, remaining, keep_tail=False)

    return {
        "language": language,
        "prefix_tail": prefix_tail,
        "suffix_head": suffix_head,
        "imports": imports[:20],
        "symbols": ast["symbols"][:40],
        "scope": ast["scope"],
        "retrieved_count": len(ranked),
        "compressed_context": compressed,
        "char_budget": cfg.max_total_chars,
    }
