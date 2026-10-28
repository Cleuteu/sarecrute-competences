#!/usr/bin/env python3
"""Dossier de présentation candidat (CV IA) — outillage de la routine cloud `routines/cv-candidat.md`.

Héritier de la compétence `creer-cv-candidat` de Léo (0.5.0, retirée du plugin le 15/10/2026 : le
dossier ne se génère plus que par le bouton de la fiche). Template et notes de maintenance dans
`routines/references/cv-candidat/`. Lecture et écriture par l'API REST d'Airtable (clé
AIRTABLE_API_KEY de l'environnement), rendu PDF par Chromium dans le conteneur. Le modèle n'écrit que
le titre du dossier anonymisé, et relit le parcours ; tout le reste est déterministe. L'accroche
(« Accroche CV ») et les descriptions du parcours sont écrites par la routine d'enrichissement et
recopiées telles quelles (28/10/2026) : ni notes, ni transcripts, ni CV, ni Profil IA ne sont lus.

Chaque run produit DEUX dossiers (depuis le 28/10/2026) : le nominatif dans « CV IA », l'anonymisé
dans « CV IA anonyme » (aucun nom, aucune coordonnée, aucun employeur), sous la même référence.

Sous-commandes, dans l'ordre d'un run :

  preparer [--dossier DIR] [--installer]
      Trouve un moteur de rendu : Playwright (node) déjà installé, sinon l'installe sous DIR/pw si
      --installer, sinon un binaire Chrome/Chromium du PATH. Écrit DIR/moteur.json.
  fetch recXXXXXXXXXXXXXX [--dossier DIR]
      Lit la fiche (seulement les champs du dossier), ses Compétences et ses Expériences ; écrit
      DIR/candidat.json (le bloc de données du template, titre vide) et DIR/etat.json (ce que la note
      finale doit dire, et les termes interdits du dossier anonymisé). Lecture seule.
  render [--dossier DIR] [--template FICHIER] [--anonyme]
      Insère DIR/candidat.json (ou candidat-anonyme.json) dans le template, rend le HTML, le PDF et
      un aperçu PNG, contrôle le PDF (pages, format A4, taille) et, en anonymisé, l'absence de tout
      terme interdit ; écrit DIR/rapport.json (ou rapport-anonyme.json). Code 2 si un contrôle échoue.
  anonymiser [--dossier DIR]
      Dérive DIR/candidat-anonyme.json de candidat.json (après le titre) : prénom, nom, contact et
      structures vidés, structures entre parenthèses retirées des descriptions. Liste ce qui reste
      d'un terme interdit (nom, prénom, coordonnée, structure) : c'est au modèle de l'ôter.
  upload recXXXXXXXXXXXXXX [--dossier DIR] [--note-plus TEXTE] [--dry-run]
      Dépose les deux PDF (API uploadAttachment) dans « CV IA » et « CV IA anonyme », remplace dans
      chacun l'ancien dossier SaRecrute (les autres pièces jointes sont gardées), écrit Statut =
      Généré, Généré le, Note. Un dossier anonymisé absent ou en échec n'empêche pas le dépôt du
      nominatif : la note le dit.
  erreur recXXXXXXXXXXXXXX --note TEXTE
      Statut = Erreur et la note. Seule écriture d'un run qui échoue.

Règles reprises de la compétence : chaque valeur du dossier est la recopie d'un champ Airtable ; ni
le CV joint, ni « Profil IA » ne sont lus ; un champ vide fait disparaître sa ligne ; pas de
localisation ; Internat / DESV / Habilitation ne s'affichent que positifs ; Statut Recherche et
En poste ? ne figurent pas ; la mobilité ne se renseigne pas.
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "appP0W2ISytaNyAhG"
T_CANDIDATS = "tblPmkTaAjS9Yoovt"
T_COMPETENCES = "tblH8Zym1DNu7PN3c"
T_EXPERIENCES = "tblTYdApkiHqKeBVi"
T_ACTES = "tblt32Afmq6vQ6FJS"

# --- Candidats : identifiants de champ (lecture par ID : les noms peuvent changer, pas les IDs)
F = {
    "prenom": "fld1WR6pNpe8sAya6", "nom": "fld6yzzWrqBZBtXly",
    "mail": "fldmtHKu93RMqkVw6", "telephone": "fldZ9229oPu876Ls2",
    "annees_exp": "fldSGOptEz0Api4wN", "dispo": "fldlCCJY7quJEqbyv",
    "contrats": "fldZaUsTcNsN7HlWe", "temps": "fldGZhonpYwDW78ze",
    "gardes": "fldI1xWGed3dcQIUs", "gardes_freq": "fldZ3kGzgXLhj5UJv",
    "remuneration": "fldZZj7aCQpzQKgZx",
    "pratiques_m": "fldsUtHmyFAFyjFgl", "specialites_m": "flde9dmHJUqdMZIOL",
    "pratiques_r": "fldKxF494zI5Kgc6n", "specialites_r": "fldYpaOYuUBHpqlqU",
    "ecole": "fldEUkJLo4ygiEZHZ", "annee_sortie": "fldp6whT8yfZdETi4",
    "internat": "fld3eO9JuwrHyNkIJ", "desv": "fldnvfN95E23ng7ep",
    "diplome_sup": "fldmi2DQKpPmcpXEV", "habilitation": "fldSIVZ8UxggjhffA",
    "langues": "fld48WU9SCR9DkVN6", "emploi": "fldizV1UoejwizYSq",
    # Écrite par l'enrichissement depuis les entretiens (28/10/2026) : le script ne lit ni Profil, ni
    # Notes, ni Notes du candidat, ni Transcripts, ni Profil IA — ces champs ne figurent pas ici.
    "accroche_cv": "fld2iZ18Ayjx3m1Pi",
    "cv_ia": "fldDfGvVlyid0xacE", "cv_ia_anonyme": "fld457VMpd1CHCAxY", "competences": "fldjLpY32oHfdOW0Z",
    "experiences": "fldVb4FwwyjB4reVg",
    "cv_statut": "fldQ9g5Mlxauvo98o", "cv_note": "fldn0zi6Mh8kW77dE", "cv_genere_le": "fldJiqeHBG46k0dBU",
}
# Libellés Airtable des champs dont le vide se signale à la recruteuse (note finale)
LIBELLES = {
    "accroche_cv": "Accroche CV", "mail": "Mail", "telephone": "Téléphone", "annees_exp": "Années d'expérience",
    "dispo": "Date de disponibilité", "contrats": "Statuts contractuels souhaités",
    "temps": "Type de temps de travail", "gardes": "Gardes", "remuneration": "Rémunération souhaitée",
    "pratiques_m": "Pratiques maitrisées", "pratiques_r": "Pratiques requises",
    "ecole": "Ecole véto", "annee_sortie": "Année de sortie", "langues": "Langues",
}
# Compétences
FC = {"acte": "fldUZQyIvlhNeZhzG", "niveau": "fld0SGFcuffxHSSq0"}
# Actes (référentiel)
FA = {"acte": "fldRieAkhj53QUXn7", "espece": "fldDB95GQHVopEXB0", "famille": "fldjYKdy0nenTcZwQ"}
# Expériences
FE = {
    "poste": "fldKL9vuSGhrwgV4c", "type": "fldp0espnc2GHvnHZ", "structure": "fldZsxMqiU6OuTCBH",
    "periode": "fldblqIgDkZX08ScY", "duree": "flduZveIw1rViotNt", "description": "fldf4RmAB4BbabJgI",
    "debut": "fldBtAlHlNFY7mREM", "fin": "fldrIXOtFY4cBEufk", "en_cours": "fldXic8NllpuNPVfk",
}
TYPES_CLINIQUE = {"Salarié", "Remplacement", "Collaborateur libéral", "Libéral installé / Associé",
                  "Internat", "Résidanat / Assistanat"}
SOURCE_EN_FIN = re.compile(r"\s*\((?=[^()]*(?:\bCV\b|compl[ée]ment|TemaVet|entretien|transcript|post|annuaire|LinkedIn))[^()]*\)\s*$", re.I)
NOM_DOSSIER_SARECRUTE = re.compile(r"^CV-.*-SaRecrute.*\.pdf$", re.I)
# Noms des champs pièce jointe, au cas où la réponse d'uploadAttachment serait rendue par nom
NOMS_PIECES = {F["cv_ia"]: "CV IA", F["cv_ia_anonyme"]: "CV IA anonyme"}
TAILLE_MAX = 5 * 1024 * 1024

HERE = Path(__file__).resolve().parent
TEMPLATE_DEFAUT = HERE.parent / "references" / "cv-candidat" / "cv-template.html"
PW_VERSION = "1.49.1"


# ----------------------------------------------------------------------------- utilitaires
def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def cle():
    k = os.environ.get("AIRTABLE_API_KEY") or os.environ.get("AIRTABLE_API_KEY_CV_AI")
    if not k:
        die("AIRTABLE_API_KEY absente de l'environnement : rien n'est lu ni écrit. Arrêt.")
    return k


def api(method, path, params=None, body=None, host="api.airtable.com"):
    url = f"https://{host}/v0/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {cle()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        die(f"Airtable {method} {path} → HTTP {e.code} : {e.read().decode(errors='replace')[:600]}")
    except urllib.error.URLError as e:
        die(f"Airtable {method} {host} injoignable : {e.reason}. Dans le conteneur des routines, c'est le proxy "
            f"de sortie qui refuse l'hôte : ajouter « {host} » aux domaines autorisés de l'environnement cloud.")


def lire_par_ids(table, ids, champs):
    """Lit des records par paquets (OR(RECORD_ID()=…)), champs par ID."""
    out = []
    for i in range(0, len(ids), 20):
        lot = ids[i:i + 20]
        formule = "OR(" + ",".join(f"RECORD_ID()='{r}'" for r in lot) + ")"
        params = [("returnFieldsByFieldId", "true"), ("filterByFormula", formule), ("pageSize", "100")]
        params += [("fields[]", f) for f in champs]
        out += api("GET", f"{BASE}/{table}", params).get("records", [])
    return out


def lire_table(table, champs):
    out, offset = [], None
    while True:
        params = [("returnFieldsByFieldId", "true"), ("pageSize", "100")] + [("fields[]", f) for f in champs]
        if offset:
            params.append(("offset", offset))
        r = api("GET", f"{BASE}/{table}", params)
        out += r.get("records", [])
        offset = r.get("offset")
        if not offset:
            return out


def sel(v):
    """Valeur affichable d'un select / multiselect / texte, telle qu'Airtable la rend par l'API."""
    if v is None:
        return ""
    if isinstance(v, list):
        return [sel(x) for x in v if sel(x)]
    if isinstance(v, dict):
        return v.get("name", "")
    return str(v).strip()


def ascii_slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s or "X"


MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
           "octobre", "novembre", "décembre"]


def date_fr(iso):
    """« 15 janvier 2027 » — la forme des dossiers déjà livrés."""
    try:
        d = dt.date.fromisoformat(iso[:10])
        return f"{d.day}{'er' if d.day == 1 else ''} {MOIS_FR[d.month - 1]} {d.year}"
    except Exception:
        return iso or ""


def nom_affiche(nom):
    """Sans la précision entre parenthèses d'un nom d'usage (« Lecarpentier (Caparroy) ») : c'est une
    information interne, pas une ligne de dossier client."""
    return (re.sub(r"\s*\([^)]*\)", "", nom or "").strip() or (nom or "")).strip()


def liste_fr(items):
    """« Temps plein, temps partiel » : seule la première valeur garde sa majuscule, sauf un sigle."""
    out = []
    for i, x in enumerate(items or []):
        x = str(x).strip()
        if i and x and not x.isupper() and not x[:2].isupper():
            x = x[0].lower() + x[1:]
        out.append(x)
    return ", ".join(x for x in out if x)


def annees(n):
    if n is None or n == "":
        return ""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if n <= 0:
        return ""
    return "1 an" if n == 1 else f"{n} ans"


def charger(dossier, nom):
    p = Path(dossier) / nom
    if not p.exists():
        die(f"{p} introuvable : lancer d'abord l'étape précédente.")
    return json.loads(p.read_text(encoding="utf-8"))


def ecrire(dossier, nom, obj):
    p = Path(dossier) / nom
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


# ----------------------------------------------------------------------------- preparer
def trouver_chrome():
    """Un binaire Chrome/Chromium : variable CV_CHROME, PATH, le Chromium préinstallé des conteneurs
    de routines (/opt/pw-browsers, constaté le 15/10/2026), ou Chrome sur un Mac."""
    if os.environ.get("CV_CHROME") and os.path.exists(os.environ["CV_CHROME"]):
        return os.environ["CV_CHROME"]
    for c in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        p = shutil.which(c)
        if p:
            return p
    bases = [Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")), Path("/opt/pw-browsers"),
             Path.home() / ".cache" / "ms-playwright"]
    for b in bases:
        if not str(b) or not b.exists():
            continue
        lien = b / "chromium"
        if lien.exists():
            return str(lien)
        for d in sorted(b.glob("chromium-*"), reverse=True):
            exe = d / "chrome-linux" / "chrome"
            if exe.exists():
                return str(exe)
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(mac):
        return mac
    return None


def playwright_ok(module):
    try:
        r = subprocess.run(["node", "-e", f"require({json.dumps(module)});console.log('ok')"],
                           capture_output=True, text=True, timeout=60)
        return r.returncode == 0 and "ok" in r.stdout
    except Exception:
        return False


def chromium_pw_present():
    for base in (Path.home() / ".cache" / "ms-playwright", Path("/root/.cache/ms-playwright")):
        if base.exists() and any(d.name.startswith("chromium") for d in base.iterdir()):
            return True
    return False


def cmd_preparer(a):
    """Moteur de rendu, par ordre de préférence :
    1. Playwright (node) sur un Chromium — celui qu'on trouve sur la machine (CV_CHROME, PATH,
       /opt/pw-browsers du conteneur, Chrome du Mac) ou celui que Playwright a lui-même installé.
       Le module npm s'installe à la demande (--installer) : le registre npm est joignable depuis le
       conteneur, les téléchargements de navigateur ne le sont pas (proxy, 15/10/2026), d'où le
       binaire explicite. Avantage : on lit l'état de la page (échelle, débordement) avant d'imprimer.
    2. Le binaire Chrome/Chromium seul, en `--print-to-pdf` : pas de mesure, mais un PDF."""
    dossier = Path(a.dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chrome = trouver_chrome()
    moteur = None
    if shutil.which("node"):
        pw_dir = dossier / "pw"
        module_local = str(pw_dir / "node_modules" / "playwright")
        env = dict(os.environ, PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD="1")
        candidats = [module_local, "playwright"]
        if not any(playwright_ok(m) for m in candidats) and a.installer:
            pw_dir.mkdir(parents=True, exist_ok=True)
            print(f"installation du module npm playwright sous {pw_dir} …")
            r = subprocess.run(["npm", "i", "--silent", "--no-audit", "--no-fund", "--prefix", str(pw_dir), "playwright"],
                               capture_output=True, text=True, timeout=600, env=env)
            print((r.stdout + r.stderr).strip()[-600:])
            if not chrome:
                cli = pw_dir / "node_modules" / "playwright" / "cli.js"
                if cli.exists():
                    r = subprocess.run(["node", str(cli), "install", "chromium"], capture_output=True, text=True,
                                       timeout=900, env=dict(os.environ))
                    print((r.stdout + r.stderr).strip()[-600:])
        for module in candidats:
            if playwright_ok(module) and (chrome or chromium_pw_present()):
                moteur = {"mode": "playwright", "pw_module": module, "chrome": chrome or ""}
                break
    if not moteur and chrome:
        moteur = {"mode": "chrome", "bin": chrome}
    if not moteur:
        die("Aucun moteur de rendu : ni Playwright (node) ni binaire Chrome/Chromium. "
            "Relancer avec --installer, ou installer Chromium dans l'environnement.", 3)
    ecrire(dossier, "moteur.json", moteur)
    print("moteur :", json.dumps(moteur, ensure_ascii=False))


# ----------------------------------------------------------------------------- fetch
def nettoyer_description(d):
    d = (d or "").strip()
    return SOURCE_EN_FIN.sub("", d).strip()


def annee(iso):
    return iso[:4] if iso else ""


def construire_experiences(records):
    """Propose le parcours du dossier : postes en clinique un par ligne (du plus récent au plus
    ancien), stages / jobs / hors clinique regroupés sur une ligne finale. Le modèle peut resserrer
    (remplacements courts d'une même période), jamais rallonger."""
    lignes, autres, brutes = [], [], []
    for r in records:
        f = r.get("fields", {})
        e = {
            "id": r["id"], "poste": sel(f.get(FE["poste"])), "type": sel(f.get(FE["type"])),
            "structure": sel(f.get(FE["structure"])), "periode": sel(f.get(FE["periode"])),
            "duree": sel(f.get(FE["duree"])), "description": nettoyer_description(f.get(FE["description"])),
            "debut": f.get(FE["debut"]) or "", "fin": f.get(FE["fin"]) or "", "en_cours": bool(f.get(FE["en_cours"])),
        }
        brutes.append(e)
    brutes.sort(key=lambda e: (e["en_cours"], e["debut"], e["fin"]), reverse=True)
    for e in brutes:
        if e["type"] in TYPES_CLINIQUE or (not e["type"] and e["poste"]):
            lignes.append({"poste": e["poste"], "structure": e["structure"], "periode": e["periode"],
                           "duree": e["duree"], "description": e["description"]})
        else:
            autres.append(e)
    if autres:
        # Une ligne finale, dans la forme des dossiers déjà livrés : intitulé « Stages et postes
        # courts », la période couverte et le nombre de postes à droite, la liste « intitulé
        # (structure) » en description. Ni durée individuelle ni durée cumulée.
        items = []
        for e in sorted(autres, key=lambda e: e["debut"]):
            lib = e["poste"] or e["type"] or "Stage"
            if e["structure"]:
                lib += f" ({e['structure']})"
            if lib not in items:
                items.append(lib)
        debuts = [e["debut"] for e in autres if e["debut"]]
        fins = [e["fin"] for e in autres if e["fin"]] + [dt.date.today().isoformat() for e in autres if e["en_cours"]]
        periode = ""
        if debuts:
            a1, a2 = annee(min(debuts)), annee(max(fins)) if fins else ""
            periode = a1 if not a2 or a2 == a1 else f"{a1} – {a2}"
        n = len(autres)
        lignes.append({
            "poste": "Stages et postes courts" if n > 1 else (autres[0]["poste"] or "Stage"),
            "structure": "" if n > 1 else autres[0]["structure"],
            "periode": periode, "duree": f"{n} postes" if n > 1 else "",
            "description": " · ".join(items) if n > 1 else "",
        })
    return lignes, brutes


def cmd_fetch(a):
    rec = a.record
    # Les seuls champs du dictionnaire F : les notes, les transcripts, le CV et le Profil IA ne
    # transitent même pas par le script.
    lus = lire_par_ids(T_CANDIDATS, [rec], list(F.values()))
    if not lus:
        die(f"{rec} : fiche candidat introuvable.")
    f = lus[0].get("fields", {})
    prenom, nom_complet = sel(f.get(F["prenom"])), sel(f.get(F["nom"]))
    nom = nom_affiche(nom_complet)
    if not (prenom or nom):
        die(f"{rec} : ni prénom ni nom — fiche anonyme, pas de dossier.")

    # Actes : référentiel complet (une lecture, ~55 lignes)
    actes = {x["id"]: x.get("fields", {}) for x in lire_table(T_ACTES, [FA["acte"], FA["espece"], FA["famille"]])}
    competences = []
    for c in lire_par_ids(T_COMPETENCES, f.get(F["competences"]) or [], [FC["acte"], FC["niveau"]]):
        cf = c.get("fields", {})
        niveau = sel(cf.get(FC["niveau"]))
        for acte_id in cf.get(FC["acte"]) or []:
            ac = actes.get(acte_id, {})
            competences.append({"espece": sel(ac.get(FA["espece"])), "famille": sel(ac.get(FA["famille"])),
                                "acte": sel(ac.get(FA["acte"])), "niveau": niveau})
    competences = [c for c in competences if c["acte"] and c["niveau"]]

    exp_records = lire_par_ids(T_EXPERIENCES, f.get(F["experiences"]) or [], list(FE.values()))
    experiences, brutes = construire_experiences(exp_records)

    n_exp = f.get(F["annees_exp"])
    emploi = sel(f.get(F["emploi"])) or "Vétérinaire"
    pratiques_r = sel(f.get(F["pratiques_r"])) or []
    sous_titre = " · ".join(x for x in [emploi, ", ".join(pratiques_r), (annees(n_exp) + " d'expérience") if annees(n_exp) else ""] if x)

    gardes = sel(f.get(F["gardes"]))
    freq = sel(f.get(F["gardes_freq"]))
    if gardes == "Oui" and freq:
        gardes = f"Oui · {freq}"
    oui = lambda v: "Oui" if sel(v) == "Oui" else ""
    # Même référence sur les deux dossiers, tirée du record et non des initiales (qui se liraient
    # sur le dossier anonymisé), stable d'une génération à l'autre.
    reference = f"SR-{rec[-5:].upper()}"
    candidat = {
        "reference": reference,
        "prenom": prenom, "nom": nom, "sousTitre": sous_titre,
        "titre": "",
        "accroche": sel(f.get(F["accroche_cv"])),
        "contact": {"email": sel(f.get(F["mail"])), "telephone": sel(f.get(F["telephone"]))},
        "cadre": {
            "experience": annees(n_exp),
            "disponibilite": date_fr(f.get(F["dispo"]) or ""),
            "contrat": liste_fr(sel(f.get(F["contrats"]))),
            "tempsTravail": liste_fr(sel(f.get(F["temps"]))),
            "gardes": gardes,
            "remuneration": sel(f.get(F["remuneration"])),
            "mobilite": "",
        },
        "pratiques": sel(f.get(F["pratiques_m"])) or [],
        "specialites": sel(f.get(F["specialites_m"])) or [],
        "recherche": (pratiques_r + (sel(f.get(F["specialites_r"])) or [])),
        "formation": {
            "ecole": sel(f.get(F["ecole"])), "anneeSortie": sel(f.get(F["annee_sortie"])),
            "internat": oui(f.get(F["internat"])), "desv": "Oui" if f.get(F["desv"]) else "",
            "diplomeSup": sel(f.get(F["diplome_sup"])), "habilitation": oui(f.get(F["habilitation"])),
        },
        "langues": sel(f.get(F["langues"])) or [],
        "experiences": experiences,
        "competences": competences,
    }
    vides = [LIBELLES[k] for k in LIBELLES if not sel(f.get(F[k]))]
    dispo = f.get(F["dispo"]) or ""
    cv_ia = [{"id": x.get("id"), "filename": x.get("filename")} for x in (f.get(F["cv_ia"]) or [])]
    # Ce qui ne doit apparaître nulle part dans le dossier anonymisé : prénom, chaque mot du nom (nom
    # d'usage entre parenthèses compris), coordonnées, et toute structure du parcours brut.
    candidats_interdits = [prenom, sel(f.get(F["mail"])), sel(f.get(F["telephone"]))]
    candidats_interdits += re.split(r"[\s()\-]+", nom_complet or "")
    candidats_interdits += [e["structure"] for e in brutes]
    interdits = []
    for t in candidats_interdits:
        t = (t or "").strip()
        if len(t) >= 3 and t.lower() not in {x.lower() for x in interdits}:
            interdits.append(t)
    etat = {
        "record_id": rec, "prenom": prenom, "nom": nom, "reference": reference,
        "statut_actuel": sel(f.get(F["cv_statut"])), "cv_ia_existants": cv_ia,
        "a_remplacer": [x["filename"] for x in cv_ia if x.get("filename") and NOM_DOSSIER_SARECRUTE.match(x["filename"])],
        "champs_vides": vides,
        "disponibilite_passee": bool(dispo and dispo[:10] < dt.date.today().isoformat()),
        "nb_competences": len(competences), "nb_competences_affichees": len([c for c in competences if c["niveau"] != "Non concerné"]),
        "nb_experiences_brutes": len(brutes), "nb_experiences_dossier": len(experiences),
        "experiences_brutes": brutes,
        "longueur_accroche": len(candidat["accroche"]),
        "nom_complet": nom_complet,
        "fichier_base": f"CV-{ascii_slug(prenom)}-{ascii_slug(nom)}-SaRecrute",
        # Le nom de fichier voyage avec la pièce jointe : jamais de nom de personne dedans.
        "fichier_base_anonyme": f"CV-anonyme-{reference}-SaRecrute",
        "interdits": interdits,
    }
    ecrire(a.dossier, "candidat.json", {"ANONYME": False, "CANDIDAT": candidat})
    ecrire(a.dossier, "etat.json", etat)
    print(json.dumps({k: etat[k] for k in ("record_id", "prenom", "nom", "reference", "statut_actuel",
                                           "cv_ia_existants", "champs_vides", "nb_competences",
                                           "nb_experiences_brutes", "nb_experiences_dossier", "longueur_accroche")},
                     ensure_ascii=False, indent=2))


# ----------------------------------------------------------------------------- anonymiser
def fuites(candidat, interdits):
    """Chaque terme interdit retrouvé dans une valeur du bloc, avec son emplacement. Comparaison sans
    casse, sur mot entier : « Paul » ne se lit pas dans « Pauline », mais bien dans « Saint-Paul »."""
    trouves = []

    def parcourir(v, chemin):
        if isinstance(v, dict):
            for k, x in v.items():
                if k != "reference":
                    parcourir(x, f"{chemin}.{k}" if chemin else k)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                parcourir(x, f"{chemin}[{i}]")
        elif isinstance(v, str) and v:
            for t in interdits:
                if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", v, re.I):
                    trouves.append({"terme": t, "champ": chemin})

    parcourir(candidat, "")
    return trouves


def cmd_anonymiser(a):
    dossier = Path(a.dossier)
    data = charger(dossier, "candidat.json")
    etat = charger(dossier, "etat.json")
    C = json.loads(json.dumps(data["CANDIDAT"]))
    C["prenom"], C["nom"] = "", ""
    C["contact"] = {"email": "", "telephone": ""}
    structures = sorted({e.get("structure", "") for e in C.get("experiences", [])} |
                        {t for t in etat.get("interdits", [])}, key=len, reverse=True)
    for e in C.get("experiences", []):
        e["structure"] = ""
        d = e.get("description", "")
        # La ligne « Stages et postes courts » est montée par le script en « intitulé (structure) » :
        # la parenthèse part avec la structure. Une structure citée hors parenthèses reste, et le
        # contrôle ci-dessous la signale au modèle.
        for s in structures:
            if s:
                d = re.sub(r"\s*\(\s*" + re.escape(s) + r"\s*\)", "", d, flags=re.I)
        # Sans leur structure, deux stages de même intitulé deviennent identiques : un seul suffit.
        items = []
        for x in d.split(" · "):
            if x.strip() and x.strip() not in items:
                items.append(x.strip())
        e["description"] = " · ".join(items)
    ecrire(dossier, "candidat-anonyme.json", {"ANONYME": True, "CANDIDAT": C})
    reste = fuites(C, etat.get("interdits", []))
    print(json.dumps({"ecrit": str(dossier / "candidat-anonyme.json"), "fuites": reste}, ensure_ascii=False, indent=2))


# ----------------------------------------------------------------------------- render
def js_bloc(data):
    """Le bloc entre /*DATA-START*/ et /*DATA-END*/ : du JSON est du JS valide."""
    cand = json.dumps(data["CANDIDAT"], ensure_ascii=False, indent=2)
    return f"\nconst ANONYME = {'true' if data.get('ANONYME') else 'false'};\n\nconst CANDIDAT = {cand};\n"


def verifier_pdf(p):
    b = Path(p).read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page(?![s/])", b))
    m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", b)
    box = [float(x) for x in m.groups()] if m else None
    a4 = bool(box) and abs(box[2] - box[0] - 595) < 2 and abs(box[3] - box[1] - 842) < 2
    return {"octets": len(b), "pages": pages, "mediabox": box, "a4": a4, "entete_pdf": b[:5] == b"%PDF-"}


def cmd_render(a):
    dossier = Path(a.dossier)
    data = charger(dossier, "candidat-anonyme.json" if a.anonyme else "candidat.json")
    etat = charger(dossier, "etat.json")
    moteur = charger(dossier, "moteur.json")
    tpl_path = Path(a.template)
    if not tpl_path.exists():
        die(f"template introuvable : {tpl_path}")
    tpl = tpl_path.read_text(encoding="utf-8")
    i, j = tpl.find("/*DATA-START*/"), tpl.find("/*DATA-END*/")
    if i < 0 or j < 0:
        die("marqueurs DATA-START / DATA-END absents du template")
    C = data["CANDIDAT"]
    problemes = []
    if C["cadre"].get("mobilite"):
        problemes.append("cadre.mobilite renseigné : interdit (décision du 27/08/2026)")
    for k in ("internat", "desv", "habilitation"):
        if C["formation"].get(k, "").strip().lower() == "non":
            problemes.append(f"formation.{k} = Non : ne s'affiche que positif")
    if a.anonyme:
        if not data.get("ANONYME"):
            problemes.append("candidat-anonyme.json sans ANONYME = true : relancer anonymiser")
        for x in fuites(C, etat.get("interdits", [])):
            problemes.append(f"dossier anonymisé : « {x['terme']} » dans {x['champ']}")
    html = tpl[: i + len("/*DATA-START*/")] + js_bloc(data) + tpl[j:]
    base = etat["fichier_base_anonyme" if a.anonyme else "fichier_base"]
    html_p, pdf_p = dossier / f"{base}.html", dossier / f"{base}.pdf"
    png_p = dossier / ("apercu-anonyme.png" if a.anonyme else "apercu.png")
    html_p.write_text(html, encoding="utf-8")
    for p in (pdf_p, png_p):
        if p.exists():
            p.unlink()

    page = {}
    if moteur["mode"] == "playwright":
        env = dict(os.environ, PW_MODULE=moteur["pw_module"], CV_CHROME=moteur.get("chrome") or "")
        r = subprocess.run(["node", str(HERE / "cv_pdf.js"), str(html_p), str(pdf_p), str(png_p)],
                           capture_output=True, text=True, timeout=300, env=env)
        try:
            page = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            page = {"erreur": (r.stdout + r.stderr).strip()[-800:]}
        if "erreur" in page:
            problemes.append("rendu Playwright : " + page["erreur"])
    else:
        prof = dossier / "prof-chrome"
        shutil.rmtree(prof, ignore_errors=True)
        communs = [moteur["bin"], "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={prof}",
                   "--hide-scrollbars", "--virtual-time-budget=15000"]
        subprocess.run(communs + ["--no-pdf-header-footer", f"--print-to-pdf={pdf_p}", html_p.as_uri()],
                       capture_output=True, text=True, timeout=300)
        subprocess.run(communs + ["--window-size=794,1123", f"--screenshot={png_p}", html_p.as_uri()],
                       capture_output=True, text=True, timeout=300)
        page = {"mode": "inconnu (chrome --print-to-pdf : pas de mesure en page)"}

    if not pdf_p.exists():
        problemes.append("PDF absent après le rendu")
        pdf = {}
    else:
        pdf = verifier_pdf(pdf_p)
        if not pdf["entete_pdf"]:
            problemes.append("fichier produit sans en-tête PDF")
        if pdf["pages"] != 1:
            problemes.append(f"{pdf['pages']} page(s) comptée(s), attendu 1")
        if not pdf["a4"]:
            problemes.append(f"MediaBox {pdf['mediabox']} : pas du A4 (595 × 842)")
        if pdf["octets"] > TAILLE_MAX:
            problemes.append(f"PDF de {pdf['octets']} octets : au-delà des 5 Mo d'Airtable")
        if pdf["octets"] < 20000:
            problemes.append(f"PDF de {pdf['octets']} octets : trop petit pour embarquer les polices, rendu suspect")
    if page.get("overflow"):
        problemes.append("la page déborde encore après ajustement (coupure basse probable)")
    if page.get("piedVisible") is False:
        problemes.append("pied de page hors de la page")
    if page.get("fonts") not in (None, "loaded") or page.get("inter") is False or page.get("fraunces") is False:
        problemes.append(f"polices : status={page.get('fonts')} inter={page.get('inter')} fraunces={page.get('fraunces')}")

    rapport = {"html": str(html_p), "pdf": str(pdf_p) if pdf_p.exists() else None,
               "apercu": str(png_p) if png_p.exists() else None, "moteur": moteur, "page": page, "pdf_controle": pdf,
               "problemes": problemes, "nb_competences": len(C.get("competences", [])),
               "nb_experiences": len(C.get("experiences", [])), "anonyme": bool(a.anonyme)}
    ecrire(dossier, "rapport-anonyme.json" if a.anonyme else "rapport.json", rapport)
    print(json.dumps(rapport, ensure_ascii=False, indent=2))
    if problemes:
        sys.exit(2)


# ----------------------------------------------------------------------------- upload / erreur
def note_automatique(etat, rapport, plus="", remplaces=(), anonyme_absent=""):
    lignes = []
    for ch in etat.get("champs_vides", []):
        if ch == "Accroche CV":
            lignes.append("Accroche CV : vide, dossier sans accroche (relancer l'enrichissement de la fiche)")
        else:
            lignes.append(f"{ch} : vide (ligne absente du dossier)")
    if etat.get("longueur_accroche", 0) > 520:
        lignes.append(f"Accroche CV longue ({etat['longueur_accroche']} caractères pour 420 visés) : à resserrer dans la fiche")
    if etat.get("disponibilite_passee"):
        lignes.append("Date de disponibilité dans le passé : à mettre à jour")
    if etat.get("nb_competences_affichees", 0) == 0:
        lignes.append("Aucune compétence cotée : le bilan est vide")
    if rapport.get("page", {}).get("mode") == "compact":
        lignes.append("Dossier dense : rendu en mode compact (familles d'actes non affichées)")
    if anonyme_absent:
        lignes.append("Dossier anonymisé non déposé : " + anonyme_absent)
    if remplaces:
        lignes.append("Ancien dossier remplacé : " + ", ".join(remplaces))
    if plus:
        lignes.append(plus.strip())
    if not lignes:
        lignes.append("Rien à signaler.")
    # La référence est ce qu'une clinique cite après avoir reçu le dossier anonymisé : dans la note,
    # la recherche d'Airtable retrouve la fiche.
    if etat.get("reference"):
        lignes.append(f"Référence des dossiers : {etat['reference']}")
    return "\n".join(lignes)


def deposer(record, champ, pdf_p, existants):
    """Dépose un PDF dans un champ pièce jointe et rend la valeur à réécrire : la nouvelle pièce plus
    les pièces étrangères au dossier (l'API ajoute, elle ne remplace pas)."""
    corps = {"contentType": "application/pdf", "filename": pdf_p.name,
             "file": base64.b64encode(pdf_p.read_bytes()).decode()}
    r = api("POST", f"{BASE}/{record}/{champ}/uploadAttachment", body=corps, host="content.airtable.com")
    apres = r.get("fields", {}).get(champ) or r.get("fields", {}).get(NOMS_PIECES.get(champ, "")) or []
    avant_ids = {x["id"] for x in existants}
    nouveaux = [x for x in apres if x["id"] not in avant_ids]
    if not nouveaux:
        die(f"dépôt de {pdf_p.name} accepté mais pièce jointe introuvable dans la réponse : vérifier la fiche "
            "à la main. " + json.dumps(r)[:400])
    gardes = [{"id": x["id"]} for x in existants if not NOM_DOSSIER_SARECRUTE.match(x.get("filename") or "")]
    return gardes + [{"id": nouveaux[-1]["id"]}]


def cmd_upload(a):
    dossier = Path(a.dossier)
    etat = charger(dossier, "etat.json")
    rapport = charger(dossier, "rapport.json")
    if etat["record_id"] != a.record:
        die(f"etat.json porte {etat['record_id']}, pas {a.record} : dossier de travail d'un autre candidat.")
    if rapport.get("problemes"):
        die("rapport.json liste des problèmes : pas de dépôt. " + " ; ".join(rapport["problemes"]), 2)
    pdf_p = Path(rapport["pdf"])
    if not pdf_p.exists():
        die(f"{pdf_p} introuvable")

    # Le dossier anonymisé ne part que s'il a passé tous ses contrôles, absence de fuite comprise.
    # Sinon le nominatif part seul et la note dit pourquoi.
    pdf_anon, anonyme_absent = None, ""
    p_anon = dossier / "rapport-anonyme.json"
    if not p_anon.exists():
        anonyme_absent = "non généré"
    else:
        r_anon = json.loads(p_anon.read_text(encoding="utf-8"))
        if r_anon.get("problemes"):
            anonyme_absent = " ; ".join(r_anon["problemes"])
        elif not (r_anon.get("pdf") and Path(r_anon["pdf"]).exists()):
            anonyme_absent = "PDF introuvable"
        else:
            pdf_anon = Path(r_anon["pdf"])

    # Relecture juste avant d'écrire : la fiche a pu bouger entre fetch et upload
    lus = lire_par_ids(T_CANDIDATS, [a.record], [F["cv_ia"], F["cv_ia_anonyme"]])
    if not lus:
        die(f"{a.record} : fiche candidat introuvable au moment du dépôt.")
    f = lus[0].get("fields", {})
    cibles = [(F["cv_ia"], pdf_p)] + ([(F["cv_ia_anonyme"], pdf_anon)] if pdf_anon else [])
    existants = {ch: f.get(ch) or [] for ch, _ in cibles}
    remplaces = [x.get("filename") for ch, _ in cibles for x in existants[ch]
                 if NOM_DOSSIER_SARECRUTE.match(x.get("filename") or "")]
    note = note_automatique(etat, rapport, a.note_plus, remplaces, anonyme_absent)
    if a.dry_run:
        print(json.dumps({"dry_run": True, "record": a.record,
                          "fichiers": [{"champ": ch, "fichier": p.name, "octets": p.stat().st_size,
                                        "garderait": len([x for x in existants[ch]
                                                          if not NOM_DOSSIER_SARECRUTE.match(x.get("filename") or "")])}
                                       for ch, p in cibles],
                          "remplacerait": remplaces, "note": note}, ensure_ascii=False, indent=2))
        return
    champs = {ch: deposer(a.record, ch, p, existants[ch]) for ch, p in cibles}
    champs.update({
        F["cv_statut"]: "Généré",
        F["cv_genere_le"]: dt.date.today().isoformat(),
        F["cv_note"]: note,
    })
    api("PATCH", f"{BASE}/{T_CANDIDATS}/{a.record}", body={"fields": champs})
    print(json.dumps({"deposes": [p.name for _, p in cibles], "remplaces": remplaces,
                      "note": note, "lien": f"https://airtable.com/{BASE}/{T_CANDIDATS}/{a.record}"},
                     ensure_ascii=False, indent=2))


def cmd_erreur(a):
    api("PATCH", f"{BASE}/{T_CANDIDATS}/{a.record}",
        body={"fields": {F["cv_statut"]: "Erreur", F["cv_note"]: a.note.strip()}})
    print(f"Statut Erreur écrit sur {a.record}.")


# ----------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("preparer"); s.add_argument("--dossier", default="work-cv"); s.add_argument("--installer", action="store_true")
    s.set_defaults(fn=cmd_preparer)
    s = sp.add_parser("fetch"); s.add_argument("record"); s.add_argument("--dossier", default="work-cv")
    s.set_defaults(fn=cmd_fetch)
    s = sp.add_parser("anonymiser"); s.add_argument("--dossier", default="work-cv")
    s.set_defaults(fn=cmd_anonymiser)
    s = sp.add_parser("render"); s.add_argument("--dossier", default="work-cv"); s.add_argument("--template", default=str(TEMPLATE_DEFAUT))
    s.add_argument("--anonyme", action="store_true")
    s.set_defaults(fn=cmd_render)
    s = sp.add_parser("upload"); s.add_argument("record"); s.add_argument("--dossier", default="work-cv")
    s.add_argument("--note-plus", default=""); s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_upload)
    s = sp.add_parser("erreur"); s.add_argument("record"); s.add_argument("--note", required=True)
    s.set_defaults(fn=cmd_erreur)
    a = p.parse_args()
    if a.cmd != "preparer" and not re.match(r"^rec[A-Za-z0-9]{14}$", getattr(a, "record", "rec00000000000000")):
        die(f"identifiant de record invalide : {a.record}")
    a.fn(a)


if __name__ == "__main__":
    main()
