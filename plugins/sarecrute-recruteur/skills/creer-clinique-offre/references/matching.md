# Comment les champs de l'offre sont réellement lus par le matching

Deux scripts Airtable produisent les rapprochements. Ils sont **déterministes** : chaque critère
est un filtre éliminatoire, il n'y a pas de score de proximité qui rattraperait un champ mal
rempli.

- **Potentielles candidatures** — offre × Candidats de la base.
- **Potentiels posts candidats** — offre × Posts scrappés « vétérinaire cherche poste ».

Ils tournent dans l'automation `Create potential values [InterfaceOffre]`, déclenchée depuis un
bouton de l'interface Airtable sur la fiche de l'offre, et dans la routine nocturne
`Create potential values [Nocturne 24h]` (3 h, Paris) — mais celle-ci balaie les **candidats et
posts** modifiés dans les 24 h, pas les offres. **Une offre qui vient d'être créée n'est donc pas
rapprochée automatiquement du vivier existant** : il faut lancer le matching depuis la fiche de
l'offre dans l'interface Airtable.

Les deux scripts, en plus de créer les nouvelles paires, **suppriment** les paires non archivées
devenues incompatibles. Corriger un champ mal rempli puis relancer le matching répare donc
proprement — mais efface aussi les paires que le recruteur n'avait pas encore traitées.

---

## Le prérequis absolu : le département

Les deux scripts s'arrêtent net, sans rien créer, si `county` de l'offre est vide :

> `❌ L'offre "…" n'a pas de département (county) défini.`

`county` est un lookup de la clinique. Sur la clinique il est rempli **automatiquement, et
seulement si `Pays` = `France`**, par l'automation `Localisation Clinique [create]` :
elle télécharge un CSV de communes, cherche la ligne dont le nom de ville est **strictement égal**
(en minuscules) à `Ville`, puis écrit `county` + `CP` sur la clinique et `latitude`/`longitude`
sur la Localisation liée.

Trois façons de tuer le matching à la création :

1. **`Pays` vide ou ≠ France** → aucune Localisation, aucun `county`. Pour une clinique suisse ou
   belge, il faut écrire `county` à la main (`Canton de Vaud`, `Province de Liège`…).
2. **`Ville` non trouvée dans le CSV** (abréviation `St`, arrondissement, faute de frappe, nom
   composé mal orthographié) → `county` reste vide. D'où `scripts/ville.py`.
3. **Homonyme** → l'automation prend la **première** ligne du CSV, qui peut être dans un autre
   département. `Sainte-Colombe` existe dans 12 départements. À vérifier avec le CP de l'annonce.

`latitude`/`longitude` ne sont pas éliminatoires côté candidats (le rayon a un repli par zone de
recherche) et ne servent pas du tout côté posts. C'est `county` qui compte.

---

## Pratiques et Spécialités : la double inclusion

```
candidat_dans_offre = toutes les pratiques CHERCHÉES par le candidat ⊂ (requises ∪ optionnelles de l'offre)
offre_dans_candidat = toutes les pratiques REQUISES par l'offre     ⊂ (cherchées ∪ acceptées par le candidat)
compatible          = candidat_dans_offre ET offre_dans_candidat
```

Un côté vide rend la comparaison vraie (`[].every(...)` est vrai). Conséquences, à connaître avant
de remplir :

- **Chaque valeur ajoutée dans « requises » exclut tous les candidats qui ne la cherchent ni ne
  l'acceptent.** Une offre `Pratiques requises = [Canine, Bovins]` élimine tous les purement
  canins. Une clinique mixte qui accepte un profil canin doit donc porter
  `requises = [Canine]`, `optionnelles = [Bovins]` — et non les deux en requises.
- Ne mettre en **requises** que ce que l'annonce impose vraiment ; tout le reste va en
  **optionnelles**, qui n'exclut personne et sert seulement à accueillir les candidats qui le
  cherchent.
- Même règle pour les spécialités : `Spécialités requises = [Chirurgie]` élimine tout candidat qui
  n'a pas coché Chirurgie. Une annonce qui dit « appétence chirurgie appréciée » →
  **optionnelles**, jamais requises.
- Les valeurs `Mixte` et `Rurale` de « Pratiques requises » n'existent pas côté candidat : les
  utiliser en requises ne rapproche personne. Traduire « mixte » en pratiques réelles
  (`Canine` + `Bovins`/`Laitier`…).
- Le champ contient des doublons historiques (`volailles` / `Vollaile`). Choisir `volailles`.

## Expérience requise : une échelle, pas un libellé

| Expérience requise de l'offre | Candidats retenus |
|---|---|
| vide | tous |
| `Etudiant` | tous |
| `Débutant` | `Débutant`, `1 à 2 ans`, `Autonome` |
| `1 à 2 ans` | `1 à 2 ans`, `Autonome` |
| `Autonome` | `Autonome` seulement |
| `Spécialiste` | **aucun** |

`Spécialiste` tombe dans le `return false` final du script : la poser **annule tout le matching**
de l'offre. Ne jamais l'utiliser. Pour un poste spécialisé, mettre `Autonome` + la spécialité en
requise.

Corollaire : `Débutant` est le réglage le plus ouvert utile. Une annonce qui accepte les jeunes
diplômés doit porter `Débutant`, pas `Autonome`.

## Statuts contractuels, Type de temps de travail, Langues

Règle « au moins une valeur commune », **mais un côté vide vaut compatible** :

- `Statuts contractuels` vide sur l'offre → aucun filtre sur le contrat. Renseigné, il exclut les
  candidats qui ne cherchent aucun de ces statuts.
- Idem `Type de temps de travail`. Une annonce ouverte aux deux → cocher les deux, ce qui est plus
  large que de n'en cocher aucun côté visibilité recruteur, et équivalent côté matching.
- Ne pas deviner : mieux vaut vide qu'une valeur inventée qui exclut.

## Logement

Exclut seulement quand l'offre dit `Non` **et** que le candidat exige un logement. Donc :

- l'annonce mentionne un logement → `Oui` ;
- l'annonce dit explicitement qu'il n'y en a pas → `Non` ;
- l'annonce n'en parle pas → **laisser vide** (mettre `Non` par défaut écarterait sans raison
  les candidats qui en ont besoin).

## Champs portés par la clinique et lus sur l'offre

| Champ (clinique) | Effet sur le matching |
|---|---|
| `Taille de clinique` | si renseignée et que le candidat a une liste de tailles souhaitées, elle doit y figurer. **Renseignée à tort = exclusions silencieuses.** Laisser vide si l'annonce ne dit rien |
| `Clinique de référé` | n'exclut que si les deux côtés sont renseignés et diffèrent. `Non` est la valeur usuelle |
| `Groupement` | l'offre en dérive un `Oui`/`Non` **toujours non vide**, comparé au `Groupe souhaité` du candidat. Nommer un groupement exclut donc les candidats qui n'en veulent pas — c'est l'effet attendu, mais ne nommer un groupe que si l'annonce le dit |
| `Intérêt géographique` | « au moins une valeur commune », vide = permissif |

## Côté géographie du candidat

Compatible si **l'une** des deux conditions est vraie :

- distance haversine clinique ↔ candidat ≤ `acceptable_distance_from_home (km)` du candidat
  (50 km par défaut) — nécessite `latitude`/`longitude` des deux côtés ;
- ou une `Zone de recherche` du candidat correspond au `county` de l'offre (avec les
  équivalences `France` → tout département numéroté, `Suisse` → `Canton …`,
  `Belgique` → `Province …`).

## Côté Posts scrappés

Plus strict : la correspondance de zone est **obligatoire** (aucun repli par distance), puis
`Expérience`, `Pratiques`, `Spécialités`, `Statuts contractuels`, `Type de temps de travail` avec
les mêmes règles que ci-dessus. Le nombre de critères qui se recoupent est stocké dans
`Critères compatibles`, et le statut initial du match est `À traiter`.

---

## Récapitulatif : les champs qui décident du matching

Sur la clinique : `Pays`, `Ville` (→ `county`, `CP`, coordonnées), et éventuellement `county` à la
main hors France ; `Taille de clinique`, `Clinique de référé`, `Groupement`,
`Intérêt géographique`.

Sur l'offre : `Pratiques requises` / `optionnelles`, `Spécialités requises` / `optionnelles`,
`Expérience requise`, `Statuts contractuels`, `Type de temps de travail`, `Logement`.

Tout le reste (`Annonce`, `Questions`, `Rémunération`, dates, liens, contacts) est de
l'information pour le recruteur : utile, mais sans effet sur les rapprochements.
