# Ajout à la skill `forces-et-failles` : reprise d'une série régionale

Deux changements à apporter à la skill, dans le même geste, en suivant ses propres règles de révision (ligne de révision, `_meta.skill_revision` des JSON, § 7 recompté par `scripts/audit-skill.py`) :

1. **Nouveau fichier** `scripts/etat-serie.py` : copier tel quel le script fourni avec ce document.
2. **Nouvelle section** : insérer le texte ci-dessous comme § 8 du SKILL.md, juste avant « 7. RÉFÉRENCES » (renuméroter en conséquence), et ajouter au § 7, rubrique **Outils**, la ligne :
   - `scripts/etat-serie.py` — état d'une série régionale lu sur le disque : fiches écrites (score recalculé depuis le `var DATA` du MASTER, niveau, pièces présentes en `actuel`, date), fiches à écrire (note de départ du cadre), alertes (score non reporté au cadre, version plus récente hors `actuel`, score illisible, MASTER ou PUBLIC manquant). Écrit une page HTML d'état et un résumé texte. Régions : les cinq de l'Union africaine, les cinq sous-régions asiatiques, ou un continent entier. `--regrouper` copie les fiches dans un dossier daté, MD5 vérifié. Usage : `python3 scripts/etat-serie.py ~ --region "Asie du Sud-Est"`.

---

## 8. REPRISE D'UNE SÉRIE RÉGIONALE

**Déclencheur.** L'auteur nomme une région, une sous-région ou un continent avec la série (« Forces et Failles, Asie du Sud-Est », « on continue l'Afrique de l'Ouest », « où en est le Moyen-Orient ? »). Cette section s'applique avant tout le reste : aucune fiche ne s'écrit avant qu'elle ait été déroulée.

**L'auteur ne nomme rien et ne range rien.** Noms de fichiers, révisions du cadre, rangement en `actuel` : la séance s'en charge. L'auteur tranche les notes et choisit le pays ; le reste est mécanique.

**Pourquoi cette section.** Le 26 septembre 2026, le cadre de l'Asie du Sud-Est donnait Singapour à 3,9 alors que sa fiche, écrite dans une autre discussion, était à 3,6 ; cinq fiches sur sept avaient changé depuis le calibrage sans que le cadre suive, et une séance ouverte hors du Projet ne savait rien de la série. Le disque est la seule mémoire commune à toutes les séances : la reprise part donc toujours de lui.

### 8.1 Ouverture de séance, dans cet ordre

1. **Accès au disque.** Si le dossier SAPERE de l'auteur n'est pas relié à la séance, le demander, et ne rien affirmer sur la série avant d'y avoir accès. Ne jamais répondre de mémoire ni depuis le calibrage.
2. **État mesuré.** Lancer `python3 <skill>/scripts/etat-serie.py ~ --region "<région>"` et relayer à l'auteur son résumé : N fiches écrites sur M, la liste des fiches écrites avec leur score, les pays à écrire, les alertes. Donner le chemin de la page d'état (elle s'ouvre seule sur macOS).
3. **Cadre.** Lire la révision la plus récente de `Cadre_FF_<Région>_*.md` (le script la nomme dans son résumé). Son § 2.1 fait foi pour les notes des fiches écrites ; le MASTER de chaque pays prime sur tout ; le calibrage n'est qu'un point de départ pour les pays à écrire. S'il n'existe pas de cadre pour la région, le dire, et le créer au premier arbitrage (§ 8.3).
4. **Alertes d'abord.** Toute alerte du script (score non reporté, version hors `actuel`, pièce manquante) se présente à l'auteur avant de proposer un pays, avec la correction proposée. On ne commence pas une fiche sur une série incohérente.
5. **Proposition.** Proposer le prochain pays à écrire (par défaut le mieux noté au calibrage parmi les pays à écrire, sauf consigne contraire du cadre) et attendre l'accord de l'auteur.

### 8.2 Pendant la séance

La fiche se produit selon les §§ 1 à 6. Les notes de départ sont celles du cadre ; tout changement de note se note au fil de l'eau, avec son motif, pour le report de fin de séance.

### 8.3 Clôture de séance, dans cet ordre

1. **Rangement.** Les livrables finaux vont dans `dossiers/forces-et-failles/[ISO3]/[année]/actuel/` ; la version remplacée part dans `historique/`. Un fichier laissé dans Téléchargements ou dans un dossier de sortie n'est pas livré.
2. **Nouvelle révision du cadre, si une note, un score ou un état a changé.** Elle s'écrit à côté de la précédente, dans `dossiers/forces-et-failles/atelier-<continent>/<année>/<région>/`, sous le nom `Cadre_FF_<Région-avec-tirets>_<AAAA-MM-JJ><lettre>.md` : même jour, lettre suivante (b, c, d…) ; autre jour, nouvelle date sans lettre. Ce modèle garantit que l'ordre alphabétique des noms est l'ordre chronologique. Elle reprend la précédente en entier et y porte : la ligne du pays au § 2.1 (notes lues dans le MASTER, somme recalculée), le motif de chaque note qui s'écarte du calibrage ou d'une règle, l'état au § 6. La révision précédente part dans `archives-cadre/` du même dossier.
3. **Contrôle.** Relancer `etat-serie.py` : la fiche du jour doit apparaître écrite, sans alerte. Relayer le nouveau compte (« 8 fiches sur 11 ») à l'auteur. Une alerte restante se corrige avant de clore, ou se déclare à l'auteur.

> *Le disque est la seule mémoire que toutes les séances partagent. Une décision qui n'y est pas écrite n'a pas été prise.*
