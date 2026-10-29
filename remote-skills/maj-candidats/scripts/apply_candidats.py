#!/usr/bin/env python3
"""Régénère la page candidats.html, le panneau « Candidats » de l'accueil et l'état persistant.

Entrées : work/candidats.json (fetch_candidats.py), work/descriptions.json (descriptions écrites
ou relues ce soir, {identifiant: texte}, passées au contrôle), .candidats-state.json (ce qui est en ligne).

Qui est en ligne après ce script :
  - un candidat publiable déjà en ligne, avec sa description (la nouvelle s'il y en a une) ;
  - un nouveau candidat publiable, SEULEMENT si work/descriptions.json lui donne une description :
    sans description validée, il attend (listé dans work/apply.json, rien n'est publié) ;
  - jamais un candidat de « retenus » (réglage manuel dans l'état, ex. recherche à reconfirmer) ;
  - jamais un candidat dont work/descriptions.json porte `null` : retiré ce soir par prudence (doute
    de la relecture sur une carte déjà en ligne), il repassera en « nouveau » la nuit suivante.
Un candidat qui n'est plus publiable disparaît de la page et de l'état ; ses réglages de carte (pas
sa description) sont gardés dans « anciens », pour le cas où il reviendrait.

La page reprend l'en-tête, le CSS, la carte et le pied de page de offres.html (assets/candidats.js
pour le script, assets/zones_geo.json pour les contours). Seuls les champs affichés partent dans le
HTML : ni nom, ni date de contact, ni empreinte.

Usage : python3 apply_candidats.py [--dry-run]
"""
import argparse
import datetime as dt
import html as _html
import json
import re
import sys

from paths import HOME, PAGE, SITE, SKILL, STATE, WORK

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--dry-run", action="store_true", help="calculer et afficher, sans rien écrire")
args = ap.parse_args()

f_cand = WORK / "candidats.json"
if not f_cand.exists():
    sys.exit("work/candidats.json absent : lance d'abord fetch_candidats.py.")
candidats = json.loads(f_cand.read_text(encoding="utf-8"))
f_desc = WORK / "descriptions.json"
nouvelles = json.loads(f_desc.read_text(encoding="utf-8")) if f_desc.exists() else {}
etat = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"candidats": {}, "retenus": {}}
publies, retenus, anciens = etat.get("candidats", {}), etat.get("retenus", {}), etat.get("anciens", {})
today = dt.date.today()

inconnues = sorted(set(nouvelles) - {c["ref"] for c in candidats})
if inconnues:
    sys.exit(f"work/descriptions.json cite des candidats hors périmètre : {inconnues}")

# ---------- qui est en ligne ce soir ----------
etat_neuf, en_attente, par_prudence = {}, [], []
for c in candidats:
    ref = c["ref"]
    if ref in retenus:
        continue
    ancien = publies.get(ref)
    if ref in nouvelles and not (nouvelles[ref] or "").strip():
        (par_prudence if ancien else en_attente).append(ref)   # `null` : doute de la relecture
        continue
    desc = (nouvelles.get(ref) or "").strip() or (ancien or {}).get("description", "")
    if not desc:
        en_attente.append(ref)   # nouveau sans description validée : il attend, rien n'est publié
        continue
    etat_neuf[ref] = dict(
        description=desc,
        # relue ce soir (nouvelle ou inchangée) : l'empreinte suit la source ; sinon on garde
        # l'ancienne, et le candidat ressortira « source modifiée » demain
        empreinte=c["empreinte"] if ref in nouvelles or ancien is None else ancien.get("empreinte"),
        ajustements=(ancien or anciens.get(ref) or {}).get("ajustements", {}),
        publie_le=(ancien or {}).get("publie_le") or today.isoformat(),
    )
retires = sorted(set(publies) - set(etat_neuf) - set(en_attente) - set(par_prudence))
# réglages des candidats sortis (ou retirés par prudence) : gardés pour un éventuel retour
anciens_neuf = {r: a for r, a in anciens.items() if r not in etat_neuf}
for r in retires + par_prudence:
    if publies[r].get("ajustements"):
        anciens_neuf[r] = {"ajustements": publies[r]["ajustements"]}

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
def cle_dispo(c):
    d = c["disponibilite"]
    if not d: return (1, 0, 0)
    if d == "Dès maintenant": return (0, 0, 0)
    m, y = d.rsplit(" ", 1)
    return (0, int(y), MOIS.index(m) + 1)

# Seuls les champs réellement affichés partent dans la page.
CHAMPS = ("ref", "titre", "pratiques", "specialites", "experience", "contrat", "temps", "gardes",
          "disponibilite", "zones", "description")
data, contact = [], {}
for c in sorted(candidats, key=lambda c: (cle_dispo(c), c["ref"])):
    if c["ref"] not in etat_neuf:
        continue
    d, a = dict(c), etat_neuf[c["ref"]]["ajustements"]
    for k in ("titre", "pratiques", "contrat", "experience"):
        if a.get(k):
            d[k] = a[k]
    if "specialites" in a:   # pastilles affichées, fixées à la relecture (liste positive)
        d["specialites"] = [s for s in d["specialites"] if s in a["specialites"]]
    d["description"] = etat_neuf[c["ref"]]["description"]
    d["zones"] = [{k: z[k] for k in ("label", "pays", "niveau", "lat", "lon")} for z in c["zones"]]
    data.append({k: d[k] for k in CHAMPS})
    contact[c["ref"]] = c.get("_contact") or ""

tpl = (SITE / "offres.html").read_text(encoding="utf-8")

# ---------- <head> ----------
head, rest = tpl.split('</head>', 1)
rep = {
    '<title>Nos offres · SaRecrute</title>': '<title>Candidats disponibles · SaRecrute</title>',
    'content="Offres de postes vétérinaires actuellement ouvertes par le cabinet SaRecrute, en France, Suisse et Belgique."':
        'content="Vétérinaires actuellement en recherche de poste, suivis par le cabinet SaRecrute. Profils anonymes, en France, Suisse et Belgique."',
    'href="https://sarecrute.com/offres"': 'href="https://sarecrute.com/candidats"',
    '<meta name="robots" content="index, follow" />': '<meta name="robots" content="noindex, nofollow" />',
    '<meta property="og:title" content="Nos offres · SaRecrute" />': '<meta property="og:title" content="Candidats disponibles · SaRecrute" />',
    'content="Offres de postes vétérinaires actuellement ouvertes par le cabinet SaRecrute."':
        'content="Vétérinaires actuellement en recherche de poste, suivis par le cabinet SaRecrute."',
    'content="https://sarecrute.com/offres"': 'content="https://sarecrute.com/candidats"',
}
for a, b in rep.items():
    assert a in head, a
    head = head.replace(a, b)
EXTRA_CSS = """
    /* ===== Page candidats (reprend les cartes de la page offres) ===== */
    .cand-zones {
      font-size: 0.8rem;
      color: var(--deep);
      line-height: 1.45;
      margin: 0;
    }
    .cand-zones b { font-weight: 600; color: var(--sage-dark); }
    .cand-spec {
      background: transparent;
      border: 1px solid var(--sage);
      color: var(--sage-dark);
    }
    /* La liste des zones compte maintenant tous les départements et cantons, aux libellés longs
       (« Canton d'Appenzell Rhodes-Extérieures ») : sans plancher à zéro, le menu élargit la colonne
       de gauche et écrase la carte. */
    #candidats .offres-layout { grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); }
    #candidats .offres-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    #candidats .offres-toolbar select { min-width: 0; flex: 1 1 0; text-overflow: ellipsis; }
    /* Deux étapes : la question « où se trouve votre clinique ? » avec la carte en grand, puis les
       candidats de la zone choisie, la carte passant dans la colonne de droite. */
    #candidats.is-accueil .cand-resultats { display: none; }
    #candidats:not(.is-accueil) .cand-accueil { display: none; }
    .cand-accueil {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr);
      grid-template-areas: "texte carte" "plus carte";
      grid-template-rows: auto 1fr;
      column-gap: 32px;
      align-items: start;
      margin-top: 8px;
    }
    .cand-accueil-texte { grid-area: texte; }
    .cand-accueil-plus { grid-area: plus; }
    .cand-carte-accueil { grid-area: carte; }
    .cand-intro { margin: 18px 0 0; font-size: 0.86rem; line-height: 1.6; color: var(--muted); }
    .cand-sous-titre { margin: -6px 0 22px; font-style: italic; font-size: 1rem; line-height: 1.5; color: var(--muted); max-width: none; }
    .cand-question {
      font-family: var(--display);
      font-size: clamp(1.5rem, 2.6vw, 2rem);
      color: var(--deep);
      margin: 0 0 6px;
    }
    .cand-question-sous { margin: 0 0 18px; color: var(--muted); font-size: 0.95rem; }
    .cand-recherche { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .cand-recherche input {
      flex: 1 1 100%;
      min-width: 0;
      font: inherit;
      font-size: 0.95rem;
      color: var(--deep);
      background: var(--warm-white);
      border: 1px solid var(--line-strong);
      border-radius: 999px;
      padding: 12px 18px;
    }
    .cand-recherche input:focus { outline: 2px solid var(--sage); outline-offset: 1px; }
    .cand-recherche-msg { min-height: 1.4em; margin: 8px 0 10px 4px; font-size: 0.85rem; color: var(--terracotta-dark); }
    .cand-carte-accueil {
      height: min(640px, calc(100vh - 140px));
      min-height: 520px;   /* colonne d'encarts + légende + note */
      border-radius: var(--radius);
      overflow: hidden;
      border: 1px solid var(--line);
      background: var(--warm-white);
    }
    .cand-tout-voir {
      margin-top: 14px;
      background: none;
      border: none;
      padding: 0;
      font: inherit;
      font-size: 0.9rem;
      color: var(--sage-dark);
      text-decoration: underline;
      text-underline-offset: 3px;
      cursor: pointer;
    }
    .cand-resultats { scroll-margin-top: 90px; }
    .cand-accueil { scroll-margin-top: 90px; }
    .cand-resultats-tete {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      justify-content: space-between;
      gap: 10px 20px;
      margin: 8px 0 20px;
    }
    .cand-titre { font-family: var(--display); font-size: clamp(1.4rem, 2.4vw, 1.8rem); color: var(--deep); margin: 0; }
    .cand-count { margin: 4px 0 0; color: var(--muted); font-size: 0.92rem; }
    .cand-changer {
      background: var(--warm-white);
      border: 1px solid var(--line-strong);
      border-radius: 999px;
      padding: 8px 16px;
      font: inherit;
      font-size: 0.85rem;
      color: var(--deep);
      cursor: pointer;
    }
    .cand-changer:hover { border-color: var(--sage); }
    #cand-carte {
      display: flex;
      flex-direction: column;
      width: 100%;
      height: 100%;
      background: var(--warm-white);
    }
    #cand-carte #offres-map {
      flex: 1;
      height: auto;
      min-height: 0;
      background: var(--warm-white);
    }
    /* Encarts (Paris et petite couronne, outre-mer) : en colonne à droite de la carte quand le bloc
       est large (étape 1 sur ordinateur), en bande dessous sinon. */
    #cand-carte { container-type: inline-size; }
    .cand-carte-corps { flex: 1; min-height: 0; display: flex; flex-direction: column; }
    .cand-encarts {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      gap: 6px 10px;
      padding: 8px 14px;
      border-top: 1px solid var(--line);
    }
    .cand-encart { margin: 0; display: flex; flex-direction: column; gap: 2px; }
    .cand-encart figcaption { font-family: var(--body); font-size: 0.68rem; color: var(--muted); line-height: 1.2; }
    .cand-encart svg { display: block; width: 58px; height: 46px; overflow: visible; }
    .cand-encart-grand svg { width: 104px; height: 74px; }
    .cand-encart path.cand-zone { stroke: #FFFDF8; stroke-width: 1; vector-effect: non-scaling-stroke; }
    .cand-encart path.cand-zone.is-survol { stroke: var(--deep); stroke-width: 2; }
    .cand-encart path.cand-zone.is-choisie { stroke: var(--terracotta); stroke-width: 2.5; }
    .cand-encart-num {
      pointer-events: none;
      font-family: var(--body);
      font-weight: 700;
      fill: var(--deep);
      text-anchor: middle;
      dominant-baseline: central;
      transition: opacity 0.15s;
    }
    .cand-encart-num.is-sombre { fill: var(--warm-white); }
    .cand-encart-num.is-hors-filtre { opacity: 0.45; }
    #cand-carte.cand-survol .cand-encart-num:not(.is-couvert) { opacity: 0.2; }
    .cand-encart-cible { cursor: pointer; outline: none; }
    figure.cand-encart-cible:focus-visible { box-shadow: 0 0 0 2px var(--deep); border-radius: 6px; }
    .cand-encart path.cand-zone:focus-visible { stroke: var(--deep); stroke-width: 2; }
    /* Colonne seulement au-dessus de 960 px : en dessous, la carte a une hauteur fixe et pleine
       largeur, et une colonne à côté sortait du cadre. */
    @media (min-width: 961px) {
    #cand-carte #offres-map { min-height: 280px; }
    /* Bande étroite (étape 2) : une seule ligne, vignettes compactes, défilement latéral au besoin,
       au lieu de deux lignes qui écrasaient la carte. */
    @container (max-width: 599px) {
      .cand-encarts { flex-wrap: nowrap; overflow-x: auto; gap: 6px; padding: 6px 12px; }
      .cand-encart figcaption { font-size: 0.6rem; white-space: nowrap; }
      .cand-encart svg { width: 46px; height: 38px; }
      .cand-encart-grand svg { width: 86px; height: 62px; }
    }
    @container (min-width: 600px) {
      .cand-carte-corps { flex-direction: row; }
      .cand-encarts {
        flex: none;
        display: grid;
        grid-template-columns: repeat(2, 70px);
        align-content: start;
        gap: 10px 12px;
        padding: 14px;
        border-top: none;
        border-left: 1px solid var(--line);
      }
      .cand-encart-grand { grid-column: 1 / -1; }
      .cand-encart svg { width: 70px; height: 52px; }
      .cand-encart-grand svg { width: 152px; height: 110px; }
      .cand-encarts { min-height: 0; overflow-y: auto; }
    }
    }
    .cand-encart-tip {
      position: fixed;
      z-index: 1000;
      pointer-events: none;
      background: #fff;
      padding: 8px 12px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--line);
      box-shadow: var(--shadow-soft);
      font-family: var(--body);
      font-size: 0.82rem;
    }
    .cand-encart-tip[hidden] { display: none; }
    .cand-encart-tip .offre-map-popup p { margin: 0; }
    .cand-encart-tip .cand-tip-detail { color: var(--muted); font-size: 0.76rem; }
    .cand-encart-tip .cand-tip-geste { margin-top: 4px; color: var(--sage-dark); font-weight: 600; }
    path.cand-zone { cursor: pointer; transition: fill-opacity 0.15s; }
    path.cand-zone.is-survol { stroke: var(--deep); stroke-width: 2; }
    path.cand-zone.is-choisie { stroke: var(--terracotta); stroke-width: 3; }
    path.cand-zone.is-hors-filtre { fill-opacity: 0.3; }
    #cand-carte.cand-survol path.cand-zone:not(.is-couvert) { fill-opacity: 0.18; }
    #cand-carte.cand-survol path.cand-zone.is-couvert { fill-opacity: 1; }
    /* leaflet.css, chargé après ce style, impose display:block aux icônes : sans cette spécificité
       le nombre se cale à gauche et tombe chez le voisin. */
    .leaflet-marker-icon.cand-zone-num {
      pointer-events: none;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      line-height: 16px;
      font-family: var(--body);
      font-size: 0.72rem;
      font-weight: 700;
      color: var(--deep);
      transition: opacity 0.15s;
    }
    .leaflet-marker-icon.cand-zone-num.is-sombre { color: var(--warm-white); }
    .leaflet-marker-icon.cand-zone-num.is-hors-filtre { opacity: 0.45; }
    #cand-carte.cand-survol .cand-zone-num:not(.is-couvert) { opacity: 0.2; }
    .cand-zone-tip { padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--line); box-shadow: var(--shadow-soft); }
    .cand-zone-tip .offre-map-popup p { margin: 0; }
    .cand-zone-tip .cand-tip-detail { color: var(--muted); font-size: 0.76rem; }
    .cand-zone-tip .cand-tip-geste { margin-top: 4px; color: var(--sage-dark); font-weight: 600; }
    .cand-legende {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px 12px;
      border-top: 1px solid var(--line);
      padding: 8px 14px;
      font-family: var(--body);
      font-size: 0.74rem;
      color: var(--deep);
    }
    .cand-legende:empty { display: none; }
    .cand-legende-titre { font-weight: 600; }
    .cand-legende-pas { display: inline-flex; align-items: center; gap: 4px; }
    .cand-legende-pas i { width: 12px; height: 12px; border-radius: 3px; display: inline-block; border: 1px solid var(--line); }
    .cand-map-note {
      border-top: 1px solid var(--line);
      padding: 10px 14px;
      font-size: 0.78rem;
      line-height: 1.6;
      color: var(--deep);
      transition: background 0.15s, color 0.15s;
    }
    .cand-map-note:empty { display: none; }
    .cand-map-note.is-hover { background: var(--sage-dark); color: var(--warm-white); }
    .cand-om {
      font: inherit;
      font-size: 0.74rem;
      color: var(--sage-dark);
      background: transparent;
      border: 1px solid var(--sage);
      border-radius: 999px;
      padding: 1px 9px;
      margin: 2px 0;
      cursor: pointer;
    }
    .cand-om:hover { background: var(--sage); color: var(--warm-white); }
    .cand-om.is-choisie { border-color: var(--terracotta); color: var(--terracotta-dark); }
    .offres-grid .offre-card { transition: opacity 0.15s, box-shadow 0.6s; }
    .offre-card.is-cible { box-shadow: 0 0 0 3px var(--terracotta), var(--shadow-soft); }
    .cand-grid-survol .offre-card:not(.is-zone-hover) { opacity: 0.4; }
    .offres-toolbar select optgroup { font-style: normal; font-weight: 600; }
    /* L'en-tête du site est collant (≈ 77 px) : la carte collante se cale dessous. */
    #candidats .offres-map-col { top: 96px; height: calc(100vh - 120px); }
    @media (max-width: 960px) {
      #candidats .offres-layout { grid-template-columns: minmax(0, 1fr); }
      /* Téléphone : la question, la carte, puis le reste. */
      .cand-accueil { grid-template-columns: minmax(0, 1fr); grid-template-areas: "texte" "carte" "plus"; grid-template-rows: auto; row-gap: 10px; }
      .cand-intro { margin-top: 14px; }
      /* Carte de hauteur fixe, légende et note dessous : la note ne la rétrécit plus. */
      #candidats .offres-map-col, .cand-carte-accueil { position: relative; height: auto; min-height: 0; }
      .cand-carte-corps { flex: none; }
      #cand-carte #offres-map { flex: none; height: 380px; }
    }
    @media (max-width: 600px) {
      #candidats .offres-grid { grid-template-columns: minmax(0, 1fr); }
      #candidats .offres-toolbar select { flex: 1 1 calc(50% - 4px); }
    }
  </style>"""
head = head.replace('  </style>', EXTRA_CSS, 1)

# ---------- <body> ----------
body = rest
start = body.index('<main>'); end = body.index('</main>') + len('</main>')
MAIN = """<main>
    <section id="candidats" class="offres-page">
      <div class="container">
        <a href="/" class="offres-breadcrumb">← Retour à l'accueil</a>
        <h1 class="offres-h1">Candidats disponibles</h1>
        <p class="cand-sous-titre">__NB_CANDIDATS__ vétérinaires en recherche de poste, tous appelés par nos recruteuses ces trois derniers mois — liste actualisée chaque jour</p>
        <!-- Étape 1 : la question du recruteur, « qui viendrait chez moi ? » -->
        <div class="cand-accueil" id="cand-accueil">
          <div class="cand-accueil-texte">
            <h2 class="cand-question">Où se trouve votre clinique ?</h2>
            <p class="cand-question-sous">Cliquez sur son département, son canton ou sa province, ou tapez-le : vous verrez les vétérinaires prêts à y travailler.</p>
            <form class="cand-recherche" id="cand-recherche" autocomplete="off">
              <input type="text" id="cand-zone-saisie" list="cand-zones-liste" placeholder="Département, canton ou code postal" aria-label="Département, canton ou code postal de votre clinique" enterkeyhint="search" />
              <datalist id="cand-zones-liste"></datalist>
            </form>
            <p class="cand-recherche-msg" id="cand-recherche-msg" role="status"></p>
          </div>
          <div class="cand-accueil-plus">
            <button type="button" class="cand-tout-voir" id="cand-tout-voir">ou parcourir tous les candidats sans choisir de zone</button>
            <p class="cand-intro">Un profil vous intéresse ? Cliquez sur « Ce profil m'intéresse » : nous vous recontactons pour en parler.</p>
          </div>
          <div class="cand-carte-accueil" id="cand-carte-accueil">
            <div id="cand-carte">
              <div class="cand-carte-corps">
                <div id="offres-map"></div>
                <div class="cand-encarts" id="cand-encarts"></div>
              </div>
              <div class="cand-legende" id="cand-legende"></div>
              <div class="cand-map-note" id="cand-map-note"></div>
            </div>
          </div>
        </div>

        <!-- Étape 2 : les candidats de la zone choisie -->
        <div class="cand-resultats" id="cand-resultats">
          <div class="cand-resultats-tete">
            <div>
              <h2 class="cand-titre" id="cand-titre"></h2>
              <p class="cand-count" id="cand-count"></p>
            </div>
            <button type="button" class="cand-changer" id="cand-changer">← Choisir une autre zone</button>
          </div>
          <div class="offres-layout">
            <div class="offres-list-col">
              <div class="offres-toolbar">
                <div class="offres-filters">
                  <select id="cand-filtre-zone" aria-label="Filtrer par zone de recherche"></select>
                  <select id="cand-filtre-pratique" aria-label="Filtrer par pratique"></select>
                  <select id="cand-filtre-contrat" aria-label="Filtrer par contrat"></select>
                  <select id="cand-filtre-experience" aria-label="Filtrer par expérience"></select>
                </div>
                <button type="button" class="offres-reset" id="cand-reset">Réinitialiser</button>
              </div>

              <div class="offres-grid" id="cand-grid"></div>
            </div>

            <div class="offres-map-col" id="cand-carte-liste"></div>
          </div>
        </div>
      </div>

    </section>
    <div class="cand-encart-tip" id="cand-encart-tip" hidden></div>
  </main>"""
body = body[:start] + MAIN.replace('__NB_CANDIDATS__', str(len(data))) + body[end:]

# Pas de formulaire de candidature ici : on retire la modale et tout le script de la page offres.
body = re.sub(r'\s*<!-- CANDIDATURE MODAL -->.*?</iframe>\s*</div>\s*</div>', '', body, count=1, flags=re.S)
s0 = body.index('  <script>\n    // ============ OFFRES ============')
s1 = body.index('</script>', s0) + len('</script>')
geo = json.load(open(SKILL / 'assets' / 'zones_geo.json'))
contours = {g['label'] for g in geo}
sans_contour = sorted({z['label'] for c in data for z in c['zones']
                       if z['niveau'] in ('dept', 'sous-pays') and z['label'] not in contours})
if sans_contour:
    sys.exit(f'Zones sans contour sur la carte (libellé à aligner sur zones_geo.json) : {sans_contour}')
for g in geo:
    g['lat'], g['lon'] = round(g['lat'], 3), round(g['lon'], 3)
script = ((SKILL / 'assets' / 'candidats.js').read_text()
          .replace('__CANDIDATS__', json.dumps(data, ensure_ascii=False))
          .replace('__ZONES_GEO__', json.dumps(geo, ensure_ascii=False, separators=(',', ':'))))
body = body[:s0] + '  <script>\n' + script + '\n  </script>' + body[s1:]
assert 'apply-overlay' not in body and 'OFFRES' not in body


page = head + "</head>" + body

# ---------- accueil : panneau « Candidats » de « Nos nouvelles offres / candidats » ----------
# Les derniers candidats appelés (dernier compte rendu d'appel, à défaut dernier signe de vie).
NB_TEASER = 8
def cle_contact(c):
    return contact.get(c["ref"], "")

PAYS_ENTIER_FR = {'France': 'toute la France', 'Suisse': 'toute la Suisse', 'Belgique': 'toute la Belgique', 'Luxembourg': 'Luxembourg'}
EXPERIENCE_FR = {'Etudiant': "Fin d'études", '1 à 2 ans': 'Semi-autonome'}
SPECIALITE_FR = {'Echographie': 'Échographie'}
def zone_tete(c):
    pays = list(dict.fromkeys(z['pays'] for z in c['zones'] if z['pays']))
    if len(pays) > 1: return ' · '.join(pays)
    if len(c['zones']) == 1: return c['zones'][0]['label']
    return pays[0] if pays else 'Plusieurs zones'
def resume_zones(c):
    l = [PAYS_ENTIER_FR.get(z['label'], z['label']) if z['niveau'] == 'pays' else z['label'] for z in c['zones']]
    l[0] = l[0][:1].upper() + l[0][1:]
    return ', '.join(l) if len(l) <= 4 else f"{', '.join(l[:3])} et {len(l) - 3} autres zones"

e = _html.escape
cartes = []
for c in sorted(data, key=cle_contact, reverse=True)[:NB_TEASER]:
    badges = ''.join(f'<span class="offre-teaser-badge">{e(SPECIALITE_FR.get(s, s))}</span>' for s in c['specialites'][:3])
    exp = EXPERIENCE_FR.get(c['experience'], c['experience'])
    cartes.append(f"""            <article class="offre-teaser-card">
              <div class="offre-teaser-head">
                <span class="offre-loc">{e(zone_tete(c))}</span>
                {f'<span class="offre-teaser-badge-corner">{e(exp)}</span>' if exp else ''}
              </div>
              <h3>{e(c['titre'])}</h3>
              <p class="cand-teaser-zones"><b>Recherche :</b> {e(resume_zones(c))}</p>
              <p class="offre-teaser-desc">{e(c['description'])}</p>
              {f'<div class="offre-teaser-badges">{badges}</div>' if badges else ''}
              <div class="offre-teaser-fields">
                <div class="offre-teaser-field"><span>Contrat souhaité</span><strong>{e(', '.join(c['contrat']) or 'Ouvert')}</strong></div><div class="offre-teaser-field"><span>Disponibilité</span><strong>{e(c['disponibilite'] or 'À préciser')}</strong></div>
              </div>
              <a href="candidats?profil={c['ref']}" class="btn btn-secondary">Voir le profil <span class="btn-arrow">→</span></a>
            </article>""")

PANNEAU = f"""        <!-- NOUVEAUX CANDIDATS : panneau généré par build_page.py (chaîne de la page candidats), ne pas éditer à la main -->
        <p class="teaser-lead">Les derniers vétérinaires appelés par nos recruteuses, parmi {len(data)} candidats en recherche de poste en France, en Suisse et en Belgique.</p>
        <div class="offres-carousel-wrap">
          <button type="button" class="offres-carousel-nav" id="candidats-carousel-prev" aria-label="Candidats précédents">‹</button>
          <div class="offres-carousel" id="candidats-carousel">
{chr(10).join(cartes)}
          </div>
          <button type="button" class="offres-carousel-nav" id="candidats-carousel-next" aria-label="Candidats suivants">›</button>
        </div>

        <div class="offres-carousel-dots" id="candidats-carousel-dots"></div>

        <div class="offres-teaser-cta">
          <a href="candidats" class="btn btn-primary">Voir tous les candidats <span class="btn-arrow">→</span></a>
        </div>
        <!-- /NOUVEAUX CANDIDATS -->
"""

accueil = HOME.read_text(encoding="utf-8")
m = re.search(r"        <!-- NOUVEAUX CANDIDATS :.*?<!-- /NOUVEAUX CANDIDATS -->\n", accueil, re.S)
if not m:
    sys.exit(f"{HOME.name} : marqueurs <!-- NOUVEAUX CANDIDATS --> introuvables dans le panneau « Candidats ».")
accueil = accueil[:m.start()] + PANNEAU + accueil[m.end():]

# Pas de date de mise à jour dans l'état : il ne doit changer que si le contenu change (sinon une
# publication et un message chaque nuit pour rien).
etat_ecrit = {"version": 1, "candidats": dict(sorted(etat_neuf.items())),
              "retenus": dict(sorted(retenus.items())), "anciens": dict(sorted(anciens_neuf.items()))}
resume = dict(en_ligne=len(data), publies_ce_soir=sorted(set(etat_neuf) - set(publies)),
              retires=retires, retires_par_prudence=sorted(par_prudence), en_attente=sorted(en_attente),
              descriptions_changees=sorted(r for r in etat_neuf if r in publies
                                           and etat_neuf[r]["description"] != publies[r].get("description")))
print(f"→ en ligne : {len(data)} · publiés ce soir : {len(resume['publies_ce_soir'])} · retirés : {len(retires)} · "
      f"retirés par prudence : {len(par_prudence)} · en attente de description : {len(en_attente)} · "
      f"descriptions changées : {len(resume['descriptions_changees'])}")
for r in en_attente:
    print(f"   … {r} attend une description validée")
if args.dry_run:
    print("--dry-run : rien n'est écrit.")
    sys.exit(0)
PAGE.write_text(page, encoding="utf-8")
HOME.write_text(accueil, encoding="utf-8")
STATE.write_text(json.dumps(etat_ecrit, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
(WORK / "apply.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
f_desc.unlink(missing_ok=True)   # consommé : un reste ne doit pas resservir demain
print(f"✔ {PAGE.name}, {HOME.name} (panneau « Candidats » : {len(cartes)} cartes) et {STATE.name} écrits.")
