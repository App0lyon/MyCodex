PLANNER = """
Objectif global :
{{GOAL}}

Contexte technique (si disponible) :
{{CONTEXT}}

Contraintes supplementaires (si disponibles) :
{{CONSTRAINTS}}

Genere une liste ordonnee de sous-taches necessaires pour atteindre l'objectif.
Base la decomposition sur le contexte et les contraintes lorsqu'ils apportent des precisions sur le perimetre ou les dependances.
Si l'objectif peut etre resolu par UNE fonction, genere EXACTEMENT UNE tache.

Chaque tache doit contenir :
- id (int)
- title (string)
- description (string)
- input (ce que la tache consomme)
- output (ce qu'elle produit)
- dependencies (liste d'ids)

Renvoie uniquement le format JSON STRICT.
"""


EXECUTOR = """
Tache a executer :
{{TASK_JSON}}

Contexte du projet :
{{PROJECT_CONTEXT}}

Code existant (si applicable) :
{{EXISTING_CODE}}

Contraintes supplementaires :
{{CONSTRAINTS}}

Instructions :
- Implemente la tache.
- Si "Code existant" est fourni, conserve tout le code non concerne intact, modifie uniquement ce qui est demande et reutilise le meme chemin de fichier.
- Si du code est requis, fournis-le dans `files` avec le contenu COMPLET des fichiers.
- Si aucun fichier n'est fourni, la reponse sera consideree comme un ECHEC.
- Si aucun code n'est requis, indique-le clairement dans `notes` et retourne `status: failure`.

FORMAT DE SORTIE OBLIGATOIRE (JSON STRICT) :

{
  "status": "success | failure",
  "files": [
    {
      "path": "chemin/fichier.ext",
      "content": "code complet ici"
    }
  ],
  "notes": "breve description"
}

N'inclus RIEN d'autre que cet objet JSON.
"""


TASK_REVIEW = """
Tache :
{{TASK_JSON}}

Contexte :
{{CONTEXT}}

Contraintes :
{{CONSTRAINTS}}

Resultat de la tache (status, notes, fichiers) :
{{EXECUTION_JSON}}

Code fourni :
{{CODE_BLOCKS}}

Produis une revision rapide du code genere/modifie pour cette tache.
Format JSON STRICT uniquement :
{
  "summary": "bref resume",
  "problems": [],
  "recommendations": []
}
"""


CRITIC = """
Objectif global :
{{GOAL}}

Contexte :
{{CONTEXT}}

Contraintes :
{{CONSTRAINTS}}

Taches executees :
{{TASK_RESULTS}}

Taches non resolues :
{{UNRESOLVED_TASKS}}

Critique precedente (si disponible) :
{{BASELINE_FEEDBACK}}

Fournis une critique FINALE (une seule fois) sur l'ensemble du resultat genere.
Donne un score global sur 100, la liste des problemes observes et des recommandations concretes.

Format de sortie STRICT (JSON uniquement) :
{
  "score": 0-100,
  "problems": [],
  "recommendations": []
}
"""


EXECUTOR_SELF_CORRECTION = """
Tache a corriger :
{{TASK_JSON}}

Etat actuel du code (status, notes, fichiers) :
{{CURRENT_CODE}}

Feedback du critique :
{{CRITIC_FEEDBACK}}

Instructions :
- Applique les recommandations du critique pour ameliorer le code fourni.
- Conserve les chemins de fichiers existants si pertinents.
- Fournis le contenu COMPLET de chaque fichier modifie dans `files`.
- Sortie JSON STRICT uniquement, aucune explication hors JSON.
- Ne marque jamais `success` si `files` est vide ou manquant.
- Si tu ne peux pas corriger, retourne `status: failure` avec une note concise.

FORMAT DE SORTIE OBLIGATOIRE (JSON STRICT) :
{
  "status": "success | failure",
  "files": [
    {
      "path": "chemin/fichier.ext",
      "content": "code complet ici"
    }
  ],
  "notes": "breve description"
}

N'inclus RIEN d'autre que cet objet JSON.
"""


OPTIMIZER = """
Prompt d'origine :
{{PROMPT}}

Contexte (optionnel) :
{{CONTEXT}}

Re-ecris ce prompt pour obtenir une reponse LLM de haute qualite :
- Clarifie le role et les attentes.
- Indique le format de sortie attendu (JSON, bullet points, etc.) si pertinent.
- Reste cible sur l'intention initiale sans ajouter de hors-sujet.
- Inclue les contraintes et definitions importantes pour reduire l'ambiguite.

Retourne uniquement le prompt optimise, sans balises ni explications.
"""


RESPONDER = """
Objectif :
{{GOAL}}

Evaluation finale (score, problemes, recommandations) :
{{FINAL_CRITIC}}

Resultats de taches (JSON) :
{{TASK_RESULTS}}

Taches non resolues (JSON) :
{{UNRESOLVED_TASKS}}

Genere un Markdown court et esthetique qui sert de reponse finale a l'utilisateur :
- Titre principal rappelant l'objectif.
- Section "Progression" listant chaque tache avec son statut (success/failure) et une note courte.
- Section "Bloquages" pour les taches non resolues si la liste n'est pas vide.
- Section "Code" listant chaque fichier genere/modifie : affiche le chemin du fichier puis un bloc code avec son contenu complet.
- Section "Recommandations" listant uniquement les recommandations clefs (pas de titre "Critique finale").
- Termine par 2 a 3 prochaines etapes si elles sont pertinentes, sinon omets la section.
"""
