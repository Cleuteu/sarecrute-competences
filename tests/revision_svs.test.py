#!/usr/bin/env python3
"""Épingle la révision des annonces SVS dans airtable_push.py (0.16.5, 28/10/2026).

Cas réel : les annonces 5537 (Am Sonnenberg) et 5521 (Herkules : taux passé de 30-80 %
à 50-100 %) avaient été modifiées sur le portail au-delà des 80 premiers caractères, à
date de publication inchangée. svs_portail.py les donnait « modifiées », le push les
comptait « ignorées (déjà en base) » — rien n'était écrit, et rien ne le signalait.

Le test fait tourner main() contre une base simulée (aucun appel réseau) et lit ce qui
aurait été envoyé à Airtable.

    python3 tests/revision_svs.test.py
"""
import importlib.util, io, json, os, sys, tempfile, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "remote-skills",
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


CANAL_SVS, CANAL_FB = "recSVSxxxxxxxxxxx", "recFBxxxxxxxxxxxx"
CANAUX = {CANAL_SVS: "Portail emploi SVS", CANAL_FB: "We need you"}
URL = "https://www.gstsvs.ch/fr/portail-demplois/marche-de-lemploi/annonce/5521"
DEBUT = ("Kleintierpraxis Herkules sucht per sofort oder nach Vereinbarung eine:n "
         "Tierärztin / Tierarzt für unser motiviertes Team in Bern. ")
AVANT = DEBUT + "Pensum 30-80 %. Moderne Infrastruktur, Röntgen, Ultraschall."
APRES = DEBUT + "Pensum 50-100 %. Moderne Infrastruktur, Röntgen, Ultraschall."
CLE = "kleintierpraxis herkules#tierarzt-bern"

EXISTANT_SVS = {"id": "recHERKULESxxxxxx", "fields": {
    "Prénom": "Anna", "Nom": "Muster", "Date du post": "2026-10-20", "Lien du post": URL,
    "Type d'entrée": "Post", "Type de post": "Clinique cherche vétérinaire",
    "Nom de la clinique": "Kleintierpraxis Herkules", "auteur_key": CLE, "Canaux": [CANAL_SVS],
    "Contenu complet": "[2026-10-20] %s · Portail emploi SVS\n%s" % (URL, AVANT)}}


def svs_in(corps, date="2026-10-20", ttt=("Temps partiel", "Temps plein")):
    return {"fields": {
        "Prénom": "Anna", "Nom": "Muster", "Date du post": date, "Lien du post": URL,
        "Type d'entrée": "Post", "Type de post": "Clinique cherche vétérinaire",
        "Nom de la clinique": "Kleintierpraxis Herkules", "auteur_key": CLE,
        "Canaux": [CANAL_SVS], "Type de temps de travail": list(ttt), "Contenu complet": corps}}


def run(records, existing):
    """main() sans réseau : renvoie (sortie, [(méthode, recId, fields)])."""
    sent = []

    class Resp:
        def __init__(self, body): self.body = body
        def read(self): return self.body

    def fake_urlopen(req):
        body = json.loads(req.data.decode()) if req.data else {}
        rid = req.full_url.rsplit("/", 1)[-1] if req.get_method() == "PATCH" else None
        if req.get_method() == "POST":
            for r in body["records"]:
                sent.append(("POST", None, r["fields"]))
            return Resp(json.dumps({"records": body["records"]}).encode())
        sent.append((req.get_method(), rid, body.get("fields")))
        return Resp(b"{}")

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(records, fh)
    ap.fetch_canaux = lambda token: CANAUX
    ap.fetch_all = lambda token: json.loads(json.dumps(existing))   # copie : main() ne doit rien muter
    ap.urllib.request.urlopen = fake_urlopen
    os.environ["AIRTABLE_API_KEY"] = "test"
    sys.argv = ["airtable_push.py", fh.name]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        ap.main()
    os.unlink(fh.name)
    return out.getvalue(), sent


print("\nsec_sig — signature inchangée pour Facebook, n° + texte intégral pour SVS")
fb = {"date": "2026-10-20", "link": "https://www.facebook.com/groups/1/posts/2/", "body": AVANT}
check("Facebook : date + 80 caractères (comme avant la 0.16.5)",
      ap.sec_sig(fb), ("2026-10-20", AVANT.lower()[:80]))
check("section sans lien (appel historique) : toujours accepté",
      ap.sec_sig({"date": "2026-10-20", "body": AVANT}), ("2026-10-20", AVANT.lower()[:80]))
s1 = {"date": "2026-10-20", "link": URL, "body": AVANT}
s2 = {"date": "2026-10-20", "link": URL, "body": APRES}
check("SVS : deux versions au même début de texte ont deux signatures", ap.sec_sig(s1) != ap.sec_sig(s2), True)
check("SVS : même identité de révision (date, n°)", (ap.rev_key(s1), ap.rev_key(s2)),
      (("2026-10-20", "5521"), ("2026-10-20", "5521")))
check("Facebook : pas d'identité de révision", ap.rev_key(fb), None)

print("\nannonce révisée (Herkules 5521) : mise à jour, plus « ignorée »")
out, sent = run([svs_in(APRES, ttt=("Temps partiel", "Temps plein"))], [EXISTANT_SVS])
patches = [s for s in sent if s[0] == "PATCH"]
check("un seul PATCH, sur l'enregistrement existant", [(m, r) for m, r, _ in patches],
      [("PATCH", "recHERKULESxxxxxx")])
check("aucune création (pas de doublon)", [s for s in sent if s[0] == "POST"], [])
contenu = patches[0][2]["Contenu complet"] if patches else ""
check("le nouveau texte est en base", "Pensum 50-100 %" in contenu, True)
check("l'ancienne version a disparu (remplacée, pas empilée)", "Pensum 30-80 %" in contenu, False)
check("une seule section", contenu.count("──────────"), 0)
check("l'en-tête garde lien et canal",
      contenu.startswith("[2026-10-20] %s · Portail emploi SVS\n" % URL), True)
check("les scalaires suivent la révision",
      patches[0][2].get("Type de temps de travail") if patches else None, ["Temps partiel", "Temps plein"])
check("le résumé compte la révision", "dont annonces révisées: 1" in out, True)

print("\nannonce inchangée : toujours ignorée (idempotence)")
out, sent = run([svs_in(AVANT)], [EXISTANT_SVS])
check("rien d'écrit", sent, [])
check("comptée « ignorée »", "ignorés (déjà en base): 1" in out, True)

print("\nannonce republiée à une AUTRE date : empilée comme avant (historique conservé)")
out, sent = run([svs_in(APRES, date="2026-10-27")], [EXISTANT_SVS])
contenu = sent[0][2]["Contenu complet"] if sent else ""
check("les deux versions restent, la plus récente en haut",
      (contenu.find("Pensum 50-100 %") < contenu.find("Pensum 30-80 %"), "Pensum 30-80 %" in contenu),
      (True, True))

print("\nFacebook : aucun changement de comportement")
LIEN_FB = "https://www.facebook.com/groups/318289868699508/posts/999/"
CORPS_FB = "Bonjour, nous recherchons un vétérinaire canin pour notre clinique de Poitiers, CDI temps plein. " * 2
EXISTANT_FB = {"id": "recLEAxxxxxxxxxxx", "fields": {
    "Prénom": "Léa", "Nom": "Martin", "Date du post": "2026-10-26", "Lien du post": LIEN_FB,
    "Type d'entrée": "Post", "Type de post": "Vétérinaire cherche poste", "Canaux": [CANAL_FB],
    "Contenu complet": "[2026-10-26] %s · We need you\n%s" % (LIEN_FB, CORPS_FB)}}
fb_in = {"fields": {"Prénom": "Léa", "Nom": "Martin", "Date du post": "2026-10-26", "Lien du post": LIEN_FB,
                    "Type d'entrée": "Post", "Type de post": "Vétérinaire cherche poste",
                    "Canaux": [CANAL_FB], "Contenu complet": CORPS_FB + " Merci de me contacter en MP."}}
out, sent = run([fb_in], [EXISTANT_FB])
check("post re-capté, texte allongé après 80 caractères : ignoré, pas de doublon", sent, [])

# Deux commentaires de la même personne, sous le même post, le même jour : même lien.
COM_A = "Je suis intéressée, je vous envoie mon CV en message privé dès ce soir."
COM_B = "Petite précision : je suis disponible à partir de janvier, en CDD comme en CDI."
EXISTANT_COM = {"id": "recCOMxxxxxxxxxxx", "fields": {
    "Prénom": "Julie", "Nom": "Bernard", "Date du post": "2026-10-26", "Lien du post": LIEN_FB,
    "Type d'entrée": "Commentaire", "Type de post": "Vétérinaire cherche poste", "Canaux": [CANAL_FB],
    "Contenu complet": "[2026-10-26] %s · We need you\n%s" % (LIEN_FB, COM_A)}}
com_in = {"fields": {"Prénom": "Julie", "Nom": "Bernard", "Date du post": "2026-10-26", "Lien du post": LIEN_FB,
                     "Type d'entrée": "Commentaire", "Type de post": "Vétérinaire cherche poste",
                     "Post source": "Clinique X - annonce", "Canaux": [CANAL_FB], "Contenu complet": COM_B}}
out, sent = run([com_in], [EXISTANT_COM])
contenu = sent[0][2]["Contenu complet"] if sent else ""
check("2e commentaire, même lien, même jour : empilé, le 1er n'est PAS remplacé",
      (COM_A in contenu, COM_B in contenu), (True, True))
check("aucune révision comptée côté Facebook", "dont annonces révisées: 0" in out, True)

print("\n%d ok, %d échec(s)" % (ok, fail))
sys.exit(1 if fail else 0)
