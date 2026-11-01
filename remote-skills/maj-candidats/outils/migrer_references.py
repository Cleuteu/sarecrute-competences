#!/usr/bin/env python3
"""Convertit un .candidats-state.json d'avant le 31/10/2026 (clés = identifiant opaque, 10 caractères
hexadécimaux, sha256 de l'identifiant Airtable) en clés SR-XXXXX (référence affichée sur la carte).

Lit les identifiants de la table Candidats (lecture seule), recalcule l'ancien identifiant de chaque
fiche et renomme les clés de `candidats`, `retenus` et `anciens`. Les valeurs ne changent pas : les
empreintes ne portent pas la référence, aucune description n'est donc à réécrire. Une clé déjà au
format SR-XXXXX est gardée telle quelle. Une clé qui n'est ni l'une ni l'autre (fiche supprimée
d'Airtable, ou référence mal recopiée dans une retenue) arrête tout sans rien écrire : la perdre
remettrait en ligne un candidat retenu.

  python3 outils/migrer_references.py [chemin de l'état]   (défaut : celui du dossier du site)
  --verifier   n'écrit rien, dit seulement ce qui serait fait
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from airtable import fetch_table   # noqa: E402
from fetch_candidats import C, REF_RE, T_CAND, ref_de   # noqa: E402
from paths import STATE   # noqa: E402


def ancien_identifiant(record_id):
    return hashlib.sha256(f"sarecrute:candidat:{record_id}".encode("utf-8")).hexdigest()[:10]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("etat", nargs="?", default=str(STATE))
    ap.add_argument("--verifier", action="store_true")
    args = ap.parse_args()
    chemin = Path(args.etat)
    etat = json.loads(chemin.read_text(encoding="utf-8"))

    vers_ref = {ancien_identifiant(r["id"]): ref_de(r["id"]) for r in fetch_table(T_CAND, [C["nom"]])}
    perdus, renommes = [], 0
    for section in ("candidats", "retenus", "anciens"):
        bloc, neuf = etat.get(section) or {}, {}
        for cle, valeur in bloc.items():
            if REF_RE.fullmatch(cle):
                cible = cle
            elif cle in vers_ref:
                cible, renommes = vers_ref[cle], renommes + 1
            else:
                perdus.append(f"{section}/{cle}")
                continue
            if cible in neuf:
                raise SystemExit(f"⛔ deux clés de {section} donnent {cible} : rien n'est écrit.")
            neuf[cible] = valeur
        if section in etat:
            etat[section] = dict(sorted(neuf.items()))

    print(f"{renommes} clé(s) renommée(s)")
    if perdus:
        raise SystemExit(f"⛔ clé(s) sans correspondance : {', '.join(map(repr, perdus))} (fiche supprimée "
                         "d'Airtable, ou référence mal recopiée). Rien n'est écrit : corriger ou retirer la clé "
                         "à la main dans l'état, puis relancer.")
    if args.verifier:
        return 0
    chemin.write_text(json.dumps(etat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"→ {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
