#!/usr/bin/env python3
"""Les huit stubs (cinq recruteur, trois admin) téléchargent leur corps par `git clone` de `stable`
d'abord (proxy GitHub de la sandbox Cowork, seul chemin resté ouvert les 01/09, 10/09 et 11/09/2026),
puis `raw` en second. Un stub qui dériverait — un seul chemin, mauvais nom de compétence, repli sur
une copie locale — ne se verrait qu'au prochain incident réseau, chez une recruteuse.

    python3 tests/stubs_distants.test.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = {
    "sarecrute-recruteur": (
        ["creer-candidat", "creer-clinique-offre", "creer-brouillons-facebook", "creer-cv-candidat", "insta-follow-veto"],
        ("alex@botyglot.com",),  # mail d'incident : recruteur seulement
    ),
    "sarecrute-admin": (
        ["scrape-veto", "maj-offres", "insta-scrape-veto"],
        (),
    ),
}
INVARIANTS = (
    'GIT_TERMINAL_PROMPT=0 git clone -q --depth 1 --branch stable "$REPO"',
    'REPO="https://github.com/Cleuteu/sarecrute-competences"',
    "deuxième essai par raw",
    'curl -fsSL "$BASE/MANIFEST"',
    "**ARRÊTE.**",
    "Ne te rabats sur aucune copie locale",
)


def main() -> int:
    blocks = {}
    for plugin, (skills, extra) in PLUGINS.items():
        for s in skills:
            p = ROOT / "plugins" / plugin / "skills" / s / "SKILL.md"
            t = p.read_text(encoding="utf-8")
            m = re.search(r"```bash\n(.*?)\n```", t, flags=re.S)
            if not m:
                print(f"ÉCHEC : pas de bloc bash dans {p.relative_to(ROOT)}", file=sys.stderr)
                return 1
            block = m.group(1)
            if f'SKILL="{s}"' not in block:
                print(f"ÉCHEC : {s} : le bloc ne porte pas son propre nom de compétence", file=sys.stderr)
                return 1
            for needle in INVARIANTS + extra:
                if needle not in t:
                    print(f"ÉCHEC : {s} : « {needle} » absent du stub", file=sys.stderr)
                    return 1
            blocks[s] = block.replace(f'SKILL="{s}"', 'SKILL="X"')
    ref = next(iter(blocks.values()))
    diverge = [s for s, b in blocks.items() if b != ref]
    if diverge:
        print("ÉCHEC : bloc de téléchargement différent dans : " + ", ".join(diverge), file=sys.stderr)
        return 1
    print(f"Bloc de téléchargement (git puis raw) identique dans les {len(blocks)} stubs des deux plugins.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
