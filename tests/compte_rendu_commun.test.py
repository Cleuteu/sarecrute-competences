#!/usr/bin/env python3
"""La doctrine « compte rendu et incidents » est un seul texte, copié dans les cinq compétences
recruteur (`remote-skills/<compétence>/references/compte-rendu.md`), parce que chaque snapshot se
télécharge seul depuis son dossier. Une copie qui dérive, c'est une recruteuse qui reçoit une
consigne différente selon la compétence qu'elle lance — sans que rien ne le signale.

    python3 tests/compte_rendu_commun.test.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = [
    "creer-candidat",
    "creer-clinique-offre",
    "creer-brouillons-facebook",
    "creer-cv-candidat",
    "insta-follow-veto",
]
REL = Path("references") / "compte-rendu.md"


def main() -> int:
    texts = {}
    for s in SKILLS:
        p = ROOT / "remote-skills" / s / REL
        if not p.exists():
            print(f"ÉCHEC : {p.relative_to(ROOT)} manquant", file=sys.stderr)
            return 1
        texts[s] = p.read_text(encoding="utf-8")
    ref = texts[SKILLS[0]]
    diverge = [s for s, t in texts.items() if t != ref]
    if diverge:
        print("ÉCHEC : copies différentes de compte-rendu.md : " + ", ".join(diverge), file=sys.stderr)
        return 1
    for needle in ("alex@botyglot.com", "[SaRecrute] Échec", "**Fait**", "**À faire par vous**", "**Pas fait**", "debug"):
        if needle not in ref:
            print(f"ÉCHEC : « {needle} » absent de compte-rendu.md", file=sys.stderr)
            return 1
    print("compte-rendu.md identique dans les cinq compétences recruteur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
