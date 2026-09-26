#!/usr/bin/env python3
"""Génère le fragment WordPress « Que propose chacun, thème par thème ? » (SAPERE 2027).

Une seule source de données alimente le tableau (écran large) et les cartes (mobile),
pour que les deux vues ne divergent jamais. Les annonces postérieures à la clôture du
registre sont ajoutées dans des encadrés « Nouveau » sans remplacer la mesure du registre.
"""
import re
from html import escape
from pathlib import Path

REG = "https://sapere.page/campagne-presidentielle-france-2027-analyse-des-programmes/"
LE_MONDE = ("https://www.lemonde.fr/politique/article/2026/09/23/"
            "presidentielle-2027-comment-des-propositions-cles-du-rn-infusent-les-discours-de-la-campagne_6780885_823448.html")

STATUTS = {
    "P1": "Engagement 2027 publié par le candidat ou son parti",
    "P2": "Proposition personnelle récente, tribune, entretien ou discours",
    "P3": "Corpus partisan pour l’échéance en cours",
    "P4": "Corpus antérieur, le plus souvent le programme de 2022",
    "P5": "Source secondaire seulement, presse ou agrégateur",
    "X": "Aucune mesure retrouvée dans le corpus dépouillé",
}

# (slug, nom, parti, image, mesures au registre, largeur de barre, état de la candidature)
CANDIDATS = [
    ("gabriel-attal", "Gabriel Attal", "Renaissance", "ATTALGabrieldessin", 65, 25, ""),
    ("raphael-glucksmann", "Raphaël Glucksmann", "Place publique", "GLUCKSMANGabrieldessin", 134, 52,
     "Primaire sociale-démocrate en octobre"),
    ("marine-le-pen", "Marine Le Pen", "Rassemblement national", "LEPENMarinedessin", 111, 43, ""),
    ("jean-luc-melenchon", "Jean-Luc Mélenchon", "La France insoumise", "MELENCHONJeanlucdessin", 157, 61, ""),
    ("edouard-philippe", "Édouard Philippe", "Horizons", "PHILIPPEEdouarddessin", 87, 34, ""),
    ("bruno-retailleau", "Bruno Retailleau", "Les Républicains", "RETAILLEAUBrunodessin", 104, 40, ""),
    ("marine-tondelier", "Marine Tondelier", "Les Écologistes", "TONDELIERMarinedessin", 259, 100,
     "Candidature soumise au vote interne du 10 au 13 décembre"),
]

VIDE = ("vide", "", "", "", "X", 0)

# Chaque case : (type, ancre du registre, intitulé, chiffre, statut, nombre de mesures).
# type : "" mesure détaillée, "o" orientation générale, "vide" aucune mesure.
THEMES = [
    ("01", "Économie et finances publiques", 114, 100, [
        ("", "diminuer-massivement-les-impots-de-production-et-les-normes", "Diminuer massivement les impôts de production et les normes", "", "P2", 7),
        ("", "taxer-les-mega-heritages-pour-alleger-les-prelevements-sur-l", "Taxer les méga-héritages pour alléger les prélèvements sur les salaires", "15 Md€ attendus, à partir de 2 M€", "P2", 10),
        ("", "inscrire-une-regle-d-or-budgetaire-dans-la-constitution", "Inscrire une règle d’or budgétaire dans la Constitution", "3 % du PIB", "P1", 18),
        ("", "geler-la-dette-francaise-detenue-par-la-banque-centrale-euro", "Geler la dette française détenue par la Banque centrale européenne", "636 Md€, soit 18 % de la dette, selon le candidat", "P2", 23),
        ("", "reduire-les-impots-de-production", "Réduire les impôts de production", "50 Md€", "P2", 6),
        ("", "reduire-de-40-md-le-handicap-fiscal-et-social-des-entrepris", "Réduire de 40 Md€ le handicap fiscal et social des entreprises *", "40 Md€, dont 25 Md€ sur le travail", "P3", 16),
        ("", "instaurer-une-taxe-de-2-sur-les-patrimoines-superieurs-a-1", "Instaurer une taxe de 2 % sur les patrimoines supérieurs à 100 M€", "", "P1", 34),
    ]),
    ("02", "Travail, emploi, retraites et revenus", 86, 75, [
        ("", "introduire-une-part-de-capitalisation-dans-le-systeme-par-re", "Introduire une part de capitalisation dans le système par répartition", "", "P2", 8),
        ("", "revaloriser-le-smic-net", "Porter le SMIC à 1,600 € net en deux ans *", "1,600 € net par mois", "P3", 11),
        ("", "abaisser-l-age-legal-de-depart", "Abaisser l’âge légal de départ à la retraite *", "62 ans, 60 ans pour les carrières longues", "P2", 8),
        ("", "abaisser-l-age-legal-de-depart-en-deux-temps", "Abaisser l’âge légal de départ en deux temps", "62 ans puis 60 ans, 40 annuités", "P2", 16),
        ("", "reduire-la-duree-d-indemnisation-du-chomage", "Réduire la durée d’indemnisation du chômage", "12 mois, contre 18", "P2", 4),
        ("", "sortir-des-35-heures-en-renvoyant-le-temps-de-travail-a-la-n", "Sortir des 35 heures en renvoyant le temps de travail à la négociation collective", "Seuil annuel de 1,623 heures", "P2", 18),
        ("", "porter-le-salaire-minimum-a-2-000-bruts-par-mois-des-2027", "Porter le salaire minimum à 2,000 € bruts par mois dès 2027", "2,000 € brut", "P1", 21),
    ]),
    ("03", "Climat, énergie et environnement", 108, 95, [
        ("", "doubler-les-investissements-dans-la-geothermie", "Doubler les investissements dans la géothermie", "160 M€ par an après doublement", "P2", 5),
        ("", "faire-de-la-sortie-des-energies-fossiles-la-cle-de-voute-du", "Faire de la sortie des énergies fossiles la clé de voûte du quinquennat", "", "P2", 23),
        ("", "reduire-la-tva-sur-l-energie", "Réduire la TVA sur l’énergie", "De 20 % à 5.5 %", "P3", 10),
        ("", "atteindre-un-mix-entierement-renouvelable", "Atteindre un mix électrique entièrement renouvelable et sortir du nucléaire", "100 % renouvelable", "P4", 18),
        ("", "fonds-unique-d-adaptation-fonds-vert-et-fonds-barnier-fusio", "Créer un fonds unique d’adaptation, fusion du Fonds vert et du fonds Barnier *", "2 Md€ par an", "P2", 10),
        ("", "produire-a-minima-600-twh-d-electricite-en-2035", "Produire au moins 600 TWh d’électricité en 2035, avec le nucléaire pour socle *", "600 TWh en 2035", "P3", 12),
        ("", "planifier-la-sortie-du-nucleaire-et-mettre-fin-aux-programme", "Planifier la sortie du nucléaire et mettre fin aux programmes EPR2 et petits réacteurs", "", "P1", 30),
    ]),
    ("04", "Agriculture, alimentation et ruralité", 63, 55, [
        ("", "accompagner-les-exploitants-par-des-plans-et-contrats-d-aven", "Accompagner les exploitants par des contrats d’avenir pour les nouvelles filières et l’adaptation climatique", "", "P2", 2),
        ("", "plafonner-les-aides-a-l-hectare-et-redeployer-les-fonds-vers", "Plafonner les aides à l’hectare et redéployer les fonds vers les petites fermes et les jeunes installés *", "", "P3", 12),
        ("", "interdire-les-importations-de-produits-agricoles-ne-respecta", "Interdire les importations de produits agricoles ne respectant pas les normes françaises *", "", "P4", 7),
        ("", "fixer-des-prix-planchers-agricoles", "Fixer des prix planchers agricoles", "", "P4", 9),
        ("", "creer-des-territoires-de-souverainete-alimentaire", "Créer des territoires de souveraineté alimentaire *", "100 territoires", "P5", 3),
        ("", "relever-de-52-a-100-hectares-le-seuil-de-degressivite-des-ai", "Relever de 52 à 100 hectares le seuil de dégressivité des aides de la politique agricole commune", "52 à 100 hectares", "P3", 6),
        ("", "adopter-des-prix-planchers-agricoles-et-un-affichage-obligat", "Adopter des prix planchers agricoles et un affichage obligatoire du partage de la valeur", "", "P1", 24),
    ]),
    ("05", "Institutions et démocratie", 46, 40, [
        ("", "limiter-a-un-seul-recours-global-les-contestations-d-un-proj", "Limiter à un seul recours global les contestations d’un projet industriel, par révision constitutionnelle", "", "P2", 5),
        ("", "instaurer-immediatement-le-scrutin-proportionnel-aux-legisla", "Instaurer immédiatement le scrutin proportionnel aux élections législatives *", "", "P3", 3),
        ("o", "instaurer-un-referendum-d-initiative-citoyenne", "Instaurer un référendum d’initiative citoyenne", "", "P4", 1),
        ("", "passer-a-une-vie-republique", "Passer à une VIe République par une assemblée constituante", "", "P4", 10),
        ("", "inscrire-une-regle-d-or-budgetaire-dans-la-constitution", "Inscrire une règle d’or budgétaire dans la Constitution *", "", "P5", 2),
        ("", "instaurer-un-bouclier-constitutionnel-contre-les-interpretat", "Instaurer un bouclier constitutionnel contre les interprétations extensives des cours européennes", "", "P1", 6),
        ("", "convoquer-un-processus-constituant-pour-passer-a-une-premier", "Convoquer un processus constituant vers une République écologique et citoyenne", "", "P1", 19),
    ]),
    ("06", "Sécurité, justice, immigration et asile", 107, 94, [
        ("", "instaurer-une-selection-de-l-immigration-par-un-systeme-a-po", "Instaurer une sélection de l’immigration par un système à points", "", "P5", 3),
        ("", "organiser-une-convention-citoyenne-sur-l-immigration", "Organiser une convention citoyenne sur l’immigration", "", "P2", 6),
        ("", "creer-des-postes-de-policiers-et-de-gendarmes", "Créer des postes de policiers et de gendarmes *", "7,000 postes", "P4", 16),
        ("", "retablir-la-police-de-proximite-et-demanteler-les-brigades-a", "Rétablir la police de proximité et démanteler les brigades anticriminalité", "", "P4", 14),
        ("", "creer-un-etat-d-urgence-contre-le-narcotrafic", "Créer un état d’urgence contre le narcotrafic *", "", "P5", 30),
        ("", "supprimer-le-droit-du-sol", "Supprimer le droit du sol", "", "P1", 10),
        ("", "creer-une-police-nationale-de-proximite", "Créer une police nationale de proximité", "", "P1", 28),
    ]),
    ("07", "Défense et industrie d’armement", 33, 29, [
        ("", "rediger-un-nouveau-livre-blanc-de-la-defense-nationale", "Rédiger un nouveau Livre blanc de la défense nationale", "", "P5", 7),
        ("", "augmenter-fortement-la-reserve-operationnelle", "Augmenter fortement la réserve opérationnelle *", "", "P3", 9),
        ("o", "maintenir-une-dissuasion-nucleaire-nationale-independante", "Maintenir une dissuasion nucléaire nationale indépendante", "", "P4", 1),
        ("", "instaurer-une-conscription-citoyenne-de-neuf-mois-et-creer-u", "Instaurer une conscription citoyenne de neuf mois et créer une garde nationale", "", "P4", 3),
        ("", "augmenter-le-nombre-de-reservistes", "Augmenter le nombre de réservistes", "De 45,000 à 250,000", "P5", 5),
        ("", "refuser-tout-partage-toute-concertation-et-tout-elargisseme", "Refuser tout partage, toute concertation et tout élargissement de la dissuasion nucléaire", "", "P2", 3),
        ("", "preparer-l-armee-francaise-a-une-guerre-de-haute-intensite-e", "Préparer l’armée française à une guerre de haute intensité en complémentarité européenne", "", "P1", 5),
    ]),
    ("08", "Europe, diplomatie et coopération", 58, 51, [
        ("", "creer-des-etats-unis-d-europe-autour-d-un-noyau-dur-de-pays", "Créer des États-Unis d’Europe autour d’un noyau dur de pays, par un référendum européen", "Noyau dur de 8 à 10 pays", "P2", 6),
        ("", "reserver-la-commande-publique-de-l-union-aux-productions-eur", "Réserver la commande publique de l’Union aux productions européennes", "2,000 Md€ concernés", "P2", 17),
        ("", "maintenir-la-formation-des-soldats-ukrainiens-et-les-livrais", "Maintenir la formation et le matériel pour l’Ukraine, mais cesser l’aide financière", "", "P2", 3),
        ("", "defendre-une-doctrine-de-non-alignement-militaire", "Défendre une doctrine de non-alignement militaire *", "", "P4", 6),
        ("", "maintenir-le-soutien-a-l-ukraine-face-a-la-russie", "Maintenir le soutien à l’Ukraine face à la Russie", "", "P2", 3),
        ("", "reserver-la-libre-circulation-dans-l-espace-schengen-aux-eur", "Réserver la libre circulation dans l’espace Schengen aux Européens", "", "P2", 5),
        ("", "porter-le-budget-de-l-union-a-2-du-pib-europeen-en-2035-et", "Porter le budget de l’Union à 2 % du PIB européen en 2035 et 5 % en 2050", "", "P1", 18),
    ]),
    ("09", "Éducation et jeunesse", 60, 53, [
        ("", "fermer-les-100-colleges-concentrant-les-plus-fortes-difficul", "Fermer les 100 collèges concentrant les plus fortes difficultés et répartir leurs élèves", "100 collèges", "P2", 9),
        ("", "revaloriser-la-remuneration-des-enseignants", "Revaloriser la rémunération des enseignants", "De 10 % à 25 %", "P2", 9),
        ("", "sanctuariser-les-etablissements-scolaires-et-mettre-fin-a-la", "Sanctuariser les établissements scolaires et mettre fin à la doctrine disciplinaire actuelle", "", "P4", 3),
        ("", "creer-un-service-public-de-la-petite-enfance", "Créer un service public de la petite enfance", "500,000 places", "P4", 10),
        ("", "revaloriser-la-remuneration-moyenne-des-enseignants", "Revaloriser la rémunération moyenne des enseignants", "+ 20 %", "P2", 7),
        ("", "ecarter-l-usage-de-l-intelligence-artificielle-par-l-eleve-a", "Écarter l’usage de l’intelligence artificielle par l’élève avant le lycée", "", "P2", 4),
        ("", "abroger-le-choc-des-savoirs-et-les-groupes-de-niveaux-en-six", "Abroger le choc des savoirs et les groupes de niveau en sixième et cinquième", "", "P1", 18),
    ]),
    ("10", "Enseignement supérieur et recherche", 28, 25, [
        ("", "former-toute-la-population-a-l-ia-du-primaire-a-la-reconver", "Former toute la population à l’intelligence artificielle, du primaire à la reconversion", "", "P5", 2),
        ("", "doubler-le-budget-de-la-recherche-europeenne", "Doubler le budget de la recherche européenne *", "Budget doublé", "P3", 7),
        ("", "augmenter-les-frais-de-scolarite-des-etudiants-etrangers-ho", "Augmenter les frais de scolarité des étudiants étrangers, hors conventions", "", "P3", 2),
        ("", "demanteler-parcoursup-et-garantir-l-acces-sans-selection-a-l", "Démanteler Parcoursup et garantir l’accès sans sélection à la formation choisie", "", "P4", 8),
        ("", "augmenter-le-nombre-annuel-d-ingenieurs-formes", "Augmenter le nombre annuel d’ingénieurs formés", "De 40,000 à 100,000 par an", "P5", 2),
        ("", "revoir-la-carte-des-formations-universitaires-et-leurs-finan", "Revoir la carte des formations universitaires et leurs financements selon les débouchés", "", "P2", 1),
        ("", "remplacer-parcoursup-et-monmaster-par-une-plateforme-d-orien", "Remplacer Parcoursup et MonMaster par une plateforme d’orientation transparente", "", "P1", 6),
    ]),
    ("11", "Santé et protection sociale", 66, 58, [
        ("", "defiscaliser-les-pensions-alimentaires-recues-pour-les-enfan", "Défiscaliser les pensions alimentaires reçues pour les enfants", "", "P2", 5),
        ("", "demarchandiser-les-creches", "Démarchandiser les crèches et les EHPAD", "", "P2", 2),
        ("", "transformer-l-aide-medicale-de-l-etat-en-dispositif-limite-a", "Transformer l’aide médicale de l’État en dispositif limité aux soins urgents", "", "P3", 15),
        ("", "creer-une-securite-sociale-integrale-geree-par-ses-cotisants", "Créer une Sécurité sociale intégrale gérée par ses cotisants", "", "P2", 12),
        ("", "mettre-fin-a-ce-qu-il-qualifie-d-open-bar-des-arrets-de", "Mettre fin à ce qu’il qualifie d’« open bar » des arrêts de travail", "", "P2", 6),
        ("", "instaurer-un-revenu-familial-de-240-par-mois-et-par-enfant", "Instaurer un Revenu familial par enfant", "240 € par mois et par enfant", "P3", 5),
        ("", "autoriser-une-fin-de-vie-choisie-et-assistee", "Autoriser une fin de vie choisie et assistée", "", "P1", 21),
    ]),
    ("12", "Collectivités et cohésion territoriale", 18, 16, [
        ("o", "faire-participer-les-collectivites-a-l-effort-budgetaire", "Faire participer les collectivités à l’effort budgétaire", "", "P5", 1),
        ("", "creer-un-contrat-de-souverainete-clarifiant-les-competences", "Créer un contrat de souveraineté clarifiant les compétences entre l’Union, l’État et les collectivités *", "", "P3", 2),
        ("", "reduire-de-5-md-les-transferts-de-l-etat-aux-regions-et-aux", "Réduire de 5 Md€ les transferts de l’État aux régions et aux intercommunalités", "5 Md€", "P3", 2),
        ("", "restructurer-les-regions-autour-des-grands-bassins-versants", "Restructurer les régions autour des grands bassins versants des fleuves", "", "P2", 4),
        ("", "decentraliser-la-politique-d-adaptation-au-changement-climat", "Décentraliser la politique d’adaptation au changement climatique", "", "P2", 1),
        ("", "reduire-les-transferts-de-l-etat-aux-collectivites", "Réduire les transferts de l’État aux collectivités", "", "P5", 1),
        ("", "garantir-un-accueil-physique-des-services-publics-a-quinze-m", "Garantir un accueil physique des services publics à quinze minutes partout en France", "", "P1", 7),
    ]),
    ("13", "Logement et urbanisme", 43, 38, [
        ("o", "engager-une-renovation-thermique-massive", "Engager une rénovation thermique massive", "", "P5", 1),
        ("", "developper-les-logements-en-bail-reel-solidaire-pour-en-fair", "Développer les logements en bail réel solidaire pour en faire une offre de masse", "", "P3", 5),
        ("", "abroger-la-loi-relative-a-la-solidarite-et-au-renouvellement", "Abroger la loi relative à la solidarité et au renouvellement urbains (SRU)", "", "P3", 11),
        ("", "construire-des-logements-publics", "Construire des logements publics", "200,000 par an", "P4", 8),
        ("", "adapter-les-batiments-aux-canicules", "Adapter les bâtiments aux canicules : climatisation et réseaux de froid", "", "P2", 2),
        ("", "faire-passer-les-travailleurs-en-premier-pour-l-attribution", "Faire passer les travailleurs en premier pour l’attribution des logements sociaux", "", "P2", 9),
        ("", "utiliser-le-droit-de-requisition-contre-les-logements-vacant", "Utiliser le droit de réquisition contre les logements vacants", "", "P1", 7),
    ]),
    ("14", "Outre-mer", 19, 17, [
        VIDE,
        ("", "adapter-les-transports-aux-specificites-ultramarines", "Adapter les transports aux spécificités ultramarines", "", "P3", 1),
        ("", "augmenter-de-700-m-le-budget-de-la-mission-outre-mer-pour-l", "Augmenter le budget de la mission Outre-mer pour les infrastructures", "+ 700 M€", "P3", 4),
        ("", "accompagner-la-nouvelle-caledonie-kanaky-vers-l-independance", "Accompagner la Nouvelle-Calédonie-Kanaky vers l’indépendance", "", "P2", 6),
        ("", "supprimer-le-droit-du-sol-a-mayotte", "Supprimer le droit du sol à Mayotte", "", "P5", 3),
        VIDE,
        ("", "combattre-la-vie-chere-outre-mer-par-les-regles-anti-trust-e", "Combattre la vie chère outre-mer par les règles anti-trust et le contrôle des marges", "", "P1", 5),
    ]),
    ("15", "Culture, médias et information", 30, 26, [
        ("", "fixer-un-age-minimal-d-acces-aux-reseaux-sociaux", "Fixer un âge minimal d’accès aux réseaux sociaux", "15 ans", "P2", 1),
        ("", "tenir-l-objectif-de-1-du-budget-de-l-etat-consacre-a-la-cu", "Tenir l’objectif de 1 % du budget de l’État consacré à la culture *", "1 % du budget de l’État", "P3", 6),
        ("", "creer-un-service-national-du-patrimoine", "Créer un service national du patrimoine", "6 mois, 18-24 ans", "P4", 5),
        ("", "demembrer-par-une-loi-de-debut-de-mandat-les-trusts-mediatiq", "Démembrer par une loi de début de mandat les trusts médiatiques et culturels", "", "P2", 8),
        VIDE,
        VIDE,
        ("", "garantir-la-liberte-de-creation-et-limiter-la-concentration", "Garantir la liberté de création et limiter la concentration des industries culturelles", "", "P1", 10),
    ]),
    ("16", "Numérique, données, IA et cybersécurité", 38, 33, [
        ("", "introduire-une-preference-europeenne-dans-les-marches-public", "Introduire une préférence européenne dans les marchés publics technologiques", "", "P5", 3),
        ("", "appliquer-fermement-aux-grandes-plateformes-les-regles-europ", "Appliquer fermement aux grandes plateformes les règles européennes existantes", "", "P2", 11),
        ("", "taxer-l-utilisation-du-reseau-par-les-geants-du-numerique", "Taxer l’utilisation du réseau par les géants du numérique", "", "P3", 5),
        ("", "developper-les-logiciels-libres-dans-les-administrations", "Développer les logiciels libres dans les administrations", "", "P4", 2),
        ("", "adopter-un-buy-european-tech-act", "Adopter un Buy European Tech Act", "", "P5", 3),
        ("", "porter-les-capacites-de-centres-de-donnees-a-1-gw-en-2030-p", "Porter les capacités de centres de données à 1 GW en 2030, puis à 4 GW en 2035", "1 GW en 2030, 4 GW en 2035", "P2", 8),
        ("", "encadrer-l-implantation-des-centres-de-donnees-et-planifier", "Encadrer l’implantation des centres de données et planifier leur consommation électrique", "", "P1", 6),
    ]),
]

# Annonces du 18 au 25 septembre 2026, pas encore versées au registre (clôture au 19 septembre).
# Clé : (numéro de thème, slug du candidat). Valeur : (intitulé, chiffre, statut, source et date).
# Sources : briques SAPERE de la base du 25 septembre (numéros entre parenthèses) et Le Monde du 23 septembre.
NOUVEAUTES = {
    ("01", "gabriel-attal"): (
        "Réaliser 150 Md€ d’économies en cinq ans et ramener le déficit sous 3 % en 2032",
        "Deux tiers sur les dépenses sociales, 100,000 postes publics en moins", "P2",
        "Plan du 23 sept., Le Figaro du 24 sept. (brique 41677)"),
    ("02", "gabriel-attal"): (
        "Supprimer l’âge légal au profit de la seule durée de cotisation", "", "P5",
        "Le Figaro, 24 sept. (brique 41704)"),
    ("02", "jean-luc-melenchon"): (
        "Augmenter le point d’indice de 10 % et titulariser les contractuels", "+ 10 %", "P3",
        "Ouvrage collectif du 4 sept., Le Monde du 23 sept. (brique 41227)"),
    ("02", "bruno-retailleau"): (
        "Ouvrir les droits à 63 ans, taux plein à 65 ans, pilier de capitalisation obligatoire",
        "Décote de 7 % par an ; 40 Md€ sur cinq ans selon le candidat", "P2",
        "LCI, 22 sept. ; Le Figaro et L’Opinion, 24 sept. (briques 41704, 41587)"),
    ("03", "gabriel-attal"): (
        "Construire quatre réacteurs par an et garantir aux industriels une électricité sous 50 €/MWh",
        "Fossiles importés ramenés de 60 % à 40 % en 2030", "P2",
        "Plan énergie du 23 sept., La Tribune du 25 sept. (brique 41630)"),
    ("03", "raphael-glucksmann"): (
        "Tripler le chèque énergie plutôt qu’une aide générale aux carburants", "", "P2",
        "Débat de la primaire, LCI, 23 sept. (brique 41776)"),
    ("03", "marine-le-pen"): (
        "Affecter au budget de l’État le produit des certificats d’économies d’énergie", "", "P3",
        "Le Monde, 23 sept."),
    ("03", "edouard-philippe"): (
        "Doubler les aides ciblées aux carburants, gagées par 7,000 non-recrutements de fonctionnaires", "", "P2",
        "L’Opinion, 25 sept. (brique 41591)"),
    ("03", "bruno-retailleau"): (
        "Supprimer les certificats d’économies d’énergie",
        "15 à 19 centimes par litre selon l’industrie pétrolière", "P3",
        "Proposition LR depuis avril, Le Monde du 23 sept."),
    ("08", "marine-le-pen"): (
        "Ne quitter le commandement intégré de l’OTAN qu’après la fin de la guerre en Ukraine",
        "En mai : sortie dès le premier mandat", "P5",
        "Entretien à Politico, 24 sept., connu par une compilation (brique 41550)"),
}

BOUGE = [
    ("Trois chiffres ronds, aucune ventilation.",
     "Gabriel Attal promet 150 Md€ d’économies en cinq ans, Bruno Retailleau chiffre sa réforme des retraites "
     "à 40 Md€ sur cinq ans, Marine Le Pen annonce un contre-budget pour début octobre. Aucun ne détaille encore "
     "ses économies poste par poste."),
    ("La pompe fait campagne.",
     "Le gazole bat son record le 22 septembre, à 2.41 € le litre, et chacun choisit son instrument : TVA à 5.5 % "
     "(Marine Le Pen), suppression des certificats d’économies d’énergie (Bruno Retailleau), aides ciblées doublées "
     "(Édouard Philippe), chèque énergie triplé (Raphaël Glucksmann), nucléaire plutôt qu’aides (Gabriel Attal)."),
    ("L’original et la copie.",
     "Selon <a href=\"" + LE_MONDE + "\">Le Monde</a> du 23 septembre, trois pistes d’économies longtemps portées "
     "par le seul RN (contribution européenne, aides aux étrangers, soutiens à l’énergie) gagnent le budget de "
     "Sébastien Lecornu et d’autres camps : droit du sol et asile suspendus à Mayotte chez Édouard Philippe, "
     "certificats d’économies d’énergie supprimés chez Bruno Retailleau. Leur rendement reste mince : sur la carence "
     "imposée aux étrangers, un député RN admet lui-même que « cela ne rapporte rien »."),
    ("Le RN retouche sa ligne étrangère.",
     "Marine Le Pen ne quitterait plus le commandement intégré de l’OTAN avant la fin de la guerre en Ukraine, et "
     "le Kremlin désavoue publiquement une mise en garde du parti contre les pressions russes, une première."),
    ("À gauche, deux calendriers.",
     "La primaire sociale-démocrate se tient en octobre, avec Raphaël Glucksmann pour favori ; les écologistes "
     "trancheront du 10 au 13 décembre entre la candidature de Marine Tondelier et un ralliement."),
]

CSS = r"""#sapere2027-synthese-v1{--ink:#111820;--paper:#fff;--line:#d8d5cc;--mute:#66717b;--red:#c91e35;--neuf:#fbf5ee;
 --p1:#3e8f7c;--p2:#9fd0c1;--p3:#d9b75a;--p4:#efdfa9;--p5:#6e7b86;--px:#dfe3e6;
 max-width:1180px;margin:0 auto;font-family:Inter,Arial,Helvetica,sans-serif!important;color:var(--ink);background:var(--paper);line-height:1.4}
#sapere2027-synthese-v1 *{box-sizing:border-box}
#sapere2027-synthese-v1 h2,#sapere2027-synthese-v1 h3,#sapere2027-synthese-v1 .ss-titre,#sapere2027-synthese-v1 .ss-theme,#sapere2027-synthese-v1 .ss-m,#sapere2027-synthese-v1 .ss-c,#sapere2027-synthese-v1 .ss-cand b,#sapere2027-synthese-v1 .ss-cand i,#sapere2027-synthese-v1 .ss-ligne b,#sapere2027-synthese-v1 .ss-chapo,#sapere2027-synthese-v1 .ss-foot,#sapere2027-synthese-v1 .ss-bouge,#sapere2027-synthese-v1 .ss-neuf-tag{text-transform:none!important;letter-spacing:normal}
#sapere2027-synthese-v1 a,#sapere2027-synthese-v1 a *,#sapere2027-synthese-v1 button{font-family:inherit!important}
#sapere2027-synthese-v1 h2.ss-titre{letter-spacing:-.02em!important}
#sapere2027-synthese-v1 .ss-head{padding:0 0 18px;border-bottom:2px solid var(--ink);margin-bottom:18px}
#sapere2027-synthese-v1 .ss-eyebrow{display:block;color:var(--red);font-size:11px;font-weight:900;letter-spacing:.16em;text-transform:uppercase;margin-bottom:10px}
#sapere2027-synthese-v1 h2.ss-titre{margin:0 0 12px;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-weight:700;font-size:clamp(30px,4vw,46px);line-height:1;letter-spacing:-.02em;color:var(--ink)!important;text-wrap:balance}
#sapere2027-synthese-v1 .ss-chapo{max-width:70ch;margin:0;font-size:15px;color:#2a333b}
#sapere2027-synthese-v1 .ss-chapo+.ss-chapo{margin-top:8px}
#sapere2027-synthese-v1 ul.ss-legende{display:flex!important;flex-wrap:wrap;gap:8px 18px;margin:16px 0 0!important;padding:0!important;list-style:none!important;font-size:12px!important;line-height:1.3!important;color:var(--mute)}
#sapere2027-synthese-v1 ul.ss-legende li{display:flex!important;align-items:center;gap:6px;margin:0!important;padding:0!important;font-size:12px!important;line-height:1.3!important;font-family:Inter,Arial,Helvetica,sans-serif!important;color:var(--mute)!important;list-style:none!important}
#sapere2027-synthese-v1 ul.ss-legende li:before,#sapere2027-synthese-v1 ul.ss-legende li:after{content:none!important}
#sapere2027-synthese-v1 .ss-chip{font-size:12px!important;line-height:16px!important;padding:1px 6px!important;margin:0!important}
#sapere2027-synthese-v1 .ss-chip{display:inline-block;min-width:26px;padding:1px 6px;border-radius:2px;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-weight:700;font-size:12px;line-height:16px;text-align:center;letter-spacing:.02em}
#sapere2027-synthese-v1 .ss-P1{background:var(--p1);color:#fff} #sapere2027-synthese-v1 .ss-P2{background:var(--p2);color:var(--ink)}
#sapere2027-synthese-v1 .ss-P3{background:var(--p3);color:var(--ink)} #sapere2027-synthese-v1 .ss-P4{background:var(--p4);color:var(--ink)}
#sapere2027-synthese-v1 .ss-P5{background:var(--p5);color:#fff} #sapere2027-synthese-v1 .ss-X{background:var(--px);color:var(--mute)}
#sapere2027-synthese-v1 .ss-NEUF{background:var(--neuf);color:var(--red);box-shadow:inset 3px 0 0 var(--red)}
#sapere2027-synthese-v1 .ss-bouge{margin:0 0 22px;padding:16px 18px 6px;background:var(--neuf);border-left:4px solid var(--red)}
#sapere2027-synthese-v1 .ss-bouge h3{margin:0 0 10px!important;padding:0!important;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-weight:700;font-size:22px!important;line-height:1.1!important;color:var(--ink)!important}
#sapere2027-synthese-v1 ol.ss-bouge-l{margin:0!important;padding:0!important;list-style:none!important;counter-reset:ssb}
#sapere2027-synthese-v1 ol.ss-bouge-l li{position:relative;margin:0 0 10px!important;padding:0 0 0 28px!important;font-size:14px!important;line-height:1.45!important;color:#2a333b!important;list-style:none!important;max-width:95ch}
#sapere2027-synthese-v1 ol.ss-bouge-l li:before{counter-increment:ssb;content:counter(ssb,decimal-leading-zero)!important;position:absolute;left:0;top:1px;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-weight:700;font-size:14px;color:var(--red)}
#sapere2027-synthese-v1 ol.ss-bouge-l li:after{content:none!important}
#sapere2027-synthese-v1 ol.ss-bouge-l b{color:var(--ink)}
#sapere2027-synthese-v1 .ss-bouge a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--red);text-underline-offset:2px}
#sapere2027-synthese-v1 .ss-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
#sapere2027-synthese-v1 table.ss-t{width:100%;min-width:1040px;border-collapse:separate;border-spacing:0;table-layout:fixed;font-size:13px}
#sapere2027-synthese-v1 table.ss-t th,#sapere2027-synthese-v1 table.ss-t td{padding:0;vertical-align:top;font-family:inherit;font-size:inherit;text-align:left;border:0}
#sapere2027-synthese-v1 table.ss-t thead th{position:sticky;top:0;z-index:2;background:var(--paper);border-bottom:1px solid var(--ink);padding:0 8px 10px}
#sapere2027-synthese-v1 table.ss-t thead th:first-child{width:150px}
#sapere2027-synthese-v1 .ss-cand{display:flex;flex-direction:column;align-items:flex-start;gap:6px}
#sapere2027-synthese-v1 .ss-cand img{width:44px;height:44px;border-radius:50%;object-fit:cover;object-position:top center;background:#eef1f5}
#sapere2027-synthese-v1 .ss-cand b{display:block;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-weight:700;font-size:16px;line-height:1.05;letter-spacing:-.01em}
#sapere2027-synthese-v1 .ss-cand i{display:block;font-style:italic;font-size:11px;color:var(--mute)}
#sapere2027-synthese-v1 .ss-cand small{display:block;font-size:10px;color:var(--mute);letter-spacing:.04em;text-transform:uppercase}
#sapere2027-synthese-v1 .ss-etat{display:block;font-size:10.5px;line-height:1.25;font-weight:600;color:var(--red)}
#sapere2027-synthese-v1 .ss-barre{display:block;height:6px;width:100%;background:#eef0f2;margin-top:2px}
#sapere2027-synthese-v1 .ss-barre i{display:block;height:100%;background:var(--ink)}
#sapere2027-synthese-v1 table.ss-t tbody th{padding:12px 10px 12px 0;border-bottom:1px solid var(--line);vertical-align:top}
#sapere2027-synthese-v1 table.ss-t tbody td{padding:12px 8px;border-bottom:1px solid var(--line);border-left:1px solid #edebe4}
#sapere2027-synthese-v1 .ss-num{display:block;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-weight:700;font-size:26px;line-height:.9;color:var(--red);letter-spacing:-.02em}
#sapere2027-synthese-v1 .ss-theme{display:block;margin-top:6px;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-weight:700;font-size:15px;line-height:1.1;text-wrap:balance}
#sapere2027-synthese-v1 .ss-tot{display:block;margin-top:6px;font-size:11px;color:var(--mute)}
#sapere2027-synthese-v1 .ss-m{display:block;margin:0;font-weight:500;line-height:1.35;text-wrap:pretty}
#sapere2027-synthese-v1 a.ss-lien{color:var(--ink);text-decoration:underline;text-decoration-color:#b9c2c9;text-decoration-thickness:1px;text-underline-offset:3px;transition:text-decoration-color .15s}
#sapere2027-synthese-v1 a.ss-lien:hover,#sapere2027-synthese-v1 a.ss-lien:focus-visible{text-decoration-color:var(--red);color:var(--ink)}
#sapere2027-synthese-v1 a.ss-lien:focus-visible{outline:2px solid var(--red);outline-offset:2px}
#sapere2027-synthese-v1 a.ss-lien:after{content:" ↗";font-size:.8em;color:var(--red)}
#sapere2027-synthese-v1 .ss-o .ss-m{font-style:italic;color:#3d4750}
#sapere2027-synthese-v1 .ss-c{display:block;margin-top:6px;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-weight:700;font-size:15px;line-height:1.1;color:var(--ink)}
#sapere2027-synthese-v1 .ss-pied{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-top:10px;font-size:10.5px!important;line-height:1.3!important;color:var(--mute);white-space:nowrap}
#sapere2027-synthese-v1 .ss-pied span{font-size:inherit!important}
#sapere2027-synthese-v1 .ss-neuf{display:block;margin-top:10px;padding:8px 8px 7px 9px;background:var(--neuf);border-left:3px solid var(--red)}
#sapere2027-synthese-v1 .ss-neuf-tag{display:block;margin-bottom:4px;font-size:9.5px!important;font-weight:800;letter-spacing:.12em!important;text-transform:uppercase!important;color:var(--red)}
#sapere2027-synthese-v1 .ss-neuf .ss-m{font-weight:600;color:var(--ink)}
#sapere2027-synthese-v1 .ss-neuf .ss-c{font-size:13.5px}
#sapere2027-synthese-v1 .ss-neuf-src{display:flex;align-items:flex-start;gap:6px;margin-top:6px;font-size:10.5px!important;line-height:1.3!important;color:var(--mute)}
#sapere2027-synthese-v1 .ss-neuf-src .ss-chip{flex:none}
#sapere2027-synthese-v1 td.ss-vide{background:#fafaf8} #sapere2027-synthese-v1 td.ss-vide .ss-m{color:var(--mute);font-style:italic}
#sapere2027-synthese-v1 .ss-cartes{display:none}
#sapere2027-synthese-v1 .ss-foot{margin-top:18px;padding-top:12px;border-top:1px solid var(--line);font-size:12px;color:var(--mute);max-width:80ch}
#sapere2027-synthese-v1 .ss-foot p{margin:0 0 8px}
#sapere2027-synthese-v1 .ss-foot a,#sapere2027-synthese-v1 .ss-chapo a{color:var(--ink);text-decoration:underline;text-underline-offset:2px}
#sapere2027-synthese-v1 .ss-cta{display:inline-block;margin-top:10px;font-weight:700;color:var(--ink)}
@media(max-width:900px){
 #sapere2027-synthese-v1 .ss-scroll{display:none} #sapere2027-synthese-v1 .ss-cartes{display:block}
 #sapere2027-synthese-v1 .ss-carte{padding:14px 0;border-bottom:1px solid var(--ink)}
 #sapere2027-synthese-v1 .ss-carte header{display:flex;align-items:baseline;gap:10px;margin-bottom:10px}
 #sapere2027-synthese-v1 .ss-carte .ss-theme{margin:0;font-size:20px}
 #sapere2027-synthese-v1 .ss-ligne{display:grid;grid-template-columns:40px 1fr;gap:10px;padding:8px 0;border-top:1px solid var(--line);align-items:start}
 #sapere2027-synthese-v1 .ss-ligne img{width:40px;height:40px;border-radius:50%;object-fit:cover;object-position:top center;background:#eef1f5}
 #sapere2027-synthese-v1 .ss-ligne b{display:block;font-family:"Barlow Semi Condensed","Arial Narrow",Arial,sans-serif!important;font-size:15px;line-height:1.1}
 #sapere2027-synthese-v1 .ss-ligne .ss-c{font-size:14px}
 #sapere2027-synthese-v1 .ss-bouge{padding:14px 14px 4px}
}
@media(prefers-reduced-motion:reduce){#sapere2027-synthese-v1 *{transition:none}}"""


def chip(st):
    return f'<span class="ss-chip ss-{st}" title="{STATUTS[st]}">{st}</span>'


def compte(n):
    return f"{n} mesure" if n <= 1 else f"{n} mesures"


def img(cand, taille):
    return (f'<img src="https://sapere.page/wp-content/uploads/2026/09/{cand[3]}.webp" '
            f'alt="" width="{taille}" height="{taille}" />')


def contenu(case, cand_slug):
    kind, cle, titre, c, st, n = case
    if kind == "vide":
        return (f'<span class="ss-m">Aucune mesure retrouvée dans le corpus dépouillé.</span>'
                f'<span class="ss-pied">{chip("X")}0 mesure</span>')
    libelle = ("Orientation générale : " if kind == "o" else "") + titre
    h = (f'<span class="ss-m"><a class="ss-lien" title="Ouvrir la fiche de cette mesure dans le registre" '
         f'href="{REG}#m-{cle}--p-{cand_slug}">{escape(libelle, quote=False)}</a></span>')
    if c:
        h += f'<span class="ss-c">{escape(c, quote=False)}</span>'
    return h + f'<span class="ss-pied">{chip(st)}{compte(n)}</span>'


def neuf(num, cand_slug):
    n = NOUVEAUTES.get((num, cand_slug))
    if not n:
        return ""
    titre, c, st, src = n
    src = re.sub(r" \(briques? [^)]*\)", "", src)  # numéros de briques : traçabilité interne, pas d'affichage public
    h = ('<span class="ss-neuf"><span class="ss-neuf-tag">Nouveau</span>'
         f'<span class="ss-m">{escape(titre, quote=False)}</span>')
    if c:
        h += f'<span class="ss-c">{escape(c, quote=False)}</span>'
    return h + f'<span class="ss-neuf-src">{chip(st)}<span>{escape(src, quote=False)}</span></span></span>'


def classe(case):
    return {"o": ' class="ss-o"', "vide": ' class="ss-vide"'}.get(case[0], "")


def generer():
    o = ['<!-- wp:html -->', '<div id="sapere2027-synthese-v1"><style>', CSS, '</style>']
    o.append('<header class="ss-head"><span class="ss-eyebrow">SAPERE · Présidentielle 2027 · Synthèse du registre · '
             'Mise à jour du 26 septembre 2026</span>')
    o.append('<h2 class="ss-titre">Que propose chacun, thème par thème ?</h2>')
    o.append(f'<p class="ss-chapo">Seize thématiques, sept candidats, une mesure par case : ce tableau condense les 922 '
             f'mesures du <a href="{REG}">Registre SAPERE des engagements 2027</a>. Chaque case donne la proposition la '
             'mieux établie du candidat sur le thème, son chiffre lorsqu’il en a publié un, et son statut documentaire, '
             'de P1, engagement 2027 publié, à P5, source secondaire. Chaque mesure est cliquable et ouvre sa fiche '
             'complète dans le registre : arguments, objections, état du droit et sources.</p>')
    o.append('<p class="ss-chapo">Une semaine de campagne a suffi à faire bouger dix cases. Les annonces du 18 au 25 '
             'septembre apparaissent dans des encadrés rouges marqués « Nouveau » : elles s’ajoutent à la mesure du '
             'registre sans la remplacer, tant qu’elles n’y ont pas été versées et argumentées.</p>')
    o.append('<ul class="ss-legende">')
    for st, lib in STATUTS.items():
        o.append(f'<li>{chip(st)} {lib}</li>')
    o.append('<li><span class="ss-chip ss-NEUF" title="Annonce du 18 au 25 septembre, pas encore versée au registre">'
             'Nouveau</span> Annonce du 18 au 25 septembre, pas encore versée au registre</li>')
    o.append('</ul>\n</header>')

    o.append('<section class="ss-bouge" aria-labelledby="ss-bouge-titre">'
             '<h3 id="ss-bouge-titre">Ce qui a bougé du 18 au 25 septembre</h3><ol class="ss-bouge-l">')
    for titre, texte in BOUGE:
        o.append(f'<li><b>{titre}</b> {texte}</li>')
    o.append('</ol></section>')

    # Vue tableau (écran large)
    o.append('<div class="ss-scroll">\n<table class="ss-t">\n<thead>\n<tr>')
    o.append('<th scope="col"><span class="ss-cand"><small>Thématique</small></span></th>')
    for cand in CANDIDATS:
        etat = f'<span class="ss-etat">{cand[6]}</span>' if cand[6] else ""
        o.append(f'<th scope="col"><span class="ss-cand">{img(cand, 44)}<b>{cand[1]}</b><i>{cand[2]}</i>'
                 f'<small>{cand[4]} mesures au registre</small><span class="ss-barre"><i style="width:{cand[5]}%"></i>'
                 f'</span>{etat}</span></th>')
    o.append('</tr>\n</thead>\n<tbody>')
    for num, nom, tot, barre, cases in THEMES:
        o.append(f'<tr>\n<th scope="row"><span class="ss-num">{num}</span><span class="ss-theme">{escape(nom, quote=False)}</span>'
                 f'<span class="ss-tot">{tot} mesures</span><span class="ss-barre"><i style="width:{barre}%"></i></span></th>')
        for cand, case in zip(CANDIDATS, cases):
            o.append(f'<td{classe(case)}>{contenu(case, cand[0])}{neuf(num, cand[0])}</td>')
        o.append('</tr>')
    o.append('</tbody>\n</table>\n</div>')

    # Vue cartes (mobile)
    o.append('<div class="ss-cartes">')
    for num, nom, tot, barre, cases in THEMES:
        o.append(f'<section class="ss-carte"><header><span class="ss-num">{num}</span>'
                 f'<span class="ss-theme">{escape(nom, quote=False)}</span></header>')
        for cand, case in zip(CANDIDATS, cases):
            o.append(f'<div class="ss-ligne">{img(cand, 40)}\n<div><b>{cand[1]}</b>\n'
                     f'<div{classe(case)}>{contenu(case, cand[0])}{neuf(num, cand[0])}</div>\n</div>\n</div>')
        o.append('</section>')
    o.append('</div>')

    etoiles = sum(case[2].endswith("*") for *_, cases in THEMES for case in cases)
    o.append('<footer class="ss-foot">')
    o.append(f'<p><strong>Règle de sélection.</strong> Dans chaque case, la mesure au statut documentaire le plus fort ; '
             f'à statut égal, la plus structurante du programme sur le thème. {etoiles} cases, marquées d’un astérisque, '
             'retiennent une mesure à statut plus faible parce qu’elle est plus structurante dans son programme. Les cases '
             'en italique signalent une orientation générale sans mesure détaillée. Le nombre de mesures sous chaque case '
             'rappelle qu’une case ne résume pas un programme.</p>')
    o.append(f'<p><strong>Annonces nouvelles.</strong> Les {len(NOUVEAUTES)} encadrés « Nouveau » proviennent des briques '
             'SAPERE du 18 au 25 septembre 2026 et de l’analyse du Monde du 23 septembre (Clément Guillou). Leur statut '
             'documentaire est provisoire : il sera confirmé, et le choix de la case éventuellement revu, lorsqu’elles '
             'seront versées au registre. Une annonce connue par une seule compilation de presse est classée P5.</p>')
    o.append(f'<p><strong>Source.</strong> Registre SAPERE des engagements 2027, clôture documentaire au 19 septembre 2026, '
             'complété par les annonces du 18 au 25 septembre. Chaque mesure du registre y est argumentée, sourcée et '
             'datée ; le tableau n’ajoute aucune information au registre, il en extrait une, et signale à part ce qui '
             f'n’y figure pas encore. Synthèse version 1.9. Infographie SAPERE. <a class="ss-cta" href="{REG}">'
             'Ouvrir le registre complet ↗</a></p>')
    o.append('</footer></div>\n<!-- /wp:html -->')
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    sortie = Path(__file__).with_name("synthese-thematique-v1.9-2026-09-26.html")
    sortie.write_text(generer(), encoding="utf-8")
    print(sortie)
