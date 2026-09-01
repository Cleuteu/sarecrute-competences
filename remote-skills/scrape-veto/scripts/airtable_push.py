#!/usr/bin/env python3
"""
scrape-veto — push vers Airtable "Posts scrappés" avec upsert-merge par personne.

Pourquoi ce script : le contexte page Facebook bloque les requêtes vers
api.airtable.com (CSP). On pousse donc depuis Bash via l'API HTTP standard.

Usage :
    export AIRTABLE_API_KEY=$(grep AIRTABLE_API_KEY ~/.zshrc | head -1 | sed 's/.*="\\(.*\\)"/\\1/')
    python3 airtable_push.py records.json            # pousse (upsert-merge auto)
    python3 airtable_push.py records.json --dry       # n'écrit rien, montre le plan

records.json = liste d'objets {"fields": {...}} au format Airtable.
  Champs utiles : Prénom, Nom, Profil Facebook, Date du post (YYYY-MM-DD), Lien du post,
  Zone de recherche, Contenu complet, Type de post, Pratiques requises[],
  Pratiques optionnelles[], Spécialités requises[], Spécialités optionnelles[],
  Type d'entrée (Post|Commentaire), Post source, Expérience, Nom de la clinique.
  Archivé (ex "Non pertinent") : champ réservé au recruteur (usage manuel), le scrape
  ne doit JAMAIS l'écrire — un post jugé non pertinent est simplement omis de records.json.
  Canaux (liste de recId de « Canaux de diffusion ») : le ou les groupes Facebook
  d'où vient le contenu. À renseigner sur CHAQUE ligne. Fusionné par UNION, jamais
  écrasé : un candidat vu sur deux groupes garde les deux. Le nom du canal est aussi
  écrit dans l'en-tête de sa section de Contenu complet ("[date] lien · Canal"), ce
  qui donne l'origine post par post. Un recId inconnu arrête le script — aucun canal
  n'est créé ici, la table se gère dans Airtable.
  Champs matching (cf. references/matching_vocab.json) : Zones de recherche[], Statuts contractuels[],
  Type de temps de travail[], Date de disponibilité (YYYY-MM-DD), Rayon accepté (km).
  Contrat court (bool) : à émettre EXPLICITEMENT (true ou false) sur toute entrée
  "Vétérinaire cherche poste", jamais omis — c'est un scalaire, donc le post le plus
  récent gagne à la fusion ; omis, l'ancienne valeur resterait figée.
  auteur_key : ne PAS le renseigner pour les CANDIDATS (le script le calcule) ;
  OBLIGATOIRE pour toute entrée CLINIQUE fusible, sous forme de clé d'OFFRE
  « <clé nue>#<slug> » (voir ci-dessous). Les valeurs select hors vocabulaire sont
  ignorées automatiquement (jamais de création d'option).

Déduplication — trois régimes :
  • Entrée CLINIQUE (Type de post « Clinique cherche vétérinaire ») fusible → UPSERT
    par OFFRE, jamais par personne (0.13.0). Chaque ligne doit porter dans auteur_key
    la clé de l'offre qu'elle republie : « <clé nue>#<slug> », clé nue = nom de la
    clinique normalisé (minuscules, sans accents, apostrophe droite) sinon
    prénom+nom. La clé se choisit au JUGEMENT (test d'extinction, SKILL §5) contre
    les offres existantes (`--offres`) : même poste → réutiliser la clé telle
    quelle ; poste différent → clé neuve. Sans clé, le script s'arrête en listant
    les offres connues de la clinique. Pourquoi : la fusion par personne agrégeait
    deux offres distinctes d'une même page (Panier Fleuri) et éclatait la même offre
    publiée par trois personnes (Sainte Croix).
  • Nom FIABLE (auteur_key non vide) → UPSERT par personne, toutes dates
    confondues. Si la personne existe déjà, on MET À JOUR son enregistrement :
    le nouveau post est empilé en haut de "Contenu complet" (séparateur daté,
    plus récent en premier), et les champs scalaires (Date, Zone, Pratiques requises…)
    prennent les valeurs du post le PLUS RÉCENT. Rien n'est perdu.
  • Nom ANONYME / non fiable → PAS de fusion. On crée, sauf si EXACTEMENT la
    même publication est déjà en base (garde d'idempotence Date|Type|Nom|Contenu[:60]).

Dans les DEUX régimes, « rien de neuf dans le contenu » ne veut pas dire « rien à
écrire » : un post rigoureusement identique cross-posté dans deux groupes apporte une
ORIGINE nouvelle. Les gardes d'idempotence ajoutent donc le canal manquant (ligne
« ⊕ CANAL » en --dry) sans toucher au contenu ni aux champs scalaires.

auteur_key = prénom+nom normalisés (sans accents, minuscules). Vide (donc pas
de fusion) si : nom vide / "Membre anonyme" / pseudo FB auto-généré (contient des
chiffres) / tout en capitales / > 6 mots (un titre d'annonce capté à la place de
l'auteur).

Les COMMENTAIRES rejoignent l'enregistrement de la personne, POST COMPRIS (20 août
2026). Une personne = un enregistrement, et une relance en commentaire ENRICHIT son
annonce au lieu d'en fabriquer une copie : Sabine Marcillaud avait 3 enregistrements
pour 1 seule offre (son annonce du 15/08 + deux « Aveyron si ça t'intéresse ! » posés
sous deux posts de candidates à 2 jours d'écart).

Ce qui protège de la confusion que l'ancien espace de clés séparé évitait :
  • la CIBLE de fusion est le POST de la personne quand elle en a un (cf. target_rank),
    jamais son commentaire le plus récent ;
  • "Type d'entrée" reste « Post » dès qu'une section est un post — un commentaire
    plus récent ne le retourne plus en « Commentaire » ;
  • chaque section de commentaire porte une ligne « 💬 COMMENTAIRE de X sous le post
    de Y » (cf. mark_comment), pour que le recruteur ne lise pas le post recopié
    comme s'il était de la personne ;
  • les scalaires d'un commentaire ne COMPLÈTENT que les champs vides de l'annonce,
    ils ne l'écrasent pas (cf. merged_scalars).
"""
import json, os, sys, re, unicodedata, urllib.request, urllib.parse, urllib.error

BASE = "appP0W2ISytaNyAhG"
TABLE = "Posts scrappés"
API = "https://api.airtable.com/v0/%s/%s" % (BASE, urllib.parse.quote(TABLE))

SEP = "\n\n──────────\n\n"
# En-tête de section : "[date] lien · Canal". Le canal est OPTIONNEL, et le lien
# doit rester reconnaissable seul : les sections déjà en base ("[date] lien") ont
# à continuer de matcher, sinon la garde d'idempotence tombe et tout est réempilé.
HEADER_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2})\]\s*((?:https?://\S+)?)\s*(?:·\s*(.+?))?\s*$")
CANAUX_TABLE = "tbluH5M2sogAN85dl"      # Canaux de diffusion (groupes FB, réseaux)
# (VOWELS / ORG_MARKERS retirés le 16 août 2026 : ils servaient à refuser une clé aux
#  noms de structure et aux surnoms tronqués, ce qui bloquait la fusion des pages de
#  clinique — cf. docstring de auteur_key.)

# Champs recopiés depuis le post le plus récent lors d'un merge (tout sauf le contenu).
SCALAR_FIELDS = ["Prénom", "Nom", "Profil Facebook", "Date du post", "Lien du post", "Zone de recherche",
                 "Type de post", "Pratiques requises", "Pratiques optionnelles",
                 "Spécialités requises", "Spécialités optionnelles", "Type d'entrée",
                 "Post source", "Expérience", "Nom de la clinique", "Archivé", "auteur_key",
                 "Zones de recherche", "Statuts contractuels", "Type de temps de travail",
                 "Date de disponibilité", "Rayon accepté (km)", "Contrat court"]

# Champs fusionnés par UNION, jamais écrasés par le post le plus récent : un
# candidat vu sur deux groupes doit garder les deux canaux. (Ne JAMAIS les mettre
# dans SCALAR_FIELDS, la première origine serait perdue à la fusion suivante.)
UNION_FIELDS = ["Canaux"]

# Garde-fou : n'écrire QUE des valeurs select existantes (sinon Airtable crée une option).
# ⚠️ Le vocabulaire vit dans references/, pas à côté de ce script : on cherche donc les
# deux emplacements (le second sert quand le script est copié ailleurs avec son vocab).
# ⚠️ Un échec de chargement N'EST PAS silencieux : jusqu'au 10 août 2026 un `except: pass`
# laissait ALLOWED vide et sanitize_selects ne filtrait plus rien — le garde-fou était
# désactivé sans que rien ne l'indique. Désormais l'absence de vocab est fatale dès qu'un
# enregistrement porte un champ protégé (cf. check_vocab_loaded).
GUARDED_FIELDS = ("Zones de recherche", "Statuts contractuels", "Type de temps de travail",
                  "Pratiques requises", "Pratiques optionnelles",
                  "Spécialités requises", "Spécialités optionnelles")
_HERE = os.path.dirname(os.path.abspath(__file__))
_VOCAB_PATHS = [os.path.join(_HERE, os.pardir, "references", "matching_vocab.json"),
                os.path.join(_HERE, "matching_vocab.json")]
ALLOWED, VOCAB_ERROR = {}, None
for _p in _VOCAB_PATHS:
    try:
        _V = json.load(open(_p))
        ALLOWED = {"Zones de recherche": set(_V["zones_de_recherche"]),
                   "Statuts contractuels": set(_V["statuts_contractuels"]),
                   "Type de temps de travail": set(_V["type_de_temps_de_travail"])}
        # Les deux niveaux de pratiques partagent un seul vocabulaire. Sous .get() : une copie
        # installée dont le vocab est antérieur au 31/08/2026 n'a pas la clé, et on préfère ne
        # pas garder ces deux champs plutôt que faire échouer le chargement entier — sans quoi
        # les trois autres champs perdraient leur garde-fou.
        if _V.get("pratiques"):
            ALLOWED["Pratiques requises"] = set(_V["pratiques"])
            ALLOWED["Pratiques optionnelles"] = set(_V["pratiques"])
        if _V.get("specialites"):
            ALLOWED["Spécialités requises"] = set(_V["specialites"])
            ALLOWED["Spécialités optionnelles"] = set(_V["specialites"])
        VOCAB_ERROR = None
        break
    except Exception as e:
        VOCAB_ERROR = "%s : %s" % (os.path.normpath(_p), e)


def check_vocab_loaded(records):
    """Refuse d'écrire des champs select si le vocabulaire n'a pas pu être chargé.

    Sans vocabulaire, toute valeur mal orthographiée créerait une option Airtable —
    ce que le projet interdit. Un records.json qui ne touche à aucun champ protégé
    peut en revanche passer sans vocab."""
    if ALLOWED:
        return
    touched = sorted({fl for r in records for fl in GUARDED_FIELDS if r["fields"].get(fl)})
    if touched:
        sys.exit("Vocabulaire des selects introuvable (%s).\n"
                 "Champs protégés présents dans records.json : %s\n"
                 "Sans ce fichier, une valeur hors vocab créerait une option Airtable : "
                 "arrêt. Attendu dans references/matching_vocab.json." % (VOCAB_ERROR, ", ".join(touched)))
    print("  ⚠️  vocabulaire des selects non chargé (%s) — aucun champ protégé dans l'input, on continue."
          % VOCAB_ERROR)


def sanitize_selects(f):
    """Retire les valeurs select hors vocabulaire (protège contre la création d'options)."""
    for field, allowed in ALLOWED.items():
        if field in f and isinstance(f[field], list):
            kept = [v for v in f[field] if v in allowed]
            dropped = [v for v in f[field] if v not in allowed]
            if dropped:
                print("  ⚠️  %s : valeurs ignorées (hors vocab) : %s" % (field, dropped))
            f[field] = kept
    return f

# Champs demandés au fetch (on a besoin du contenu pour merger la cible).
FETCH_FIELDS = ["Prénom", "Nom", "Date du post", "Lien du post", "Contenu complet",
                "Type d'entrée", "auteur_key", "Canaux", "Type de post", "Nom de la clinique"]

CLINIC_TYPE = "Clinique cherche vétérinaire"


def bare_key(f):
    """Clé nue d'un contenu clinique : le nom de la clinique normalisé s'il est connu,
    sinon la clé personne. C'est le préfixe attendu avant « # » dans une clé d'offre —
    le nom de la clinique plutôt que l'auteur, parce que la même offre est publiée par
    plusieurs personnes (Sainte Croix : 3 auteurs pour 1 offre)."""
    return norm(f.get("Nom de la clinique")) or auteur_key(f.get("Prénom"), f.get("Nom"))


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def norm(s):
    # L'apostrophe typographique est normalisée : sans ça « d'Ossau » et « d'Ossau »
    # font deux clés différentes et la clinique ne se retrouve jamais elle-même.
    return re.sub(r"\s+", " ", strip_accents((s or "").replace("’", "'")).lower()).strip()


def auteur_key(prenom, nom):
    """Clé personne fiable, ou '' si anonyme / non fiable (→ pas de fusion).

    ⚠️ Ne rejette PLUS les noms de structure ni les surnoms tronqués (16 août 2026).
    Les deux exclusions datent de l'époque où la clé ne servait qu'aux candidats ;
    appliquées aux pages de clinique elles empêchaient précisément la fusion qu'on
    veut (une clinique qui republie son annonce doit rester UN enregistrement) :
    « Clinique Vétérinaire de l'Ecluse » avait 7 enregistrements, « Vétérinaire des
    Salines » 6, et les pseudos FB tronqués (Lisa Jrn, Jo Vstk, San Cmb) 3 à 5.
    Le nom complet normalisé reste discriminant : le seul faux positif possible est
    un homonyme EXACT, que le garde-fou « annonce vraiment différente ⇒ entrée
    séparée » (cf. SKILL.md §5) rattrape à la relecture.

    Ce qui reste rejeté, ce sont les noms qui ne désignent personne de stable :
    anonymes, pseudos auto-générés par FB (ils portent des chiffres), tout en
    capitales, et les titres d'annonce captés à la place de l'auteur (> 6 mots)."""
    prenom = (prenom or "").strip()
    nom = (nom or "").strip()
    full = (prenom + " " + nom).strip()
    if not nom:
        return ""
    low = strip_accents(full).lower()
    if "anonyme" in low:
        return ""
    if any(ch.isdigit() for ch in full):
        return ""
    if len(full.split()) > 6:
        return ""
    if any(c.isalpha() for c in full) and full == full.upper():   # tout en capitales
        return ""
    return norm(full)


PIN = "#"   # marqueur de clé figée à la main, ex. "remi mereaux#etudiants-a6"


def effective_key(f):
    """Clé d'indexation réelle : la clé calculée, SAUF si elle a été figée à la main.

    Le champ auteur_key est normalement recalculé depuis Prénom+Nom (les
    enregistrements legacy l'ont vide, l'upsert marche quand même). Mais une clé
    renseignée à la main et contenant « # » est RESPECTÉE telle quelle.

    À quoi ça sert : sortir un enregistrement du chemin de fusion automatique. Deux
    annonces vraiment différentes du même auteur (Rémi Mereaux : un poste vétérinaire
    mixte ET une offre pour étudiants A6 ; Liora Simmenauer : urgentiste ET clinicat)
    doivent vivre dans deux enregistrements. Séparées à la main, elles étaient
    refusionnées au scrape suivant puisque la clé se recalcule depuis le nom. Il
    suffit désormais d'écrire « remi mereaux#etudiants-a6 » dans auteur_key : plus
    aucun post ne l'y rejoindra automatiquement.

    ⚠️ Conséquence à connaître : un enregistrement figé ne reçoit plus rien tout seul.
    Laisse toujours UN enregistrement non figé par auteur pour absorber ses nouvelles
    publications — sinon elles créeront un enregistrement de plus.

    Le marqueur est volontairement explicite : on ne devine jamais un figeage à partir
    d'un écart entre la clé stockée et le nom (un nom corrigé après coup produirait cet
    écart sans qu'on veuille figer quoi que ce soit)."""
    stored = (f.get("auteur_key") or "").strip()
    if PIN in stored:
        return stored
    return auteur_key(f.get("Prénom"), f.get("Nom"))


def exact_key(f):
    """Signature d'une publication exacte (idempotence pour les anonymes)."""
    body = re.sub(r"\s+", " ", (f.get("Contenu complet") or "")).strip().lower()[:60]
    return "|".join([f.get("Date du post", ""), f.get("Type d'entrée", ""),
                     norm(f.get("Prénom")), norm(f.get("Nom")), body])


COMMENT_MARK = "💬 COMMENTAIRE"
# ⚠️ Le marqueur est retiré AVANT de signer une section (cf. sec_sig) : les sections
# de commentaire écrites avant le 20 août 2026 n'en portent pas, et sans ce nettoyage
# le même commentaire re-scrapé produirait une signature différente — donc une section
# en double à chaque passage.
COMMENT_MARK_RE = re.compile(r"^\s*" + COMMENT_MARK + r"[^\n]*\n+")


def mark_comment(content, f):
    """Préfixe le contenu d'un COMMENTAIRE d'une ligne qui dit ce que c'est.

    Sans elle, une section de commentaire empilée dans l'enregistrement d'une clinique
    se lit comme une seconde annonce — alors que le gros du texte y est le post d'un
    TIERS (le bloc « ━━━ Post commenté ━━━ »). Le recruteur qui lit la description doit
    voir d'un coup d'œil ce qui est de la personne et ce qui ne l'est pas."""
    body = COMMENT_MARK_RE.sub("", (content or "").lstrip())
    who = " ".join(x for x in [(f.get("Prénom") or "").strip(), (f.get("Nom") or "").strip()] if x)
    who = who or "cette personne"
    src = (f.get("Post source") or "").split(" - ")[0].strip()
    head = "%s de %s" % (COMMENT_MARK, who)
    if src:
        head += " sous le post de %s" % src
    return head + " — ce qui suit « Post commenté » n'est pas de %s.\n" % who + body


def sec_sig(s):
    body = COMMENT_MARK_RE.sub("", s["body"] or "")
    return (s["date"], re.sub(r"\s+", " ", body).strip().lower()[:80])


def parse_sections(content, fb_date, fb_link, fb_canal=""):
    """Découpe un Contenu complet en sections {date, link, canal, body}. Gère le
    legacy (post unique sans en-tête → une section avec la date/lien/canal du
    record). `fb_canal` ne doit être fourni que si le record a UN seul canal :
    sur un record multi-canaux, on ne peut pas deviner de quel groupe vient une
    section sans en-tête, et il vaut mieux ne rien affirmer."""
    content = (content or "").strip()
    if not content:
        return []
    secs = []
    for chunk in re.split(r"\n*─{5,}\n*", content):
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.split("\n")
        m = HEADER_RE.match(lines[0].strip())
        if m:
            # En-tête sans canal (toutes les sections écrites avant l'ajout du champ) :
            # on retombe sur le canal du record, seule attribution disponible — et
            # `fb_canal` est vide dès que le record a plusieurs canaux, donc on ne
            # devine jamais. C'est ce qui fait que l'historique se complète tout seul.
            secs.append({"date": m.group(1), "link": m.group(2), "canal": m.group(3) or fb_canal or "",
                         "body": "\n".join(lines[1:]).strip()})
        else:
            secs.append({"date": fb_date or "", "link": fb_link or "", "canal": fb_canal or "",
                         "body": chunk})
    return secs


def dedup_sections(secs):
    seen, out = set(), []
    for s in secs:
        sig = sec_sig(s)
        if sig in seen:
            continue
        seen.add(sig)
        out.append(s)
    return out


def render_sections(secs):
    """Rend les sections en texte, plus récent en haut."""
    secs = sorted(secs, key=lambda s: s["date"], reverse=True)
    blocks = []
    for s in secs:
        head = ("[%s] %s" % (s["date"], s.get("link") or "")).rstrip()
        if s.get("canal"):
            head += " · " + s["canal"]
        blocks.append(head + "\n" + s["body"])
    return SEP.join(blocks)


def merged_scalars(field_dicts):
    """Scalaires de l'enregistrement fusionné : le POST le plus récent d'abord, puis
    les commentaires en COMPLÉMENT — premier qui renseigne un champ, gagne.

    Deux écarts assumés avec l'ancien « le plus récent écrase tout » :
      • un COMMENTAIRE ne remplace jamais une valeur de l'annonce, il ne remplit que
        les trous. C'est ce qu'on veut d'une relance : l'annonce de Sabine Marcillaud
        ne dit rien de l'expérience attendue, ses commentaires sous des posts de
        débutantes le disent — le champ se remplit sans que le reste bouge.
      • une valeur VIDE ne chasse plus une valeur pleine, même venue d'un post plus
        récent : une annonce republiée en version courte ne doit pas effacer les
        pratiques et spécialités déjà extraites de sa version longue.

    "Date du post" fait exception et prend l'activité la plus récente, commentaire
    compris : c'est l'indicateur de fraîcheur en prospection (une offre relancée
    avant-hier n'est pas une offre de la semaine dernière)."""
    is_com = lambda f: f.get("Type d'entrée") == "Commentaire"
    by_date = lambda l: sorted(l, key=lambda f: f.get("Date du post") or "", reverse=True)
    posts = [f for f in field_dicts if not is_com(f)]
    out = {}
    for f in by_date(posts) + by_date([f for f in field_dicts if is_com(f)]):
        for k in SCALAR_FIELDS:
            v = f.get(k)
            if k in out or v is None or v == "" or v == []:
                continue
            out[k] = v
    if posts:
        # La personne a publié une annonce : l'enregistrement est un Post, et il n'a
        # pas de "Post source" (ce champ ne décrit que le parent d'un commentaire).
        out["Type d'entrée"] = "Post"
        out["Post source"] = ""
    dates = [f.get("Date du post") for f in field_dicts if f.get("Date du post")]
    if dates:
        out["Date du post"] = max(dates)
    return out


def target_rank(f):
    """Préférence d'un enregistrement existant comme CIBLE de fusion.

    Un POST l'emporte toujours sur un commentaire, puis le plus récent gagne : les
    relances doivent rejoindre l'ANNONCE, pas s'accumuler sur le dernier commentaire.
    Sans ce classement, la fusion par personne ferait dériver l'offre vers un
    enregistrement dont le contenu principal est le post de quelqu'un d'autre."""
    return (0 if f.get("Type d'entrée") == "Commentaire" else 1, f.get("Date du post") or "")


def union_links(field_dicts):
    """Union ordonnée des canaux de plusieurs jeux de champs (1re origine d'abord)."""
    out = []
    for f in field_dicts:
        for rid in (f.get("Canaux") or []):
            if rid not in out:
                out.append(rid)
    return out


def fetch_canaux(token):
    """recId → nom du canal, pour l'en-tête de section. Aucune création possible :
    un recId inconnu est une erreur, jamais un canal à inventer."""
    url = "https://api.airtable.com/v0/%s/%s?pageSize=100&fields%%5B%%5D=Name" % (BASE, CANAUX_TABLE)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    data = json.loads(urllib.request.urlopen(req).read())
    return {r["id"]: (r["fields"].get("Name") or "") for r in data.get("records", [])}


def canal_of(f, canaux):
    """Nom du canal d'un record, seulement s'il en a exactement un (sinon '')."""
    ids = f.get("Canaux") or []
    return canaux.get(ids[0], "") if len(ids) == 1 else ""


def fetch_all(token):
    recs, offset = [], None
    while True:
        params = [("pageSize", "100")] + [("fields[]", x) for x in FETCH_FIELDS]
        if offset:
            params.append(("offset", offset))
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                     headers={"Authorization": "Bearer " + token})
        data = json.loads(urllib.request.urlopen(req).read())
        recs += data.get("records", [])
        offset = data.get("offset")
        if not offset:
            break
    return recs


def list_offres(token, filtre=""):
    """--offres [filtre] : liste les clés d'offre clinique déjà en base.

    Une clé d'offre est un auteur_key figé « <clé nue>#<slug> ». C'est CE listing que
    le scrape consulte avant d'écrire records.json : pour chaque post clinique, soit le
    poste correspond à une offre listée ici (→ réutiliser sa clé telle quelle), soit
    c'est une offre nouvelle (→ inventer « <clé nue>#<slug> » neuf). Le filtre est un
    sous-texte de la clé, insensible aux accents/majuscules."""
    fl = norm(filtre)
    rows = []
    for r in fetch_all(token):
        f = r["fields"]
        stored = (f.get("auteur_key") or "").strip()
        if PIN not in stored or (fl and fl not in norm(stored)):
            continue
        secs = parse_sections(f.get("Contenu complet"), f.get("Date du post"), f.get("Lien du post"))
        body = re.sub(r"\s+", " ", secs[0]["body"])[:110] if secs else ""
        rows.append("%s | %s | %s" % (stored, f.get("Date du post", ""), body))
    for row in sorted(rows):
        print(row)
    if not rows:
        print("(aucune offre%s)" % (" pour « %s »" % filtre if filtre else ""))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    token = os.environ.get("AIRTABLE_API_KEY")
    if not token:
        sys.exit("AIRTABLE_API_KEY manquant (export depuis ~/.zshrc).")
    if "--offres" in sys.argv:
        return list_offres(token, args[0] if args else "")
    if not args:
        sys.exit("Usage: airtable_push.py records.json [--dry] | airtable_push.py --offres [filtre]")
    records = json.load(open(args[0]))
    check_vocab_loaded(records)

    # 0) Canaux : on valide AVANT d'écrire. Un recId inconnu = arrêt, pas de canal
    #    créé à la volée (la table des canaux se gère dans Airtable, pas ici).
    canaux = fetch_canaux(token)
    inconnus = sorted({rid for r in records for rid in (r["fields"].get("Canaux") or [])
                       if rid not in canaux})
    if inconnus:
        sys.exit("Canaux inconnus dans records.json : %s\n"
                 "Vérifie les recId contre la table « Canaux de diffusion » — "
                 "ce script n'en crée jamais." % ", ".join(inconnus))
    sans_canal = sum(1 for r in records if not (r["fields"].get("Canaux") or []))
    if sans_canal:
        print("  ⚠️  %d ligne(s) sans Canaux : l'origine du contenu sera perdue." % sans_canal)

    # 1) Répartir l'input : personnes fiables (groupées par clé) vs anonymes.
    groups, singles, sans_offre = {}, [], []
    for r in records:
        f = sanitize_selects(dict(r["fields"]))
        # UNE personne = UN enregistrement, commentaires compris (20 août 2026 —
        # l'espace de clés séparé "com:" a été retiré, cf. docstring du module).
        # Chaque section de commentaire est marquée pour rester reconnaissable dans la
        # description ; le marquage se fait ICI, avant tout découpage en sections.
        if f.get("Type d'entrée") == "Commentaire":
            f["Contenu complet"] = mark_comment(f.get("Contenu complet"), f)
        # effective_key et pas auteur_key : records.json n'est pas censé renseigner la
        # clé pour les CANDIDATS (elle se calcule), mais une clé figée ("…#suffixe")
        # est un choix délibéré de viser cet enregistrement — on la respecte.
        k = effective_key(f)
        # Depuis la 0.13.0, une entrée CLINIQUE fusible doit porter sa clé d'OFFRE
        # (« <clé nue>#<slug> ») : la fusion par personne agrégeait les offres
        # distinctes d'une même clinique et éclatait la même offre publiée par
        # plusieurs personnes. La clé d'offre se choisit au jugement (cf. SKILL §5,
        # test d'extinction), jamais ici — donc son absence est une erreur d'input.
        if f.get("Type de post") == CLINIC_TYPE and k and PIN not in k:
            sans_offre.append(f)
        f["auteur_key"] = k
        (groups.setdefault(k, []).append(f) if k else singles.append(f))

    # 2) Index de l'existant. On recalcule la clé depuis le nom (les records
    #    legacy ont auteur_key vide) → l'upsert marche même sans backfill.
    existing = fetch_all(token)

    # Entrées clinique sans clé d'offre : arrêt AVANT toute écriture, avec les offres
    # déjà connues de chaque clinique pour aider au jugement. Ne « répare » jamais ça
    # en retirant le contrôle : choisis (ou crée) la clé d'offre et réécris records.json.
    if sans_offre:
        offres = {}
        for r in existing:
            stored = (r["fields"].get("auteur_key") or "").strip()
            if PIN in stored:
                offres.setdefault(stored.split(PIN)[0], []).append(stored)
        msg = ["%d entrée(s) clinique sans clé d'offre (auteur_key « <clé nue>#<slug> ») :" % len(sans_offre)]
        for f in sans_offre:
            b = bare_key(f)
            msg.append("  • %s | %s | %s :: %s" % (
                f.get("Date du post", "?"),
                (f.get("Nom de la clinique") or (f.get("Prénom", "") + " " + f.get("Nom", ""))).strip(),
                ("offres existantes : " + ", ".join(sorted(set(offres.get(b, []))))) if offres.get(b)
                else "aucune offre connue pour « %s »" % b,
                re.sub(r"\s+", " ", f.get("Contenu complet") or "")[:70]))
        msg.append("Choisis la clé au jugement (test d'extinction, cf. SKILL §5) : réutilise une clé")
        msg.append("listée ci-dessus si c'est le même poste, sinon invente « <clé nue>#<slug> » neuf.")
        msg.append("`airtable_push.py --offres [filtre]` liste toutes les offres connues.")
        sys.exit("\n".join(msg))

    by_key, exact_recs = {}, {}
    # Sections déjà en base par AUTEUR (clé nue : regroupe ses enregistrements figés et
    # non figés). Sert à ne jamais ré-empiler ailleurs un texte déjà présent chez lui.
    # Indexé sous la clé personne ET sous le préfixe nu d'une clé figée : les offres
    # clinique sont figées sous le nom de la CLINIQUE alors que leurs posts peuvent
    # venir de plusieurs personnes.
    sigs_by_person = {}
    for r in existing:
        f = r["fields"]
        # exact_recs (et pas un simple set) : quand la publication est déjà en base, il
        # faut pouvoir la PATCHER pour lui ajouter un canal manquant (cf. add_canaux).
        exact_recs.setdefault(exact_key(f), r)
        stored = (f.get("auteur_key") or "").strip()
        sig_keys = {auteur_key(f.get("Prénom"), f.get("Nom"))}
        if PIN in stored:
            sig_keys.add(stored.split(PIN)[0])
        sig_keys.discard("")
        if sig_keys:
            sigs = {sec_sig(s) for s in parse_sections(
                f.get("Contenu complet"), f.get("Date du post"),
                f.get("Lien du post"), canal_of(f, canaux))}
            for sk in sig_keys:
                sigs_by_person.setdefault(sk, set()).update(sigs)
        k = effective_key(f)   # respecte une clé figée à la main ("…#suffixe")
        if k:
            # Cible = le POST de la personne s'il existe, sinon son commentaire le plus
            # récent (cf. target_rank). Une relance rejoint ainsi l'annonce elle-même.
            cur = by_key.get(k)
            if not cur or target_rank(f) > target_rank(cur["fields"]):
                by_key[k] = r

    to_create, to_patch, to_link, skipped = [], [], [], 0

    def add_canaux(target, flist):
        """Le contenu est déjà en base : ne reste-t-il qu'un canal à ajouter ?

        Un post RIGOUREUSEMENT identique publié dans deux groupes ne crée aucune section
        nouvelle (la signature de section est date+corps, pas le lien) — mais son origine,
        elle, est nouvelle. Avant le 10 août 2026 les gardes d'idempotence sortaient avant
        l'union et le second canal était perdu : c'est précisément ce que « Canaux » doit
        enregistrer. On ne touche QUE Canaux : le post n'étant pas plus récent, il n'a
        aucune raison d'écraser les champs scalaires."""
        # Si le même enregistrement reçoit déjà un patch de contenu, ne pas en ajouter un
        # second : celui-ci porte une union calculée avant, il écraserait la plus large.
        if any(rid == target["id"] for rid, _f, _tf in to_patch):
            return False
        tf = target["fields"]
        union = union_links([tf] + list(flist))
        if union and union != (tf.get("Canaux") or []):
            to_link.append((target["id"], {"Canaux": union}, tf))
            return True
        return False

    # 3) Personnes fiables → upsert.
    for k, flist in groups.items():
        in_secs = dedup_sections([s for f in flist for s in parse_sections(
            f.get("Contenu complet"), f.get("Date du post"), f.get("Lien du post"),
            canal_of(f, canaux))])
        # Une section déjà présente CHEZ CET AUTEUR — même dans un autre de ses
        # enregistrements, figé compris — n'est pas nouvelle : sans ce filtre, une
        # annonce séparée à la main était ré-empilée dans l'enregistrement resté
        # ouvert, et le même texte se retrouvait en base deux fois.
        already = sigs_by_person.get(k.split(PIN)[0], set())
        in_secs = [s for s in in_secs if sec_sig(s) not in already]
        target = by_key.get(k)
        if not in_secs:                    # rien de neuf nulle part chez cet auteur
            if target:
                add_canaux(target, flist)  # …mais peut-être une origine nouvelle
            skipped += len(flist)
            continue
        if target:
            tf = target["fields"]
            t_secs = parse_sections(tf.get("Contenu complet"), tf.get("Date du post"),
                                    tf.get("Lien du post"), canal_of(tf, canaux))
            t_sigs = {sec_sig(s) for s in t_secs}
            if {sec_sig(s) for s in in_secs} <= t_sigs:      # aucune section nouvelle
                add_canaux(target, flist)                    # …mais peut-être un canal
                skipped += len(flist)
                continue
            fields = merged_scalars(flist + [tf])
            fields["auteur_key"] = k
            # Union des canaux : la fusion ajoute une origine, elle n'en remplace pas.
            # (in_secs d'abord dans le dédup → un en-tête legacy sans canal se voit
            #  enrichi par la version datée du canal, à signature identique.)
            union = union_links(flist + [tf])
            if union:
                fields["Canaux"] = union
            fields["Contenu complet"] = render_sections(dedup_sections(in_secs + t_secs))
            to_patch.append((target["id"], fields, tf))
        else:
            fields = merged_scalars(flist)
            fields["auteur_key"] = k
            union = union_links(flist)
            if union:
                fields["Canaux"] = union
            fields["Contenu complet"] = render_sections(in_secs)
            to_create.append({"fields": fields})

    # 4) Anonymes / non fiables → pas de fusion, garde d'idempotence exacte.
    #    Même règle que ci-dessus : publication déjà en base ⇒ on n'en recrée pas une,
    #    mais on lui ajoute le canal si elle vient d'un second groupe.
    seen_batch = {}
    for f in singles:
        ek = exact_key(f)
        queued = seen_batch.get(ek)
        if queued is not None:
            # Même publication deux fois dans CE lot (cross-post entre deux groupes, nom
            # non fusionnable) : on n'en crée qu'une, mais elle porte les deux canaux.
            union = union_links([queued, f])
            if union:
                queued["Canaux"] = union
            skipped += 1
            continue
        dup = exact_recs.get(ek)
        if dup is not None:
            add_canaux(dup, [f])
            skipped += 1
            continue
        seen_batch[ek] = f
        to_create.append({"fields": f})

    print("Input: %d lignes | nouveaux: %d | mises à jour: %d | canaux ajoutés: %d | "
          "ignorés (déjà en base): %d"
          % (len(records), len(to_create), len(to_patch), len(to_link), skipped))

    if dry:
        def cnames(f):
            return "/".join(canaux.get(r, r) for r in (f.get("Canaux") or [])) or "—"
        for c in to_create:
            f = c["fields"]
            who = (f.get("Prénom", "") + " " + f.get("Nom", "")).strip() or f.get("Nom de la clinique", "") or "(anonyme)"
            print("  + CRÉER ", f.get("Date du post"), "|", who, "|", cnames(f),
                  "::", (f.get("Contenu complet") or "")[:50].replace("\n", " "))
        for rid, f, tf in to_patch:
            who = (f.get("Prénom", "") + " " + f.get("Nom", "")).strip()
            avant, apres = cnames(tf), cnames(f)
            canal_txt = apres if avant == apres else "%s → %s" % (avant, apres)
            print("  ~ MAJ   ", rid, "|", who, "| nouveau top:", f.get("Date du post"),
                  "| canaux:", canal_txt)
        for rid, f, tf in to_link:
            who = ((tf.get("Prénom") or "") + " " + (tf.get("Nom") or "")).strip() or "(anonyme)"
            print("  ⊕ CANAL ", rid, "|", who, "| contenu déjà en base, canaux:",
                  "%s → %s" % (cnames(tf), cnames(f)))
        return

    created = 0
    for i in range(0, len(to_create), 10):
        body = json.dumps({"records": to_create[i:i + 10]}).encode()
        req = urllib.request.Request(API, data=body, method="POST",
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            resp = json.loads(urllib.request.urlopen(req).read())
            created += len(resp.get("records", []))
        except urllib.error.HTTPError as e:
            print("POST ERREUR %d: %s" % (e.code, e.read().decode())); sys.exit(1)

    patched, linked = 0, 0
    for rid, fields, _tf in to_patch:
        body = json.dumps({"fields": fields}).encode()
        req = urllib.request.Request(API + "/" + rid, data=body, method="PATCH",
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req).read()
            patched += 1
        except urllib.error.HTTPError as e:
            print("PATCH %s ERREUR %d: %s" % (rid, e.code, e.read().decode())); sys.exit(1)

    for rid, fields, _tf in to_link:
        body = json.dumps({"fields": fields}).encode()
        req = urllib.request.Request(API + "/" + rid, data=body, method="PATCH",
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req).read()
            linked += 1
        except urllib.error.HTTPError as e:
            print("PATCH canaux %s ERREUR %d: %s" % (rid, e.code, e.read().decode())); sys.exit(1)

    print("CRÉÉS: %d | MIS À JOUR: %d | CANAUX AJOUTÉS: %d" % (created, patched, linked))


if __name__ == "__main__":
    main()
