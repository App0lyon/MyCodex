import * as vscode from 'vscode';

export function getContextFromEditor(editor: vscode.TextEditor): string {
	const maxLines = vscode.workspace.getConfiguration('mycodex').get<number>('contextMaxLines', 40);
	const startLine = Math.max(0, editor.selection.active.line - Math.floor(maxLines / 2));
	const endLine = Math.min(editor.document.lineCount - 1, startLine + maxLines);
	const range = new vscode.Range(startLine, 0, endLine, editor.document.lineAt(endLine).text.length);
	return editor.document.getText(range);
}
