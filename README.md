# MyCodex

Copilote local compose d un agent Python (planner/executor/critic avec memoire et optimisation de prompt) et d une extension VS Code pour piloter l agent directement depuis l editeur.

## Arborescence
- `agent/` : backend FastAPI/CLI qui orchestre planification, execution, critique et memoire.
- `vscode-extension/mycodex/` : extension VS Code qui ouvre un chat dedie et envoie les requetes a l agent (HTTP ou CLI).

## Pre-requis
- Python 3.11+ et pip.
- Node.js 18+ et npm pour l extension.
- Ollama lance sur la machine avec les modeles : `llama3.1:8b`, `codellama:13b`, `qwen2.5`, `gemma3:4b`.
  - Commandes rappel : `ollama serve` puis `ollama pull <modele>`.

## Mise en route rapide

### 1) Agent en mode API (recommande pour VS Code)
```bash
cd agent
pip install -r requirements.txt
ollama serve
ollama pull llama3.1:8b
ollama pull codellama:13b
ollama pull qwen2.5
ollama pull gemma3:4b
python main.py
```
- API FastAPI sur `http://0.0.0.0:5000`.
- Healthcheck `GET /health`.
- Endpoint principal `POST /api/run` avec corps :
```json
{ "goal": "...", "context": "...", "constraints": "", "use_memory": true }
```
- Pour desactiver l optimisation de prompt : `--disable-optimizer` ou `"optimize": false`.
- Pour couper la memoire : `--disable-memory` ou `"use_memory": false`.

### 2) Agent en mode CLI
```bash
python main.py --mode cli --goal "Ton objectif" --context "Contexte" --constraints "" --max-workers 2
```
- Meme flags `--disable-optimizer` et `--disable-memory` disponibles.

### 3) Optimiseur seul
```bash
python main.py --mode optimize --prompt "Ton prompt brut" --context "Contexte optionnel"
```

### 4) Extension VS Code
- Dossier `vscode-extension/mycodex`.
- Lancer le backend (API ou CLI) puis dans VS Code : Palette -> `MyCodex: Ouvrir le chat`.
- Reglages clefs :
  - `mycodex.transport` : `http` (defaut) ou `cli`.
  - `mycodex.apiBaseUrl` : exemple `http://localhost:5000/api/run`.
  - `mycodex.cliCommand` : `python main.py --goal "{query}" --context "{context}" --constraints "" --no-verbose`.
  - `mycodex.cliCwd` : chemin de travail pour la commande (detecte `agent/main.py` par defaut).
- Commandes npm (depuis `vscode-extension/mycodex`) : `npm run compile`, `npm run watch`, `npm test`.

## Ressources detaillees
- Architecture et options agent : `agent/README.md`.
- Guide extension : `vscode-extension/mycodex/README.md`.
