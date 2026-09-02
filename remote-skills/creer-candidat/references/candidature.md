# L'offre visée : pratiques, contrôle du matching, candidature

Référence de l'ÉTAPE 7 du PROMPT. Ne sert que si le recruteur a **désigné une offre** (« arrivée
par mail sur l'annonce Hedera », « postule chez X »). Sans offre nommée, l'étape est sautée : on ne
devine jamais l'offre depuis le texte d'une source.

Base **PROD** `appP0W2ISytaNyAhG` · Offres `tblVZva5yHSCnucsK` · Candidatures `tbl3LnGoBxnheGI7v` ·
Potentielles candidatures `tblVFAcFwcitGLdJW`.

Toujours par **ID de champ**, **sans `typecast`**.

---

## Retrouver l'offre — table Offres d'emploi

| Champ | ID | Usage |
|---|---|---|
| Nom de la clinique | `fldl4VMacV8OsoHvF` | formule — la clé de recherche (`search_records`, `fields: "ALL_SEARCHABLE_FIELDS"`) |
| Second name | `fldqXF6HUy6GRRUVi` | distingue deux offres d'une même clinique |
| Archivée ? | `fldsyc8RzbIyiH4mZ` | ne retenir que les offres **non archivées** |
| Pratiques requises | `fldgYo4mPQjxqPen4` | → candidat (voir plus bas) |
| Pratiques optionnelles | `fld8BRQsnbvz7UpKM` | → candidat, optionnelles seulement |
| Spécialités requises / optionnelles | `fldfxUJuNO2kkstGq` / `fldUJWi2hIVuf5OPF` | **lecture seule, pour le contrôle** — jamais recopiées sur le candidat |
| Expérience requise | `fldJiOMS63jUDSsz6` | contrôle : `Etudiant` · `Débutant` · `1 à 2 ans` · `Autonome` · `Spécialiste` |
| county | `fld8ja3Moe2jkF0kE` | lookup clinique — contrôle géographique |
| Responsable de l'offre | `fldPqVh2fe65tIct2` | information : à qui appartient l'offre |

- **Une seule offre non archivée** trouvée → continuer.
- **Plusieurs** (deux offres d'une même clinique, ou deux cliniques au nom proche) → les montrer
  (nom, second name, pratiques, expérience requise, responsable) et demander laquelle. C'est la
  seule question de cette étape.
- **Aucune** → le dire, proposer `creer-clinique-offre`, et **sauter le reste de l'étape**. Ne pas
  créer d'offre ici.

## Les pratiques de l'offre → la fiche du candidat

Exception explicite, et bornée, à la règle « une annonce de clinique n'est pas une source
candidat » : **postuler à un poste canin, c'est dire qu'on veut faire du canin.** C'est une
déclaration du candidat, pas le plateau technique de la clinique.

| Notion | Depuis l'offre visée ? | Pourquoi |
|---|---|---|
| **Pratiques (espèces)** | **oui** | l'espèce d'un poste auquel on postule est un choix du candidat |
| Spécialités | **non** | ce qu'une clinique propose ne dit rien de ce qu'un candidat sait faire ; la barre des spécialités reste celle de la doctrine (preuve exigée) |
| Actes (grille `Compétences`) | **non** | « le plateau technique n'est pas une compétence » — un poste qui fait des césariennes ne cote rien |

Règles d'écriture, dans l'ordre :

1. **Les sources du candidat priment.** Cette recopie ne tourne qu'**après** l'ÉTAPE 6 et ne touche
   que des champs **vides**. Si le CV, le transcript ou le post ont donné des pratiques, l'offre
   n'ajoute rien en requises : une requise de plus **exclut** des offres, et le candidat a dit ce
   qu'il voulait.
2. `Pratiques requises` de l'offre → `Pratiques requises` (`fldKxF494zI5Kgc6n`) **et**
   `Pratiques maitrisées` (`fldsUtHmyFAFyjFgl`) du candidat, si vides. C'est ce que fait déjà
   l'automation « Convert post to candidat » pour un post.
3. `Pratiques optionnelles` de l'offre → `Pratiques optionnelles` (`fld6tibAOw9YfzkuI`) du
   candidat, **en ajout** (ce champ n'exclut jamais personne). Jamais en maitrisées : « la
   clinique fait aussi du NAC » ne dit pas que le candidat en sait faire.
4. **Recopie 1 pour 1**, sans mapping : les dix valeurs (`Canine` · `Bovins` · `Equine` · `NAC` ·
   `Allaitant` · `Laitier` · `Ovin/Caprin` · `Porcin` · `Loups` · `Volailles`) sont identiques dans
   les deux tables depuis le 31/08/2026. Une valeur qui manquerait côté Candidats : la laisser et
   le signaler, jamais `typecast`.
5. Le dire dans le compte rendu : « Pratiques posées depuis l'offre Hedera : Canine (requise +
   maîtrisée), NAC (optionnelle) ».

## Ce que dirait le matching — trois contrôles, aucun bloquant

À faire **avant** de créer la candidature, avec les règles de `champs-candidat.md`. Un écart
n'empêche rien : le recruteur a décidé de présenter ce candidat, la candidature se crée. Mais
**chaque écart est signalé en ⚠️** dans le récapitulatif avant feu vert et dans le compte rendu.
C'est le « Julie a 1 an, Hedera demande 1 à 2 ans minimum » que le recruteur veut voir avant de
présenter.

| Contrôle | Règle | Écart à signaler |
|---|---|---|
| **Expérience** | candidat retenu si son `Expérience` est **au moins** celle requise, sur l'échelle `Etudiant < Débutant < 1 à 2 ans < Autonome` ; vide côté candidat = `Débutant` ; `Spécialiste` requis ne retient personne | « Expérience : <candidat> pour une offre qui demande <requis> » |
| **Pratiques** | double inclusion : requises du candidat ⊂ (requises ∪ optionnelles de l'offre) **et** requises de l'offre ⊂ (requises ∪ optionnelles du candidat) ; un côté vide = vrai | « Pratiques : l'offre exige <X>, absent de la fiche » ou l'inverse |
| **Géographie** | `county` de l'offre présent dans `Zones de recherche` du candidat (avec `France` → tout département), **ou** ville géocodée des deux côtés | « Zone : l'offre est en <county>, hors des zones du candidat » — ou « pas de zone ni de ville côté candidat : le matching ne le trouvera pas » |

Les spécialités **requises** de l'offre se lisent aussi, pour information seulement : « l'offre
exige Chirurgie, la fiche n'en porte pas » — sans jamais les poser sur le candidat.

## Créer la candidature — table Candidatures

### D'abord : existe-t-elle déjà ?

`list_records_for_table` sur `tbl3LnGoBxnheGI7v` filtré sur `Candidat` (`fldIk7cKNui6UXCgp`) **et**
`Offre d'emploi` (`fldLif0bwmAjllfu1`), comme le font les automations « Transformation en
candidature ». Si une ligne existe : **ne rien créer**, la montrer (statut, prochaine action,
propriétaire) et passer à l'archivage de la paire potentielle.

⚠️ Les deux filtres doivent porter une valeur : un filtre à valeur vide est ignoré et renverrait
toute la table.

### Les champs

| Champ | ID | Valeur |
|---|---|---|
| Candidat | `fldIk7cKNui6UXCgp` | `["rec…"]` — le candidat de l'ÉTAPE 5 |
| Offre d'emploi | `fldLif0bwmAjllfu1` | `["rec…"]` — l'offre retrouvée |
| Propriétaire de la candidature | `fldi2CuWMAAZVGrQI` | `{"email": "…"}` — **le recruteur de l'ÉTAPE 1**, pas le responsable de l'offre |
| Statut candidature | `fldiYea1jiErQf4DY` | voir la grille ci-dessous |
| Prochaine action | `fldHoAtNQBKKNdnIM` | idem |
| Date prochaine action | `fld5JiNeF9RS5SSsM` | `YYYY-MM-DD`, aujourd'hui sauf indication du recruteur |

**Ne jamais écrire** : `Notes` (`fldvIrOrRNwFsAeHI`), `Notes du recruteur` (`fldcDGAILdxSjqnFB`),
`Notes de la clinique` (`fldUF6Dlh7waWd8Nf`) — espaces du recruteur et de la clinique ; `Profil
du candidat` (`fldAI7g8EbZO9XC77`, copié par l'automation « Update Profil [create candidature] ») ;
`Statut de la candidature pour la clinique` (`fldp8BS6lRiX2rdRp`, posé par « Set Candidature
status for clinic ») ; `Archivée` ; `Type de nurturing` ; les dates `intro_*` / `reminder_*` ;
toute formule ou lookup.

### Statut et prochaine action — une grille, pas une question

Le statut se déduit de **comment le candidat arrive**. Le montrer dans le récapitulatif avant feu
vert avec la valeur retenue ; le recruteur la change en un mot. Pas de question séparée.

| Situation | Statut candidature | Prochaine action | Date |
|---|---|---|---|
| Le candidat a postulé lui-même (mail de candidature, message, réponse à l'annonce) | `Candidat postulé` | `Proposer le candidat à la clinique` | aujourd'hui |
| Le recruteur a eu le candidat et il est d'accord pour être présenté | `Candidat intéressé` | `Proposer le candidat à la clinique` | aujourd'hui |
| Le recruteur veut d'abord lui parler du poste | `Candidat à contacter` | `Proposer au candidat` | aujourd'hui |
| Le recruteur lui a déjà proposé le poste, attend sa réponse | `En attente 1er retour candidat` | **ne rien écrire** | **ne rien écrire** |

Le dernier cas est le seul que l'automation « Set 1ère relance when create candidature » traite :
sur ce statut, elle pose elle-même `Relancer le candidat` et la date de création + 7 jours. Écrire
la prochaine action soi-même la ferait écraser. Pour tous les autres statuts l'automation ne fait
rien, c'est à la compétence de remplir les deux champs.

Valeurs du select `Statut candidature`, pour mémoire : `Candidat à contacter` · `En attente 1er
retour candidat` · `Candidat relancé` · `Candidat intéressé` · `Candidat postulé` · `Candidat
postulé - 1ere relance` · `En process` · `Candidat indécis` · `Nurturing` · `Candidat embauché` ·
`Perdu de vue` · `Refusé par le candidat` · `Refusé par la clinique` · `Déjà en contact avec
clinique` · `Pas pertinent`. `Prochaine action` : `Proposer au candidat` · `Relancer le candidat` ·
`Proposer le candidat à la clinique` · `Relancer la clinique` · `Archiver la candidature`.

### Ensuite : la paire potentielle

Si une ligne de `Potentielles candidatures` (`tblVFAcFwcitGLdJW`) porte ce couple — `Offre
d'emploi` `fldXVOrUdEnoxkRXt` et `Candidat` `fldOfcm7ifjdtDjU2` — cocher `archived?`
(`fldvtoqLTjsE6YU2G`). Sinon la même personne serait proposée deux fois au recruteur, une fois en
potentielle et une fois en candidature. Sur un candidat créé à l'instant il n'y a en général
aucune paire (le matching n'a pas encore tourné) : l'absence est normale, ne pas la signaler.

## Compte rendu de l'étape

- l'offre retrouvée (nom, second name, recordId) — ou « offre non trouvée, rien créé » ;
- les pratiques posées depuis l'offre, champ par champ — ou « rien posé, la fiche en avait déjà » ;
- les trois contrôles, avec les ⚠️ ;
- la candidature créée (recordId, statut, prochaine action) — ou la candidature existante trouvée ;
- la paire potentielle archivée, s'il y en avait une.
