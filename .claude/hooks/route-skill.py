#!/usr/bin/env python3
"""UserPromptSubmit hook — détecte les invocations de skills dans le prompt
utilisateur, consulte .claude/skill-routing.json, et injecte une décision
de routage que Claude Code voit avant de traiter la demande.

Exit codes :
  0 → stdout injecté dans le contexte (si non vide)
  1 → erreur côté hook (loggée, pas bloquant)
  Pas de code 2 : on ne bloque jamais le prompt.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


SKILL_PATTERN = re.compile(
    r"(?:^|[\s(`\"'])/([a-zA-Z][a-zA-Z0-9_:-]+)",
    re.MULTILINE,
)


def read_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def find_routing_file(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        candidate = parent / ".claude" / "skill-routing.json"
        if candidate.is_file():
            return candidate
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        candidate = Path(env) / ".claude" / "skill-routing.json"
        if candidate.is_file():
            return candidate
    return None


def load_routing(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[route-skill] impossible de lire {path}: {exc}", file=sys.stderr)
        return {}


def extract_skills(prompt: str) -> list[str]:
    seen: list[str] = []
    for match in SKILL_PATTERN.finditer(prompt):
        name = match.group(1)
        if name.lower() in {
            "http", "https", "tmp", "etc", "usr", "home", "var", "opt", "root",
            "bin", "dev", "proc", "sys", "mnt", "srv",
        }:
            continue
        if name not in seen:
            seen.append(name)
    return seen


def lookup(skill: str, routing: dict) -> dict | None:
    routes = routing.get("routes", {})
    if skill in routes:
        return {**routes[skill], "skill": skill, "matched": "exact"}
    for pattern in routing.get("patterns", []):
        regex = pattern.get("match")
        if not regex:
            continue
        try:
            if re.search(regex, skill):
                return {
                    **{k: v for k, v in pattern.items() if k != "match"},
                    "skill": skill,
                    "matched": f"pattern:{regex}",
                }
        except re.error:
            continue
    return None


def format_routing(decisions: list[dict], default: dict | None) -> str:
    if not decisions:
        return ""
    lines = [
        "<advisor-routing>",
        "Routage automatique pour ce prompt (table : .claude/skill-routing.json) :",
        "",
    ]
    for d in decisions:
        agent = d.get("agent", "code-worker")
        model = d.get("model", "sonnet")
        why = d.get("why", "")
        skill = d.get("skill", "?")
        match_kind = d.get("matched", "")
        suffix = f" — {why}" if why else ""
        lines.append(
            f"- `/{skill}` → agent **{agent}** (Claude **{model}**){suffix}"
        )
        if match_kind.startswith("pattern:"):
            lines.append(f"  (match par pattern : `{match_kind[8:]}`)")
    lines.append("")
    lines.append(
        "Règle : avant d'exécuter chacune de ces skills, délègue à l'agent "
        "nommé via l'outil `Agent` (subagent_type correspondant) pour qu'elle "
        "tourne sur le bon modèle. Si une skill n'est pas listée, applique "
        "par défaut l'agent "
        f"**{(default or {}).get('agent', 'code-worker')}** "
        f"(Claude **{(default or {}).get('model', 'sonnet')}**)."
    )
    lines.append("</advisor-routing>")
    return "\n".join(lines)


def main() -> int:
    payload = read_payload()
    prompt = (
        payload.get("prompt")
        or payload.get("user_message")
        or payload.get("message")
        or ""
    )
    if not isinstance(prompt, str) or not prompt.strip():
        return 0

    cwd = Path(payload.get("cwd") or os.getcwd())
    routing_file = find_routing_file(cwd)
    if not routing_file:
        return 0

    routing = load_routing(routing_file)
    if not routing:
        return 0

    skills = extract_skills(prompt)
    if not skills:
        return 0

    decisions = []
    for skill in skills:
        hit = lookup(skill, routing)
        if hit:
            decisions.append(hit)

    output = format_routing(decisions, routing.get("default"))
    if output:
        sys.stdout.write(output)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[route-skill] erreur non bloquante : {exc}", file=sys.stderr)
        sys.exit(1)
