#!/usr/bin/env python3
"""Télécharge la doctrine d'enrichissement candidat depuis le dépôt et l'écrit sur stdout.

Le prompt de la routine cloud « Enrichissement candidat » est versionné dans
Cleuteu/sarecrute-competences (routines/profil-ia-candidat.md). C'est LUI qui fait
autorité sur l'extraction des champs, la cotation des actes et la rédaction du
Profil IA — la compétence le lit au lieu de le recopier, pour qu'il n'existe qu'à
un seul endroit et que la routine cloud et la compétence ne divergent jamais.

Le fichier n'est pas bundlé dans le plugin : `routines/` vit à la racine du dépôt,
pas sous `plugins/`. D'où le téléchargement, avec cache local en repli.

Usage :
    python3 routine.py              # écrit le prompt sur stdout
    python3 routine.py --path       # écrit seulement le chemin du fichier en cache
    python3 routine.py --refresh    # ignore le cache et retélécharge
"""

import argparse
import json
import os
import sys
import time
import urllib.request

RAW_URL = (
    "https://raw.githubusercontent.com/Cleuteu/sarecrute-competences/"
    "main/routines/profil-ia-candidat.md"
)
CACHE = os.path.expanduser("~/.sarecrute/profil-ia-candidat.md")
CACHE_MAX_AGE = 6 * 3600  # 6 h : le prompt bouge, mais pas plusieurs fois par heure
TAILLE_MINIMALE = 5000  # un prompt tronqué est plus dangereux qu'une erreur franche


def telecharger():
    with urllib.request.urlopen(RAW_URL, timeout=30) as r:
        return r.read().decode("utf-8")


def charger(refresh=False):
    """Renvoie (texte, origine). Origine : 'dépôt' ou 'cache (<âge>)'."""
    frais = (
        not refresh
        and os.path.exists(CACHE)
        and (time.time() - os.path.getmtime(CACHE)) < CACHE_MAX_AGE
    )
    if frais:
        with open(CACHE, encoding="utf-8") as f:
            texte = f.read()
        if len(texte) >= TAILLE_MINIMALE:
            age = int((time.time() - os.path.getmtime(CACHE)) / 60)
            return texte, f"cache ({age} min)"

    try:
        texte = telecharger()
    except Exception as e:
        # Un cache périmé vaut mieux qu'un enrichissement improvisé de mémoire.
        if os.path.exists(CACHE):
            with open(CACHE, encoding="utf-8") as f:
                texte = f.read()
            if len(texte) >= TAILLE_MINIMALE:
                age = int((time.time() - os.path.getmtime(CACHE)) / 3600)
                print(
                    f"⚠️  Dépôt injoignable ({e}) — prompt lu dans le cache local "
                    f"(vieux de {age} h). Vérifier qu'il est à jour avant de s'y fier.",
                    file=sys.stderr,
                )
                return texte, f"cache périmé ({age} h)"
        print(
            json.dumps(
                {
                    "erreur": f"téléchargement impossible : {e}",
                    "cache": "absent ou tronqué",
                    "repli": "ne pas improviser l'enrichissement — créer la fiche avec ses "
                    "sources, puis lancer le bouton « Enrichissement candidat » depuis "
                    "l'interface Airtable et laisser Statut IA vide",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(2)

    if len(texte) < TAILLE_MINIMALE:
        print(
            json.dumps(
                {
                    "erreur": f"prompt anormalement court ({len(texte)} caractères) — "
                    "réponse tronquée ou fichier déplacé dans le dépôt",
                    "url": RAW_URL,
                    "repli": "lancer le bouton « Enrichissement candidat » depuis l'interface",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(2)

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        f.write(texte)
    return texte, "dépôt"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--path", action="store_true", help="écrire le chemin du cache, pas le contenu")
    p.add_argument("--refresh", action="store_true", help="ignorer le cache")
    args = p.parse_args()

    texte, origine = charger(refresh=args.refresh)

    if args.path:
        print(CACHE)
        return

    print(
        f"# Doctrine d'enrichissement candidat — source : {origine}\n"
        f"# {RAW_URL}\n"
        f"# Ce qui suit fait autorité. Voir l'ÉTAPE 6 du SKILL.md pour les cinq adaptations\n"
        f"# (recordId, Statut IA, sources déjà écrites, compte rendu) — et rien d'autre.\n"
    )
    print(texte)


if __name__ == "__main__":
    main()
