import * as vscode from 'vscode';

export function buildHtml(webview: vscode.Webview): string {
	const nonce = getNonce();
	return String.raw/* html */ `
    <!DOCTYPE html>
    <html lang="fr">
      <meta http-equiv="Content-Security-Policy"
        content="
          default-src 'none';
          style-src 'unsafe-inline';
          script-src 'nonce-${nonce}' ${webview.cspSource};
        "
      />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <style>
          :root {
            color-scheme: dark;
            --bg: #0d1014;
            --bg-strong: #11161c;
            --panel: #11161c;
            --muted: #9499a1;
            --border: #2a313a;
            --accent: #0c9961;
            --glow: rgba(12, 153, 97, 0.2);
            --input: #0f141a;
            --card: linear-gradient(135deg, #11161c, #0f1318 50%, #0d1014 100%);
            --shadow: 0 25px 60px rgba(0, 0, 0, 0.35);
            --button: #1d92ff;
            --button-hover: #0f7adc;
            --error: #d94848;
          }
          * {
            box-sizing: border-box;
          }
          html, body {
            height: 100%;
          }
          body {
            margin: 0;
            font-family: "Segoe UI", "SF Pro Display", "Inter", system-ui, -apple-system, sans-serif;
            background:
              radial-gradient(120% 60% at 16% 20%, rgba(26, 102, 255, 0.18), transparent),
              radial-gradient(90% 55% at 82% 0%, rgba(12, 153, 97, 0.12), transparent),
              var(--bg);
            color: #eef1f6;
          }
          .surface {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            gap: 14px;
            padding: 18px 18px 16px;
          }
          .hero {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 14px;
            border-radius: 14px;
            padding: 16px;
            background: var(--card);
            border: 1px solid #1b2129;
            box-shadow: var(--shadow);
          }
          .hero-text {
            display: flex;
            flex-direction: column;
            gap: 6px;
          }
          .eyebrow {
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            font-size: 12px;
            color: var(--muted);
          }
          .hero-title {
            margin: 0;
            font-size: 20px;
            letter-spacing: 0.2px;
            color: #f7f9fc;
          }
          .subtitle {
            margin: 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.6;
            max-width: 520px;
          }
          .status-chip {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: #0d1117;
            font-size: 12px;
            letter-spacing: 0.2px;
            box-shadow: 0 6px 28px rgba(0, 0, 0, 0.35);
          }
          .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: var(--accent);
            box-shadow: 0 0 0 8px var(--glow);
            transition: background 0.1s ease, box-shadow 0.1s ease;
          }
          .status-dot[data-tone="busy"] {
            background: var(--button);
            box-shadow: 0 0 0 8px rgba(13, 112, 215, 0.2);
          }
          .status-dot[data-tone="error"] {
            background: var(--error);
            box-shadow: 0 0 0 8px rgba(217, 72, 72, 0.16);
          }
          .panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 12px;
            border: 1px solid #1b2129;
            border-radius: 16px;
            padding: 14px;
            background: var(--panel);
            box-shadow: var(--shadow);
          }
          .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
          }
          .panel-title {
            font-weight: 600;
            letter-spacing: 0.3px;
          }
          .panel-actions {
            display: flex;
            align-items: center;
            gap: 10px;
          }
          .ghost-btn {
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 8px 12px;
            background: #0f1318;
            color: #eef1f6;
            cursor: pointer;
            font-size: 12px;
            transition: border-color 0.15s ease, background 0.15s ease;
          }
          .ghost-btn:hover {
            border-color: #2f78ff;
            background: #111821;
          }
          .ghost-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }
          .toggle {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 10px;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: #0f1318;
            color: #eef1f6;
            cursor: pointer;
            user-select: none;
            font-size: 12px;
            transition: border-color 0.12s ease, background 0.12s ease;
          }
          .toggle:hover {
            border-color: #2f78ff;
            background: #111821;
          }
          .toggle input {
            display: none;
          }
          .toggle-slider {
            width: 32px;
            height: 18px;
            border-radius: 999px;
            background: #1f2730;
            position: relative;
            box-shadow: inset 0 0 0 1px #2a313a;
            transition: background 0.12s ease;
          }
          .toggle-slider::after {
            content: '';
            position: absolute;
            top: 3px;
            left: 3px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #c6cbd4;
            transition: transform 0.16s ease, background 0.12s ease;
          }
          .toggle input:checked + .toggle-slider {
            background: rgba(12, 153, 97, 0.35);
            box-shadow: inset 0 0 0 1px rgba(12, 153, 97, 0.5), 0 0 0 4px rgba(12, 153, 97, 0.12);
          }
          .toggle input:checked + .toggle-slider::after {
            transform: translateX(14px);
            background: #36b37e;
          }
          .toggle-label {
            font-weight: 600;
          }
          .feed {
            flex: 1;
            min-height: 220px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 4px 2px 6px 2px;
          }
          .placeholder {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 12px;
            align-items: center;
            padding: 14px 12px;
            border: 1px dashed var(--border);
            border-radius: 12px;
            color: var(--muted);
            background: #0d1117;
          }
          .placeholder-icon {
            width: 32px;
            height: 32px;
            border-radius: 12px;
            display: grid;
            place-items: center;
            background: #0f1318;
            border: 1px solid var(--border);
            color: #f7f9fc;
            font-weight: 600;
          }
          .bubble {
            border: 1px solid var(--border);
            background: #0f141a;
            border-radius: 14px;
            padding: 12px 12px 12px 14px;
            position: relative;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
          }
          .bubble::before {
            content: '';
            position: absolute;
            inset: 0 auto 0 0;
            width: 3px;
            border-radius: 14px 0 0 14px;
            background: #2f78ff;
          }
          .bubble.assistant::before {
            background: #36b37e;
          }
          .bubble.error::before {
            background: var(--error);
          }
          .bubble-text {
            margin: 0;
            color: #dfe3e9;
            line-height: 1.6;
            white-space: pre-wrap;
          }
          .composer {
            display: flex;
            flex-direction: column;
            gap: 8px;
            border-top: 1px solid var(--border);
            padding-top: 14px;
          }
          .composer-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            color: var(--muted);
            font-weight: 600;
          }
          .input-row {
            display: flex;
            align-items: stretch;
            gap: 10px;
          }
          textarea {
            flex: 1;
            resize: none;
            overflow-y: hidden;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: var(--input);
            color: #eef1f6;
            font-family: inherit;
            font-size: 14px;
            line-height: 1.5;
            padding: 10px 12px;
            min-height: 56px;
            max-height: 500px;
            outline: none;
            box-sizing: border-box;
            transition: height 0.1s ease;
          }
          textarea:focus {
            border-color: #2f78ff;
            box-shadow: 0 0 0 1px rgba(47, 120, 255, 0.45);
          }
          .primary-btn {
            border: none;
            border-radius: 10px;
            padding: 10px 16px;
            cursor: pointer;
            background: var(--button);
            color: #f8fbff;
            font-weight: 700;
            box-shadow: 0 10px 30px rgba(13, 112, 215, 0.35);
            transition: transform 0.12s ease, box-shadow 0.12s ease, background 0.12s ease;
          }
          .primary-btn:hover {
            background: var(--button-hover);
            transform: translateY(-1px);
            box-shadow: 0 12px 34px rgba(13, 112, 215, 0.45);
          }
          .primary-btn:active {
            transform: translateY(0);
          }
          .primary-btn:disabled {
            opacity: 0.7;
            cursor: progress;
          }
          .helpers {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            color: var(--muted);
            font-size: 12px;
          }
          .context-area {
            border: 1px dashed var(--border);
            border-radius: 12px;
            padding: 10px 12px;
            background: #0f1318;
            display: flex;
            flex-direction: column;
            gap: 8px;
          }
          .context-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
          }
          .context-sub {
            margin: 0;
            color: var(--muted);
            font-size: 12px;
          }
          .context-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
          }
          .context-empty {
            color: var(--muted);
            font-size: 12px;
          }
          .history {
            border: 1px solid #1b2129;
            border-radius: 12px;
            padding: 12px;
            background: #0f1318;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
            display: grid;
            gap: 10px;
          }
          .history-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
          }
          .history-title {
            font-weight: 600;
            letter-spacing: 0.2px;
          }
          .history-sub {
            color: var(--muted);
            font-size: 12px;
          }
          .history-list {
            display: grid;
            gap: 8px;
          }
          .history-list.scrollable {
            max-height: 280px;
            overflow-y: auto;
            padding-right: 4px;
          }
          .history-empty {
            color: var(--muted);
            font-size: 12px;
          }
          .history-item {
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px;
            background: #0f141a;
            display: grid;
            gap: 6px;
          }
          .history-meta {
            color: var(--muted);
            font-size: 12px;
          }
          .history-actions {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
          }
          .history-btn {
            border: 1px solid var(--border);
            background: #0f1318;
            color: #eef1f6;
            border-radius: 8px;
            padding: 6px 10px;
            cursor: pointer;
            font-size: 12px;
            transition: border-color 0.12s ease, background 0.12s ease;
          }
          .history-btn:hover {
            border-color: #2f78ff;
            background: #111821;
          }
          .chip {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 8px 10px;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: #0f141a;
            min-width: 0;
          }
          .chip-dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--button);
            flex-shrink: 0;
          }
          .chip-title {
            font-weight: 600;
            font-size: 12px;
            color: #eef1f6;
          }
          .chip-meta {
            color: var(--muted);
            font-size: 11px;
          }
          .chip-text {
            display: flex;
            flex-direction: column;
            gap: 2px;
            min-width: 0;
          }
          .chip-text span {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .chip-remove {
            margin-left: auto;
            border: none;
            background: none;
            color: var(--muted);
            cursor: pointer;
            font-size: 12px;
            padding: 4px 6px;
            border-radius: 8px;
            transition: color 0.12s ease, background 0.12s ease;
          }
          .chip-remove:hover {
            color: #f7f9fc;
            background: rgba(255, 255, 255, 0.05);
          }
          .md {
            color: #e9edf5;
            line-height: 1.6;
            display: grid;
            gap: 10px;
          }
          .md h1, .md h2, .md h3, .md h4 {
            margin: 0;
            color: #f8fbff;
            letter-spacing: 0.2px;
          }
          .md h1 { font-size: 18px; }
          .md h2 { font-size: 16px; }
          .md h3 { font-size: 14px; }
          .md p {
            margin: 0;
          }
          .md ul, .md ol {
            padding-left: 18px;
            margin: 0;
            display: grid;
            gap: 6px;
          }
          .md code {
            background: #0f141a;
            border: 1px solid #1f2730;
            border-radius: 6px;
            padding: 2px 6px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 12px;
          }
          .code-block {
            background: #0c1015;
            border: 1px solid #1f2730;
            border-radius: 10px;
            padding: 10px 12px;
            overflow-x: auto;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 12px;
            line-height: 1.5;
          }
          .run-card {
            display: grid;
            gap: 12px;
            padding: 12px;
            border: 1px solid #1f2730;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.02);
          }
          .run-header {
            display: flex;
            align-items: center;
            gap: 10px;
            justify-content: space-between;
            flex-wrap: wrap;
          }
          .run-goal {
            font-weight: 700;
            color: #f8fbff;
            margin: 0;
            font-size: 14px;
          }
          .pill {
            padding: 6px 10px;
            border-radius: 999px;
            border: 1px solid #1f2730;
            background: #0d1117;
            color: #c8ced8;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
          }
          .pill-dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--accent);
          }
          .task-list {
            display: grid;
            gap: 8px;
          }
          .task-card {
            border: 1px solid #1f2730;
            border-radius: 10px;
            padding: 10px;
            background: #0f1318;
            display: grid;
            gap: 6px;
          }
          .context-block {
            border: 1px dashed var(--border);
            border-radius: 10px;
            padding: 10px;
            background: #0d1117;
            color: #dfe3e9;
            font-size: 12px;
            white-space: pre-wrap;
          }
          .pill.secondary {
            background: rgba(255, 255, 255, 0.04);
            border-color: #1f2730;
            color: #c8ced8;
          }
          .task-title {
            margin: 0;
            color: #f1f5fb;
            font-weight: 600;
          }
          .task-status {
            color: var(--muted);
            font-size: 12px;
            margin: 0;
          }
          .task-output {
            background: #0c1015;
            border-radius: 8px;
            padding: 8px;
            border: 1px solid #1f2730;
            overflow-x: auto;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 12px;
            white-space: pre-wrap;
          }
          .monospace {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
          }
          ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
          }
          ::-webkit-scrollbar-thumb {
            background: #242b34;
            border-radius: 8px;
          }
        </style>
      </head>
      <body>
        <div class="surface">
          <header class="hero">
            <div class="hero-text">
              <p class="eyebrow">MYCODEX</p>
              <h1 class="hero-title">Assistant integré.</h1>
              <p class="subtitle">Interface pour discuter avec l'agent, envoyer du contexte et suivre les reponses.</p>
            </div>
            <div class="status-chip" id="statusChip">
              <span class="status-dot" id="statusDot" aria-hidden="true"></span>
              <span id="statusLine">Pret</span>
            </div>
          </header>

          <section class="panel">
            <div class="panel-header">
              <div class="panel-title">Fil de discussion</div>
              <div class="panel-actions">
                <label class="toggle" id="optimizeToggle" title="Activer l'optimisation de prompt">
                  <input type="checkbox" id="optimizeCheckbox" checked />
                  <span class="toggle-slider" aria-hidden="true"></span>
                  <span class="toggle-label">Optimisation</span>
                </label>
                <label class="toggle" id="searchToggle" title="Activer la recherche web">
                  <input type="checkbox" id="searchCheckbox" />
                  <span class="toggle-slider" aria-hidden="true"></span>
                  <span class="toggle-label">Recherche Web</span>
                </label>
                <button class="ghost-btn" id="addBtn" title="Nouvelle demande">Nouvelle demande</button>
                <button class="ghost-btn" id="fileBtn" title="Ajouter des fichiers au contexte">Ajouter des fichiers</button>
              </div>
            </div>

            <div class="context-area">
              <div class="context-header">
                <div>
                  <div class="composer-label">Contexte</div>
                  <p class="context-sub">Fichiers choisis et extrait d'editeur envoyes avec l'objectif.</p>
                </div>
                <div class="panel-actions">
                  <span class="context-sub" id="contextCount">Aucun element</span>
                </div>
              </div>
              <div class="context-list" id="contextList">
                <div class="context-empty">Aucun fichier ou extrait ajoute.</div>
              </div>
            </div>

            <div class="history">
              <div class="history-header">
                <div class="history-title">Historique des discussions</div>
                <div class="history-sub">Stockage local (panel uniquement)</div>
              </div>
              <div class="history-list" id="historyList">
                <div class="history-empty">Aucune discussion sauvegardee pour le moment.</div>
              </div>
            </div>

            <div class="feed" id="feed">
              <div class="placeholder">
                <div class="placeholder-icon">AI</div>
                <div class="placeholder-text">Aucune discussion pour le moment. Decris ton objectif ou colle un message d'erreur.</div>
              </div>
            </div>

            <div class="composer">
              <label for="prompt" class="composer-label">Objectif</label>
              <div class="input-row">
                <textarea id="prompt" placeholder="Decris ce que tu veux accomplir ou pose ta question"></textarea>
                <button id="send" class="primary-btn" title="Envoyer">Envoyer</button>
              </div>
              <div class="helpers">
                <span class="hint" id="helperHint">Entree pour envoyer - Maj+Entree pour une nouvelle ligne.</span>
              </div>
            </div>
          </section>
        </div>
        <script nonce="${nonce}">
          window.addEventListener('DOMContentLoaded', () => {
            const vscode = acquireVsCodeApi();
            const promptEl = document.getElementById('prompt');
            const sendBtn = document.getElementById('send');
            const feed = document.getElementById('feed');
            const statusLine = document.getElementById('statusLine');
            const fileBtn = document.getElementById('fileBtn');
            const addBtn = document.getElementById('addBtn');
            const contextList = document.getElementById('contextList');
            const statusDot = document.getElementById('statusDot');
            const contextCount = document.getElementById('contextCount');
            const historyList = document.getElementById('historyList');
            const searchCheckbox = document.getElementById('searchCheckbox');
            const optimizeCheckbox = document.getElementById('optimizeCheckbox');

            const state = {
              history: [],
              files: [],
              selectionContext: '',
              sending: false,
              sessions: [],
              currentSessionId: undefined,
              enableSearch: false,
              enableOptimize: true,
            };

            const MAX_HEIGHT = 500;

            const autoResize = (el) => {
              if (!el) return;

              el.style.height = 'auto';
              const newHeight = Math.min(el.scrollHeight, MAX_HEIGHT);
              el.style.height = newHeight + 'px';
              el.style.overflowY = el.scrollHeight > MAX_HEIGHT ? 'auto' : 'hidden';
            };

            const scheduleAutoResize = () => requestAnimationFrame(() => autoResize(promptEl));

            window.addEventListener('load', scheduleAutoResize);
            promptEl.addEventListener('input', scheduleAutoResize);
            promptEl.addEventListener('change', scheduleAutoResize);
            promptEl.addEventListener('paste', scheduleAutoResize);
            promptEl.addEventListener('focus', scheduleAutoResize);
            scheduleAutoResize();

            function setStatus(message, tone = 'idle') {
              statusLine.textContent = message;
              statusDot.dataset.tone = tone;
            }

            function toStoredMessages(messages) {
              return (messages || []).map((msg) => ({
                kind: msg?.kind || 'assistant',
                text: msg?.text || '',
              }));
            }

            function rebuildMessages(stored) {
              return (stored || []).map((msg) => {
                if ((msg?.kind || '').startsWith('assistant')) {
                  const payload = buildAssistantPayload(msg?.text || '');
                  return { kind: msg?.kind || 'assistant', text: payload.text, rich: payload.rich };
                }
                return { kind: msg?.kind || 'user', text: msg?.text || '' };
              });
            }

            function persistState() {
              try {
                vscode.setState({
                  sessions: (state.sessions || []).map((session) => ({
                    id: session.id,
                    title: session.title,
                    createdAt: session.createdAt,
                    messages: toStoredMessages(session.messages),
                  })),
                  currentSessionId: state.currentSessionId,
                  enableSearch: state.enableSearch,
                  enableOptimize: state.enableOptimize,
                });
              } catch {
                // Si setState n'est pas disponible, on ignore.
              }
            }

            function hydrateState() {
              try {
                const saved = vscode.getState ? vscode.getState() || {} : {};
                if (Array.isArray(saved.sessions)) {
                  state.sessions = saved.sessions.map((session) => ({
                    id: session.id || String(Date.now()),
                    title: session.title || 'Discussion',
                    createdAt: Number(session.createdAt) || Date.now(),
                    messages: Array.isArray(session.messages) ? session.messages : [],
                  }));
                }
                if (saved.currentSessionId) {
                  state.currentSessionId = saved.currentSessionId;
                }
                if (typeof saved.enableSearch === 'boolean') {
                  state.enableSearch = saved.enableSearch;
                }
                if (typeof saved.enableOptimize === 'boolean') {
                  state.enableOptimize = saved.enableOptimize;
                }
              } catch {
                // Pas de state persiste, on garde les valeurs par defaut.
              }
            }

            function formatData(data) {
              const text = (typeof data === 'string' ? data : JSON.stringify(data)) || '';
              try {
                return JSON.stringify(JSON.parse(text), null, 2);
              } catch {
                return text;
              }
            }

            function escapeHtml(text) {
              return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
            }

            function markdownToHtml(mdText) {
              const escaped = escapeHtml(mdText);

              const BT = String.fromCharCode(96);
              const FENCE = BT + BT + BT;

              const codeBlockPattern = new RegExp(FENCE + "(\\w+)?\\n([\\s\\S]*?)" + FENCE, "g");
              const inlineCodePattern = new RegExp(BT + "([^" + BT + "]+)" + BT, "g");

              let html = escaped
                .replace(new RegExp("^### (.*)$", "gm"), "<h3>$1</h3>")
                .replace(new RegExp("^## (.*)$", "gm"), "<h2>$1</h2>")
                .replace(new RegExp("^# (.*)$", "gm"), "<h1>$1</h1>");

              html = html.replace(codeBlockPattern, (_match, lang, code) => {
                const language = lang ? ' data-lang="' + lang + '"' : "";
                return '<pre class="code-block"' + language + ">" + code + "</pre>";
              });

              html = html.replace(inlineCodePattern, "<code>$1</code>");

              // Lists
              html = html.replace(new RegExp("^(?:- |\\* )(.*)$", "gm"), "<li>$1</li>");
              html = html.replace(new RegExp("(<li>.*</li>\\s*)+", "g"), (m) => "<ul>" + m + "</ul>");

              html = html.replace(new RegExp("\\n\\n+", "g"), "</p><p>");
              html = "<p>" + html + "</p>";
              return html;
            }

            function makeMarkdownElement(mdText) {
              const wrapper = document.createElement('div');
              wrapper.className = 'md';
              wrapper.innerHTML = markdownToHtml(mdText);
              return wrapper;
            }

            function tryParseJson(data) {
              if (typeof data === 'object') {
                return data;
              }
              if (typeof data !== 'string') {
                return undefined;
              }
              try {
                return JSON.parse(data);
              } catch {
                return undefined;
              }
            }

            function isRunResponse(obj) {
              return (
                obj &&
                typeof obj === 'object' &&
                'goal' in obj &&
                'context' in obj &&
                Array.isArray(obj.tasks)
              );
            }

            function renderTaskCard(task, kindLabel) {
              const card = document.createElement('div');
              card.className = 'task-card';

              const data = task && typeof task === 'object' ? task : {};
              const meta = data.task && typeof data.task === 'object' ? data.task : data;
              const execution = data.execution && typeof data.execution === 'object' ? data.execution : undefined;

              const title = document.createElement('p');
              title.className = 'task-title';
              const titleText = meta.title || meta.description || (meta.id ? 'Tache ' + meta.id : 'Tache');
              title.textContent = titleText + (kindLabel ? ' (' + kindLabel + ')' : '');
              card.appendChild(title);

              const status = document.createElement('p');
              status.className = 'task-status';
              const statusLabel =
                execution?.status ||
                data.status ||
                data.state ||
                (kindLabel === 'a suivre' ? 'en attente' : 'inconnu');
              status.textContent = 'Statut: ' + statusLabel;
              card.appendChild(status);

              const notesText = execution?.notes || data.notes || '';
              if (notesText) {
                const notes = document.createElement('p');
                notes.className = 'task-output';
                notes.textContent = notesText;
                card.appendChild(notes);
              }

              const review = execution?.review;
              if (review?.summary) {
                const summary = document.createElement('p');
                summary.className = 'task-output';
                summary.textContent = 'Review: ' + review.summary;
                card.appendChild(summary);
              }

              const files = Array.isArray(execution?.files) ? execution.files : [];
              if (files.length) {
                const filesBlock = document.createElement('div');
                filesBlock.className = 'task-output';
                filesBlock.textContent = 'Fichiers generes:';
                const list = document.createElement('ul');
                files.forEach((file) => {
                  const li = document.createElement('li');
                  li.textContent = shortenPath(file?.path || 'Fichier');
                  list.appendChild(li);
                });
                filesBlock.appendChild(list);
                card.appendChild(filesBlock);
              }

              if (!files.length && data.result) {
                const out = document.createElement('div');
                out.className = 'task-output';
                out.textContent = typeof data.result === 'string' ? data.result : JSON.stringify(data.result, null, 2);
                card.appendChild(out);
              }
              return card;
            }

            function renderRunResponse(run) {
              const wrap = document.createElement('div');
              wrap.className = 'run-card';

              const header = document.createElement('div');
              header.className = 'run-header';
              const goal = document.createElement('p');
              goal.className = 'run-goal';
              goal.textContent = run.goal || 'Objectif';
              header.appendChild(goal);

              const stats = document.createElement('div');
              stats.className = 'pill';
              const dot = document.createElement('span');
              dot.className = 'pill-dot';
              const label = document.createElement('span');
              label.textContent = 'Taches completees: ' + (run.completed_tasks ?? 0);
              stats.appendChild(dot);
              stats.appendChild(label);
              header.appendChild(stats);

              const memoryStatus = document.createElement('div');
              memoryStatus.className = 'pill secondary';
              const memDot = document.createElement('span');
              memDot.className = 'pill-dot';
              const memActive = Boolean(run._memoryActive);
              memDot.style.background = memActive ? 'var(--accent)' : '#6b7280';
              const memLabel = document.createElement('span');
              memLabel.textContent = memActive ? 'Memoire active' : 'Memoire inactive';
              memoryStatus.appendChild(memDot);
              memoryStatus.appendChild(memLabel);
              header.appendChild(memoryStatus);

              wrap.appendChild(header);

              if (run.response) {
                const answer = document.createElement('div');
                answer.className = 'md';
                answer.innerHTML = '<h3>Reponse</h3>' + markdownToHtml(run.response);
                wrap.appendChild(answer);
              }

              const taskList = document.createElement('div');
              taskList.className = 'task-list';
              (run.tasks || []).forEach((task) => taskList.appendChild(renderTaskCard(task, 'terminee')));
              (run.unresolved_tasks || []).forEach((task) => taskList.appendChild(renderTaskCard(task, 'a suivre')));

              if (taskList.childElementCount > 0) {
                wrap.appendChild(taskList);
              }

              if (run.context) {
                const ctx = document.createElement('div');
                ctx.className = 'code-block';
                ctx.textContent = run.context;
                wrap.appendChild(ctx);
              }

              if (run.context_used && run.context_used !== run.context) {
                const ctxUsed = document.createElement('div');
                ctxUsed.className = 'context-block';
                ctxUsed.textContent = "Contexte enrichi utilise:\n" + run.context_used;
                wrap.appendChild(ctxUsed);
              }

              if (run.memory_context) {
                const mem = document.createElement('div');
                mem.className = 'context-block';
                mem.textContent = "Extrait memoire reinjecte:\n" + run.memory_context;
                wrap.appendChild(mem);
              }

              return wrap;
            }

            function buildAssistantPayload(data) {
              const parsed = tryParseJson(data);
              if (isRunResponse(parsed)) {
                const memActive = Boolean(state.currentSessionId) || state.history.length > 1;
                const rich = renderRunResponse({ ...parsed, _memoryActive: memActive });
                return { text: JSON.stringify(parsed, null, 2), rich };
              }

              const text = formatData(data);
              const rich = makeMarkdownElement(text);
              return { text, rich };
            }

            function renderHistory() {
              feed.innerHTML = '';
              if (!state.history.length) {
                const placeholder = document.createElement('div');
                placeholder.className = 'placeholder';
                const icon = document.createElement('div');
                icon.className = 'placeholder-icon';
                icon.textContent = 'AI';
                const text = document.createElement('div');
                text.className = 'placeholder-text';
                text.textContent = "Aucune discussion pour le moment. Decris ton objectif ou colle un message d'erreur.";
                placeholder.appendChild(icon);
                placeholder.appendChild(text);
                feed.appendChild(placeholder);
                return;
              }

              state.history.forEach((entry) => {
                const card = document.createElement('article');
                card.className = 'bubble ' + entry.kind;
                if (entry.rich) {
                  card.appendChild(entry.rich);
                } else {
                  const text = document.createElement('p');
                  text.className = 'bubble-text monospace';
                  text.textContent = entry.text || '';
                  card.appendChild(text);
                }
                feed.appendChild(card);
              });
              feed.scrollTop = feed.scrollHeight;
            }

            function renderOptimizeToggle() {
              if (!optimizeCheckbox) return;
              optimizeCheckbox.checked = !!state.enableOptimize;
            }

            function renderSearchToggle() {
              if (!searchCheckbox) return;
              searchCheckbox.checked = !!state.enableSearch;
            }

            function shortenPath(filepath) {
              if (!filepath) return '';
              const parts = filepath.split(/[\/\\]/).filter(Boolean);
              if (parts.length <= 3) {
                return filepath;
              }
              return '.../' + parts.slice(-3).join('/');
            }

            function renderContext() {
              contextList.innerHTML = '';
              const hasSelection = Boolean((state.selectionContext || '').trim());
              const hasFiles = state.files && state.files.length > 0;
              const total = (hasSelection ? 1 : 0) + (hasFiles ? state.files.length : 0);
              contextCount.textContent = total ? total + ' element(s)' : 'Aucun element';

              if (!hasSelection && !hasFiles) {
                const empty = document.createElement('div');
                empty.className = 'context-empty';
                empty.textContent = 'Aucun fichier ou extrait ajoute.';
                contextList.appendChild(empty);
                return;
              }

              if (hasSelection) {
                const chip = document.createElement('div');
                chip.className = 'chip';
                const dot = document.createElement('span');
                dot.className = 'chip-dot';
                const text = document.createElement('div');
                text.className = 'chip-text';
                const title = document.createElement('span');
                title.className = 'chip-title';
                title.textContent = 'Extrait editeur';
                const meta = document.createElement('span');
                meta.className = 'chip-meta';
                const snippet = (state.selectionContext || '').trim();
                meta.textContent = snippet ? snippet.slice(0, 120) + (snippet.length > 120 ? '...' : '') : '';
                text.appendChild(title);
                text.appendChild(meta);
                chip.appendChild(dot);
                chip.appendChild(text);
                const remove = document.createElement('button');
                remove.className = 'chip-remove';
                remove.title = 'Retirer cet extrait';
                remove.textContent = 'x';
                remove.addEventListener('click', () => {
                  state.selectionContext = '';
                  renderContext();
                  setStatus('Extrait retire du contexte.');
                });
                chip.appendChild(remove);
                contextList.appendChild(chip);
              }

              if (hasFiles) {
                state.files.forEach((file, index) => {
                  const chip = document.createElement('div');
                  chip.className = 'chip';
                  const dot = document.createElement('span');
                  dot.className = 'chip-dot';
                  const text = document.createElement('div');
                  text.className = 'chip-text';
                  const title = document.createElement('span');
                  title.className = 'chip-title';
                  title.textContent = file.name || 'Fichier';
                  const meta = document.createElement('span');
                  meta.className = 'chip-meta';
                  meta.textContent = shortenPath(file.path || '');
                  text.appendChild(title);
                  text.appendChild(meta);
                  chip.appendChild(dot);
                  chip.appendChild(text);
                  const remove = document.createElement('button');
                  remove.className = 'chip-remove';
                  remove.title = 'Retirer ce fichier';
                  remove.textContent = 'x';
                  const key = file.path || file.name || String(index);
                  remove.addEventListener('click', () => {
                    state.files = (state.files || []).filter(
                      (candidate, idx) => (candidate.path || candidate.name || String(idx)) !== key
                    );
                    renderContext();
                    setStatus('Fichier retire du contexte.');
                  });
                  chip.appendChild(remove);
                  contextList.appendChild(chip);
                });
              }
            }

            function renderSessionList() {
              if (!historyList) return;
              historyList.innerHTML = '';
              const hasScroll = (state.sessions || []).length > 3;
              historyList.className = hasScroll ? 'history-list scrollable' : 'history-list';
              if (!state.sessions || !state.sessions.length) {
                const empty = document.createElement('div');
                empty.className = 'history-empty';
                empty.textContent = 'Aucune discussion sauvegardee pour le moment.';
                historyList.appendChild(empty);
                return;
              }

              state.sessions.forEach((session) => {
                const item = document.createElement('div');
                item.className = 'history-item';
                const title = document.createElement('div');
                title.className = 'chip-title';
                title.textContent = session.title || 'Discussion';
                const meta = document.createElement('div');
                meta.className = 'history-meta';
                const date = new Date(session.createdAt || Date.now());
                meta.textContent = date.toLocaleString('fr-FR') + ' • ' + (session.messages ? session.messages.length : 0) + ' message(s)';
                const actions = document.createElement('div');
                actions.className = 'history-actions';
                const restore = document.createElement('button');
                restore.className = 'history-btn';
                restore.textContent = 'Restaurer';
                restore.addEventListener('click', () => {
                  state.history = rebuildMessages(session.messages);
                  state.currentSessionId = session.id;
                  renderHistory();
                  persistState();
                  setStatus('Discussion restauree depuis l\'historique.');
                });
                const remove = document.createElement('button');
                remove.className = 'history-btn';
                remove.textContent = 'Supprimer';
                remove.addEventListener('click', () => deleteSession(session.id));
                actions.appendChild(restore);
                actions.appendChild(remove);
                item.appendChild(title);
                item.appendChild(meta);
                item.appendChild(actions);
                historyList.appendChild(item);
              });
            }

            function buildContextPayload() {
              const parts = [];
              const selection = (state.selectionContext || '').trim();
              if (selection) {
                parts.push("Context depuis l'editeur:\n" + selection);
              }
              (state.files || []).forEach((file) => {
                const content = typeof file.content === 'string' ? file.content : '';
                const label = file.path || file.name || 'fichier';
                parts.push('Fichier: ' + label + '\n' + content);
              });
              return parts.join('\n\n---\n\n').trim();
            }

            function buildConversationHistory() {
              const turns = [];
              (state.history || []).forEach((entry) => {
                const kind = (entry.kind || '').toLowerCase();
                if (!kind.startsWith('user') && !kind.startsWith('assistant')) {
                  return;
                }
                const role = kind.startsWith('user') ? 'user' : 'assistant';
                const content = (entry.text || '').toString().trim();
                if (!content) {
                  return;
                }
                const compact = content.length > 1200 ? content.slice(-1200) : content;
                turns.push({ role, content: compact });
              });
              return turns.slice(-12);
            }

            function mergeFiles(existing, incoming) {
              const byPath = new Map();
              (existing || []).forEach((file) => {
                if (file.path) {
                  byPath.set(file.path, file);
                } else if (file.name) {
                  byPath.set(file.name, file);
                }
              });
              (incoming || []).forEach((file) => {
                if (file.path) {
                  byPath.set(file.path, file);
                } else if (file.name) {
                  byPath.set(file.name, file);
                }
              });
              return Array.from(byPath.values());
            }

            function archiveCurrentDiscussion() {
              if (!state.history || !state.history.length) {
                return;
              }
              const firstUser = state.history.find((entry) => (entry.kind || '').startsWith('user'));
              const title = (firstUser?.text || 'Discussion').slice(0, 120);
              const messages = toStoredMessages(state.history);
              const sessionId = state.currentSessionId || 'session-' + Date.now();

              // Si on est sur une session restauree, on met a jour la session existante au lieu de dupliquer.
              const existingIndex = (state.sessions || []).findIndex((s) => s.id === sessionId);
              if (existingIndex >= 0) {
                const updated = { ...state.sessions[existingIndex], messages, title };
                const sessionsCopy = [...state.sessions];
                sessionsCopy.splice(existingIndex, 1);
                state.sessions = [updated, ...sessionsCopy].slice(0, 15);
                state.currentSessionId = sessionId;
                persistState();
                renderSessionList();
                return;
              }

              const session = {
                id: sessionId,
                title,
                createdAt: Date.now(),
                messages,
              };
              state.sessions = [session, ...(state.sessions || [])].slice(0, 15);
              state.currentSessionId = session.id;
              persistState();
              renderSessionList();
            }

            function deleteSession(sessionId) {
              vscode.postMessage({ type: 'deleteMemoryEntry', id: sessionId });
            }

            function handleFilesMessage(message) {
              if (!message) {
                setStatus('Impossible de traiter la selection de fichiers.', 'error');
                return;
              }

              if (!message.ok) {
                setStatus(String(message.data || 'Aucun fichier ajoute.'), 'error');
                return;
              }

              const files = Array.isArray(message.data) ? message.data : [];
              const skipped = typeof message.skipped === 'number' ? message.skipped : 0;
              state.files = mergeFiles(state.files, files);
              renderContext();

              const names = state.files.map((file) => file.name || file.path).filter(Boolean);
              const statusText = names.length
                ? 'Fichiers ajoutes: ' + names.join(', ')
                : 'Aucun fichier ajoute.';
              const skipText = skipped > 0 ? ' (' + skipped + ' hors workspace ignores)' : '';
              setStatus(statusText + skipText, 'idle');
            }

            function setLoading(isLoading) {
              state.sending = isLoading;
              sendBtn.disabled = isLoading;
              sendBtn.textContent = isLoading ? 'Envoi...' : 'Envoyer';
            }

            function sendPrompt() {
              if (state.sending) {
                return;
              }

              const prompt = (promptEl.value || '').trim();
              if (!prompt) {
                setStatus('Merci de saisir un objectif.');
                promptEl.focus();
                return;
              }

              if (!state.currentSessionId) {
                state.currentSessionId = 'session-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6);
                persistState();
              }

              const context = buildContextPayload();
              state.history.push({ kind: 'user', text: prompt });
              const history = buildConversationHistory();
              renderHistory();
              setLoading(true);
              setStatus('Envoi (memoire active)...', 'busy');

              vscode.postMessage({
                type: 'ask',
                prompt,
                context,
                history,
                sessionId: state.currentSessionId,
                enableSearch: !!state.enableSearch,
                enableOptimize: !!state.enableOptimize,
              });
              promptEl.value = '';
              autoResize(promptEl);
            }

            function handleResponseMessage(message) {
              setLoading(false);
              if (!message) {
                setStatus('Reponse vide ou inconnue.', 'error');
                state.history.push({ kind: 'assistant error', text: 'Reponse vide ou inconnue.' });
                renderHistory();
                return;
              }

              if (message.ok) {
                const { text, rich } = buildAssistantPayload(message.data);
                state.history.push({ kind: 'assistant', text, rich });
                renderHistory();
                setStatus('Reponse recue.', 'idle');
              } else {
                const errorText = String(message.data || 'Erreur inconnue.');
                state.history.push({ kind: 'assistant error', text: errorText });
                renderHistory();
                setStatus('Erreur pendant l\'appel.', 'error');
              }
            }

            sendBtn.addEventListener('click', sendPrompt);
            promptEl.addEventListener('keydown', (event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendPrompt();
              }
            });

            addBtn?.addEventListener('click', () => {
              archiveCurrentDiscussion();
              state.history = [];
              state.files = [];
              state.selectionContext = '';
              state.currentSessionId = undefined;
              renderHistory();
              renderContext();
              persistState();
              setStatus('Nouvelle demande prete.');
              promptEl.value = '';
              autoResize(promptEl);
            });

            optimizeCheckbox?.addEventListener('change', () => {
              state.enableOptimize = !!optimizeCheckbox.checked;
              persistState();
              setStatus(state.enableOptimize ? 'Optimisation activee.' : 'Optimisation desactivee.');
            });

            searchCheckbox?.addEventListener('change', () => {
              state.enableSearch = !!searchCheckbox.checked;
              persistState();
              setStatus(state.enableSearch ? 'Recherche web activee.' : 'Recherche web desactivee.');
            });

            fileBtn?.addEventListener('click', () => {
              setStatus('Choisissez des fichiers dans le workspace...');
              vscode.postMessage({ type: 'pickFiles' });
            });

            window.addEventListener('message', (event) => {
              const msg = event.data;
              if (!msg || !msg.type) {
                return;
              }

              if (msg.type === 'prefill') {
                if (msg.prompt) {
                  promptEl.value = msg.prompt;
                }
                if (msg.context) {
                  state.selectionContext = msg.context;
                }
                renderContext();
                requestAnimationFrame(() => {
                  autoResize(promptEl);
                  promptEl.focus();
                  promptEl.selectionStart = promptEl.selectionEnd = promptEl.value.length;
                });
                setStatus('Selection pre-remplie.');
                return;
              }

              if (msg.type === 'files') {
                handleFilesMessage(msg);
                return;
              }

              if (msg.type === 'history') {
                if (msg.ok && Array.isArray(msg.data)) {
                  const count = msg.data.length;
                  const sessions = msg.data.map((entry) => ({
                    id: String(entry.id || entry.timestamp || Date.now()),
                    title: entry.notes || entry.goal || 'Discussion',
                    createdAt: Number(entry.timestamp) ? Number(entry.timestamp) * 1000 : Date.now(),
                    messages: [
                      {
                        kind: 'assistant',
                        text: entry.response || entry.notes || '',
                      },
                    ],
                  }));
                  state.sessions = sessions;
                  renderSessionList();
                  setStatus(count ? 'Discussions chargees (' + count + ').' : 'Aucune discussion trouvee dans la memoire.');
                } else {
                  setStatus('Impossible de charger la memoire: ' + (msg.data || 'erreur'), 'error');
                }
                return;
              }

              if (msg.type === 'deleteMemoryEntry') {
                if (msg.ok) {
                  const sessionId = String(msg.id || '');
                  state.sessions = (state.sessions || []).filter((s) => String(s.id) !== sessionId);
                  if (state.currentSessionId === sessionId) {
                    state.currentSessionId = undefined;
                  }
                  renderSessionList();
                  persistState();
                  setStatus('Discussion supprimee.');
                } else {
                  setStatus('Suppression memoire echouee: ' + (msg.data || 'erreur'), 'error');
                }
                return;
              }

              if (msg.type === 'response') {
                handleResponseMessage(msg);
              }
            });

            hydrateState();
            vscode.postMessage({ type: 'loadHistory' });
            setStatus('Pret');
            renderHistory();
            renderContext();
            renderSessionList();
            renderOptimizeToggle();
            renderSearchToggle();
          });
        </script>
      </body>
    </html>
  `;
}

function getNonce(): string {
	const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
	let text = '';
	for (let i = 0; i < 16; i++) {
		text += possible.charAt(Math.floor(Math.random() * possible.length));
	}
	return text;
}
