# MyCodex (VS Code)

Extension VS Code qui ouvre un chat dedie pour piloter l agent Python (planner / executor / critic). Par defaut, elle appelle l API HTTP FastAPI (`POST /api/run`), et peut basculer en mode CLI si besoin.

## Fonctionnalites
- Commande `MyCodex: Ouvrir le chat` : panel chat avec prompt + contexte.
- Commande `MyCodex: Envoyer la selection` : envoie la selection courante (ou la ligne active) et un extrait de contexte autour.
- Vue laterale (icones MyCodex) : chat accessible en permanence sans panel separe.
- Transport HTTP par defaut (`POST /api/run`), CLI disponible en option (`python main.py ... --no-verbose`).
- Affichage des reponses en texte brut/JSON (non interprete).
- Toggle memoire directement dans le chat (on/off) avec affichage du contexte memoire reinjecte par l'agent.

## Configuration
`Fichier > Preferences > Parametres > Extensions > MyCodex`
- `mycodex.transport` (`http` par defaut | `cli`) : mode d appel.
- `mycodex.apiBaseUrl` : endpoint POST (corps par defaut `{ goal, context, constraints: "" }`). Exemple : `http://localhost:5000/api/run`.
- `mycodex.cliCommand` : commande shell avec placeholders `{query}` et `{context}`. Par defaut : `python main.py --goal "{query}" --context "{context}" --constraints "" --no-verbose`.
- `mycodex.cliCwd` : repertoire de travail pour la commande (vide = detection auto: `agent/main.py` puis workspace).
- `mycodex.contextMaxLines` : lignes max de contexte recuperees autour du curseur pour la commande "Envoyer la selection".
- Toggle memoire (dans le panel) : envoie `use_memory: true/false` a l'API, ou ajoute `--disable-memory` en mode CLI.

## Flux recommande
1) Lancer le service FastAPI de l agent (`python agent/main.py` lance `POST /api/run` sur `http://localhost:5000`). Ou, en secours, preparer la commande CLI (`python main.py --mode cli ...`).
2) VS Code -> Command Palette -> `MyCodex: Ouvrir le chat`.
3) Entrer un objectif dans le champ prompt, ajouter du contexte si besoin, cliquer "Envoyer".
4) Pour un snippet, selectionner du code puis `MyCodex: Envoyer la selection`.

## API attendue (HTTP)
- Methode : `POST` sur `mycodex.apiBaseUrl`
- Corps par defaut :
```json
{
  "goal": "string",
  "context": "string",
  "constraints": ""
}
```
- Reponse : texte ou JSON (affiche tel quel dans le panel).

## Developpement
- Build : `npm run compile`
- Watch : `npm run watch`
- Tests : `npm test`

## Notes
- Pas de streaming : le backend doit renvoyer un texte/JSON complet.
- En mode CLI, la sortie standard est affichee. Code de sortie != 0 = erreur. 
