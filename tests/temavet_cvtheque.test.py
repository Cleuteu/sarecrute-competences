#!/usr/bin/env python3
"""Épingle la source CV-thèque TÉMAVet (scrape-veto 0.17.0, 28/10/2026).

Deux morceaux :
  - temavet_cvtheque.py lit une fiche (HTML du <main>, tel que l'exporte temavet_cvtheque.js) et en
    tire le squelette : identité remise en casse, contact, date, zones traduites, pratiques ;
  - airtable_push.py traite un profil comme un document tenu à jour : sa nouvelle version (date plus
    récente, ou texte changé) REMPLACE l'ancienne au lieu de s'empiler.

La fiche est synthétique (le dépôt est public : aucune donnée de candidat ici), mais reprend la
structure réelle de la page relevée le 28/10/2026. Aucun appel réseau.

    python3 tests/temavet_cvtheque.test.py
"""
import importlib.util, io, json, os, sys, tempfile, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, os.pardir, "remote-skills", "scrape-veto", "scripts")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(SCRIPTS, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tv, ap = charger("temavet_cvtheque"), charger("airtable_push")
ok = fail = 0


def check(label, got, want):
    global ok, fail
    if got == want:
        ok += 1
        print("  ok    %s" % label)
    else:
        fail += 1
        print("  ÉCHEC %s\n        attendu : %r\n        obtenu  : %r" % (label, want, got))


def case(lab, *vals):
    v = "".join('<div class="mr-2"> %s </div>' % x for x in vals)
    return ('<div class="mb-6"><div class="ml-[85px] flex flex-row"><div class="text-sm uppercase font-medium '
            'text-gray-500 w-[200px] mb-2">%s</div><div class="text-sm pl-10 font-semibold text-sm">%s</div></div></div>'
            % (lab, v))


def sec(titre):
    return '<div class="text-md font-medium text-black-500 leading-6 decoration-black-500 mb-2">%s</div>' % titre


def bloc(titre, org, dates, lieu, desc):
    return ('<div class="flex flex-col"><h2 class="font-semibold text-md mr-2 capitalize">%s</h2><p class="italic">%s</p>'
            '<p class="text-xs">%s</p><p class="text-sm">%s</p><p class="text-sm text-gray-500">%s</p></div>'
            % (titre, org, dates, lieu, desc))


def fiche(nom="Madame JEANNE EXEMPLE", tel="0600000000 / 0600000000", maj="16/10/2026", activite=("Canine (+/- NAC)", "Mixte")):
    zones = ["Bretagne", "Gironde (33)", "Ajaccio (20000)", "Bastia (20200)", "Saint-Denis (97400)", "Guadeloupe", "Maroc"]
    return "".join([
        '<div> Informations du candidat </div><button> Télécharger le CV </button>',
        '<h2 class="font-semibold text-lg"> Prise de contact </h2>',
        '<div class="flex flex-row mb-1 text-base font-semibold"> %s </div>' % nom,
        '<div class="flex flex-row items-center mb-1"><span>Jeanne.Exemple@example.org</span></div>',
        '<div class="flex flex-row mb-1"> %s </div>' % tel,
        '<div class="flex flex-row items-center mb-1"> Dernière mise à jour : %s </div>' % maj,
        '<div class="text-sm font-bold">Zones de recherche :</div>',
        "".join('<div class="mr-4 mb-2 bg-vjcyan-100 py-1 px-2"> %s </div>' % z for z in zones),
        sec("A propos"), sec("Statut et recherche"),
        case("Statut actuel", "Vétérinaire diplômé UE"), case("Disponibilité", "Dès maintenant"),
        case("Poste recherché", "Praticien"), case("Temps de travail", "Temps complet"),
        case("Activité du poste (si praticien)", *activite),
        sec("Expériences professionnelles"), sec("Expériences"), sec("Postes"),
        bloc("Vétérinaire canin", "Clinique des Exemples", "2021-09-01 -", "Exempleville", "Consultations et chirurgie"),
        sec("Stages"),
        case("Années d'expérience en tant que praticien", "≥ 2 ans et < 5 ans d'expérience"),
        sec("Diplômes et formations"), case("Année de sortie", "2021"),
        sec("Spécialisations cliniques"),
        '<div><h2 class="font-semibold text-md">CES (Certificat d\'Etudes Supérieures)</h2><p class="text-xs">2024</p>'
        '<p class="text-sm">ENVT (Toulouse)</p><p class="text-sm text-gray-500">CES de chirurgie</p></div>',
        sec("Compétences"), case("Compétences spécialisées cliniques", "Urgences / Soins intensifs", "Dermatologie"),
        sec("Informations complémentaires"),
    ])


VOCAB = tv.charger_vocab()

print("\nlire_fiche — identité, contact, date")
f = tv.lire_fiche(fiche())
check("date de mise à jour en ISO", f["maj"], "2026-10-16")
check("civilité séparée du nom", (f["civilite"], f["nom_complet"]), ("Madame", "JEANNE EXEMPLE"))
check("mail en minuscules", f["mail"], "jeanne.exemple@example.org")
check("deux fois le même numéro → un seul", f["tel"], "0600000000")
check("rien de l'interface dans le texte (bouton, fenêtre de contact)",
      any(x in f["texte"] for x in ("Télécharger", "Prise de contact", "Informations du candidat")), False)
check("un bloc d'expérience garde le titre de sa section", "\nPOSTES\n- Vétérinaire canin · Clinique des Exemples" in f["texte"], True)
check("une section vide n'apparaît pas (les années ne passent pas sous « Stages »)", "STAGES" in f["texte"], False)
check("une case se lit « libellé : valeurs »",
      "Activité du poste (si praticien) : Canine (+/- NAC), Mixte" in f["texte"], True)
g = tv.lire_fiche(fiche(nom="", tel="0611111111"))
check("sans nom : le contact se lit quand même", (g["mail"], g["tel"]), ("jeanne.exemple@example.org", "0611111111"))

print("\nprenom_nom — les capitales désignent le nom, puis reviennent en casse normale")
check("tout en capitales", tv.prenom_nom("JEANNE EXEMPLE"), ("Jeanne", "Exemple"))
check("prénom composé, nom composé", tv.prenom_nom("Jean-Paul DUPONT-MARTIN"), ("Jean-Paul", "Dupont-Martin"))
check("deux prénoms avant le nom en capitales", tv.prenom_nom("Anne Sophie EXEMPLE"), ("Anne Sophie", "Exemple"))
check("sans repère de casse : le premier mot est le prénom", tv.prenom_nom("Louise Martin"), ("Louise", "Martin"))
check("un nom en capitales n'est pas fusionnable, remis en casse il l'est",
      (ap.auteur_key("JEANNE", "EXEMPLE"), ap.auteur_key(*tv.prenom_nom("JEANNE EXEMPLE"))), ("", "jeanne exemple"))

print("\nzones_vocab — régions, départements, villes, DOM")
zv, hors = tv.zones_vocab(f["zones"], VOCAB)
check("une région donne ses départements", all(d in zv for d in VOCAB["macro_regions"]["Bretagne"]), True)
check("département entre parenthèses", "33 - Gironde" in zv, True)
check("Corse : le code postal tranche (200xx / 202xx)", ("20 - Corse-du-Sud" in zv, "20 - Haute-Corse" in zv), (True, True))
check("DOM par code postal et par nom", ("974 - La Réunion" in zv, "971 - Guadeloupe" in zv), (True, True))
check("hors vocabulaire : gardé à part, jamais forcé", hors, ["Maroc"])
check("aucune valeur hors du vocabulaire", [z for z in zv if z not in VOCAB["zones_de_recherche"]], [])
check("texte libre : les villes sans leur code postal", tv.zone_texte(["Nice (06000)", "Nice (06100)", "Var (83)"]), "Nice, Var (83)")

print("\npratiques — chaque activité cochée est une alternative")
check("canine ou mixte : canine requise, bovins et NAC optionnels",
      tv.pratiques(["Canine (+/- NAC)", "Mixte"]), (["Canine"], ["Bovins", "NAC"]))
check("mixte ou rurale : bovins requis", tv.pratiques(["Mixte", "Rurale 100%"]), (["Bovins"], ["Canine"]))
check("activité non traduite : rien de deviné", tv.pratiques(["Autre", "Faune sauvage"]), ([], []))

print("\nsquelette")
sq = tv.squelette(tv.lire_fiche(fiche(nom="")), 900001, "https://job.temavet.fr/users/veterinaire/900001",
                  "recTEMAVETxxxxxxx", VOCAB, carte_nom="Jeanne EXEMPLE")
fl = sq["fields"]
check("sans nom sur la fiche : celui de la carte", (fl.get("Prénom"), fl.get("Nom")), ("Jeanne", "Exemple"))
check("post candidat", (fl["Type de post"], fl["Type d'entrée"]), ("Vétérinaire cherche poste", "Post"))
check("temps de travail traduit", fl["Type de temps de travail"], ["Temps plein"])
check("compétence déclarée → spécialité OPTIONNELLE, hors vocab ignorée", fl["Spécialités optionnelles"], ["Urgences"])
check("carte sans nom : « Praticien » n'est pas un nom", tv.nom_de_carte(["Praticien", "|", "Temps complet"]), "")
check("carte avec nom", tv.nom_de_carte(["Jeanne EXEMPLE", "Praticien"]), "Jeanne EXEMPLE")
sans_nom = tv.squelette(tv.lire_fiche(fiche(nom="")), 900002, "https://job.temavet.fr/users/veterinaire/900002",
                        "recTEMAVETxxxxxxx", VOCAB, carte_nom="")["fields"]
check("profil sans nom : clé figée sur le n°, pas de Nom inventé",
      (sans_nom.get("auteur_key"), "Nom" in sans_nom), ("temavet#900002", False))
check("la clé figée est respectée par le push", ap.effective_key(sans_nom), "temavet#900002")
check("un profil nommé n'a pas de clé (le push la calcule)", "auteur_key" in fl, False)
check("rien de jugé dans le squelette",
      [k for k in ("Expérience", "Statuts contractuels", "Date de disponibilité", "Contrat court", "Spécialités requises") if k in fl], [])

print("\nairtable_push — un profil se remplace, il ne s'empile pas")
CANAL_TV, CANAL_FB = "recTEMAVETxxxxxxx", "recFBxxxxxxxxxxxx"
CANAUX = {CANAL_TV: "CV-thèque TÉMAVet", CANAL_FB: "We need you"}
URL = "https://job.temavet.fr/users/veterinaire/900001"
CORPS = tv.lire_fiche(fiche())["texte"]
CORPS2 = CORPS.replace("Dès maintenant", "Janvier 2027")
EXISTANT = {"id": "recJEANNExxxxxxxx", "fields": {
    "Prénom": "Jeanne", "Nom": "Exemple", "Date du post": "2026-09-01", "Lien du post": URL,
    "Type d'entrée": "Post", "Type de post": "Vétérinaire cherche poste", "Canaux": [CANAL_TV],
    "Expérience": "Autonome", "Contenu complet": "[2026-09-01] %s · CV-thèque TÉMAVet\n%s" % (URL, CORPS)}}


def entree(corps, date):
    return {"fields": {"Prénom": "Jeanne", "Nom": "Exemple", "Date du post": date, "Lien du post": URL,
                       "Type d'entrée": "Post", "Type de post": "Vétérinaire cherche poste",
                       "Canaux": [CANAL_TV], "Contenu complet": corps}}


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
    ap.fetch_all = lambda token: json.loads(json.dumps(existing))
    ap.urllib.request.urlopen = fake_urlopen
    os.environ["AIRTABLE_API_KEY"] = "test"
    sys.argv = ["airtable_push.py", fh.name]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        ap.main()
    os.unlink(fh.name)
    return out.getvalue(), sent


s_old = {"date": "2026-09-01", "link": URL, "body": CORPS}
s_new = {"date": "2026-10-16", "link": URL, "body": CORPS}
check("identité de révision : le n° seul, toutes dates", (ap.rev_key(s_old), ap.rev_key(s_new)),
      (("profil", "900001"), ("profil", "900001")))
check("même texte, autre date : deux signatures", ap.sec_sig(s_old) != ap.sec_sig(s_new), True)

out, sent = run([entree(CORPS, "2026-10-16")], [EXISTANT])
patches = [s for s in sent if s[0] == "PATCH"]
contenu = patches[0][2]["Contenu complet"] if patches else ""
check("profil revalidé : un PATCH sur l'enregistrement existant, aucune création",
      ([(m, r) for m, r, _ in patches], [s for s in sent if s[0] == "POST"]), ([("PATCH", "recJEANNExxxxxxxx")], []))
check("une seule section, à la nouvelle date", (contenu.count("──────────"), contenu.startswith("[2026-10-16] " + URL)), (0, True))
check("Date du post avance", patches[0][2].get("Date du post") if patches else None, "2026-10-16")
check("ce qui a été jugé reste (Expérience)", patches[0][2].get("Expérience") if patches else None, "Autonome")
check("le résumé compte la révision", "dont annonces révisées: 1" in out, True)

out, sent = run([entree(CORPS2, "2026-10-16")], [EXISTANT])
contenu = sent[0][2]["Contenu complet"] if sent else ""
check("profil modifié : la nouvelle version remplace l'ancienne",
      ("Janvier 2027" in contenu, "Dès maintenant" in contenu), (True, False))

out, sent = run([entree(CORPS, "2026-09-01")], [EXISTANT])
check("profil inchangé : rien d'écrit", sent, [])

LIEN_FB = "https://www.facebook.com/groups/318289868699508/posts/999/"
AVEC_FB = json.loads(json.dumps(EXISTANT))
AVEC_FB["fields"]["Canaux"] = [CANAL_TV, CANAL_FB]
AVEC_FB["fields"]["Contenu complet"] = ("[2026-09-20] %s · We need you\nJe cherche un poste en canine.\n\n──────────\n\n"
                                        "[2026-09-01] %s · CV-thèque TÉMAVet\n%s" % (LIEN_FB, URL, CORPS))
out, sent = run([entree(CORPS, "2026-10-16")], [AVEC_FB])
contenu = sent[0][2]["Contenu complet"] if sent else ""
check("le post Facebook de la même personne reste, le profil seul est remplacé",
      (contenu.count("──────────"), "Je cherche un poste en canine." in contenu, contenu.count(URL)), (1, True, 1))

print("\n%d ok, %d échec(s)" % (ok, fail))
sys.exit(1 if fail else 0)
