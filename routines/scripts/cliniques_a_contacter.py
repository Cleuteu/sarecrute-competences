#!/usr/bin/env python3
"""Cliniques à contacter — score des posts « Clinique cherche vétérinaire » et lot hebdomadaire.

Source de vérité du classement (la copie `sarecrute/airtable/score_posts_cliniques.py` ne sert
plus qu'au rendu PDF local). Lit la base prod Airtable avec la clé AIRTABLE_API_KEY (REST), et :

  * calcule pour chaque post clinique un score /19 et ses raisons (voir score()) ;
  * rapproche le post d'une clinique déjà en base (nom normalisé, mail, téléphone du texte) ;
  * écarte les groupes de cliniques (table « Auteurs posts exclus », types Groupe exclu ET Groupe
    accepté, champ Cliniques.Groupement, signal textuel), les annonces sans mail, les cliniques
    déjà en base — qui ne vont pas dans le lot mais gardent un score ;
  * avec --attribuer : écrit Score / Raisons / Clinique existante sur les posts évalués, puis
    attribue un lot de N posts par recruteuse active (Attribué à, Attribué le, Attribué jusqu'au =
    dimanche de la semaine), en alternant par rang pour que les lots soient de qualité égale.
    Un post attribué il y a moins de 14 jours n'est pas réattribué.

Usage :
  python3 cliniques_a_contacter.py                      # lecture seule, rapport sur stdout
  python3 cliniques_a_contacter.py --attribuer          # écrit + attribue (lot 20 par recruteuse)
  python3 cliniques_a_contacter.py --attribuer --lot 12 --dry-run
  options : --today YYYY-MM-DD  --cache DIR  --rapport fichier.md

Décisions d'Alex et des recruteuses (04 et 10/09/2026) : mail obligatoire pour le lot ; aucun
groupe, même « accepté » au scrape (autre process d'acquisition) ; fraîcheur ≤ 15 j = +4 ; les
cliniques déjà en base relèvent du propriétaire du client, pas d'un nouveau contact ; le lot
expire le dimanche, sans report ; jamais de nouvelle valeur de select.
"""
import os, sys, json, re, collections, datetime as dt, urllib.request, urllib.parse, time, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--attribuer", action="store_true", help="écrit les scores et attribue le lot")
ap.add_argument("--lot", type=int, default=20, help="taille du lot par recruteuse")
ap.add_argument("--dry-run", action="store_true", help="avec --attribuer : calcule, n'écrit rien")
ap.add_argument("--cache", default=None)
ap.add_argument("--rapport", default=None)
ap.add_argument("--today", default=None)
ap.add_argument("--jusquau", default=None, help="fin de validité du lot (défaut : dimanche de la semaine)")
ap.add_argument("--force", action="store_true", help="attribuer même si un lot est encore en cours")
A = ap.parse_args()
today = dt.date.fromisoformat(A.today) if A.today else dt.date.today()

BASE = "appP0W2ISytaNyAhG"
T_POSTS = "Posts scrappés"
F = dict(  # champs de Posts scrappés écrits par ce script
    score="fldXYoTSgsiLIWeCt", raisons="fldZsPy6ohFUjoISj", clinique_existante="fldfPvYIlbDZ8V0sv",
    attribue_a="fld1F3kcHSc4j4i0M", attribue_le="fldcIiPZVcxFm67XS", attribue_jusquau="fld24nHYzT2JlNqgO",
)
KEY = os.environ.get("AIRTABLE_API_KEY")
if not KEY:
    sys.exit("AIRTABLE_API_KEY absente de l'environnement : rien n'est lu ni écrit. Arrêt.")
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def api(method, table, params=None, body=None):
    url = f"https://api.airtable.com/v0/{BASE}/{urllib.parse.quote(table)}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=H, method=method)
    return json.load(urllib.request.urlopen(req))


def fetch(table, params):
    out, offset = [], None
    while True:
        p = dict(params)
        if offset:
            p["offset"] = offset
        d = api("GET", table, p)
        out += d["records"]
        offset = d.get("offset")
        if not offset:
            return out
        time.sleep(0.21)


def load(name, table, params):
    if A.cache and os.path.exists(os.path.join(A.cache, name)):
        return json.load(open(os.path.join(A.cache, name)))
    r = fetch(table, params)
    if A.cache:
        os.makedirs(A.cache, exist_ok=True)
        json.dump(r, open(os.path.join(A.cache, name), "w"), ensure_ascii=False)
    return r


posts = load("posts.json", T_POSTS, {"filterByFormula": "{Type de post}='Clinique cherche vétérinaire'"})
cand = load("candidats.json", "Candidats", {"fields[]": ["Statut Recherche", "Zones de recherche", "county", "Pratiques maitrisées", "Années d'expérience", "Expérience", "Mail", "Téléphone", "Statuts contractuels souhaités", "Type de temps de travail", "Contrat court", "Candidature"], "filterByFormula": "{Statut Recherche}='En recherche active'"})
cl = load("cliniques.json", "Cliniques", {"fields[]": ["Nom de la clinique", "Status commercial", "cliniqueSearch", "county", "Mail1", "Mail2", "Téléphone", "Profil Facebook", "archived", "Propriétaires du client", "Groupement"]})
cands = load("candidatures.json", "Candidatures", {"fields[]": ["Statut candidature", "Candidat"]})
exclus = load("exclus.json", "Auteurs posts exclus", {})
recruteurs = load("recruteurs.json", "Recruteurs", {"filterByFormula": "{Actif}", "fields[]": ["Nom", "Email", "Actif"]})

COUNTRIES = {"France", "Suisse", "Espagne", "Luxembourg", "Belgique", "Polynésie française", "Ile Maurice", "Nouvelle calédonie"}
ORDER = ["Etudiant", "Débutant", "1 à 2 ans", "Autonome", "Spécialiste"]


def country_of(z):
    if z in COUNTRIES:
        return z
    if z.startswith("Canton"):
        return "Suisse"
    if z.startswith("Province"):
        return "Belgique"
    return "France"


# ---------- vivier : candidats actifs, fiche complète, non embauchés ----------
hired = {cid for r in cands if r["fields"].get("Statut candidature") == "Candidat embauché" for cid in r["fields"].get("Candidat", [])}
V = []
for c in cand:
    f = c["fields"]
    if c["id"] in hired:
        continue
    if not (f.get("Zones de recherche") and f.get("Pratiques maitrisées") and (f.get("Années d'expérience") is not None or f.get("Expérience")) and (f.get("Mail") or f.get("Téléphone"))):
        continue
    V.append(f)


def exp_ok(pe, ce):
    if not pe or not ce:
        return True
    if pe == "Spécialiste":
        return ce == "Spécialiste"
    return ORDER.index(ce) >= ORDER.index(pe)


def vivier(f):
    pz = set(f.get("Zones de recherche", [])); pd = pz - COUNTRIES; pc_country = {country_of(z) for z in pz}
    pp = set(f.get("Pratiques requises", [])); pk = set(f.get("Statuts contractuels", []))
    if not pz:
        return None
    n = 0
    for v in V:
        vz = set(v.get("Zones de recherche", []))
        geo = bool(vz & pd) or bool(vz & (pz & COUNTRIES)) or any(z in COUNTRIES and z != "France" and z in pc_country for z in vz)
        if not geo:
            continue
        if pp and not (pp <= set(v.get("Pratiques maitrisées", []))):
            continue
        if not exp_ok(f.get("Expérience"), v.get("Expérience")):
            continue
        vk = set(v.get("Statuts contractuels souhaités", []))
        if pk and vk and not (pk & vk):
            continue
        n += 1
    return n


# ---------- cliniques connues : trois clés ----------
def norm_mail(m): return (m or "").strip().lower().rstrip(".")
def norm_tel(t): return re.sub(r"\D", "", t or "")[-9:]


by_key, by_mail, by_tel = {}, {}, {}
for c in cl:
    f = c["fields"]
    if f.get("cliniqueSearch"):
        by_key[f["cliniqueSearch"]] = (c["id"], f)
    for m in (f.get("Mail1"), f.get("Mail2")):
        if m:
            by_mail[norm_mail(m)] = (c["id"], f)
    if f.get("Téléphone") and len(norm_tel(f["Téléphone"])) == 9:
        by_tel[norm_tel(f["Téléphone"])] = (c["id"], f)

MAIL_RX = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
TEL_RX = re.compile(r"(?:\+33\s?|0)[1-9](?:[ .-]?\d{2}){4}")


def body(f):
    return (f.get("Contenu complet", "") or "").split("Post commenté")[0]


def known(f):
    t = body(f); k = f.get("clinique_key")
    if k and k in by_key:
        return by_key[k], "nom"
    for m in MAIL_RX.findall(t):
        if norm_mail(m) in by_mail:
            return by_mail[norm_mail(m)], "mail"
    for tl in TEL_RX.findall(t):
        if norm_tel(tl) in by_tel:
            return by_tel[norm_tel(tl)], "téléphone"
    return None, None


# ---------- groupes et intermédiaires ----------
EX = {"Auteur": [], "Groupe exclu": [], "Groupe accepté": []}
for r in exclus:
    g = r["fields"]
    if g.get("Actif") and g.get("Valeur") and g.get("Type") in EX:
        EX[g["Type"]].append(g["Valeur"].strip())
BANAL = {"mon véto", "mon veto", "monveto", "mon chat & moi"}


def _low(x): return (x or "").lower()


def match_entry(val, f, t):
    v = _low(val); auteur = _low(f.get("Prénom", "") + " " + f.get("Nom", "")); nom = _low(f.get("Nom de la clinique"))
    if v in auteur or (nom and v in nom):
        return True
    if "." in v or v in BANAL or len(v) < 5:
        sig = " ".join(re.findall(r"[\w.+-]+@[\w.-]+|https?://\S+|www\.\S+", t)).lower()
        return v in sig
    return re.search(r"(?<![\w'’])" + re.escape(v) + r"(?![\w])", t, re.I) is not None


GRP_RX = re.compile(r"\b(?:groupe(?!s? de discussion| facebook| fb| whatsapp| de travail| d'entraide| d'élevages?| d'éleveurs| de (?:\d+|deux|trois|quatre|cinq|six) (?:vétos|vétérinaires|asv|personnes|collègues|confrères))(?: de cliniques| vétérinaire| [A-Z][\w'-]+)?|réseau de (?:cliniques|structures|centres)|notre réseau de|cliniques du groupe|holding|(?:notre|l'|une) enseigne|adhérents? (?:au|à un|du) groupement|groupement [A-Z][\w'-]+)", re.I)
NEG_RX = re.compile(r"(?:aucun|sans|pas de|pas d'un|pas dans un|pas (?:encore )?rachet\w+ par (?:un|des|le)|hors|indépendant\w* de tout|indépendant\w* d'un|indépendant\w* des|n'appartenons? (?:pas )?à aucun|n'appartient (?:pas )?à aucun|à aucun|zéro|ni)\s+(?:grand |gros |grands |petit )?(?:groupe|réseau|enseigne|holding)", re.I)


def groupe(f, t, kf):
    for v in EX["Auteur"]:
        tel = re.sub(r"\D", "", v)
        if (tel and len(tel) >= 9 and tel in re.sub(r"\D", "", t)) or (not tel and match_entry(v, f, t)):
            return "intermédiaire", f"auteur blacklisté « {v} »"
    for typ in ("Groupe exclu", "Groupe accepté"):
        for v in EX[typ]:
            if match_entry(v, f, t):
                return "arbitré", f"{typ.lower()} au scrape : « {v} »"
    if kf and kf.get("Groupement"):
        return "arbitré", f"fiche Clinique rattachée au groupement « {kf['Groupement']} »"
    neg = [m.start() for m in NEG_RX.finditer(t)]
    hits = [m.group(0) for m in GRP_RX.finditer(t) if not any(0 <= m.start() - n <= 60 for n in neg)]
    if hits:
        return "probable", "signal dans le texte : « " + " », « ".join(dict.fromkeys(hits[:3])) + " »"
    return None, None


# ---------- score ----------
def score(f):
    t = body(f); why = []; excl = None
    dates = sorted(set(re.findall(r"^\[(\d{4}-\d{2}-\d{2})\]", t, re.M)))
    if f.get("Date du post"):
        dates = sorted(set(dates + [f["Date du post"]]))
    if not dates:
        dates = [f.get("Date de création", str(today))[:10]]
    last = dt.date.fromisoformat(dates[-1]); first = dt.date.fromisoformat(dates[0])
    age = (today - last).days; span = (last - first).days; n = len(dates)
    st = set(f.get("Statuts contractuels", []))
    if f.get("Type d'entrée") == "Commentaire":
        excl = "commentaire"
    elif st & {"Achat/Vente de clinique", "Prophylaxie", "Internat"} and not (st & {"CDI", "CDD", "Collaboration libérale", "Association"}):
        excl = "hors périmètre : " + ", ".join(sorted(st))
    elif f.get("Contrat court"):
        excl = "mission < 1 mois"
    elif age > 60:
        excl = f"dernière publication il y a {age} j"
    m = vivier(f)
    if excl is None and m == 0:
        excl = "aucun candidat compatible au vivier"
    if excl is None and m is None:
        excl = "pas de département exploitable"
    s = 0
    if n >= 3: s += 2; why.append(f"republié {n} fois")
    elif n == 2: s += 1; why.append("republié 2 fois")
    if span >= 30: s += 1; why.append(f"cherche depuis {span} j")
    urg = re.search(r"\burgen\w*|d[èe]s que possible|au plus (?:vite|tôt)|dès maintenant|immédiat\w*", t, re.I)
    if urg: s += 1; why.append(f"urgence (« {urg.group(0)} »)")
    plural = re.search(r"\b(?:2|deux|3|trois|plusieurs) (?:vétérinaires|vétos|postes)", t, re.I)
    if plural: s += 1; why.append(f"plusieurs postes (« {plural.group(0)} »)")
    if m:
        s += 4 if m >= 10 else 3 if m >= 6 else 2 if m >= 3 else 1
        why.append(f"{m} candidat(s) compatible(s)")
    if st & {"CDI", "Association", "Collaboration libérale"}: s += 2; why.append("/".join(sorted(st & {"CDI", "Association", "Collaboration libérale"})))
    elif st == {"CDD"}: s += 1; why.append("CDD seul")
    elif not st: s += 1; why.append("contrat non précisé")
    if "Temps plein" in set(f.get("Type de temps de travail", [])): s += 1; why.append("temps plein")
    j = []
    if f.get("Nom de la clinique"): s += 1; j.append("nom")
    mails = MAIL_RX.findall(t); tels = TEL_RX.findall(t)
    if mails: s += 1; j.append("mail")
    if tels: s += 1; j.append("tél")
    if j: why.append("joignable : " + ", ".join(j))
    if age <= 15: s += 4; why.append(f"dernière publication il y a {age} j")
    elif age <= 30: s += 2; why.append(f"dernière publication il y a {age} j")
    else: why.append(f"dernière publication il y a {age} j")
    kc, how = known(f)
    kid, kf = kc if kc else (None, None)
    glabel, gwhy = groupe(f, t, kf)
    if glabel == "intermédiaire":
        excl = excl or gwhy
    has_mail = bool(mails) or bool(kf and (kf.get("Mail1") or kf.get("Mail2")))
    tels_n = {}
    for tl in tels:
        tels_n.setdefault(norm_tel(tl), re.sub(r"[ .-]", "", tl))
    return dict(score=s, excl=excl, why=why, age=age, n=n, span=span, m=m, mails=sorted({norm_mail(x) for x in mails}),
                tels=sorted(tels_n.values()), known_id=kid, known=kf, how=how, groupe=glabel, groupe_why=gwhy, has_mail=has_mail)


rows = []
for p in posts:
    r = score(p["fields"]); r["id"] = p["id"]; r["f"] = p["fields"]; rows.append(r)
elig = [r for r in rows if r["excl"] is None]
groupes = [r for r in elig if r["groupe"]]
sans_mail = [r for r in elig if not r["groupe"] and not r["known"] and not r["has_mail"]]
new = [r for r in elig if not r["groupe"] and not r["known"] and r["has_mail"]]
relance = [r for r in elig if not r["groupe"] and r["known"] and r["known"].get("Status commercial") not in ("Signé", "Refusé", "Annonce plus dispo")]
ecart = [r for r in elig if not r["groupe"] and r["known"] and r["known"].get("Status commercial") in ("Signé", "Refusé", "Annonce plus dispo")]
excl_count = collections.Counter(r["excl"].split(":")[0].split(" il y a")[0] for r in rows if r["excl"])


def raisons(r):
    """Une ligne lisible par la recruteuse ; le score seul ne dit rien."""
    if r["excl"]:
        return "Exclu : " + r["excl"]
    pre = ""
    if r["groupe"]:
        pre = f"Groupe de cliniques ({r['groupe']} — {r['groupe_why']}) : hors prospection. "
    elif r["known"]:
        pre = f"Déjà en base (statut {r['known'].get('Status commercial')}, rapprochée par {r['how']}) : relance du propriétaire, pas un nouveau contact. "
    elif not r["has_mail"]:
        pre = "Sans mail dans l'annonce : contact Facebook seulement. "
    return pre + " ; ".join(r["why"])


# ---------- attribution du lot ----------
def prochain_dimanche(d):
    return d + dt.timedelta(days=(6 - d.weekday()) % 7)


def attribuer():
    recs = sorted([r["fields"] for r in recruteurs if r["fields"].get("Email")], key=lambda x: x.get("Nom", ""))
    if not recs:
        sys.exit("Aucune recruteuse active avec un e-mail dans la table Recruteurs : pas d'attribution.")
    en_cours = [r for r in rows if r["f"].get("Attribué jusqu'au") and dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) >= today]
    if en_cours and not A.force:
        return recs, None, max(dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) for r in en_cours), 0, 0
    limite = today - dt.timedelta(days=14)
    pool = []
    for r in sorted(new, key=lambda r: (-r["score"], r["age"])):
        al = r["f"].get("Attribué le")
        if al and dt.date.fromisoformat(al) > limite:
            continue
        pool.append(r)
    lots = {x["Email"]: [] for x in recs}
    for i, r in enumerate(pool[: A.lot * len(recs)]):
        lots[recs[i % len(recs)]["Email"]].append(r)
    jusquau = dt.date.fromisoformat(A.jusquau) if A.jusquau else prochain_dimanche(today)
    updates = {}
    for r in rows:
        upd = {F["score"]: r["score"] if r["excl"] is None else None, F["raisons"]: raisons(r),
               F["clinique_existante"]: [r["known_id"]] if r["known_id"] else []}
        updates[r["id"]] = upd
    for email, lot in lots.items():
        for r in lot:
            updates[r["id"]].update({F["attribue_a"]: {"email": email}, F["attribue_le"]: str(today), F["attribue_jusquau"]: str(jusquau)})
    if not A.dry_run:
        items = [{"id": rid, "fields": flds} for rid, flds in updates.items()]
        for i in range(0, len(items), 10):
            api("PATCH", T_POSTS, body={"records": items[i:i + 10]})
            time.sleep(0.21)
    return recs, lots, jusquau, len(pool), len(updates)


# ---------- rapport ----------
def ligne(r):
    f = r["f"]; zone = f.get("Zone de recherche") or f.get("conv_county") or "?"
    contact = ", ".join(r["mails"] + r["tels"]) or "pas de contact dans le texte"
    return f"- **{f.get('conv_nom_clinique')}** — {zone} · score {r['score']}/19 · post n°{f.get('Numéro')} · {contact}\n  {' ; '.join(r['why'])}"


out = [f"# Cliniques à contacter — {today.strftime('%d/%m/%Y')}", "",
       f"{len(rows)} posts clinique évalués, {len(elig)} éligibles : {len(new)} nouvelles avec mail, {len(groupes)} groupes, {len(sans_mail)} sans mail, {len(relance)} déjà en base en cours, {len(ecart)} Signé/Refusé.",
       "Exclus : " + ", ".join(f"{k} {v}" for k, v in excl_count.most_common()) + ".", ""]
if A.attribuer:
    recs, lots, jusquau, npool, nupd = attribuer()
    if lots is None:
        out.append(f"## Lot en cours jusqu'au {jusquau.strftime('%d/%m')} : pas de nouvelle attribution")
        out.append("Un lot hebdomadaire est encore valide ; les scores n'ont pas été réécrits non plus. Relancer après sa date de fin, ou avec --force pour attribuer quand même.")
        lots = {}
    else:
        out.append(f"## Lots de la semaine (jusqu'au {jusquau.strftime('%d/%m')}){' — SIMULATION, rien écrit' if A.dry_run else ''}")
        out.append(f"Réservoir : {npool} posts attribuables (non attribués depuis 14 j). {nupd} posts {'auraient été' if A.dry_run else ''} mis à jour (Score, Raisons, Clinique existante).")
        for x in recs:
            lot = lots[x["Email"]]
            out.append(f"\n### {x.get('Nom')} — {len(lot)} clinique(s)")
            out += [ligne(r) for r in lot]
        if npool < A.lot * len(recs):
            out.append(f"\n⚠️ Réservoir insuffisant pour {A.lot} par recruteuse : lots réduits plutôt que gonflés avec des annonces sans mail.")
else:
    out.append("## Top 20 nouvelles cliniques avec mail (lecture seule)")
    out += [ligne(r) for r in sorted(new, key=lambda r: (-r["score"], r["age"]))[:20]]
probables = [r for r in groupes if r["groupe"] == "probable"]
if probables:
    out.append("\n## Groupes probables à faire arbitrer par Alex (blacklist scrape-veto)")
    out += [f"- n°{r['f'].get('Numéro')} {r['f'].get('conv_nom_clinique')} ({r['f'].get('conv_county')}) : {r['groupe_why']}" for r in probables]
txt = "\n".join(out)
print(txt)
if A.rapport:
    open(A.rapport, "w").write(txt + "\n")
