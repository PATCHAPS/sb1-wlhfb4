"""Télécharge un skill depuis GitHub et l'empaquette en .zip pour l'app Claude.

Usage :
    python empaqueter_skill.py <owner/repo> <nom-du-skill> [dossier_de_sortie]

- clone le dépôt (git, profondeur 1) dans un dossier temporaire vide ;
- cherche le dossier dont le SKILL.md déclare `name: <nom-du-skill>`
  (ou, à défaut, un dossier portant ce nom) ;
- affiche la liste des fichiers et le SKILL.md complet pour relecture ;
- refuse les liens symboliques et tout chemin qui sort du dossier du skill ;
- écrit <dossier_de_sortie>/<nom>.zip avec le dossier du skill à la racine.

Le script n'exécute aucun code du dépôt téléchargé.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

DEPOT = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
LIMITE_OCTETS = 30 * 1024 * 1024


def nom_declare(skill_md: Path) -> str:
    texte = skill_md.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^---\s*\n(.*?)\n---", texte, re.S)
    if not m:
        return ""
    n = re.search(r"^name:\s*['\"]?([^'\"\n]+)", m.group(1), re.M)
    return n.group(1).strip() if n else ""


def trouver_dossier(racine: Path, nom: str) -> Path | None:
    candidats = [p for p in racine.rglob("SKILL.md") if ".git" not in p.parts]
    for p in candidats:
        if nom_declare(p).lower() == nom.lower():
            return p.parent
    for p in candidats:
        if p.parent.name.lower() == nom.lower():
            return p.parent
    return None


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    depot, nom = sys.argv[1].strip(), sys.argv[2].strip()
    sortie = Path(sys.argv[3] if len(sys.argv) > 3 else ".").resolve()
    depot = depot.removeprefix("https://github.com/").removesuffix(".git").strip("/")
    if not DEPOT.match(depot):
        print(f"Dépôt invalide : {depot} (attendu owner/repo)")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        cible = Path(tmp) / "depot"
        res = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet",
             f"https://github.com/{depot}.git", str(cible)],
            capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            print(f"Clonage impossible : {res.stderr.strip()[:300]}")
            return 1

        dossier = trouver_dossier(cible, nom)
        if dossier is None:
            noms = sorted({nom_declare(p) or p.parent.name
                           for p in cible.rglob("SKILL.md") if ".git" not in p.parts})
            print(f"Skill « {nom} » introuvable. Skills du dépôt : {', '.join(noms) or 'aucun'}")
            return 1

        fichiers, total = [], 0
        for p in sorted(dossier.rglob("*")):
            if p.is_symlink():
                print(f"REFUS : lien symbolique {p.relative_to(dossier)}")
                return 1
            if p.is_file():
                p.resolve().relative_to(dossier.resolve())   # lève si hors du dossier
                total += p.stat().st_size
                fichiers.append(p)
        if total > LIMITE_OCTETS:
            print(f"REFUS : skill trop lourd ({total // 1024} Ko)")
            return 1

        print(f"=== Fichiers du skill ({len(fichiers)}, {total // 1024} Ko) ===")
        for p in fichiers:
            print(f"  {p.relative_to(dossier)}  ({p.stat().st_size} o)")
        print("\n=== SKILL.md (à relire avant de recommander) ===")
        print((dossier / "SKILL.md").read_text(encoding="utf-8", errors="replace"))

        nom_final = nom_declare(dossier / "SKILL.md") or dossier.name
        if re.search(r"claude|anthropic", nom_final, re.I):
            print(f"\nATTENTION : le nom « {nom_final} » contient un mot réservé ; "
                  "renomme le champ name du SKILL.md avant l'import.")

        sortie.mkdir(parents=True, exist_ok=True)
        archive = sortie / f"{dossier.name}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for p in fichiers:
                z.write(p, Path(dossier.name) / p.relative_to(dossier))
        print(f"\nArchive prête : {archive}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
