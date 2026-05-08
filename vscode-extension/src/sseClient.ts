import * as vscode from 'vscode';

export type TokenHandler = (token: string) => void;

export async function streamCompletion(
  url: string,
  payload: unknown,
  token: vscode.CancellationToken,
  onToken: TokenHandler,
): Promise<void> {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(payload),
    signal: AbortSignal.any([AbortSignal.timeout(30_000), toAbortSignal(token)]),
  });

  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (!token.isCancellationRequested) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';
    for (const evt of events) {
      const line = evt.split('\n').find((l) => l.startsWith('data: '));
      if (!line) continue;
      const data = JSON.parse(line.slice(6));
      if (data.type === 'token') onToken(data.token);
      if (data.type === 'done') return;
    }
  }
}

function toAbortSignal(token: vscode.CancellationToken): AbortSignal {
  const ctrl = new AbortController();
  token.onCancellationRequested(() => ctrl.abort());
  return ctrl.signal;
}
