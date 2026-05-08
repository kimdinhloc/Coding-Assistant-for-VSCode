from typing import Dict

async def build_context(prefix: str, suffix: str, language: str) -> Dict:
    return {
        "language": language,
        "prefix_tail": prefix[-1200:],
        "suffix_head": suffix[:800],
        "symbols": [],
        "retrieved_chunks": [],
        "budget": 3000,
    }
