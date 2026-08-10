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
  Zone de recherche, Contenu complet, Type de post, Pratiques[], Spécialités[],
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
  Ne PAS renseigner candidat_key : le script le calcule. Les valeurs select hors
  vocabulaire sont ignorées automatiquement (jamais de création d'option).

Déduplication — deux régimes :
  • Nom FIABLE (candidat_key non vide) → UPSERT par personne, toutes dates
    confondues. Si la personne existe déjà, on MET À JOUR son enregistrement :
    le nouveau post est empilé en haut de "Contenu complet" (séparateur daté,
    plus récent en premier), et les champs scalaires (Date, Zone, Pratiques…)
    prennent les valeurs du post le PLUS RÉCENT. Rien n'est perdu.
  • Nom ANONYME / non fiable → PAS de fusion. On crée, sauf si EXACTEMENT la
    même publication est déjà en base (garde d'idempotence Date|Type|Nom|Contenu[:60]).

Dans les DEUX régimes, « rien de neuf dans le contenu » ne veut pas dire « rien à
écrire » : un post rigoureusement identique cross-posté dans deux groupes apporte une
ORIGINE nouvelle. Les gardes d'idempotence ajoutent donc le canal manquant (ligne
« ⊕ CANAL » en --dry) sans toucher au contenu ni aux champs scalaires.

candidat_key = prénom+nom normalisés (sans accents, minuscules). Vide (donc pas
de fusion) si : nom vide / "Membre anonyme" / non-personnel (chiffres, tout en
capitales, > 4 mots, marqueurs "clinique/service/recrute/cabinet") / surnom
tronqué (nom ≤ 3 lettres ou sans voyelle, ex. Lmd, Drc, Vie).
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
VOWELS = set("aeiouy")
ORG_MARKERS = ("clinique", "cabinet", "service", "recrute", "hopital", "groupe", "veterinaire ")

# Champs recopiés depuis le post le plus récent lors d'un merge (tout sauf le contenu).
SCALAR_FIELDS = ["Prénom", "Nom", "Profil Facebook", "Date du post", "Lien du post", "Zone de recherche",
                 "Type de post", "Pratiques", "Spécialités", "Type d'entrée",
                 "Post source", "Expérience", "Nom de la clinique", "Archivé", "candidat_key",
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
GUARDED_FIELDS = ("Zones de recherche", "Statuts contractuels", "Type de temps de travail")
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
                "Type d'entrée", "candidat_key", "Canaux"]


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def norm(s):
    return re.sub(r"\s+", " ", strip_accents(s).lower()).strip()


def candidat_key(prenom, nom):
    """Clé personne fiable, ou '' si anonyme / non fiable (→ pas de fusion)."""
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
    if len(full.split()) > 4:
        return ""
    if any(c.isalpha() for c in full) and full == full.upper():   # tout en capitales
        return ""
    if any(m in low + " " for m in ORG_MARKERS):
        return ""
    n_alpha = re.sub(r"[^a-z]", "", strip_accents(nom).lower())   # surnom tronqué
    if len(n_alpha) <= 3 or not (set(n_alpha) & VOWELS):
        return ""
    return norm(full)


def exact_key(f):
    """Signature d'une publication exacte (idempotence pour les anonymes)."""
    body = re.sub(r"\s+", " ", (f.get("Contenu complet") or "")).strip().lower()[:60]
    return "|".join([f.get("Date du post", ""), f.get("Type d'entrée", ""),
                     norm(f.get("Prénom")), norm(f.get("Nom")), body])


def sec_sig(s):
    return (s["date"], re.sub(r"\s+", " ", s["body"]).strip().lower()[:80])


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


def scalars_from_newest(field_dicts):
    """Champs scalaires du post le plus récent (Date du post max)."""
    newest = max(field_dicts, key=lambda f: f.get("Date du post", ""))
    return {k: newest.get(k) for k in SCALAR_FIELDS if newest.get(k) is not None}


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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    token = os.environ.get("AIRTABLE_API_KEY")
    if not token:
        sys.exit("AIRTABLE_API_KEY manquant (export depuis ~/.zshrc).")
    if not args:
        sys.exit("Usage: airtable_push.py records.json [--dry]")
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
    groups, singles = {}, []
    for r in records:
        f = sanitize_selects(dict(r["fields"]))
        # Les commentaires ne fusionnent JAMAIS par personne (une réaction n'est pas
        # un profil candidat) → toujours créés (dédup sur publication exacte).
        is_comment = f.get("Type d'entrée") == "Commentaire"
        k = "" if is_comment else candidat_key(f.get("Prénom"), f.get("Nom"))
        f["candidat_key"] = k
        (groups.setdefault(k, []).append(f) if k else singles.append(f))

    # 2) Index de l'existant. On recalcule la clé depuis le nom (les records
    #    legacy ont candidat_key vide) → l'upsert marche même sans backfill.
    existing = fetch_all(token)
    by_key, exact_recs = {}, {}
    for r in existing:
        f = r["fields"]
        # exact_recs (et pas un simple set) : quand la publication est déjà en base, il
        # faut pouvoir la PATCHER pour lui ajouter un canal manquant (cf. add_canaux).
        exact_recs.setdefault(exact_key(f), r)
        if f.get("Type d'entrée") == "Commentaire":
            continue  # un commentaire n'est jamais une cible de fusion
        k = candidat_key(f.get("Prénom"), f.get("Nom"))
        if k:
            cur = by_key.get(k)
            if not cur or f.get("Date du post", "") > cur["fields"].get("Date du post", ""):
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
        target = by_key.get(k)
        if target:
            tf = target["fields"]
            t_secs = parse_sections(tf.get("Contenu complet"), tf.get("Date du post"),
                                    tf.get("Lien du post"), canal_of(tf, canaux))
            t_sigs = {sec_sig(s) for s in t_secs}
            if {sec_sig(s) for s in in_secs} <= t_sigs:      # aucune section nouvelle
                add_canaux(target, flist)                    # …mais peut-être un canal
                skipped += len(flist)
                continue
            fields = scalars_from_newest(flist + [tf])
            fields["candidat_key"] = k
            # Union des canaux : la fusion ajoute une origine, elle n'en remplace pas.
            # (in_secs d'abord dans le dédup → un en-tête legacy sans canal se voit
            #  enrichi par la version datée du canal, à signature identique.)
            union = union_links(flist + [tf])
            if union:
                fields["Canaux"] = union
            fields["Contenu complet"] = render_sections(dedup_sections(in_secs + t_secs))
            to_patch.append((target["id"], fields, tf))
        else:
            fields = scalars_from_newest(flist)
            fields["candidat_key"] = k
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
