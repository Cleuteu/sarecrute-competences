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

1. **Cinq champs sur `Candidatures`** (tbl3LnGoBxnheGI7v) : `Mail IA - Sujet` (texte court),
   `Mail IA - Body` (texte long), `Mail IA - Note` (texte long), `Mail IA - Statut` (sélection
   unique : En cours, Généré, Erreur), `Mail IA - Généré le` (date).
2. **La routine cloud** sur claude.ai/code/routines : déclencheur API, dépôt
   `Cleuteu/sarecrute-competences` attaché, connecteur **Airtable** coché (pas Gmail pour l'instant),
   instructions = « Suis intégralement les instructions du fichier
   routines/mail-presentation-candidature.md du dépôt Cleuteu/sarecrute-competences, en les appliquant
   au candidatureId transmis au déclenchement. » Noter le `trig_…` et le reporter dans
   `sarecrute/airtable/declencherMailPresentation.js`.
3. **Trois automations, un seul script** (`declencherMailPresentation.js`, collé à la main, secret
   `ANTHROPIC_KEY` coché) :
   - **Bouton candidat** « Générer les mails de présentation » (bouton d'interface sur Candidats) :
     Find records sur Candidatures — Candidat = déclencheur, Archivée décochée, `date_intro_clinic`
     vide, `Mail IA - Body` vide, `Mail IA - Statut` ≠ En cours, `Mail de présentation - Body` vide,
     et (Statut = Candidat intéressé OU Prochaine action = Proposer le candidat à la clinique) —
     puis groupe répété : « Mettre à jour l'entrée » (Mail IA - Statut = En cours) puis le script avec
     `candidatureId` = élément courant. Zéro candidature éligible = zéro déclenchement : chaque run
     compte, la plateforme limite les déclenchements par jour. « Candidat postulé » est exclu : la
     présentation est déjà faite.
   - **Après enrichissement** : déclencheur « enregistrement modifié » sur Candidats, champ surveillé
     Statut IA, condition Statut IA = Exécuté, puis exactement le même corps.
   - **Bouton candidature** « Générer le mail de présentation » (bouton d'interface sur Candidatures) :
     groupe conditionnel — si `date_intro_clinic` est renseigné ou `Mail IA - Statut` = En cours,
     « Mettre à jour l'entrée » écrit seulement `Mail IA - Note` (« Déjà présenté le … » / « Génération
     déjà en cours ») sans déclencher ; sinon « Mettre à jour l'entrée » (En cours) puis le script avec
     `candidatureId` = Déclencheur > Record ID. C'est le seul chemin qui régénère un mail existant.
   ⚠️ Un Find records dont une valeur de comparaison est vide est ignoré : la condition sur le
   candidat reste en tête, et on vérifie le comptage avant d'activer.
4. **Interface** : afficher `Mail IA - Sujet`, `Mail IA - Body`, `Mail IA - Note`, `Mail IA - Statut`
   sur les pages « Détails des Intéressés » et « Détails des Postulés », à côté des champs
   `Mail de présentation - *` de la recruteuse.
5. `git push origin main` du dépôt des compétences, avec l'accord d'Alex : la routine clone `main`.

Recette : les neuf candidatures de l'essai à blanc du 09/09/2026 (page
https://claude.ai/code/artifact/62a6295c-2a8b-44d5-a5c5-85cd9651dd2c), bouton par bouton, comparées
au mail réel.
