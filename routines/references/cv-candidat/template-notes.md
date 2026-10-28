# Dossier de présentation candidat — notes de maintenance du template

Document de maintenance, **pas un prompt** : la routine `routines/cv-candidat.md` ne le lit pas. Il
rassemble ce que Léo a appris en construisant `cv-template.html` (compétence `creer-cv-candidat`,
versions 0.1 à 0.5, août–octobre 2026), pour que personne ne refasse les mêmes essais. Le template
n'est plus rempli à la main : `routines/scripts/cv_candidat.py` recopie les champs Airtable dans le
bloc de données, et `routines/scripts/cv_pdf.js` imprime.

## Le template existe — ne le reconstruis pas

`cv-template.html` est validé : une page A4 tenue aussi bien par une fiche vide que par un bilan de
136 actes sur huit espèces. Il embarque l'auto-ajustement, l'anonymisation, le bilan en jauges et les
états vides. On remplace ce qui est entre `/*DATA-START*/` et `/*DATA-END*/`, et c'est tout. Ne
touche à aucune règle CSS : reconstruire un template à chaque dossier produit des documents qui
dérivent visuellement les uns des autres, exactement ce que la standardisation cherche à éliminer.

`cv-standard-modele.js` est le bloc de données du **modèle vierge** : aucun nom de personne, chaque
ligne portant en guise de valeur le nom du champ Airtable qui l'alimente, et le référentiel complet
des actes (table `Actes`, `tblt32Afmq6vQ6FJS`) coté `"Non évalué"`. Il sert à montrer le standard,
à vérifier une modification du template, et comme jeu d'essai de densité maximale. Ses
valeurs-repères doivent rester aussi courtes qu'une vraie valeur : une explication gonfle la colonne
latérale, fait chuter l'échelle, et le modèle cesse de ressembler aux dossiers qu'il représente.

## Les champs du dossier et leur source Airtable

| Bloc du dossier | Champ Airtable (table `Candidats`, `tblPmkTaAjS9Yoovt`) |
|---|---|
| Prénom / Nom | `fld1WR6pNpe8sAya6` / `fld6yzzWrqBZBtXly` |
| Sous-titre | `Emploi recherché` + `Pratiques requises` + `Années d'expérience` |
| Accroche | quatre lignes rédigées depuis `Profil`, `Notes`, `Notes du candidat`, `Transcripts` — jamais `Profil IA`, jamais le CV |
| Contact | `Mail`, `Téléphone` — **et rien d'autre : pas de localisation** |
| Cadre recherché | `Années d'expérience`, `Date de disponibilité`, `Statuts contractuels souhaités`, `Type de temps de travail`, `Gardes` + `Fréquence tolérable des gardes`, `Rémunération souhaitée` |
| Domaines maîtrisés | `Pratiques maitrisées` + `Spécialités maitrisées` |
| Domaines recherchés | `Pratiques requises` + `Spécialités requises` |
| Formation et diplômes | `Ecole véto`, `Année de sortie`, `Internat`, `DESV?`, `Diplôme supplémentaire`, `Habilitation sanitaire` |
| Langues | `Langues` — noms seuls, jamais de niveau |
| Compétences vérifiées | table `Compétences` (`tblH8Zym1DNu7PN3c`), un enregistrement par acte, avec `Espèce` et `Famille` (lookups de l'acte) |
| Parcours | table `Expériences` (`tblTYdApkiHqKeBVi`) : `Poste`, `Structure`, `Période`, `Durée`, `Description` sans la mention de source entre parenthèses |

Les identifiants exacts sont dans `cv_candidat.py` (dictionnaires `F`, `FC`, `FA`, `FE`) : c'est lui
qui fait foi, cette table n'est qu'une lecture humaine.

Décisions qui tiennent :

- **`Statut Recherche` et `En poste ?` ne figurent pas** (07/09/2026) : un dossier qui circule chez une
  clinique n'a pas à exposer la situation courante du candidat, et ces lignes se périmaient entre
  l'envoi et la lecture.
- **Pas de localisation**, nulle part : ni `Ville`, ni `Département`, ni `CP`, ni la ville citée dans
  `Précisions sur la zone de recherche`.
- **`mobilite` ne se renseigne pas** (27/08/2026). La clé existe dans le bloc et la ligne s'afficherait,
  mais la zone de recherche se discute de vive voix.
- **`Internat`, `DESV?`, `Habilitation sanitaire` ne s'affichent que positifs.** Une valeur exactement
  « Oui » sort en pastille verte portant son intitulé ; une valeur détaillée garde son bloc intitulé +
  texte ; « Non » n'apparaît jamais.
- **`Echelon` et `Rémunération brute mensuelle CC`** sont des calculs internes de convention
  collective : jamais dans le dossier.
- **Le parcours** : postes en clinique un par ligne, du plus récent à plus ancien ; stages, jobs
  étudiants et postes hors clinique regroupés sur une ligne finale (période couverte et nombre de
  postes, sans durée cumulée : plusieurs expériences sont cotées « moins d'un mois », une somme
  produirait un chiffre que la base ne dit pas). Depuis le 15/10/2026 le parcours est une **frise** :
  colonne de gauche (27 mm) avec la durée en gras et la période en gris dessous, à droite l'intitulé
  et la structure sur une ligne pleine largeur puis la description. Les durées se comparent en
  colonne, et un intitulé long n'est plus cassé en deux par une date (« Remplacements vétérinaires
  canins » tenait sur deux lignes à côté de deux noms de structure).
- **La colonne latérale** (révision du 15/10/2026) : contact sans intitulés (un e-mail et un numéro
  se reconnaissent seuls) ; dans « Cadre recherché », intitulé et valeur **sur la même ligne** quand
  les deux sont courts (intitulé ≤ 13 caractères, valeur ≤ 18, classe `.kv.long` sinon, qui
  reprend la forme empilée). La carte du cadre passe de douze lignes à huit, et c'est elle qui
  bridait la page : les millimètres rendus ont financé un corps de texte plus grand partout (actes
  8,4 → 9,2 px, descriptions 7,9 → 8,6 px en gris plus foncé, accroche 9,6 → 10,2 px et fer à
  gauche au lieu de justifié, valeurs 9,2 → 9,6 px). Tailles de base, avant `--scale`.

## Le bilan de compétences : un acte par ligne, noté sur trois points

Chaque acte porte une **jauge de trois crans**, placée **devant** l'intitulé (révision de lisibilité
du 15/10/2026 : à droite, sur une colonne pleine largeur, dix centimètres séparaient l'acte de son
niveau ; devant, elle se lit comme une puce et les jauges restent alignées en colonne). C'est la
table `NIVEAUX` en tête du template :

| Niveau Airtable | Crans | Couleur |
|---|---|---|
| `Autonome` | ●●● | vert |
| `Ponctuel` | ●●○ | orange |
| `En apprentissage` | ●○○ | or |
| `Jamais fait` | ○○○ | gris |
| `Non évalué` | ○○○ tireté | réservé au modèle vierge, n'existe pas dans Airtable |
| `Non concerné` | — | non affiché |

Les décomptes restent sur trois états (« 11 acquis · 7 en cours »), parce que c'est ce qu'une
clinique compte. Le regroupement est à deux niveaux, **espèce puis famille d'actes** ; l'ordre des
familles suit le référentiel Airtable (constante `FAMILLES` en tête du moteur), pour qu'un chirurgien
et un rural présentent leurs actes dans le même ordre. **Les « non acquis » s'affichent**, et c'est
délibéré : l'honnêteté sur les limites est ce qui rend le reste crédible.

Deux mises en page selon la densité, décidées par le seul nombre d'actes (`.bilan.mono` à 24 au
plus) :

- **24 actes au plus — tableau** : la famille est un intitulé à gauche (32 mm, capitales grises),
  ses actes coulent à droite, plusieurs par ligne, un filet entre deux familles. Dix actes ne
  justifient pas sept bandeaux pleine largeur : avant le 15/10/2026, le dossier de Manon
  Lecarpentier (10 actes, 7 familles) était une pile de bandeaux à un acte chacun.
- **Au-delà — deux colonnes typographiques**, un acte par ligne sous un bandeau de famille sur fond
  sauge (c'est le bandeau qui permet d'aller droit à « imagerie » sur cinquante actes). Le modèle
  vierge (53 actes) sort ainsi à l'échelle 0,98.

## La contrainte qui structure tout : une seule page A4

`@page { size: A4; margin: 0; }`. Le contenu ne doit jamais déborder sur une deuxième page, ni pour
une fiche à peine qualifiée, ni pour 136 actes sur huit espèces. D'où la routine d'auto-ajustement :
après rendu, mesurer la hauteur réelle et faire varier `--scale` **de 1.11 vers 0.82 par pas de
0.01**, en retenant la première valeur qui ne déborde pas. Si 0.82 déborde encore, le rendu bascule
du mode `chips` au mode `compact` (une ligne de texte par état et par espèce, sans intitulé de
famille) et la boucle recommence.

**1.11 n'est pas arbitraire : c'est le format commun.** Le plafond est calé pour qu'une fiche
complète l'atteigne elle aussi ; la quasi-totalité des dossiers sortent donc à la même taille de
texte. Ne le remonte pas pour faire respirer un dossier léger : tu rendrais les dossiers inégaux.
Pour rendre un dossier plus lisible, le levier est la taille de base des règles CSS (ce qui a été
fait le 15/10/2026), pas le plafond. Mesures après cette révision : Lecarpentier 1,11 (latérale
669 px pour 763), modèle vierge 0,98, jeu d'essai 136 actes / 8 espèces 1,00 en compact.

**Une mesure prise trop tôt est fausse, et elle se fige.** Si la routine mesure avant le chargement
des polices, elle trouve un débordement énorme, descend au plancher et n'y revient jamais. Trois
protections, les trois nécessaires :

- `renderMain("chips")` est appelé une fois, immédiatement, hors de la routine d'ajustement. Quand
  le seul appel vivait dans `fit()`, une routine qui n'aboutissait pas laissait le PDF **sans sa
  colonne principale**, invisible à l'écran.
- Plusieurs passes (`document.fonts.ready`, `load`, `setTimeout`), qui ne transitent pas toutes par
  `requestAnimationFrame` : à l'impression, sous `--virtual-time-budget`, rAF peut n'être jamais servi.
- Un garde-fou de préparation (`document.fonts.status === "loaded"`, page avec une hauteur), sauf la
  passe finale forcée à 2 s. Ne le remplace pas par un seuil en pixels : sur un dossier dense, un
  débordement légitime bloquerait toutes les passes.

C'est presque toujours la **colonne latérale** (54 mm) qui bride, pas les compétences. Leviers qui
ont marché : resserrer le pas vertical des cartes, transformer les qualifications binaires en
pastilles. Levier mesuré puis annulé : élargir la latérale à 67 mm ne gagne que deux centièmes et
prive la colonne principale de sa réserve. Pour mesurer, `cv_pdf.js` lit `--scale`, le mode, le
débordement et la hauteur de contenu de chaque colonne (par le bas du dernier enfant :
`aside.scrollHeight` et `main.scrollHeight` sont inutilisables, ce sont des éléments flex étirés).

## Architecture du fichier

Un seul `.html` autonome, sans dépendance externe hors Google Fonts, avec le bloc de données en
tête, le moteur de rendu en JS vanilla et le CSS print. Champs de `CANDIDAT`, tous obligatoires,
dans cet ordre — une valeur vide masque sa ligne, elle ne se supprime pas du bloc :
`reference`, `prenom`, `nom`, `sousTitre`, `accroche`, `contact{ email, telephone }`,
`cadre{ experience, disponibilite, contrat, tempsTravail, gardes, remuneration, mobilite }`,
`pratiques[]`, `specialites[]`, `recherche[]`,
`formation{ ecole, anneeSortie, internat, desv, diplomeSup, habilitation }`, `langues[]`,
`experiences[]` (`{ poste, structure, periode, duree, description }`),
`competences[]` (`{ espece, famille, acte, niveau }`, niveau recopié verbatim ; le regroupement, le
tri et les décomptes sont automatiques). `ANONYME` (booléen) précède le bloc.

Fichiers produits : `CV-Prenom-Nom-SaRecrute.html` et `.pdf`, référence `SR-<année>-<initiales>`,
`SR-MODELE` pour le modèle vierge.

## La charte graphique (relevée sur sarecrute.com)

```css
--sr-cream:      #F8F4EA   /* fond de page */
--sr-paper:      #FFFDF8   /* cartes, colonne principale */
--sr-forest:     #203832   /* texte principal, titres */
--sr-green:      #426354   /* aplats, bandeau, lentille du logo */
--sr-sage:       #6E9278   /* anneau clair du logo, filets */
--sr-muted:      #64736E   /* texte secondaire, dates */
--sr-terracotta: #C87355   /* accent principal — le « R » de SaRecrute */
--sr-gold:       #DCA85E   /* accent secondaire, avec parcimonie */
```

Titres et nom en **Fraunces** (500–600, `letter-spacing: -0.02em`, fallback Georgia) ; corps en
**Inter** (400 / 500 / 600). Micro-labels de section en capitales, 9,5–10 pt, `letter-spacing`
0.05–0.10 em, couleur `--sr-muted` : c'est la signature typographique du site. Rayons : 999 px pour
les pills, 24 px pour les grandes cartes, 12–14 px pour les petites ; pas d'ombres lourdes. Logo en
SVG inline : deux anneaux qui se chevauchent (`viewBox 0 0 120 80`, lentille `#426354`, anneaux
`#6E9278` et `#C87355`), wordmark « SaRecrute » en Fraunces 600 avec **le R en terracotta**. Le
terracotta reste réservé au R du logo et au sous-titre métier : sur un dossier candidat, il se
lirait comme un signal négatif.

Composition : bandeau d'en-tête de 32 mm, bloc identité (nom, sous-titre, accroche), puis deux
colonnes — latérale 54 mm (Contact, Cadre recherché, Domaines, Formation, Langues), principale
(Compétences vérifiées, Parcours). Pied : filet fin, « SaRecrute · Recrutement vétérinaire · France ·
Suisse · Espagne · Belgique », référence du dossier.

## L'anonymisation

`ANONYME = true` : le nom devient prénom + initiale (« Margot F. »), la carte Contact est remplacée
par « Communiquées après accord de mise en relation », le pied porte « Profil anonymisé ». Le reste
est déjà sans localisation ni employeur. C'est le standard du métier pour diffuser un profil avant
accord de mise en relation : sans ça, le cabinet se fait court-circuiter.

## Impression et contrôle — ce qui a coûté un essai

- `--virtual-time-budget` n'est pas décoratif : il laisse Google Fonts charger et l'ajustement
  converger. Sans lui, le PDF sort en polices de repli.
- `--user-data-dir` neuf à chaque appel : sans profil propre, Chrome se rattache à une instance
  ouverte et échoue en silence, sans fichier.
- **Le PDF n'est pas la capture d'écran** : deux chemins de rendu, qui n'échouent pas pareil.
  Contrôle le PDF lui-même.
- **Le nombre de pages ne prouve rien** : la page a une hauteur fixe et `overflow: hidden`, un
  débordement se traduit par une coupure basse silencieuse, pas par une seconde page. D'où la mesure
  en page (`cv_pdf.js`) et le contrôle du pied de page sur l'aperçu.
- Ne cherche pas `/FontFile` pour prouver l'embarquement des polices : Chrome les range dans des flux
  compressés, le compte ressort à zéro sur des PDF valides. Un PDF d'une page fait 300–450 Ko avec
  les polices ; bien moins, c'est suspect.
- Après toute modification du template, teste les deux extrêmes : une fiche sans aucune compétence
  **et** le modèle vierge (53 actes) ou un bilan de 130 actes. C'est là que se vérifie le basculement
  `chips` → `compact`. Mesuré sur 136 actes et 8 espèces : une ligne par famille et par état donne
  1515 px pour 852 disponibles, une ligne par état sans intitulé 756 px.

## Dépôt dans la fiche

Le connecteur MCP Airtable n'expose aucun outil de pièce jointe : le dépôt passe par
`POST https://content.airtable.com/v0/{baseId}/{recordId}/{fieldId}/uploadAttachment` (base64,
5 Mo max). **L'API ajoute, elle ne remplace pas** : un doublon a été créé le 13/10/2026 sur la fiche
Lecarpentier. Le script réécrit donc le champ après dépôt (nouvelle pièce seule plus les pièces
étrangères). Ne jamais confondre `CV IA` (`fldDfGvVlyid0xacE`, le dossier produit) avec `CV`
(`fldsj2ukrpjPzu5ox`, le CV d'origine du candidat, qui n'est jamais une source).

## Ce qui a été laissé avec la compétence manuelle

La Partie 1 du PROMPT.md de Léo — analyse et scoring du vivier (grille sur 100, Top 8) et lecture
d'un CV PDF par pdf.js dans la pane — n'a pas été reprise dans la routine : elle ne se déclenche pas
par un bouton. Elle est dans l'historique git (`remote-skills/creer-cv-candidat/PROMPT.md`, dernière
version 0.5.0 au commit `ce68857`).
