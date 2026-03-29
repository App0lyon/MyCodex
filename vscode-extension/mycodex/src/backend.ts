import * as cp from 'child_process';
import { existsSync } from 'fs';
import * as http from 'http';
import * as https from 'https';
import * as path from 'path';
import * as vscode from 'vscode';
import { Transport } from './types';

type ConversationTurn = { role: string; content: string };
export type Provider = 'ollama' | 'nvidia';
export type MemoryEntry = {
	id: string;
	goal: string;
	context: string;
	notes: string;
	response: string;
	conversation_id: string;
	timestamp: number;
};

export async function callBackend(
	prompt: string,
	context: string,
	history: ConversationTurn[] = [],
	sessionId?: string,
	enableSearch = false,
	enableOptimize = true,
	useMemory = true,
	provider: Provider = 'ollama'
): Promise<unknown> {
	const config = vscode.workspace.getConfiguration('mycodex');
	const transport = (config.get<string>('transport', 'http') as Transport) || 'http';
	const rawContext = (context || '').trim();
	const historyContext = buildHistoryContext(history);
	const combinedContext = [rawContext, historyContext ? `Historique:\n${historyContext}` : '']
		.filter(Boolean)
		.join('\n\n')
		.trim();
	const contextForTransport = transport === 'cli' ? combinedContext : rawContext;
	const workspaceRoot = detectWorkspaceRoot();

	if (transport === 'cli') {
		const cmdTemplate = config.get<string>(
			'cliCommand',
			'python main.py --goal "{query}" --context "{context}" --constraints "" --no-verbose'
		);
		const cwd = resolveCliCwd(config);
		const cmdParts = splitCommandLine(cmdTemplate);
		if (!cmdParts.length) {
			throw new Error('Commande CLI vide.');
		}
		const [command, ...templateArgs] = cmdParts;
		const resolvedParts = [command, ...templateArgs].map((part) =>
			part.split('{query}').join(prompt).split('{context}').join(contextForTransport)
		);
		const [resolvedCommand, ...args] = resolvedParts;
		if (enableSearch) {
			args.push('--enable-search');
		}
		if (!enableOptimize) {
			args.push('--disable-optimizer');
		}
		if (!useMemory) {
			args.push('--disable-memory');
		}
		if (provider === 'nvidia') {
			args.push('--provider', 'nvidia');
		}
		if (workspaceRoot) {
			args.push('--workspace-root', workspaceRoot);
			args.push('--apply-changes');
		}

		return new Promise<string>((resolve, reject) => {
			const proc = cp.spawn(resolvedCommand, args, { shell: false, cwd });
			let stdout = '';
			let stderr = '';

			proc.stdout.on('data', (data) => (stdout += data.toString()));
			proc.stderr.on('data', (data) => (stderr += data.toString()));
			proc.on('error', (err) => reject(err));
			proc.on('close', (code) => {
				if (code !== 0) {
					return reject(new Error(`CLI exited with code ${code}: ${stderr || stdout}`));
				}
				resolve(stdout.trim());
			});
		});
	}

	const baseUrl = deriveProviderRunUrl(
		config.get<string>('apiBaseUrl', 'http://localhost:5000/api/run'),
		provider
	);
	const payload: Record<string, unknown> = {
		goal: prompt,
		context: contextForTransport,
		constraints: '',
		provider,
		use_memory: useMemory,
		history,
		enable_search: enableSearch,
		optimize: enableOptimize,
	};
	if (sessionId) {
		payload.session_id = sessionId;
	}
	if (workspaceRoot) {
		payload.workspace_root = workspaceRoot;
		payload.apply_changes = true;
	}
	const httpResult = await postJsonWithLongTimeout(baseUrl, payload);
	if (httpResult.status < 200 || httpResult.status >= 300) {
		const detail = httpResult.body ? `: ${httpResult.body}` : '';
		throw new Error(`HTTP ${httpResult.status} ${httpResult.statusText}${detail}`);
	}

	const text = httpResult.body;
	try {
		return JSON.parse(text);
	} catch {
		return text;
	}
}

export async function fetchMemoryEntries(): Promise<MemoryEntry[]> {
	const config = vscode.workspace.getConfiguration('mycodex');
	const baseUrl = config.get<string>('apiBaseUrl', 'http://localhost:5000/api/run');
	const apiRoot = deriveApiRoot(baseUrl);
	const response = await fetch(`${apiRoot}/memory`, { method: 'GET' });
	if (!response.ok) {
		throw new Error(`HTTP ${response.status} ${response.statusText}`);
	}
	return (await response.json()) as MemoryEntry[];
}

export async function deleteMemoryEntry(entryId: string): Promise<void> {
	const config = vscode.workspace.getConfiguration('mycodex');
	const baseUrl = config.get<string>('apiBaseUrl', 'http://localhost:5000/api/run');
	const apiRoot = deriveApiRoot(baseUrl);
	const response = await fetch(`${apiRoot}/memory/${encodeURIComponent(entryId)}`, { method: 'DELETE' });
	if (!response.ok) {
		throw new Error(`HTTP ${response.status} ${response.statusText}`);
	}
}

function deriveApiRoot(runUrl: string): string {
	if (!runUrl) {
		return '';
	}
	const withoutTrailing = runUrl.endsWith('/') ? runUrl.slice(0, -1) : runUrl;
	// Remove the trailing /run if present
	if (withoutTrailing.toLowerCase().endsWith('/run')) {
		return withoutTrailing.slice(0, -4);
	}
	// If the URL already ends with /api, keep it; otherwise try to strip path to /api
	const apiIndex = withoutTrailing.toLowerCase().lastIndexOf('/api');
	if (apiIndex >= 0) {
		return withoutTrailing.slice(0, apiIndex + 4);
	}
	return withoutTrailing;
}

function deriveProviderRunUrl(runUrl: string, provider: Provider): string {
	const withoutTrailing = runUrl.endsWith('/') ? runUrl.slice(0, -1) : runUrl;
	if (provider !== 'nvidia') {
		if (withoutTrailing.toLowerCase().endsWith('/run/nvidia')) {
			return withoutTrailing.slice(0, -7);
		}
		return withoutTrailing;
	}
	if (withoutTrailing.toLowerCase().endsWith('/run/nvidia')) {
		return withoutTrailing;
	}
	if (withoutTrailing.toLowerCase().endsWith('/run')) {
		return `${withoutTrailing}/nvidia`;
	}
	return `${withoutTrailing}/nvidia`;
}

function splitCommandLine(commandLine: string): string[] {
	const parts: string[] = [];
	let current = '';
	let quote: '"' | "'" | '' = '';

	for (let index = 0; index < commandLine.length; index += 1) {
		const char = commandLine[index];
		if (quote) {
			if (char === quote) {
				quote = '';
				continue;
			}
			if (char === '\\' && quote === '"' && index + 1 < commandLine.length) {
				const next = commandLine[index + 1];
				if (next === '"' || next === '\\') {
					current += next;
					index += 1;
					continue;
				}
			}
			current += char;
			continue;
		}

		if (char === '"' || char === "'") {
			quote = char;
			continue;
		}

		if (/\s/.test(char)) {
			if (current) {
				parts.push(current);
				current = '';
			}
			continue;
		}

		current += char;
	}

	if (quote) {
		throw new Error('Commande CLI invalide: guillemet non ferme.');
	}
	if (current) {
		parts.push(current);
	}
	return parts;
}

function buildHistoryContext(history: ConversationTurn[]): string {
	if (!Array.isArray(history) || !history.length) {
		return '';
	}
	return history
		.slice(-12)
		.map((turn) => {
			const label = (turn.role || '').toLowerCase() === 'assistant' ? 'Assistant' : 'Utilisateur';
			const content = (turn.content || '').toString().trim();
			if (!content) {
				return '';
			}
			const compact = content.length > 600 ? content.slice(-600) : content;
			return `${label}: ${compact}`;
		})
		.filter(Boolean)
		.join('\n');
}

function detectAgentCwd(): string | undefined {
	const folders = vscode.workspace.workspaceFolders || [];
	for (const folder of folders) {
		const workspacePath = folder.uri.fsPath;
		const candidates = [
			path.join(workspacePath, 'agent', 'main.py'),
			path.join(workspacePath, '..', 'agent', 'main.py'),
			path.join(workspacePath, '..', '..', 'agent', 'main.py'),
		];

		for (const candidate of candidates) {
			if (existsSync(candidate)) {
				return path.dirname(candidate);
			}
		}
	}

	const builtInCandidate = path.join(__dirname, '..', '..', '..', 'agent', 'main.py');
	if (existsSync(builtInCandidate)) {
		return path.dirname(builtInCandidate);
	}

	return undefined;
}

function detectWorkspaceRoot(): string | undefined {
	return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || undefined;
}

function resolveCliCwd(config: vscode.WorkspaceConfiguration): string {
	const configured = (config.get<string>('cliCwd') || '').trim();
	if (configured) {
		return configured;
	}

	const guessed = detectAgentCwd();
	if (guessed) {
		return guessed;
	}

	const firstWorkspace = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
	return firstWorkspace || vscode.workspace.rootPath || process.cwd();
}

async function postJsonWithLongTimeout(
	runUrl: string,
	payload: Record<string, unknown>,
	timeoutMs = 600_000
): Promise<{ status: number; statusText: string; body: string }> {
	return new Promise((resolve, reject) => {
		let parsed: URL;
		try {
			parsed = new URL(runUrl);
		} catch (err) {
			reject(new Error(`URL invalide: ${runUrl}`));
			return;
		}

		const isHttps = parsed.protocol === 'https:';
		const data = Buffer.from(JSON.stringify(payload));
		const options: http.RequestOptions = {
			method: 'POST',
			hostname: parsed.hostname,
			port: parsed.port ? Number(parsed.port) : isHttps ? 443 : 80,
			path: `${parsed.pathname}${parsed.search}`,
			headers: {
				'Content-Type': 'application/json',
				'Content-Length': data.length,
			},
		};

		const req = (isHttps ? https : http).request(options, (res) => {
			const chunks: Buffer[] = [];
			res.on('data', (chunk) => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk))));
			res.on('end', () => {
				const body = Buffer.concat(chunks).toString('utf-8');
				resolve({
					status: res.statusCode || 0,
					statusText: res.statusMessage || '',
					body,
				});
			});
		});

		req.setTimeout(timeoutMs, () => {
			req.destroy(new Error(`Timeout apres ${timeoutMs}ms sans reponse`));
		});

		req.on('error', (err) => {
			const reason =
				err instanceof Error
					? [err.message, (err as any).code || (err as any).errno].filter(Boolean).join(' | ')
					: String(err);
			reject(new Error(`Appel /api/run echoue: ${reason || 'erreur inconnue'}`));
		});

		req.write(data);
		req.end();
	});
}
