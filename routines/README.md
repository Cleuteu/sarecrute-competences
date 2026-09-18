# Routines cloud

Prompts des routines Claude Code cloud (claude.ai/code/routines), versionnés ici.

Claude Code n'a aucun accès aux routines cloud : il ne peut ni les lister, ni lire leur
prompt. Ce dossier est la source de vérité — on discute et modifie le prompt ici, puis on
pousse. Le formulaire web ne contient qu'un pointeur vers le fichier.

## Fichiers

| Fichier | Routine | Déclencheur |
| --- | --- | --- |
| `profil-ia-candidat.md` | Enrichissement d'un candidat : champs structurés, Profil IA, grille de compétences par acte et parcours professionnel (base `appP0W2ISytaNyAhG`, tables `Candidats`, `Actes`, `Compétences`, `Expériences`) | API (`/fire`), `text` = `recordId:recXXXXXXXXXXXXXX` |
| `mail-presentation-candidature.md` | Rédaction du mail de présentation d'un candidat à une clinique, enregistré dans la candidature (jamais envoyé par la routine). Lit `Candidatures`, `Candidats`, `Compétences`, `Offres d'emploi`, `Cliniques` ; écrit uniquement les champs `Mail de présentation - *` de la candidature. Exemples de ton dans `references/mails-presentation-exemples.md`. **Pas encore déployée** : routine cloud à créer, et trois champs à créer sur Candidatures (`Mail de présentation - Statut`, `- Généré le`, `- Note IA`). | API (`/fire`), `text` = `candidatureId:recXXXXXXXXXXXXXX` |
| `cliniques-a-contacter.md` | Lot hebdomadaire de cliniques à contacter : lance `scripts/cliniques_a_contacter.py --attribuer`, qui score les posts « Clinique cherche vétérinaire » de `Posts scrappés`, écrit `Score` / `Raisons` / `Clinique existante`, et attribue 10 **cliniques** par recruteuse active (`Attribué à`, `Attribué le`, `Attribué jusqu'au` = dimanche). **Une clinique = une recruteuse**, y compris de semaine en semaine (posts regroupés par fiche liée, nom normalisé, mail, téléphone). Les recruteuses lisent leur lot sur les pages « À contacter — Sarah / Pamela » de l'interface Posts scrappés. Un lot encore valide bloque la réattribution. Déployée le 10/09/2026, ouverte aux recruteuses le 14/09/2026. | Planifiée : lundi 07:00 Europe/Paris (`0 5 * * 1` UTC), routine `trig_01QQwayZkev8GB8am3yhrt8T` |
| `maj-offres-site.md` | Mise à jour quotidienne des offres du site sarecrute.com : version automatique de la compétence `maj-offres` (scripts de `remote-skills/maj-offres/`). Tourne dans un clone du **dépôt Pages `Cleuteu/sarecrute`** (attaché à la routine), clone `sarecrute-competences` pour les scripts, lit Airtable, écrit les descriptions, contrôle l'anonymat, régénère `offres.html` / `index.html` / `.offres-state.json`, commite et pousse sur `main` (`scripts/publier_site.py publier`), puis envoie par le connecteur Gmail un compte rendu à Sarah (`publier_site.py recap`, adresse lue dans `Recruteurs`) — **seulement s'il y a eu des changements**. Échec = mail à Alex, rien à Sarah. **Pas encore déployée** (18/09/2026), voir ci-dessous. | Planifiée : tous les jours 02:00 Europe/Paris (`0 0 * * *` UTC en été, `0 1 * * *` en hiver) |

## Convention

Chaque fichier contient le prompt **intégral et rien d'autre** : pas d'en-tête, pas de
commentaire, pas de front matter. Le run cloud le suit tel quel, donc tout ce qui est
ajouté au fichier est lu comme une instruction.

Côté routine, le champ **Instructions** est réduit à un pointeur :

```
Suis intégralement les instructions du fichier routines/profil-ia-candidat.md du dépôt
Cleuteu/sarecrute-competences, en les appliquant au recordId transmis au déclenchement.
```

Prérequis pour que ça fonctionne :

- le dépôt `Cleuteu/sarecrute-competences` doit être attaché à la routine (champ
  « Sélectionner un dépôt ») — il est cloné à chaque run, sur `main` ;
- le connecteur Airtable doit être coché dans la section **Connectors** de la routine ;
- une modification du prompt n'est active qu'après un `git push` sur `main`.

## Déploiement de `mail-presentation-candidature` (à faire, dans cet ordre)

Décisions d'Alex des 09 et 10/09/2026 : Sarah seule pour l'instant, vouvoiement systématique, **rien
ne part tout seul**, pas d'automation d'envoi (Sarah copie dans Gmail, joint le CV, envoie elle-même,
suivi Mailsuite conservé), brouillon Gmail par la routine **après** validation du texte. **La routine
écrit dans des champs réservés à l'IA** (`Mail IA - *`) et ne touche jamais aux champs de la
recruteuse (`Mail de présentation - Sujet / Body`, existants).

1. **Champs sur `Candidatures`** — FAIT le 10/09/2026 : `Mail IA - Sujet` fldssJ9lpjVphhFET, `Mail IA - Body`
   fldBtOSybTvWyhZ5J, `Mail IA - Note` fldyMr27NmTQjWVqI, `Mail IA - Statut` fld2EEdsoXQhcJ2yt (En cours /
   Généré / Erreur), `Mail IA - Généré le` fldfpiPZKDkLCuuDs, et la formule **`Mail IA - Éligible`**
   fld6PHJNp2IUPdgr9 (« oui » si non archivée, date_intro_clinic vide, Mail IA - Body vide, Statut ≠ En
   cours, Mail de présentation - Body vide, et statut Candidat intéressé OU prochaine action Proposer le
   candidat à la clinique). L'éligibilité se règle dans cette formule : l'API n'accepte pas de groupe OU
   dans un Find records.
2. **La routine cloud** — FAITE par Alex : « Génération mail présentation candidat à clinique »,
   `trig_01K582k1wWqi8BRpov5q7ueG`. Instructions = pointeur vers ce fichier (avec repli sur l'URL raw
   si le dépôt n'est pas cloné), connecteur Airtable, modèle Opus 5.
3. **Trois automations** — squelettes créés par API le 10/09/2026, désactivés, script à coller à la main
   (`sarecrute/airtable/declencherMailPresentation.js`, variable `candidatureId`, secret `ROUTINE_CLAUDE_KEY` (jeton propre à la routine, généré dans la modale de son déclencheur API ; ni clé API, ni setup-token, ni jeton d’une autre routine)) :
   - `wfllefNfQ6O0BPcBu` **Mails de présentation après enrichissement** : Statut IA → Exécuté, Find records
     (Candidat = déclencheur ET Éligible = oui), groupe répété : En cours puis script (candidatureId =
     élément courant > Record ID).
   - `wflM3niWGUbtwgbJi` **Générer les mails de présentation [bouton candidat]** : même corps ; poser le
     bouton sur les pages Candidats.
   - `wflvLDIQ0E826RrTj` **Générer le mail de présentation [bouton candidature]** : trois branches — déjà
     présenté (note seule), génération en cours (note seule), sinon En cours puis script (candidatureId =
     Déclencheur > Record ID). Seul chemin qui régénère un mail existant. Bouton sur « Détails des
     Intéressés » et « Détails des Postulés ».
   Une fois le script collé, ces automations ne sont plus modifiables par API.
4. **Interface** : afficher `Mail IA - Sujet`, `Mail IA - Body`, `Mail IA - Note`, `Mail IA - Statut`
   sur les pages « Détails des Intéressés » et « Détails des Postulés », à côté des champs
   `Mail de présentation - *` de la recruteuse.
5. `git push origin main` du dépôt des compétences, avec l'accord d'Alex : la routine clone `main`.

Recette : les neuf candidatures de l'essai à blanc du 09/09/2026 (page
https://claude.ai/code/artifact/62a6295c-2a8b-44d5-a5c5-85cd9651dd2c), bouton par bouton, comparées
au mail réel.

## Déploiement de `cliniques-a-contacter` (à faire par Alex)

Décisions d'Alex et des recruteuses (04 et 10/09/2026) : un lot fermé de 10 cliniques par recruteuse
et par semaine, qui expire le dimanche **sans report** ; pas de groupes de cliniques (autre process),
mail obligatoire, fraîcheur ≤ 15 jours prioritaire ; le contact se trace dans `Cliniques` via le bouton
« Convert post to clinique + offre », jamais sur le post ; pas de Telegram pour l'instant.

1. **Champs sur `Posts scrappés`** — FAITS le 10/09/2026 : `Attribué à` fld1F3kcHSc4j4i0M (collaborateur),
   `Attribué le` fldcIiPZVcxFm67XS, `Attribué jusqu'au` fld24nHYzT2JlNqgO, `Score` fldXYoTSgsiLIWeCt,
   `Raisons` fldZsPy6ohFUjoISj, `Clinique existante` fldfPvYIlbDZ8V0sv (lien Cliniques, inverse
   fldB3keMt5bfxGO6G), `Statut clinique existante` fldEZoNIi2PrdiUuJ (lookup), et la formule
   **`À contacter (semaine)`** flde5EceJW3IPwMWk (« oui » si lot non expiré, non archivé, sans offre liée) —
   c'est le filtre des pages.
2. **Pages d'interface** — CRÉÉES le 10/09/2026 dans l'interface Posts scrappés (pbdeYiRLmpICdqQK7), en
   brouillon : « À contacter — Sarah » pagWKxjE22zMa1cgk et « À contacter — Pamela » pagxPnx9UivTK7jmT,
   filtrées sur `Attribué à` = la recruteuse et `À contacter (semaine)` = oui, triées par Score, ouvrant
   la fiche « Détails de Posts scrappés Clinique » (celle qui porte le bouton de conversion). **À publier
   dans l'UI** (l'API ne publie pas). Un compteur « x / 10 » en tête de page se pose dans l'UI aussi.
3. **Premier lot** — ATTRIBUÉ le 10/09/2026 par Alex depuis sa machine, valable jusqu'au 20/09 (première
   semaine longue) ; d'abord 20 par recruteuse, **ramené à 10 le soir même** (décision d'Alex : on avait dit 10). Rapport : `sarecrute/docs/lot-cliniques-2026-09-10.md`.
4. **La routine cloud** — CRÉÉE le 10/09/2026 (`trig_01QQwayZkev8GB8am3yhrt8T`, environnement `sarecrute`,
   Instructions = pointeur vers `routines/cliniques-a-contacter.md`, variable d'environnement
   `AIRTABLE_API_KEY` ; le script écrit par l'API REST, pas par le MCP ; sans la clé il s'arrête sans rien
   écrire). Cron passé le 14/09/2026 de `0 23 * * 0` (dimanche 23:00 UTC = lundi 01:00 Paris, mais encore
   dimanche pour la date UTC du conteneur) à **`0 5 * * 1`** (lundi 07:00 Europe/Paris) ; le script calcule
   de toute façon sa date « du jour » en heure de Paris.
5. `git push origin main` du dépôt des compétences, avec l'accord d'Alex : la routine clone `main`.
6. **Une clinique = une recruteuse** — décision d'Alex du 14/09/2026 après une collision (Cabinet des
   Alouettes, Valmont, servi à Pamela et à Sarah par deux posts distincts). Le script regroupe les posts
   par clinique, n'en met qu'un par clinique dans un lot, rend une clinique déjà attribuée à sa recruteuse
   d'origine semaine après semaine, et répartit à charge égale. **Remise à zéro le 14/09/2026** : les
   attributions des 10/09 et 14/09 ont été vidées et un seul lot de 10 cliniques par recruteuse a été
   attribué, valable jusqu'au dimanche 20/09 ; la routine prend le relais le lundi 21/09.

Réservoir mesuré le 10/09 : 113 posts attribuables pour 20 par semaine, et 15 à 25 nouveaux éligibles par
semaine. Quand il manque, le script réduit les lots plutôt que de les gonfler d'annonces sans mail, et le
dit dans son rapport.

## Déploiement de `maj-offres-site` (à faire par Alex)

Décisions d'Alex du 18/09/2026 : **routine planifiée seule**, tous les jours à 2h, pas de déclencheur
API ni d'automation Airtable ; compte rendu **par mail à Sarah**, uniquement s'il y a des changements
(pas de Telegram) ; **rien d'identifiant** (clinique, ville, personne, chiffres précis) en ligne ni dans
les dépôts — seul le mail, interne, nomme les cliniques. Les dépublications et les publications partent
sans relecture humaine ; une description qui ne passe pas le garde-fou anonymat après deux réécritures
est abandonnée et l'offre part sans ce bloc, ce que le mail signale.

Ce qui change de doctrine : **le dépôt Pages devient la référence pour les offres.** En local,
`./deploy.sh` commence désormais par `sync-offres.py` (rapatrie les blocs d'offres du dépôt dans les
sources locales) et publie aussi `.offres-state.json`. La compétence `maj-offres` à la main commence par
`./deploy.sh --sync` (PROMPT.md 0.3.0).

1. **Pousser l'état dans le dépôt Pages avant le premier run** : un `./deploy.sh` depuis le dossier du
   site suffit (il copie `.offres-state.json` dans le clone et commite). **Sans ce fichier, la routine
   verrait les 44 offres comme nouvelles et réécrirait toutes les descriptions.** Ordre à respecter.
2. `git push origin main` de ce dépôt (`sarecrute-competences`) : la routine clone `main` pour les
   scripts (`remote-skills/maj-offres/`, dont le nouveau `publier_site.py`) et le prompt. Pas besoin de
   `main:stable` pour la routine ; le pousser aussi si l'on veut la compétence manuelle 0.3.0 chez les
   utilisateurs du plugin.
3. **La routine cloud** (claude.ai/code/routines) : dépôt attaché = **`Cleuteu/sarecrute`** (le dépôt
   Pages, pas celui-ci — c'est là qu'elle doit pousser), environnement `sarecrute` (porte déjà
   `AIRTABLE_API_KEY`), connecteur **Gmail** coché (le compte d'Alex : les mails partent de là ;
   l'échec s'envoie à cette même adresse), modèle Opus 5, planification `0 0 * * *` UTC (2h Paris en
   été ; `0 1 * * *` en hiver si l'heure exacte compte). Instructions = pointeur :
   « Suis intégralement les instructions du fichier routines/maj-offres-site.md du dépôt
   Cleuteu/sarecrute-competences (branche main ; le clone à faire est décrit dans son ÉTAPE 1). »
4. **Adresse de Sarah** : `Recruteurs` porte aujourd'hui son gmail (e-mail collaborateur Airtable).
   Le récap doit partir sur son adresse sarecrute : **remplacer la valeur du champ `Email` de sa fiche**
   par la bonne adresse (à ne pas deviner). Le script lit ce champ.
5. **Premier run à la main** (« Run now ») en journée, Alex devant : vérifier (a) que le clone de
   `sarecrute-competences` passe depuis l'environnement — sinon le repli `raw` du prompt, sinon plan B :
   copier `remote-skills/maj-offres/` dans le dépôt Pages par `deploy.sh` — ; (b) que le `git push
   origin HEAD:main` est accepté par le proxy GitHub du cloud pour un dépôt attaché ; (c) que le build
   Pages est confirmé et que le mail arrive à Sarah avec les bons noms. Puis relire le commit poussé :
   message fixe, trois fichiers, aucun nom de clinique.

Points ouverts : la routine ne connaît pas le fuseau Europe/Paris, elle calcule l'heure du commit et
la date du mail elle-même (`publier_site.py`, règle été/hiver simplifiée). Les descriptions écrites la
nuit ne sont relues par personne avant la mise en ligne — c'est le choix du 18/09 ; si une description
gêne, Sarah le dit, on la corrige à la main dans Airtable (annonce ou notes), la routine la réécrit la
nuit suivante.
