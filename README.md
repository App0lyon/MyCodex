# MyCodex

Copilote local compose d un agent Python (planner/executor/critic avec memoire, optimisation de prompt, recherche dans le workspace et provider NVIDIA Build optionnel) et d une extension VS Code pour piloter l agent directement depuis l editeur.

## Arborescence
- `agent/` : backend FastAPI/CLI qui orchestre planification, execution, critique et memoire.
- `vscode-extension/mycodex/` : extension VS Code qui ouvre un chat dedie et envoie les requetes a l agent (HTTP ou CLI).

## Pre-requis
- Python 3.11+ et pip.
- `uv` recommande pour gerer l'environnement Python du backend.
- Node.js 18+ et npm pour l extension.
- Ollama lance sur la machine avec les modeles : `llama3.1:8b`, `codellama:13b`, `qwen2.5`, `gemma3:4b`.
  - Commandes rappel : `ollama serve` puis `ollama pull <modele>`.

## Mise en route rapide

### 1) Agent en mode API (recommande pour VS Code)
```bash
cd agent
uv sync
uv run python main.py
```

Alternative `pip` :
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
{ "goal": "...", "context": "...", "constraints": "", "use_memory": true, "session_id": "chat-1", "workspace_root": "C:/mon-projet" }
```
- Route NVIDIA Build : `POST /api/run/nvidia` avec le meme payload. Definir `NVIDIA_BUILD_API_KEY` ou `--nvidia-api-key`.
  - Defaults NVIDIA choisis pour ce projet : `qwen/qwq-32b` (planning/review/reponse) et `qwen/qwen2.5-coder-7b-instruct` (generation/correction de code).
- Pour desactiver l optimisation de prompt : `--disable-optimizer` ou `"optimize": false`.
- Pour couper la memoire : `--disable-memory` ou `"use_memory": false`. Cote API, la memoire n'est activee que si `session_id` est fourni.
- Pour activer la recherche locale de fichiers, fournissez `workspace_root` ou utilisez l'extension VS Code depuis un workspace ouvert.

### 2) Agent en mode CLI
```bash
cd agent
uv run python main.py --mode cli --provider nvidia --goal "Ton objectif" --context "Contexte" --constraints "" --max-workers 2
```
- Meme flags `--disable-optimizer` et `--disable-memory` disponibles.

### 3) Optimiseur seul
```bash
cd agent
uv run python main.py --mode optimize --prompt "Ton prompt brut" --context "Contexte optionnel"
```

### 4) Tests backend avec uv
```bash
cd agent
uv run --group test pytest
```

### 5) Extension VS Code
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
