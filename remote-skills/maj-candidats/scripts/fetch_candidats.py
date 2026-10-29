#!/usr/bin/env python3
"""Lit l'Airtable de production, choisit les candidats à publier et calcule ce qui change.

Périmètre publié (règle du 28/10/2026) : candidat « En recherche active », pas embauché par
SaRecrute, n'ayant pas signalé avoir trouvé, avec un signe de vie de moins de 3 mois et au
moins un compte rendu d'appel (Communications « Transcript text » ou champ Transcripts de la
fiche). Les dates de modification Airtable sont inutilisables (mises à jour en masse) : le
« dernier signe de vie » est le plus récent de la création, d'un post « Vétérinaire cherche
poste », d'une communication, d'une présentation, d'un entretien, d'une réponse à une
proposition et des entrées datées des notes (relances sans réponse exclues).

Écrit dans WORK (données personnelles : rien de ce dossier n'est commité) :
  candidats.json   les candidats publiables : champs de carte publics + _nom, _contact (interne)
  dossiers/REF.json  sources validées, carte et termes interdits, pour rédiger et contrôler
  todo.json        descriptions à écrire (« nouveau ») ou à relire (« source modifiée »)
  diff.json        ajouts, retraits (avec motif), revues, retenus — nommés pour le compte rendu

Un candidat déjà en ligne repasse aussi dans todo.json (« contrôle ») si sa description échoue au
contrôle avec les termes interdits du jour (un nom ou une ville ajoutés à sa fiche, par exemple).

Usage : python3 fetch_candidats.py [--date AAAA-MM-JJ] [--initialiser]
  --initialiser  autorise l'absence de .candidats-state.json (toute première mise en place) ; sans
                 lui, un état absent alors que candidats.html existe arrête le script : repartir de
                 zéro republierait tout comme « nouveau », sans les réglages ni les retenus.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import re
import shutil
import sys

from airtable import fetch_table
from check_descriptions import alertes
from paths import PAGE, SKILL, STATE, WORK

# ---------------------------------------------------------------- tables et champs
T_CAND, T_CANDIDATURES, T_COMM = "tblPmkTaAjS9Yoovt", "tbl3LnGoBxnheGI7v", "tblljQmKBIAxlaesD"
T_POSTS, T_COMP, T_ACTES, T_EXP = "tblE8XF5PjgUd7PdP", "tblH8Zym1DNu7PN3c", "tblt32Afmq6vQ6FJS", "tblTYdApkiHqKeBVi"

C = dict(  # Candidats
    nom="fldYoAnklCFHyrjLh", statut="fldOijG6rapbZUqMR", cree="fld1zQWiaMpOwKAjM",
    dispo="fldlCCJY7quJEqbyv", en_poste="fldnAVvWO3EfSOXXs", notes="fld0s84U1HdrHKqkg",
    transcripts="fldNMVoFoHx3t3O9D", auteur_key="fldkPqxhISja7S1RU",
    p_req="fldKxF494zI5Kgc6n", p_mai="fldsUtHmyFAFyjFgl", p_opt="fld6tibAOw9YfzkuI",
    s_mai="flde9dmHJUqdMZIOL", s_req="fldYpaOYuUBHpqlqU", s_opt="fldB1A9V3S74LbseU",
    contrats="fldZaUsTcNsN7HlWe", zones="fldacGQbzpkx88ULc", experience="fldfwzkT8yXZthQiZ",
    temps="fldGZhonpYwDW78ze", gardes="fldI1xWGed3dcQIUs",
    habilitation="fldSIVZ8UxggjhffA", profil_ia="fldtz8Gy68I1RMXrm", profil="fldlnO9d1ctGABT9v",
    annees="fldSGOptEz0Api4wN", freq_gardes="fldZ3kGzgXLhj5UJv", logement="fldpnnrJHV3BWLIYC",
    internat="fld3eO9JuwrHyNkIJ", desv="fldnvfN95E23ng7ep", taille="fldgUE6JdEkDwTzmB",
    refere="fldLICFF8e0p6Bz6d", groupe="fldJEVu81KYnd7zWG", precisions_zone="fldDCZKuKUoFfPgSC",
    # identifiants personnels : jamais publiés, servent de liste d'interdits au contrôle
    prenom="fld1WR6pNpe8sAya6", nom_famille="fld6yzzWrqBZBtXly", mail="fldmtHKu93RMqkVw6",
    tel="fldZ9229oPu876Ls2", ville="fldgnVDSacJdlzRG9", cp="fldjFm8KKLcFNgyNb",
    ecole="fldEUkJLo4ygiEZHZ", sortie="fldp6whT8yfZdETi4", diplome_sup="fldmi2DQKpPmcpXEV",
)
K = dict(  # Candidatures
    candidat="fldIk7cKNui6UXCgp", statut="fldiYea1jiErQf4DY", cree="fldv3AuwQgRM0yetP",
    intro_cand="fld9QJvBSFmddWGbr", intro_clin="fldvTlz0oSMu5pQyB", entretien="fldItuC23r3EwYm70",
    notes="fldvIrOrRNwFsAeHI", notes_rec="fldcDGAILdxSjqnFB",
)
M = dict(candidat="fldLfFD5vyQzMlgVZ", cree="fldSr4WkkrExr7F73", transcript="fldPT6fEB34T1sQHs")
P = dict(candidat="fldWa55md6fo4nRes", date="fldpHNjzipmU9hy7r", type="fldIy6iyrM0b9YrMN",
         date2="fld7tJn424p0HybQu", auteur_key="fldMuzJEYkcMB90bC")
COMP = dict(candidat="fldgZcNbLQ9vRF5mU", actes="fldUZQyIvlhNeZhzG", niveau="fld0SGFcuffxHSSq0")
ACTE = dict(nom="fldRieAkhj53QUXn7", espece="fldDB95GQHVopEXB0", famille="fldjYKdy0nenTcZwQ")
EXP = dict(candidat="fldYbpAW0GK8Ijm1w", poste="fldKL9vuSGhrwgV4c", type="fldp0espnc2GHvnHZ",
           pratiques="fldwrqz3c7QlBahc7", duree="flduZveIw1rViotNt", en_cours="fldXic8NllpuNPVfk",
           description="fldf4RmAB4BbabJgI", structure="fldZsxMqiU6OuTCBH",
           ville1="fldwHvWw1YCyD4G98", ville2="fldofaADJZBXYaaX3")

ACTIF = "En recherche active"
EMBAUCHE = "Candidat embauché"
REPONSES = {"Refusé par le candidat", "Nurturing", "Refusé par la clinique", "Déjà en contact avec clinique",
            "Candidat indécis", "Candidat intéressé", EMBAUCHE, "Candidat postulé", "En process"}
FENETRE_JOURS = 92   # « moins de 3 mois »

# Entrées datées des notes : une relance sans réponse n'est pas un signe de vie ; « j'ai trouvé »
# en est un, mais il sort le candidat du périmètre s'il est le plus récent.
OUT = (r"relance|pas de r[ée]ponse|ne r[ée]pond|sans r[ée]ponse|propal|propos[ée]|envoy[ée]|r[ée]pondeur|"
       r"message laiss|appel[ée]? (?:pas|sans)|laiss[ée] un|tentative|mis pas en recherche|jamais (?:re-?)?r[ée]pondu")
FOUND = (r"(?:a|ai|avons) trouv[ée]|j'ai commenc|a commenc[ée]|a sign[ée]|ai sign[ée]|va signer|"
         r"promesse d.embauche|en poste depuis|plus en recherche|n'est plus en recherche|ne cherche plus|"
         r"a accept[ée] un poste|j'ai accept|install[ée]e? (?:à|a) son compte|embauch[ée]e? (?:à|a|chez|dans)|"
         r"pris un poste|retrouv[ée] un poste|ai d[ée]j[àa] trouv")
DRE = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?![\d/])")

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def sel(v):
    if isinstance(v, list):
        return [sel(x) for x in v]
    return v.get("name") if isinstance(v, dict) else v


def D(s):
    if not s:
        return None
    if isinstance(s, list):
        s = s[0] if s else None
        if not s:
            return None
    return dt.date.fromisoformat(str(s)[:10])


def entrees_datees(texte, cree, today):
    """(date, sorte) des dates jj/mm[/aa] d'un texte de notes. Année absente : la plus ancienne
    plausible pour un signe de vie (un signe douteux ne doit pas rajeunir un candidat), la plus
    récente pour un « a trouvé » (un départ douteux doit le sortir, pas le garder en ligne)."""
    res = []
    for m in DRE.finditer(texte or ""):
        j, mo, an = int(m.group(1)), int(m.group(2)), m.group(3)
        if not (1 <= j <= 31 and 1 <= mo <= 12):
            continue
        ctx = texte[max(0, m.start() - 25): m.end() + 160].lower()
        trouve = bool(re.search(FOUND, ctx))
        annees = ([int(an) + (2000 if len(an) == 2 else 0)] if an
                  else [today.year, today.year - 1] if trouve else [today.year - 1, today.year])
        x = None
        for a in annees:
            try:
                x = dt.date(a, mo, j)
            except ValueError:
                x = None
                continue
            if x > today or a < 2023:
                x = None
                continue
            if not an and cree and x < cree - dt.timedelta(days=10):
                x = None
                continue
            break
        if x is None:
            continue
        avant = texte[max(0, m.start() - 30):m.start()].lower()
        if re.search(r"dispo|partir d|jusqu|d[èe]s le|avant le|commence le|fin |d[ée]but|entre le", avant):
            continue   # une date de disponibilité ou de projet n'est pas un échange
        sorte = "found" if trouve else ("out" if re.search(OUT, ctx) else "in")
        res.append((x, sorte))
    return res


def ref_de(record_id):
    """Identifiant public d'un candidat : empreinte de l'identifiant Airtable COMPLET. Il ne figure ni
    sur les dossiers envoyés aux cliniques ni nulle part ailleurs : une clinique qui garde un ancien
    dossier (référence SR-XXXXX, 5 derniers caractères) ne peut pas le recalculer ni relier la carte
    publique à la personne. Stable d'une nuit à l'autre."""
    return hashlib.sha256(f"sarecrute:candidat:{record_id}".encode("utf-8")).hexdigest()[:10]


def empreinte(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def nettoie(t):
    return re.sub(r"\*\*|__|`", "", t or "").strip()


# ---------------------------------------------------------------- carte publique
GEO = {z["label"]: z for z in json.loads((SKILL / "assets" / "zones_geo.json").read_text(encoding="utf-8"))}
TITRES = json.loads((SKILL.parent / "maj-offres" / "assets" / "titre_specialites.json").read_text(encoding="utf-8"))
PT = TITRES["pratiques_titre"]
SOUS_PAYS = {   # libellés Airtable des zones hors départements français → libellés de la carte
    "Canton de Neuchatel": "Canton de Neuchâtel",
    "Province de Bruxelles": "Région de Bruxelles-Capitale",
}
PAYS = {"France", "Suisse", "Belgique", "Espagne", "Luxembourg"}
AUTRES = {"Nouvelle calédonie": "Nouvelle-Calédonie", "Ile Maurice": "Île Maurice"}


def zone(z):
    """« 29 - Finistère » → Finistère (29) ; canton, province, pays ; territoires sans contour."""
    m = re.match(r"^(\d{2,3}) - (.+)$", z)
    if m:
        code, nom = m.groups()
        if nom == "Mayotte":       # le select Airtable code Mayotte « 974 », comme La Réunion
            code = "976"
        if code == "20":           # « 20 - Corse-du-Sud » : la carte et l'URL attendent 2A / 2B
            code = "2A" if nom == "Corse-du-Sud" else "2B"
        label = f"{nom} ({code})"
        g = GEO.get(label)
        return dict(label=label, pays="France", niveau="dept", lat=g and g["lat"], lon=g and g["lon"])
    if z in PAYS:
        return dict(label=z, pays=z, niveau="pays", lat=None, lon=None)
    label = SOUS_PAYS.get(z, z)
    if label.startswith(("Canton ", "Province ", "Région de Bruxelles")):
        g = GEO.get(label)
        return dict(label=label, pays="Suisse" if label.startswith("Canton") else "Belgique",
                    niveau="sous-pays", lat=g and g["lat"], lon=g and g["lon"])
    return dict(label=AUTRES.get(z, z), pays=None, niveau="autre", lat=None, lon=None)


def titre(pratiques, spec_req):
    if len(spec_req or []) == 1 and spec_req[0] == "Urgences":
        return "Vétérinaire urgentiste"
    mots = []
    for p in pratiques:
        m = PT.get(p) or ("rural" if p in ("Ovin/Caprin",) else None)
        if m and m not in mots:
            mots.append(m)
    ordre = ["canin", "rural", "équin", "NAC", "mixte"]
    mots.sort(key=lambda m: ordre.index(m) if m in ordre else 99)
    return "Vétérinaire " + "/".join(mots) if mots else "Vétérinaire"


def dispo(iso, today):
    if not iso:
        return None
    d = dt.date.fromisoformat(iso[:10])
    if d <= today + dt.timedelta(days=14):
        return "Dès maintenant"
    return f"{MOIS[d.month - 1]} {d.year}"


# ---------------------------------------------------------------- lecture

def lire_airtable():
    print("→ lecture d'Airtable …", flush=True)
    t = dict(
        cand=fetch_table(T_CAND, sorted(set(C.values()))),
        candidatures=fetch_table(T_CANDIDATURES, sorted(set(K.values()))),
        comm=fetch_table(T_COMM, sorted(set(M.values()))),
        posts=fetch_table(T_POSTS, sorted(set(P.values()))),
        comp=fetch_table(T_COMP, sorted(set(COMP.values()))),
        actes=fetch_table(T_ACTES, sorted(set(ACTE.values()))),
        exp=fetch_table(T_EXP, sorted(set(EXP.values()))),
    )
    print("   " + ", ".join(f"{k} {len(v)}" for k, v in t.items()))
    return t


def signes_de_vie(t, today):
    """Par candidat : dernier signe de vie, embauche, « a trouvé », dernier compte rendu d'appel."""
    F = lambda r, k: r["fields"].get(k)
    cle_vers_cand = collections.defaultdict(list)
    for r in t["cand"]:
        k = (F(r, C["auteur_key"]) or "").strip()
        if k:
            cle_vers_cand[k].append(r["id"])
    posts = collections.defaultdict(list)
    for p in t["posts"]:
        if sel(F(p, P["type"])) != "Vétérinaire cherche poste":
            continue
        d = D(F(p, P["date"])) or D(F(p, P["date2"]))
        if not d:
            continue
        ids = set(F(p, P["candidat"]) or [])
        k = (F(p, P["auteur_key"]) or "").strip()
        if k and len(cle_vers_cand.get(k, [])) == 1:
            ids |= set(cle_vers_cand[k])
        for i in ids:
            posts[i].append(d)
    comms, appels = collections.defaultdict(list), collections.defaultdict(list)
    for m in t["comm"]:
        d = D(F(m, M["cree"]))
        for i in F(m, M["candidat"]) or []:
            if d:
                comms[i].append(d)
                if (F(m, M["transcript"]) or "").strip():
                    appels[i].append(d)
    par_cand = collections.defaultdict(list)
    for k in t["candidatures"]:
        for i in F(k, K["candidat"]) or []:
            par_cand[i].append(k)

    res = {}
    for r in t["cand"]:
        i, f = r["id"], r["fields"]
        cree = D(f.get(C["cree"])) or D(r.get("createdTime"))
        sig = [cree] + posts.get(i, []) + comms.get(i, [])
        embauche, trouve = None, []
        for k in par_cand.get(i, []):
            s, kc = sel(F(k, K["statut"])), D(F(k, K["cree"]))
            if s == EMBAUCHE:
                embauche = max(filter(None, [embauche, kc])) if (embauche or kc) else today
            for champ in ("intro_clin", "entretien"):
                x = D(F(k, K[champ]))
                if x and x <= today:
                    sig.append(x)
            if s in REPONSES:
                x = max(filter(None, [kc, D(F(k, K["intro_cand"]))]), default=None)
                if x:
                    sig.append(x)
            texte = (F(k, K["notes"]) or "") + "\n" + (F(k, K["notes_rec"]) or "")
            for x, sorte in entrees_datees(texte, kc or cree, today):
                if sorte != "out":
                    sig.append(x)
                if sorte == "found":
                    trouve.append(x)
        texte = (f.get(C["notes"]) or "") + "\n" + (f.get(C["transcripts"]) or "")[:3000]
        for x, sorte in entrees_datees(texte, cree, today):
            if sorte != "out":
                sig.append(x)
            if sorte == "found":
                trouve.append(x)
        sig = [x for x in sig if x]
        dernier = max(sig) if sig else None
        a_appel = bool(appels.get(i)) or bool((f.get(C["transcripts"]) or "").strip())
        res[i] = dict(dernier=dernier, embauche=embauche, trouve=max(trouve) if trouve else None,
                      a_appel=a_appel, dernier_appel=max(appels[i]) if appels.get(i) else None)
    return res


def motif_hors_perimetre(r, s, today):
    """None si le candidat est publiable, sinon la raison (pour le compte rendu)."""
    statut = sel(r["fields"].get(C["statut"]))
    if statut != ACTIF:
        return f"statut « {statut or 'vide'} »"
    if s["embauche"]:
        return "embauché via SaRecrute"
    if s["trouve"] and s["dernier"] and s["trouve"] >= s["dernier"] - dt.timedelta(days=3):
        return "a signalé avoir trouvé un poste"
    if not s["dernier"] or (today - s["dernier"]).days >= FENETRE_JOURS:
        return "pas de signe de vie depuis plus de 3 mois"
    if not s["a_appel"]:
        return "aucun compte rendu d'appel"
    if not r["fields"].get(C["zones"]):
        return "aucune zone de recherche renseignée"
    return None


def carte_affichee(carte, ajustements):
    """La carte telle qu'elle sera en ligne : réglages de l'état appliqués (titre, pratiques, contrat,
    expérience remplacés ; pastilles limitées à la liste « specialites » si elle existe)."""
    c = dict(carte)
    for k in ("titre", "pratiques", "contrat", "experience"):
        if ajustements.get(k):
            c[k] = ajustements[k]
    if "specialites" in ajustements:
        c["specialites"] = [s for s in carte["specialites"] if s in ajustements["specialites"]]
    return c


def construire(t, today, reglages):
    F = lambda r, k: sel(r["fields"].get(k))
    actes = {a["id"]: a["fields"] for a in t["actes"]}
    comp_par, exp_par = collections.defaultdict(list), collections.defaultdict(list)
    for k in t["comp"]:
        for i in k["fields"].get(COMP["candidat"]) or []:
            comp_par[i].append(k["fields"])
    for e in t["exp"]:
        for i in e["fields"].get(EXP["candidat"]) or []:
            exp_par[i].append(e["fields"])
    signes = signes_de_vie(t, today)

    # Deux fiches de même identifiant (improbable) : seule une collision entre fiches publiables
    # compte ; elles sont alors écartées, pas tout le volet candidats.
    refs = collections.Counter(ref_de(r["id"]) for r in t["cand"]
                               if not motif_hors_perimetre(r, signes[r["id"]], today))
    doublons = {x for x, n in refs.items() if n > 1}

    publiables, hors = [], {}
    for r in t["cand"]:
        i, ref = r["id"], ref_de(r["id"])
        s = signes[i]
        motif = motif_hors_perimetre(r, s, today) or (
            "identifiant en double avec une autre fiche (à régler à la main)" if ref in doublons else None)
        if motif:
            hors[ref] = dict(ref=ref, _nom=F(r, C["nom"]), motif=motif)
            continue
        p_req, p_mai = F(r, C["p_req"]) or [], F(r, C["p_mai"]) or []
        pratiques = p_req or p_mai
        s_mai, s_req = F(r, C["s_mai"]) or [], F(r, C["s_req"]) or []
        zones = [zone(z) for z in (F(r, C["zones"]) or [])]
        carte = dict(
            ref=ref, titre=titre(pratiques, s_req), pratiques=pratiques,
            specialites=sorted(set(s_mai) | set(s_req)), experience=F(r, C["experience"]),
            contrat=F(r, C["contrats"]) or [], temps=F(r, C["temps"]) or [], gardes=F(r, C["gardes"]),
            disponibilite=dispo(F(r, C["dispo"]), today), zones=zones,
        )
        competences = [dict(acte=actes.get(a, {}).get(ACTE["nom"]), espece=sel(actes.get(a, {}).get(ACTE["espece"])),
                            famille=sel(actes.get(a, {}).get(ACTE["famille"])), niveau=sel(k.get(COMP["niveau"])))
                       for k in comp_par.get(i, []) for a in (k.get(COMP["actes"]) or [])]
        experiences, structures = [], []
        for e in exp_par.get(i, []):
            experiences.append(dict(poste=e.get(EXP["poste"]), type=sel(e.get(EXP["type"])),
                                    pratiques=sel(e.get(EXP["pratiques"])), duree=e.get(EXP["duree"]),
                                    en_cours=bool(e.get(EXP["en_cours"])), description=e.get(EXP["description"])))
            structures += [e.get(EXP["structure"]), e.get(EXP["ville1"]), e.get(EXP["ville2"])]
        sources = dict(
            profil_ia=nettoie(F(r, C["profil_ia"])), profil_recruteur=nettoie(F(r, C["profil"])),
            competences=competences, experiences=experiences,
            champs=dict(pratiques_maitrisees=p_mai, pratiques_recherchees=p_req,
                        pratiques_optionnelles=F(r, C["p_opt"]) or [], specialites_maitrisees=s_mai,
                        specialites_recherchees=s_req, specialites_optionnelles=F(r, C["s_opt"]) or [],
                        experience=carte["experience"], annees_experience=F(r, C["annees"]),
                        en_poste=F(r, C["en_poste"]), gardes=carte["gardes"],
                        frequence_gardes_toleree=F(r, C["freq_gardes"]), logement_requis=F(r, C["logement"]),
                        internat=F(r, C["internat"]), desv=F(r, C["desv"]),
                        habilitation_sanitaire=F(r, C["habilitation"]), taille_clinique=F(r, C["taille"]),
                        clinique_de_refere=F(r, C["refere"]), groupe_souhaite=F(r, C["groupe"]),
                        precisions_zone=F(r, C["precisions_zone"])),
        )
        interdits = [F(r, C[k]) for k in ("prenom", "nom_famille", "mail", "tel", "ville", "cp", "ecole",
                                          "sortie", "diplome_sup")] + structures
        interdits = sorted({str(x).strip() for x in interdits if x and len(str(x).strip()) >= 2})
        contact = s["dernier_appel"] or s["dernier"]
        visible = carte_affichee(carte, reglages.get(ref, {}))
        cachees = sorted(set(carte["specialites"]) - set(visible["specialites"]))
        # L'empreinte suit tout ce que la relecture doit revoir : sources, carte affichée (hors
        # disponibilité, qui bouge seule avec la date) et termes interdits.
        repere = {k: v for k, v in visible.items() if k not in ("disponibilite", "ref")}
        repere["zones"] = [z["label"] for z in zones]
        publiables.append(dict(carte=carte, _nom=F(r, C["nom"]), _contact=contact.isoformat() if contact else "",
                               empreinte=empreinte([sources, repere, interdits]),
                               dossier=dict(ref=ref, carte_publique={**visible, "zones": [z["label"] for z in zones]},
                                            pastilles_non_affichees=cachees,
                                            sources_validees=sources, interdits=interdits)))
    return publiables, hors


# ---------------------------------------------------------------- diff

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="date du jour (AAAA-MM-JJ), pour rejouer un calcul")
    ap.add_argument("--initialiser", action="store_true", help="autoriser l'absence d'état (première mise en place)")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()

    if not STATE.exists() and PAGE.exists() and not args.initialiser:
        raise SystemExit(f"{STATE.name} absent alors que {PAGE.name} existe : rien n'est fait. Repartir de zéro "
                         "republierait tous les candidats comme nouveaux, sans réglages ni retenus. "
                         "Restaurer l'état depuis l'historique git du dépôt Pages.")
    etat = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"candidats": {}, "retenus": {}}
    publies, retenus, anciens = etat.get("candidats", {}), etat.get("retenus", {}), etat.get("anciens", {})
    # réglages de carte : ceux d'un candidat en ligne, ou d'un candidat qui revient après un retrait
    reglages = {**{r: a.get("ajustements", {}) for r, a in anciens.items()},
                **{r: c.get("ajustements", {}) for r, c in publies.items()}}

    publiables, hors = construire(lire_airtable(), today, reglages)
    par_ref = {p["carte"]["ref"]: p for p in publiables}

    dossiers = WORK / "dossiers"
    shutil.rmtree(dossiers, ignore_errors=True)
    dossiers.mkdir(parents=True)
    for p in publiables:
        (dossiers / f"{p['carte']['ref']}.json").write_text(json.dumps(p["dossier"], ensure_ascii=False, indent=1),
                                                            encoding="utf-8")
    (WORK / "candidats.json").write_text(json.dumps(
        [{**p["carte"], "_nom": p["_nom"], "_contact": p["_contact"], "empreinte": p["empreinte"]} for p in publiables],
        ensure_ascii=False, indent=1), encoding="utf-8")

    todo, ajouts, revues = [], [], []
    for ref, p in sorted(par_ref.items()):
        if ref in retenus:
            continue
        dossier = str(dossiers / f"{ref}.json")
        if ref not in publies:
            todo.append(dict(ref=ref, raison="retour" if ref in anciens else "nouveau", dossier=dossier))
            ajouts.append(dict(ref=ref, _nom=p["_nom"], titre=p["carte"]["titre"],
                               zones=[z["label"] for z in p["carte"]["zones"]]))
            continue
        actuelle = publies[ref].get("description", "")
        pb = alertes(actuelle, p["dossier"]["interdits"])
        if pb:
            # contrôlée avec les termes interdits du jour : à réécrire avant de publier
            todo.append(dict(ref=ref, raison="contrôle", description_actuelle=actuelle, alertes=pb, dossier=dossier))
            revues.append(dict(ref=ref, _nom=p["_nom"], titre=p["carte"]["titre"]))
        elif publies[ref].get("empreinte") != p["empreinte"]:
            todo.append(dict(ref=ref, raison="source modifiée", description_actuelle=actuelle, dossier=dossier))
            revues.append(dict(ref=ref, _nom=p["_nom"], titre=p["carte"]["titre"]))
    retraits = []
    for ref in sorted(publies):
        if ref not in par_ref:
            h = hors.get(ref, dict(ref=ref, _nom=None, motif="fiche supprimée d'Airtable"))
            retraits.append(dict(ref=ref, _nom=h["_nom"], motif=h["motif"]))
    retenus_publiables = [dict(ref=r, _nom=par_ref[r]["_nom"], raison=retenus[r]) for r in sorted(retenus) if r in par_ref]

    diff = dict(date=today.isoformat(), total_publiables=len(publiables), ajouts=ajouts, retraits=retraits,
                revues=revues, retenus=retenus_publiables)
    (WORK / "todo.json").write_text(json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")
    (WORK / "diff.json").write_text(json.dumps(diff, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in ("descriptions.json", "apply.json"):   # restes d'une nuit précédente : ne doivent pas resservir
        (WORK / f).unlink(missing_ok=True)

    print(f"→ {WORK}")
    print(f"   publiables : {len(publiables)} · déjà en ligne : {sum(1 for r in par_ref if r in publies)} · "
          f"retenus : {len(retenus_publiables)}")
    print(f"   à ajouter : {len(ajouts)} · à retirer : {len(retraits)} · à relire : {len(revues)}")
    # Pas de nom ici : cette sortie reste dans le journal de la routine. Les noms sont dans diff.json.
    for x in todo:
        print(f"   {'+' if x['raison'] in ('nouveau', 'retour') else '~'} {x['ref']} — {x['raison']}")
    for r in retraits:
        print(f"   − {r['ref']} — {r['motif']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
