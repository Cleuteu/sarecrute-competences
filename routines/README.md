# Routines cloud

Prompts des routines Claude Code cloud (claude.ai/code/routines), versionnés ici.

Claude Code n'a aucun accès aux routines cloud : il ne peut ni les lister, ni lire leur
prompt. Ce dossier est la source de vérité — on discute et modifie le prompt ici, puis on
pousse. Le formulaire web ne contient qu'un pointeur vers le fichier.

## Fichiers

| Fichier | Routine | Déclencheur |
| --- | --- | --- |
| `profil-ia-candidat.md` | Enrichissement d'un candidat : champs structurés, Profil IA, et grille de compétences par acte (base `appP0W2ISytaNyAhG`, tables `Candidats`, `Actes`, `Compétences`) | API (`/fire`), `text` = `recordId:recXXXXXXXXXXXXXX` |
| `mail-presentation-candidature.md` | Rédaction du mail de présentation d'un candidat à une clinique, enregistré dans la candidature (jamais envoyé par la routine). Lit `Candidatures`, `Candidats`, `Compétences`, `Offres d'emploi`, `Cliniques` ; écrit uniquement les champs `Mail de présentation - *` de la candidature. Exemples de ton dans `references/mails-presentation-exemples.md`. **Pas encore déployée** : routine cloud à créer, et trois champs à créer sur Candidatures (`Mail de présentation - Statut`, `- Généré le`, `- Note IA`). | API (`/fire`), `text` = `candidatureId:recXXXXXXXXXXXXXX` |
| `cliniques-a-contacter.md` | Lot hebdomadaire de cliniques à contacter : lance `scripts/cliniques_a_contacter.py --attribuer`, qui score les posts « Clinique cherche vétérinaire » de `Posts scrappés`, écrit `Score` / `Raisons` / `Clinique existante`, et attribue 20 posts par recruteuse active (`Attribué à`, `Attribué le`, `Attribué jusqu'au` = dimanche). Les recruteuses lisent leur lot sur les pages « À contacter — Sarah / Pamela » de l'interface Posts scrappés. Un lot encore valide bloque la réattribution. **Pas encore déployée** (voir ci-dessous). | Planifiée : lundi 07:00 Europe/Paris |

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

Décisions d'Alex et des recruteuses (04 et 10/09/2026) : un lot fermé de 20 cliniques par recruteuse
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
   dans l'UI** (l'API ne publie pas). Un compteur « x / 20 » en tête de page se pose dans l'UI aussi.
3. **Premier lot** — ATTRIBUÉ le 10/09/2026 par Alex depuis sa machine, valable jusqu'au 20/09 (première
   semaine longue). Rapport : `sarecrute/docs/lot-cliniques-2026-09-10.md`.
4. **La routine cloud** — À CRÉER : planifiée le lundi à 07:00 Europe/Paris, Instructions = pointeur vers
   `routines/cliniques-a-contacter.md`, dépôt attaché (cloné sur `main`), **variable d'environnement
   `AIRTABLE_API_KEY`** dans l'environnement de la routine (le script écrit par l'API REST, pas par le
   MCP ; sans la clé il s'arrête sans rien écrire). Connecteur Airtable inutile. Premier lundi utile :
   le 21/09 — le 14/09 le script verra le lot en cours et n'attribuera rien (garde-fou `--force`).
5. `git push origin main` du dépôt des compétences, avec l'accord d'Alex : la routine clone `main`.

Réservoir mesuré le 10/09 : 113 posts attribuables pour 40 par semaine, et 15 à 25 nouveaux éligibles par
semaine. Quand il manque, le script réduit les lots plutôt que de les gonfler d'annonces sans mail, et le
dit dans son rapport.
