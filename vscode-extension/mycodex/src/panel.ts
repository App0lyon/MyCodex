import * as vscode from 'vscode';
import { buildHtml } from './webview/html';
import { createMessageHandler } from './webview/messaging';

export class CodexPanel {
	public static currentPanel: CodexPanel | undefined;
	private readonly panel: vscode.WebviewPanel;
	private disposables: vscode.Disposable[] = [];

	private constructor(panel: vscode.WebviewPanel) {
		this.panel = panel;
		this.panel.webview.html = buildHtml(this.panel.webview);
		this.panel.webview.onDidReceiveMessage(createMessageHandler(this.panel.webview), null, this.disposables);

		this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
	}

	public static render(): CodexPanel {
		if (CodexPanel.currentPanel) {
			CodexPanel.currentPanel.panel.reveal(vscode.ViewColumn.Beside);
			return CodexPanel.currentPanel;
		}

		const panel = vscode.window.createWebviewPanel(
			'mycodexChat',
			'MyCodex Chat',
			vscode.ViewColumn.Beside,
			{
				enableScripts: true,
			}
		);

		CodexPanel.currentPanel = new CodexPanel(panel);
		return CodexPanel.currentPanel;
	}

	public sendPrompt(prompt: string, context: string) {
		this.panel.webview.postMessage({ type: 'prefill', prompt, context });
	}

	public dispose() {
		CodexPanel.currentPanel = undefined;

		this.panel.dispose();
		while (this.disposables.length) {
			const d = this.disposables.pop();
			if (d) {
				d.dispose();
			}
		}
	}
}
