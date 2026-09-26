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

Exemples :
    python3 regrouper_asie_sud_est.py ~ --etat      # page d'état de la série, ouverte dans le navigateur, rien n'est copié
    python3 regrouper_asie_sud_est.py ~ --simuler   # ce qui serait regroupé
    python3 regrouper_asie_sud_est.py ~             # regroupement réel

La référence des scores est le cadre le plus récent
(`atelier-asie/2026/asie-du-sud-est/Cadre_FF_Asie-du-Sud-Est_*.md`) : un « ÉCART »
signale une fiche dont le score n'a pas été reporté dans le cadre.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
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


NIVEAUX_ECHELLE = [  # borne basse, libellé, couleur canonique SAPERE
    (4.0, "Solidement ancré", "#14532D"),
    (3.0, "Résilient sous contrainte", "#5F7A1A"),
    (2.5, "Sous tension structurelle", "#1E5C99"),
    (1.5, "Fragile et dépendant", "#D35400"),
    (0.0, "Défaillance critique", "#111111"),
]


def niveau_de(score: str):
    v = float(score.replace(",", "."))
    for borne, lib, coul in NIVEAUX_ECHELLE:
        if v >= borne:
            return lib, coul


def cadre_le_plus_recent(ff):
    """Dernière révision du cadre, dans le dossier de l'atelier (jamais dans archives-cadre/)."""
    if not ff:
        return None
    atelier = ff / "atelier-asie" / "2026" / "asie-du-sud-est"
    revs = sorted(atelier.glob("Cadre_FF_Asie-du-Sud-Est_*.md")) if atelier.is_dir() else []
    return revs[-1] if revs else None


def scores_du_cadre(cadre):
    """Colonne « Score » des tableaux du cadre : première occurrence par pays (§ 2.1 avant § 2.2)."""
    noms = {nom: iso for iso, nom, _, _ in PAYS}
    trouves, idx = {}, None
    for ligne in cadre.read_text(encoding="utf-8").splitlines():
        if not ligne.startswith("|"):
            idx = None
            continue
        cells = [c.strip().strip("*").strip() for c in ligne.strip().strip("|").split("|")]
        if "Pays" in cells and "Score" in cells:
            idx = cells.index("Score")
            continue
        if idx is not None and len(cells) > idx and cells[0] in noms:
            m = re.search(r"\d,\d", cells[idx])
            if m:
                trouves.setdefault(noms[cells[0]], m.group(0))
    return trouves


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
    """MASTER ou PUBLIC, que le fichier soit nommé Claude-Sapere_XXX_Master_… ou MASTER.html."""
    n = f.name
    if "_Master_" in n or n.upper() == "MASTER.HTML":
        return "Master"
    if "_Public_" in n or n.upper() == "PUBLIC.HTML":
        return "Public"
    return None


def fraicheur(f: Path):
    """Clé de tri : date du nom de fichier, puis date d'enregistrement."""
    m = DATE_NOM.search(f.name)
    mt = f.stat().st_mtime
    return (m.group(1) if m else date.fromtimestamp(mt).isoformat(), mt)


def dossiers_telechargements(explicite):
    if explicite:
        return [explicite.expanduser()]
    home = Path.home()
    return [d for d in (home / "Downloads", home / "Téléchargements") if d.is_dir()]


IGNORES = {"Library", "Applications", "node_modules", "_archives-millesimes-anterieurs", "historique"}


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
        deja = [p for p in ranges if role(p) == r and md5(p) == md5(meilleur)]
        if deja:
            meilleur = deja[0]  # contenu identique déjà rangé : rien à verser
        retenus.append(meilleur)
        if meilleur in telecharges:
            pris.append(meilleur)
    return retenus, pris


NIVEAUX = r"(?:Solidement ancr|R[ée]silient sous contrainte|Sous tension structurelle|Fragile et d[ée]pendant|D[ée]faillance critique)"
# Cartouche du PUBLIC : « 3,6/5 · Résilient sous contrainte · ... » (balises éventuelles entre les deux).
SCORE_GLOBAL = re.compile(r"(\d,\d)\s*(?:</?[^>]+>\s*)*/\s*5\s*(?:</?[^>]+>\s*)*(?:·|&middot;|&#183;|-)?\s*(?:</?[^>]+>\s*)*" + NIVEAUX)


def lire_score(fichiers):
    """Score GLOBAL : le « X,X/5 » immédiatement suivi d'un libellé de niveau
    (cartouche du hero), lu dans le PUBLIC puis le MASTER. Une note de pilier
    isolée n'est jamais prise pour le score."""
    for r in ("Public", "Master"):
        for f in fichiers:
            if role(f) == r and f.suffix == ".html":
                m = SCORE_GLOBAL.search(f.read_text(encoding="utf-8", errors="ignore"))
                if m:
                    return m.group(1), f.name
    return None, None


def etat(fichiers) -> str:
    noms = [p.name for p in fichiers]
    m = any(role(f) == "Master" for f in fichiers)
    p = any(role(f) == "Public" for f in fichiers)
    s = any("veille-seuils-bascule" in n or "SEUILS" in n.upper() for n in noms)
    if m and p:
        return "MASTER + PUBLIC" + (" + seuils" if s else "")
    if m or p:
        return "incomplète (" + ("MASTER" if m else "PUBLIC") + " seul)"
    return "à écrire"


def page_etat(fiches, cadre, racine):
    faites = sorted([f for f in fiches if f["ecrite"]], key=lambda f: -float(f["score"].replace(",", ".")))
    a_faire = [f for f in fiches if not f["ecrite"]]
    n, total = len(faites), len(fiches)

    def seg(f):
        if f["ecrite"]:
            return f'<span class="seg" style="background:{f["couleur"]}" title="{f["nom"]} {f["score"]}"></span>'
        return f'<span class="seg vide" title="{f["nom"]} : à écrire"></span>'

    def pieces(f):
        out = []
        for cle, lib in (("master", "MASTER"), ("public", "PUBLIC"), ("seuils", "Seuils"), ("apercu", "Aperçu")):
            ok = f[cle]
            out.append(f'<span class="piece {"ok" if ok else "manque"}">{"✓" if ok else "✗"} {lib}</span>')
        return "".join(out)

    def alertes(f):
        a = []
        if f["ecart"]:
            a.append(f'<span class="alerte">Cadre à {f["ref"]} : score non reporté</span>')
        if f["hors"]:
            a.append('<span class="alerte">Version plus récente hors <code>actuel</code></span>')
        if f["illisible"]:
            a.append('<span class="alerte">Score illisible dans la fiche</span>')
        return "".join(a) or '<span class="rien">à jour</span>'

    lignes_faites = "".join(f'''
      <tr>
        <td class="pays">{f["nom"]}<span class="iso">{f["iso"]}</span></td>
        <td class="score" style="color:{f["couleur"]}">{f["score"]}</td>
        <td><span class="niveau" style="background:{f["couleur"]}">{f["niveau"]}</span></td>
        <td class="pieces">{pieces(f)}</td>
        <td class="date">{f["date"]}</td>
        <td>{alertes(f)}</td>
      </tr>''' for f in faites)
    lignes_a_faire = "".join(f'''
      <tr class="afaire">
        <td class="pays">{f["nom"]}<span class="iso">{f["iso"]}</span></td>
        <td class="score">{f["ref"]}</td>
        <td colspan="4">Point de départ du calibrage. Aucune fiche trouvée sur le disque.</td>
      </tr>''' for f in a_faire)
    nb_alertes = sum(1 for f in faites if f["ecart"] or f["hors"] or f["illisible"])
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Asie du Sud-Est · état de la série</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap">
<style>
  body{{margin:0;background:#F4F5F7;color:#1B2230;font:15px/1.45 Inter,-apple-system,"Helvetica Neue",Arial,sans-serif}}
  main{{max-width:1080px;margin:0 auto;padding:32px 20px 48px}}
  .serie{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#8B1A1A;font-weight:600}}
  h1{{font-size:30px;margin:6px 0 4px;font-weight:800;text-wrap:balance}}
  .sous{{color:#5A6372;font-size:13px}}
  .compteur{{display:flex;align-items:baseline;gap:14px;margin:28px 0 10px;flex-wrap:wrap}}
  .compteur b{{font-size:44px;font-weight:800;font-variant-numeric:tabular-nums}}
  .compteur span{{color:#5A6372}}
  .barre{{display:flex;gap:4px;margin-bottom:8px}}
  .seg{{flex:1;height:14px;border-radius:3px}}
  .seg.vide{{background:repeating-linear-gradient(135deg,#fff 0 5px,#E3E6EB 5px 10px);border:1px solid #C9CED6}}
  .legende{{font-size:12px;color:#5A6372;margin-bottom:28px}}
  h2{{font-size:17px;margin:28px 0 10px}}
  .tab{{overflow-x:auto;background:#fff;border:1px solid #E1E4E9;border-radius:8px}}
  table{{border-collapse:collapse;width:100%;min-width:760px}}
  th{{text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#6B7382;font-weight:600;padding:10px 12px;border-bottom:1px solid #E1E4E9}}
  td{{padding:11px 12px;border-bottom:1px solid #EEF0F3;vertical-align:middle}}
  tr:last-child td{{border-bottom:0}}
  .pays{{font-weight:600}}
  .iso{{display:inline-block;margin-left:8px;font-size:11px;color:#8A93A2;font-weight:400}}
  .score{{font-weight:800;font-size:18px;font-variant-numeric:tabular-nums}}
  .niveau{{color:#fff;font-size:12px;padding:3px 9px;border-radius:999px;white-space:nowrap}}
  .pieces{{white-space:nowrap}}
  .piece{{display:inline-block;font-size:11px;padding:2px 7px;border-radius:4px;margin-right:4px}}
  .piece.ok{{background:#E7F2EA;color:#1A5C2E}}
  .piece.manque{{background:#F3F4F6;color:#9AA1AC}}
  .date{{font-size:13px;color:#5A6372;white-space:nowrap;font-variant-numeric:tabular-nums}}
  .alerte{{display:inline-block;font-size:12px;background:#FDECEC;color:#A32D2D;padding:2px 8px;border-radius:4px;margin:1px 4px 1px 0}}
  .rien{{font-size:12px;color:#1A5C2E}}
  .afaire td{{color:#8A93A2}}
  .afaire .pays{{color:#1B2230}}
  .afaire .score{{font-size:15px;font-weight:600;color:#8A93A2}}
  footer{{margin-top:28px;font-size:12px;color:#6B7382}}
  code{{font-size:12px}}
</style></head><body><main>
  <div class="serie">SAPERE · Les Forces et les Failles · grille v3</div>
  <h1>Asie du Sud-Est : où en est la série</h1>
  <div class="sous">État calculé le {datetime.now().strftime("%d/%m/%Y à %H:%M")} en lisant les fiches sur le disque ({racine}).</div>
  <div class="compteur"><b>{n} / {total}</b><span>fiches écrites · {total - n} à écrire · {nb_alertes} fiche(s) avec une alerte</span></div>
  <div class="barre">{"".join(seg(f) for f in faites + a_faire)}</div>
  <div class="legende">Un segment par pays, de la fiche la mieux notée à la moins bien notée ; hachuré = à écrire. Couleurs de l'échelle SAPERE.</div>
  <h2>Fiches écrites ({n})</h2>
  <div class="tab"><table>
    <thead><tr><th>Pays</th><th>Score</th><th>Niveau</th><th>Pièces en <code>actuel</code></th><th>Fiche du</th><th>Contrôle</th></tr></thead>
    <tbody>{lignes_faites}</tbody></table></div>
  <h2>À écrire ({total - n})</h2>
  <div class="tab"><table>
    <thead><tr><th>Pays</th><th>Calibrage</th><th colspan="4"></th></tr></thead>
    <tbody>{lignes_a_faire}</tbody></table></div>
  <footer>Score lu dans le PUBLIC de chaque fiche. Référence des contrôles : {cadre.name if cadre else "calibrage intégré au script (aucun cadre trouvé)"}.
  Page régénérée à chaque lancement de <code>python3 ~/regrouper_asie_sud_est.py ~ --etat</code> : ne pas la modifier à la main.</footer>
</main></body></html>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sapere", type=Path, help="dossier SAPERE du disque")
    ap.add_argument("--telechargements", type=Path, help="dossier des téléchargements (défaut : ~/Downloads et ~/Téléchargements)")
    ap.add_argument("--dest", type=Path, help="dossier de regroupement (défaut : dossiers/forces-et-failles/asie-du-sud-est/regroupement_AAAA-MM-JJ)")
    ap.add_argument("--simuler", action="store_true", help="affiche ce qui serait copié, sans rien écrire")
    ap.add_argument("--etat", action="store_true", help="écrit et ouvre la page d'état de la série, sans rien copier")
    a = ap.parse_args()
    if a.etat:
        a.simuler = True

    racine = a.sapere.expanduser().resolve()
    ff = trouver_racine_ff(racine)
    dest = a.dest or (ff or racine) / "asie-du-sud-est" / f"regroupement_{date.today().isoformat()}"
    dl = dossiers_telechargements(a.telechargements)
    print(f"Répertoire parcouru : {racine}")
    print(f"Rangement : {ff or 'aucun dossier dossiers/forces-et-failles, recherche dans tout le répertoire'}")
    print("Inventaire des fichiers Claude-Sapere_* en cours...")
    inv = inventaire([racine] + dl, dest.resolve())
    cadre = cadre_le_plus_recent(ff)
    ref_cadre = scores_du_cadre(cadre) if cadre else {}
    print(f"Référence des scores : {cadre or 'calibrage intégré au script (aucun cadre trouvé)'}")
    print(f"{len(inv)} fichier(s) Claude-Sapere_* trouvés.\nTéléchargements : {', '.join(map(str, dl)) or 'aucun'}\nDestination : {dest}{'  (simulation)' if a.simuler else ''}\n")

    lignes, copies, ecarts, a_ranger, fiches = [], 0, [], [], []
    for rang, (iso, nom, calib, niveau) in enumerate(PAYS, 1):
        calib = ref_cadre.get(iso, calib)
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
        score = lu or (f"illisible (calibrage {calib})" if fs else f"{calib} (calibrage, fiche absente)")
        alerte = "  ÉCART" if lu and lu != calib else ""
        noms_fs = [f.name.upper() for f in fs]
        ecrite = any(role(f) == "Master" for f in fs) or any(role(f) == "Public" for f in fs)
        sc = lu or calib
        lib, coul = niveau_de(sc)
        dates = [fraicheur(f)[0] for f in fs if role(f)]
        fiches.append(dict(
            iso=iso, nom=nom, ecrite=ecrite, score=sc, ref=calib, niveau=lib, couleur=coul,
            master=any(role(f) == "Master" for f in fs), public=any(role(f) == "Public" for f in fs),
            seuils=any("SEUILS" in n or "VEILLE-SEUILS" in n for n in noms_fs),
            apercu=any(n.startswith("APERCU") for n in noms_fs),
            date=datetime.strptime(max(dates), "%Y-%m-%d").strftime("%d/%m/%Y") if dates else "",
            ecart=bool(alerte), hors=bool(pris), illisible=ecrite and not lu))
        print(f"{rang:>2}. {nom:<15} {score:<6} {st:<28} {source or ''}{alerte}")
        lignes.append(f"| {rang} | {nom} | {iso} | {score}{' ⚠ calibrage ' + calib if alerte else ''} | {niveau if not alerte else 'à relire'} | {st} | {source or 'n.d.'} |")
        for f in fs:
            cible = dest / f"{rang:02d}_{iso}" / f.name
            empreinte = md5(f)
            print(f"      {f.name}  md5 {empreinte}")
            if a.etat:
                continue
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
    if a.etat:
        cible = (ff or racine) / "asie-du-sud-est" / "ETAT_Asie-du-Sud-Est.html"
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_text(page_etat(fiches, cadre, racine), encoding="utf-8")
        print(f"\nPage d'état : {cible}")
        if sys.platform == "darwin":
            subprocess.run(["open", str(cible)])
        return
    if a.simuler:
        print(f"\n{copies} fichier(s) seraient copiés. Relancer sans --simuler pour écrire.")
    else:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "INDEX.md").write_text(index + "\n", encoding="utf-8")
        print(f"\n{copies} fichier(s) copiés et vérifiés (MD5). Index : {dest / 'INDEX.md'}")


if __name__ == "__main__":
    main()
