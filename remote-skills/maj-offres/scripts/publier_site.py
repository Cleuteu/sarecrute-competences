#!/usr/bin/env python3
"""
Étapes 6 et 7 de la routine cloud quotidienne : publier et rendre compte.

Ne tourne QUE dans un clone du dépôt GitHub Pages (Cleuteu/sarecrute), là où la page
d'accueil s'appelle index.html. Dans le dossier de travail local d'Alex, c'est deploy.sh
qui publie — ce script refuse d'y tourner.

  publier [--dry-run] [--attendre SEC]
      1. repasse le garde-fou anonymat sur TOUTES les descriptions enregistrées
         (check_anonymat.py --state) : une seule alerte bloquante = rien n'est publié ;
      2. vérifie que seuls offres.html, index.html et .offres-state.json ont changé ;
      3. commit (message fixe, sans aucun nom de clinique) et push sur main ;
      4. attend que sarecrute.com serve exactement le tableau OFFRES publié
         (le build Pages est asynchrone), au plus --attendre secondes ;
      5. écrit work/publication.json (statut, commit, mise en ligne confirmée ou non).
      Sans changement : « rien à publier », publication.json le dit, code 0.

  recap
      Compose le mail de compte rendu à partir de work/diff.json, work/todo.json,
      .offres-state.json et work/publication.json, et lit l'adresse de la destinataire
      dans la table Recruteurs (première recruteuse active dont le nom commence par le
      prénom donné, « Sarah » par défaut) — champ « Email compte Claude », l'adresse
      sarecrute, jamais le champ « Email » (gmail collaborateur Airtable). Alex est en copie :
      c'est l'adresse du compte du connecteur Gmail, la routine la connaît, pas ce script.
      Écrit work/recap.json : destinataire, copie, sujet, corps. Ce mail est INTERNE : il nomme les cliniques, c'est voulu — c'est ainsi que
      la recruteuse reconnaît ses dossiers. Rien de tout cela n'est commité.

Codes de sortie : 0 ok · 1 usage/environnement · 2 anonymat bloquant · 3 git/push.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from paths import SITE, HOME, STATE, WORK

SCRIPTS = Path(__file__).resolve().parent
SITE_URL = "https://sarecrute.com/offres.html"
FICHIERS_PUBLIES = ("offres.html", "index.html", ".offres-state.json")
T_RECRUTEURS = "tblDUpPwkuHYnAPyt"
F_REC_NOM, F_REC_ACTIF = "fldwLiZVl731wiI4o", "fldscrgHc1n9M60XZ"
F_REC_EMAIL = "fldaxrZ7PftpZQQfl"   # « Email compte Claude » = adresse sarecrute (décision d'Alex, 18/09/2026)
COPIE = "l'adresse du compte du connecteur Gmail (Alex)"


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(SITE), *args], check=check,
                          capture_output=True, text=True)


def heure_paris():
    # Europe/Paris sans dépendre de tzdata dans le conteneur : UTC+2 de fin mars à fin octobre.
    now = datetime.now(timezone.utc)
    d = now.date()
    def dernier_dimanche(mois):
        j = d.replace(month=mois, day=31)
        return j - timedelta(days=(j.weekday() + 1) % 7)
    ete = dernier_dimanche(3) <= d < dernier_dimanche(10)
    return now + timedelta(hours=2 if ete else 1)


def bloc_offres(html):
    m = re.search(r"const OFFRES = (\[.*?\]);", html, re.DOTALL)
    return m.group(1) if m else None


def lire(p, defaut):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else defaut


# ---------------------------------------------------------------- publier

def cmd_publier(args):
    if HOME.name != "index.html" or git("rev-parse", "--is-inside-work-tree", check=False).returncode:
        print("⛔ publier_site.py ne tourne que dans un clone du dépôt Pages (index.html + .git). "
              "Dans le dossier de travail local, c'est ./deploy.sh qui publie.")
        return 1

    # 1. anonymat sur tout l'état — bloquant
    r = subprocess.run([sys.executable, str(SCRIPTS / "check_anonymat.py"), "--state"],
                       capture_output=True, text=True)
    print(r.stdout.rstrip())
    if r.returncode:
        print("⛔ Contrôle d'anonymat bloquant : rien n'est publié.")
        (WORK / "publication.json").write_text(json.dumps(
            {"statut": "bloqué (anonymat)", "detail": r.stdout}, ensure_ascii=False, indent=1))
        return 2

    # 2. seuls les trois fichiers attendus bougent
    modifies = [l[3:].strip() for l in git("status", "--porcelain").stdout.splitlines() if l.strip()]
    inattendus = [f for f in modifies if f not in FICHIERS_PUBLIES]
    if inattendus:
        print(f"⛔ Fichiers modifiés hors périmètre, publication refusée : {inattendus}")
        return 3
    if not modifies:
        print("✔ Rien à publier : le dépôt est déjà à jour.")
        (WORK / "publication.json").write_text(json.dumps(
            {"statut": "rien à publier"}, ensure_ascii=False, indent=1))
        return 0
    print(f"→ à publier : {modifies}")

    if args.dry_run:
        print(git("diff", "--stat").stdout.rstrip())
        print("\n--dry-run : ni commit ni push.")
        return 0

    # 3. commit + push — message fixe : aucun nom de clinique ne doit entrer dans l'historique
    git("add", *[f for f in FICHIERS_PUBLIES if f in modifies])
    git("-c", "user.name=Routine SaRecrute", "-c", "user.email=routine@sarecrute.com",
        "commit", "-q", "-m", f"Mise à jour des offres — {heure_paris():%Y-%m-%d %H:%M} (routine)")
    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    p = git("push", "-q", "origin", "HEAD:main", check=False)
    if p.returncode:
        print(f"⛔ push refusé :\n{p.stderr.strip()}")
        (WORK / "publication.json").write_text(json.dumps(
            {"statut": "commit local, push refusé", "commit": sha, "detail": p.stderr},
            ensure_ascii=False, indent=1))
        return 3
    print(f"✔ Poussé : {sha}")

    # 4. attendre la version servie
    attendu = bloc_offres((SITE / "offres.html").read_text(encoding="utf-8"))
    en_ligne, debut = False, time.time()
    while time.time() - debut < args.attendre:
        try:
            with urllib.request.urlopen(SITE_URL, timeout=30) as resp:
                if bloc_offres(resp.read().decode("utf-8", "replace")) == attendu:
                    en_ligne = True
                    break
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"   (site injoignable : {e})")
        time.sleep(15)
    print("✔ En ligne : sarecrute.com sert le nouveau tableau d'offres." if en_ligne
          else f"⚠ Mise en ligne non confirmée après {args.attendre} s (le build Pages traîne ?).")

    (WORK / "publication.json").write_text(json.dumps({
        "statut": "publié", "commit": sha, "fichiers": modifies,
        "heure": heure_paris().strftime("%d/%m/%Y %H:%M"),
        "en_ligne_confirme": en_ligne,
    }, ensure_ascii=False, indent=1))
    return 0


# ---------------------------------------------------------------- recap

def destinataire(prenom):
    from fetch_offres import fetch_table  # lit AIRTABLE_API_KEY à l'import
    for r in fetch_table(T_RECRUTEURS, [F_REC_NOM, F_REC_EMAIL, F_REC_ACTIF]):
        f = r.get("fields", {})
        if f.get(F_REC_ACTIF) and str(f.get(F_REC_NOM, "")).strip().lower().startswith(prenom.lower()):
            if f.get(F_REC_EMAIL):
                return str(f[F_REC_NOM]).strip(), str(f[F_REC_EMAIL]).strip()
    raise SystemExit(f"Aucune recruteuse active « {prenom}… » avec e-mail dans Recruteurs.")


def libelle(o):
    clin = o.get("_clinique") or "(clinique inconnue)"
    ville = o.get("_ville")
    return f"{clin}" + (f" ({ville})" if ville else "") + f" — {o.get('titre') or '?'}"


def cmd_recap(args):
    diff = lire(WORK / "diff.json", None)
    if diff is None:
        print("work/diff.json absent — relance fetch_offres.py.")
        return 1
    todo = lire(WORK / "todo.json", [])
    airtable = {o["ref"]: o for o in lire(WORK / "airtable.json", [])}
    state = lire(STATE, {"offers": {}})["offers"]
    pub = lire(WORK / "publication.json", {"statut": "inconnu"})

    nom, email = destinataire(args.destinataire)
    prenom = nom.split()[0]
    date = heure_paris().strftime("%d/%m/%Y")
    ajouts, retraits = diff.get("ajoutees", []), diff.get("retirees", [])

    L = [f"Bonjour {prenom},", "",
         f"Le site a été mis à jour cette nuit ({date}). Voici ce qui a changé."]

    L += ["", f"Dépubliées ({len(retraits)})" if retraits else "Dépubliées : aucune"]
    for o in retraits:
        L.append(f"  - {libelle(o)} — {o.get('raison', '')}")

    L += ["", f"Publiées ({len(ajouts)})" if ajouts else "Publiées : aucune"]
    for o in ajouts:
        L.append(f"  - {libelle(o)}")
        desc = state.get(o["ref"], {}).get("description", "")
        if desc:
            L.append(f"      Description : {desc}")
        elif o["ref"] in diff.get("sans_texte_source", []):
            L.append("      Sans description : aucune annonce ni note sur la fiche Airtable.")
        else:
            L.append("      Sans description : aucun texte n'a passé le contrôle d'anonymat, "
                     "l'offre est en ligne sans ce bloc. À compléter à la main si besoin.")

    # « source modifiée » ne veut pas dire description changée : le modèle garde le texte
    # quand l'information n'a pas bougé. On ne signale que ce qui a vraiment changé.
    revues = [t for t in todo
              if t["raison"] == "source modifiée" and t["ref"] not in {a["ref"] for a in ajouts}
              and (t.get("description_actuelle") or "") != (state.get(t["ref"], {}).get("description") or "")]
    if revues:
        L += ["", f"Descriptions revues ({len(revues)}) — l'annonce ou les notes ont changé"]
        for t in revues:
            o = airtable.get(t["ref"], t)
            L.append(f"  - {libelle(o)}")
            L.append(f"      Avant : {t.get('description_actuelle') or '(vide)'}")
            L.append(f"      Après : {state.get(t['ref'], {}).get('description') or '(vide)'}")

    total = diff.get("total_publiables")
    L += ["", f"Offres en ligne : {total}" if total is not None else ""]
    if pub.get("statut") == "publié":
        L.append("Mise en ligne vérifiée sur sarecrute.com." if pub.get("en_ligne_confirme")
                 else "Publication poussée, mise en ligne pas encore confirmée au moment de l'envoi "
                      "(le site se met à jour en quelques minutes).")
    else:
        L.append(f"Attention : statut de publication « {pub.get('statut')} ».")
    L += ["", "Les noms de cliniques ci-dessus sont pour toi : sur le site, seul le département apparaît.",
          "", "— Routine SaRecrute (automatique, tous les jours à 2h)"]

    n = len(ajouts) + len(retraits)
    sujet = (f"Site SaRecrute — {len(ajouts)} publiée(s), {len(retraits)} dépubliée(s) — {date}"
             if n else f"Site SaRecrute — descriptions revues — {date}")
    recap = {"destinataire": email, "nom": nom, "copie": COPIE, "sujet": sujet,
             "corps": "\n".join(l for l in L if l is not None),
             "changements": n + len(revues)}
    (WORK / "recap.json").write_text(json.dumps(recap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {WORK}/recap.json — pour {nom} <{email}>, copie : {COPIE}\n")
    print(f"Sujet : {sujet}\n\n{recap['corps']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("publier")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--attendre", type=int, default=600, help="secondes d'attente du build Pages")
    p.set_defaults(fn=cmd_publier)
    r = sub.add_parser("recap")
    r.add_argument("--destinataire", default="Sarah", help="prénom dans la table Recruteurs")
    r.set_defaults(fn=cmd_recap)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
