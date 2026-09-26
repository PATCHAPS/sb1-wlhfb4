#!/usr/bin/env python3
"""Regroupe les fiches « Les Forces et les Failles » de l'Asie du Sud-Est.

Parcourt le dossier SAPERE du disque, cherche pour chacun des onze pays de la
sous-région les fichiers de `dossiers/forces-et-failles/[ISO3]/2026/actuel/`
(et, à défaut, le dernier sous-dossier de `travail/`), puis les COPIE dans un
dossier de regroupement unique. Les originaux ne sont jamais déplacés ni
modifiés. Un index `INDEX.md` donne l'état de chaque pays, le score LU DANS
LA FICHE elle-même (le MASTER fait foi) et l'empreinte MD5 de chaque fichier.
Le calibrage ci-dessous n'est qu'une référence : tout écart entre lui et la
fiche est signalé, jamais corrigé en silence.

Tout le répertoire donné (par exemple ~, soit /Users/sapere) est aussi
inventorié, hors dossiers système et cachés, ainsi que Téléchargements : une fiche téléchargée depuis
une discussion avec Claude et pas encore rangée y est souvent la plus récente.
Pour chaque rôle (MASTER, PUBLIC), la version retenue est la plus récente,
d'après la date du nom de fichier puis la date d'enregistrement ; l'index
signale toute version prise dans Téléchargements, à ranger en `actuel`.

Usage :
    python3 regrouper_asie_sud_est.py CHEMIN_DU_DOSSIER_SAPERE [--telechargements DOSSIER] [--dest DOSSIER] [--simuler]

Exemple :
    python3 regrouper_asie_sud_est.py ~/SAPERE --simuler
    python3 regrouper_asie_sud_est.py ~/SAPERE
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

# Notes du fichier Cadre_FF_Asie-du-Sud-Est_2026-09-26 : RÉFÉRENCE À CONTRÔLER,
# pas source. Singapour y figure à 3,9 alors que la dernière version est à 3,6.
PAYS = [
    ("SGP", "Singapour", "3,9", "Résilient sous contrainte"),
    ("MYS", "Malaisie", "3,4", "Résilient sous contrainte"),
    ("VNM", "Vietnam", "3,2", "Résilient sous contrainte"),
    ("IDN", "Indonésie", "3,2", "Résilient sous contrainte"),
    ("THA", "Thaïlande", "3,2", "Résilient sous contrainte"),
    ("PHL", "Philippines", "2,9", "Sous tension structurelle"),
    ("KHM", "Cambodge", "2,6", "Sous tension structurelle"),
    ("BRN", "Brunei", "2,6", "Sous tension structurelle"),
    ("TLS", "Timor-Oriental", "2,4", "Fragile et dépendant"),
    ("LAO", "Laos", "2,1", "Fragile et dépendant"),
    ("MMR", "Myanmar", "1,5", "Fragile et dépendant"),
]

EXTENSIONS = {".html", ".md", ".txt", ".pdf"}


def md5(chemin: Path) -> str:
    h = hashlib.md5()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 16), b""):
            h.update(bloc)
    return h.hexdigest()


def trouver_racine_ff(sapere: Path) -> Path:
    """Localise `dossiers/forces-et-failles`, où qu'il soit sous SAPERE."""
    direct = sapere / "dossiers" / "forces-et-failles"
    if direct.is_dir():
        return direct
    for cand in sapere.rglob("forces-et-failles"):
        if cand.is_dir() and cand.parent.name == "dossiers":
            return cand
    return None


def fichiers_du_pays(ff: Path, iso: str):
    """Rend (source, fichiers) : `actuel` s'il est garni, sinon le dernier `travail`."""
    base = ff / iso / "2026"
    actuel = base / "actuel"
    garnis = [p for p in sorted(actuel.glob("*")) if p.is_file() and p.suffix in EXTENSIONS] if actuel.is_dir() else []
    if garnis:
        return "actuel", garnis
    travail = base / "travail"
    if travail.is_dir():
        sous = sorted((d for d in travail.iterdir() if d.is_dir()), key=lambda d: d.name)
        for d in reversed(sous):
            fs = [p for p in sorted(d.glob("*")) if p.is_file() and p.suffix in EXTENSIONS]
            if any("_Master_" in p.name or "_Public_" in p.name for p in fs):
                return f"travail/{d.name}", fs
    return None, []


DATE_NOM = re.compile(r"(20\d\d-\d\d-\d\d)")


def role(f: Path):
    for r in ("_Master_", "_Public_"):
        if r in f.name:
            return r.strip("_")
    return None


def fraicheur(f: Path):
    """Clé de tri : date du nom de fichier, puis date d'enregistrement."""
    m = DATE_NOM.search(f.name)
    return (m.group(1) if m else "0000-00-00", f.stat().st_mtime)


def dossiers_telechargements(explicite):
    if explicite:
        return [explicite.expanduser()]
    home = Path.home()
    return [d for d in (home / "Downloads", home / "Téléchargements") if d.is_dir()]


IGNORES = {"Library", "Applications", "node_modules", "_archives-millesimes-anterieurs"}


def inventaire(racines, exclure):
    """Tous les fichiers Claude-Sapere_* sous les racines, hors dossiers système et cachés."""
    vus, trouves = set(), []
    for r in racines:
        for dirpath, dirnames, filenames in os.walk(r):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in IGNORES
                           and not d.startswith("regroupement_")]
            for n in filenames:
                if n.startswith("Claude-Sapere_"):
                    p = Path(dirpath, n).resolve()
                    if p.suffix in EXTENSIONS and p not in vus and exclure not in p.parents:
                        vus.add(p)
                        trouves.append(p)
    return trouves


def epars_du_pays(inv, iso):
    return [p for p in inv if p.name.startswith(f"Claude-Sapere_{iso}_")]


def fusionner(ranges, telecharges):
    """Garde, par rôle, la version la plus récente ; rend (fichiers, pris_en_telechargement)."""
    retenus, pris = [p for p in ranges if role(p) is None], []
    for r in ("Master", "Public"):
        cands = [p for p in ranges + telecharges if role(p) == r]
        if not cands:
            continue
        meilleur = max(cands, key=fraicheur)
        retenus.append(meilleur)
        if meilleur in telecharges:
            pris.append(meilleur)
    return retenus, pris


SCORE = re.compile(r"(\d,\d)\s*/\s*5")


def lire_score(fichiers):
    """Score affiché, lu dans le MASTER d'abord, sinon dans le PUBLIC."""
    for marque in ("_Master_", "_Public_"):
        for f in fichiers:
            if marque in f.name and f.suffix == ".html":
                m = SCORE.search(f.read_text(encoding="utf-8", errors="ignore"))
                if m:
                    return m.group(1), f.name
    return None, None


def etat(fichiers) -> str:
    noms = [p.name for p in fichiers]
    m = any("_Master_" in n for n in noms)
    p = any("_Public_" in n for n in noms)
    s = any("veille-seuils-bascule" in n for n in noms)
    if m and p:
        return "MASTER + PUBLIC" + (" + seuils" if s else "")
    if m or p:
        return "incomplète (" + ("MASTER" if m else "PUBLIC") + " seul)"
    return "à écrire"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sapere", type=Path, help="dossier SAPERE du disque")
    ap.add_argument("--telechargements", type=Path, help="dossier des téléchargements (défaut : ~/Downloads et ~/Téléchargements)")
    ap.add_argument("--dest", type=Path, help="dossier de regroupement (défaut : dossiers/forces-et-failles/asie-du-sud-est/regroupement_AAAA-MM-JJ)")
    ap.add_argument("--simuler", action="store_true", help="affiche ce qui serait copié, sans rien écrire")
    a = ap.parse_args()

    racine = a.sapere.expanduser().resolve()
    ff = trouver_racine_ff(racine)
    dest = a.dest or (ff or racine) / "asie-du-sud-est" / f"regroupement_{date.today().isoformat()}"
    dl = dossiers_telechargements(a.telechargements)
    print(f"Répertoire parcouru : {racine}")
    print(f"Rangement : {ff or 'aucun dossier dossiers/forces-et-failles, recherche dans tout le répertoire'}")
    print("Inventaire des fichiers Claude-Sapere_* en cours...")
    inv = inventaire([racine] + dl, dest.resolve())
    print(f"{len(inv)} fichier(s) Claude-Sapere_* trouvés.\nTéléchargements : {', '.join(map(str, dl)) or 'aucun'}\nDestination : {dest}{'  (simulation)' if a.simuler else ''}\n")

    lignes, copies, ecarts, a_ranger = [], 0, [], []
    for rang, (iso, nom, calib, niveau) in enumerate(PAYS, 1):
        source, fs = fichiers_du_pays(ff, iso) if ff else (None, [])
        ranges = {f.resolve() for f in fs}
        ailleurs = [p for p in epars_du_pays(inv, iso) if p not in ranges]
        fs, pris = fusionner([f.resolve() for f in fs], ailleurs)
        if pris:
            source = (source + " + " if source else "") + "hors rangement"
            a_ranger += [f"{nom} : {p}" for p in pris]
        st = etat(fs)
        lu, lu_dans = lire_score(fs)
        if lu and lu != calib:
            ecarts.append(f"{nom} : fiche {lu} ({lu_dans}), calibrage {calib}")
        score = lu or f"{calib} (calibrage, fiche absente)"
        alerte = "  ÉCART" if lu and lu != calib else ""
        print(f"{rang:>2}. {nom:<15} {score:<6} {st:<28} {source or ''}{alerte}")
        lignes.append(f"| {rang} | {nom} | {iso} | {score}{' ⚠ calibrage ' + calib if alerte else ''} | {niveau if not alerte else 'à relire'} | {st} | {source or 'n.d.'} |")
        for f in fs:
            cible = dest / f"{rang:02d}_{iso}" / f.name
            empreinte = md5(f)
            print(f"      {f.name}  md5 {empreinte}")
            if not a.simuler:
                cible.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, cible)
                if md5(cible) != empreinte:
                    sys.exit(f"Copie altérée : {cible}")
            lignes.append(f"|  |  |  |  |  | `{f.name}` | md5 `{empreinte}` |")
            copies += 1

    index = "\n".join([
        "# Les Forces et les Failles · Asie du Sud-Est · regroupement",
        "",
        f"Regroupé le {date.today().isoformat()} depuis `{ff}`. Copies, les originaux restent en place.",
        "Grille SAPERE 2.2, grille v3. Score lu dans chaque fiche (le MASTER fait foi) ;",
        "pour les pays sans fiche, note du calibrage du 25-26 septembre 2026.",
        "",
        "| Rang | Pays | ISO3 | Score | Niveau | État / fichier | Source / MD5 |",
        "|---|---|---|---|---|---|---|",
        *lignes,
        "",
        "## Versions prises hors rangement (Téléchargements ou ailleurs, plus récentes, à verser en `actuel`)",
        "",
        *([f"- {x}" for x in a_ranger] or ["Aucune."]),
        "",
        "## Écarts entre fiches et calibrage",
        "",
        *([f"- {e}" for e in ecarts] or ["Aucun."]),
        "",
        "Le classement se recalcule sur les scores lus : ne jamais le recopier du calibrage.",
    ])
    if a_ranger:
        print("\nPLUS RÉCENT HORS RANGEMENT (à verser en actuel) :")
        for x in a_ranger:
            print("  - " + x)
    if ecarts:
        print("\nÉCARTS fiche / calibrage (à reporter dans le cadre) :")
        for e in ecarts:
            print("  - " + e)
    if a.simuler:
        print(f"\n{copies} fichier(s) seraient copiés. Relancer sans --simuler pour écrire.")
    else:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "INDEX.md").write_text(index + "\n", encoding="utf-8")
        print(f"\n{copies} fichier(s) copiés et vérifiés (MD5). Index : {dest / 'INDEX.md'}")


if __name__ == "__main__":
    main()
