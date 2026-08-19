#!/usr/bin/env python3
"""
Étape 1 de la mise à jour des offres du site SaRecrute.

Lit Airtable (base PROD), garde les offres publiables (clinique "Signé" + non
archivée), les compare à l'état précédent (.offres-state.json) et écrit dans
work/ :

  airtable.json  — toutes les offres cibles, champs normalisés + textes sources
  todo.json      — celles qui ont besoin d'une description (nouvelle ou source modifiée)
  diff.json      — résumé lisible : ajouts / retraits / descriptions à revoir

Aucune écriture dans Airtable, aucune écriture dans les fichiers du site.
"""
import json
import os
import re
import hashlib
import subprocess
import urllib.parse
import urllib.request

from paths import STATE, SKILL, WORK

BASE = "appP0W2ISytaNyAhG"           # Recrutement vétérinaire (PROD)
T_OFFRES = "tblVZva5yHSCnucsK"       # Offres d'emploi
T_CLINIQUES = "tblagWImxHH15rRAh"    # Cliniques

F = {
    "archivee":   "fldsyc8RzbIyiH4mZ",
    "statut_clin": "fldqkT8Ibecwoy9sZ",  # lookup "Status commercial (from Clinique)"
    "clinique":   "fldtUGOTlzMmBrrx9",   # lien vers Cliniques
    "nom_clin":   "fldl4VMacV8OsoHvF",   # formule "Nom de la clinique" (INTERNE, jamais publié)
    "cp":         "fldiG5KJU9HLjJ2Ty",   # lookup CP (from Clinique)
    "pratiques":  "fldgYo4mPQjxqPen4",   # Pratiques requises
    "spec_req":   "fldfxUJuNO2kkstGq",   # Spécialités requises (PAS les optionnelles)
    "contrat":    "fldDUXxile41HOLbD",   # Statuts contractuels
    "temps":      "fldv1Ajitw8BTejsd",   # Type de temps de travail
    "gardes":     "fldaeLw3kyhReMCCp",
    "remu":       "fldEa1Kc6pL40u8n2",
    "experience": "fldJiOMS63jUDSsz6",   # Expérience requise
    "demarrage":  "fldm2dcrjrYxG8E3v",   # Date de démarrage
    "annonce":    "fldideBaQV8ILp2zJ",   # Texte de publication (source primaire)
    "annonce_alt": "fldLIH3nwT4p9uhHC",  # Annonce — repli quand "Texte de publication" est vide
    "notes":      "fldxzx6oC1zsF3aug",   # Notes (offre)
}
F_CLIN = {
    "nom":   "fldHJd3Ts1vfLn4TQ",
    "ville": "fldf8t2ihJMGnh7wz",
    "pays":  "fld5COKjkzYSSKA98",
    "notes": "fldJIET4sokOxl5f7",        # Notes (clinique)
    "veto":  "fldLUWwSfCGb99kxc",        # Nom du vétérinaire
    "mail1": "fldIrQarKGnhq3g76",
    "mail2": "fldjg9sc0KdWi6I4O",
}

DEPTS = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
    "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron",
    "13": "Bouches-du-Rhône", "14": "Calvados", "15": "Cantal", "16": "Charente",
    "17": "Charente-Maritime", "18": "Cher", "19": "Corrèze", "20": "Corse",
    "21": "Côte-d'Or", "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne",
    "25": "Doubs", "26": "Drôme", "27": "Eure", "28": "Eure-et-Loir",
    "29": "Finistère", "30": "Gard", "31": "Haute-Garonne", "32": "Gers",
    "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine", "36": "Indre",
    "37": "Indre-et-Loire", "38": "Isère", "39": "Jura", "40": "Landes",
    "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire", "44": "Loire-Atlantique",
    "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne", "48": "Lozère",
    "49": "Maine-et-Loire", "50": "Manche", "51": "Marne", "52": "Haute-Marne",
    "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse", "56": "Morbihan",
    "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise", "61": "Orne",
    "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin",
    "68": "Haut-Rhin", "69": "Rhône", "70": "Haute-Saône", "71": "Saône-et-Loire",
    "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie", "75": "Paris",
    "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines",
    "79": "Deux-Sèvres", "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne",
    "83": "Var", "84": "Vaucluse", "85": "Vendée", "86": "Vienne",
    "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort",
    "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne", "95": "Val-d'Oise", "971": "Guadeloupe",
    "972": "Martinique", "973": "Guyane", "974": "La Réunion", "976": "Mayotte",
}
_TITRES = json.loads((SKILL / "assets" / "titre_specialites.json").read_text())
SPEC_TITRE = _TITRES["specialites"]
PRATIQUE_TITRE = _TITRES["pratiques_titre"]
PRATIQUE_CANON = _TITRES["pratiques_canon"]


def api_key():
    k = os.environ.get("AIRTABLE_API_KEY")
    if k:
        return k
    out = subprocess.run(
        ["bash", "-lc", "grep AIRTABLE_API_KEY ~/.zshrc | head -1"],
        capture_output=True, text=True,
    ).stdout
    m = re.search(r'AIRTABLE_API_KEY=["\']?([^"\'\s]+)', out)
    if not m:
        raise SystemExit("AIRTABLE_API_KEY introuvable (env ou ~/.zshrc)")
    return m.group(1)


KEY = api_key()


def fetch_table(table, fields):
    """Récupère tous les records d'une table (pagination incluse)."""
    records, offset = [], None
    while True:
        q = [("pageSize", "100"), ("returnFieldsByFieldId", "true")]
        q += [("fields[]", f) for f in fields]
        if offset:
            q.append(("offset", offset))
        url = f"https://api.airtable.com/v0/{BASE}/{table}?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {KEY}"})
        with urllib.request.urlopen(req) as r:
            data = json.load(r)
        records += data.get("records", [])
        offset = data.get("offset")
        if not offset:
            return records


def names(v):
    if isinstance(v, list):
        return [x.get("name", x) if isinstance(x, dict) else x for x in v]
    if isinstance(v, dict) and "name" in v:
        return [v["name"]]
    if isinstance(v, str):
        return [v]
    return []


def one(v):
    n = names(v)
    return n[0] if n else None


def dept_from_cp(cp):
    if not cp:
        return None
    digits = re.sub(r"\D", "", str(cp))
    if len(digits) < 2:
        return None
    code = digits[:3] if digits[:3] in ("971", "972", "973", "974", "976") else digits[:2]
    nom = DEPTS.get(code)
    return f"{nom} ({code})" if nom else None


def titre(pratiques, spec_req, contrat):
    """
    Règles de titre :
      - une spécialité REQUISE remplace la pratique  → « Vétérinaire Urgentiste »
      - sinon la ou les pratiques                    → « Vétérinaire canin/rural »
      - « Internat » en statut contractuel ajoute    → « … en Clinicat »
        (la pratique est alors conservée)
    Les spécialités OPTIONNELLES sont volontairement ignorées : elles décrivent
    un plus apprécié, pas la nature du poste. S'en servir produirait des titres
    faux (« Vétérinaire en management » sur un poste de médecine générale).
    """
    if spec_req:
        base = "Vétérinaire " + SPEC_TITRE.get(spec_req[0], spec_req[0])
    elif pratiques:
        # plusieurs pratiques peuvent retomber sur le même mot (Bovins + Laitier
        # → « rural ») : on déduplique en gardant l'ordre.
        mots = []
        for p in pratiques:
            w = PRATIQUE_TITRE.get(p, p.lower())
            if w not in mots:
                mots.append(w)
        base = "Vétérinaire " + "/".join(mots)
    else:
        base = "Vétérinaire"
    if "Internat" in (contrat or []):
        base += " en Clinicat"
    return base


def src_hash(annonce, notes_offre, notes_clin):
    blob = "\x00".join([(annonce or "").strip(), (notes_offre or "").strip(),
                        (notes_clin or "").strip()])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def main():

    clin_recs = fetch_table(T_CLINIQUES, list(F_CLIN.values()))
    clin = {r["id"]: r.get("fields", {}) for r in clin_recs}

    offre_recs = fetch_table(T_OFFRES, list(F.values()))

    state = json.loads(STATE.read_text()) if STATE.exists() else {"offers": {}}
    known = state.get("offers", {})

    targets, skipped = [], {"archivee": 0, "non_signe": 0}
    for r in offre_recs:
        f = r.get("fields", {})
        if f.get(F["archivee"]):
            skipped["archivee"] += 1
            continue
        if "Signé" not in names(f.get(F["statut_clin"])):
            skipped["non_signe"] += 1
            continue

        link = f.get(F["clinique"]) or []
        clin_id = link[0] if isinstance(link, list) and link else None
        cf = clin.get(clin_id, {}) if clin_id else {}

        cp = one(f.get(F["cp"]))
        dept = dept_from_cp(cp)
        if not dept:
            pays = cf.get(F_CLIN["pays"])
            pays = pays.get("name") if isinstance(pays, dict) else pays
            dept = pays or "France"

        # canonisation : la table Airtable contient des doublons et coquilles
        # (« volailles »/« Vollaile », « Rurale »). On normalise ici pour que
        # titres, filtre et libellés restent cohérents.
        pratiques = []
        for p in names(f.get(F["pratiques"])):
            c = PRATIQUE_CANON.get(p, p)
            if c not in pratiques:
                pratiques.append(c)
        spec_req = names(f.get(F["spec_req"]))
        contrat = names(f.get(F["contrat"]))
        targets.append({
            "ref": r["id"][-6:],
            "recordId": r["id"],
            "createdAt": r["createdTime"],
            "titre": titre(pratiques, spec_req, contrat),
            "departement": dept,
            "pratiques": pratiques,
            "specialite": spec_req[0] if spec_req else None,
            "contrat": contrat,
            "temps": names(f.get(F["temps"])),
            "gardes": one(f.get(F["gardes"])),
            "experience": one(f.get(F["experience"])),
            "date_demarrage": f.get(F["demarrage"]),
            # --- INTERNE : jamais publié, sert au contrôle d'anonymat ---
            "_clinique": f.get(F["nom_clin"]) or cf.get(F_CLIN["nom"]),
            "_cp": cp,
            "_ville": cf.get(F_CLIN["ville"]),
            "_veto": cf.get(F_CLIN["veto"]),
            "_src": {
                # "Annonce" n'est lu qu'en repli : concaténer les deux changerait
                # l'empreinte des offres qui ont les deux champs et signalerait
                # à tort leurs descriptions comme à réécrire.
                "annonce": (f.get(F["annonce"]) or "").strip()
                           or f.get(F["annonce_alt"]),
                "notes_offre": f.get(F["notes"]),
                "notes_clinique": cf.get(F_CLIN["notes"]),
            },
        })

    for t in targets:
        t["srcHash"] = src_hash(t["_src"]["annonce"], t["_src"]["notes_offre"],
                                t["_src"]["notes_clinique"])

    target_refs = {t["ref"] for t in targets}
    added = sorted(target_refs - set(known))
    removed = sorted(set(known) - target_refs)

    todo, changed, no_source = [], [], []
    for t in sorted(targets, key=lambda x: x["createdAt"], reverse=True):
        prev = known.get(t["ref"])
        has_src = any((t["_src"].get(k) or "").strip() for k in
                      ("annonce", "notes_offre", "notes_clinique"))
        is_new = prev is None
        src_changed = bool(prev) and prev.get("srcHash") != t["srcHash"]
        if not (is_new or src_changed):
            continue
        if not has_src:
            no_source.append(t["ref"])
            continue
        if src_changed:
            changed.append(t["ref"])
        todo.append({
            "ref": t["ref"],
            "raison": "nouvelle" if is_new else "source modifiée",
            "titre": t["titre"],
            "departement": t["departement"],
            "description_actuelle": (prev or {}).get("description", ""),
            "source": t["_src"],
        })

    (WORK / "airtable.json").write_text(
        json.dumps(targets, ensure_ascii=False, indent=1), encoding="utf-8")
    (WORK / "todo.json").write_text(
        json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")

    # Liste noire d'anonymat : tous les noms de cliniques, villes, vétérinaires
    # et domaines e-mail de la base. C'est l'ensemble exact de ce qui pourrait
    # identifier une structure — bien plus précis qu'une heuristique.
    block = {"cliniques": set(), "villes": set(), "personnes": set(), "domaines": set()}
    for cf in clin.values():
        if cf.get(F_CLIN["nom"]):
            block["cliniques"].add(str(cf[F_CLIN["nom"]]).strip())
        if cf.get(F_CLIN["ville"]):
            for part in re.split(r"[-/,;]| et ", str(cf[F_CLIN["ville"]])):
                part = part.strip()
                if len(part) >= 4:
                    block["villes"].add(part)
        if cf.get(F_CLIN["veto"]):
            block["personnes"].add(str(cf[F_CLIN["veto"]]).strip())
        for mk in ("mail1", "mail2"):
            mail = cf.get(F_CLIN[mk])
            if mail and "@" in str(mail):
                block["domaines"].add(str(mail).split("@")[1].strip().lower())
    (WORK / "blocklist.json").write_text(
        json.dumps({k: sorted(v) for k, v in block.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    diff = {
        "total_publiables": len(targets),
        "ignorees": skipped,
        "ajoutees": added,
        "retirees": removed,
        "descriptions_a_ecrire": [t["ref"] for t in todo],
        "dont_source_modifiee": changed,
        "sans_texte_source": no_source,
    }
    (WORK / "diff.json").write_text(
        json.dumps(diff, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps(diff, ensure_ascii=False, indent=1))
    print(f"\n→ {WORK}/todo.json : {len(todo)} description(s) à écrire")


if __name__ == "__main__":
    main()
