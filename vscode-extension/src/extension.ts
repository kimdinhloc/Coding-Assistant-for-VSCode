import * as vscode from 'vscode';
import { CopilotStyleInlineProvider } from './provider';

export function activate(context: vscode.ExtensionContext) {
  const provider = new CopilotStyleInlineProvider();

  context.subscriptions.push(
    vscode.languages.registerInlineCompletionItemProvider({ pattern: '**' }, provider),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('autocomplete.triggerInline', async () => {
      await vscode.commands.executeCommand('editor.action.inlineSuggest.trigger');
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('autocomplete.acceptNextWord', async () => {
      await vscode.commands.executeCommand('editor.action.inlineSuggest.acceptNextWord');
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('autocomplete.acceptNextLine', async () => {
      await vscode.commands.executeCommand('editor.action.inlineSuggest.acceptNextLine');
    }),
  );
}

export function deactivate() {}
