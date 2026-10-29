#!/usr/bin/env python3
"""
Étapes 6 et 7 de la routine cloud quotidienne : publier et rendre compte.

Ne tourne QUE dans un clone du dépôt GitHub Pages (Cleuteu/sarecrute), là où la page
d'accueil s'appelle index.html. Dans le dossier de travail local d'Alex, c'est deploy.sh
qui publie — ce script refuse d'y tourner.

  publier [--dry-run] [--attendre SEC]
      1. repasse le garde-fou anonymat sur TOUTES les descriptions enregistrées
         (check_anonymat.py --state pour les offres ; maj-candidats/check_descriptions.py --state
         pour les candidats si leur page ou leur état a changé) : une seule alerte bloquante = rien
         n'est publié ;
      2. vérifie que seuls offres.html, index.html, .offres-state.json, candidats.html et
         .candidats-state.json ont changé ;
      3. commit (message fixe, sans aucun nom de clinique ni de candidat) et push sur main ;
      4. attend que sarecrute.com serve exactement les tableaux OFFRES et CANDIDATS publiés
         (le build Pages est asynchrone), au plus --attendre secondes ;
      5. écrit work/publication.json (statut, commit, mise en ligne confirmée ou non).
      Sans changement : « rien à publier », publication.json le dit, code 0.

  recap
      Compose le compte rendu à partir de work/diff.json, work/todo.json, .offres-state.json,
      work/publication.json et, pour les candidats, du travail de maj-candidats (diff.json,
      apply.json, .candidats-state.json), et lit l'adresse de la destinataire
      dans la table Recruteurs (première recruteuse active dont le nom commence par le
      prénom donné, « Sarah » par défaut) — champ « Email compte Claude », l'adresse
      sarecrute, jamais le champ « Email » (gmail collaborateur Airtable). Alex est en copie :
      c'est l'adresse du compte du connecteur Gmail, la routine la connaît, pas ce script.
      Écrit work/recap.json : destinataire, copie, sujet, corps. Ce message est INTERNE : il
      nomme les cliniques, c'est voulu — c'est ainsi que la recruteuse reconnaît ses dossiers.
      Rien de tout cela n'est commité.

  telegram [--echec TEXTE]
      Envoie work/recap.json par l'API Bot Telegram (variable TELEGRAM_BOT_TOKEN) à la
      recruteuse (champ « Telegram chat ID » de sa fiche Recruteurs) et à Alex
      (variable TELEGRAM_CHAT_ALEX). Décision d'Alex du 18/09/2026 : Telegram remplace le
      mail, le connecteur Gmail des routines ne sachant que créer des brouillons.
      --echec TEXTE : envoie TEXTE à Alex seul (compte rendu d'incident), sans recap.json.
      Sans jeton : code 1 et rien d'envoyé — la routine se rabat sur un brouillon Gmail.

  telegram --decouvrir
      Affiche les chat ID des personnes qui ont écrit au bot (getUpdates), pour remplir
      « Telegram chat ID » dans Recruteurs et TELEGRAM_CHAT_ALEX. À lancer en local.

Codes de sortie : 0 ok · 1 usage/environnement · 2 anonymat bloquant · 3 git/push · 4 Telegram refusé.
"""
import argparse
import json
import os
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
SITE_URL_CANDIDATS = "https://sarecrute.com/candidats.html"
FICHIERS_PUBLIES = ("offres.html", "index.html", ".offres-state.json", "candidats.html", ".candidats-state.json")
FICHIERS_CANDIDATS = ("candidats.html", ".candidats-state.json")
# Le volet candidats (remote-skills/maj-candidats) a son propre dossier de travail.
SCRIPTS_CANDIDATS = SCRIPTS.parent.parent / "maj-candidats" / "scripts"
WORK_CANDIDATS = Path(os.environ.get("MAJ_CANDIDATS_WORK")
                      or Path.home() / ".sarecrute" / "maj-candidats" / "work").expanduser()
STATE_CANDIDATS = SITE / ".candidats-state.json"
T_RECRUTEURS = "tblDUpPwkuHYnAPyt"
F_REC_NOM, F_REC_ACTIF = "fldwLiZVl731wiI4o", "fldscrgHc1n9M60XZ"
F_REC_EMAIL = "fldaxrZ7PftpZQQfl"   # « Email compte Claude » = adresse sarecrute (décision d'Alex, 18/09/2026)
F_REC_TELEGRAM = "fldxtWfHEbPeYUPJG"  # « Telegram chat ID »
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
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


def bloc_candidats(html):
    m = re.search(r"const CANDIDATS = (\[.*?\]);", html, re.DOTALL)
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

    # 2. seuls les fichiers attendus bougent
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

    # 2 bis. candidats : leurs descriptions repassent leur propre garde-fou
    if any(f in FICHIERS_CANDIDATS for f in modifies):
        r = subprocess.run([sys.executable, str(SCRIPTS_CANDIDATS / "check_descriptions.py"), "--state"],
                           capture_output=True, text=True, env={**os.environ, "SARECRUTE_SITE": str(SITE)})
        print(r.stdout.rstrip())
        if r.returncode:
            print("⛔ Contrôle des descriptions de candidats bloquant : rien n'est publié.")
            (WORK / "publication.json").write_text(json.dumps(
                {"statut": "bloqué (candidats)", "detail": r.stdout}, ensure_ascii=False, indent=1))
            return 2

    if args.dry_run:
        print(git("diff", "--stat").stdout.rstrip())
        print("\n--dry-run : ni commit ni push.")
        return 0

    # 3. commit + push — message fixe : aucun nom de clinique ne doit entrer dans l'historique.
    #    Auteur = l'identité git de la session cloud (le compte GitHub d'Alex) : le proxy de push
    #    refuse vers une branche non « claude/ » un commit signé d'un autre auteur que le titulaire.
    git("add", *[f for f in FICHIERS_PUBLIES if f in modifies])
    git("commit", "-q", "-m", f"Mise à jour des offres et des candidats — {heure_paris():%Y-%m-%d %H:%M} (routine)")
    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    p = git("push", "-q", "origin", "HEAD:main", check=False)
    if p.returncode:
        print(f"⛔ push refusé :\n{p.stderr.strip()}")
        (WORK / "publication.json").write_text(json.dumps(
            {"statut": "commit local, push refusé", "commit": sha, "detail": p.stderr},
            ensure_ascii=False, indent=1))
        return 3
    print(f"✔ Poussé : {sha}")

    # 4. attendre la version servie (offres, et candidats si leur page existe)
    attendus = [(SITE_URL, bloc_offres, bloc_offres((SITE / "offres.html").read_text(encoding="utf-8")))]
    if (SITE / "candidats.html").exists():
        attendus.append((SITE_URL_CANDIDATS, bloc_candidats,
                         bloc_candidats((SITE / "candidats.html").read_text(encoding="utf-8"))))
    en_ligne, debut, servis = False, time.time(), set()
    while time.time() - debut < args.attendre:
        for url, bloc, attendu in attendus:
            if url in servis:
                continue
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    if bloc(resp.read().decode("utf-8", "replace")) == attendu:
                        servis.add(url)
            except (urllib.error.URLError, TimeoutError) as e:
                print(f"   ({url} injoignable : {e})")
        if len(servis) == len(attendus):
            en_ligne = True
            break
        time.sleep(15)
    print("✔ En ligne : sarecrute.com sert les nouvelles offres et les nouveaux candidats." if en_ligne
          else f"⚠ Mise en ligne non confirmée après {args.attendre} s (le build Pages traîne ?).")

    (WORK / "publication.json").write_text(json.dumps({
        "statut": "publié", "commit": sha, "fichiers": modifies,
        "heure": heure_paris().strftime("%d/%m/%Y %H:%M"),
        "en_ligne_confirme": en_ligne,
    }, ensure_ascii=False, indent=1))
    return 0


# ---------------------------------------------------------------- recap

def fiche_recruteuse(prenom):
    """Fiche Recruteurs de la première recruteuse active dont le nom commence par `prenom`."""
    from fetch_offres import fetch_table  # lit AIRTABLE_API_KEY à l'import
    for r in fetch_table(T_RECRUTEURS, [F_REC_NOM, F_REC_EMAIL, F_REC_ACTIF, F_REC_TELEGRAM]):
        f = r.get("fields", {})
        if f.get(F_REC_ACTIF) and str(f.get(F_REC_NOM, "")).strip().lower().startswith(prenom.lower()):
            return {k: (str(f[k]).strip() if f.get(k) else "") for k in (F_REC_NOM, F_REC_EMAIL, F_REC_TELEGRAM)}
    raise SystemExit(f"Aucune recruteuse active « {prenom}… » dans Recruteurs.")


def destinataire(prenom):
    f = fiche_recruteuse(prenom)
    if not f[F_REC_EMAIL]:
        raise SystemExit(f"Pas d'« Email compte Claude » sur la fiche de {f[F_REC_NOM]}.")
    return f[F_REC_NOM], f[F_REC_EMAIL]


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
    if pub.get("statut") == "publié":
        L.append("Mise en ligne vérifiée sur sarecrute.com." if pub.get("en_ligne_confirme")
                 else "Publication poussée, mise en ligne pas encore confirmée au moment de l'envoi "
                      "(le site se met à jour en quelques minutes).")
    else:
        L.append(f"Attention : statut de publication « {pub.get('statut')} ».")

    L += ["", "— Offres —"]
    L += ["", f"Offres dépubliées ({len(retraits)})" if retraits else "Offres dépubliées : aucune"]
    for o in retraits:
        L.append(f"  - {libelle(o)} — {o.get('raison', '')}")

    L += ["", f"Offres publiées ({len(ajouts)})" if ajouts else "Offres publiées : aucune"]
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

    nc = recap_candidats(L)
    L += ["", "Les noms de cliniques et de candidats ci-dessus sont pour toi : sur le site, seuls le "
              "département apparaît, sans nom ni référence.",
          "", "— Routine SaRecrute (automatique, tous les jours à 2h ; questions et corrections : Alex)"]

    n = len(ajouts) + len(retraits)
    morceaux = []
    if n:
        morceaux.append(f"{len(ajouts)} offre(s) publiée(s), {len(retraits)} dépubliée(s)")
    if nc["ajouts"] or nc["retraits"]:
        morceaux.append(f"{nc['ajouts']} candidat(s) publié(s), {nc['retraits']} retiré(s)")
    sujet = f"Site SaRecrute — {' ; '.join(morceaux) if morceaux else 'fiches mises à jour'} — {date}"
    recap = {"destinataire": email, "nom": nom, "copie": COPIE, "sujet": sujet,
             "corps": "\n".join(l for l in L if l is not None),
             "changements": n + len(revues) + nc["total"]}
    (WORK / "recap.json").write_text(json.dumps(recap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {WORK}/recap.json — pour {nom} <{email}>, copie : {COPIE}\n")
    print(f"Sujet : {sujet}\n\n{recap['corps']}")
    return 0


def recap_candidats(L):
    """Ajoute à L la partie candidats du compte rendu (noms internes, comme pour les cliniques)."""
    diff = lire(WORK_CANDIDATS / "diff.json", None)
    app = lire(WORK_CANDIDATS / "apply.json", None)
    if diff is None or app is None:
        L += ["", "Candidats : la mise à jour n'a pas tourné cette nuit."]
        return {"ajouts": 0, "retraits": 0, "total": 0}
    etat = lire(STATE_CANDIDATS, {"candidats": {}})["candidats"]
    noms = {x["ref"]: x for x in lire(WORK_CANDIDATS / "candidats.json", [])}
    noms.update({x["ref"]: {**noms.get(x["ref"], {}), **x}
                 for x in diff.get("ajouts", []) + diff.get("retraits", []) + diff.get("revues", [])})
    def qui(ref):
        x = noms.get(ref, {})
        return f"{x.get('_nom') or '(nom inconnu)'}" + (f" — {x['titre']}" if x.get("titre") else "")
    publies, retires, attente = app.get("publies_ce_soir", []), app.get("retires", []), app.get("en_attente", [])
    prudence = app.get("retires_par_prudence", [])
    changees = app.get("descriptions_changees", [])
    L += ["", "— Candidats —"]
    L += ["", f"Candidats publiés ({len(publies)})" if publies else "Candidats publiés : aucun"]
    for ref in publies:
        L.append(f"  - {qui(ref)}")
        L.append(f"      Description : {etat.get(ref, {}).get('description', '')}")
    motifs = {x["ref"]: x.get("motif", "") for x in diff.get("retraits", [])}
    L += ["", f"Candidats retirés ({len(retires)})" if retires else "Candidats retirés : aucun"]
    for ref in retires:
        L.append(f"  - {qui(ref)} — {motifs.get(ref, '')}")
    if prudence:
        L += ["", f"Retirés par prudence ({len(prudence)}) — la relecture de cette nuit a eu un doute ; "
                  "à regarder (le candidat repassera en relecture la nuit prochaine)"]
        for ref in prudence:
            L.append(f"  - {qui(ref)}")
    if attente:
        L += ["", f"En attente ({len(attente)}) — description pas encore validée, rien n'est en ligne"]
        for ref in attente:
            L.append(f"  - {qui(ref)}")
    if changees:
        L += ["", f"Descriptions de candidats revues ({len(changees)})"]
        for ref in changees:
            L.append(f"  - {qui(ref)}")
            L.append(f"      Après : {etat.get(ref, {}).get('description', '')}")
    L += ["", f"Candidats en ligne : {app.get('en_ligne')}"]
    return {"ajouts": len(publies), "retraits": len(retires) + len(prudence),
            "total": len(publies) + len(retires) + len(prudence) + len(attente) + len(changees)}


# ---------------------------------------------------------------- telegram

def tg(token, method, **params):
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(TELEGRAM_API.format(token=token, method=method), data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"ok": False, "description": f"HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}"}
    except urllib.error.URLError as e:
        return {"ok": False, "description": f"réseau : {e}"}


def tg_envoyer(token, chat_id, texte):
    """Envoie en texte brut, découpé sous la limite Telegram (4096 caractères)."""
    morceaux, courant = [], ""
    for ligne in texte.split("\n"):
        if len(courant) + len(ligne) + 1 > 3900:
            morceaux.append(courant); courant = ""
        courant += ("\n" if courant else "") + ligne
    morceaux.append(courant)
    for m in morceaux:
        r = tg(token, "sendMessage", chat_id=chat_id, text=m, disable_web_page_preview=True)
        if not r.get("ok"):
            return r.get("description", "refus inconnu")
    return None


def cmd_telegram(args):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN absent : rien n'est envoyé.")
        return 1

    if args.decouvrir:
        r = tg(token, "getUpdates")
        if not r.get("ok"):
            print(f"⛔ Telegram : {r.get('description')}")
            return 4
        vus = {}
        for u in r.get("result", []):
            m = u.get("message") or {}
            chat, de = m.get("chat", {}), m.get("from", {})
            if chat.get("id"):
                vus[chat["id"]] = (f'{de.get("first_name", "")} {de.get("last_name", "")} '
                                   f'@{de.get("username", "")}  ({chat.get("type")})')
        if not vus:
            print("Aucun message reçu par le bot : chaque destinataire doit d'abord lui écrire (bouton Démarrer).")
        for cid, qui in vus.items():
            print(f"{cid}\t{qui}")
        return 0

    alex = os.environ.get("TELEGRAM_CHAT_ALEX", "").strip()
    if args.echec:
        if not alex:
            print("TELEGRAM_CHAT_ALEX absent : incident non envoyé.")
            return 1
        err = tg_envoyer(token, alex, f"ÉCHEC routine maj-offres-site — {heure_paris():%d/%m/%Y %H:%M}\n\n{args.echec}")
        print("✔ Incident envoyé à Alex." if not err else f"⛔ Telegram : {err}")
        return 0 if not err else 4

    recap = lire(WORK / "recap.json", None)
    if recap is None:
        print("work/recap.json absent — lance d'abord `recap`.")
        return 1
    if not recap.get("changements"):
        # publication sans changement notable (une disponibilité passée à « Dès maintenant »…) :
        # pas de message, Sarah n'a rien à regarder
        print("Rien de notable à signaler : aucun message envoyé.")
        return 0
    fiche = fiche_recruteuse(args.destinataire)
    cibles = []
    if fiche[F_REC_TELEGRAM]:
        cibles.append((fiche[F_REC_NOM], fiche[F_REC_TELEGRAM]))
    else:
        print(f"⚠ Pas de « Telegram chat ID » sur la fiche de {fiche[F_REC_NOM]} : elle ne recevra rien.")
    if alex:
        cibles.append(("Alex", alex))
    else:
        print("⚠ TELEGRAM_CHAT_ALEX absent : Alex ne recevra rien.")
    if not cibles:
        return 1

    texte = f"{recap['sujet']}\n\n{recap['corps']}"
    code = 0
    for nom, cid in cibles:
        err = tg_envoyer(token, cid, texte)
        print(f"✔ Envoyé à {nom}." if not err else f"⛔ {nom} : {err}")
        code = code or (4 if err else 0)
    return code


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
    t = sub.add_parser("telegram")
    t.add_argument("--destinataire", default="Sarah", help="prénom dans la table Recruteurs")
    t.add_argument("--echec", metavar="TEXTE", help="envoyer un compte rendu d'incident à Alex seul")
    t.add_argument("--decouvrir", action="store_true", help="lister les chat ID vus par le bot")
    t.set_defaults(fn=cmd_telegram)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
