import * as path from 'path';
import * as vscode from 'vscode';

export function isUriInsideWorkspace(uri: vscode.Uri): boolean {
	// VS Code resolves this correctly for most schemes; fall back to a path check for edge cases.
	if (vscode.workspace.getWorkspaceFolder(uri)) {
		return true;
	}

	const folders = vscode.workspace.workspaceFolders || [];
	if (!folders.length) {
		return false;
	}

	const target = path.resolve(uri.fsPath);
	return folders.some((folder) => {
		const base = path.resolve(folder.uri.fsPath);
		if (target === base) {
			return true;
		}
		const normalizedBase = base.endsWith(path.sep) ? base : base + path.sep;
		return target.startsWith(normalizedBase);
	});
}
