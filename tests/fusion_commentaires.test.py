#!/usr/bin/env python3
"""Épingle la fusion « un commentaire enrichit l'annonce » (airtable_push.py, 20/08/2026).

Cas réel : Sabine Marcillaud avait 3 enregistrements pour 1 seule offre — son annonce
du 15/08 (Villeneuve d'Aveyron), plus deux « Aveyron si ça t'intéresse ! » posés sous
deux posts de candidates les 17 et 19/08. Les commentaires fusionnaient entre eux mais
jamais avec le post, dans un espace de clés séparé.

Tous les pièges testés ici sont SILENCIEUX : ils ne lèvent aucune erreur, ils écrivent
juste des données fausses (ou en double) en base.

    python3 tests/fusion_commentaires.test.py
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "plugins", "sarecrute-admin", "skills",
                      "scrape-veto", "scripts", "airtable_push.py")
spec = importlib.util.spec_from_file_location("airtable_push", SCRIPT)
ap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ap)

ok = fail = 0


def check(label, got, want):
    global ok, fail
    if got == want:
        ok += 1
        print("  ok    %s" % label)
    else:
        fail += 1
        print("  ÉCHEC %s\n        attendu : %r\n        obtenu  : %r" % (label, want, got))


POST = {"Prénom": "Sabine", "Nom": "Marcillaud", "Type d'entrée": "Post",
        "Date du post": "2026-08-15", "Type de post": "Clinique cherche vétérinaire",
        "Pratiques": ["Canine", "Bovins"], "Statuts contractuels": ["CDI", "Collaboration libérale"],
        "Contenu complet": "URGENT Véto mixte recherché·e à Villeneuve d'Aveyron"}
# Le commentaire hérite du post commenté (une candidate en CDD prophylaxie) : ces
# valeurs décrivent la CANDIDATE, pas l'offre de Sabine — elles ne doivent rien écraser.
COM = {"Prénom": "Sabine", "Nom": "Marcillaud", "Type d'entrée": "Commentaire",
       "Date du post": "2026-08-19", "Type de post": "Clinique cherche vétérinaire",
       "Expérience": "Débutant", "Statuts contractuels": ["Prophylaxie", "CDD"],
       "Post source": "Membre anonyme - #prophylaxie #décembre2026 Bonjour",
       "Contenu complet": "Aveyron si ça t intéresse !\n\n━━━ Post commenté — Membre anonyme (2026-08-19) ━━━\n#prophylaxie #décembre2026 Bonjour,"}

print("\ntarget_rank — la relance rejoint l'ANNONCE, pas le dernier commentaire")
check("un post l'emporte sur un commentaire plus récent",
      ap.target_rank(POST) > ap.target_rank(COM), True)
check("entre deux posts, le plus récent gagne",
      ap.target_rank(dict(POST, **{"Date du post": "2026-08-20"})) > ap.target_rank(POST), True)

print("\nmerged_scalars — le commentaire COMPLÈTE l'annonce, il ne la remplace pas")
sc = ap.merged_scalars([COM, POST])
check("Type d'entrée reste « Post » malgré un commentaire plus récent", sc["Type d'entrée"], "Post")
check("Post source vidé (il ne décrit que le parent d'un commentaire)", sc["Post source"], "")
check("Expérience absente de l'annonce, comblée par le commentaire", sc["Expérience"], "Débutant")
check("Statuts de l'annonce NON écrasés par ceux hérités du post commenté",
      sc["Statuts contractuels"], ["CDI", "Collaboration libérale"])
check("Date du post = activité la plus récente (fraîcheur en prospection)",
      sc["Date du post"], "2026-08-19")
check("une valeur vide ne chasse pas une valeur pleine",
      ap.merged_scalars([dict(POST, **{"Date du post": "2026-08-20", "Pratiques": []}), POST])["Pratiques"],
      ["Canine", "Bovins"])
check("sans aucun post, l'enregistrement reste un Commentaire",
      ap.merged_scalars([COM])["Type d'entrée"], "Commentaire")

print("\nmark_comment — reconnaissable dans la description, et idempotent")
marked = ap.mark_comment(COM["Contenu complet"], COM)
check("la 1re ligne dit qui commente et sous quel post",
      marked.split("\n")[0],
      "💬 COMMENTAIRE de Sabine Marcillaud sous le post de Membre anonyme"
      " — ce qui suit « Post commenté » n'est pas de Sabine Marcillaud.")
check("le texte du commentaire est conservé intact",
      "Aveyron si ça t intéresse !" in marked, True)
check("re-marquer ne double pas la ligne", ap.mark_comment(marked, COM), marked)

print("\nsec_sig — insensible au marqueur (sinon doublon à chaque re-scrape)")
nu = {"date": "2026-08-19", "body": COM["Contenu complet"]}      # section d'avant le 20/08
neuf = {"date": "2026-08-19", "body": marked}                    # même commentaire, marqué
check("une section pré-20/08 et sa version marquée ont la MÊME signature",
      ap.sec_sig(nu), ap.sec_sig(neuf))
check("deux commentaires différents gardent des signatures différentes",
      ap.sec_sig(neuf) != ap.sec_sig({"date": "2026-08-17", "body": marked}), True)

print("\n%d ok, %d échec(s)" % (ok, fail))
sys.exit(1 if fail else 0)
