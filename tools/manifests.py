#!/usr/bin/env python3
"""Génère (ou vérifie) le MANIFEST de chaque compétence distante de remote-skills/.

Pourquoi un manifest : depuis Cowork, github.com est filtré par le proxy de sortie
(« GitHub access to this repository is not enabled for this session », 403), donc le
tarball d'archive de la branche `stable` ne se télécharge pas. raw.githubusercontent.com
passe, mais il sert fichier par fichier : le stub SKILL.md a besoin de la liste des
fichiers à tirer. C'est ce MANIFEST.

Format du MANIFEST (première ligne = version, puis un chemin relatif par ligne) :

    version=0.2.0
    PROMPT.md
    references/champs-candidat.md
    scripts/cv.py

La version est celle de la première ligne du PROMPT.md (« **nom — version X.Y.Z (date)** »).
Le stub compare la version du manifest à celle du PROMPT.md téléchargé : raw sert chaque
fichier séparément, un `git push` entre deux téléchargements donnerait sinon un mélange de
versions sans que rien ne le signale.

Usage :
    python3 tools/manifests.py            # réécrit tous les MANIFEST
    python3 tools/manifests.py --check    # code 1 si un MANIFEST n'est pas à jour (test)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMOTE = ROOT / "remote-skills"
IGNORE_DIRS = {"__pycache__", ".DS_Store"}
IGNORE_SUFFIXES = {".pyc"}
VERSION_RE = re.compile(r"version (\d+\.\d+\.\d+)")


def version_of(skill: Path) -> str:
    first = (skill / "PROMPT.md").read_text(encoding="utf-8").splitlines()[0]
    m = VERSION_RE.search(first)
    if not m:
        sys.exit(f"{skill.name}/PROMPT.md : pas de version sur la première ligne : {first!r}")
    return m.group(1)


def files_of(skill: Path) -> list[str]:
    out = []
    for p in sorted(skill.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(skill)
        if rel.name == "MANIFEST" or rel.name in IGNORE_DIRS:
            continue
        if any(part in IGNORE_DIRS for part in rel.parts) or p.suffix in IGNORE_SUFFIXES:
            continue
        if re.search(r"\s", rel.as_posix()):
            # Le stub parcourt le MANIFEST avec `for f in $(…)` : un espace couperait le chemin.
            sys.exit(f"{skill.name}: chemin avec espace interdit dans remote-skills : {rel}")
        out.append(rel.as_posix())
    # PROMPT.md en premier : c'est lui que le stub lit pour vérifier la version.
    out.sort(key=lambda s: (s != "PROMPT.md", s))
    return out


def manifest_text(skill: Path) -> str:
    return "\n".join([f"version={version_of(skill)}", *files_of(skill)]) + "\n"


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for skill in sorted(p for p in REMOTE.iterdir() if p.is_dir()):
        if not (skill / "PROMPT.md").exists():
            continue
        wanted = manifest_text(skill)
        target = skill / "MANIFEST"
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == wanted:
            continue
        if check:
            stale.append(skill.name)
        else:
            target.write_text(wanted, encoding="utf-8")
            print(f"écrit  {target.relative_to(ROOT)}")
    if check and stale:
        print(
            "MANIFEST périmé pour : " + ", ".join(stale) + "\n"
            "→ python3 tools/manifests.py, puis committer les MANIFEST avec la modification.",
            file=sys.stderr,
        )
        return 1
    if check:
        print("MANIFEST à jour pour toutes les compétences distantes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
