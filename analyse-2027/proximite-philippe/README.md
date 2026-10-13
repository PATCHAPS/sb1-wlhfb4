# Simulation de proximité avec Édouard Philippe (travail interne, non publié)

État au 13 octobre 2026, registre v4.28.

- `grille.md` : 64 questions sur 16 thèmes, ancres −2 / 0 / +2 (version validée).
- `codes_<candidat>.json` : position de chaque candidat par question, avec la ou les mesures du registre qui la fondent (`null` = non comparable).
- `codes_philippe.json` : codes actuellement utilisés pour Philippe.
- `codes_philippe_registre.json` : 35 codes fondés sur le registre v4.28.
- `codes_philippe_simul.json` : variante avec 5 positions en attente d'entrée au registre (nucléaire, renouvelables, taxe Zucman, Bougival, audiovisuel public).
- `score2.py` : calcul. Proximité = 1 − moyenne des |C − P| / 4 sur toutes les questions codées chez les deux candidats, sans pondération ; détail par thème affiché si au moins deux questions sont comparables.
- `scores_v2.json` : derniers résultats.

Règles : un code ne repose que sur une mesure du registre ; une mesure ne sert qu'à une question ; les positions de parti comptent pour tous les candidats.

À faire : question 11.5 (fin de vie) à réécrire depuis la loi n° 2026-794 du 18 août 2026.
