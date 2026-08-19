#!/usr/bin/env python3
"""
Étape 3 de la mise à jour des offres du site SaRecrute.

Fusionne work/descriptions.json (écrit par le modèle) dans .offres-state.json,
puis régénère :
  - offres.html            → tableau OFFRES (données publiques uniquement)
  - site_sarecrute_v4.html → cartes du carousel + map OFFRES_TEASER

Le tag "Nouvelle offre" est posé sur les offres récentes, avec un minimum
garanti (--min-new, défaut 5) même si la fenêtre est vide.

Usage :
  python3 apply_offres.py [--window-days 30] [--min-new 5] [--dry-run]
"""
import argparse
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from paths import SITE, STATE, SKILL, WORK

OFFRES_HTML = SITE / "offres.html"
HOME_HTML = SITE / "site_sarecrute_v4.html"
CENTROIDS = SKILL / "assets" / "dept_centroids.json"

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc."]

# Libellés d'affichage, source unique = assets/titre_specialites.json.
# offres.html les reçoit par injection (voir sync_labels) ; l'accueil étant du
# HTML statique, c'est ce script qui traduit directement.
# (initialisés dans main(), après la définition des chemins)
EXPERIENCE_LABELS = {}
PRATIQUE_LABELS = {}

# Champs autorisés dans le HTML publié. Tout le reste (nom de clinique, CP,
# textes sources) reste dans work/ et ne sort jamais.
PUBLIC_FIELDS = ["ref", "titre", "departement", "pratiques", "specialite",
                 "contrat", "temps", "gardes", "experience", "disponibilite",
                 "lat", "lon", "createdAt", "isNew", "description"]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def fmt_date(iso, today):
    if not iso:
        return None
    if iso <= today:
        return "Dès que possible"
    try:
        y, m, d = iso.split("-")
        return f"{d} {MOIS[int(m) - 1]} {y}"
    except Exception:
        return iso


def coords(dept, cent):
    m = re.search(r"\((\d{2,3})\)", dept or "")
    if m and m.group(1) in cent:
        c = cent[m.group(1)]
        return c["lat"], c["lon"]
    pays = cent.get("_pays", {})
    if dept in pays:
        return pays[dept]["lat"], pays[dept]["lon"]
    for label, c in pays.items():                     # correspondance partielle
        base = label.split(" (")[0]
        if dept and base.lower() in dept.lower():
            return c["lat"], c["lon"]
    return None, None


def splice(html, pattern, replacement, label):
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        raise SystemExit(f"Ancre introuvable dans le HTML : {label}")
    return html[:m.start()] + replacement + html[m.end():]


def build_offers(targets, state, window_days, min_new, today_iso):
    cent = json.loads(CENTROIDS.read_text())
    known = state["offers"]

    offers = []
    missing_coords = []
    for t in sorted(targets, key=lambda x: x["createdAt"], reverse=True):
        lat, lon = coords(t["departement"], cent)
        if lat is None:
            missing_coords.append((t["ref"], t["departement"]))
        offers.append({
            "ref": t["ref"],
            "titre": t["titre"],
            "departement": t["departement"],
            "pratiques": t["pratiques"],
            "specialite": t.get("specialite"),
            "contrat": t["contrat"],
            "temps": t["temps"],
            "gardes": t["gardes"],
            "experience": t["experience"],
            "disponibilite": fmt_date(t.get("date_demarrage"), today_iso),
            "lat": lat,
            "lon": lon,
            "createdAt": t["createdAt"],
            "description": known.get(t["ref"], {}).get("description", ""),
            "isNew": False,
        })

    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    recent = [o for o in offers if o["createdAt"] >= cutoff]
    tagged = recent if len(recent) >= min_new else offers[:min_new]
    tagged_refs = {o["ref"] for o in tagged}
    for o in offers:
        o["isNew"] = o["ref"] in tagged_refs

    return offers, [o for o in offers if o["isNew"]], missing_coords


def render_offres_page(offers):
    html = OFFRES_HTML.read_text(encoding="utf-8")
    public = [{k: o[k] for k in PUBLIC_FIELDS if k in o} for o in offers]
    data = json.dumps(public, ensure_ascii=False, separators=(",", ":"))
    html = splice(html, r"const OFFRES = \[.*?\];",
                  f"const OFFRES = {data};", "const OFFRES (offres.html)")

    # Tables de libellés : réinjectées depuis l'asset pour qu'une nouvelle
    # pratique n'apparaisse jamais brute dans le menu « Pratiques ».
    html = splice(html, r"const PRATIQUE_LABELS = \{.*?\};",
                  "const PRATIQUE_LABELS = "
                  + json.dumps(PRATIQUE_LABELS, ensure_ascii=False) + ";",
                  "const PRATIQUE_LABELS (offres.html)")
    html = splice(html, r"const EXPERIENCE_LABELS = \{.*?\};",
                  "const EXPERIENCE_LABELS = "
                  + json.dumps(EXPERIENCE_LABELS, ensure_ascii=False) + ";",
                  "const EXPERIENCE_LABELS (offres.html)")
    return html


def render_home(new_offers):
    html = HOME_HTML.read_text(encoding="utf-8")

    cards = []
    for o in new_offers:
        badges = "".join(
            f'<span class="offre-teaser-badge">{esc(c)}</span>' for c in o["contrat"])
        fields = []
        if o["temps"]:
            libelle = ("Plein, partiel"
                       if {"Temps plein", "Temps partiel"} <= set(o["temps"])
                       else ", ".join(o["temps"]))
            fields.append('<div class="offre-teaser-field"><span>Temps de travail</span>'
                          f"<strong>{esc(libelle)}</strong></div>")
        if o["gardes"]:
            fields.append('<div class="offre-teaser-field"><span>Gardes</span>'
                          f'<strong>{esc(o["gardes"])}</strong></div>')
        dispo = o["disponibilite"] or "Dès que possible"
        fields.append('<div class="offre-teaser-field"><span>Disponibilité</span>'
                      f"<strong>{esc(dispo)}</strong></div>")
        exp_label = EXPERIENCE_LABELS.get(o["experience"], o["experience"])
        exp = (f'<span class="offre-teaser-badge-corner">{esc(exp_label)}</span>'
               if exp_label else "")
        cards.append(
            '            <article class="offre-teaser-card">\n'
            '              <div class="offre-teaser-head">\n'
            f'                <span class="offre-loc">{esc(o["departement"])}</span>\n'
            f"                {exp}\n"
            "              </div>\n"
            f'              <h3>{esc(o["titre"])}</h3>\n'
            f'              <p class="offre-teaser-desc">{esc(o["description"])}</p>\n'
            '              <div class="offre-teaser-badges">\n'
            f"                {badges}\n"
            "              </div>\n"
            '              <div class="offre-teaser-fields">\n'
            f'                {"".join(fields)}\n'
            "              </div>\n"
            '              <button type="button" class="btn btn-secondary" '
            f'data-offre-ref="{esc(o["ref"])}">Postuler '
            '<span class="btn-arrow">→</span></button>\n'
            "            </article>\n"
        )

    html = splice(
        html,
        r'(?<=<div class="offres-carousel" id="offres-carousel">\n).*?'
        r'(?=          </div>\n          <button type="button" class="offres-carousel-nav" id="offres-carousel-next")',
        "\n" + "".join(cards),
        "bloc carousel (accueil)",
    )

    teaser = {o["ref"]: {"titre": o["titre"], "departement": o["departement"]}
              for o in new_offers}
    body = ",\n".join(
        f'      {json.dumps(k)}: {{ titre: {json.dumps(v["titre"], ensure_ascii=False)}, '
        f'departement: {json.dumps(v["departement"], ensure_ascii=False)} }}'
        for k, v in teaser.items())
    return splice(html, r"const OFFRES_TEASER = \{.*?\};",
                  "const OFFRES_TEASER = {\n" + body + ",\n    };",
                  "const OFFRES_TEASER (accueil)")


def main():
    global EXPERIENCE_LABELS, PRATIQUE_LABELS
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--min-new", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    titres = json.loads((SKILL / "assets" / "titre_specialites.json").read_text())
    EXPERIENCE_LABELS = titres["experience"]
    PRATIQUE_LABELS = titres["pratiques_filtre"]

    targets = json.loads((WORK / "airtable.json").read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {"offers": {}}

    # 1. fusionner les nouvelles descriptions
    desc_file = WORK / "descriptions.json"
    new_desc = json.loads(desc_file.read_text()) if desc_file.exists() else {}
    by_ref = {t["ref"]: t for t in targets}
    for ref, text in new_desc.items():
        if ref not in by_ref:
            raise SystemExit(f"Description fournie pour une offre hors périmètre : {ref}")
        state["offers"].setdefault(ref, {})["description"] = text.strip()

    # 2. synchroniser l'état sur le périmètre courant
    for ref, t in by_ref.items():
        state["offers"].setdefault(ref, {"description": ""})["srcHash"] = t["srcHash"]
    for ref in list(state["offers"]):
        if ref not in by_ref:
            del state["offers"][ref]

    today = datetime.now(timezone.utc).date().isoformat()
    offers, new_offers, missing = build_offers(
        targets, state, args.window_days, args.min_new, today)

    sans_desc = [o["ref"] for o in offers if not o["description"]]
    sans_desc_new = [o["ref"] for o in new_offers if not o["description"]]

    print(f"offres publiées      : {len(offers)}")
    print(f'tag "Nouvelle offre" : {len(new_offers)} '
          f'({args.window_days} j, minimum {args.min_new})')
    print(f"sans description     : {len(sans_desc)} {sans_desc if sans_desc else ''}")
    if missing:
        print(f"⚠ coordonnées carte manquantes : {missing}")
    if sans_desc_new:
        print(f"⚠ offres taguées sans description : {sans_desc_new}")

    if args.dry_run:
        print("\n--dry-run : aucun fichier modifié.")
        return

    offres_out = render_offres_page(offers)
    home_out = render_home(new_offers)

    OFFRES_HTML.write_text(offres_out, encoding="utf-8")
    HOME_HTML.write_text(home_out, encoding="utf-8")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True),
                     encoding="utf-8")
    if desc_file.exists():
        desc_file.unlink()

    print("\n✔ offres.html, site_sarecrute_v4.html et .offres-state.json mis à jour.")


if __name__ == "__main__":
    main()
