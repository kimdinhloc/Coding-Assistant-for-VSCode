import * as vscode from 'vscode';
import { streamCompletion } from './sseClient';

export class CopilotStyleInlineProvider implements vscode.InlineCompletionItemProvider {
  private cache = new Map<string, string>();

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    _context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken,
  ): Promise<vscode.InlineCompletionItem[]> {
    const prefix = document.getText(new vscode.Range(new vscode.Position(0, 0), position));
    const suffix = document.getText(new vscode.Range(position, document.lineAt(document.lineCount - 1).range.end));
    const key = `${document.uri.toString()}:${document.version}:${position.line}:${position.character}`;
    const cached = this.cache.get(key);
    if (cached) return [new vscode.InlineCompletionItem(cached)];

    let completion = '';
    await streamCompletion('http://localhost:8000/v1/completions/stream', { prefix, suffix, language: document.languageId }, token, (t) => {
      completion += t;
    });

    if (!completion.trim()) return [];
    this.cache.set(key, completion);
    return [new vscode.InlineCompletionItem(completion)];
  }
}
