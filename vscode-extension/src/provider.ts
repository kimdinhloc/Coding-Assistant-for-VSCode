import * as vscode from 'vscode';
import { streamCompletion } from './sseClient';

type CompletionPayload = {
  prefix: string;
  suffix: string;
  language: string;
};

type CacheEntry = { key: string; value: string; createdAt: number };

class LruTtlCache {
  private map = new Map<string, CacheEntry>();

  constructor(private readonly maxSize: number, private readonly ttlMs: number) {}

  get(key: string): string | undefined {
    const current = this.map.get(key);
    if (!current) return undefined;
    if (Date.now() - current.createdAt > this.ttlMs) {
      this.map.delete(key);
      return undefined;
    }

    this.map.delete(key);
    this.map.set(key, current);
    return current.value;
  }

  set(key: string, value: string): void {
    if (this.map.has(key)) {
      this.map.delete(key);
    }

    this.map.set(key, { key, value, createdAt: Date.now() });
    if (this.map.size <= this.maxSize) return;

    const firstKey = this.map.keys().next().value as string | undefined;
    if (firstKey) this.map.delete(firstKey);
  }
}

export class CopilotStyleInlineProvider implements vscode.InlineCompletionItemProvider {
  private readonly completionCache = new LruTtlCache(256, 10_000);
  private readonly prefixCache = new LruTtlCache(512, 5_000);
  private readonly inFlight = new Map<string, AbortController>();
  private readonly lastRequestMs = new Map<string, number>();

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    _context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken,
  ): Promise<vscode.InlineCompletionItem[]> {
    await delay(50); // debounce
    if (token.isCancellationRequested) return [];

    const fileKey = document.uri.toString();
    if (!this.allowRequest(fileKey, 75)) return []; // throttle

    const payload = this.buildPayload(document, position);
    const cacheKey = `${fileKey}:${document.version}:${position.line}:${position.character}`;

    const cachedCompletion = this.completionCache.get(cacheKey);
    if (cachedCompletion) return [this.toInlineItem(cachedCompletion, position)];

    const prefixHashKey = `${fileKey}:${hashString(payload.prefix.slice(-512))}:${hashString(payload.suffix.slice(0, 256))}`;
    const prefixHit = this.prefixCache.get(prefixHashKey);
    if (prefixHit) return [this.toInlineItem(prefixHit, position)];

    this.inFlight.get(fileKey)?.abort();
    const ctrl = new AbortController();
    this.inFlight.set(fileKey, ctrl);

    let completion = '';
    await streamCompletion(
      'http://localhost:8000/v1/completions/stream',
      payload,
      token,
      ctrl.signal,
      (chunk) => {
        completion += chunk;
      },
      { timeoutMs: 30_000, maxReconnect: 1 },
    );

    this.inFlight.delete(fileKey);
    const normalized = completion.replace(/\r\n/g, '\n').trimEnd();
    if (!normalized.trim()) return [];

    this.completionCache.set(cacheKey, normalized);
    this.prefixCache.set(prefixHashKey, normalized);
    return [this.toInlineItem(normalized, position)];
  }

  private allowRequest(fileKey: string, throttleMs: number): boolean {
    const now = Date.now();
    const last = this.lastRequestMs.get(fileKey) ?? 0;
    if (now - last < throttleMs) return false;
    this.lastRequestMs.set(fileKey, now);
    return true;
  }

  private toInlineItem(text: string, position: vscode.Position): vscode.InlineCompletionItem {
    const item = new vscode.InlineCompletionItem(text, new vscode.Range(position, position));
    return item;
  }

  private buildPayload(document: vscode.TextDocument, position: vscode.Position): CompletionPayload {
    const prefix = document.getText(new vscode.Range(new vscode.Position(0, 0), position));
    const suffix = document.getText(
      new vscode.Range(position, document.lineAt(document.lineCount - 1).range.end),
    );
    return { prefix, suffix, language: document.languageId };
  }
}

async function delay(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

function hashString(value: string): string {
  let hash = 5381;
  for (let i = 0; i < value.length; i += 1) {
    hash = ((hash << 5) + hash) ^ value.charCodeAt(i);
  }
  return (hash >>> 0).toString(16);
}
