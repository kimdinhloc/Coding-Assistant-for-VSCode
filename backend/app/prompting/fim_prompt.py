from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(slots=True)
class PromptBudget:
    total_chars: int = 9000
    prefix_ratio: float = 0.45
    context_ratio: float = 0.40
    suffix_ratio: float = 0.15


class PromptCache:
    def __init__(self, max_items: int = 512) -> None:
        self.max_items = max_items
        self._items: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        value = self._items.get(key)
        if value is None:
            return None
        self._items.pop(key)
        self._items[key] = value
        return value

    def set(self, key: str, prompt: str) -> None:
        if key in self._items:
            self._items.pop(key)
        self._items[key] = prompt
        if len(self._items) > self.max_items:
            first = next(iter(self._items))
            self._items.pop(first)


PROMPT_CACHE = PromptCache()
STOP_TOKENS = ["<|endoftext|>", "<fim_prefix>", "<fim_suffix>", "<fim_middle>"]


def build_fim_prompt(prefix: str, suffix: str, context: dict, language: str = "python") -> dict:
    budget = PromptBudget()
    prefix_budget = int(budget.total_chars * budget.prefix_ratio)
    context_budget = int(budget.total_chars * budget.context_ratio)
    suffix_budget = budget.total_chars - prefix_budget - context_budget

    p = compress_code(prefix)[-prefix_budget:]
    s = compress_code(suffix)[:suffix_budget]
    c = compress_code(context.get("compressed_context", ""))[:context_budget]

    cache_key = hash_prompt_key(language, p, s, c)
    cached = PROMPT_CACHE.get(cache_key)
    if cached:
        return {"prompt": cached, "stop": STOP_TOKENS, "cache_hit": True}

    lang_instruction = f"# Language: {language}\n# Complete only the missing middle code."
    prompt = (
        "<fim_prefix>\n"
        f"{lang_instruction}\n{p}\n\n"
        f"# Context\n{c}\n"
        "<fim_suffix>\n"
        f"{s}\n"
        "<fim_middle>"
    )
    PROMPT_CACHE.set(cache_key, prompt)
    return {"prompt": prompt, "stop": STOP_TOKENS, "cache_hit": False}


def compress_code(text: str) -> str:
    text = re.sub(r"#.*", "", text)
    text = re.sub(r"//.*", "", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    dedup: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        key = line.strip()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        dedup.append(line)
    return "\n".join(dedup).strip()


def hash_prompt_key(language: str, prefix: str, suffix: str, context: str) -> str:
    raw = f"{language}|{prefix}|{suffix}|{context}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()
