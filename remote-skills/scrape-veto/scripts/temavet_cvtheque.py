#!/usr/bin/env python3
"""
scrape-veto — collecteur de la CV-thèque vétérinaire de TÉMAVet Job (job.temavet.fr), côté candidats.

La CV-thèque est réservée aux recruteurs abonnés : elle se lit dans le Chrome de l'utilisateur, avec
sa session, par scripts/temavet_cvtheque.js (liste et fiches lues par fetch, export par download
blob). Ce script fait le reste de la CAPTURE mécanique : il lit l'export, compare avec la base et
prépare un squelette de records.json ; le JUGEMENT (exclusions, Expérience, Spécialités requises,
Statuts, Date de disponibilité, Contrat court) reste à la compétence, comme pour Facebook et la SVS.

Usage :
    python3 temavet_cvtheque.py connus
        Imprime, en une ligne JSON, les profils déjà en base (n° → date de mise à jour) : c'est
        l'argument de __tvStart({connus: …}) dans la page, qui n'a alors à recharger que les fiches
        mises à jour depuis le dernier passage (lecture incrémentale, 0.17.1).
    python3 temavet_cvtheque.py collect --canal recXXXXXXXXXXXXXX --export ~/Downloads/temavet_cv_<date>.json --out temavet_raw.json
        Lit chaque fiche de l'export, compare avec les profils déjà en base (sections de « Contenu
        complet » dont le lien pointe sur /users/veterinaire/<n°>) et écrit :
          - a_juger      : profils NOUVEAUX, ou MODIFIÉS (texte changé), avec un squelette de champs ;
          - reactualises : texte inchangé, date de mise à jour plus récente — records prêts à pousser
                           tels quels (le push remplace la section et avance « Date du post ») ;
          - inchanges    : même texte, même date (ignorés) — y compris les fiches connues que la
                           lecture incrémentale n'a pas rechargées (relue: false) ;
          - disparus     : en base, plus dans la CV-thèque (à signaler, jamais archivés ici) ;
          - inaccessibles: fiches refusées par TÉMAVet (« Vous n'avez pas accès à la page profil »).
        Lit Airtable avec AIRTABLE_API_KEY ; n'y écrit RIEN. Pas de « Vu en ligne le » ici, à la
        différence du portail SVS : la CV-thèque affiche encore des profils que personne n'a mis à
        jour depuis 2023, être visible n'y dit rien de l'activité du candidat — sa date de mise à
        jour, si.
    python3 temavet_cvtheque.py fiche --export <fichier> <n°>
        Affiche une fiche analysée et son squelette (mise au point).

Ce que le script pose, parce que la fiche le déclare dans des cases et non en texte libre :
  - « Zones de recherche » : région → ses départements (macro_regions du vocab, règle candidat de
    §3), département « (NN) » et ville « (CP) » → le département, pays et DOM présents dans le vocab ;
    le reste (Maroc, Seychelles…) ne reste que dans « Zone de recherche », texte libre ;
  - « Type de temps de travail » (Temps complet → Temps plein) ;
  - « Pratiques requises / optionnelles » depuis l'« Activité du poste » : chaque activité cochée est
    une alternative acceptée, donc requises = ce qui est commun à toutes, optionnelles = le reste ;
  - « Spécialités optionnelles » depuis les « Compétences spécialisées cliniques » déclarées (une
    compétence déclarée est une prétention : optionnelle, cf. §3) ;
  - Prénom / Nom (capitales remises en casse normale : un nom tout en capitales n'est pas fusionnable
    par le push), Mail1, Téléphone.
"""
import sys, re, json, html, os, time, urllib.request, urllib.parse, datetime as dt
from html.parser import HTMLParser

BASE = "appP0W2ISytaNyAhG"
T_POSTS = "tblE8XF5PjgUd7PdP"
PROFIL_RE = re.compile(r"job\.temavet\.fr/users/veterinaire/(\d+)")
HEADER_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2})\]\s*((?:https?://\S+)?)\s*(?:·\s*(.+?))?\s*$")
VOCAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "references", "matching_vocab.json")

# Activité du poste → (pratiques que l'activité impose, pratiques qu'elle laisse ouvertes).
# « Mixte » sans espèce nommée = Canine + Bovins (convention de §3). Non mappées, laissées au texte :
# Faune sauvage, Animaux exotiques, Élevage industriel et productions animales, Autre.
ACTIVITE = {
    "Canine (+/- NAC)": ({"Canine"}, {"NAC"}),
    "Mixte": ({"Canine", "Bovins"}, set()),
    "Canine/Equine": ({"Canine", "Equine"}, set()),
    "Rurale 100%": ({"Bovins"}, set()),
    "NAC 100%": ({"NAC"}, set()),
    "Équine 100%": ({"Equine"}, set()),
}
SPECIALITE = {
    "Médecine interne": "Médecine interne", "Chirurgie": "Chirurgie", "Urgences / Soins intensifs": "Urgences",
    "Ophtalmologie": "Ophtalmologie", "Reproduction": "Reproduction", "Neurologie": "Neurologie",
    "Cardiologie": "Cardiologie", "Cancérologie": "Oncologie", "Orthopédie (carnivores domestiques)": "Orthopédie",
    "Ostéopathie": "Ostéopathie",
}
TEMPS = {"Temps complet": "Temps plein", "Temps partiel": "Temps partiel"}
DOM = {"Guadeloupe": "971 - Guadeloupe", "Martinique": "972 - Martinique", "Guyane": "973 - Guyane",
       "La Réunion": "974 - La Réunion", "Mayotte": "974 - Mayotte"}
CIVILITE_RX = re.compile(r"^(?:Madame|Monsieur|Mademoiselle|Docteur|Dr\.?)\s+", re.I)


class _Tokens(HTMLParser):
    """HTML d'une fiche → suite de (genre, texte). Les genres viennent des classes de la page :
    LAB (libellé d'une case), SEC (titre de section), ZONE, NOM, EXP_* (blocs d'expérience ou de
    diplôme : titre, structure, dates, lieu, description) ; tout le reste est une valeur (v)."""
    VOID = {"br", "hr", "img", "input", "meta", "link", "source", "area", "col", "embed", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.out = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append((tag, dict(attrs).get("class") or ""))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        data = re.sub(r"\s+", " ", data).strip()
        if not data:
            return
        kind = "v"
        for tag, cls in reversed(self.stack):
            if tag in ("script", "style", "button", "form", "template"):
                return
            if "uppercase" in cls and "text-gray-500" in cls:
                kind = "LAB"; break
            if "leading-6" in cls and "decoration-" in cls:
                kind = "SEC"; break
            if "bg-vjcyan-100 py-1 px-2" in cls:
                kind = "ZONE"; break
            if "text-base font-semibold" in cls:
                kind = "NOM"; break
            if tag == "h2" and "font-semibold" in cls:
                kind = "EXP_T"; break
            if tag == "p":
                kind = ("EXP_ORG" if "italic" in cls else "EXP_DATE" if "text-xs" in cls
                        else "EXP_DESC" if "text-gray-500" in cls else "EXP_LIEU" if "text-sm" in cls else "v")
                break
        self.out.append((kind, data))


def lire_fiche(page_html):
    """Fiche TÉMAVet → dict : identité, contact, date de mise à jour, zones, cases (libellé → valeurs)
    et texte intégral rendu pour « Contenu complet »."""
    t = _Tokens()
    t.feed(page_html)
    toks = t.out
    out = {"civilite": "", "nom_complet": "", "mail": "", "tel": "", "maj": "", "zones": [], "cases": {}, "texte": ""}
    i_nom = next((k for k, (g, _) in enumerate(toks) if g == "NOM"), None)
    i_maj = next((k for k, (g, x) in enumerate(toks) if x.startswith("Dernière mise à jour")), None)
    if i_maj is None:
        return out
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", toks[i_maj][1])
    if m:
        out["maj"] = "%s-%s-%s" % (m.group(3), m.group(2), m.group(1))
    if i_nom is not None and i_nom < i_maj:
        nom = toks[i_nom][1]
        c = CIVILITE_RX.match(nom)
        out["civilite"], out["nom_complet"] = (c.group(0).strip(), nom[c.end():].strip()) if c else ("", nom)
    # Contact : les valeurs juste avant la date (le nom peut manquer : le bloc commence alors après
    # le titre de la fenêtre « Prise de contact »).
    debut = i_maj
    while debut > 0 and toks[debut - 1][0] == "v" and i_maj - debut < 3:
        debut -= 1
    for g, x in toks[debut:i_maj]:
        if "@" in x and not out["mail"]:
            out["mail"] = x.strip().lower()
        elif re.fullmatch(r"[+\d][\d .\-()/]{7,}", x) and not out["tel"]:
            out["tel"] = " / ".join(dict.fromkeys(n.strip() for n in x.split("/")))   # « A / A » → « A »
    corps = toks[i_maj + 1:]
    out["zones"] = list(dict.fromkeys(x for g, x in corps if g == "ZONE"))
    # Rendu du texte : cases « Libellé : valeurs », blocs d'expérience ou de diplôme en puces sous le
    # titre de leur section. Les cases se passent de titre : la page ne dit pas à quel niveau elles
    # appartiennent (les années d'expérience suivent une section « Stages » souvent vide), un titre
    # les rangerait sous la mauvaise section.
    lignes, sec_en_attente, lab, bloc = [], None, None, None
    if out["zones"]:
        lignes.append("Zones de recherche : " + ", ".join(out["zones"]))

    def poser(ligne, puce=False):
        nonlocal sec_en_attente
        if puce and sec_en_attente:
            lignes.extend(["", sec_en_attente.upper()])
        elif not puce and lignes and lignes[-1][:1] in ("-", " "):
            lignes.append("")                  # fin d'une liste à puces
        sec_en_attente = None
        lignes.append(ligne)

    def fermer_bloc():
        nonlocal bloc
        if bloc:
            tete = " · ".join(bloc.get(k, "") for k in ("EXP_T", "EXP_ORG", "EXP_DATE", "EXP_LIEU") if bloc.get(k))
            poser("- " + tete, puce=True)
            if bloc.get("EXP_DESC"):
                lignes.append("  " + bloc["EXP_DESC"])
        bloc = None

    def fermer_case():
        nonlocal lab
        if lab is not None:
            vals = out["cases"].get(lab, [])
            if vals:
                if all(len(v) <= 60 for v in vals):
                    poser("%s : %s" % (lab, ", ".join(vals)))
                else:
                    poser(lab + " :")
                    lignes.extend(vals)
        lab = None

    for g, x in corps:
        if g == "ZONE" or x == "Zones de recherche :":
            continue
        if g == "SEC":
            fermer_bloc(); fermer_case()
            sec_en_attente = x
        elif g == "LAB":
            fermer_bloc(); fermer_case()
            lab = x
            out["cases"].setdefault(lab, [])
        elif g.startswith("EXP_"):
            fermer_case()
            if bloc is None or g == "EXP_T" or g in bloc:
                fermer_bloc()
                bloc = {}
            bloc[g] = x
        elif lab is not None:
            out["cases"][lab].append(x)
        else:
            fermer_bloc()
            poser(x)
    fermer_bloc(); fermer_case()
    out["texte"] = "\n".join(lignes).strip()
    return out


def casse(mot):
    """« DUPONT » → « Dupont », « JEAN-PIERRE » → « Jean-Pierre » ; un mot qui n'est pas tout en
    capitales est gardé tel quel (« de », « McKenzie »)."""
    if mot.isupper():
        return "-".join(p[:1].upper() + p[1:].lower() for p in mot.split("-"))
    return mot


def prenom_nom(full):
    """« Louis DUPONT » → (Louis, Dupont) : les capitales de fin désignent le nom. Sans repère de casse
    (tout en capitales ou tout en casse normale), le premier mot est le prénom."""
    mots = full.split()
    if not mots:
        return "", ""
    if len(mots) == 1:
        return "", casse(mots[0])
    k = len(mots)
    if not mots[0].isupper():
        while k > 1 and mots[k - 1].isupper():
            k -= 1
    if k == len(mots):
        k = 1
    return " ".join(casse(m) for m in mots[:k]), " ".join(casse(m) for m in mots[k:])


def charger_vocab():
    try:
        return json.load(open(VOCAB, encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit("Vocabulaire introuvable (%s) : %s. Arrêt — sans lui les zones ne se traduisent pas." % (VOCAB, e))


def zones_vocab(zones, vocab):
    """Zones TÉMAVet → (valeurs du multi-select « Zones de recherche », zones restées hors vocab)."""
    permis = set(vocab["zones_de_recherche"])
    par_code = {}
    for v in vocab["zones_de_recherche"]:
        m = re.match(r"^(\d{2,3}) - ", v)
        if m:
            par_code.setdefault(m.group(1), []).append(v)

    def dept(code, cp=""):
        if code in ("2A", "2B") or code == "20":
            haute = code == "2B" or (cp[:3] not in ("200", "201") if cp else False)
            return "20 - Haute-Corse" if haute else "20 - Corse-du-Sud"
        if code == "976":
            return "974 - Mayotte"            # le vocab range Mayotte sous 974
        vals = par_code.get(code, [])
        return vals[0] if len(vals) == 1 else ("974 - La Réunion" if code == "974" else "")

    out, hors = [], []
    for z in zones:
        z = z.strip()
        m = re.search(r"\((\d{5})\)$", z)                   # ville (code postal)
        m2 = re.search(r"\((\d{2,3}|2[AB])\)$", z)          # département (code)
        if z in vocab["macro_regions"]:
            vals = vocab["macro_regions"][z]
        elif m:
            cp = m.group(1)
            vals = [dept(cp[:3] if cp[:2] in ("97", "98") else cp[:2], cp)]
        elif m2:
            vals = [dept(m2.group(1))]
        elif z in DOM:
            vals = [DOM[z]]
        elif z in permis:
            vals = [z]
        else:
            vals = []
        vals = [v for v in vals if v in permis]
        if vals:
            out.extend(vals)
        else:
            hors.append(z)
    return list(dict.fromkeys(out)), hors


def zone_texte(zones):
    """Texte libre « Zone de recherche » : les villes une seule fois, sans leurs codes postaux."""
    vus = []
    for z in zones:
        z = re.sub(r"\s*\(\d{5}\)$", "", z.strip())
        if z not in vus:
            vus.append(z)
    return ", ".join(vus)


def pratiques(activites):
    """Activités cochées (des alternatives) → (requises, optionnelles), cf. ACTIVITE."""
    connues = [ACTIVITE[a] for a in activites if a in ACTIVITE]
    if not connues:
        return [], []
    req = set.intersection(*[r for r, _ in connues])
    tout = set().union(*[r | o for r, o in connues])
    ordre = ["Canine", "Bovins", "Equine", "NAC"]
    return [p for p in ordre if p in req], [p for p in ordre if p in tout - req]


def nom_de_carte(lignes):
    """Le nom en tête de la carte de la liste, ou '' quand la carte n'en a pas : elle commence alors
    directement par le poste recherché (« Praticien »), qu'il ne faut pas prendre pour un nom."""
    tete = (lignes or [""])[0]
    if tete in ("Praticien", "Non praticien", "|") or tete.startswith(("Temps ", "Vétérinaire ", "Étudiant")):
        return ""
    return tete


def squelette(f, num, url, canal, vocab, carte_nom=""):
    """Champs Airtable mécaniques d'un profil. Ce qui demande un jugement (Expérience, Spécialités
    requises, Statuts contractuels, Date de disponibilité, Contrat court, exclusion) est laissé vide
    et se lit dans les clés « _… », aides à la lecture à retirer avant le push."""
    c = f["cases"]
    prenom, nom = prenom_nom(f["nom_complet"] or carte_nom)
    zv, hors = zones_vocab(f["zones"], vocab)
    req, opt = pratiques(c.get("Activité du poste (si praticien)", []))
    spe = list(dict.fromkeys(SPECIALITE[s] for s in c.get("Compétences spécialisées cliniques", []) if s in SPECIALITE))
    temps = list(dict.fromkeys(TEMPS[t] for t in c.get("Temps de travail", []) if t in TEMPS))
    champs = {
        "Type de post": "Vétérinaire cherche poste", "Type d'entrée": "Post",
        "Date du post": f["maj"], "Lien du post": url, "Prénom": prenom, "Nom": nom,
        "Contenu complet": f["texte"], "Canaux": [canal], "Mail1": f["mail"], "Téléphone": f["tel"],
        "Zone de recherche": zone_texte(f["zones"]), "Zones de recherche": zv,
        "Type de temps de travail": temps, "Pratiques requises": req, "Pratiques optionnelles": opt,
        "Spécialités optionnelles": spe,
    }
    champs = {k: v for k, v in champs.items() if v not in ("", [], None)}
    if not nom:
        # Profil sans nom (ni sur la fiche ni sur la carte) : pour le push, un post sans nom n'est jamais
        # fusionné, donc chaque mise à jour du profil créerait un enregistrement de plus. Une clé figée
        # (« # », cf. effective_key du push) garde le profil sur un seul enregistrement.
        champs["auteur_key"] = "temavet#%d" % num
    un = lambda lab: ", ".join(c.get(lab, []))
    return {"fields": champs, "_numero": num, "_statut": un("Statut actuel"), "_poste_recherche": un("Poste recherché"),
            "_secteur_non_praticien": un("Secteur du poste (si non praticien)"), "_disponibilite": un("Disponibilité"),
            "_annees_praticien": un("Années d'expérience en tant que praticien"), "_annee_sortie": un("Année de sortie"),
            "_ecole": un("Diplômé (ou futur diplômé) de"), "_internat": un("Internat"),
            "_activites": c.get("Activité du poste (si praticien)", []), "_zones_hors_vocab": hors,
            "_besoin_logement": un("Besoin logement")}


def en_base():
    """Profils TÉMAVet déjà en base : n° → la section la plus récente qui porte son lien."""
    key = os.environ.get("AIRTABLE_API_KEY")
    if not key:
        sys.exit("AIRTABLE_API_KEY absente : impossible de comparer avec la base. Arrêt (rien collecté).")
    H = {"Authorization": "Bearer " + key}
    out, off = {}, None
    while True:
        q = [("pageSize", "100"), ("filterByFormula", "FIND('job.temavet.fr/users/veterinaire/', {Contenu complet})"),
             ("fields[]", "Contenu complet"), ("fields[]", "Numéro"), ("fields[]", "Prénom"), ("fields[]", "Nom"),
             ("fields[]", "auteur_key")]
        if off:
            q.append(("offset", off))
        d = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://api.airtable.com/v0/%s/%s?%s" % (BASE, T_POSTS, urllib.parse.urlencode(q)), headers=H)))
        for r in d["records"]:
            f = r["fields"]
            for chunk in re.split(r"\n*─{5,}\n*", f.get("Contenu complet", "")):
                lines = chunk.strip().split("\n")
                h = HEADER_RE.match(lines[0].strip()) if lines else None
                p = PROFIL_RE.search(h.group(2)) if h else None
                if not p:
                    continue
                num = int(p.group(1))
                if num in out and out[num]["date"] >= h.group(1):
                    continue
                out[num] = {"rec": r["id"], "numero": f.get("Numéro"), "date": h.group(1),
                            "nom": ("%s %s" % (f.get("Prénom", ""), f.get("Nom", ""))).strip(),
                            "auteur_key": f.get("auteur_key", ""), "texte": norm("\n".join(lines[1:]))}
        off = d.get("offset")
        if not off:
            return out
        time.sleep(0.21)


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def charger_export(path):
    d = json.load(open(os.path.expanduser(path), encoding="utf-8"))
    if not isinstance(d, dict) or "profils" not in d or "cartes" not in d:
        sys.exit("%s n'est pas un export de temavet_cvtheque.js (clés profils / cartes absentes)." % path)
    return d


def classer(export, connus, canal, vocab):
    """Export de la page + profils en base → le contenu de temavet_raw.json (sans réseau)."""
    noms_carte = {c["id"]: nom_de_carte(c.get("lignes")) for c in export["cartes"]}
    a_juger, reactualises, inchanges, inaccessibles = [], [], [], []
    for c in export["cartes"]:
        num, p = c["id"], export["profils"].get(c["id"])
        k = connus.get(int(num))
        if not p and k:
            # Fiche connue que la lecture incrémentale n'a pas rechargée : plus bas dans la liste que
            # trois fiches connues revenues à leur date, donc inchangée elle aussi.
            inchanges.append({"numero": int(num), "rec": k["rec"], "post": k["numero"], "nom": k["nom"], "relue": False})
            continue
        if not p or "/users/veterinaire/" not in p.get("url", "") or p.get("status") != 200:
            inaccessibles.append({"numero": int(num), "nom": noms_carte.get(num, "")})
            continue
        f = lire_fiche(p["html"])
        if not f["maj"] or not f["texte"]:
            inaccessibles.append({"numero": int(num), "nom": noms_carte.get(num, ""), "raison": "fiche illisible"})
            continue
        sq = squelette(f, int(num), p["url"], canal, vocab, noms_carte.get(num, ""))
        if k and "#" in (k["auteur_key"] or ""):
            sq["fields"]["auteur_key"] = k["auteur_key"]   # clé figée à la main : respectée à l'entrée
        if k and norm(f["texte"]) == k["texte"]:
            if f["maj"] <= k["date"]:
                inchanges.append({"numero": int(num), "rec": k["rec"], "post": k["numero"], "nom": k["nom"], "relue": True})
                continue
            # Texte inchangé, mise à jour plus récente : le candidat a revalidé son profil. Rien à
            # rejuger ; on n'envoie que de quoi remplacer la section et dater, pour ne pas écraser
            # ce que la compétence ou la recruteuse ont posé sur l'enregistrement.
            garde = ("Type de post", "Type d'entrée", "Date du post", "Lien du post", "Prénom", "Nom",
                     "Contenu complet", "Canaux", "auteur_key")
            reactualises.append({"numero": int(num), "rec": k["rec"], "post": k["numero"], "avant": k["date"],
                                 "fields": {x: v for x, v in sq["fields"].items() if x in garde}})
            continue
        a_juger.append({"numero": int(num), "etat": "modifié" if k else "nouveau", "rec_existant": k["rec"] if k else None,
                        "nom": "%s %s" % (sq["fields"].get("Prénom", ""), sq["fields"].get("Nom", "")), "squelette": sq})
    # Disparus : en base, absents de la LISTE (lue en entier même en incrémental) ; une fiche
    # inaccessible ou non relue est toujours listée, donc toujours en ligne.
    en_ligne = {int(c["id"]) for c in export["cartes"]}
    complet = len(export["cartes"]) >= (export.get("total_annonce") or 0)
    disparus = [] if not complet else [{"numero": n, "post": v["numero"], "rec": v["rec"], "nom": v["nom"]}
                                       for n, v in connus.items() if n not in en_ligne]
    return {"collecte_le": export.get("collecte_le"), "canal": canal, "acces_fin": export.get("acces_fin"),
            "quota_debut": export.get("quota_debut"), "quota_fin": export.get("quota_fin"),
            "profils_annonces": export.get("total_annonce"), "profils_listes": len(export["cartes"]),
            "fiches_lues": len(export["profils"]), "complet": complet,
            "a_juger": a_juger, "reactualises": reactualises, "inchanges": inchanges,
            "disparus": disparus, "inaccessibles": inaccessibles}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("connus", "collect", "fiche"):
        sys.exit(__doc__)
    args = sys.argv[2:]
    if sys.argv[1] == "connus":
        print(json.dumps({str(n): v["date"] for n, v in sorted(en_base().items())}, separators=(",", ":")))
        return

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    if not opt("--export"):
        sys.exit("--export <fichier> obligatoire : le JSON téléchargé par temavet_cvtheque.js.")
    export, vocab = charger_export(opt("--export")), charger_vocab()
    noms_carte = {c["id"]: nom_de_carte(c.get("lignes")) for c in export["cartes"]}
    if sys.argv[1] == "fiche":
        num = args[-1]
        p = export["profils"].get(num) or sys.exit("Profil n°%s absent de l'export." % num)
        f = lire_fiche(p["html"])
        print(f["texte"]); print()
        print(json.dumps(squelette(f, int(num), p["url"], "recXXXXXXXXXXXXXX", vocab, noms_carte.get(num, "")),
                         ensure_ascii=False, indent=1))
        return
    canal, out_path = opt("--canal"), opt("--out", "temavet_raw.json")
    if not canal or not re.match(r"^rec[A-Za-z0-9]{14}$", canal):
        sys.exit("--canal recXXXXXXXXXXXXXX obligatoire : le recId du canal CV-thèque TÉMAVet (table Canaux de diffusion).")
    res = classer(export, en_base(), canal, vocab)
    json.dump(res, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    a_juger, disparus, inaccessibles = res["a_juger"], res["disparus"], res["inaccessibles"]
    nouveaux = sum(1 for a in a_juger if a["etat"] == "nouveau")
    print("%s profils annoncés, %d listés, %d fiches lues · %d nouveaux, %d modifiés à juger · %d réactualisés (prêts) · "
          "%d inchangés (dont %d non relus) · %d disparus · %d inaccessibles → %s" % (
              export.get("total_annonce"), res["profils_listes"], res["fiches_lues"], nouveaux, len(a_juger) - nouveaux,
              len(res["reactualises"]), len(res["inchanges"]), sum(1 for i in res["inchanges"] if not i["relue"]),
              len(disparus), len(inaccessibles), out_path))
    print("Accès CV-thèque jusqu'au %s · quota de téléchargement %s → %s%s" % (
        export.get("acces_fin"), export.get("quota_debut"), export.get("quota_fin"),
        "" if export.get("quota_debut") == export.get("quota_fin") else "  ⚠️ LE QUOTA A BOUGÉ PENDANT LA COLLECTE"))
    if not res["complet"]:
        print("⚠️ Liste incomplète (%d profils listés sur %s annoncés) : disparus non calculés." % (
            len(export["cartes"]), export.get("total_annonce")))
    for a in a_juger:
        sq = a["squelette"]
        print("  n°%-6s %-8s %-28s %s · %s · %s" % (a["numero"], a["etat"], a["nom"][:28], sq["fields"].get("Date du post"),
                                                  sq["_poste_recherche"] or "?", sq["_statut"]))
    for d in disparus:
        print("  ✖ disparu : profil n°%s → post n°%s %s (à signaler)" % (d["numero"], d["post"], d["nom"]))
    for d in inaccessibles:
        print("  · inaccessible : profil n°%s %s" % (d["numero"], d["nom"]))


if __name__ == "__main__":
    main()
