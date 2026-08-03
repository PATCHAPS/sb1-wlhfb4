# SAPERE — Les cinq cercles qui ont fabriqué Macron

Infographie interactive au format **fragment autonome compatible Elementor Pro / WordPress**.

Fichier : [`infographie-cercles-macron-elementor.html`](infographie-cercles-macron-elementor.html)

## Intégration dans Elementor Pro

1. Ouvrez la page dans Elementor et ajoutez un widget **HTML** (ou **Code personnalisé** Elementor Pro, emplacement : corps de page).
2. Collez l'intégralité du fichier dans le widget. Le bloc est autonome : styles, script et chargement des polices Google Fonts sont inclus, aucune modification du `<head>` n'est nécessaire.
3. Publiez. Le bloc fonctionne aussi dans l'aperçu de l'éditeur Elementor et supporte plusieurs instances sur une même page.

## Améliorations de compatibilité Elementor / WordPress

- **Fragment sans `<!DOCTYPE>`, `<html>`, `<head>` ni `<body>`** : le widget HTML d'Elementor injecte le contenu dans la page ; un document complet y provoque un balisage invalide.
- **CSS entièrement scopé sous `.sap-cercles`** avec un bloc de neutralisation des styles de thème (boutons, titres, listes, blockquotes, liens) : l'infographie garde son apparence quel que soit le thème actif (Hello, Astra, OceanWP…).
- **Polices chargées par JavaScript avec déduplication** (`id="sap-fonts"`) : pas de doublon si le widget est présent plusieurs fois ou re-rendu par l'éditeur.
- **Initialisation robuste** : garde `data-sap-init` contre la double liaison des événements, exécution à `DOMContentLoaded` ou immédiate, et ré-initialisation via les hooks `elementorFrontend` (`frontend/element_ready`) pour l'aperçu de l'éditeur.
- **Aucun `id` HTML dupliquable** : les notices du répertoire utilisent `data-node`, les identifiants d'accessibilité du SVG sont générés par instance. Plusieurs copies du widget peuvent coexister sans collision.
- **Styles d'impression** inclus, `prefers-reduced-motion` respecté (transitions et défilements doux désactivés).

## Fonctionnalités ajoutées

- **Filtre par cercle** (graduations 1–5 et clé de la carte) : atténue les nœuds et les blocs du répertoire hors du cercle choisi, **combinable** avec le filtre par fonction.
- **Compteur d'entrées visibles** (« 5 entrées sur 19 ») mis à jour en direct dans la légende.
- **Lien direct fiche → répertoire** : chaque fiche propose « Voir dans le répertoire » qui fait défiler et met en évidence la notice complète.
- **Navigation clavier complète** : Tab, Entrée/Espace pour activer, flèches pour passer d'un nom à l'autre sur la carte, **Échap** pour tout réinitialiser.
- **Comportement tactile amélioré** : sur mobile, le premier appui ouvre la fiche, le second seulement fait défiler vers le répertoire.
- **Indication de glissement intelligente** : le message « Faites glisser la carte » n'apparaît que si la carte déborde réellement de son conteneur.
