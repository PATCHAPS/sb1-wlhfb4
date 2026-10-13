# Consignes de codage (proximité SAPERE)

Dossier : ce répertoire (analyse-2027/proximite-philippe/).

1. Lis `grille.md` (64 questions, ancres −2 / 0 / +2, crans ±1 parfois définis).
2. Lis en entier le fichier de mesures du candidat `rows_<candidat>.txt`. Chaque ligne : `[NN] 'titre','source','précisions/manques','coût',...`, NN = numéro du thème du registre. Lis aussi `codes_philippe.json` comme exemple de format et de niveau d'exigence.
3. Pour chacune des 64 questions, code la position du candidat :
   - entier −2..+2, ou `null` (= n.c.) si AUCUNE mesure du registre ne permet de trancher ;
   - UNIQUEMENT à partir des mesures du fichier (titre, précisions, citations qui y figurent). Aucune connaissance extérieure, aucune déduction de l'étiquette partisane ;
   - une mesure peut venir d'un autre thème que celui de la question, mais une même mesure ne peut servir qu'à UNE seule question (pas de double compte) ;
   - en cas de doute entre deux crans, prends le plus prudent (le plus proche de 0) et signale-le dans `doute` ;
   - une mesure contradictoire ou retirée/remplacée dans les précisions (« remplacé par », « à reconfirmer ») : tiens compte de la version la plus récente et signale-le.
4. Écris le résultat dans `codes_<candidat>.json` : liste de 64 objets
   `{"q":"01.1","code":1,"mesures":["titre exact copié du fichier", ...],"justif":"≤ 30 mots en français","doute":"" }`
   Pour `null` : `"mesures":[]`, justif courte (« aucune mesure »).
   Les titres doivent être copiés à l'identique (vérifiables par recherche de chaîne `'titre'` dans le fichier).
5. Vérifie par script Python : 64 entrées, q uniques, codes dans {−2..2, null}, chaque titre présent dans rows, aucun titre utilisé deux fois.
6. Réponds en ≤ 150 mots : nombre de questions codées, liste des cas douteux (q + raison en une ligne). Ne modifie aucun autre fichier.

Format des nombres : 2,000 et 4.93 %. Pas de tiret cadratin.
