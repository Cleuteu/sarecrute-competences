# Champs Airtable — table Candidats

Base **PROD** « Recrutement vétérinaire » : `appP0W2ISytaNyAhG` · Candidats `tblPmkTaAjS9Yoovt`.

Toujours écrire par **ID de champ** et **sans `typecast`**. Une valeur de select absente des
listes ci-dessous fait échouer l'écriture — c'est voulu : on ne crée jamais de nouvelle valeur de
select (ni via `typecast`, ni via `update_field`). Si la source ne rentre dans aucune valeur
existante, on laisse vide et on le signale au recruteur.

La colonne **matching** dit ce que le champ fait au rapprochement candidat × offre, tel que le
script `candidaturesPotentielles.js` le lit réellement. Trois valeurs :

- **gate** — vide ou mal rempli, le candidat ne matche rien ;
- **exclut** — chaque valeur posée retire des offres ; vide = permissif ;
- **—** — information pour le recruteur, aucun effet.

---

## Identité et contact

| Champ | ID | Type | matching | Quoi y mettre |
|---|---|---|---|---|
| Prénom | `fld1WR6pNpe8sAya6` | texte | — | **obligatoire** (avec Nom) |
| Nom | `fld6yzzWrqBZBtXly` | texte | — | séparé du prénom : `Noms` est une formule |
| Mail | `fldmtHKu93RMqkVw6` | email | — | jamais depuis une URL, jamais celui d'une clinique |
| Téléphone | `fldZ9229oPu876Ls2` | tél | — | idem — l'identifiant d'un post FB ressemble à un 06 |
| Profil Facebook | `fldtHMm6iexTdCfEk` | url | — | souvent le seul moyen de joindre un profil sourcé FB |
| Profil Instagram | `fldKujBdXm8Vw4Xze` | url | — | |
| Profil LinkedIn | `fldpUlTONGaMobJa5` | url | — | |
| Ville | `fldgnVDSacJdlzRG9` | texte | **gate** (distance) | domicile, orthographe du CSV — déclenche le géocodage |
| CP | `fldjFm8KKLcFNgyNb` | texte | idem | écrasé par l'automation si la ville est trouvée |
| Pays | `fld7Yagembu2ZPNhU` | select | — | `France` · `Suisse` · `Espagne ` · `Portugal` · `Belgique` · `Irlande` · `Angleterre` · `Luxembourg` |
| county | `fldfKuAsEj3O4YvnZ` | select | **gate** (zone) | **ne pas écrire si la ville est reconnue** : l'automation le pose. À la main hors France |
| Sourceur | `fldECFOFPFdxzzFFP` | collaborateur | — | `{"email": "…"}` — le recruteur |
| Ajouté au CRM par | `fldq8pztsTZBa0IK4` | collaborateur | — | idem, même personne pour une saisie à la main |

`Département` (`fldYqVlSZwekkJunh`, texte) est un vestige : le champ lu par le matching est
`county`. `ville_departement` (`fldXxLAaMSu9tSP6P`) est une formule.

## Statut et provenance

| Champ | ID | Type | matching | Valeurs |
|---|---|---|---|---|
| Statut Recherche | `fldOijG6rapbZUqMR` | select | **gate** | `En recherche active` · `En recherche passive` · `Pas en recherche` · `Blacklisté` |
| Emploi recherché | `fldizV1UoejwizYSq` | select | — | `Vétérinaire` · `ASV` |
| Canal de contact | `fldoXNvz9C6zQaiK6` | select | — | `Mail` · `Linkedin` · `Facebook` · `Téléphone` · `Instagram` · `Vétowork` · `Pas contacté` |
| Source du candidat | `fldVyZvVmWllrD7ZT` | select | — | `Facebook` · `TemaVet` · `Instagram` · `Linkedin` · `Bouche à oreille` · `Annuaire Roy` · `Formulaire` · `Vetowork` |
| En poste ? | `fldnAVvWO3EfSOXXs` | select | — | `Oui` · `Non` |
| Contrat court | `fldgCpT78wU4xcBj8` | case | **exclut** | critère d'éligibilité du matching nocturne — ne cocher que si la source le dit |
| Statut IA | `fldAHJDEHXjNj6p8P` | select | — | `En cours` · `Exécuté` · `Erreur` — voir ÉTAPE 6 du SKILL.md |

⚠️ **`Statut Recherche` est le vrai interrupteur.** Côté offre, le script ne considère que les
candidats en `En recherche active` ou `En recherche passive` (`statutRecherche && [...].includes`) :
une cellule vide est éliminatoire. Et la routine nocturne « Supprimer les valeurs potentielles
obsolètes » nettoie chaque nuit les paires des candidats « pas en recherche ». Un candidat sans ce
champ est invisible, sans message d'erreur nulle part.

## Les sources brutes — verbatim, jamais retouchées

| Champ | ID | Type | Contenu |
|---|---|---|---|
| CV text | `fldFe8hgz5ekEHayv` | texte long | texte extrait du CV |
| CV | `fldsj2ukrpjPzu5ox` | pièces jointes | le fichier lui-même (voir `scripts/cv.py`) |
| Transcripts | `fldNMVoFoHx3t3O9D` | texte long | transcripts d'entretiens **concaténés** |
| Post | `fldHUHmAzr4nRRlrU` | texte long | annonce écrite par le candidat, sections séparées par `──────────` |
| Lettre de motivation | `fldMSrkD4cUo98WSp` | pièces jointes | si le recruteur en a une |
| Notes | `fld0s84U1HdrHKqkg` | texte long | **espace du recruteur — ne jamais écrire, pas même une ligne de contexte** |
| Notes du candidat | `fld8WaHsnucNvdEqW` | texte long | ce que le candidat écrit lui-même — **ne jamais écrire** |
| Profil | `fldlnO9d1ctGABT9v` | richText | **réservé au recruteur — ne jamais écrire** |
| Profil IA | `fldtz8Gy68I1RMXrm` | richText | écrit par l'enrichissement (ÉTAPE 6), pas à la création |

## Ce que cherche le candidat — les champs du matching

Les pratiques et spécialités se comparent par **double inclusion** avec celles de l'offre :

```
candidat_dans_offre = toutes les pratiques REQUISES par le candidat ⊂ (requises ∪ optionnelles de l'offre)
offre_dans_candidat = toutes les pratiques REQUISES par l'offre     ⊂ (requises ∪ optionnelles du candidat)
compatible          = les deux
```

Un côté vide rend la comparaison vraie. **Conséquence : chaque valeur mise en « requises » côté
candidat retire toutes les offres qui ne la couvrent pas.** Un candidat qui veut faire de la canine
et accepterait du bovin porte `requises = [Canine]`, `optionnelles = [Bovins]` — pas les deux en
requises. Tout ce qui est « apprécierait », « pourquoi pas », « ouvert à » va en optionnelles.

| Champ | ID | Type | matching | Valeurs |
|---|---|---|---|---|
| Pratiques requises | `fldKxF494zI5Kgc6n` | multi | **exclut** | `Canine` · `Bovins` · `Equine` · `NAC` · `Allaitant` · `Laitier` · `Ovin/Caprin` · `Porcin` · `Loups` · `Volailles` |
| Pratiques optionnelles | `fld6tibAOw9YfzkuI` | multi | permissif | idem |
| Spécialités requises | `fldYpaOYuUBHpqlqU` | multi | **exclut** | `Urgences` · `Laboratoire` · `Echographie` · `Orthopédie` · `Chirurgie` · `Ophtalmologie` · `Ostéopathie` · `Management` · `Cardiologie` · `Reproduction` · `Oncologie` · `Neurologie` · `Médecine interne` · `Anatomie Pathologique` |
| Spécialités optionnelles | `fldB1A9V3S74LbseU` | multi | permissif | idem + `Epidémiologie` |
| Zones de recherche | `fldacGQbzpkx88ULc` | multi | **gate** | `France` · `Suisse` · `Espagne` · `Luxembourg` · `Belgique` · `Polynésie française` · `Ile Maurice` · `Nouvelle calédonie` · puis `01 - Ain` … `95 - Val-d'Oise`, DOM, cantons suisses, provinces belges |
| Expérience | `fldfwzkT8yXZthQiZ` | select | **gate** | `Etudiant` · `Débutant` · `1 à 2 ans` · `Autonome` · `Spécialiste` |
| Statuts contractuels souhaités | `fldZaUsTcNsN7HlWe` | multi | exclut | `CDI` · `CDD` · `Association` · `Vacation` · `Collaboration libérale` · `Internat` · `Prophylaxie` · `Achat/Vente de clinique` |
| Type de temps de travail | `fldGZhonpYwDW78ze` | multi | exclut | `Temps plein` · `Temps partiel` |
| Logement requis | `fldpnnrJHV3BWLIYC` | select | exclut si `Oui` | `Oui` · `Préférable` · `Non` |
| Gardes | `fldI1xWGed3dcQIUs` | select | — | `Oui` · `Non` |
| Taille de clinique recherchée | `fldgUE6JdEkDwTzmB` | multi | exclut | `Petite` · `Moyenne` · `Grande` |
| Clinique de référé recherché | `fldLICFF8e0p6Bz6d` | select | exclut | `Oui` · `Non` |
| Groupe souhaité | `fldJEVu81KYnd7zWG` | select | exclut | `Oui` · `Non` — l'offre en dérive une valeur **toujours non vide**, donc `Non` retire toutes les cliniques de groupement |
| Intérêt géographique recherché | `fldZuLhTNHAFnHJf7` | multi | exclut | `Alpes` · `Pyrénées` · `Méditerranée` · `Océan Atlantique Sud-Ouest` · `Océan Atlantique Nord Ouest` · `Campagne` · `Grande ville` |
| Langues | `fld48WU9SCR9DkVN6` | multi | — | `Français` · `Espagnol` · `Anglais` · `Allemand` · `Italien` · `Portugais` |
| Régions de recherche | `fldh6w9K5t4FhZYRq` | lien | indirect | **ne pas écrire** : déclenche une automation qui réécrit `Zones de recherche` |

### Géographie : deux chemins, un seul suffit

Compatible si **l'une** des deux conditions est vraie :

- distance haversine candidat ↔ clinique ≤ rayon — nécessite `latitude`/`longitude` des deux côtés,
  donc une `Ville` géocodée ;
- ou une `Zone de recherche` du candidat correspond au `county` de l'offre, avec les équivalences
  `France` → tout département numéroté, `Suisse` → `Canton …`, `Belgique` → `Province …`.

D'où : **un candidat sans ville n'est pas perdu, un candidat sans zone de recherche l'est** dès
qu'on ne connaît pas son domicile. `Zones de recherche` est la soupape.

⚠️ Le rayon personnel `acceptable_distance_from_home (km)` (`fldXmn4DsK0m6QCYJ`) n'est lu **que**
quand le matching part d'une offre. Lancé depuis la fiche candidat, le script retombe sur 50 km en
dur. Le renseigner reste utile, mais ne suffit pas à élargir la portée d'un candidat.

### Expérience : une échelle, et vide n'est pas neutre

| `Expérience requise` de l'offre | Candidats retenus |
|---|---|
| vide ou `Etudiant` | tous |
| `Débutant` | `Débutant`, `1 à 2 ans`, `Autonome` |
| `1 à 2 ans` | `1 à 2 ans`, `Autonome` |
| `Autonome` | `Autonome` seulement |
| `Spécialiste` | aucun (bug connu côté offre) |

Côté candidat, `nomExperience(...) || "Débutant"` : **une cellule vide vaut « Débutant »**, décision
d'Alex. Le candidat disparaît donc des offres qui demandent `1 à 2 ans` ou `Autonome`. Renseigner ce
champ dès que la source permet de trancher ; entre deux paliers, prendre le plus bas.

`Années d'expérience` (`fldSGOptEz0Api4wN`, entier) ne sert **pas** au matching : il pilote
`Echelon`, donc la rémunération convention collective. Ne jamais déduire l'un de l'autre, ni de
l'année de sortie — une équivalence étrangère récente sur un diplôme de 2018 ne fait que quelques
mois d'exercice, le cas existe dans la base.

## Parcours et conditions — information seule

| Champ | ID | Type |
|---|---|---|
| Ecole véto | `fldEUkJLo4ygiEZHZ` | texte |
| Année de sortie | `fldp6whT8yfZdETi4` | texte (ex. `2023`) |
| Internat | `fld3eO9JuwrHyNkIJ` | select `Oui` · `Non` |
| Diplôme supplémentaire | `fldmi2DQKpPmcpXEV` | texte |
| DESV ? | `fldnvfN95E23ng7ep` | case (pousse l'échelon à 5) |
| Habilitation sanitaire | `fldSIVZ8UxggjhffA` | select `Oui` · `Non` |
| Date de disponibilité | `fldlCCJY7quJEqbyv` | date `YYYY-MM-DD` |
| Rémunération souhaitée | `fldZZj7aCQpzQKgZx` | texte |
| Mobilité | `fldb7cKK29Dv5ncsX` | texte |
| Fréquence tolérable des gardes | `fldZ3kGzgXLhj5UJv` | texte |
| Précisions sur la zone de recherche | `fldDCZKuKUoFfPgSC` | texte long |
| Pratiques maitrisées | `fldsUtHmyFAFyjFgl` | multi (mêmes valeurs que « requises ») |
| Spécialités maitrisées | `flde9dmHJUqdMZIOL` | multi (+ `Epidémiologie`, `Imagerie`) |
| Déjà en contact avec | `fldW10LPhNpiLfNho` | multi (groupements) |
| Temps par semaine | `fldaoQDjYTUGtdK1p` | nombre |
| Forfait | `fld5OZoqKblCo90Xk` | select `Jour` · `Heure` |
| Majoration | `fldgnahnQT3wkydx9` | pourcentage |

« Maitrisées » décrit ce que le candidat **sait faire** ; « requises / optionnelles » ce qu'il
**veut faire**. Seules les secondes entrent dans le matching. Un candidat peut maîtriser le bovin
et ne plus vouloir en faire.

## Champs à ne pas toucher

Formules et lookups : `Noms`, `fullNameSearch`, `ville_departement`, `Echelon`,
`Coefficiant echelon`, `Coefficiant temps de travail`, les trois `Rémunération … CC`, `latitude`,
`longitude`, `Dernier événement`, `Dernière modification (champs propres)`, `Dernière
modification`, `Date de création`, `Numéro (à partir de Posts scrappés)`, les deux
`… (à partir de Candidature)`.

Liens gérés ailleurs : `Candidature`, `Potentielles candidatures`, `Communications`,
`Posts scrappés`, `Localisations`, `Compétences candidat` (se remplit depuis les lignes de la table
`Compétences`), `Régions de recherche`.

Réservés : `Notes` et `Notes du candidat` (voir ci-dessus), `Profil`, `candidat_key` (clé du
scrape), `Appels`, `Candidat entièrement sourcé`, `Sourcing jusqu'au`, `Date prévue d'embauche`,
`Poste visé (site web)`.

---

## Table Compétences — `tblH8Zym1DNu7PN3c`

La grille par acte, écrite à l'ÉTAPE 6 selon les règles de la routine (une ligne = ce candidat, sur
cet acte, à ce niveau). Référentiel `Actes` : `tblt32Afmq6vQ6FJS`, **lecture seule** sauf le champ
`Synonymes`.

| Champ | ID | Type | Valeurs |
|---|---|---|---|
| Candidat | `fldgZcNbLQ9vRF5mU` | lien | `["rec…"]` — jamais `Offre d'emploi` |
| Acte | `fldUZQyIvlhNeZhzG` | lien | un seul acte par ligne |
| Niveau | `fld0SGFcuffxHSSq0` | select | `Autonome` · `Ponctuel` · `En apprentissage` · `Jamais fait` · `Non concerné` |
| Source | `fldBN1P752reydaWJ` | select | **`Extraction IA`** pour une extraction automatique. `Entretien` · `CV` · `Déclaratif candidat` · `Clinique` sont réservés à ce qu'un humain a saisi |
| Commentaire | `fldyRHCFQLear6aNa` | texte long | le verbatim court qui décide, suivi de son origine |
| Écrit par l'IA le | `fld6U06U9wybb90F7` | dateTime | ISO 8601 UTC, **dans le même appel** que `Niveau` — c'est la signature qui rend la ligne réinscriptible |

Ne pas écrire `Désignation`, `Côté`, `Espèce`, `Famille`, `Dernière modification (cotation)`,
`Cotation gelée` : formules et lookups.

Champs du référentiel `Actes` : `Acte` (`fldRieAkhj53QUXn7`), `Espèce` (`fldDB95GQHVopEXB0` —
`Canine` · `Bovins` · `Equine` · `NAC` · `Ovin/Caprin` · `Porcin` · `Volailles` · `Allaitant` ·
`Laitier` · `Loups` · `Transverse`), `Famille` (`fldjYKdy0nenTcZwQ`), `Synonymes`
(`fld8Ep7IUakyLyiYZ` — **seul champ modifiable**, en ajout uniquement), `Notes`
(`fldbcV7A918bBsv9y`).
