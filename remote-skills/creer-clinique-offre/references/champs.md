# Champs Airtable — Cliniques et Offres d'emploi

Base **PROD** « Recrutement vétérinaire » : `appP0W2ISytaNyAhG`.

Toujours écrire par **ID de champ** et **sans `typecast`**. Une valeur de select absente de la
liste ci-dessous fait échouer l'écriture — c'est voulu : on ne crée jamais de nouvelle valeur de
select (ni via `typecast`, ni via `update_field`). Si l'annonce ne rentre dans aucune valeur
existante, on laisse le champ vide et on le signale au recruteur.

---

## Table Cliniques — `tblagWImxHH15rRAh`

### À remplir à la création

| Champ | ID | Type | Quoi y mettre |
|---|---|---|---|
| Nom de la clinique | `fldHJd3Ts1vfLn4TQ` | texte | nom exact de la structure. **Champ primaire** |
| Ville | `fldf8t2ihJMGnh7wz` | texte | orthographe validée par `scripts/ville.py` (voir SKILL.md) |
| Pays | `fld5COKjkzYSSKA98` | select | `France` \| `Suisse` \| `Belgique` \| `Espagne` \| `Luxembourg`. **Obligatoire** |
| county | `fldgsRdtLrBThQfb1` | select | **ne pas écrire si Pays = France** (l'automation le remplit). À écrire à la main sinon |
| CP | `fldDXSlaKMWl2wTnc` | texte | idem : écrasé par l'automation si Pays = France |
| Nom du vétérinaire | `fldLUWwSfCGb99kxc` | texte | Dr / gérant signataire de l'annonce |
| Contact non véto | `fldMSNUy9rIiycyqq` | texte | si le contact de l'annonce est ASV / RH / office manager |
| Mail1 | `fldIrQarKGnhq3g76` | email | e-mail principal de l'annonce |
| Mail2 | `fldjg9sc0KdWi6I4O` | email | second e-mail si l'annonce en donne deux |
| Téléphone | `fld0bMHIpnFrh4nOs` | texte | tel qu'écrit dans l'annonce |
| Canal de contact | `fld8Pe9yuKw9P89W1` | select | `Mail` \| `Linkedin` \| `Messenger` \| `Téléphone` |
| Status commercial | `fldyfue6Bm95TR9vC` | select | `A contacter` à la création (voir liste complète plus bas) |
| Profil Facebook | `fldm1LEvy0D3Siz5u` | url | profil/page de l'auteur de l'annonce |
| Profil LinkedIn | `fldWyltUYXGcwSo90` | url | |
| Groupement | `fldtzraNljgAQj6KF` | select | seulement si l'annonce nomme le groupe (liste fermée plus bas) |
| Pratiques | `fldYQFC4sx2pV0ffx` | multi | activité de la structure (≠ pratiques du poste, qui vont sur l'offre) |
| Spécialités | `fldlnfxU1vPcXso4Q` | multi | plateaux/spécialités de la structure |
| Clinique de référé | `fldqPvfT0Zw7vaoPP` | select | `Oui` \| `Non` — met `Non` sauf mention de référé |
| Taille de clinique | `fldLvG3FUuyQgifEf` | select | `Petite` \| `Moyenne` \| `Grande` — **laisser vide si l'annonce ne le dit pas** |
| Intérêt géographique | `fldR3vmorlt2RISu0` | multi | `Alpes` \| `Pyrénées` \| `Méditerranée` \| `Océan Atlantique Sud-Ouest` \| `Océan Atlantique Nord-Ouest` \| `Campagne` \| `Grande ville` |
| Engagement du lead | `fldhpCvHu3yN8lS70` | select | `Froid` \| `Tiède` \| `Chaud` — `Froid` pour une annonce trouvée, `Tiède` si la clinique a écrit la première |
| Notes | `fldJIET4sokOxl5f7` | richText | contexte + **texte intégral de l'annonce** et sa provenance |
| Propriétaires du client | `fldOCZHesfhv1TO20` | collaborateurs | `[{"email": "<email du recruteur>"}]` |
| Appels | `fldsqgo2tdPz6INFe` | texte | laisser vide |

### Valeurs des selects fermés

- **Status commercial** : `A contacter` · `En attente de 1ere réponse` · `En attente 1ère rép - 1ère relance` · `Contact établi` · `En discussion` · `En discussion - 1ère relance faite` · `En discussion - 2ème relance faite` · `Signé` · `Nurturing` · `Annonce plus dispo` · `Refusé`
- **Groupement** : `VetPartners` · `Vetmint SA` · `FOVEA` · `Dr Milou` · `SEVETYS` · `MonVeto` · `QOVETIA` · `IVC Evidensia` · `Argos` · `Smartemis` · `VPLUS` · `Univet` · `vet&Go`
- **Pratiques** (clinique) : `Canine` · `Equine` · `NAC` · `Bovins` · `Loups` · `Oiseaux` · `Porcin` · `Volaille` · `Ovin` · `Caprin`
- **Spécialités** (clinique) : `Chirurgie` · `Urgences` · `Laboratoire` · `Orthopédie` · `Echographie` · `Ophtalmologie` · `Ostéopathie` · `Management` · `Cardiologie` · `Reproduction` · `Oncologie` · `Médecine interne` · `Anatomie Pathologique`
- **county** : `01 - Ain` … `95 - Val-d'Oise`, `971 - Guadeloupe`, `972 - Martinique`, `973 - Guyane`, `974 - La Réunion`, `974 - Mayotte`, puis `Canton de Genève` · `Canton de Berne` · `Canton de Vaud` · `Canton de Neuchatel` · `Canton de Fribourg` · `Canton du Valais` · `Province de Liège` · `Province d'Anvers` · `Province de Bruxelles`.
  Le libellé français exact est celui de la colonne `departement` du CSV — `scripts/ville.py` le renvoie déjà au bon format.

### Champs à ne pas toucher

`Prochaine action` / `Date prochaine action` (posés par l'automation « Set 1ere relance when
create clinique »), `intro_at`, `reminder_at`, `Date propal`, `replied?`, `archived`,
`Localisations`, `latitude`, `longitude`, tous les `delay_*`/`pretty_*`, `Short name`,
`Nombre d'offres d'emploi`, `Factures`, `Communications`, `Poste vétérinaire`.

---

## Table Offres d'emploi — `tblVZva5yHSCnucsK`

Le champ primaire `Name` est une formule (nom de la clinique + `Second name`) : rien à écrire.

### Structurants pour le matching — voir `references/matching.md`

| Champ | ID | Type | Valeurs |
|---|---|---|---|
| Clinique | `fldtUGOTlzMmBrrx9` | lien | `["rec…"]` — **obligatoire** |
| Emploi recherché | `fldC1pPXhUzhDh6Qj` | select | `Vétérinaire` \| `ASV` |
| Pratiques requises | `fldgYo4mPQjxqPen4` | multi | `Canine` · `NAC` · `Equine` · `Bovins` · `Oiseaux` · `Allaitant` · `Laitier` · `Ovin` · `Caprin` · `Porcin` · `volailles` · `Vollaile` · `Mixte` · `Rurale` |
| Pratiques optionnelles | `fld8BRQsnbvz7UpKM` | multi | idem sans `Mixte`/`Rurale` |
| Spécialités requises | `fldfxUJuNO2kkstGq` | multi | `Chirurgie` · `Urgences` · `Orthopédie` · `Ophtalmologie` · `Echographie` · `Ostéopathie` · `Management` · `Cardiologie` · `Reproduction` · `Oncologie` · `Médecine interne` · `Anatomie Pathologique` · `Neurologie` |
| Spécialités optionnelles | `fldUJWi2hIVuf5OPF` | multi | idem |
| Expérience requise | `fldJiOMS63jUDSsz6` | select | `Etudiant` \| `Débutant` \| `1 à 2 ans` \| `Autonome` \| `Spécialiste` |
| Statuts contractuels | `fldDUXxile41HOLbD` | multi | `CDI` · `CDD` · `Association` · `Vacataire` · `Salarié` · `Collaboration libérale` · `Internat` · `Prophylaxie` · `Achat/Vente de clinique` |
| Type de temps de travail | `fldv1Ajitw8BTejsd` | multi | `Temps plein` · `Temps partiel` |
| Gardes | `fldaeLw3kyhReMCCp` | select | `Oui` \| `Non` |
| Logement | `fldQp3HD2aNtBX8t1` | select | `Oui` \| `Non` |
| Langues requises | `fldfEwntfKHQS1tVb` | multi | `Français` · `Espagnol` · `Anglais` · `Allemand` |

### Informatifs

| Champ | ID | Type | Quoi y mettre |
|---|---|---|---|
| Annonce | `fldLIH3nwT4p9uhHC` | texte long | **texte intégral de l'annonce**, jamais tronqué |
| Questions | `fldMw26Azh3ZyT0Cg` | texte long | questions à poser à la clinique (une par ligne, préfixées `- `) |
| Lien de l'offre (FB/LinkedIn...) | `fldzuEBZkX6jQNeSS` | url | lien du post d'origine |
| Date de publication | `fldH4usQBpHkdNQJ3` | date | `YYYY-MM-DD`, date de parution de l'annonce |
| Date de démarrage | `fldm2dcrjrYxG8E3v` | date | prise de poste souhaitée |
| Date de fin (si CDD) | `fldQ4c5kxfZLlqFH1` | date | |
| Fréquence des gardes | `fld9R5EVefQSKWknP` | texte | ex. « 1 week-end sur 4 » |
| Rémunération | `fldEa1Kc6pL40u8n2` | texte | ce que dit l'annonce. **Interne — jamais publié** |
| Second name | `fldqXF6HUy6GRRUVi` | texte | seulement si la clinique a plusieurs offres (ex. `Rural`, `Temps partiel`) |
| Contrat court | `fldSRaHJgSv9bwr1q` | case | cocher pour un remplacement / vacation courte |
| Notes | `fldxzx6oC1zsF3aug` | richText | notes internes |
| Responsable de l'offre | `fldPqVh2fe65tIct2` | collaborateur | `{"email": "<email du recruteur>"}` |
| Propriétaire de l'offre | `fldERU7fexhGsuZJ3` | collaborateur | `{"email": "<email du recruteur>"}` |
| Observateurs de l'offre | `fld4kPI6CoaQaPcsH` | collaborateurs | laisser vide |

### Champs à ne pas toucher

`Archivée ?`, `Description du poste`, `Description courte du poste`, `Texte de publication`,
`Image de publication`, `url image publication` (remplis plus tard, au moment de la publication),
et tous les lookups/rollups (`county`, `latitude`, `longitude`, `Ville (from Clinique)`,
`Status commercial (from Clinique)`, `Taille de clinique`, `Clinique de référé`, `Groupement`,
`Intérêt géographique`, `Nombre de publications`, `Candidatures`, `Potentielles candidatures`,
`Potentiels posts candidats`, `Campagnes`, `Posts scrappés`, `Factures`).

---

## Champs collaborateur

Les trois champs d'attribution — `Propriétaires du client` sur la clinique,
`Responsable de l'offre` et `Propriétaire de l'offre` sur l'offre — s'écrivent par e-mail :

```json
{"email": "prenom@exemple.fr"}
```

et pour le champ multi-collaborateurs de la clinique, `[{"email": "prenom@exemple.fr"}]`.
Écrire par e-mail plutôt que par identifiant `usr…` évite de tenir une liste à jour dans ce
fichier (vérifié : Airtable résout l'e-mail en collaborateur à l'écriture).

L'e-mail vient de l'étape 1 du PROMPT : fichier local `$HOME/.sarecrute/recruteur.json`, sinon la
table **`Recruteurs`** (`tblDUpPwkuHYnAPyt`) — `Nom` `fldwLiZVl731wiI4o`, `Email` `fld4ETJcqeL3e2Ur0`
(le collaborateur Airtable, celui qu'on écrit ici), `Email compte Claude` `fldaxrZ7PftpZQQfl` (la
clé de comparaison avec l'utilisateur de la session ; seul champ que la compétence écrit, si
vide), `Actif` `fldscrgHc1n9M60XZ`. Si l'e-mail retenu n'est pas celui d'un collaborateur de la
base, l'écriture échoue : c'est la ligne `Recruteurs` qui porte un mauvais `Email`, le dire. Pour retrouver les collaborateurs existants sans quitter Claude, lire les
champs `Responsable de l'offre` (`fldPqVh2fe65tIct2`) et `Propriétaire de l'offre`
(`fldERU7fexhGsuZJ3`) de quelques offres récentes : la valeur renvoyée contient `name`, `email`
et `id`.
