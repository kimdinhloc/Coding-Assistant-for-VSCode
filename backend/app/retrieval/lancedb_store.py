from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import math


@dataclass(slots=True)
class VectorRecord:
    doc_id: str
    path: str
    language: str
    chunk: str
    embedding: list[float]
    modified_at: float


class LanceDBStore:
    """In-memory LanceDB-like adapter for development.

    Mirrors production interfaces: indexing, delta upserts, hybrid retrieval and reranking.
    """

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    async def index_repository(self, repo_root: str, extensions: tuple[str, ...] = (".py", ".ts", ".js", ".go", ".rs")) -> int:
        count = 0
        for path in Path(repo_root).rglob("*"):
            if not path.is_file() or path.suffix not in extensions:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            await self.upsert_file(str(path), text, self._language_from_ext(path.suffix), path.stat().st_mtime)
            count += 1
        return count

    async def upsert_file(self, path: str, content: str, language: str, modified_at: float) -> None:
        chunks = self._chunk(content)
        for idx, chunk in enumerate(chunks):
            doc_id = f"{path}:{idx}"
            self._records[doc_id] = VectorRecord(
                doc_id=doc_id,
                path=path,
                language=language,
                chunk=chunk,
                embedding=self._embed(chunk),
                modified_at=modified_at,
            )

    async def search(self, query: str, language: str, k: int = 5) -> list[dict]:
        q_emb = self._embed(query)
        candidates = [r for r in self._records.values() if r.language == language] or list(self._records.values())
        scored = []
        for rec in candidates:
            semantic = self._cosine(q_emb, rec.embedding)
            lexical = 1.0 if any(tok in rec.chunk.lower() for tok in query.lower().split()) else 0.0
            score = (0.7 * semantic) + (0.3 * lexical)
            scored.append((score, rec))
        scored.sort(key=lambda item: item[0], reverse=True)

        top = []
        for score, rec in scored[:k]:
            top.append({"path": rec.path, "score": score, "recency": rec.modified_at, "text": rec.chunk})
        return top

    def _chunk(self, content: str, chunk_size: int = 600, overlap: int = 120) -> list[str]:
        if not content:
            return []
        out = []
        start = 0
        while start < len(content):
            end = min(len(content), start + chunk_size)
            out.append(content[start:end])
            if end >= len(content):
                break
            start = max(0, end - overlap)
        return out

    def _embed(self, text: str, dim: int = 32) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [digest[i] / 255 for i in range(dim)]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def _language_from_ext(self, ext: str) -> str:
        return {".py": "python", ".ts": "typescript", ".js": "javascript", ".go": "go", ".rs": "rust"}.get(ext, "python")
