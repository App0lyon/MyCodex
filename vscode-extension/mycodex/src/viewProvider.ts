import * as vscode from 'vscode';
import { buildHtml } from './webview/html';
import { createMessageHandler } from './webview/messaging';

export class CodexViewProvider implements vscode.WebviewViewProvider {

	resolveWebviewView(webviewView: vscode.WebviewView): void {
		webviewView.webview.options = { enableScripts: true };
		webviewView.webview.html = buildHtml(webviewView.webview);
		webviewView.webview.onDidReceiveMessage(createMessageHandler(webviewView.webview));
	}
}
