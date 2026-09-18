#!/usr/bin/env python3
"""
scrape-veto — collecteur du marché de l'emploi de la SVS (gstsvs.ch), côté cliniques.

Le portail est un site HTML classique : pas de Chrome, pas de session, pas de helpers. Ce script
fait la CAPTURE mécanique (liste des annonces, fiche de chacune, contact, langue) et prépare un
squelette de records.json ; le JUGEMENT (exclusions, pratiques, expérience, Poste, Questions, clé
d'offre) reste à la compétence, comme pour Facebook (principe « capturer / juger / écrire séparément »).

Usage :
    python3 svs_portail.py collect --canal recXXXXXXXXXXXXXX --out svs_raw.json [--all] [--max N]
        Liste toutes les annonces « Vétérinaire » du portail, lit chaque fiche, compare avec les
        annonces déjà en base (posts dont le Lien du post pointe sur /annonce/<n°>) et écrit :
          - annonces  : les fiches NOUVELLES (ou MODIFIÉES : même n°, texte différent), avec un
                        squelette de champs Airtable prêt à compléter ;
          - connues   : n° déjà en base et inchangés (ignorés, sauf --all) ;
          - disparues : n° en base qui ne sont plus en ligne (le poste est sans doute pourvu :
                        à signaler, jamais archivé ici).
        Lit Airtable avec AIRTABLE_API_KEY. Seule écriture : « Vu en ligne le » = aujourd'hui sur les
        posts déjà en base dont l'annonce est encore en ligne (--sans-marquer pour s'en passer). Le
        score hebdo lit cette date pour la fraîcheur : une annonce publiée il y a trois mois mais
        toujours affichée est un poste toujours ouvert, pas une annonce périmée.
    python3 svs_portail.py fiche 5449
        Affiche la fiche d'une annonce (mise au point).

Langue de l'annonce : détectée sur le texte (français / allemand / italien) ; si le texte ne tranche
pas, le canton décide (Vaud, Genève, Neuchâtel, Jura → français ; Tessin → italien ; sinon allemand ;
Berne, Fribourg, Valais sont bilingues, le texte fait foi). Décision d'Alex (18/09/2026) : sur cette
source, « Langues requises » porte la langue de l'annonce (Français / Allemand) — c'est la langue de
travail du poste. L'italien n'a pas de valeur select : champ laissé vide, signalé dans le résumé.

Cantons → « Zones de recherche » : seuls Genève, Vaud, Berne, Neuchâtel, Fribourg et Valais existent
dans le vocabulaire ; les autres cantons ne donnent que « Suisse » (le score hebdo écartera « pas de
département exploitable », c'est voulu : hors zone des recruteuses). Le nom du canton reste dans
« Zone de recherche » (texte libre).
"""
import sys, re, json, html, os, time, urllib.request, urllib.parse, unicodedata, datetime as dt

SITE = "https://www.gstsvs.ch"
LISTE = "/fr/portail-demplois/marche-de-lemploi?tx_solrgstsvs_jobportal%5Bfilter%5D%5B0%5D=category%3AV%C3%A9t%C3%A9rinaire&tx_solrgstsvs_jobportal%5Bpage%5D={page}"
FICHE = "/fr/portail-demplois/marche-de-lemploi/annonce/{n}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) SaRecrute scrape-veto"}
BASE = "appP0W2ISytaNyAhG"
T_POSTS = "tblE8XF5PjgUd7PdP"
F_VU_EN_LIGNE = "Vu en ligne le"      # champ date ISO, écrit par --marquer (nom : l'API accepte les noms)

CANTON_ZONE = {"Genève": "Canton de Genève", "Vaud": "Canton de Vaud", "Berne": "Canton de Berne",
               "Neuchâtel": "Canton de Neuchatel", "Fribourg": "Canton de Fribourg", "Valais": "Canton du Valais"}
CANTON_FR = {"Vaud", "Genève", "Neuchâtel", "Jura"}
CANTON_IT = {"Tessin"}
CANTONS = {"Zurich", "Berne", "Lucerne", "Uri", "Schwytz", "Obwald", "Nidwald", "Glaris", "Zoug", "Fribourg", "Soleure",
           "Bâle-Ville", "Bâle-Campagne", "Schaffhouse", "Appenzell Rhodes-Extérieures", "Appenzell Rhodes-Intérieures",
           "Saint-Gall", "Grisons", "Argovie", "Thurgovie", "Tessin", "Vaud", "Valais", "Neuchâtel", "Genève", "Jura",
           "toute la Suisse"}  # libellés du portail (facette « canton »)
DE_RX = re.compile(r"\b(?:wir|und|für|mit|eine[nr]?|unsere[rn]?|suchen|Tierärztin|Tierarzt|Praxis|Stelle|Bewerbung|gesucht|Kleintier\w*|Grosstier\w*|Gemischtpraxis|Verstärkung|Team|Sie|Ihre?)\b")
IT_RX = re.compile(r"\b(?:cerchiamo|veterinari[oa]|clinica|ambulatorio|assunzione|candidatura|lavoro|siamo|nostro|nostra|della|degli|per il)\b", re.I)
FR_RX = re.compile(r"\b(?:nous|vous|pour|avec|recherch\w+|vétérinaire|cabinet|clinique|poste|équipe|candidature|recrut\w+|notre|votre)\b", re.I)


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def texte(h):
    """HTML → lignes de texte propres (même principe que la lecture navigateur)."""
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S)
    h = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>|</div>|</tr>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h)
    lines = [re.sub(r"[ \t\xa0]+", " ", l).strip() for l in h.split("\n")]
    return [l for l in lines if l]


def liste():
    """Tous les n° d'annonces « Vétérinaire » (offres), par pages successives."""
    nums, page = [], 1
    while page <= 30:
        h = get(SITE + LISTE.format(page=page))
        found = re.findall(r'href="[^"]*/marche-de-lemploi/annonce/(\d+)"', h)
        found = [n for n in dict.fromkeys(found) if n not in nums]
        if not found:
            break
        nums += found
        page += 1
        time.sleep(0.4)
    return nums


def langue(corps, canton):
    de, it, fr = len(DE_RX.findall(corps)), len(IT_RX.findall(corps)), len(FR_RX.findall(corps))
    if de >= 8 and de > 2 * fr:
        return "de"
    if it >= 8 and it > 2 * fr:
        return "it"
    if fr >= 8 and fr > 2 * max(de, it):
        return "fr"
    if canton in CANTON_FR:
        return "fr"
    if canton in CANTON_IT:
        return "it"
    return "de" if de > fr else "fr"


def fiche(n):
    url = SITE + FICHE.format(n=n)
    h = get(url)
    m = re.search(r"<main[^>]*>(.*?)</main>", h, re.S)
    body_html = m.group(1) if m else h
    lines = texte(body_html)
    # bloc annonce : de « Offre d'emploi » à « Contacter »
    s = next((i for i, l in enumerate(lines) if l == "Offre d'emploi"), -1) + 1
    e = next((i for i, l in enumerate(lines) if l == "Contacter"), len(lines))
    bloc = lines[s:e]
    out = {"numero": int(n), "url": url, "titre": bloc[0] if bloc else "", "meta": [], "canton": "", "pensum": "",
           "date_pub": "", "des": "", "jeunes_bienvenus": False, "permanent": None, "corps": ""}
    # en-tête : titre, éventuels sous-titres libres (« 40–100 % | Pensum flexibel », nom d'établissement),
    # puis la ligne « Numéro d'annonce … » qui ancre la lecture des méta-lignes
    inum = next((j for j, l in enumerate(bloc) if l.startswith("Numéro d'annonce ")), None)
    if inum is None:
        out["corps"] = "\n".join(bloc[1:]); out["contact"] = {}; out["langue"] = langue(out["corps"], ""); return out
    if inum > 1:
        out["titre"] = " · ".join(bloc[:inum])
    i = inum
    while i < len(bloc):
        l = bloc[i]
        mm = re.match(r"Numéro d'annonce (\d+) \| (\d{2})\.(\d{2})\.(\d{4})", l)
        if mm:
            out["date_pub"] = f"{mm.group(4)}-{mm.group(3)}-{mm.group(2)}"; i += 1; continue
        if l == "Jeunes professionnels bienvenus":
            out["jeunes_bienvenus"] = True; i += 1; continue
        mm = re.match(r"^(Emploi [^,]+|Stage[^,]*|Internship[^,]*|Remplacement[^,]*|Temporaire[^,]*)(?:, (\d+)[–-](\d+)%)?$", l)
        if mm:
            out["meta"].append(l); out["permanent"] = l.startswith("Emploi permanent")
            if mm.group(2):
                out["pensum"] = f"{mm.group(2)}-{mm.group(3)}"
            i += 1; continue
        mm = re.match(r"Poste à repourvoir dès: ?(.*)", l)
        if mm:
            out["des"] = mm.group(1).strip(); i += 1; continue
        # le canton : un libellé de la facette « canton » du portail, seul sur sa ligne
        if not out["canton"] and l in CANTONS:
            out["canton"] = l; i += 1; continue
        break
    corps = bloc[i:]
    # le titre est souvent répété en tête du corps
    out["corps"] = "\n".join(corps)
    out["pdfs"] = re.findall(r"^\S+\.pdf$", out["corps"], re.M)
    out["corps"] = "\n".join(l for l in out["corps"].split("\n") if not re.match(r"^\S+\.pdf$", l))
    # contact
    contact = {"entreprise": "", "civilite": "", "nom": "", "adresse": "", "cp": "", "ville": "", "tel": "", "mail": "", "site": ""}
    cm = re.search(r'contact--company">(.*?)</p>', body_html, re.S)
    if cm:
        contact["entreprise"] = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cm.group(1)))).strip()
    adr = re.search(r'contact--col-address">(.*?)</div>', body_html, re.S)
    if adr:
        ps = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", p))).strip() for p in re.findall(r"<p[^>]*>(.*?)</p>", adr.group(1), re.S)]
        ps = [p for p in ps if p]
        for p in ps:
            if re.match(r"^(Monsieur|Madame|Herr|Frau|Signor\w*)\b", p) or re.search(r"\b(med\.|Dr\.?|vét\.|vet\.)", p) and len(p) < 40 and not re.search(r"\d", p):
                contact["civilite"] = (contact["civilite"] + " " + p).strip()
            elif re.match(r"^\d{4}\s+\S", p):
                contact["cp"], contact["ville"] = p[:4], p[5:].strip()
            elif re.search(r"\d", p) and not contact["adresse"]:
                contact["adresse"] = p
            elif not contact["nom"]:
                contact["nom"] = p
            elif not contact["adresse"]:
                contact["adresse"] = p
    tm = re.search(r'link-phone"[^>]*>(.*?)</a>', body_html, re.S)
    if tm:
        contact["tel"] = html.unescape(tm.group(1)).strip()
    em = re.search(r'link-mail"[^>]*>(.*?)</a>', body_html, re.S)
    if em:
        contact["mail"] = html.unescape(re.sub(r"<[^>]+>", "", em.group(1))).strip().lower()
    wm = re.search(r'link-website"[^>]*href="([^"]+)"', body_html)
    if wm:
        contact["site"] = wm.group(1)
    out["contact"] = contact
    out["langue"] = langue(out["corps"], out["canton"])
    return out


def strip_accents(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))


def cle_nue(nom):
    s = strip_accents(nom.lower()).replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]", " ", s)).strip()


def squelette(a, canal):
    """Champs Airtable mécaniques. Ce qui demande un jugement (Pratiques, Expérience, Poste, Gardes,
    Questions, auteur_key, exclusion) est laissé à la compétence — vide ici, jamais deviné."""
    c = a["contact"]
    prenom, nom = "", ""
    if c["nom"]:
        parts = c["nom"].split()
        prenom, nom = (parts[0], " ".join(parts[1:])) if len(parts) > 1 else ("", parts[0])
    f = {
        "Type de post": "Clinique cherche vétérinaire", "Type d'entrée": "Post",
        "Date du post": a["date_pub"], "Lien du post": a["url"],
        "Nom de la clinique": c["entreprise"], "Prénom": prenom, "Nom": nom,
        "Zone de recherche": (c["ville"] + (f" ({a['canton']})" if a["canton"] else "")).strip(),
        "Zones de recherche": ["Suisse"] + ([CANTON_ZONE[a["canton"]]] if a["canton"] in CANTON_ZONE else []),
        "Contenu complet": a["corps"], "Canaux": [canal],
        "Mail1": c["mail"], "Téléphone": c["tel"], "Ville": c["ville"], "CP": c["cp"],
        "Emploi recherché": "Vétérinaire", "Post source": f"Portail emploi SVS, annonce n°{a['numero']}",
    }
    if a["langue"] == "fr":
        f["Langues requises"] = ["Français"]
    elif a["langue"] == "de":
        f["Langues requises"] = ["Allemand"]
    if a["permanent"]:
        f["Statuts contractuels"] = ["CDI"]
    if a["pensum"]:
        lo, hi = (int(x) for x in a["pensum"].split("-"))
        f["Type de temps de travail"] = (["Temps plein"] if lo >= 80 else []) + (["Temps partiel"] if lo < 80 else []) + (["Temps plein"] if lo < 80 <= hi else [])
        f["Type de temps de travail"] = list(dict.fromkeys(f["Type de temps de travail"]))
    md = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", a["des"] or "")
    if md:
        f["Date de disponibilité"] = f"{md.group(3)}-{int(md.group(2)):02d}-{int(md.group(1)):02d}"
    f = {k: v for k, v in f.items() if v not in ("", [], None)}
    return {"fields": f, "_cle_nue": cle_nue(c["entreprise"] or c["nom"]), "_langue": a["langue"], "_jeunes_bienvenus": a["jeunes_bienvenus"],
            "_pensum": a["pensum"], "_des": a["des"], "_site": c["site"], "_civilite": c["civilite"], "_titre": a["titre"], "_canton": a["canton"]}


def en_base(canal):
    """Annonces SVS déjà en base : n° → (recId, corps normalisé de la 1re section)."""
    key = os.environ.get("AIRTABLE_API_KEY")
    if not key:
        sys.exit("AIRTABLE_API_KEY absente : impossible de comparer avec la base. Arrêt (rien collecté).")
    H = {"Authorization": "Bearer " + key}
    out, off = {}, None
    while True:
        q = [("pageSize", "100"), ("filterByFormula", "FIND('gstsvs.ch', {Lien du post})"),
             ("fields[]", "Lien du post"), ("fields[]", "Contenu complet"), ("fields[]", "Numéro"), ("fields[]", "Nom de la clinique"),
             ("fields[]", F_VU_EN_LIGNE)]
        if off:
            q.append(("offset", off))
        d = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.airtable.com/v0/{BASE}/{T_POSTS}?" + urllib.parse.urlencode(q), headers=H)))
        for r in d["records"]:
            f = r["fields"]; m = re.search(r"/annonce/(\d+)", f.get("Lien du post", ""))
            if m:
                # texte complet du record, normalisé : une annonce est « inchangée » si le début de son
                # corps s'y retrouve (les en-têtes [date] lien · canal et les lignes de méta ne comptent pas)
                body = "\n".join(l for l in f.get("Contenu complet", "").split("\n") if not l.startswith("["))
                out[int(m.group(1))] = {"rec": r["id"], "numero": f.get("Numéro"), "clinique": f.get("Nom de la clinique"),
                                        "texte": re.sub(r"\s+", " ", body).strip().lower(), "vu": f.get(F_VU_EN_LIGNE)}
        off = d.get("offset")
        if not off:
            return out
        time.sleep(0.21)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "fiche":
        print(json.dumps(fiche(sys.argv[2]), ensure_ascii=False, indent=1)); return
    if sys.argv[1] != "collect":
        sys.exit(__doc__)
    args = sys.argv[2:]
    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default
    canal, out_path, tout, maxn = opt("--canal"), opt("--out", "svs_raw.json"), "--all" in args, int(opt("--max", "0") or 0)
    if not canal or not re.match(r"^rec[A-Za-z0-9]{14}$", canal):
        sys.exit("--canal recXXXXXXXXXXXXXX obligatoire : le recId du canal « Portail emploi SVS » (table Canaux de diffusion).")
    connus = en_base(canal)
    nums = liste()
    if maxn:
        nums = nums[:maxn]
    annonces, inchangees = [], []
    ignorees = []
    for n in nums:
        a = fiche(n)
        if not a["date_pub"] or a["date_pub"] < "2000" or len(a["corps"]) < 40:
            ignorees.append({"numero": int(n), "raison": "fiche vide ou sans date (résidu du portail)"}); continue
        sig = re.sub(r"\s+", " ", a["corps"]).strip().lower()[:200]
        k = connus.get(int(n))
        if k and sig in k["texte"] and not tout:
            inchangees.append({"numero": int(n), "rec": k["rec"], "post": k["numero"], "clinique": k["clinique"]}); continue
        a["etat"] = "modifiée" if k else "nouvelle"
        a["rec_existant"] = k["rec"] if k else None
        a["squelette"] = squelette(a, canal)
        annonces.append(a)
        time.sleep(0.4)
    en_ligne = {int(n) for n in nums}
    # disparues : seulement sur une lecture complète du portail (--max tronque la liste)
    disparues = [] if maxn else [{"annonce": n, "post": v["numero"], "rec": v["rec"], "clinique": v["clinique"]}
                                 for n, v in connus.items() if n not in en_ligne]
    # « Vu en ligne le » : la seule écriture de ce script, sur les posts déjà en base encore affichés
    marques = 0
    if "--sans-marquer" not in args:
        today = dt.date.today().isoformat()
        a_marquer = [v["rec"] for n, v in connus.items() if n in en_ligne and v.get("vu") != today]
        H = {"Authorization": "Bearer " + os.environ["AIRTABLE_API_KEY"], "Content-Type": "application/json"}
        for i in range(0, len(a_marquer), 10):
            body = {"records": [{"id": rid, "fields": {F_VU_EN_LIGNE: today}} for rid in a_marquer[i:i + 10]]}
            urllib.request.urlopen(urllib.request.Request(f"https://api.airtable.com/v0/{BASE}/{T_POSTS}", data=json.dumps(body).encode(), headers=H, method="PATCH"))
            marques += len(body["records"]); time.sleep(0.21)
    res = {"collecte_le": dt.date.today().isoformat(), "canal": canal, "annonces_en_ligne": len(nums),
           "annonces": annonces, "connues_inchangees": inchangees, "disparues": disparues, "ignorees": ignorees}
    json.dump(res, open(out_path, "w"), ensure_ascii=False, indent=1)
    par_langue = {}
    for a in annonces:
        par_langue[a["langue"]] = par_langue.get(a["langue"], 0) + 1
    print(f"{len(nums)} annonces en ligne · {len(annonces)} à juger ({', '.join(f'{k} : {v}' for k, v in sorted(par_langue.items()))}) · "
          f"{len(inchangees)} déjà en base et inchangées ({marques} « Vu en ligne le » mis à jour) · {len(disparues)} disparues du portail → {out_path}")
    for a in annonces:
        c = a["contact"]
        print(f"  [{a['langue']}] n°{a['numero']} {a['etat']:<9} {c['entreprise'][:40]:<40} {a['canton']:<14} {a['date_pub']} {c['mail']}")
    for d in disparues:
        print(f"  ✖ disparue : annonce n°{d['annonce']} → post n°{d['post']} {d['clinique']} (poste sans doute pourvu, à signaler)")
    for d in ignorees:
        print(f"  · ignorée : annonce n°{d['numero']} ({d['raison']})")


if __name__ == "__main__":
    main()
