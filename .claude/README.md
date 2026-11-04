# Advisor — Sélection automatique du modèle Claude

Ce dossier équipe le dépôt d'un dispositif de routage qui envoie chaque tâche vers le modèle Claude le mieux adapté. Il fonctionne à trois étages, du plus automatique au plus explicite.

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│  Prompt utilisateur                                           │
│    │                                                          │
│    ▼                                                          │
│  Hook UserPromptSubmit (.claude/hooks/route-skill.py)         │  ← ÉTAGE 1 : automatique
│    ├─ Repère les /skill-name dans le prompt                   │
│    ├─ Consulte .claude/skill-routing.json                     │
│    └─ Injecte un bloc <advisor-routing>...</advisor-routing>  │
│       dans le contexte, AVANT que Claude ne réponde           │
│                                                               │
│  ─────────────────────────────────────────────────────────    │
│                                                               │
│  Orchestrateur (ta session principale)                        │
│    ├─ Voit la décision injectée                               │
│    └─ Délègue à l'agent recommandé                            │
│                                                               │
│  ─────────────────────────────────────────────────────────    │
│                                                               │
│  Sous-agent spécialisé (Agent tool)                           │  ← ÉTAGE 2 : délégation
│    ├─ advisor         → Haiku 5.5                             │
│    ├─ fast-scout      → Haiku 5.5                             │
│    ├─ code-worker     → Sonnet 5.5                            │
│    ├─ deep-reasoner   → Opus 4.7                              │
│    └─ narrative-writer→ Fable 5.1                             │
│                                                               │
│  ─────────────────────────────────────────────────────────    │
│                                                               │
│  Slash command /advisor <tâche>                               │  ← ÉTAGE 3 : explicite
│    └─ Pour forcer une décision quand aucun /skill n'est cité  │
└───────────────────────────────────────────────────────────────┘
```

## Les fichiers

| Fichier | Rôle |
|---|---|
| `.claude/skill-routing.json` | **Table de routage** : `routes` (correspondances exactes) + `patterns` (regex fallback) + `default`. Modifier ce fichier seul suffit à changer le routage. |
| `.claude/hooks/route-skill.py` | **Hook** Python exécuté à chaque `UserPromptSubmit`. Lit le prompt, repère `/skill-name`, consulte la table, injecte un bloc `<advisor-routing>`. Jamais bloquant. |
| `.claude/settings.json` | Enregistre le hook auprès de Claude Code. |
| `.claude/agents/advisor.md` | Routeur léger (Haiku) pour les cas non-couverts par le hook. |
| `.claude/agents/deep-reasoner.md` | Opus 4.7 — architecture, concurrence, sécurité, refactors transversaux. |
| `.claude/agents/code-worker.md` | Sonnet 5.5 — workhorse code courant. |
| `.claude/agents/fast-scout.md` | Haiku 5.5 — recherches, extractions, classifications. |
| `.claude/agents/narrative-writer.md` | Fable 5.1 — prose longue, style SAPERE. |
| `.claude/commands/advisor.md` | Slash command `/advisor <tâche>` pour un routage explicite. |

## Ce que fait le hook, étape par étape

1. Claude Code vous passe le prompt via stdin au format JSON (`{"prompt": "...", "cwd": "...", ...}`).
2. Le script extrait les occurrences de `/<name>` avec une regex prudente (ignore les URLs, les chemins système `/tmp`, `/etc`...).
3. Pour chaque skill, il cherche dans l'ordre :
   - `routes[<skill>]` → correspondance exacte,
   - `patterns[].match` → premier pattern regex qui matche,
   - `default` → sinon rien d'injecté (fallback silencieux).
4. Il émet sur stdout un bloc `<advisor-routing>` listant `skill → agent (modèle) — pourquoi`.
5. Claude Code intègre ce bloc dans le contexte comme s'il faisait partie du prompt, **avant** de commencer à répondre.

Résultat : vous tapez `/anthropic-skills:article-histoire-sapere sur la Commune`, et avant même que l'orchestrateur ne lise la skill, il sait qu'il doit déléguer à `narrative-writer` (Fable).

## Modifier le routage

### Ajouter une skill connue
Éditer `.claude/skill-routing.json` et ajouter une entrée dans `routes` :
```json
"ma-nouvelle-skill": {
  "model": "opus",
  "agent": "deep-reasoner",
  "why": "Raisonnement multi-étapes"
}
```

### Ajouter une règle par motif
Dans `patterns` (ordonné : premier match gagne) :
```json
{ "match": "^legal:(review|compliance)", "model": "opus", "agent": "deep-reasoner" }
```

### Changer le défaut
Modifier la section `default` du JSON. C'est ce qui s'applique quand une skill est absente *et* qu'aucun pattern ne matche.

### Ajouter un sous-agent
Créer `.claude/agents/<nom>.md` avec frontmatter `name/description/model/tools`. Le `description` est ce qui pousse l'orchestrateur à déléguer tout seul quand la demande colle. Référencer ensuite ce nouvel agent dans `skill-routing.json`.

## Les quatre modèles — grille mnémotechnique

| Déclencheur dans la demande | Modèle | Agent |
|---|---|---|
| `architecte`, `audit`, `race condition`, `sécurité`, `refactor transversal`, skill d'analyse multi-sources | Opus 4.7 | `deep-reasoner` |
| `ajoute`, `implémente`, `corrige`, `écris les tests`, `intègre`, skill small-business / data standard | Sonnet 5.5 | `code-worker` |
| `trouve`, `liste`, `combien`, `extrais`, `classe`, `résume en 3 lignes` | Haiku 5.5 | `fast-scout` |
| `article`, `rédige`, `portrait`, `récit`, `reportage`, `édito`, skill SAPERE éditoriale, blog | Fable 5.1 | `narrative-writer` |

## Tests rapides

```bash
# Vérifier que le JSON est valide
python3 -c "import json; json.load(open('.claude/skill-routing.json'))"

# Simuler le hook avec un prompt
echo '{"prompt":"lance /anthropic-skills:article-histoire-sapere","cwd":"'"$PWD"'"}' \
  | python3 .claude/hooks/route-skill.py

# Lister toutes les routes définies
jq '.routes | keys' .claude/skill-routing.json
```

## Limites honnêtes

- **Le hook n'exécute rien lui-même.** Il injecte une décision ; c'est l'orchestrateur qui doit effectivement déléguer via l'outil `Agent`. Si une skill est conçue pour s'exécuter directement sur la session principale, l'injection ne forcera pas le changement de modèle de cette session (Claude Code ne permet pas de switcher mid-tour). Dans ce cas, le gain est seulement conscientisant : vous saurez que la skill *aurait dû* tourner ailleurs.
- **Détection par pattern ≠ détection sémantique.** Un prompt comme « *inspire-toi du style de l'article-histoire-sapere* » ne déclenchera pas le hook (pas de `/`). Pour ces cas, invoquez `/advisor` explicitement.
- **Le quota tokens n'est pas pris en compte.** La table recommande par profil de tâche, pas selon votre budget.
