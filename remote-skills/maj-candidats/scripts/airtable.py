"""Lecture de l'Airtable de production (lecture seule, aucune écriture).

La clé vient de AIRTABLE_API_KEY (routine cloud : variable de l'environnement) ; en local,
à défaut, de la ligne `export AIRTABLE_API_KEY=…` de ~/.zshrc.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "appP0W2ISytaNyAhG"


def _cle():
    cle = os.environ.get("AIRTABLE_API_KEY", "").strip()
    if cle:
        return cle
    zshrc = Path.home() / ".zshrc"
    if zshrc.is_file():
        for ligne in zshrc.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r'\s*export\s+AIRTABLE_API_KEY="?([^"\s]+)"?', ligne)
            if m:
                return m.group(1)
    raise SystemExit("AIRTABLE_API_KEY absente (environnement ou ~/.zshrc).")


def fetch_table(table, fields):
    """Tous les enregistrements de `table`, champs indexés par identifiant (returnFieldsByFieldId).

    Sans returnFieldsByFieldId, les champs reviennent indexés par nom et tous les filtres
    échouent en silence."""
    cle, recs, offset = _cle(), [], None
    while True:
        q = [("pageSize", "100"), ("returnFieldsByFieldId", "true")] + [("fields[]", f) for f in fields]
        if offset:
            q.append(("offset", offset))
        req = urllib.request.Request(
            f"https://api.airtable.com/v0/{BASE}/{table}?" + urllib.parse.urlencode(q),
            headers={"Authorization": f"Bearer {cle}"})
        for essai in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or essai == 3:
                    raise
                time.sleep(2 * (essai + 1))
        recs += d["records"]
        offset = d.get("offset")
        if not offset:
            return recs
        time.sleep(0.22)
