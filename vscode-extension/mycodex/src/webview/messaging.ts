import * as path from 'path';
import * as vscode from 'vscode';
import { callBackend } from '../backend';
import { isUriInsideWorkspace } from '../utils/workspace';

export function createMessageHandler(webview: vscode.Webview) {
	return async (message: any) => {
		if (message?.type === 'ask') {
			const prompt = String(message.prompt ?? '');
			const context = String(message.context ?? '');
			const history = Array.isArray(message.history) ? message.history : [];
			const sessionId = message.sessionId ? String(message.sessionId) : undefined;
			const enableSearch = Boolean(message.enableSearch);
			const enableOptimize = message.enableOptimize !== false;
			const useMemory = message.useMemory !== false;
			const provider = message.provider === 'nvidia' ? 'nvidia' : 'ollama';
			if (!prompt.trim()) {
				webview.postMessage({ type: 'response', ok: false, data: 'Le prompt est vide.' });
				return;
			}

			try {
				const result = await callBackend(prompt, context, history, sessionId, enableSearch, enableOptimize, useMemory, provider);
				webview.postMessage({ type: 'response', ok: true, data: result });
			} catch (err: unknown) {
				const msg = err instanceof Error ? err.message : 'Erreur inconnue.';
				webview.postMessage({ type: 'response', ok: false, data: msg });
			}
			return;
		}

		if (message?.type === 'pickFiles') {
			try {
				const workspaceFolders = vscode.workspace.workspaceFolders;

				// Workspace racine (support multi-root). Si aucun workspace, VS Code ouvre un selecteur generique.
				const selectedFolder =
					workspaceFolders && workspaceFolders.length
						? workspaceFolders.length === 1
							? workspaceFolders[0]
							: await vscode.window.showWorkspaceFolderPick({
									placeHolder: 'Choisissez le workspace source',
							  })
						: undefined;

				const uris = await vscode.window.showOpenDialog({
					title: 'Ajouter des fichiers au contexte',
					defaultUri: selectedFolder?.uri,
					canSelectFiles: true,
					canSelectFolders: false,
					canSelectMany: true,
					openLabel: 'Ajouter au contexte',
				});

				if (!uris || !uris.length) {
					webview.postMessage({
						type: 'files',
						ok: false,
						data: 'Aucun fichier selectionne.',
					});
					return;
				}

				const decoder = new TextDecoder();
				const files: Array<{ path: string; name: string; content: string }> = [];
				const allowedUris =
					workspaceFolders && workspaceFolders.length ? uris.filter(isUriInsideWorkspace) : uris;
				const skipped =
					workspaceFolders && workspaceFolders.length ? uris.length - allowedUris.length : 0;

				if (!allowedUris.length) {
					webview.postMessage({
						type: 'files',
						ok: false,
						data: 'Les fichiers doivent etre dans le workspace ouvert.',
					});
					return;
				}

				for (const uri of allowedUris) {
					try {
						const content = decoder.decode(await vscode.workspace.fs.readFile(uri));
						files.push({
							path: uri.fsPath,
							name: path.basename(uri.fsPath),
							content,
						});
					} catch (err) {
						files.push({
							path: uri.fsPath,
							name: path.basename(uri.fsPath),
							content: 'Erreur de lecture du fichier.',
						});
					}
				}

				webview.postMessage({
					type: 'files',
					ok: true,
					data: files,
					skipped,
				});
			} catch (err: unknown) {
				webview.postMessage({
					type: 'files',
					ok: false,
					data: err instanceof Error ? err.message : 'Erreur inconnue.',
				});
			}
		}
	};
}
