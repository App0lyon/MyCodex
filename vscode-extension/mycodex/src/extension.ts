import * as vscode from 'vscode';
import { CodexPanel } from './panel';
import { getContextFromEditor } from './utils/context';
import { CodexViewProvider } from './viewProvider';

export function activate(context: vscode.ExtensionContext) {
	const openChat = vscode.commands.registerCommand('mycodex.openChat', () => {
		CodexPanel.render();
	});

	const askSelection = vscode.commands.registerCommand('mycodex.askSelection', async () => {
		const editor = vscode.window.activeTextEditor;
		if (!editor) {
			return vscode.window.showWarningMessage('Aucun editeur actif.');
		}
		const selection =
			editor.document.getText(editor.selection) || editor.document.lineAt(editor.selection.active.line).text;
		if (!selection.trim()) {
			return vscode.window.showWarningMessage('La selection est vide.');
		}
		const panel = CodexPanel.render();
		panel?.sendPrompt(selection, getContextFromEditor(editor));
	});

	const chatViewProvider = new CodexViewProvider();
	context.subscriptions.push(
		openChat,
		askSelection,
		vscode.window.registerWebviewViewProvider('mycodex.chatView', chatViewProvider)
	);
}

export function deactivate() {}
