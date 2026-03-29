Architecture
------------
- Prompt Optimizer (gemma3:4b) -> re-ecrit un prompt pour maximiser la qualite des reponses LLM.
- Planner (qwen2.5) -> genere une liste de sous-taches JSON.
- Task Queue -> ordonnance les taches en respectant les dependances.
- Executor (codellama:13b) -> implemente chaque tache.
- Task Reviewer (qwen2.5) -> relit chaque tache et remonte problemes/recommandations sur le code genere.
- Self-Correction (codellama:13b) -> applique automatiquement les recommandations du critic sur le code produit.
- Final Critic (qwen2.5) -> produit une revue globale apres generation.
- Memory module -> conserve un historique court/long terme des runs pour enrichir le contexte automatiquement.
- Workspace search -> indexe le workspace local, trouve des fichiers pertinents par nom/contenu et reinjecte ces extraits dans la planification et l'execution.
- Provider NVIDIA Build optionnel -> route dediee `/api/run/nvidia` basee sur les endpoints gratuits NVIDIA Build.
  - Modele general par defaut : `qwen/qwq-32b`
  - Modele code par defaut : `qwen/qwen2.5-coder-7b-instruct`

Pipeline optimise
-----------------
- Client Ollama unique partage par tous les agents.
- Execution parallele des taches sans dependances via un pool de threads (parametre max_workers).
- Revision par tache, puis critique initiale, passage de self-correction si des recommandations/problemes sont detectes, puis critique finale sur le code corrige.
- Serialisation des resultats en JSON structure (taches, execution, final_critic, non-resolus).
- Les corrections sont ignorees si elles ne fournissent pas de fichiers valides afin d'eviter d'ecraser un resultat existant par du vide.
- Contexte enrichi automatiquement par la memoire : les interactions recentes et pertinentes sont reinjectees dans les prompts; desactiveable via `--disable-memory` ou `use_memory: false`.
- Les taches dependantes recuperent maintenant les fichiers produits par leurs dependances au lieu de re-travailler uniquement le contexte brut.
- Si `workspace_root` est fourni, le planner et l'executor recoivent aussi une vue du workspace et des fichiers trouves par recherche locale.

Utilisation
-----------
1) Lancer Ollama en local (http://localhost:11434) avec les modeles necessaires.
2) Installer les deps backend :
   - recommande avec `uv` : `uv sync`
   - fallback pip : `pip install -r requirements.txt`
3) Mode FastAPI (recommande pour l'extension VS Code) :
   - `uv run python main.py` lance un serveur FastAPI sur `0.0.0.0:5000`.
   - Endpoint healthcheck : `GET /health`
   - Endpoint principal : `POST /api/run` avec un JSON `{ "goal": "...", "context": "...", "constraints": "...", "use_memory": true, "session_id": "chat-1", "workspace_root": "C:/mon-projet" }`.
   - Endpoint NVIDIA Build : `POST /api/run/nvidia` avec le meme payload. Necessite `NVIDIA_BUILD_API_KEY` ou `--nvidia-api-key`.
   - Endpoint prompt optimizer : `POST /api/optimize` avec `{ "prompt": "...", "context": "..." }`.
   - Endpoint optimizer NVIDIA : `POST /api/optimize/nvidia`.
   - L'optimisation de prompt est active par defaut sur `/api/run`; pour la desactiver passer `"optimize": false` ou lancer le serveur avec `--disable-optimizer` (desactive aussi `/api/optimize`).
   - La memoire est active par defaut seulement si `session_id` est fourni; pour la desactiver sur un appel, passer `"use_memory": false`.
   - Pour VS Code, passer `mycodex.transport` a `http` et `mycodex.apiBaseUrl` a `http://localhost:5000/api/run`.
4) Mode CLI (execution unique) :
   - `uv run python main.py --mode cli --goal "Ton objectif" --context "Contexte" --constraints "Contraintes" --max-workers 2`
   - L'optimisation de prompt est active par defaut; pour la desactiver ajouter `--disable-optimizer` (s'applique aussi aux modes API/optimize).
   - Le module de memoire est actif par defaut; pour le desactiver ajouter `--disable-memory`. Le chemin de persistance peut etre change avec `--memory-path`.
5) Mode optimize (prompt unique) :
   - `uv run python main.py --mode optimize --prompt "Ton prompt brut" --context "Contexte optionnel"`
6) Tests backend :
   - `uv run --group test pytest`
   - La suite couvre la lecture ciblee des fichiers workspace et l'application des patchs sur disque.

Parametres principaux
---------------------
- --mode : `api` (defaut) pour lancer FastAPI, `cli` pour une execution unique.
- --host / --port : bind HTTP du serveur FastAPI.
- --reload : rechargement auto de l'API (developpement uniquement).
- --goal : objectif global (requis en mode CLI).
- --context : contexte technique (optionnel).
- --constraints : contraintes supplementaires pour l'executor.
- --workspace-root : racine locale du projet a indexer pour la recherche de fichiers.
- --provider : `ollama` ou `nvidia` (utile en mode CLI).
- --nvidia-api-key : cle API NVIDIA Build. Alternativement, exporter `NVIDIA_BUILD_API_KEY`.
- --nvidia-general-model : modele NVIDIA pour planning/review/response.
- --nvidia-code-model : modele NVIDIA pour execution/self-correction.
- --ollama-url : URL Ollama (defaut http://localhost:11434).
- --planner-model / --executor-model / --critic-model : noms des modeles Ollama.
- --review-model : modele utilise pour la revision par tache (defaut critic-model).
- --self-correction-model : modele utilise pour appliquer les recommandations du critic (defaut executor-model).
- --max-workers : nombre de taches sans dependances traitees en parallele (defaut 2).
- --no-verbose : desactive les logs de progression (planification/execution/critique).

Ollama SetUp
------------
ollama serve

ollama pull llama3.1:8b
ollama pull codellama:13b
ollama pull qwen2.5
ollama pull gemma3:4b

ollama list
