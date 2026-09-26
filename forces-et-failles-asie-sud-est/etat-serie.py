#!/usr/bin/env python3
"""État d'une série « Les Forces et les Failles », région par région.

Lit le disque et dit, pour une région, une sous-région ou un continent entier :
quelles fiches sont écrites (score, niveau, pièces présentes, date), lesquelles
restent à écrire, et ce qui cloche (score non reporté dans le cadre, version plus
récente hors `actuel`, score illisible). Produit une page HTML d'état, ouverte
dans le navigateur, et un résumé texte que la séance Claude relaie à l'auteur.

Rien n'est modifié sur le disque, hormis l'écriture de la page d'état (et, avec
--regrouper, la copie des fiches dans un dossier daté, originaux intacts).

Le score d'une fiche est recalculé depuis le littéral `var DATA` de son MASTER
(somme pondérée, Decimal, arrondi commercial au dixième) ; à défaut, lu dans le
cartouche du PUBLIC (« 3,6/5 · Résilient sous contrainte »). La référence des
contrôles est la révision la plus récente du cadre de la région
(`Cadre_FF_<Région>_*.md`, où qu'il soit sous `dossiers/forces-et-failles`,
hors dossiers d'archives).

Usage :
    python3 etat-serie.py ~ --region "Asie du Sud-Est"
    python3 etat-serie.py ~ --region "Afrique de l'Ouest"
    python3 etat-serie.py ~ --region Asie            # les cinq sous-régions
    python3 etat-serie.py ~ --region "Asie du Sud-Est" --regrouper
    python3 etat-serie.py --regions                  # liste des régions reconnues
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Nomenclatures SAPERE : Union africaine pour l'Afrique (skill forces-et-failles § 5.1),
# references/regions-asie.md pour l'Asie (§ 5.2). 54 + 47 pays.
REGIONS = {
    "Afrique": {
        "Afrique du Nord": [("DZA", "Algérie"), ("EGY", "Égypte"), ("LBY", "Libye"), ("MAR", "Maroc"),
                            ("MRT", "Mauritanie"), ("TUN", "Tunisie")],
        "Afrique de l'Ouest": [("BEN", "Bénin"), ("BFA", "Burkina Faso"), ("CPV", "Cap-Vert"),
                               ("CIV", "Côte d'Ivoire"), ("GMB", "Gambie"), ("GHA", "Ghana"), ("GIN", "Guinée"),
                               ("GNB", "Guinée-Bissau"), ("LBR", "Liberia"), ("MLI", "Mali"), ("NER", "Niger"),
                               ("NGA", "Nigeria"), ("SEN", "Sénégal"), ("SLE", "Sierra Leone"), ("TGO", "Togo")],
        "Afrique centrale": [("BDI", "Burundi"), ("CMR", "Cameroun"), ("CAF", "Centrafrique"),
                             ("COG", "Congo-Brazzaville"), ("GAB", "Gabon"), ("GNQ", "Guinée équatoriale"),
                             ("COD", "République démocratique du Congo"), ("STP", "São Tomé-et-Príncipe"),
                             ("TCD", "Tchad")],
        "Afrique de l'Est": [("COM", "Comores"), ("DJI", "Djibouti"), ("ERI", "Érythrée"), ("ETH", "Éthiopie"),
                             ("KEN", "Kenya"), ("MDG", "Madagascar"), ("MUS", "Maurice"), ("UGA", "Ouganda"),
                             ("RWA", "Rwanda"), ("SYC", "Seychelles"), ("SOM", "Somalie"), ("SDN", "Soudan"),
                             ("SSD", "Soudan du Sud"), ("TZA", "Tanzanie")],
        "Afrique australe": [("ZAF", "Afrique du Sud"), ("AGO", "Angola"), ("BWA", "Botswana"), ("SWZ", "Eswatini"),
                             ("LSO", "Lesotho"), ("MWI", "Malawi"), ("MOZ", "Mozambique"), ("NAM", "Namibie"),
                             ("ZMB", "Zambie"), ("ZWE", "Zimbabwe")],
    },
    "Asie": {
        "Caucase et Asie centrale": [("ARM", "Arménie"), ("AZE", "Azerbaïdjan"), ("GEO", "Géorgie"),
                                     ("KAZ", "Kazakhstan"), ("KGZ", "Kirghizistan"), ("UZB", "Ouzbékistan"),
                                     ("TJK", "Tadjikistan"), ("TKM", "Turkménistan")],
        "Asie du Sud": [("AFG", "Afghanistan"), ("BGD", "Bangladesh"), ("BTN", "Bhoutan"), ("IND", "Inde"),
                        ("MDV", "Maldives"), ("NPL", "Népal"), ("PAK", "Pakistan"), ("LKA", "Sri Lanka")],
        "Asie du Sud-Est": [("BRN", "Brunei"), ("KHM", "Cambodge"), ("IDN", "Indonésie"), ("LAO", "Laos"),
                            ("MYS", "Malaisie"), ("MMR", "Myanmar"), ("PHL", "Philippines"), ("SGP", "Singapour"),
                            ("THA", "Thaïlande"), ("TLS", "Timor-Oriental"), ("VNM", "Vietnam")],
        "Asie de l'Est": [("CHN", "Chine"), ("PRK", "Corée du Nord"), ("KOR", "Corée du Sud"), ("JPN", "Japon"),
                          ("MNG", "Mongolie"), ("TWN", "Taïwan")],
        "Moyen-Orient": [("SAU", "Arabie saoudite"), ("BHR", "Bahreïn"), ("ARE", "Émirats arabes unis"),
                         ("IRQ", "Irak"), ("IRN", "Iran"), ("ISR", "Israël"), ("JOR", "Jordanie"), ("KWT", "Koweït"),
                         ("LBN", "Liban"), ("OMN", "Oman"), ("PSE", "Palestine"), ("QAT", "Qatar"),
                         ("SYR", "Syrie"), ("YEM", "Yémen")],
    },
}
assert sum(len(v) for v in REGIONS["Afrique"].values()) == 54
assert sum(len(v) for v in REGIONS["Asie"].values()) == 47

POIDS = {"I": "0.135", "II": "0.135", "III": "0.09", "IV": "0.09", "V": "0.09",
         "VI": "0.135", "VII": "0.09", "VIII": "0.135", "IX": "0.10"}
ECHELLE = [(Decimal("4.0"), "Solidement ancré", "#14532D"),
           (Decimal("3.0"), "Résilient sous contrainte", "#5F7A1A"),
           (Decimal("2.5"), "Sous tension structurelle", "#1E5C99"),
           (Decimal("1.5"), "Fragile et dépendant", "#D35400"),
           (Decimal("0"), "Défaillance critique", "#111111")]
EXT = {".html", ".md", ".txt", ".pdf"}
IGNORES = {"Library", "Applications", "node_modules", "historique", "archives-cadre",
           "_archives-millesimes-anterieurs"}


def norm(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def resoudre(region):
    """Rend [(continent, région, [(iso, nom)])] pour un nom de région ou de continent."""
    n = norm(region)
    for cont, regs in REGIONS.items():
        if n == norm(cont):
            return [(cont, r, p) for r, p in regs.items()]
        for r, p in regs.items():
            if n == norm(r):
                return [(cont, r, p)]
    noms = [r for regs in REGIONS.values() for r in regs] + list(REGIONS)
    sys.exit(f"Région inconnue : {region}. Régions reconnues : {', '.join(noms)}.")


def num(t):
    return Decimal(str(t).split("/")[0].replace(",", ".").strip())


def dec_fr(d, n=1):
    return f"{d:.{n}f}".replace(".", ",")


def niveau(score):
    for borne, lib, coul in ECHELLE:
        if score >= borne:
            return lib, coul


def md5(p):
    h = hashlib.md5()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def role(p):
    n = p.name
    if "_Master_" in n or n.upper() == "MASTER.HTML":
        return "Master"
    if "_Public_" in n or n.upper() == "PUBLIC.HTML":
        return "Public"
    return None


DATE_NOM = re.compile(r"(20\d\d-\d\d-\d\d)")


def fraicheur(p):
    m = DATE_NOM.search(p.name)
    mt = p.stat().st_mtime
    return (m.group(1) if m else date.fromtimestamp(mt).isoformat(), mt)


def racine_ff(racine):
    d = racine / "SAPERE" / "dossiers" / "forces-et-failles"
    if d.is_dir():
        return d
    d = racine / "dossiers" / "forces-et-failles"
    if d.is_dir():
        return d
    for c in racine.rglob("forces-et-failles"):
        if c.is_dir() and c.parent.name == "dossiers":
            return c
    return None


def inventaire(racines):
    vus, out = set(), []
    for r in racines:
        for dp, dn, fn in os.walk(r):
            dn[:] = [d for d in dn if not d.startswith(".") and d not in IGNORES and not d.startswith("regroupement_")]
            for n in fn:
                if n.startswith("Claude-Sapere_"):
                    p = Path(dp, n).resolve()
                    if p.suffix in EXT and p not in vus:
                        vus.add(p)
                        out.append(p)
    return out


def actuel(ff, iso):
    """Fichiers de ff/ISO/<année la plus récente>/actuel."""
    base = ff / iso if ff else None
    if not base or not base.is_dir():
        return []
    annees = sorted(d for d in base.iterdir() if d.is_dir() and d.name.isdigit())
    for a in reversed(annees):
        d = a / "actuel"
        fs = [p.resolve() for p in sorted(d.glob("*")) if p.is_file() and p.suffix in EXT] if d.is_dir() else []
        if fs:
            return fs
    return []


def retenir(ranges, ailleurs):
    """Par rôle, la version la plus récente ; un contenu identique déjà rangé l'emporte."""
    out, hors = [p for p in ranges if role(p) is None], []
    for r in ("Master", "Public"):
        cands = [p for p in ranges + ailleurs if role(p) == r]
        if not cands:
            continue
        best = max(cands, key=fraicheur)
        same = [p for p in ranges if role(p) == r and md5(p) == md5(best)]
        best = same[0] if same else best
        out.append(best)
        if best not in ranges:
            hors.append(best)
    return out, hors


def littéral_data(html):
    i = html.find("var DATA")
    if i < 0:
        return None
    j = html.index("{", i)
    d = 0
    for k in range(j, len(html)):
        d += {"{": 1, "}": -1}.get(html[k], 0)
        if d == 0:
            break
    try:
        return json.loads(html[j:k + 1])
    except Exception:
        return None


NIV_RE = r"(?:Solidement ancr|R[ée]silient sous contrainte|Sous tension structurelle|Fragile et d[ée]pendant|D[ée]faillance critique)"
CARTOUCHE = re.compile(r"(\d,\d)\s*(?:</?[^>]+>\s*)*/\s*5\s*(?:</?[^>]+>\s*)*(?:·|&middot;|&#183;|-)?\s*(?:</?[^>]+>\s*)*" + NIV_RE)


def score_fiche(fs):
    """(score affiché, somme brute ou None, notes {pilier: note}, origine)."""
    for p in fs:
        if role(p) == "Master" and p.suffix == ".html":
            data = littéral_data(p.read_text(encoding="utf-8", errors="ignore"))
            if data:
                notes = {}
                for k, b in data.items():
                    if k in POIDS and isinstance(b, dict) and "n" in b:
                        try:
                            notes[k] = num(b["n"])
                        except Exception:
                            pass
                if notes:
                    poids = sum(Decimal(POIDS[k]) for k in notes)
                    brut = sum(notes[k] * Decimal(POIDS[k]) for k in notes) / poids
                    return brut.quantize(Decimal("0.1"), ROUND_HALF_UP), brut, notes, "MASTER (var DATA)"
    for r in ("Public", "Master"):
        for p in fs:
            if role(p) == r and p.suffix == ".html":
                m = CARTOUCHE.search(p.read_text(encoding="utf-8", errors="ignore"))
                if m:
                    return num(m.group(1)), None, {}, f"{r} (cartouche)"
    return None, None, {}, None


def cadre_region(ff, region):
    """Révision la plus récente de Cadre_FF_<Région>_*.md, hors archives."""
    if not ff:
        return None
    cible, cands = norm(region), []
    for dp, dn, fn in os.walk(ff):
        dn[:] = [d for d in dn if d not in IGNORES and not d.startswith(".") and not d.startswith("archives")]
        for n in fn:
            m = re.match(r"Cadre_FF_(.+?)_(20\d\d-\d\d-\d\d[a-z]?)\.md$", n)
            if m and norm(m.group(1)) == cible:
                cands.append((m.group(2), Path(dp, n)))
    return max(cands)[1] if cands else None


def scores_cadre(cadre, pays):
    noms = {nom: iso for iso, nom in pays}
    out, idx = {}, None
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
                out.setdefault(noms[cells[0]], num(m.group(0)))
    return out


def examiner(ff, inv, cont, region, pays):
    cadre = cadre_region(ff, region)
    ref = scores_cadre(cadre, pays) if cadre else {}
    fiches = []
    for iso, nom in pays:
        ranges = actuel(ff, iso)
        ailleurs = [p for p in inv if p.name.startswith(f"Claude-Sapere_{iso}_") and p not in ranges]
        fs, hors = retenir(ranges, ailleurs)
        noms = [p.name.upper() for p in fs]
        ecrite = any(role(p) for p in fs)
        sc, brut, notes, origine = score_fiche(fs) if ecrite else (None, None, {}, None)
        r = ref.get(iso)
        base = sc if sc is not None else r
        lib, coul = niveau(base) if base is not None else ("", "#9AA1AC")
        dates = [fraicheur(p)[0] for p in fs if role(p)]
        fiches.append(dict(
            continent=cont, region=region, iso=iso, nom=nom, ecrite=ecrite, score=sc, brut=brut, notes=notes,
            origine=origine, ref=r, niveau=lib, couleur=coul, fichiers=fs,
            master=any(role(p) == "Master" for p in fs), public=any(role(p) == "Public" for p in fs),
            seuils=any("SEUILS" in n for n in noms), apercu=any(n.startswith("APERCU") for n in noms),
            date=datetime.strptime(max(dates), "%Y-%m-%d").strftime("%d/%m/%Y") if dates else "",
            ecart=ecrite and sc is not None and r is not None and sc != r,
            non_reporte=ecrite and bool(ref) and r is None,
            hors=[str(p) for p in hors], illisible=ecrite and sc is None))
    return cadre, fiches


def alertes(f):
    a = []
    if f["ecart"]:
        a.append(f"score de la fiche {dec_fr(f['score'])}, cadre {dec_fr(f['ref'])} : cadre à mettre à jour")
    if f["non_reporte"]:
        a.append("fiche écrite absente du cadre")
    if f["hors"]:
        a.append("version plus récente hors actuel : " + ", ".join(f["hors"]))
    if f["illisible"]:
        a.append("score illisible dans la fiche")
    if f["ecrite"] and not f["public"]:
        a.append("PUBLIC manquant")
    if f["ecrite"] and not f["master"]:
        a.append("MASTER manquant")
    return a


def cle_score(f):
    s = f["brut"] if f["brut"] is not None else f["score"]
    return -(s if s is not None else Decimal(0))


def page(titre, blocs, racine):
    toutes = [f for _, _, fs in blocs for f in fs]
    faites = [f for f in toutes if f["ecrite"]]
    n, total = len(faites), len(toutes)
    nb_al = sum(1 for f in faites if alertes(f))
    plusieurs = len(blocs) > 1

    def seg(f):
        if f["ecrite"]:
            return f'<span class="seg" style="background:{f["couleur"]}" title="{f["nom"]} {dec_fr(f["score"]) if f["score"] else ""}"></span>'
        return f'<span class="seg vide" title="{f["nom"]} : à écrire"></span>'

    def pieces(f):
        return "".join(
            f'<span class="piece {"ok" if f[k] else "manque"}">{"✓" if f[k] else "✗"} {lib}</span>'
            for k, lib in (("master", "MASTER"), ("public", "PUBLIC"), ("seuils", "Seuils"), ("apercu", "Aperçu")))

    def controle(f):
        a = alertes(f)
        return "".join(f'<span class="alerte">{x}</span>' for x in a) or '<span class="rien">à jour</span>'

    sections = []
    for cont, region, fs in blocs:
        ec = sorted([f for f in fs if f["ecrite"]], key=cle_score)
        af = sorted([f for f in fs if not f["ecrite"]], key=lambda f: (-(f["ref"] or 0), norm(f["nom"])))
        barre = "".join(seg(f) for f in ec + af)
        lignes_ec = "".join(f'''
        <tr><td class="pays">{f["nom"]}<span class="iso">{f["iso"]}</span></td>
          <td class="score" style="color:{f["couleur"]}">{dec_fr(f["score"]) if f["score"] is not None else "?"}</td>
          <td><span class="niveau" style="background:{f["couleur"]}">{f["niveau"]}</span></td>
          <td class="pieces">{pieces(f)}</td><td class="date">{f["date"]}</td><td>{controle(f)}</td></tr>''' for f in ec)
        lignes_af = "".join(f'''
        <tr class="afaire"><td class="pays">{f["nom"]}<span class="iso">{f["iso"]}</span></td>
          <td class="score">{dec_fr(f["ref"]) if f["ref"] is not None else "–"}</td>
          <td colspan="4">{"Note de départ inscrite au cadre." if f["ref"] is not None else "Aucune note de départ au cadre."}</td></tr>''' for f in af)
        entete = f'<h2 class="region">{region} <span>{len(ec)} / {len(fs)}</span></h2>' if plusieurs else ""
        sections.append(f'''
      <section>{entete}
        <div class="barre">{barre}</div>
        <h3>Fiches écrites ({len(ec)})</h3>
        {'<div class="tab"><table><thead><tr><th>Pays</th><th>Score</th><th>Niveau</th><th>Pièces</th><th>Fiche du</th><th>Contrôle</th></tr></thead><tbody>' + lignes_ec + '</tbody></table></div>' if ec else '<div class="vide-msg">Aucune fiche écrite pour l’instant.</div>'}
        <h3>À écrire ({len(af)})</h3>
        {'<div class="tab"><table><thead><tr><th>Pays</th><th>Cadre</th><th colspan="4"></th></tr></thead><tbody>' + lignes_af + '</tbody></table></div>' if af else '<div class="vide-msg">Série complète.</div>'}
      </section>''')
    cadres = sorted({f["cadre"] for f in toutes if f.get("cadre")})
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titre} · état de la série</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap">
<style>
  body{{margin:0;background:#F4F5F7;color:#1B2230;font:15px/1.45 Inter,-apple-system,"Helvetica Neue",Arial,sans-serif}}
  main{{max-width:1080px;margin:0 auto;padding:32px 20px 48px}}
  .serie{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#8B1A1A;font-weight:600}}
  h1{{font-size:30px;margin:6px 0 4px;font-weight:800;text-wrap:balance}}
  .sous{{color:#5A6372;font-size:13px}}
  .compteur{{display:flex;align-items:baseline;gap:14px;margin:28px 0 14px;flex-wrap:wrap}}
  .compteur b{{font-size:44px;font-weight:800;font-variant-numeric:tabular-nums}}
  .compteur span{{color:#5A6372}}
  section{{margin-bottom:26px}}
  h2.region{{font-size:20px;margin:30px 0 10px;padding-top:18px;border-top:1px solid #DDE1E7}}
  h2.region span{{font-size:14px;color:#5A6372;font-weight:600;margin-left:8px}}
  h3{{font-size:15px;margin:20px 0 8px}}
  .barre{{display:flex;gap:4px;margin:6px 0 4px}}
  .seg{{flex:1;height:14px;border-radius:3px}}
  .seg.vide{{background:repeating-linear-gradient(135deg,#fff 0 5px,#E3E6EB 5px 10px);border:1px solid #C9CED6}}
  .legende{{font-size:12px;color:#5A6372}}
  .tab{{overflow-x:auto;background:#fff;border:1px solid #E1E4E9;border-radius:8px}}
  table{{border-collapse:collapse;width:100%;min-width:760px}}
  th{{text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#6B7382;font-weight:600;padding:10px 12px;border-bottom:1px solid #E1E4E9}}
  td{{padding:11px 12px;border-bottom:1px solid #EEF0F3;vertical-align:middle}}
  tr:last-child td{{border-bottom:0}}
  .pays{{font-weight:600}} .iso{{margin-left:8px;font-size:11px;color:#8A93A2;font-weight:400}}
  .score{{font-weight:800;font-size:18px;font-variant-numeric:tabular-nums}}
  .niveau{{color:#fff;font-size:12px;padding:3px 9px;border-radius:999px;white-space:nowrap}}
  .pieces{{white-space:nowrap}}
  .piece{{display:inline-block;font-size:11px;padding:2px 7px;border-radius:4px;margin-right:4px}}
  .piece.ok{{background:#E7F2EA;color:#1A5C2E}} .piece.manque{{background:#F3F4F6;color:#9AA1AC}}
  .date{{font-size:13px;color:#5A6372;white-space:nowrap;font-variant-numeric:tabular-nums}}
  .alerte{{display:inline-block;font-size:12px;background:#FDECEC;color:#A32D2D;padding:2px 8px;border-radius:4px;margin:1px 4px 1px 0}}
  .rien{{font-size:12px;color:#1A5C2E}}
  .afaire td{{color:#8A93A2}} .afaire .pays{{color:#1B2230}} .afaire .score{{font-size:15px;font-weight:600;color:#8A93A2}}
  .vide-msg{{color:#6B7382;font-size:14px;padding:6px 0}}
  footer{{margin-top:28px;font-size:12px;color:#6B7382}}
</style></head><body><main>
  <div class="serie">SAPERE · Les Forces et les Failles</div>
  <h1>{titre} : où en est la série</h1>
  <div class="sous">État calculé le {datetime.now().strftime("%d/%m/%Y à %H:%M")} en lisant les fiches sur le disque ({racine}).</div>
  <div class="compteur"><b>{n} / {total}</b><span>fiches écrites · {total - n} à écrire · {nb_al} fiche(s) avec une alerte</span></div>
  <div class="legende">Barres : un segment par pays, de la fiche la mieux notée à la moins bien notée, puis les pays à écrire (hachurés). Couleurs de l'échelle SAPERE.</div>
  {"".join(sections)}
  <footer>Score recalculé depuis le MASTER (somme pondérée) ou lu dans le cartouche du PUBLIC.
  Cadre(s) de référence : {", ".join(cadres) or "aucun cadre trouvé pour cette région"}.
  Page régénérée à chaque lancement de <code>etat-serie.py</code> : ne pas la modifier à la main.</footer>
</main></body></html>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("racine", nargs="?", type=Path, default=Path.home(), help="répertoire à parcourir (défaut : ~)")
    ap.add_argument("--region", help="région, sous-région ou continent (ex. « Asie du Sud-Est », « Afrique »)")
    ap.add_argument("--regions", action="store_true", help="liste les régions reconnues")
    ap.add_argument("--regrouper", action="store_true", help="copie aussi les fiches écrites dans un dossier daté")
    ap.add_argument("--ne-pas-ouvrir", action="store_true", help="n'ouvre pas la page dans le navigateur")
    a = ap.parse_args()
    if a.regions or not a.region:
        for cont, regs in REGIONS.items():
            print(f"{cont} ({sum(len(p) for p in regs.values())} pays)")
            for r, p in regs.items():
                print(f"  {r} ({len(p)})")
        return

    racine = a.racine.expanduser().resolve()
    ff = racine_ff(racine)
    cibles = resoudre(a.region)
    titre = a.region if len(cibles) > 1 else cibles[0][1]
    dl = [d for d in (Path.home() / "Downloads", Path.home() / "Téléchargements") if d.is_dir()]
    inv = inventaire([racine] + [d for d in dl if racine not in d.parents and d != racine])

    blocs = []
    for cont, region, pays in cibles:
        cadre, fiches = examiner(ff, inv, cont, region, pays)
        for f in fiches:
            f["cadre"] = cadre.name if cadre else None
        blocs.append((cont, region, fiches))

    # Résumé texte, relayé par la séance à l'auteur.
    toutes = [f for _, _, fs in blocs for f in fs]
    faites = [f for f in toutes if f["ecrite"]]
    print(f"ÉTAT · {titre} · {len(faites)} fiche(s) écrite(s) sur {len(toutes)}")
    print(f"Fiches lues sous : {ff or racine}")
    for cont, region, fs in blocs:
        cadre = fs[0]["cadre"] if fs else None
        print(f"\n== {region} · {sum(f['ecrite'] for f in fs)} / {len(fs)} · cadre : {cadre or 'aucun'}")
        for f in sorted([f for f in fs if f["ecrite"]], key=cle_score):
            s = dec_fr(f["score"]) if f["score"] is not None else "?"
            b = f" (somme {dec_fr(f['brut'], 4)})" if f["brut"] is not None else ""
            al = alertes(f)
            print(f"  ÉCRITE    {f['nom']:<22} {s}{b}  {f['niveau']}  fiche du {f['date']}" + (f"  ⚠ {' ; '.join(al)}" if al else ""))
        for f in sorted([f for f in fs if not f["ecrite"]], key=lambda f: (-(f["ref"] or 0), norm(f["nom"]))):
            print(f"  À ÉCRIRE  {f['nom']:<22} " + (f"note de départ au cadre {dec_fr(f['ref'])}" if f["ref"] is not None else "aucune note de départ"))

    base = ff or racine
    cible = base / "etat" / f"ETAT_{norm(titre).replace(' ', '-')}.html"
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(page(titre, blocs, racine), encoding="utf-8")
    print(f"\nPage d'état : {cible}")

    if a.regrouper:
        dest = base / "regroupements" / f"{norm(titre).replace(' ', '-')}_{date.today().isoformat()}"
        n = 0
        for f in faites:
            for p in f["fichiers"]:
                c = dest / f"{f['iso']}_{norm(f['nom']).replace(' ', '-')}" / p.name
                c.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, c)
                if md5(c) != md5(p):
                    sys.exit(f"Copie altérée : {c}")
                n += 1
        print(f"Regroupement : {n} fichier(s) copiés et vérifiés (MD5) dans {dest}")

    if sys.platform == "darwin" and not a.ne_pas_ouvrir:
        subprocess.run(["open", str(cible)])


if __name__ == "__main__":
    main()
