# Advisor — Sélection automatique du modèle Claude

Ce dossier équipe le dépôt d'un **advisor** qui route chaque tâche vers le modèle Claude le mieux adapté, et de quatre sous-agents spécialisés — chacun figé sur un modèle précis.

## Les quatre voies de routage

| Sous-agent | Modèle | Pour quoi |
|---|---|---|
| `advisor` | Haiku 5.5 | Classe la demande, renvoie une recommandation. Ne fait pas le travail. |
| `deep-reasoner` | Opus 4.7 | Architecture, bugs de concurrence, sécurité, refactors lourds, specs floues. |
| `code-worker` | Sonnet 5.5 | Workhorse : features, bugs standards, tests, intégrations d'API, édits moyens. |
| `fast-scout` | Haiku 5.5 | Recherches, extractions, comptages, classifications, résumés courts. |
| `narrative-writer` | Fable 5.1 | Articles, portraits, reportages, prose longue en français travaillé. |

## Comment ça marche

Claude Code lit les fichiers `.claude/agents/*.md` au démarrage. Chaque fichier déclare un sous-agent avec, dans son frontmatter YAML :
- `name` : l'identifiant pour l'invoquer,
- `description` : la règle d'activation (lue par l'orchestrateur quand il décide de déléguer),
- `model` : le modèle Claude verrouillé pour ce sous-agent (`opus`, `sonnet`, `haiku`, `fable`),
- `tools` (optionnel) : la liste restreinte des outils autorisés.

L'orchestrateur principal (le Claude Code que vous pilotez) choisit d'invoquer un sous-agent quand le profil de la tâche correspond à sa `description`. Chaque invocation **tourne sur le modèle déclaré**, pas sur celui de la session principale.

## Deux manières d'utiliser l'advisor

### 1. Routage explicite — slash command

```
/advisor Rédige un portrait de Mujica, 1500 mots, style SAPERE
```

L'advisor renvoie :
```
## Recommandation du routeur
- Modèle : claude-fable-5-1
- Sous-agent suggéré : narrative-writer
- Confiance : haute
- Pourquoi : « rédige un portrait » + style SAPERE → plume narrative
- Alternative si échec : claude-sonnet-5-5
```

### 2. Routage automatique — par description d'agent

Vous dites simplement la tâche à Claude Code ; la `description` des sous-agents (notamment « Use PROACTIVELY » sur l'advisor) pousse l'orchestrateur à déléguer tout seul au bon modèle. Pas besoin de `/advisor` pour les cas évidents.

## Grille de décision rapide

- **Signaux Opus** : `architecte`, `audit`, `race condition`, `fuite`, `sécurité`, `refactor transversal`.
- **Signaux Sonnet** : `ajoute`, `implémente`, `corrige`, `écris les tests`, `intègre`.
- **Signaux Haiku** : `trouve`, `liste`, `combien`, `extrais`, `classe`.
- **Signaux Fable** : `article`, `rédige`, `portrait`, `récit`, `reportage`, `édito`, `SAPERE`, `blog`.

## Ce que l'advisor **ne fait pas**

- Il ne change pas le modèle de votre session principale (celle que vous pilotez). Seul `/model` le fait.
- Il ne peut pas bifurquer entre modèles au milieu d'un même tour.
- Il ne connaît pas l'état de votre portefeuille/quota — il recommande selon la tâche, pas selon la trésorerie en tokens.

## Modifier le dispositif

- **Ajouter un sous-agent** : créer `.claude/agents/<nom>.md` avec frontmatter `name/description/model/tools` et un corps d'instructions.
- **Déplacer un déclencheur** : éditer la section « Signaux lexicaux déclencheurs » dans `.claude/agents/advisor.md`.
- **Changer le modèle par défaut** d'un sous-agent : modifier la clé `model` de son frontmatter.
