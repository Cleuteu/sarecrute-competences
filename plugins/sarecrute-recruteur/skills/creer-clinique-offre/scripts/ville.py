#!/usr/bin/env python3
"""Résout une ville française en département (county), CP et coordonnées.

Interroge le MÊME fichier que l'automation Airtable « Localisation Clinique »
(villes_france - villes.csv du dépôt Cleuteu/geo-data) et reproduit sa règle de
correspondance : égalité stricte du nom de commune, en minuscules. Sert à écrire
dans « Ville » une orthographe que l'automation retrouvera, et à repérer les
homonymes où elle choisirait le mauvais département.

Usage :
    python3 ville.py "Le Plessis-Belleville"
    python3 ville.py "Brignoles" --cp 83170
    python3 ville.py "st etienne" --cp 42100
"""

import argparse
import csv
import json
import os
import sys
import time
import unicodedata
import urllib.request

CSV_URL = (
    "https://raw.githubusercontent.com/Cleuteu/geo-data/refs/heads/main/"
    "villes_france%20-%20villes.csv"
)
CACHE = os.path.expanduser("~/.sarecrute/villes_france.csv")
CACHE_MAX_AGE = 30 * 24 * 3600  # 30 jours

ABREVIATIONS = {
    "st": "saint",
    "ste": "sainte",
    "sts": "saints",
    "stes": "saintes",
}


def charger_csv():
    frais = os.path.exists(CACHE) and (time.time() - os.path.getmtime(CACHE)) < CACHE_MAX_AGE
    if not frais:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        try:
            with urllib.request.urlopen(CSV_URL, timeout=30) as r:
                data = r.read()
            with open(CACHE, "wb") as f:
                f.write(data)
        except Exception as e:  # cache périmé mais présent = mieux que rien
            if not os.path.exists(CACHE):
                print(json.dumps({"erreur": f"téléchargement du CSV impossible : {e}"},
                                 ensure_ascii=False))
                sys.exit(2)
    with open(CACHE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normaliser(s):
    """Forme relâchée pour retrouver une orthographe approchante."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    for car in "-'’.":
        s = s.replace(car, " ")
    mots = [ABREVIATIONS.get(m, m) for m in s.split() if m]
    return " ".join(mots)


def ligne(row):
    return {
        "ville": row["ville"],
        "county": row["departement"],
        "code_postal": row["code_postal"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ville")
    p.add_argument("--cp", help="code postal lu dans l'annonce, pour départager les homonymes")
    args = p.parse_args()

    villes = charger_csv()
    cible = (args.ville or "").strip()

    # Ce que l'automation Airtable verrait : égalité stricte, en minuscules.
    exacts = [r for r in villes if r["ville"].lower() == cible.lower()]

    res = {
        "requete": cible,
        "cp_fourni": args.cp,
        "trouve": bool(exacts),
        "orthographe_reconnue_par_l_automation": bool(exacts),
        "avertissements": [],
    }

    if not exacts:
        approche = [r for r in villes if normaliser(r["ville"]) == normaliser(cible)]
        res["propositions"] = [ligne(r) for r in approche[:10]]
        if approche:
            res["avertissements"].append(
                "L'automation Airtable ne reconnaîtra PAS cette orthographe (elle compare le nom "
                "à l'identique). Écris dans « Ville » l'orthographe proposée ci-dessus."
            )
        else:
            res["avertissements"].append(
                "Commune absente du CSV (commune étrangère, arrondissement, ou nom erroné). "
                "Aucune géolocalisation automatique : renseigne « county » à la main sur la "
                "clinique, sinon aucun matching ne tournera."
            )
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    res["nb_communes_de_ce_nom"] = len(exacts)
    if len(exacts) > 1:
        res["homonymes"] = [ligne(r) for r in exacts[:8]]
    premier = ligne(exacts[0])  # celui que l'automation retiendra
    res["choisi_par_l_automation"] = premier

    retenu = premier
    if args.cp:
        cp = args.cp.strip().replace(" ", "")
        sur_cp = [r for r in exacts if r["code_postal"] == cp]
        if not sur_cp:
            sur_cp = [r for r in exacts if r["code_postal"][:2] == cp[:2]]
        if sur_cp:
            retenu = ligne(sur_cp[0])
        else:
            res["avertissements"].append(
                f"Aucune des {len(exacts)} communes nommées « {cible} » ne porte le CP {cp} : "
                "vérifie la ville et le CP de l'annonce."
            )
    res["retenu"] = retenu

    if len(exacts) > 1:
        res["avertissements"].append(
            f"{len(exacts)} communes portent ce nom. L'automation prendra "
            f"« {premier['county']} » (CP {premier['code_postal']})."
        )
    if retenu["county"] != premier["county"]:
        res["avertissements"].append(
            f"CORRECTION À FAIRE APRÈS CRÉATION : county = « {retenu['county']} » et "
            f"CP = {retenu['code_postal']}. L'automation aura écrit "
            f"« {premier['county']} » / {premier['code_postal']}, ce qui enverrait l'offre "
            "dans le mauvais département."
        )

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
