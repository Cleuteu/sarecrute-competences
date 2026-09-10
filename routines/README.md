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
   (`sarecrute/airtable/declencherMailPresentation.js`, variable `candidatureId`, secret `ROUTINE_CLAUDE_KEY` (jeton OAuth sk-ant-oat01, pas une clé API)) :
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
