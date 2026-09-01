#!/usr/bin/env python3
"""
Étape 2b : garde-fou anonymat.

Compare chaque description à une liste noire construite depuis Airtable
(tous les noms de cliniques, villes, vétérinaires et domaines e-mail de la base)
et signale ce qui pourrait identifier une structure.

Deux niveaux :
  BLOQUANT — nom de clinique / ville / personne, e-mail, URL, téléphone, code
             postal. Sortie code 1 : ne pas appliquer avant correction.
  À VÉRIFIER — chiffres précis (taille d'équipe, surface, salaire…). Non bloquant,
             mais à relire : un « 3 vétérinaires + 400 m² » restreint beaucoup.

Ce contrôle attrape les recopiages littéraux. Il ne remplace pas la relecture.

Usage : python3 check_anonymat.py [--state]
  défaut  : contrôle work/descriptions.json (les nouvelles descriptions)
  --state : contrôle toutes les descriptions déjà enregistrées
"""
import argparse
import json
import re
import sys
import unicodedata

from paths import STATE, WORK

RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RE_URL = re.compile(r"https?://|www\.|\b[\w-]+\.(?:fr|com|vet|be|ch)\b", re.I)
RE_TEL = re.compile(r"(?:\+\d{2,3}[\s.]?)?(?:\d{2}[\s.]?){4}\d{2}")
RE_CP = re.compile(r"\b\d{5}\b")

# Villes/mots de la liste noire qu'on autorise malgré tout : pays et grandes
# régions sont volontairement publiés (le champ "departement" les affiche déjà).
VILLES_AUTORISEES = {
    "france", "suisse", "belgique", "espagne", "luxembourg", "bretagne",
    "alsace", "normandie", "corse", "provence", "occitanie", "romande",
}

# Seuls noms propres / acronymes autorisés en milieu de phrase dans une
# description. Tout autre mot capitalisé hors début de segment est traité comme
# un identifiant potentiel (ville, clinique, personne, marque).
MAJUSCULES_AUTORISEES = {
    "cdi", "cdd", "asv", "ccn", "cc", "nac", "irm", "tplo", "ct", "idexx",
    "improve", "cat", "dog", "friendly", "france", "suisse", "belgique",
    "espagne", "luxembourg", "bretagne", "alsace", "normandie", "corse",
    "provence", "occitanie", "romande", "europeen", "europeenne", "env", "chv",
    "ceav", "ecvs", "desv", "ces",
}


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def tokens_significatifs(nom):
    """Tokens d'un nom propre susceptibles d'identifier, hors mots génériques."""
    generiques = {
        "clinique", "cliniques", "veterinaire", "veterinaires", "vet", "cabinet",
        "centre", "chv", "hopital", "selarl", "scp", "sarl", "sas", "docteur",
        "dr", "de", "du", "des", "la", "le", "les", "et", "aux", "au", "d",
        "l", "saint", "sainte", "st", "ste", "mixte", "canin", "canine", "rural",
    }
    out = []
    for t in re.split(r"[^\wÀ-ÿ]+", norm(nom)):
        if len(t) >= 4 and t not in generiques:
            out.append(t)
    return out


def check(desc, offer, block):
    bloquant, avertir = [], []
    d = norm(desc)

    if RE_EMAIL.search(desc):
        bloquant.append("adresse e-mail")
    if RE_URL.search(desc):
        bloquant.append("URL / nom de domaine")
    if RE_TEL.search(desc):
        bloquant.append("numéro de téléphone")
    if RE_CP.search(desc):
        bloquant.append("code postal")
    if offer.get("_cp") and str(offer["_cp"]) in desc:
        bloquant.append(f'code postal exact : {offer["_cp"]}')

    for dom in block.get("domaines", []):
        if dom and norm(dom) in d:
            bloquant.append(f"domaine e-mail : « {dom} »")

    # Identifiants de CETTE offre : tolérance zéro. On se limite volontairement
    # à sa propre clinique / ville / vétérinaire — croiser avec les centaines
    # d'autres structures de la base ne produirait que du faux positif (les noms
    # de cliniques sont pleins de mots courants : « Pont neuf », « Deux Vallées »).
    for champ, label in (("_clinique", "nom de la clinique"),
                         ("_ville", "ville de la clinique"),
                         ("_veto", "nom du vétérinaire")):
        for tok in tokens_significatifs(offer.get(champ)):
            if tok in VILLES_AUTORISEES:
                continue
            if re.search(rf"\b{re.escape(tok)}\b", d):
                bloquant.append(f'{label} : « {tok} »')

    # Noms propres en milieu de phrase : une description bien écrite n'en contient
    # pas (hors acronymes et régions autorisés). Attrape les villes citées dans
    # l'annonce source (« à 30 min de Lille ») que le scope par offre ne voit pas.
    for seg in re.split(r"·|\.\s|:|;|\(|\)|/", desc):
        mots = re.findall(r"[\wÀ-ÿ'’\-]+", seg.strip())
        for i, mot in enumerate(mots):
            if i == 0 or not mot[:1].isupper():
                continue
            if norm(mot) in MAJUSCULES_AUTORISEES or len(mot) < 3:
                continue
            bloquant.append(f'nom propre en milieu de phrase : « {mot} »')

    nums = re.findall(r"\d[\d\s.,]*", desc)
    if nums:
        neutres = {"100", "24"}
        if not all(n.strip().rstrip(".,") in neutres for n in nums):
            avertir.append(f"chiffre(s) : {[n.strip() for n in nums]}")

    return sorted(set(bloquant)), sorted(set(avertir))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", action="store_true")
    args = ap.parse_args()

    offers = {o["ref"]: o for o in json.loads((WORK / "airtable.json").read_text())}
    bl_file = WORK / "blocklist.json"
    if not bl_file.exists():
        print("work/blocklist.json absent — relance fetch_offres.py.")
        return 1
    block = json.loads(bl_file.read_text())

    if args.state:
        state = json.loads(STATE.read_text())
        descs = {r: v.get("description", "") for r, v in state["offers"].items()}
    else:
        f = WORK / "descriptions.json"
        if not f.exists():
            print("work/descriptions.json absent — rien à contrôler.")
            return 0
        descs = json.loads(f.read_text())

    n_blocking = 0
    n_warn = 0
    checked = 0
    for ref in sorted(descs):
        desc = (descs[ref] or "").strip()
        if not desc:
            continue
        checked += 1
        offer = offers.get(ref)
        if not offer:
            print(f"⚠ BLOQUANT {ref} : hors périmètre (absent de airtable.json)")
            n_blocking += 1
            continue
        bloquant, avertir = check(desc, offer, block)
        if bloquant or avertir:
            print(f"\n{ref} — {offer['departement']}")
            print(f'   « {desc} »')
            for a in bloquant:
                print(f"   ⛔ {a}")
            for a in avertir:
                print(f"   ℹ  à vérifier — {a}")
            n_blocking += len(bloquant)
            n_warn += len(avertir)

    print(f"\n{checked} description(s) contrôlée(s) — "
          f"{n_blocking} bloquante(s), {n_warn} à vérifier.")
    if n_blocking:
        print("⛔ Corrige les alertes bloquantes avant d'appliquer.")
        return 1
    print("✔ Aucun élément identifiant détecté.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
