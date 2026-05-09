import * as vscode from 'vscode';

export type TokenHandler = (token: string) => void;

export type StreamOptions = {
  timeoutMs: number;
  maxReconnect: number;
};

const DEFAULT_STREAM_OPTIONS: StreamOptions = {
  timeoutMs: 30_000,
  maxReconnect: 1,
};

export async function streamCompletion(
  url: string,
  payload: unknown,
  token: vscode.CancellationToken,
  externalAbort: AbortSignal,
  onToken: TokenHandler,
  options: Partial<StreamOptions> = {},
): Promise<void> {
  const cfg = { ...DEFAULT_STREAM_OPTIONS, ...options };

  let attempt = 0;
  while (attempt <= cfg.maxReconnect && !token.isCancellationRequested) {
    try {
      const completed = await streamAttempt(url, payload, token, externalAbort, onToken, cfg.timeoutMs);
      if (completed) return;
    } catch {
      // retry loop
    }

    attempt += 1;
    if (attempt <= cfg.maxReconnect) {
      await sleep(150 * attempt);
    }
  }
}

async function streamAttempt(
  url: string,
  payload: unknown,
  token: vscode.CancellationToken,
  externalAbort: AbortSignal,
  onToken: TokenHandler,
  timeoutMs: number,
): Promise<boolean> {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(payload),
    signal: AbortSignal.any([AbortSignal.timeout(timeoutMs), toAbortSignal(token), externalAbort]),
  });

  if (!response.ok || !response.body) return false;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (!token.isCancellationRequested) {
    const { done, value } = await reader.read();
    if (done) return true;

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';

    for (const frame of frames) {
      const dataLine = frame.split('\n').find((line) => line.startsWith('data: '));
      if (!dataLine) continue;

      const data = JSON.parse(dataLine.slice(6));
      if (data.type === 'token') onToken(String(data.token ?? ''));
      if (data.type === 'done') return true;
      if (data.type === 'error') return false;
    }
  }

  return true;
}

function toAbortSignal(token: vscode.CancellationToken): AbortSignal {
  const ctrl = new AbortController();
  token.onCancellationRequested(() => ctrl.abort());
  return ctrl.signal;
}

async function sleep(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}
