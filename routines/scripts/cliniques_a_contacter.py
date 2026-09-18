#!/usr/bin/env python3
"""Cliniques à contacter — score des posts « Clinique cherche vétérinaire » et lot hebdomadaire.

Seule implémentation du classement (l'ancien script local et son rendu PDF ont été supprimés le
10/09/2026 : le score se lit dans Airtable). Lit la base prod avec la clé AIRTABLE_API_KEY (REST), et :

  * calcule pour chaque post clinique un score /23 et ses raisons (voir score()) ;
  * rapproche le post d'une clinique déjà en base (nom normalisé, mail, téléphone du texte) ;
  * écarte les groupes de cliniques (table « Auteurs posts exclus », types Groupe exclu ET Groupe
    accepté, champ Cliniques.Groupement, signal textuel), les annonces sans mail, les cliniques
    déjà en base — qui ne vont pas dans le lot mais gardent un score ;
  * avec --attribuer : écrit Score / Raisons / Clinique existante sur les posts évalués, puis
    attribue un lot de N cliniques par recruteuse active (Attribué à, Attribué le, Attribué
    jusqu'au = dimanche de la semaine), à charge égale et par rang de score pour que les lots
    soient de qualité comparable. La routine cloud tourne le lundi matin : le lot de la semaine
    précédente a expiré la veille, un nouveau lot est régénéré chaque lundi.
    Une clinique = une recruteuse (décision d'Alex, 14/09/2026) : les posts sont regroupés par
    clinique (fiche liée, nom normalisé, mail, téléphone), un seul post par clinique part dans un
    lot, et une clinique déjà attribuée revient toujours à la même recruteuse, semaine après
    semaine — si son lot est plein, la clinique attend ; elle ne passe jamais à l'autre. Une
    clinique attribuée il y a moins de 14 jours n'est pas réattribuée, par quelque post que ce soit.

Usage :
  python3 cliniques_a_contacter.py                      # lecture seule, rapport sur stdout
  python3 cliniques_a_contacter.py --attribuer          # écrit + attribue (lot 10 par recruteuse)
  python3 cliniques_a_contacter.py --attribuer --lot 12 --dry-run
  python3 cliniques_a_contacter.py --attribuer --force --rejouer   # recalcule le lot en cours
  python3 cliniques_a_contacter.py --attribuer --recharger --lot 10   # commande de la routine :
      lot du lundi si aucun lot n'est en cours, puis recharge automatique de N cliniques pour chaque
      recruteuse dont le lot en cours est épuisé (toutes ses cliniques archivées ou converties). Sans plafond.
      (--rejouer garde les attributions en cours tant que les données n'ont pas bougé : un post
       mieux classé scrappé entre-temps peut déplacer et libérer le dernier post d'un lot)
  options : --today YYYY-MM-DD  --cache DIR  --rapport fichier.md

Décisions d'Alex et des recruteuses (04, 10 et 14/09/2026) : mail obligatoire pour le lot ; aucun
groupe, même « accepté » au scrape (autre process d'acquisition) ; fraîcheur ≤ 15 j = +4 ; les
cliniques déjà en base relèvent du propriétaire du client, pas d'un nouveau contact ; le lot
expire le dimanche, sans report ; cible des recruteuses (17/09/2026, message de Sarah) = bonus +2 poste
ouvert aux débutants, +2 région demandée ou clinique de campagne/mixte/équine (voir cible()) ; une clinique n'est jamais partagée entre deux recruteuses (pas
de doublon de communication) ; jamais de nouvelle valeur de select.

Adhérents Vetcoop (décision d'Alex, 18/09/2026) : SaRecrute est partenaire recrutement du groupement
d'achat Vetcoop (tarifs membres, commission d'apport d'affaires, non-sollicitation). Le script lit la
table « Adhérents Vetcoop » et reconnaît un post d'adhérent par la case « Membre Vetcoop » du post ou de
la fiche Clinique rapprochée, par mail, par domaine de mail (hors domaines génériques) ou par nom
normalisé ; il coche alors « Membre Vetcoop » sur le post (jamais décoché). Un post d'adhérent est
retenu même sans candidat compatible au vivier, lourdement pondéré (« +10 adhérent Vetcoop », score
/33), passe en tête du réservoir, revient dans le réservoir chaque semaine tant qu'il n'est ni converti
ni archivé (la règle des 14 jours ne le retient pas), et ne part QU'À la recruteuse VETCOOP_RECRUTEUSE
(Sarah) : si la clinique appartient déjà à l'autre recruteuse, ou si Sarah n'est pas active, le post
n'est pas attribué et le rapport le signale en « arbitrage ». Avec --vetcoop-immediat (dans la commande
de la routine), un adhérent nouvellement détecté entre dans le lot EN COURS de Sarah sans attendre le
lundi. Les autres exclusions (commentaire, hors périmètre, > 60 j, intermédiaire) s'appliquent.

Mails d'intro (même décision) : avec --dossier-mails fichier.json, le script exporte les posts du lot en
cours (Attribué jusqu'au ≥ aujourd'hui, ni archivés ni convertis) dont « Mail intro proposé » est vide,
avec tout ce que la routine peut lire pour rédiger (champs de scrape-veto, texte, recruteuse, Vetcoop).
La routine rédige, puis ecrire_mails_intro.py écrit le champ avec ses garde-fous. Ce script-ci ne
rédige rien.
"""
import os, sys, json, re, collections, datetime as dt, urllib.request, urllib.parse, time, argparse, unicodedata

ap = argparse.ArgumentParser()
ap.add_argument("--attribuer", action="store_true", help="écrit les scores et attribue le lot")
ap.add_argument("--lot", type=int, default=10, help="taille du lot par recruteuse")
ap.add_argument("--dry-run", action="store_true", help="avec --attribuer : calcule, n'écrit rien")
ap.add_argument("--cache", default=None)
ap.add_argument("--rapport", default=None)
ap.add_argument("--today", default=None)
ap.add_argument("--jusquau", default=None, help="fin de validité du lot (défaut : dimanche de la semaine)")
ap.add_argument("--force", action="store_true", help="attribuer même si un lot est encore en cours")
ap.add_argument("--rejouer", action="store_true", help="recalcule le lot de même date de fin au lieu d'en créer un second")
ap.add_argument("--recharger", action="store_true", help="sert N cliniques de plus à chaque recruteuse dont le lot en cours est épuisé")
ap.add_argument("--dossier-mails", default=None, help="exporte en JSON les posts du lot en cours sans « Mail intro proposé », pour la rédaction par la routine")
ap.add_argument("--vetcoop-immediat", action="store_true", help="ajoute au lot en cours de Sarah les adhérents Vetcoop pas encore attribués, sans attendre le lundi")
A = ap.parse_args()
# date « du jour » en heure de Paris : la routine cloud tourne en UTC, et un lundi 01:00 à Paris est
# encore dimanche en UTC — le lot partirait avec la mauvaise date de fin et le garde-fou se tromperait.
from zoneinfo import ZoneInfo
today = dt.date.fromisoformat(A.today) if A.today else dt.datetime.now(ZoneInfo("Europe/Paris")).date()

BASE = "appP0W2ISytaNyAhG"
T_POSTS = "Posts scrappés"
T_RECRUTEURS = "Recruteurs"
F = dict(  # champs de Posts scrappés écrits par ce script
    score="fldXYoTSgsiLIWeCt", raisons="fldZsPy6ohFUjoISj", clinique_existante="fldfPvYIlbDZ8V0sv",
    attribue_a="fld1F3kcHSc4j4i0M", attribue_le="fldcIiPZVcxFm67XS", attribue_jusquau="fld24nHYzT2JlNqgO",
    membre_vetcoop="fld7UJUNeJ4nlxDlO",
)
F_MAIL_INTRO = "fldrOglkyBQ6grgGo"  # Posts scrappés.« Mail intro proposé » : écrit par ecrire_mails_intro.py, jamais ici
VETCOOP_RECRUTEUSE = "Sarah"  # prénom dans Recruteurs.Nom : les adhérents Vetcoop ne partent qu'à elle
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
cl = load("cliniques.json", "Cliniques", {"fields[]": ["Nom de la clinique", "Status commercial", "cliniqueSearch", "county", "Mail1", "Mail2", "Téléphone", "Profil Facebook", "archived", "Propriétaires du client", "Groupement", "Membre Vetcoop"]})
cands = load("candidatures.json", "Candidatures", {"fields[]": ["Statut candidature", "Candidat"]})
exclus = load("exclus.json", "Auteurs posts exclus", {})
recruteurs = load("recruteurs.json", T_RECRUTEURS, {"filterByFormula": "{Actif}", "fields[]": ["Nom", "Email", "Actif"]})
adherents = load("adherents_vetcoop.json", "Adhérents Vetcoop", {"filterByFormula": "NOT({Sorti})", "fields[]": ["Nom adhérent", "Email 1", "Email 2"]})
canaux = {r["id"]: r["fields"].get("Name", "") for r in load("canaux.json", "Canaux de diffusion", {"fields[]": ["Name"]})}
NOMS = {r["fields"]["Email"]: r["fields"].get("Nom", r["fields"]["Email"]) for r in recruteurs if r["fields"].get("Email")}

COUNTRIES = {"France", "Suisse", "Espagne", "Luxembourg", "Belgique", "Polynésie française", "Ile Maurice", "Nouvelle calédonie"}
ORDER = ["Etudiant", "Débutant", "1 à 2 ans", "Autonome", "Spécialiste"]


# ---------- cible des recruteuses (retour de Sarah, 17/09/2026) ----------
# « Viser les postes pour débutants dans des régions demandées (nord, bretagne, sud, frontière belge /
# suisse, IDF, savoie / pyrénées, toulouse, sud-ouest, gironde) ou clinique de campagne : poste en mixte
# ou rurale, ou équine 100 % / majoritaire équine. » C'est un bonus au score, pas un filtre : Sarah a
# converti des cliniques hors cible (Bas-Rhin, Maine-et-Loire). La traduction des régions en
# départements est une interprétation à faire valider par les recruteuses.
REGIONS_DEMANDEES = {
    "nord": {"59", "62", "80", "02", "60"},
    "frontière belge": {"59", "02", "08", "55", "54"},
    "bretagne": {"22", "29", "35", "56"},
    "sud": {"04", "05", "06", "13", "83", "84", "11", "30", "34", "66"},
    "frontière suisse": {"01", "25", "39", "68", "74", "90"},
    "IDF": {"75", "77", "78", "91", "92", "93", "94", "95"},
    "savoie": {"73", "74"},
    "pyrénées": {"09", "31", "64", "65", "66"},
    "toulouse": {"31", "81", "82", "32"},
    "sud-ouest": {"33", "40", "47", "24", "64", "65", "32", "31", "81", "82", "46"},
    "gironde": {"33"},
}
RURAL = {"Bovins", "Allaitant", "Laitier", "Ovin/Caprin", "Porcin", "Volailles"}
DEB_RX = re.compile(r"jeunes? dipl[ôo]m\w+|d[ée]butant\w*|sortie? d'?[ée]cole|premi[èe]re? (?:expérience|poste)|junior", re.I)
DEB_NEG_RX = re.compile(r"(?:pas|non|aucun|sans)\s+(?:de\s+|d')?(?:profils?\s+)?(?:jeunes? dipl[ôo]m|d[ée]butant|junior)", re.I)
CAMP_RX = re.compile(r"\b(?:mixte|rural\w*|campagne|[ée]quins?|chevaux|bovins?)\b", re.I)


def cible(f, t):
    """Bonus « cible des recruteuses » : +2 poste ouvert aux débutants, +2 région demandée ou clinique de campagne."""
    pts, why = 0, []
    e = f.get("Expérience")
    if e in ("Débutant", "Etudiant"):
        pts += 2; why.append("ouvert aux débutants")
    elif not e and DEB_RX.search(t) and not DEB_NEG_RX.search(t):
        pts += 2; why.append(f"ouvert aux débutants (« {DEB_RX.search(t).group(0)} »)")
    depts = {z[:2] for z in f.get("Zones de recherche", []) if z[:2].isdigit()}
    regions = [k for k, v in REGIONS_DEMANDEES.items() if depts & v]
    prat = set(f.get("Pratiques requises", [])) | set(f.get("Pratiques optionnelles", []))
    camp = sorted(prat & (RURAL | {"Equine"}))
    if regions:
        pts += 2; why.append("région demandée : " + ", ".join(regions))
    elif camp:
        pts += 2; why.append("clinique de campagne : " + ", ".join(camp))
    elif CAMP_RX.search(t):
        pts += 2; why.append(f"clinique de campagne (« {CAMP_RX.search(t).group(0)} »)")
    return pts, why


# ---------- langue de l'annonce (décision d'Alex, 18/09/2026 : pas de clinique germanophone ni italophone dans le lot) ----------
DE_RX = re.compile(r"\b(?:wir|und|für|mit|eine[nr]?|unsere[rn]?|suchen|Tierärztin|Tierarzt|Praxis|Stelle|Bewerbung|gesucht|Kleintier\w*|Grosstier\w*|Gemischtpraxis|Verstärkung|Team)\b", re.I)
IT_RX = re.compile(r"\b(?:cerchiamo|veterinari[oa]|clinica|ambulatorio|assunzione|candidatura|lavoro|siamo|nostro|nostra|per il|della|degli)\b", re.I)
FR_RX = re.compile(r"\b(?:nous|vous|pour|avec|recherch\w+|vétérinaire|cabinet|clinique|poste|équipe|candidature|recrut\w+)\b", re.I)


def langue_annonce(f, t):
    """« de », « it » ou « fr ». D'abord l'exigence posée par le scrape (Langues requises sans Français), puis le texte."""
    lr = set(f.get("Langues requises", []))
    if lr and "Français" not in lr:
        if "Allemand" in lr:
            return "de"
        if "Italien" in lr:
            return "it"
    corps = t[:3000]
    de, it, fr = len(DE_RX.findall(corps)), len(IT_RX.findall(corps)), len(FR_RX.findall(corps))
    if de >= 8 and de > 2 * fr:
        return "de"
    if it >= 8 and it > 2 * fr:
        return "it"
    return "fr"


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


def mails_de(f, t):
    """Adresses de l'annonce : texte du post + champs miroirs Mail1/Mail2 (posés au scrape ou par la recruteuse)."""
    ms = MAIL_RX.findall(t)
    for k in ("Mail1", "Mail2"):
        v = (f.get(k) or "").strip()
        if v and MAIL_RX.fullmatch(v):
            ms.append(v)
    return ms


def known(f):
    t = body(f); k = f.get("clinique_key")
    if k and k in by_key:
        return by_key[k], "nom"
    for m in mails_de(f, t):
        if norm_mail(m) in by_mail:
            return by_mail[norm_mail(m)], "mail"
    for tl in TEL_RX.findall(t):
        if norm_tel(tl) in by_tel:
            return by_tel[norm_tel(tl)], "téléphone"
    return None, None


# ---------- adhérents Vetcoop ----------
GENERIQUES = {"gmail.com", "googlemail.com", "hotmail.com", "hotmail.ch", "hotmail.fr", "yahoo.fr", "yahoo.com", "bluewin.ch",
              "gmx.ch", "gmx.net", "gmx.de", "outlook.com", "outlook.fr", "icloud.com", "me.com", "sunrise.ch", "protonmail.com",
              "proton.me", "live.fr", "live.com", "orange.fr", "wanadoo.fr", "free.fr", "laposte.net", "sfr.fr", "hispeed.ch"}
_NOM_STOP = re.compile(r"\b(?:sarl|sàrl|sa|ag|gmbh|sàrl\.|dr|dre|med|méd|vet|vét|cabinet|clinique|veterinaire|vétérinaire|tierarztpraxis|tierarzt|tierärzte|praxis|kleintierpraxis|tierklinik|centre|le|la|les|du|de|des|d)\b")


def norm_nom(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _NOM_STOP.sub(" ", re.sub(r"[^a-z0-9]+", " ", s))
    return re.sub(r"\s+", " ", s).strip()


AD_MAILS, AD_DOM, AD_NOMS = {}, {}, {}
for _r in adherents:
    _g = _r["fields"]; _nom = _g.get("Nom adhérent", "")
    for _m in (_g.get("Email 1"), _g.get("Email 2")):
        if _m:
            AD_MAILS[norm_mail(_m)] = _nom
            _d = norm_mail(_m).split("@")[-1]
            if _d and _d not in GENERIQUES:
                AD_DOM[_d] = _nom
    _k = norm_nom(_nom)
    if len(_k) >= 6:  # un nom trop court (« mutts ») matcherait n'importe quoi
        AD_NOMS[_k] = _nom


def vetcoop(f, t, kf):
    """Le post vient-il d'un adhérent Vetcoop ? Renvoie le motif (lisible dans Raisons) ou None.
    Ordre : case du post, fiche Clinique rapprochée, mail exact, domaine non générique, nom normalisé."""
    if f.get("Membre Vetcoop"):
        return "case cochée sur le post"
    if kf and kf.get("Membre Vetcoop"):
        return "fiche Clinique cochée"
    ms = [norm_mail(m) for m in mails_de(f, t)]
    for m in ms:
        if m in AD_MAILS:
            return f"mail de l'adhérent « {AD_MAILS[m]} »"
    for m in ms:
        d = m.split("@")[-1]
        if d in AD_DOM:
            return f"domaine de l'adhérent « {AD_DOM[d]} »"
    k = norm_nom(f.get("Nom de la clinique"))
    if k and k in AD_NOMS:
        return f"nom de l'adhérent « {AD_NOMS[k]} »"
    return None


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
    if f.get("Vu en ligne le"):  # sources hors Facebook (portail SVS) : encore affichée = encore ouverte
        dates = sorted(set(dates + [f["Vu en ligne le"][:10]]))
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
    elif langue_annonce(f, t) != "fr":
        excl = "annonce en " + {"de": "allemand", "it": "italien"}[langue_annonce(f, t)]
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
    mails = mails_de(f, t); tels = TEL_RX.findall(t)
    if mails: s += 1; j.append("mail")
    if tels: s += 1; j.append("tél")
    if j: why.append("joignable : " + ", ".join(j))
    pc, cw = cible(f, t); s += pc; why += cw
    if age <= 15: s += 4; why.append(f"dernière publication il y a {age} j")
    elif age <= 30: s += 2; why.append(f"dernière publication il y a {age} j")
    else: why.append(f"dernière publication il y a {age} j")
    kc, how = known(f)
    kid, kf = kc if kc else (None, None)
    glabel, gwhy = groupe(f, t, kf)
    if glabel == "intermédiaire":
        excl = excl or gwhy
    vc = vetcoop(f, t, kf)
    if vc:
        # un adhérent qui cherche est retenu même si le vivier ne donne rien aujourd'hui : c'est Sarah qui décide
        if excl in ("aucun candidat compatible au vivier", "pas de département exploitable"):
            why.append(f"adhérent Vetcoop : retenu malgré « {excl} »"); excl = None
        s += 10; why.append(f"adhérent Vetcoop ({vc})")
    has_mail = bool(mails) or bool(kf and (kf.get("Mail1") or kf.get("Mail2")))
    tels_n = {}
    for tl in tels:
        tels_n.setdefault(norm_tel(tl), re.sub(r"[ .-]", "", tl))
    return dict(score=s, excl=excl, why=why, age=age, n=n, span=span, m=m, mails=sorted({norm_mail(x) for x in mails}),
                tels=sorted(tels_n.values()), known_id=kid, known=kf, how=how, groupe=glabel, groupe_why=gwhy, has_mail=has_mail,
                vetcoop=vc)


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


# ---------- une clinique = une recruteuse : regrouper les posts d'une même clinique ----------
def signaux_clinique(r):
    """Ce qui identifie la clinique d'un post : fiche liée, nom normalisé, mails et téléphones du texte."""
    s = set()
    if r["known_id"]:
        s.add(("fiche", r["known_id"]))
    if r["f"].get("clinique_key"):
        s.add(("nom", r["f"]["clinique_key"]))
    for m in r["mails"]:
        s.add(("mail", m))
    for t in r["tels"]:
        if len(norm_tel(t)) == 9:
            s.add(("tel", norm_tel(t)))
    return s


_parent = {}


def _find(x):
    _parent.setdefault(x, x)
    while _parent[x] != x:
        _parent[x] = _parent[_parent[x]]
        x = _parent[x]
    return x


def _union(a, b):
    ra, rb = _find(a), _find(b)
    if ra != rb:
        _parent[ra] = rb


_par_signal = collections.defaultdict(list)
for r in rows:
    for sig in signaux_clinique(r):
        _par_signal[sig].append(r["id"])
for _ids in _par_signal.values():  # deux posts qui partagent un signal sont la même clinique
    for _i in _ids[1:]:
        _union(_ids[0], _i)
for r in rows:
    r["clinique"] = _find(r["id"])


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


def _proprio_recentes(exclure=frozenset()):
    """Propriétaire de chaque clinique (dernière recruteuse servie) et cliniques servies il y a moins de 14 j."""
    limite = today - dt.timedelta(days=14)
    proprio, recentes = {}, set()
    for r in sorted([x for x in rows if x["id"] not in exclure and x["f"].get("Attribué à") and x["f"].get("Attribué le")],
                    key=lambda x: x["f"]["Attribué le"]):
        proprio[r["clinique"]] = r["f"]["Attribué à"].get("email")
        if dt.date.fromisoformat(r["f"]["Attribué le"]) > limite:
            recentes.add(r["clinique"])
    return proprio, recentes


def ordre_pool(r):
    """Adhérents Vetcoop d'abord (ils doivent partir), puis score décroissant, puis fraîcheur."""
    return (not r["vetcoop"], -r["score"], r["age"])


def sarah_email(recs_fields):
    """E-mail de la recruteuse Vetcoop parmi les recruteuses actives, None si absente."""
    return next((x["Email"] for x in recs_fields if VETCOOP_RECRUTEUSE.lower() in (x.get("Nom") or "").lower()), None)


def _pool(recentes):
    """Réservoir : nouvelles cliniques avec mail, adhérents Vetcoop en tête puis par score, un seul post par clinique, hors cliniques chaudes."""
    pool, vues = [], set()
    for r in sorted(new, key=ordre_pool):
        if r["clinique"] in vues:
            continue
        if r["clinique"] in recentes and not r["vetcoop"]:
            continue  # un adhérent Vetcoop revient chaque semaine tant qu'il n'est pas traité
        vues.add(r["clinique"])
        pool.append(r)
    return pool


def _patch(table, updates):
    items = [{"id": rid, "fields": flds} for rid, flds in updates.items()]
    for i in range(0, len(items), 10):
        api("PATCH", table, body={"records": items[i:i + 10]})
        time.sleep(0.21)


_INV = {v: k for k, v in F.items()}
_NOMS = {"attribue_a": "Attribué à", "attribue_le": "Attribué le", "attribue_jusquau": "Attribué jusqu'au"}


def _memoriser(updates):
    """Reporte les champs d'attribution écrits dans les copies en mémoire des posts (rows[...]["f"])."""
    by_id = {r["id"]: r for r in rows}
    for rid, flds in updates.items():
        for fid, val in flds.items():
            nom = _NOMS.get(_INV.get(fid))
            if nom:
                by_id[rid]["f"][nom] = val
            if nom is None:
                continue
        # Attribué à : la REST renvoie un objet collaborateur ; on garde la même forme
        if F["attribue_a"] in flds and flds[F["attribue_a"]]:
            by_id[rid]["f"]["Attribué à"] = {"email": flds[F["attribue_a"]]["email"]}


def attribuer():
    recs = sorted([r["fields"] for r in recruteurs if r["fields"].get("Email")], key=lambda x: x.get("Nom", ""))
    if not recs:
        sys.exit("Aucune recruteuse active avec un e-mail dans la table Recruteurs : pas d'attribution.")
    jusquau = dt.date.fromisoformat(A.jusquau) if A.jusquau else prochain_dimanche(today)
    # --rejouer : le lot de même date de fin est recalculé, pas doublé — ses posts redeviennent libres
    lot_courant = {r["id"] for r in rows if A.rejouer and r["f"].get("Attribué jusqu'au") == str(jusquau)}
    en_cours = [r for r in rows if r["id"] not in lot_courant and r["f"].get("Attribué jusqu'au")
                and dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) >= today]
    if en_cours and not A.force:
        return recs, None, max(dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) for r in en_cours), 0, 0, 0, []
    rang = {r["id"]: i for i, r in enumerate(sorted(new, key=ordre_pool))}
    # une clinique appartient à la recruteuse qui l'a eue en dernier, et reste chaude 14 j
    proprio, recentes = _proprio_recentes(lot_courant)
    # --rejouer : le lot recalculé garde ses attributions (les recruteuses ont pu commencer à
    # appeler) ; si deux se partagent une clinique, elle va à celle qui tient le post le mieux
    # classé et l'autre post est libéré. Une clinique déjà détenue les semaines d'avant lui reste.
    for r in sorted([x for x in rows if x["id"] in lot_courant and x["f"].get("Attribué à")],
                    key=lambda x: rang.get(x["id"], len(rang))):
        proprio.setdefault(r["clinique"], r["f"]["Attribué à"].get("email"))
    actifs = {x["Email"] for x in recs}
    pool = _pool(recentes)
    ordre = [x["Email"] for x in recs]
    lots = {e: [] for e in ordre}
    sarah = sarah_email(recs)
    arbitrages = []  # adhérents Vetcoop qu'on ne peut pas donner à Sarah sans décision humaine
    for r in pool:
        p = proprio.get(r["clinique"])
        if r["vetcoop"]:
            # un adhérent Vetcoop ne part qu'à Sarah (décision d'Alex, 18/09/2026)
            if not sarah:
                arbitrages.append((r, f"{VETCOOP_RECRUTEUSE} absente des recruteuses actives")); continue
            if p and p in actifs and p != sarah:
                arbitrages.append((r, f"clinique déjà attribuée à {NOMS.get(p, p)} : ne change pas de main sans arbitrage")); continue
            if len(lots[sarah]) >= A.lot:
                arbitrages.append((r, f"lot de {NOMS.get(sarah, sarah)} complet : attendra la semaine prochaine")); continue
            cible = sarah
        elif p and p in actifs:
            if len(lots[p]) >= A.lot:
                continue  # sa recruteuse a son compte : la clinique attendra la semaine prochaine
            cible = p
        else:
            libres = [e for e in ordre if len(lots[e]) < A.lot]
            if not libres:
                break
            cible = min(libres, key=lambda e: (len(lots[e]), ordre.index(e)))
        lots[cible].append(r)
    updates = {}
    for r in rows:
        upd = {F["score"]: r["score"] if r["excl"] is None else None, F["raisons"]: raisons(r),
               F["clinique_existante"]: [r["known_id"]] if r["known_id"] else []}
        if r["vetcoop"] and not r["f"].get("Membre Vetcoop"):
            upd[F["membre_vetcoop"]] = True  # on coche, on ne décoche jamais
        updates[r["id"]] = upd
    attribues = set()
    for email, lot in lots.items():
        for r in lot:
            updates[r["id"]].update({F["attribue_a"]: {"email": email}, F["attribue_le"]: str(today), F["attribue_jusquau"]: str(jusquau)})
            attribues.add(r["id"])
    liberes = lot_courant - attribues  # sortis du lot recalculé : on rend les posts au réservoir
    for rid in liberes:
        updates[rid].update({F["attribue_a"]: None, F["attribue_le"]: None, F["attribue_jusquau"]: None})
    _memoriser(updates)  # recharger() tourne dans le même run et doit voir le lot du jour, même en dry-run
    if not A.dry_run:
        _patch(T_POSTS, updates)
    return recs, lots, jusquau, len(pool), len(updates), len(liberes), arbitrages


def recharger():
    """Recharge automatique (décision d'Alex, 17/09/2026, sans plafond ; ni bouton ni case : la page liste ne
    le permet pas). Une recruteuse active dont le lot en cours est épuisé — toutes ses cliniques valables
    (Attribué jusqu'au ≥ aujourd'hui) archivées ou converties en offre — reçoit N cliniques de plus, valables
    jusqu'à la fin du lot en cours. Une recruteuse sans lot en cours n'est pas rechargée (le lundi s'en charge).
    Mêmes règles que le lot : réservoir avec mail, une clinique = une recruteuse (une clinique servie à l'autre
    recruteuse ne change jamais de main), rien de servi depuis 14 j. Les posts servis reçoivent aussi
    Score/Raisons (un post scrappé en semaine n'en a pas encore). La routine est réveillée par une automation
    Airtable à chaque post d'un lot en cours qui sort de « À contacter (semaine) » ; c'est ici qu'on décide."""
    recs = sorted([r for r in recruteurs if r["fields"].get("Email")], key=lambda x: x["fields"].get("Nom", ""))
    actifs = {r["fields"]["Email"] for r in recs}
    demandes, etat = [], {}
    for rec in recs:
        email = rec["fields"]["Email"]
        lot = [r for r in rows if (r["f"].get("Attribué à") or {}).get("email") == email and r["f"].get("Attribué jusqu'au")
               and dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) >= today]
        restants = [r for r in lot if not r["f"].get("Archivé") and not r["f"].get("Offre d'emploi")]
        etat[email] = (len(lot), len(restants))
        if lot and not restants:
            demandes.append(rec)
    if not demandes:
        return None, etat
    fins = [dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) for r in rows if r["f"].get("Attribué jusqu'au")
            and dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) >= today]
    jusquau = max(fins) if fins else prochain_dimanche(today)
    proprio, recentes = _proprio_recentes()
    pool = _pool(recentes)
    sarah = sarah_email([r["fields"] for r in recs])
    lots, pris = {}, set()
    for rec in demandes:
        email = rec["fields"]["Email"]; lot = []
        for r in pool:
            if r["id"] in pris:
                continue
            p = proprio.get(r["clinique"])
            if p and p in actifs and p != email:
                continue  # clinique de l'autre recruteuse : elle ne change pas de main
            if r["vetcoop"] and email != sarah:
                continue  # adhérent Vetcoop : Sarah seulement
            lot.append(r); pris.add(r["id"])
            if len(lot) >= A.lot:
                break
        lots[email] = lot
    updates = {}
    for email, lot in lots.items():
        for r in lot:
            updates[r["id"]] = {F["score"]: r["score"], F["raisons"]: raisons(r),
                                F["clinique_existante"]: [r["known_id"]] if r["known_id"] else [],
                                F["attribue_a"]: {"email": email}, F["attribue_le"]: str(today), F["attribue_jusquau"]: str(jusquau)}
            if r["vetcoop"] and not r["f"].get("Membre Vetcoop"):
                updates[r["id"]][F["membre_vetcoop"]] = True
    _memoriser(updates)
    if not A.dry_run:
        _patch(T_POSTS, updates)
    return (demandes, lots, jusquau, len(pool)), etat


def vetcoop_immediat():
    """Adhérents Vetcoop dans le lot EN COURS de Sarah, tout de suite (décision d'Alex, 18/09/2026 : « lourdement
    pondéré pour sortir directement dans les résultats hebdomadaires »). Ne touche à aucune autre attribution.
    Candidats : posts éligibles, nouveaux (pas déjà en base), avec mail, adhérents, pas dans un lot en cours,
    un seul post par clinique. Une clinique de l'autre recruteuse n'est pas déplacée (arbitrage). Valables
    jusqu'à la fin du lot en cours, puis le lundi les reprend (ils ne sont pas retenus par la règle des 14 j)."""
    recs = [r["fields"] for r in recruteurs if r["fields"].get("Email")]
    actifs = {x["Email"] for x in recs}
    sarah = sarah_email(recs)
    if not sarah:
        return None, f"{VETCOOP_RECRUTEUSE} absente des recruteuses actives : aucun adhérent ajouté"
    proprio, _ = _proprio_recentes()
    fins = [dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) for r in rows if r["f"].get("Attribué jusqu'au")
            and dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) >= today]
    jusquau = max(fins) if fins else prochain_dimanche(today)
    ajout, arbitrages, vues = [], [], set()
    for r in sorted([x for x in new if x["vetcoop"]], key=ordre_pool):
        if r["f"].get("Attribué à") and r["f"].get("Attribué jusqu'au") and dt.date.fromisoformat(r["f"]["Attribué jusqu'au"]) >= today:
            vues.add(r["clinique"]); continue  # déjà dans un lot en cours
        if r["clinique"] in vues:
            continue
        vues.add(r["clinique"])
        p = proprio.get(r["clinique"])
        if p and p in actifs and p != sarah:
            arbitrages.append((r, f"clinique déjà attribuée à {NOMS.get(p, p)} : ne change pas de main sans arbitrage")); continue
        ajout.append(r)
    updates = {}
    for r in ajout:
        updates[r["id"]] = {F["score"]: r["score"], F["raisons"]: raisons(r),
                            F["clinique_existante"]: [r["known_id"]] if r["known_id"] else [],
                            F["attribue_a"]: {"email": sarah}, F["attribue_le"]: str(today), F["attribue_jusquau"]: str(jusquau)}
        if not r["f"].get("Membre Vetcoop"):
            updates[r["id"]][F["membre_vetcoop"]] = True
    _memoriser(updates)
    if updates and not A.dry_run:
        _patch(T_POSTS, updates)
    return (ajout, arbitrages, jusquau, sarah), None


# ---------- rapport ----------
def ligne(r):
    f = r["f"]; zone = f.get("Zone de recherche") or f.get("conv_county") or "?"
    contact = ", ".join(r["mails"] + r["tels"]) or "pas de contact dans le texte"
    vc = " · **adhérent Vetcoop**" if r.get("vetcoop") else ""
    return f"- **{f.get('conv_nom_clinique')}** — {zone} · score {r['score']}/33 · post n°{f.get('Numéro')}{vc} · {contact}\n  {' ; '.join(r['why'])}"


out = [f"# Cliniques à contacter — {today.strftime('%d/%m/%Y')}", "",
       f"{len(rows)} posts clinique évalués, {len(elig)} éligibles : {len(new)} nouvelles avec mail, {len(groupes)} groupes, {len(sans_mail)} sans mail, {len(relance)} déjà en base en cours, {len(ecart)} Signé/Refusé.",
       "Exclus : " + ", ".join(f"{k} {v}" for k, v in excl_count.most_common()) + ".", ""]
if A.attribuer:
    recs, lots, jusquau, npool, nupd, nlib, arbitrages = attribuer()
    if lots is None:
        out.append(f"## Lot en cours jusqu'au {jusquau.strftime('%d/%m')} : pas de nouvelle attribution")
        out.append("Un lot hebdomadaire est encore valide ; les scores n'ont pas été réécrits non plus. Relancer après sa date de fin, ou avec --force pour attribuer quand même.")
        lots = {}
    else:
        out.append(f"## Lots de la semaine (jusqu'au {jusquau.strftime('%d/%m')}){' — SIMULATION, rien écrit' if A.dry_run else ''}")
        out.append(f"Réservoir : {npool} cliniques attribuables (une clinique = un post, aucune attribuée depuis 14 j). {nupd} posts {'auraient été' if A.dry_run else ''} mis à jour (Score, Raisons, Clinique existante).")
        if nlib:
            out.append(f"Lot recalculé : {nlib} post(s) {'auraient été' if A.dry_run else ''} libéré(s) de l'attribution précédente.")
        for x in recs:
            lot = lots[x["Email"]]
            out.append(f"\n### {x.get('Nom')} — {len(lot)} clinique(s)")
            out += [ligne(r) for r in lot]
        if npool < A.lot * len(recs):
            out.append(f"\n⚠️ Réservoir insuffisant pour {A.lot} par recruteuse : lots réduits plutôt que gonflés avec des annonces sans mail.")
        if arbitrages:
            out.append(f"\n### Adhérents Vetcoop non attribués — arbitrage d'Alex")
            out += [f"- post n°{r['f'].get('Numéro')} {r['f'].get('conv_nom_clinique')} : {motif}" for r, motif in arbitrages]
if A.recharger:
    res, etat = recharger()
    noms = NOMS
    bilan = " ; ".join(f"{noms[e]} : {n - k} sur {n} traitée(s)" if n else f"{noms[e]} : pas de lot en cours" for e, (n, k) in etat.items())
    if res is None:
        out.append(f"\n## Recharge automatique : aucun lot épuisé ({bilan})")
    else:
        demandes, rlots, rjusquau, rpool = res
        out.append(f"\n## Recharge automatique (jusqu'au {rjusquau.strftime('%d/%m')}){' — SIMULATION, rien écrit' if A.dry_run else ''}")
        out.append(f"Lot(s) épuisé(s) : " + ", ".join(d["fields"].get("Nom", d["fields"]["Email"]) for d in demandes) + f" ({bilan}). Réservoir : {rpool} cliniques attribuables.")
        for d in demandes:
            lot = rlots[d["fields"]["Email"]]
            out.append(f"\n### {d['fields'].get('Nom')} — {len(lot)} clinique(s) de plus")
            out += [ligne(r) for r in lot]
            if len(lot) < A.lot:
                out.append(f"\n⚠️ Réservoir insuffisant : {len(lot)} clinique(s) au lieu de {A.lot}.")
if A.vetcoop_immediat:
    res, err = vetcoop_immediat()
    if err:
        out.append(f"\n## Adhérents Vetcoop, entrée immédiate : {err}")
    else:
        ajout, varb, vjusquau, vsarah = res
        out.append(f"\n## Adhérents Vetcoop, entrée immédiate dans le lot de {NOMS.get(vsarah, vsarah)} (jusqu'au {vjusquau.strftime('%d/%m')}){' — SIMULATION, rien écrit' if A.dry_run else ''}")
        out.append("Aucun adhérent nouveau à ajouter : ceux détectés sont déjà dans un lot en cours, déjà en base, ou sans mail." if not ajout else f"{len(ajout)} clinique(s) ajoutée(s) :")
        out += [ligne(r) for r in ajout]
        if varb:
            out.append("\n### Adhérents Vetcoop non ajoutés — arbitrage d'Alex")
            out += [f"- post n°{r['f'].get('Numéro')} {r['f'].get('conv_nom_clinique')} : {motif}" for r, motif in varb]
if not A.attribuer and not A.recharger and not A.vetcoop_immediat:
    out.append("## Top 20 nouvelles cliniques avec mail (lecture seule)")
    out += [ligne(r) for r in sorted(new, key=lambda r: (-r["score"], r["age"]))[:20]]
probables = [r for r in groupes if r["groupe"] == "probable"]
if probables:
    out.append("\n## Groupes probables à faire arbitrer par Alex (blacklist scrape-veto)")
    out += [f"- n°{r['f'].get('Numéro')} {r['f'].get('conv_nom_clinique')} ({r['f'].get('conv_county')}) : {r['groupe_why']}" for r in probables]


# ---------- dossier pour la rédaction des mails d'intro ----------
def dossier_mails(path):
    """Les posts du lot en cours (toutes recruteuses) qui n'ont pas encore de « Mail intro proposé » :
    ce que la routine a le droit de lire pour rédiger. Le texte est celui de l'annonce (public, écrit par la
    clinique) ; les champs structurés sont ceux posés par scrape-veto ou la recruteuse. Rien d'autre."""
    recs_by_email = {r["fields"]["Email"]: r["fields"] for r in recruteurs if r["fields"].get("Email")}
    dossier = []
    for r in rows:
        f = r["f"]
        if not (f.get("Attribué à") and f.get("Attribué jusqu'au")):
            continue
        if dt.date.fromisoformat(f["Attribué jusqu'au"]) < today or f.get("Archivé") or f.get("Offre d'emploi"):
            continue
        if (f.get("Mail intro proposé") or "").strip():
            continue
        email = (f.get("Attribué à") or {}).get("email"); rec = recs_by_email.get(email, {})
        dossier.append({
            "post_id": r["id"], "numero": f.get("Numéro"),
            "recruteuse": {"nom": rec.get("Nom"), "email": email},
            "membre_vetcoop": bool(r.get("vetcoop")), "vetcoop_motif": r.get("vetcoop"),
            "clinique": f.get("conv_nom_clinique"), "nom_clinique_brut": f.get("Nom de la clinique"),
            "contact": (f.get("Prénom", "") + " " + f.get("Nom", "")).strip(),
            "mails": r["mails"], "telephones": r["tels"], "canaux": [canaux.get(c, c) for c in f.get("Canaux", [])],
            "ville": f.get("Ville"), "cp": f.get("CP"), "zone": f.get("Zone de recherche"), "county": f.get("conv_county"), "pays": f.get("conv_pays"),
            "poste": f.get("Poste"), "emploi": f.get("Emploi recherché"), "experience": f.get("Expérience"),
            "pratiques_requises": f.get("Pratiques requises", []), "pratiques_optionnelles": f.get("Pratiques optionnelles", []),
            "specialites_requises": f.get("Spécialités requises", []), "specialites_optionnelles": f.get("Spécialités optionnelles", []),
            "statuts": f.get("Statuts contractuels", []), "temps": f.get("Type de temps de travail", []), "contrat_court": bool(f.get("Contrat court")),
            "gardes": f.get("Gardes"), "frequence_gardes": f.get("Fréquence des gardes"), "logement": f.get("Logement"),
            "remuneration": f.get("Rémunération"), "date_disponibilite": f.get("Date de disponibilité"),
            "langues": f.get("Langues requises", []), "questions": f.get("Questions"),
            "date_post": f.get("Date du post"), "score": r["score"], "raisons": raisons(r),
            "contenu": body(f)[:6000],
        })
    json.dump(dossier, open(path, "w"), ensure_ascii=False, indent=1)
    return dossier


if A.dossier_mails:
    d = dossier_mails(A.dossier_mails)
    par = collections.Counter(x["recruteuse"]["nom"] or x["recruteuse"]["email"] for x in d)
    out.append(f"\n## Mails d'intro à rédiger : {len(d)} post(s) du lot en cours sans « Mail intro proposé » → {A.dossier_mails}"
               + (" (" + ", ".join(f"{k} : {v}" for k, v in par.items()) + ")" if par else ""))
txt = "\n".join(out)
print(txt)
if A.rapport:
    open(A.rapport, "w").write(txt + "\n")
