from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import re


SUPPORTED_LANGUAGES = {"python", "typescript", "javascript", "go", "rust"}


@dataclass(slots=True)
class Symbol:
    name: str
    kind: str
    line: int
    language: str
    scope: str


@dataclass(slots=True)
class ParseSnapshot:
    content_hash: str
    symbols: list[Symbol] = field(default_factory=list)
    scope: str = "global"


class TreeSitterManager:
    """Parser manager facade with incremental cache hooks.

    Uses regex walkers as fallback until real tree-sitter bindings are linked.
    """

    def __init__(self) -> None:
        self._cache: dict[str, ParseSnapshot] = {}

    def parse(self, file_path: str, source: str, language: str) -> dict:
        lang = self._normalize_language(language)
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
        cached = self._cache.get(file_path)
        if cached and cached.content_hash == digest:
            return self._to_response(lang, cached, incremental=True)

        symbols = self._extract_symbols(source, lang)
        scope = self._resolve_scope(source)
        snapshot = ParseSnapshot(content_hash=digest, symbols=symbols, scope=scope)
        self._cache[file_path] = snapshot
        return self._to_response(lang, snapshot, incremental=False)

    def apply_incremental_update(self, file_path: str, source: str, language: str, dirty_start: int, dirty_end: int) -> dict:
        del dirty_start, dirty_end  # placeholder for real tree-sitter dirty-range parsing
        return self.parse(file_path, source, language)

    def _normalize_language(self, language: str) -> str:
        lang = language.lower()
        aliases = {"ts": "typescript", "js": "javascript", "py": "python"}
        lang = aliases.get(lang, lang)
        if lang not in SUPPORTED_LANGUAGES:
            return "python"
        return lang

    def _to_response(self, language: str, snapshot: ParseSnapshot, incremental: bool) -> dict:
        return {
            "language": language,
            "scope": snapshot.scope,
            "incremental": incremental,
            "symbols": [asdict(s) for s in snapshot.symbols],
        }

    def _extract_symbols(self, source: str, language: str) -> list[Symbol]:
        lines = source.splitlines()
        symbols: list[Symbol] = []

        patterns = {
            "python": {
                "function": r"\s*def\s+([A-Za-z_][A-Za-z0-9_]*)",
                "class": r"\s*class\s+([A-Za-z_][A-Za-z0-9_]*)",
                "variable": r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=",
            },
            "typescript": {
                "interface": r"\s*interface\s+([A-Za-z_][A-Za-z0-9_]*)",
                "class": r"\s*class\s+([A-Za-z_][A-Za-z0-9_]*)",
                "method": r"\s*(?:public\s+|private\s+|protected\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                "variable": r"\s*(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)",
            },
            "javascript": {
                "function": r"\s*function\s+([A-Za-z_][A-Za-z0-9_]*)",
                "class": r"\s*class\s+([A-Za-z_][A-Za-z0-9_]*)",
                "variable": r"\s*(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)",
            },
            "go": {
                "function": r"\s*func\s+([A-Za-z_][A-Za-z0-9_]*)",
                "type": r"\s*type\s+([A-Za-z_][A-Za-z0-9_]*)",
                "variable": r"\s*var\s+([A-Za-z_][A-Za-z0-9_]*)",
            },
            "rust": {
                "function": r"\s*fn\s+([A-Za-z_][A-Za-z0-9_]*)",
                "struct": r"\s*struct\s+([A-Za-z_][A-Za-z0-9_]*)",
                "variable": r"\s*let\s+(?:mut\s+)?([A-Za-z_][A-Za-z0-9_]*)",
            },
        }

        lang_patterns = patterns.get(language, patterns["python"])
        scope = self._resolve_scope(source)
        for line_no, line in enumerate(lines, start=1):
            for kind, pattern in lang_patterns.items():
                m = re.match(pattern, line)
                if m:
                    symbols.append(Symbol(name=m.group(1), kind=kind, line=line_no, language=language, scope=scope))
                    break
        return symbols

    def _resolve_scope(self, source: str) -> str:
        indent = 0
        for line in source.splitlines()[-60:]:
            if line.strip():
                indent = len(line) - len(line.lstrip(" "))
        return "global" if indent == 0 else "nested"
