# Méthode validée le 13 octobre 2026 : score global sur toutes les questions comparées, sans pondération ;
# détail par thème affiché seulement si au moins deux questions sont comparables.
import json, re
import os
D = os.path.dirname(os.path.abspath(__file__)) + '/'
allq = [l.split()[1] for l in open(D + 'grille.md') if re.match(r'- \d\d\.\d', l)]
def load(c): return {e['q']: e['code'] for e in json.load(open(D + f'codes_{c}.json'))}
P = load('philippe'); res = {}
for c in ['retailleau', 'attal', 'zemmour', 'lepen', 'glucksmann', 'tondelier', 'melenchon']:
    C = load(c)
    pr = [(q, C.get(q), P[q]) for q in allq if P.get(q) is not None and C.get(q) is not None]
    prox = lambda L: round(100 * (1 - sum(abs(a - b) / 4 for _, a, b in L) / len(L)))
    th = {}
    for t in sorted({q[:2] for q in allq}):
        L = [x for x in pr if x[0][:2] == t]
        th[t] = {'n': len(L), 'prox': prox(L) if len(L) >= 2 else None}
    res[c] = {'global': prox(pr), 'n': len(pr), 'identiques': sum(a == b for _, a, b in pr),
              'opposes': sum(abs(a - b) >= 3 for _, a, b in pr), 'themes': th}
json.dump(res, open(D + 'scores_v2.json', 'w'), ensure_ascii=False, indent=1)
for c, v in res.items():
    print(f"{c:11} {v['global']:3} n={v['n']:2} id={v['identiques']:2} opp={v['opposes']:2} ",
          ' '.join(f"{t}:{x['prox']}/{x['n']}" for t, x in v['themes'].items() if x['prox'] is not None))
