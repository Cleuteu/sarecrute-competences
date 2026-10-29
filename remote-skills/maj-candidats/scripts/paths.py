"""Résolution des chemins de maj-candidats (même convention que maj-offres).

  SITE  — dossier du site (contient offres.html et la page d'accueil). Résolu par
          $SARECRUTE_SITE, sinon le dossier courant, sinon ~/code/Cleuteu/sarecrute.
  HOME  — la page d'accueil : site_sarecrute_v4.html dans le dossier de travail local,
          index.html dans un clone du dépôt Pages Cleuteu/sarecrute (routine cloud).
  STATE — .candidats-state.json, dans le dossier du site. Versionné dans le dépôt Pages :
          descriptions déjà publiques, empreintes et réglages de carte, rien d'identifiant.
  WORK  — dossier de travail, hors du dépôt : $MAJ_CANDIDATS_WORK, sinon
          ~/.sarecrute/maj-candidats/work. Contient des données personnelles (noms,
          sources de rédaction) : rien de ce dossier ne doit être commité.
  SKILL — dossier de la compétence, en lecture seule (assets/).
"""
import os
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
HOME_NAMES = ("site_sarecrute_v4.html", "index.html")


def _home_in(site: Path):
    for name in HOME_NAMES:
        if (site / name).is_file():
            return site / name
    return None


def _resolve_site() -> Path:
    env = os.environ.get("SARECRUTE_SITE")
    candidates = ([Path(env).expanduser()] if env else []) + [
        Path.cwd(),
        Path.home() / "code" / "Cleuteu" / "sarecrute",
    ]
    for c in candidates:
        if (c / "offres.html").is_file() and _home_in(c) is not None:
            return c
    raise SystemExit(
        "Dossier du site introuvable (offres.html + site_sarecrute_v4.html ou index.html attendus).\n"
        "Essayé : " + ", ".join(map(str, candidates)) + "\n"
        "Lance la commande depuis le dossier du site, ou exporte SARECRUTE_SITE=/chemin/du/site."
    )


SITE = _resolve_site()
HOME = _home_in(SITE)
STATE = SITE / ".candidats-state.json"
PAGE = SITE / "candidats.html"

WORK = Path(os.environ.get("MAJ_CANDIDATS_WORK")
            or Path.home() / ".sarecrute" / "maj-candidats" / "work").expanduser()
WORK.mkdir(parents=True, exist_ok=True)
