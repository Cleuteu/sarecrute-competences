"""Fond de carte de la page candidats : départements (métropole et DROM), cantons suisses, provinces
belges et Luxembourg, tirés de Natural Earth admin-1 10m (domaine public).

Allègement sans casser les frontières communes : sommets arrondis sur une grille de PAS degré,
puis chaque frontière entre deux nœuds (point où change le voisinage) est simplifiée UNE fois
(Douglas-Peucker, TOLERANCE degré) et réutilisée telle quelle par les deux zones qui la
partagent : pas de jour ni de chevauchement entre voisins. Les îles de moins de ILOT_MIN degré²
sont retirées, jamais les enclaves (un polygone qui touche une autre zone : retiré, il laisserait
un trou chez son voisin). Les zones faites de plusieurs entités qui se touchent (les trois
districts du Luxembourg) sont fondues en un seul contour. Le point où s'écrit le nombre est
replacé à l'intérieur de la zone quand celui de Natural Earth tombe dehors (Soleure, Mayotte).
Les noms des départements viennent de la liste officielle, pas de Natural Earth (coquilles, ex.
« Seien-et-Marne »).

Sortie : zones_geo.json = [{label, pays, niveau, code, lat, lon, poly: [[[x, y], ...], ...]}],
coordonnées en entiers (degré / PAS), décodées par la page.

Outil de développement, pas utilisé par la routine : à relancer seulement pour changer le fond de
carte. Source à télécharger (domaine public, ~40 Mo) :
  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson
Usage : python3 -I geo_zones.py <admin1.geojson>   → écrit ../assets/zones_geo.json"""
import json, math, pathlib, sys
from collections import defaultdict
HERE = pathlib.Path(__file__).parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
SORTIE = HERE.parent / 'assets' / 'zones_geo.json'
PAS = 0.001
TOLERANCE = 0.008
ILOT_MIN = 0.001

DROM = {'FR-GP': '971', 'FR-MQ': '972', 'FR-GF': '973', 'FR-RE': '974', 'FR-YT': '976'}
DEPARTEMENTS = {
    '01': 'Ain', '02': 'Aisne', '03': 'Allier', '04': 'Alpes-de-Haute-Provence', '05': 'Hautes-Alpes',
    '06': 'Alpes-Maritimes', '07': 'Ardèche', '08': 'Ardennes', '09': 'Ariège', '10': 'Aube', '11': 'Aude',
    '12': 'Aveyron', '13': 'Bouches-du-Rhône', '14': 'Calvados', '15': 'Cantal', '16': 'Charente',
    '17': 'Charente-Maritime', '18': 'Cher', '19': 'Corrèze', '2A': 'Corse-du-Sud', '2B': 'Haute-Corse',
    '21': "Côte-d'Or", '22': "Côtes-d'Armor", '23': 'Creuse', '24': 'Dordogne', '25': 'Doubs', '26': 'Drôme',
    '27': 'Eure', '28': 'Eure-et-Loir', '29': 'Finistère', '30': 'Gard', '31': 'Haute-Garonne', '32': 'Gers',
    '33': 'Gironde', '34': 'Hérault', '35': 'Ille-et-Vilaine', '36': 'Indre', '37': 'Indre-et-Loire',
    '38': 'Isère', '39': 'Jura', '40': 'Landes', '41': 'Loir-et-Cher', '42': 'Loire', '43': 'Haute-Loire',
    '44': 'Loire-Atlantique', '45': 'Loiret', '46': 'Lot', '47': 'Lot-et-Garonne', '48': 'Lozère',
    '49': 'Maine-et-Loire', '50': 'Manche', '51': 'Marne', '52': 'Haute-Marne', '53': 'Mayenne',
    '54': 'Meurthe-et-Moselle', '55': 'Meuse', '56': 'Morbihan', '57': 'Moselle', '58': 'Nièvre', '59': 'Nord',
    '60': 'Oise', '61': 'Orne', '62': 'Pas-de-Calais', '63': 'Puy-de-Dôme', '64': 'Pyrénées-Atlantiques',
    '65': 'Hautes-Pyrénées', '66': 'Pyrénées-Orientales', '67': 'Bas-Rhin', '68': 'Haut-Rhin', '69': 'Rhône',
    '70': 'Haute-Saône', '71': 'Saône-et-Loire', '72': 'Sarthe', '73': 'Savoie', '74': 'Haute-Savoie',
    '75': 'Paris', '76': 'Seine-Maritime', '77': 'Seine-et-Marne', '78': 'Yvelines', '79': 'Deux-Sèvres',
    '80': 'Somme', '81': 'Tarn', '82': 'Tarn-et-Garonne', '83': 'Var', '84': 'Vaucluse', '85': 'Vendée',
    '86': 'Vienne', '87': 'Haute-Vienne', '88': 'Vosges', '89': 'Yonne', '90': 'Territoire de Belfort',
    '91': 'Essonne', '92': 'Hauts-de-Seine', '93': 'Seine-Saint-Denis', '94': 'Val-de-Marne', '95': "Val-d'Oise",
    '971': 'Guadeloupe', '972': 'Martinique', '973': 'Guyane', '974': 'La Réunion', '976': 'Mayotte',
}
CANTONS = {
    'CH-AG': "Canton d'Argovie", 'CH-AI': "Canton d'Appenzell Rhodes-Intérieures",
    'CH-AR': "Canton d'Appenzell Rhodes-Extérieures", 'CH-BE': 'Canton de Berne',
    'CH-BL': 'Canton de Bâle-Campagne', 'CH-BS': 'Canton de Bâle-Ville', 'CH-FR': 'Canton de Fribourg',
    'CH-GE': 'Canton de Genève', 'CH-GL': 'Canton de Glaris', 'CH-GR': 'Canton des Grisons',
    'CH-JU': 'Canton du Jura', 'CH-LU': 'Canton de Lucerne', 'CH-NE': 'Canton de Neuchâtel',
    'CH-NW': 'Canton de Nidwald', 'CH-OW': "Canton d'Obwald", 'CH-SG': 'Canton de Saint-Gall',
    'CH-SH': 'Canton de Schaffhouse', 'CH-SO': 'Canton de Soleure', 'CH-SZ': 'Canton de Schwytz',
    'CH-TG': 'Canton de Thurgovie', 'CH-TI': 'Canton du Tessin', 'CH-UR': "Canton d'Uri",
    'CH-VD': 'Canton de Vaud', 'CH-VS': 'Canton du Valais', 'CH-ZG': 'Canton de Zoug',
    'CH-ZH': 'Canton de Zurich',
}
PROVINCES = {
    'BE-VAN': "Province d'Anvers", 'BE-VBR': 'Province du Brabant flamand',
    'BE-VLI': 'Province de Limbourg', 'BE-VOV': 'Province de Flandre-Orientale',
    'BE-VWV': 'Province de Flandre-Occidentale', 'BE-WBR': 'Province du Brabant wallon',
    'BE-WHT': 'Province de Hainaut', 'BE-WLG': 'Province de Liège',
    'BE-WLX': 'Province de Luxembourg', 'BE-WNA': 'Province de Namur',
    'BE-BRU': 'Région de Bruxelles-Capitale',
}
PAYS = {'FR': 'France', 'CH': 'Suisse', 'BE': 'Belgique', 'LU': 'Luxembourg'}


def aire(r):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]))) / 2


def anneau(r):
    out = []
    for x, y in r:
        p = (round(x / PAS), round(y / PAS))
        if not out or out[-1] != p:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out if len(out) >= 3 else None


def polygones(geom):
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    out = []
    for p in polys:
        ext = anneau(p[0])
        if ext:
            out.append([ext] + [a for a in (anneau(r) for r in p[1:]) if a])
    return out


def aire_signee(r):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1])) / 2


def fusionner(label, polys):
    """Fond en un contour les polygones d'une même zone qui se touchent : orientés dans le même
    sens, deux voisins parcourent leur frontière commune en sens inverse ; ces arêtes s'annulent
    et les autres se rechaînent."""
    if len(polys) < 2 or any(len(p) > 1 for p in polys):
        return polys
    exts = [p[0] if aire_signee(p[0]) > 0 else p[0][::-1] for p in polys]
    aretes = {(r[k], r[(k + 1) % len(r)]) for r in exts for k in range(len(r))}
    restes = sorted(e for e in aretes if (e[1], e[0]) not in aretes)
    if len(restes) == len(aretes):
        return polys
    suivant = defaultdict(list)
    for a, b in restes:
        suivant[a].append(b)
    anneaux = []
    while suivant:
        depart = min(suivant)
        r, a = [depart], depart
        while True:
            b = suivant[a].pop()
            if not suivant[a]:
                del suivant[a]
            if b == depart:
                break
            r.append(b)
            a = b
        anneaux.append(r)
    print(f'{label} : {len(polys)} polygones fondus en {len(anneaux)}')
    return [[r] for r in anneaux]


def retirer_ilots(zones):
    porteurs = defaultdict(set)    # sommet -> zones dont un anneau le contient
    for label, z in zones.items():
        for poly in z['poly']:
            for r in poly:
                for pt in r:
                    porteurs[pt].add(label)
    for z in zones.values():
        def a_garder(poly):
            return aire(poly[0]) * PAS * PAS >= ILOT_MIN or any(len(porteurs[pt]) > 1 for pt in poly[0])
        gardes = [p for p in z['poly'] if a_garder(p)]
        z['poly'] = gardes or sorted(z['poly'], key=lambda p: -aire(p[0]))[:1]


def dans_anneau(x, y, r):
    dedans = False
    for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            dedans = not dedans
    return dedans


def dans_poly(x, y, poly):
    return dans_anneau(x, y, poly[0]) and not any(dans_anneau(x, y, t) for t in poly[1:])


def distance_bord(x, y, poly):
    d = math.inf
    for r in poly:
        for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
            dx, dy = x1 - x0, y1 - y0
            u = max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
            d = min(d, math.hypot(x - x0 - u * dx, y - y0 - u * dy))
    return d


def point_interieur(poly, n=40):
    """Point de la grille n×n de l'emprise le plus éloigné des bords (pôle d'inaccessibilité approché)."""
    xs, ys = [p[0] for p in poly[0]], [p[1] for p in poly[0]]
    meilleur, dmax = None, -1
    for i in range(1, n):
        for j in range(1, n):
            x = min(xs) + (max(xs) - min(xs)) * i / n
            y = min(ys) + (max(ys) - min(ys)) * j / n
            if dans_poly(x, y, poly):
                d = distance_bord(x, y, poly)
                if d > dmax:
                    meilleur, dmax = (x, y), d
    return meilleur


def douglas_peucker(pts, tol):
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    pile = [(0, len(pts) - 1)]
    while pile:
        i, j = pile.pop()
        (x0, y0), (x1, y1) = pts[i], pts[j]
        dx, dy = x1 - x0, y1 - y0
        long_ = math.hypot(dx, dy)
        dmax, kmax = -1, None
        for k in range(i + 1, j):
            x, y = pts[k]
            d = abs(dy * (x - x0) - dx * (y - y0)) / long_ if long_ else math.hypot(x - x0, y - y0)
            if d > dmax:
                dmax, kmax = d, k
        if kmax is not None and dmax > tol:
            keep[kmax] = True
            pile += [(i, kmax), (kmax, j)]
    return [p for p, k in zip(pts, keep) if k]


def simplifier(anneaux, tol):
    """Simplifie chaque frontière une seule fois. Un nœud est un sommet où l'ensemble des zones
    bordées change ; entre deux nœuds, l'arc est commun aux mêmes anneaux et reçoit partout le
    même tracé simplifié (à l'envers chez le voisin)."""
    bordants = defaultdict(set)    # arête non orientée -> anneaux qui la contiennent
    porteurs = defaultdict(set)    # sommet -> anneaux qui le contiennent
    for i, r in enumerate(anneaux):
        for k, a in enumerate(r):
            bordants[frozenset((a, r[(k + 1) % len(r)]))].add(i)
            porteurs[a].add(i)

    def est_noeud(r, k):
        a = r[k]
        avant = bordants[frozenset((r[k - 1], a))]
        apres = bordants[frozenset((a, r[(k + 1) % len(r)]))]
        return avant != apres or porteurs[a] != avant

    arcs, out = {}, []
    for r in anneaux:
        n = len(r)
        noeuds = [k for k in range(n) if est_noeud(r, k)]
        if not noeuds:
            # Île, ou enclave bordée par un seul voisin (Bruxelles) : deux points fixes choisis de
            # la même façon des deux côtés de la frontière.
            k0 = min(range(n), key=lambda k: r[k])
            k1 = max(range(n), key=lambda k: ((r[k][0] - r[k0][0]) ** 2 + (r[k][1] - r[k0][1]) ** 2, r[k]))
            noeuds = sorted({k0, k1})
        res = []
        for a, b in zip(noeuds, noeuds[1:] + noeuds[:1]):
            fin = b if b > a else b + n
            arc = tuple(r[m % n] for m in range(a, fin + 1))
            inv = arc[::-1]
            canon = min(arc, inv)
            if canon not in arcs:
                arcs[canon] = douglas_peucker(list(canon), tol)
            s = arcs[canon] if canon == arc else arcs[canon][::-1]
            res.extend(s[:-1])
        out.append(res if len(res) >= 3 and aire(res) > 0 else None)
    return out


def main():
    if SRC is None:
        raise SystemExit(__doc__)
    g = json.load(open(SRC))
    zones = {}
    for f in g['features']:
        p = f['properties']
        iso2 = p.get('iso_a2')
        if iso2 not in PAYS:
            continue
        code = p['iso_3166_2']
        if iso2 == 'FR':
            num = DROM.get(code) or code[3:]
            nom = DEPARTEMENTS[num]
            label, niveau = f'{nom} ({num})', 'dept'
        elif iso2 == 'CH':
            label, niveau = CANTONS[code], 'sous-pays'
        elif iso2 == 'BE':
            label, niveau = PROVINCES[code], 'sous-pays'
        else:
            label, niveau = 'Luxembourg', 'pays'   # les trois districts ne font qu'une zone
        z = zones.setdefault(label, {'label': label, 'pays': PAYS[iso2], 'niveau': niveau,
                                     'code': code, 'lat': p['latitude'], 'lon': p['longitude'], 'poly': []})
        z['poly'] += polygones(f['geometry'])
    for label, z in zones.items():
        z['poly'] = fusionner(label, z['poly'])
    retirer_ilots(zones)
    anneaux = [r for z in zones.values() for poly in z['poly'] for r in poly]
    simples = iter(simplifier(anneaux, TOLERANCE / PAS))
    for z in zones.values():
        polys = []
        for poly in z['poly']:
            rs = [next(simples) for _ in poly]
            if rs[0]:
                polys.append([rs[0]] + [r for r in rs[1:] if r])
        z['poly'] = polys
    lu = zones.get('Luxembourg')
    if lu:   # point d'étiquette du pays, pas celui d'un de ses districts
        lu['lat'], lu['lon'] = 49.78, 6.10
    # Le nombre s'écrit dans la plus grande partie de la zone, pas dans une exclave ou un îlot.
    for z in zones.values():
        principal = max(z['poly'], key=lambda p: aire(p[0]))
        if not dans_poly(z['lon'] / PAS, z['lat'] / PAS, principal):
            px, py = point_interieur(principal)
            print(f"{z['label']} : point d'étiquette replacé dans la zone")
            z['lon'], z['lat'] = round(px * PAS, 4), round(py * PAS, 4)
        assert dans_poly(z['lon'] / PAS, z['lat'] / PAS, principal), z['label']
    for z in zones.values():
        z['poly'] = [[[list(p) for p in r] for r in poly] for poly in z['poly']]
    out = sorted(zones.values(), key=lambda z: (z['pays'], z['label']))
    json.dump(out, open(SORTIE, 'w'), ensure_ascii=False, separators=(',', ':'))
    n = sum(len(r) for z in out for poly in z['poly'] for r in poly)
    print(f'{len(out)} zones, {n} sommets, {SORTIE.stat().st_size // 1024} Ko')


if __name__ == '__main__':
    main()
