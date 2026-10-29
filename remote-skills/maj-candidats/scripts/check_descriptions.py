#!/usr/bin/env python3
"""Garde-fou des descriptions publiques de candidats : attrape les recopiages littéraux et les
écarts de format. Ne remplace pas la relecture (PROMPT.md, « Vérifier ») : il ne juge pas le sens.

  (défaut)  contrôle work/descriptions.json (les descriptions écrites ce soir)
  --state   contrôle toutes les descriptions de .candidats-state.json dont le candidat est encore
            publiable (son dossier est dans work/dossiers/)

Chaque description est confrontée aux termes interdits de son dossier (nom, prénom, e-mail,
téléphone, ville, code postal, école, année de sortie, diplôme, structures et villes du parcours),
y compris leurs dérivés (« rennaise » pour Rennes), puis à des listes bloquantes : internat,
nationalités et gentilés, nombres en lettres, marqueurs du poste actuel. Code 1 si une alerte
bloquante subsiste. Un faux positif se corrige en reformulant : mieux vaut réécrire une phrase
anodine que laisser passer un détail qui désigne la personne.
"""
import argparse
import json
import re
import sys
import unicodedata

from paths import STATE, WORK


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


GENERIQUES = {"clinique", "cliniques", "veterinaire", "veterinaires", "cabinet", "centre", "hopital",
              "selarl", "scp", "sarl", "sas", "docteur", "saint", "sainte", "mixte", "canin", "canine",
              "rural", "rurale", "urgence", "urgences", "animaux", "france", "suisse", "belgique",
              "espagne", "luxembourg", "groupe", "sante", "animal", "equine", "equin", "bovine", "service",
              "services", "universite", "ecole", "nationale", "faculte", "medecine", "specialisee",
              "referes", "refere", "chirurgie", "imagerie", "consultation", "pratique", "stage",
              "internat", "remplacement", "remplacements", "clinic", "hospital", "veterinary", "vet",
              "vets", "vetos", "pole", "domicile", "chats", "chiens", "chevaux", "elevage",
              "feline", "felin", "interne", "diplome", "master", "soins", "intensifs", "canins",
              "chien", "chat", "hospitalier", "hospitaliere", "hospitalisation", "reference", "urgentiste"}
MAJ_OK = {"nac", "cdi", "cdd", "asv", "desv", "ces", "irm", "tplo", "ct", "cat", "friendly"}
MOTS_PROSCRITS = ["passionn", "dynamique", "motive", "pepite", "profil ideal", "valoris", "opportunit",
                  "mise en recit", "reseau active", "remuneration", "salaire", "echelon", "point faible",
                  "promotion", "ancien militaire"]
# Catégories que la doctrine interdit et que les termes du dossier ne couvrent pas (PROMPT.md, § 2).
BLOQUANTS = [
    # « médecine interne » et « former en interne » sont des expressions courantes, pas un internat
    (r"\binterna[ts]?\b|(?<!medecine )(?<!en )\binternes?\b|r[ée]sidanat|\bresidency\b|\binternship\b",
     "internat (formation rare)"),
    (r"\b(?:actuel(?:le)?s?|actuellement|aujourd'hui|en ce moment)\b", "poste actuel"),
    (r"\b(?:en charge d|responsable d|chef d|seule? v[ée]t[ée]rinaire|encadrement d'(?:une )?[ée]quipe|"
     r"gestion d'(?:une )?[ée]quipe|management d'(?:une )?[ée]quipe)", "poste actuel (fonctions)"),
    (r"\banciens? |\banciennes? |\bex-", "parcours singularisant (« ancien… »)"),
    (r"\b(?:deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|quinze|vingt|trente|cent|mille|"
     r"dizaines?|douzaines?|vingtaines?|trentaines?|centaines?)\b", "nombre en lettres"),
    (r"\b(?:fran[cç]ais|belges?|suisses?|luxembourgeois|espagnol|italien|portugais|allemand|roumain|"
     r"hongrois|polonais|bulgare|tch[eè]que|slovaque|croate|serbe|grec|britannique|anglais|irlandais|"
     r"n[ée]erlandais|hollandais|libanais|marocain|alg[ée]rien|tunisien|s[ée]n[ée]galais|ivoirien|"
     r"camerounais|qu[ée]b[ée]cois|canadien|am[ée]ricain|br[ée]silien|argentin|parisien|lyonnais|"
     r"marseillais|toulousain|nantais|bordelais|lillois|rennais|strasbourgeois|niçois|montpelli[ée]rain|"
     r"breton|normand|alsacien|lorrain|savoyard|basque|corse|wallon|flamand|bruxellois|genevois|vaudois|"
     r"fribourgeois|valaisan|neuch[aâ]telois)(?:e|es|s|ne|nes)?\b", "nationalité ou gentilé"),
]
GENRE = re.compile(r"\b(diplom|form|install|passionn|motiv|specialis|habitu|interess|attir|bas|orient|"
                   r"habilit|recrut|confront|expos|implant|engag|lanc|ne|nee)ee?s?\b", re.I)


def alertes(desc, interdits):
    pb = []
    d = norm(desc)
    segs = [s.strip() for s in desc.split(" · ")]
    if len(segs) != 3:
        pb.append(f"{len(segs)} segment(s) au lieu de 3")
    if not (100 <= len(desc) <= 250):
        pb.append(f"longueur {len(desc)}")
    if desc.rstrip().endswith("."):
        pb.append("point final")
    if re.search(r"\d", desc):
        pb.append("chiffre")
    if re.search(r"@|https?://|www\.", desc):
        pb.append("e-mail / URL")
    for terme in interdits:
        for tok in re.split(r"[^\w]+", norm(terme)):
            if len(tok) < 4 or tok in GENERIQUES:
                continue
            # dérivés : « rennes » attrape « rennaise », « bucarest » attrape « bucarestois » ; un terme
            # de quatre lettres ne se cherche qu'en mot entier (« post » ne doit pas attraper « poste »)
            racine = tok[:-2] if len(tok) >= 6 else tok[:-1] if len(tok) == 5 else None
            if re.search(rf"\b{re.escape(tok)}\b", d) or (racine and re.search(rf"\b{re.escape(racine)}\w*", d)):
                pb.append(f"terme interdit : « {tok} »")
    for motif, libelle in BLOQUANTS:
        m = re.search(motif, d)
        if m:
            pb.append(f"{libelle} : « {m.group(0).strip()} »")
    for seg in segs:
        for k, mot in enumerate(re.findall(r"[\wÀ-ÿ'’\-]+", seg)):
            if k and mot[:1].isupper() and norm(mot) not in MAJ_OK:
                pb.append(f"majuscule en milieu de segment : « {mot} »")
    for w in MOTS_PROSCRITS:
        if w in d:
            pb.append(f"mot proscrit : « {w} »")
    for m in GENRE.finditer(d):
        if m.group(0).endswith(("ee", "ees")):
            pb.append(f"accord genré : « {m.group(0)} »")
    if re.search(r"\b(il|elle)\b", d):
        pb.append("pronom sujet")
    return sorted(set(pb))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", action="store_true", help="contrôler toutes les descriptions en ligne")
    args = ap.parse_args()
    if args.state:
        etat = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"candidats": {}}
        descs = {r: c.get("description", "") for r, c in etat.get("candidats", {}).items()}
        if descs and not (WORK / "dossiers").is_dir():
            print("⛔ work/dossiers absent : lance fetch_candidats.py avant le contrôle (sans dossiers, rien n'est vérifié).")
            return 1
    else:
        f = WORK / "descriptions.json"
        descs = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    bloquants, controles = 0, 0
    for ref, desc in sorted(descs.items()):
        dossier = WORK / "dossiers" / f"{ref}.json"
        if not dossier.exists():
            if not args.state:
                print(f"\n{ref} : pas de dossier dans work/dossiers (candidat hors périmètre ?)\n   ⛔ refusé")
                bloquants += 1
            continue   # --state : candidat qui sort du périmètre ce soir, sa carte sera retirée
        controles += 1
        pb = alertes(desc, json.loads(dossier.read_text(encoding="utf-8"))["interdits"])
        if pb:
            bloquants += 1
            print(f"\n{ref} « {desc} »")
            for p in pb:
                print(f"   ⛔ {p}")
    print(f"\n{controles} description(s) contrôlée(s) — {bloquants} avec alerte.")
    return 1 if bloquants else 0


if __name__ == "__main__":
    sys.exit(main())
