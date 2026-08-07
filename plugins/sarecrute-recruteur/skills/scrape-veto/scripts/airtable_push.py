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
  Champs matching (cf. matching_vocab.json) : Zones de recherche[], Statuts contractuels[],
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
HEADER_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2})\]\s*(\S*)\s*$")
VOWELS = set("aeiouy")
ORG_MARKERS = ("clinique", "cabinet", "service", "recrute", "hopital", "groupe", "veterinaire ")

# Champs recopiés depuis le post le plus récent lors d'un merge (tout sauf le contenu).
SCALAR_FIELDS = ["Prénom", "Nom", "Profil Facebook", "Date du post", "Lien du post", "Zone de recherche",
                 "Type de post", "Pratiques", "Spécialités", "Type d'entrée",
                 "Post source", "Expérience", "Nom de la clinique", "Archivé", "candidat_key",
                 "Zones de recherche", "Statuts contractuels", "Type de temps de travail",
                 "Date de disponibilité", "Rayon accepté (km)", "Contrat court"]

# Garde-fou : n'écrire QUE des valeurs select existantes (sinon Airtable crée une option).
_VOCAB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matching_vocab.json")
try:
    _V = json.load(open(_VOCAB_PATH))
    ALLOWED = {"Zones de recherche": set(_V["zones_de_recherche"]),
               "Statuts contractuels": set(_V["statuts_contractuels"]),
               "Type de temps de travail": set(_V["type_de_temps_de_travail"])}
except Exception:
    ALLOWED = {}


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
                "Type d'entrée", "candidat_key"]


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


def parse_sections(content, fb_date, fb_link):
    """Découpe un Contenu complet en sections {date, link, body}. Gère le legacy
    (post unique sans en-tête → une section avec la date/lien du record)."""
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
            secs.append({"date": m.group(1), "link": m.group(2), "body": "\n".join(lines[1:]).strip()})
        else:
            secs.append({"date": fb_date or "", "link": fb_link or "", "body": chunk})
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
    blocks = [("[%s] %s" % (s["date"], s["link"])).rstrip() + "\n" + s["body"] for s in secs]
    return SEP.join(blocks)


def scalars_from_newest(field_dicts):
    """Champs scalaires du post le plus récent (Date du post max)."""
    newest = max(field_dicts, key=lambda f: f.get("Date du post", ""))
    return {k: newest.get(k) for k in SCALAR_FIELDS if newest.get(k) is not None}


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
    by_key, exact_sigs = {}, set()
    for r in existing:
        f = r["fields"]
        exact_sigs.add(exact_key(f))
        if f.get("Type d'entrée") == "Commentaire":
            continue  # un commentaire n'est jamais une cible de fusion
        k = candidat_key(f.get("Prénom"), f.get("Nom"))
        if k:
            cur = by_key.get(k)
            if not cur or f.get("Date du post", "") > cur["fields"].get("Date du post", ""):
                by_key[k] = r

    to_create, to_patch, skipped = [], [], 0

    # 3) Personnes fiables → upsert.
    for k, flist in groups.items():
        in_secs = dedup_sections([s for f in flist for s in parse_sections(
            f.get("Contenu complet"), f.get("Date du post"), f.get("Lien du post"))])
        target = by_key.get(k)
        if target:
            tf = target["fields"]
            t_secs = parse_sections(tf.get("Contenu complet"), tf.get("Date du post"), tf.get("Lien du post"))
            t_sigs = {sec_sig(s) for s in t_secs}
            if {sec_sig(s) for s in in_secs} <= t_sigs:      # rien de neuf → idempotent
                skipped += len(flist)
                continue
            fields = scalars_from_newest(flist + [tf])
            fields["candidat_key"] = k
            fields["Contenu complet"] = render_sections(dedup_sections(in_secs + t_secs))
            to_patch.append((target["id"], fields, tf))
        else:
            fields = scalars_from_newest(flist)
            fields["candidat_key"] = k
            fields["Contenu complet"] = render_sections(in_secs)
            to_create.append({"fields": fields})

    # 4) Anonymes / non fiables → pas de fusion, garde d'idempotence exacte.
    seen_batch = set()
    for f in singles:
        ek = exact_key(f)
        if ek in exact_sigs or ek in seen_batch:
            skipped += 1
            continue
        seen_batch.add(ek)
        to_create.append({"fields": f})

    print("Input: %d lignes | nouveaux: %d | mises à jour: %d | ignorés (déjà en base): %d"
          % (len(records), len(to_create), len(to_patch), skipped))

    if dry:
        for c in to_create:
            f = c["fields"]
            who = (f.get("Prénom", "") + " " + f.get("Nom", "")).strip() or f.get("Nom de la clinique", "") or "(anonyme)"
            print("  + CRÉER ", f.get("Date du post"), "|", who, "::", (f.get("Contenu complet") or "")[:50].replace("\n", " "))
        for rid, f, tf in to_patch:
            who = (f.get("Prénom", "") + " " + f.get("Nom", "")).strip()
            print("  ~ MAJ   ", rid, "|", who, "| nouveau top:", f.get("Date du post"))
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

    patched = 0
    for rid, fields, _tf in to_patch:
        body = json.dumps({"fields": fields}).encode()
        req = urllib.request.Request(API + "/" + rid, data=body, method="PATCH",
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req).read()
            patched += 1
        except urllib.error.HTTPError as e:
            print("PATCH %s ERREUR %d: %s" % (rid, e.code, e.read().decode())); sys.exit(1)

    print("CRÉÉS: %d | MIS À JOUR: %d" % (created, patched))


if __name__ == "__main__":
    main()
