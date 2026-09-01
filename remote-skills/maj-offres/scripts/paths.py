"""Résolution des chemins de la compétence maj-offres.

La compétence est distribuée par le plugin `sarecrute-admin` : son dossier
d'installation change à chaque version et est réécrit par `claude plugin
update`. Aucun script ne doit donc y écrire, ni supposer un chemin absolu.

  SITE  — dossier du site (contient offres.html et site_sarecrute_v4.html).
          Résolu par $SARECRUTE_SITE, sinon le dossier courant, sinon
          ~/code/Cleuteu/sarecrute.
  STATE — état persistant, dans le dossier du site (non déployé par deploy.sh).
  WORK  — dossier de travail, HORS du plugin : $MAJ_OFFRES_WORK, sinon
          ~/.sarecrute/maj-offres/work.
  SKILL — dossier de la compétence, en LECTURE seule (assets/ bundlés).
"""
import os
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def _resolve_site() -> Path:
    tried = []
    env = os.environ.get("SARECRUTE_SITE")
    candidates = ([Path(env).expanduser()] if env else []) + [
        Path.cwd(),
        Path.home() / "code" / "Cleuteu" / "sarecrute",
    ]
    for c in candidates:
        tried.append(str(c))
        if (c / "offres.html").is_file() and (c / "site_sarecrute_v4.html").is_file():
            return c
    raise SystemExit(
        "Dossier du site introuvable (offres.html + site_sarecrute_v4.html attendus).\n"
        "Essayé : " + ", ".join(tried) + "\n"
        "Lance la commande depuis le dossier du site, ou exporte SARECRUTE_SITE=/chemin/du/site."
    )


SITE = _resolve_site()
STATE = SITE / ".offres-state.json"

WORK = Path(os.environ.get("MAJ_OFFRES_WORK")
            or Path.home() / ".sarecrute" / "maj-offres" / "work").expanduser()
WORK.mkdir(parents=True, exist_ok=True)
