#!/usr/bin/env python3
"""Épingle le périmètre des candidats publiés sur le site (maj-candidats 0.3.0, 20/11/2026).

Cas réel : la nuit du 20/11/2026, la routine a retiré du site une candidate qui cherchait toujours,
avec le motif « a signalé avoir trouvé un poste ». Sa note de candidature disait seulement
« Le 19/11 : relance pour être sûr et savoir si elle a trouvé un poste » : une expression régulière
cherchait « a trouvé » autour des dates des notes, et elle a lu cette question comme une réponse.
Un autre candidat n'a jamais été publié à cause de « relance X et <clinique> : ne sont plus en
recherche », une phrase sur la clinique.

Règle d'Alex du 20/11/2026 : le texte des notes ne sort jamais un candidat. Il sert seulement à
dater le dernier contact, en écartant les relances sans réponse. C'est le champ « Statut Recherche »
qui dit si quelqu'un cherche encore.

Le test appelle signes_de_vie() et motif_hors_perimetre() sur une base simulée (aucun appel
réseau).

    python3 tests/maj_candidats_perimetre.test.py
"""
import datetime as dt
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, os.pardir, "remote-skills", "maj-candidats", "scripts")

# paths.py exige un dossier de site (offres.html + index.html) et crée le dossier de travail
site, work = tempfile.mkdtemp(), tempfile.mkdtemp()
for nom in ("offres.html", "index.html"):
    open(os.path.join(site, nom), "w").close()
os.environ["SARECRUTE_SITE"], os.environ["MAJ_CANDIDATS_WORK"] = site, work
sys.path.insert(0, SCRIPTS)
spec = importlib.util.spec_from_file_location("fetch_candidats", os.path.join(SCRIPTS, "fetch_candidats.py"))
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)
C, K, M = fc.C, fc.K, fc.M

ok = fail = 0


def check(label, got, want):
    global ok, fail
    if got == want:
        ok += 1
        print("  ok    %s" % label)
    else:
        fail += 1
        print("  ÉCHEC %s\n        attendu : %r\n        obtenu  : %r" % (label, want, got))


TODAY = dt.date(2026, 11, 20)
TRANSCRIPT = "Compte rendu d'appel."   # sans date : le début des transcripts est lu comme des notes


def candidat(rid, notes="", statut=fc.ACTIF, cree="2026-09-02T07:42:22.000Z"):
    return {"id": rid, "createdTime": cree, "fields": {
        C["nom"]: rid, C["statut"]: statut, C["cree"]: cree, C["notes"]: notes,
        C["transcripts"]: TRANSCRIPT, C["zones"]: ["44 - Loire-Atlantique"]}}


def candidature(rid, cand, notes, statut="Candidat postulé", cree="2026-09-02T07:42:31.000Z"):
    return {"id": rid, "fields": {K["candidat"]: [cand], K["statut"]: statut, K["cree"]: cree, K["notes"]: notes}}


# 1. Le cas du 20/11 : réponse le 02/10, puis deux relances dont une question « a-t-elle trouvé ».
QUESTION = ("Le 15/09 : relance léo pas de réponse\n"
            "Le 30/09 : relance : se tourne peut être pas vers la suisse car problème perso\n"
            "Le 19/11 : relance pour être sur et savoir si elle a trouvé un poste\n"
            "Le 20/11 : tentative d'appel sans succès cette semaine, je réessayerai la semaine prochaine\n")
REPONSE = ("Appel le 02/09/26\n\n"
           "Le 02/10/26 : Bonjour Sarah, je suis vraiment navrée de ne pas être revenue vers toi plus tôt, "
           "je jongle malheureusement avec des problèmes qui occupent tout mon temps. Je te remercie pour "
           "tes relances et je te prie de m'excuser pour ma réponse tardive. Bonne journée\n")
# 2. Une phrase sur la clinique (« ne sont plus en recherche »), pas sur le candidat.
CLINIQUE = ("Le 28/09 : clinique absente jusque le 29/09\n"
            "Le 07/10 : relance candidat et clinique\n"
            "Le 12/10 : ne sont plus en recherche\n")
# 3. Un candidat qui écrit lui-même avoir trouvé, mais dont le statut n'a pas été changé : il reste
#    publiable (le statut décide). La recruteuse change le statut, et il sort.
TROUVE = "Le 18/11/26 : Bonjour, j'ai trouvé un poste, merci pour tout !\n"

t = dict(
    cand=[candidat("recQuestion00001", notes=REPONSE), candidat("recClinique00002"),
          candidat("recTrouve0000003", notes=TROUVE),
          candidat("recPasRecherche4", notes=TROUVE, statut="Pas en recherche"),
          candidat("recVieux00000005", notes="Le 02/06/26 : Bonjour, je cherche toujours\n",
                   cree="2026-05-01T08:00:00.000Z")],
    candidatures=[candidature("recK1", "recQuestion00001", QUESTION),
                  candidature("recK2", "recClinique00002", CLINIQUE, statut="Nurturing")],
    comm=[], posts=[], comp=[], actes=[], exp=[])
s = fc.signes_de_vie(t, TODAY)
motif = {r["id"]: fc.motif_hors_perimetre(r, s[r["id"]], TODAY) for r in t["cand"]}

print("Question « savoir si elle a trouvé » (cas du 20/11/2026)")
check("reste publiable", motif["recQuestion00001"], None)
check("dernier contact = sa réponse du 02/10, pas les relances", s["recQuestion00001"]["dernier"], dt.date(2026, 10, 2))
check("plus aucune clé « trouve » dans les signes de vie", "trouve" in s["recQuestion00001"], False)

print("Phrase sur une clinique « ne sont plus en recherche »")
check("reste publiable", motif["recClinique00002"], None)

print("Le statut décide, pas le texte")
check("« j'ai trouvé » dans les notes, statut actif : publiable", motif["recTrouve0000003"], None)
check("même note, statut « Pas en recherche » : retiré", motif["recPasRecherche4"], "statut « Pas en recherche »")

print("La date du dernier contact vient toujours des notes")
check("contact du 02/06 : plus de 3 mois", motif["recVieux00000005"], "pas de signe de vie depuis plus de 3 mois")
check("les relances ne comptent pas comme contact",
      [sorte for _, sorte in fc.entrees_datees(QUESTION, dt.date(2026, 9, 2), TODAY)], ["out"] * 4)

print("Aucun motif tiré du texte")
check("aucun motif « a trouvé » possible",
      any("trouv" in (m or "") for m in motif.values()), False)
check("plus de constante FOUND dans le script", hasattr(fc, "FOUND"), False)

print("\n%d ok, %d échec(s)" % (ok, fail))
sys.exit(1 if fail else 0)
