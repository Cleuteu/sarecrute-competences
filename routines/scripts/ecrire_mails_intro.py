#!/usr/bin/env python3
"""Écrit les mails d'intro rédigés par la routine dans « Mail intro proposé » des posts du lot.

Usage :
  python3 ecrire_mails_intro.py dossier.json mails.json [--dry-run]

  dossier.json : sortie de cliniques_a_contacter.py --dossier-mails (les posts du lot en cours sans mail).
  mails.json   : {"recXXXXXXXXXXXXXX": "corps complet du mail, salutation et signature comprises", ...}

C'est le seul endroit qui écrit ce champ. La routine rédige, ce script vérifie puis écrit ; un mail
refusé n'empêche pas les autres. Garde-fous, dans l'ordre :
  * le post est dans le dossier (on n'écrit jamais sur un post que le script d'attribution n'a pas servi) ;
  * texte non vide, 300 à 3 000 caractères, qui commence par « Bonjour » ou « Guten Tag » ;
  * aucun montant (€, CHF), aucun pourcentage de remise ou de tarif (un taux d'activité repris de
    l'annonce, « 60 à 80 % », est permis), aucune promesse de délai chiffrée, aucune
    mention « prise de poste effective » / « Stellenantritt » (décisions d'Alex, 18/09/2026 : pas de prix
    dans le mail d'intro ; le « au succès » se dit « si nous ne plaçons pas de vétérinaire, vous ne nous
    devez rien », jamais « dus à la prise de poste ») ;
  * la signature porte le nom de la recruteuse attributaire, et personne d'autre ;
  * « Vetcoop » apparaît si et seulement si le post est marqué membre_vetcoop dans le dossier ;
  * relecture du post juste avant d'écrire : « Mail intro proposé » toujours vide, toujours attribué à la
    même recruteuse, ni archivé ni converti (la recruteuse a pu avancer entre les deux étapes).
Sortie : rapport sur stdout. Code 0 si tout est écrit, 2 si au moins un mail a été refusé, 1 sur erreur d'API.
"""
import os, sys, json, re, time, urllib.request, urllib.parse

BASE = "appP0W2ISytaNyAhG"
T_POSTS = "Posts scrappés"
F_MAIL = "fldrOglkyBQ6grgGo"        # Mail intro proposé
F_ATTRIBUE_A = "fld1F3kcHSc4j4i0M"  # Attribué à
F_ARCHIVE = "fldxWMqDIu4hd7Ygc"     # Archivé
F_OFFRE = "fld6jPvoQT9UPs3Kz"       # Offre d'emploi
F_NUMERO = "fldvt7wDBCKynWQxD"

args = [a for a in sys.argv[1:] if not a.startswith("--")]
DRY = "--dry-run" in sys.argv
if len(args) != 2:
    sys.exit(__doc__)
dossier = {d["post_id"]: d for d in json.load(open(args[0]))}
mails = json.load(open(args[1]))
KEY = os.environ.get("AIRTABLE_API_KEY")
if not KEY:
    sys.exit("AIRTABLE_API_KEY absente de l'environnement : rien n'est lu ni écrit. Arrêt.")
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

INTERDITS = [
    (re.compile(r"€|\bCHF\b|\beuros?\b|\bfrancs?\b", re.I), "montant ou devise"),
    # un taux d'activité (« 60 à 80 % ») vient de l'annonce et est permis ; une remise ou un tarif en % ne le sont pas
    (re.compile(r"(?<!\d)[−–-]\s?\d+\s?%|\d+\s?%\s*(?:de\s+)?(?:réduction|remise|rabais|moins cher)|(?:réduction|remise|rabais|réduits?|inférieurs?)\s+(?:de|à)\s+\d+\s?%", re.I), "pourcentage de remise ou de tarif"),
    (re.compile(r"prise de poste effective|à la prise de poste|Stellenantritt|Arbeitsbeginn", re.I), "formule « prise de poste » interdite"),
    (re.compile(r"\b\d+\s*(?:jours?|semaines?|j\b)\s*(?:pour|en moyenne|de délai)", re.I), "délai chiffré"),
    (re.compile(r"\b(?:tarif|honoraires?)\s+(?:de|à|:)\s*\d", re.I), "tarif chiffré"),
    (re.compile(r"\btu\b|\bton\b|\bta\b|\btes\b", re.I), "tutoiement"),
]


def api(method, path, params=None, body=None):
    url = f"https://api.airtable.com/v0/{BASE}/{urllib.parse.quote(path)}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=H, method=method)
    return json.load(urllib.request.urlopen(req))


def verifier(pid, texte):
    """Renvoie la liste des motifs de refus (vide = accepté)."""
    d = dossier.get(pid)
    if not d:
        return ["post absent du dossier"]
    t = (texte or "").strip()
    pb = []
    if not t:
        return ["texte vide"]
    if not re.match(r"^(Bonjour|Guten Tag)\b", t):
        pb.append("ne commence pas par « Bonjour » ou « Guten Tag »")
    if len(t) < 300:
        pb.append(f"trop court ({len(t)} caractères)")
    if len(t) > 3000:
        pb.append(f"trop long ({len(t)} caractères)")
    for rx, motif in INTERDITS:
        m = rx.search(t)
        if m:
            pb.append(f"{motif} (« {m.group(0)} »)")
    nom = (d["recruteuse"].get("nom") or "").strip()
    if nom:
        if not all(part.lower() in t.lower() for part in nom.split()):
            pb.append(f"signature : « {nom} » attendu")
        autres = {"Sarah Vanhersel", "Pamela Martinez"} - {nom}
        for a in autres:
            if a.split()[0].lower() in t.lower():
                pb.append(f"signature : « {a} » ne doit pas apparaître")
    else:
        pb.append("recruteuse inconnue dans le dossier")
    if d.get("membre_vetcoop") and "vetcoop" not in t.lower():
        pb.append("adhérent Vetcoop : la mention du partenariat manque")
    if not d.get("membre_vetcoop") and "vetcoop" in t.lower():
        pb.append("pas adhérent Vetcoop : la mention du partenariat est interdite")
    return pb


def relire(pids):
    """État courant des posts concernés, en un seul appel par paquet de 50."""
    out = {}
    for i in range(0, len(pids), 50):
        formula = "OR(" + ",".join(f"RECORD_ID()='{p}'" for p in pids[i:i + 50]) + ")"
        d = api("GET", T_POSTS, {"filterByFormula": formula, "returnFieldsByFieldId": "true",
                                 "fields[]": [F_MAIL, F_ATTRIBUE_A, F_ARCHIVE, F_OFFRE, F_NUMERO]})
        for r in d["records"]:
            out[r["id"]] = r["fields"]
        time.sleep(0.21)
    return out


refus, ok = [], []
for pid, texte in mails.items():
    pb = verifier(pid, texte)
    if pb:
        refus.append((pid, pb))
    else:
        ok.append(pid)

etat = relire(ok) if ok else {}
a_ecrire = []
for pid in ok:
    f = etat.get(pid)
    d = dossier[pid]
    if f is None:
        refus.append((pid, ["post introuvable à la relecture"])); continue
    if (f.get(F_MAIL) or "").strip():
        refus.append((pid, ["« Mail intro proposé » déjà rempli entre-temps : on ne l'écrase pas"])); continue
    if f.get(F_ARCHIVE) or f.get(F_OFFRE):
        refus.append((pid, ["post archivé ou converti entre-temps"])); continue
    if ((f.get(F_ATTRIBUE_A) or {}).get("email") or "") != (d["recruteuse"].get("email") or ""):
        refus.append((pid, ["le post n'est plus attribué à la même recruteuse"])); continue
    a_ecrire.append(pid)

ecrits = 0
if a_ecrire and not DRY:
    items = [{"id": pid, "fields": {F_MAIL: mails[pid].strip()}} for pid in a_ecrire]
    try:
        for i in range(0, len(items), 10):
            api("PATCH", T_POSTS, body={"records": items[i:i + 10]})
            ecrits += len(items[i:i + 10]); time.sleep(0.21)
    except urllib.error.HTTPError as e:
        print(f"ERREUR API Airtable {e.code} : {e.read().decode()[:600]}")
        print(f"{ecrits} mail(s) écrit(s) avant l'erreur.")
        sys.exit(1)

manquants = [pid for pid in dossier if pid not in mails]
print(f"# Mails d'intro — {'SIMULATION, rien écrit' if DRY else 'écriture'}")
print(f"{len(dossier)} post(s) dans le dossier, {len(mails)} mail(s) proposé(s), {len(a_ecrire)} accepté(s), {len(refus)} refusé(s), {len(manquants)} sans mail proposé.")
for pid in a_ecrire:
    d = dossier[pid]
    print(f"- ✔ n°{d.get('numero')} {d.get('clinique')} → {d['recruteuse'].get('nom')}{' · Vetcoop' if d.get('membre_vetcoop') else ''} ({len(mails[pid].strip())} car.)")
for pid, pb in refus:
    d = dossier.get(pid, {})
    print(f"- ✖ n°{d.get('numero', '?')} {d.get('clinique', pid)} : " + " ; ".join(pb))
for pid in manquants:
    d = dossier[pid]
    print(f"- … n°{d.get('numero')} {d.get('clinique')} : aucun mail proposé (le lien Gmail gardera le texte fixe)")
sys.exit(2 if refus else 0)
