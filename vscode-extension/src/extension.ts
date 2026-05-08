import * as vscode from 'vscode';
import { CopilotStyleInlineProvider } from './provider';

export function activate(context: vscode.ExtensionContext) {
  const provider = new CopilotStyleInlineProvider();
  context.subscriptions.push(
    vscode.languages.registerInlineCompletionItemProvider({ pattern: '**' }, provider),
  );
}

export function deactivate() {}
