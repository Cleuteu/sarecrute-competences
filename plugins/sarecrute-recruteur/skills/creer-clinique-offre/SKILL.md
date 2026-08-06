---
name: creer-clinique-offre
description: >-
  Crée dans l'Airtable de recrutement vétérinaire (base prod « Recrutement vétérinaire ») la
  clinique et l'offre d'emploi correspondant à une annonce que le recruteur colle dans Claude,
  puis prépare le premier contact : brouillon Gmail si la clinique a une adresse mail, sinon
  message Messenger à copier-coller. Se déclenche quand l'utilisateur colle une annonce
  vétérinaire ou demande de « créer la clinique et l'offre », « ajouter cette annonce dans
  Airtable », « enregistrer cette offre », « nouvelle clinique + offre », ou formulation
  équivalente.
---

# Créer une clinique et son offre d'emploi depuis une annonce

Le recruteur colle une annonce (Facebook, LinkedIn, mail reçu, site d'emploi). À partir de ce seul
texte : créer la clinique, créer l'offre, et préparer le message de premier contact. **Aucun envoi
automatique** : le mail reste un brouillon, le message Messenger est rendu à copier.

Prérequis : connecteur **Airtable** disponible ; connecteur **Gmail** pour le brouillon.

Base **PROD** : `appP0W2ISytaNyAhG` · Cliniques `tblagWImxHH15rRAh` · Offres `tblVZva5yHSCnucsK`.

## Ressources bundlées

| Fichier | Rôle |
|---|---|
| `references/champs.md` | tous les champs à remplir, leurs IDs, les valeurs de select autorisées |
| `references/matching.md` | **à lire avant de remplir l'offre** : comment chaque champ est lu par le moteur de rapprochement candidats / posts |
| `scripts/ville.py` | résout la ville en département + CP + coordonnées, avec la même règle que l'automation Airtable |

Écrire **par ID de champ**, **sans `typecast`**. Ne jamais ajouter de valeur à un champ select :
si l'annonce ne rentre dans aucune valeur existante, laisser vide et le signaler.

## Étape 1 — Savoir au nom de qui on travaille

L'offre et la clinique doivent être attribuées au recruteur qui lance la commande, sans le lui
demander à chaque fois.

1. Lire `$HOME/.sarecrute/recruteur.json` (sous Windows : `%USERPROFILE%\.sarecrute\recruteur.json`) :
   ```json
   { "responsable": "Prénom Nom", "email": "prenom@exemple.fr" }
   ```
   S'il existe, l'utiliser **sans poser de question** et le dire en une ligne dans le compte rendu.
2. Sinon, demander avec AskUserQuestion parmi les collaborateurs de la base
   (voir `references/champs.md`), en pré-sélectionnant celui dont l'e-mail correspond au compte
   Claude de l'utilisateur. Écrire ensuite le fichier (créer le dossier) et préciser qu'il peut le
   modifier pour changer d'identité. Ce fichier est **local** : ne jamais le versionner.

Cet e-mail alimente `Propriétaires du client` (clinique), `Responsable de l'offre` et
`Propriétaire de l'offre` (offre), sous la forme `{"email": "…"}`.

## Étape 2 — Dépouiller l'annonce

Lire l'annonce **en entier** et en extraire, sans rien inventer :

- **identification** : nom de la structure, ville, CP, nom du vétérinaire ou du contact,
  e-mail(s), téléphone, groupement nommé, lien du post, date de parution ;
- **le poste** : pratiques, spécialités, expérience, statut contractuel, temps de travail, gardes
  et leur fréquence, logement, dates de démarrage / de fin, rémunération, langues ;
- **le contexte** : ce qui décrit la structure (référé, plateau technique, taille si chiffrée).

Deux règles de lecture :

- **Ce que l'annonce ne dit pas reste vide.** Un champ deviné exclut des candidats (voir
  `references/matching.md`) — c'est plus coûteux qu'un champ vide.
- **Requis vs optionnel** : « recherche un vétérinaire canin, appétence rurale appréciée » donne
  `Pratiques requises = [Canine]` et `Pratiques optionnelles = [Bovins]`. Tout ce qui est
  « apprécié », « un plus », « idéalement » va en optionnel.

Préparer aussi la liste des **Questions** à poser à la clinique : une ligne par question préfixée
`- `, portant exactement sur ce que l'annonce laisse en suspens (taille et composition de
l'équipe, contexte du recrutement, rythme des gardes, profil junior accepté ?, ratio
canine/rurale, forfait heures ou jours, date de prise de poste…). C'est ce champ que le recruteur
aura sous les yeux au téléphone.

## Étape 3 — Résoudre la ville

```bash
python3 ~/.claude/skills/creer-clinique-offre/scripts/ville.py "<ville>" --cp <CP si connu>
```

Le département (`county`) conditionne **tout** le matching : sans lui, aucun rapprochement n'est
créé. Traiter la sortie du script :

- `orthographe_reconnue_par_l_automation: true` et une seule commune → écrire `Ville` telle que
  renvoyée, ne pas toucher `county` ni `CP` : l'automation les remplira.
- Orthographe non reconnue → utiliser l'orthographe proposée dans `propositions`.
- Plusieurs communes du même nom → comparer `choisi_par_l_automation` et `retenu`. S'ils diffèrent,
  noter la correction à appliquer à l'étape 5.
- Commune absente du CSV (clinique étrangère, arrondissement) → renseigner `county` **à la main**
  (`Canton de Vaud`, `Province de Liège`…) et prévenir le recruteur qu'il n'y aura pas de
  coordonnées.

## Étape 4 — Chercher un doublon avant de créer

Ne jamais créer une clinique sans avoir cherché :

1. **par e-mail** — `list_records_for_table` sur `tblagWImxHH15rRAh` :
   ```json
   {"operator":"or","operands":[
     {"operator":"=","operands":["fldIrQarKGnhq3g76","<mail>"]},
     {"operator":"=","operands":["fldjg9sc0KdWi6I4O","<mail>"]}]}
   ```
   avec `fieldIds` = `["fldHJd3Ts1vfLn4TQ","fldf8t2ihJMGnh7wz","fldgsRdtLrBThQfb1","fldyfue6Bm95TR9vC","fldIrQarKGnhq3g76","fldle3UZwCK3LMzci"]`
   — le dernier (`Poste vétérinaire`) dit tout de suite si la clinique a déjà des offres.
2. **par nom et par ville** — `search_records` sur la même table, `fields` =
   `["fldHJd3Ts1vfLn4TQ","fldLUWwSfCGb99kxc","fldf8t2ihJMGnh7wz"]`. Le nom de structure varie
   souvent d'une annonce à l'autre (« Clinique vétérinaire des Tilleuls » / « Vétos des
   Tilleuls ») : chercher le mot distinctif, pas la raison sociale entière.
3. **par nom du vétérinaire** (`fldLUWwSfCGb99kxc`) quand l'annonce est signée.

Si une clinique existante correspond : **ne pas la recréer**. Demander confirmation au recruteur,
puis ne créer que l'offre en la liant à cette clinique. Compléter au passage les champs vides de
la clinique (téléphone, second mail, profil FB…) sans écraser ce qui est déjà renseigné, et sans
toucher `Status commercial` — le recruteur y a peut-être déjà travaillé.

Si la clinique a déjà une offre non archivée, le signaler : soit l'annonce est la même (mettre à
jour l'offre existante plutôt que d'en créer une seconde), soit c'est un second poste et il faut
alors renseigner `Second name` (`fldqXF6HUy6GRRUVi`) sur la nouvelle offre.

## Étape 5 — Créer la clinique

Présenter d'abord au recruteur le récapitulatif de ce qui va être écrit (clinique + offre),
champ par champ, en signalant ce qui reste vide faute d'information. **Attendre son feu vert.**

Puis `create_records_for_table` sur `tblagWImxHH15rRAh`. Valeurs par défaut d'une clinique issue
d'une annonce :

| Champ | Valeur |
|---|---|
| `Pays` (`fld5COKjkzYSSKA98`) | `France` sauf indication contraire — **obligatoire**, c'est lui qui déclenche la géolocalisation |
| `Status commercial` (`fldyfue6Bm95TR9vC`) | `A contacter` |
| `Canal de contact` (`fld8Pe9yuKw9P89W1`) | `Mail` s'il y a une adresse, sinon `Messenger` / `Téléphone` selon ce dont on dispose |
| `Engagement du lead` (`fldhpCvHu3yN8lS70`) | `Froid` pour une annonce trouvée, `Tiède` si la clinique a écrit la première |
| `Clinique de référé` (`fldqPvfT0Zw7vaoPP`) | `Non`, sauf mention de référé |
| `Notes` (`fldJIET4sokOxl5f7`) | provenance (« annonce FB du 05/08/26 ») **puis le texte intégral de l'annonce** |
| `Propriétaires du client` (`fldOCZHesfhv1TO20`) | `[{"email": "<recruteur>"}]` |

Laisser vide `Taille de clinique` si l'annonce ne la dit pas, et ne pas toucher
`Prochaine action` / `Date prochaine action` (une automation les pose).

**Puis vérifier la géolocalisation** : relire la clinique (`county`, `CP`, `latitude`) une dizaine
de secondes plus tard — l'automation est asynchrone.

- `county` rempli et cohérent → continuer.
- `county` vide → l'automation n'a pas trouvé la ville. Corriger `Ville` avec l'orthographe du
  CSV (ce qui relance l'automation), ou écrire `county` à la main.
- `county` rempli mais dans le mauvais département (cas des homonymes) → écrire `county` et `CP`
  à la main avec les valeurs `retenu` du script, et prévenir que `latitude`/`longitude` pointent
  encore sur l'autre commune.

## Étape 6 — Créer l'offre

**Lire `references/matching.md` avant de remplir.** Les pièges qui font qu'une offre ne
rapproche personne, dans l'ordre de fréquence :

1. `county` vide → le matching s'arrête avant tout le reste ;
2. trop de valeurs en `Pratiques requises` / `Spécialités requises` → le reste va en optionnelles ;
3. `Expérience requise = Spécialiste` → **exclut tout le monde**, ne jamais l'utiliser ;
4. `Logement = Non` posé par défaut alors que l'annonce n'en parle pas ;
5. `Taille de clinique` devinée sur la clinique.

`create_records_for_table` sur `tblVZva5yHSCnucsK`, avec :

- `Clinique` (`fldtUGOTlzMmBrrx9`) = `["<recId de la clinique>"]` ;
- `Emploi recherché` (`fldC1pPXhUzhDh6Qj`) = `Vétérinaire` ou `ASV` selon l'annonce ;
- `Annonce` (`fldLIH3nwT4p9uhHC`) = **texte intégral**, jamais tronqué ;
- `Questions` (`fldMw26Azh3ZyT0Cg`) = la liste préparée à l'étape 2 ;
- `Date de publication` (`fldH4usQBpHkdNQJ3`) = date de parution ; à défaut, la date du jour ;
- `Lien de l'offre` (`fldzuEBZkX6jQNeSS`) = URL du post quand on l'a ;
- `Responsable de l'offre` (`fldPqVh2fe65tIct2`) et `Propriétaire de l'offre` (`fldERU7fexhGsuZJ3`)
  = `{"email": "<recruteur>"}` ;
- les champs du poste renseignés par l'annonce, et **seulement** ceux-là.

Ne pas remplir `Description du poste`, `Texte de publication`, `Image de publication` : ils sont
écrits plus tard, au moment de la publication.

**Puis relire l'offre créée** et vérifier `county`, `latitude`, `longitude` (lookups) : c'est la
seule preuve que le matching pourra tourner.

## Étape 7 — Lancer le matching

Le rapprochement n'est **pas** automatique à la création d'une offre : la routine nocturne ne
balaie que les candidats et posts récemment modifiés. Dire au recruteur d'ouvrir la fiche de
l'offre dans l'interface Airtable et de lancer le bouton de création des valeurs potentielles
(automation `Create potential values [InterfaceOffre]`) pour confronter l'offre au vivier
existant.

S'il le fait et que rien ne sort, reprendre les champs de l'étape 6 dans l'ordre : c'est presque
toujours un `county` manquant ou un « requis » de trop.

## Étape 8 — Préparer le premier contact

### Si la clinique a une adresse mail → brouillon Gmail

`create_draft` du connecteur Gmail, **sans jamais envoyer**. Le brouillon part dans la boîte du
compte Gmail connecté, donc celle du recruteur.

- `to` : `Mail1`, et `Mail2` s'il existe.
- `subject` : `Suite à votre annonce pour le poste vétérinaire`.
- Corps : reprendre le message maison, signé par le recruteur de l'étape 1, et l'ancrer sur
  **un ou deux éléments précis de l'annonce** (la pratique, la région, le type de contrat) pour
  qu'il ne ressemble pas à un envoi en masse :

  > Bonjour Docteur,
  >
  > Je me présente, <Prénom Nom>, agent pour les vétérinaires. J'accompagne actuellement une
  > cinquantaine de vétérinaires dans leur recherche de poste.
  >
  > Votre annonce pour <le poste, en une demi-ligne reprise de l'annonce> rassemble plusieurs
  > critères qui intéressent certains des vétérinaires avec lesquels j'échange.
  >
  > Je souhaiterais m'entretenir avec vous, notamment afin d'avoir plus d'informations sur le
  > poste que vous proposez. Seriez-vous disponible pour en discuter prochainement par téléphone ?
  >
  > Cordialement,
  > <Prénom Nom> — Agent de recrutement vétérinaire

  Registre : sobre et concret, comme le reste des échanges cliniques. Pas de superlatif
  marketing, pas de promesse de candidats nommés.

Signaler dans le compte rendu qu'une automation Airtable (« Mail intro clinique ») envoie déjà ce
message depuis l'interface quand la clinique est en `A contacter` avec `Canal de contact = Mail` :
il faut choisir l'une des deux voies, pas les deux. Si le recruteur envoie le brouillon à la main,
c'est à lui de passer `Status commercial` à `En attente de 1ere réponse` et de renseigner
`intro_at` — la compétence ne les touche pas.

### Sinon → message Messenger à copier-coller

Rendre le message **dans la réponse**, dans un bloc de code pour qu'il se copie d'un geste, avec
le lien du profil ou de la page Facebook de la clinique (`Profil Facebook`, ou le lien du post).
Même contenu, mais plus court et sans objet — Messenger n'en a pas :

> Bonjour Docteur, je me présente, <Prénom Nom>, agent pour les vétérinaires. J'accompagne une
> cinquantaine de vétérinaires dans leur recherche de poste et votre annonce pour <le poste>
> correspond à plusieurs d'entre eux. Seriez-vous disponible prochainement pour en échanger par
> téléphone ? Merci d'avance.

Ne pas ouvrir Messenger, ne pas envoyer : le recruteur colle lui-même.

## Étape 9 — Compte rendu

- au nom de quel recruteur on a travaillé ;
- clinique créée (ou réutilisée) et offre créée, avec leurs IDs ;
- `county` / coordonnées obtenus, ou le problème restant ;
- **les champs laissés vides faute d'information dans l'annonce** — c'est la liste que le
  recruteur complétera après son appel ;
- les questions posées dans `Questions` ;
- le rappel de lancer le matching depuis l'interface ;
- ce qui a été préparé pour le contact (brouillon Gmail, ou message à coller) et le fait que rien
  n'a été envoyé.

## Pièges connus

- **`typecast` jamais.** Il créerait des valeurs de select parasites. Une écriture qui échoue sur
  une valeur inconnue est le comportement voulu : c'est le signal qu'il faut choisir une valeur
  existante ou laisser vide.
- **Le MCP Airtable et les noms de champs accentués** : passer par les **IDs** de champs
  (`fldXXX`) en lecture comme en écriture, y compris dans `fieldIds` et `sort`. Et il n'accepte
  pas `filterByFormula` — utiliser l'objet `filters` structuré.
- **Le CP est écrasé** par l'automation de géolocalisation quand `Pays = France` : inutile de
  l'écrire, sauf en correction manuelle après coup.
- **`Rémunération`** est un champ interne, souvent rempli de notes brutes. Ne jamais le recopier
  dans un message à la clinique ni dans un texte publié.
- **Une offre archivée archive ses candidatures** (automation). Ne jamais cocher `Archivée ?` pour
  « nettoyer » un essai : supprimer l'enregistrement de test.
- **Relancer le matching supprime les paires non archivées devenues incompatibles.** Corriger un
  champ mal rempli est donc sain, mais efface les rapprochements pas encore traités par le
  recruteur : le prévenir avant.
