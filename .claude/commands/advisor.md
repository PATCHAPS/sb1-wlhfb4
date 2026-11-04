---
description: Route the current task to the right Claude model. Invoke before heavy work with a short description of what you're about to do; the advisor returns a model recommendation (Opus / Sonnet / Haiku / Fable) and the matching specialist agent.
argument-hint: "<description de la tâche à mener>"
---

Invoque l'agent `advisor` avec la description de tâche suivante :

$ARGUMENTS

L'advisor doit :
1. Classer la tâche selon sa grille (raisonnement profond / code courant / scout rapide / rédaction narrative).
2. Renvoyer le **modèle recommandé** et le **sous-agent** à utiliser.
3. Si la tâche est exécutable immédiatement, proposer un prompt reformulé pour ce sous-agent.

Format strict : la section « Recommandation du routeur » définie dans `.claude/agents/advisor.md`.
