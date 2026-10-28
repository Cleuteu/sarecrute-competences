# Dossier de présentation candidat — notes de maintenance du template

Document de maintenance, **pas un prompt** : la routine `routines/cv-candidat.md` ne le lit pas. Il
rassemble ce que Léo a appris en construisant `cv-template.html` (compétence `creer-cv-candidat`,
versions 0.1 à 0.5, août–octobre 2026), pour que personne ne refasse les mêmes essais. Le template
n'est plus rempli à la main : `routines/scripts/cv_candidat.py` recopie les champs Airtable dans le
bloc de données, et `routines/scripts/cv_pdf.js` imprime.

## Le template existe — ne le reconstruis pas

`cv-template.html` est validé : une page A4 tenue aussi bien par une fiche vide que par un bilan de
136 actes sur huit espèces. Il embarque l'auto-ajustement, l'anonymisation, le bilan en étiquettes à
jauge et les états vides. Sa mise en page date du 28/10/2026 (voir « La mise en page »). On remplace ce qui est entre `/*DATA-START*/` et `/*DATA-END*/`, et c'est tout. Ne
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
| Prénom / Nom | `fld1WR6pNpe8sAya6` / `fld6yzzWrqBZBtXly` — absents du dossier anonymisé |
| Référence | `SR-` + les 5 derniers caractères de l'identifiant du record, la même sur les deux dossiers |
| Sous-titre | `Emploi recherché` + `Pratiques requises` + `Années d'expérience` |
| Titre (anonymisé seulement) | 3 à 8 mots rédigés par la routine depuis les seuls champs du bloc ; vide = sous-titre sans les années |
| Accroche | `Accroche CV` (`fld2iZ18Ayjx3m1Pi`), écrite par la routine d'enrichissement depuis les entretiens et recopiée telle quelle (depuis le 28/10/2026 ; avant, la routine du CV la rédigeait elle-même depuis `Profil`, `Notes`, `Notes du candidat` et `Transcripts`). Vide = pas d'accroche, et la note demande de relancer l'enrichissement |
| Contact | `Mail`, `Téléphone` — **et rien d'autre : pas de localisation** |
| Cadre recherché | `Années d'expérience`, `Date de disponibilité`, `Statuts contractuels souhaités`, `Type de temps de travail`, `Gardes` + `Fréquence tolérable des gardes`, `Rémunération souhaitée` |
| Domaines maîtrisés | `Pratiques maitrisées` + `Spécialités maitrisées` |
| Domaines recherchés | `Pratiques requises` + `Spécialités requises` |
| Formation et diplômes | `Ecole véto`, `Année de sortie`, `Internat`, `DESV?`, `Diplôme supplémentaire`, `Habilitation sanitaire` |
| Langues | `Langues` — noms seuls, jamais de niveau |
| Compétences vérifiées | table `Compétences` (`tblH8Zym1DNu7PN3c`), un enregistrement par acte, avec `Espèce` et `Famille` (lookups de l'acte) |
| Parcours | table `Expériences` (`tblTYdApkiHqKeBVi`) : `Poste`, `Structure`, `Période`, `Durée`, `Description`. Depuis le 28/10/2026 la `Description` est écrite pour le client par l'enrichissement (missions, rien de personnel) ; citations, sources et réserves vont dans `Justification` (`fldoeq7bBWmigzIOf`), que le dossier ne lit jamais |

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
  produirait un chiffre que la base ne dit pas). Le parcours est une **frise** (voir « La mise en
  page »).

## La mise en page (28/10/2026)

Reprise d'un dossier anonymisé fait à la main pour Ana Vanesa Fernandez Clemente (« CV anonyme -
Veterinaire medecine feline », dans son « CV IA »), validée par Alex le 28/10/2026, en corrigeant
ses défauts. La révision du 15/10/2026 (cadre en intitulé/valeur, jauge devant l'acte, bilan en
tableau) est dans l'historique git, au commit qui précède ce remplacement.

- **En-tête vert foncé** (`--sr-forest`) pleine largeur : logo à gauche, « Dossier de présentation »
  et la référence à droite ; puis le sous-titre en capitales or, le nom en Fraunces blanc, les
  coordonnées à droite du nom, l'accroche pleine largeur (176 mm : à 128 mm, à côté des
  coordonnées, elle prenait six lignes au lieu de quatre).
- **Le logo est dessiné en SVG sur le fond du bandeau**, viewBox recadré au trait extérieur des
  anneaux (`18.5 12.5 83 55`) : dans la référence c'était une image collée avec son propre fond (un
  rectangle visible) et rentrée de 8 mm par rapport à la marge ; avec le viewBox d'origine
  (`0 0 120 80`), le SVG rentrait encore de 2 mm. Pas de slogan sous le wordmark : à cette taille il
  était illisible.
- **Filet en trois tiers égaux** (sauge, terracotta, or) : la référence avait trois segments de
  largeurs quelconques.
- **Bandeau des repères** sur fond sauge à 12 % : tout le cadre recherché (expérience,
  disponibilité, contrat avec le temps de travail en seconde ligne, gardes avec la fréquence en
  seconde ligne, rémunération). Chaque case après la première porte son filet **et** une marge
  intérieure (dans la référence, le texte touchait le séparateur). Une valeur de 22 caractères au
  plus garde sa largeur naturelle et ne passe jamais à la ligne (`.fact`) ; les plus longues se
  partagent le reste (`.fact.long`, 30 à 64 mm). Une fiche à deux cases ne s'étire donc pas.
- **Deux colonnes** sous le bandeau : principale (parcours, formation) et latérale de 64 mm
  (compétences, domaines, langues). Au-delà de 24 actes, le bilan passe dans la principale et la
  formation dans la latérale (classe `.dense`) : 53 actes dans 64 mm finissaient en mode texte à côté
  d'une colonne presque vide.
- **Titres de section** en Fraunces 600 sur un filet terracotta.
- **Frise du parcours** : une pastille terracotta pleine par poste, reliées par un filet ; une
  pastille creuse sauge pour la ligne « Stages et postes courts ». Dans la référence, les pastilles
  alternaient deux couleurs sans rien signifier. Au-dessus de l'intitulé, la période en capitales
  terracotta, toujours avec `→` (la référence mêlait `→`, `·` et `—`), et la durée en gris ;
  l'intitulé en gras, la structure en italique, la description en liste à tirets (une description
  en « a · b · c » donne trois tirets).
- **Étiquettes à coins arrondis** (1,6 mm, pas des pilules), comme la référence. Mais la couleur porte
  ici un sens, avec sa légende : voir le bilan.
- `+25 %` ne se coupe plus avant le `%` : espace fine insécable devant `%` et `€` (fonction `typo`).
- Fond de page blanc, pas crème : c'est la référence, et un dossier imprimé.

## Le bilan de compétences : une étiquette par acte, notée sur trois points

Chaque acte est une **étiquette** dont le fond porte le niveau, avec une **jauge de trois crans**
à l'intérieur, devant l'intitulé : la jauge répète le niveau pour qui ne distingue pas les teintes,
et la légende sous le titre « Compétences » ne montre que les niveaux présents. C'est la table
`NIVEAUX` en tête du template :

| Niveau Airtable | Crans | Étiquette |
|---|---|---|
| `Autonome` | ●●● | fond sauge, texte vert foncé |
| `Ponctuel` | ●●○ | fond orangé, texte brun |
| `En apprentissage` | ●○○ | fond or pâle |
| `Jamais fait` | ○○○ | fond blanc filet gris, texte gris |
| `Non évalué` | ○○○ tireté | réservé au modèle vierge, n'existe pas dans Airtable |
| `Non concerné` | — | non affiché |

Le terracotta reste hors du bilan : sur une compétence, il se lirait comme une alerte.

Les décomptes restent sur trois états (« 11 acquis · 7 en cours »), parce que c'est ce qu'une
clinique compte. Le regroupement est à deux niveaux, **espèce puis famille d'actes** ; l'ordre des
familles suit le référentiel Airtable (constante `FAMILLES` en tête du moteur), pour qu'un chirurgien
et un rural présentent leurs actes dans le même ordre. **Les « non acquis » s'affichent**, et c'est
délibéré : l'honnêteté sur les limites est ce qui rend le reste crédible.

Deux mises en page selon la densité, décidées par le seul nombre d'actes :

- **24 actes au plus — colonne latérale** : l'espèce et ses décomptes, puis chaque famille en
  capitales grises au-dessus de ses étiquettes.
- **Au-delà — colonne principale** (`.dense`), sous le parcours : une famille par ligne filetée,
  l'intitulé à gauche (30 mm), les étiquettes à droite. Si la page déborde encore, le mode
  `compact` donne une ligne de texte par niveau et par espèce, jauge en tête.

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
Pour rendre un dossier plus lisible, le levier est la taille de base des règles CSS, pas le
plafond. Mesures de la mise en page du 28/10/2026 : Voutaz (6 actes, 5 lignes de parcours) 1,11,
Lecarpentier (10 actes) 1,07 et 1,04 en anonymisé (le titre métier tient deux lignes), Delastre (ni
acte ni parcours) 1,11, modèle vierge (53 actes, sans parcours) 1,11 en compact, Lecarpentier avec
les 53 actes du référentiel 0,83 en compact.

**Une mesure prise trop tôt est fausse, et elle se fige.** Si la routine mesure avant le chargement
des polices, elle trouve un débordement énorme, descend au plancher et n'y revient jamais. Trois
protections, les trois nécessaires :

- `render("chips")` est appelé une fois, immédiatement, hors de la routine d'ajustement. Quand
  le seul appel vivait dans `fit()`, une routine qui n'aboutissait pas laissait le PDF **sans sa
  colonne principale**, invisible à l'écran.
- Plusieurs passes (`document.fonts.ready`, `load`, `setTimeout`), qui ne transitent pas toutes par
  `requestAnimationFrame` : à l'impression, sous `--virtual-time-budget`, rAF peut n'être jamais servi.
- Un garde-fou de préparation (`document.fonts.status === "loaded"`, page avec une hauteur), sauf la
  passe finale forcée à 2 s. Ne le remplace pas par un seuil en pixels : sur un dossier dense, un
  débordement légitime bloquerait toutes les passes.

Depuis le 28/10/2026 c'est la **colonne latérale** (64 mm, le bilan) qui bride dès que les actes
passent la dizaine : Lecarpentier la remplit (713 px pour 719) quand la principale garde 46 px. Le
seuil de 24 actes pour basculer le bilan à gauche en découle ; s'il faut le bouger, mesure avant.
Pour mesurer, `cv_pdf.js` lit `--scale`, le mode, le
débordement et la hauteur de contenu de chaque colonne (par le bas du dernier enfant :
`aside.scrollHeight` et `main.scrollHeight` sont inutilisables, ce sont des éléments flex étirés).

## Architecture du fichier

Un seul `.html` autonome, sans dépendance externe hors Google Fonts, avec le bloc de données en
tête, le moteur de rendu en JS vanilla et le CSS print. Champs de `CANDIDAT`, tous obligatoires,
dans cet ordre — une valeur vide masque sa ligne, elle ne se supprime pas du bloc :
`reference`, `prenom`, `nom`, `sousTitre`, `titre`, `accroche`, `contact{ email, telephone }`,
`cadre{ experience, disponibilite, contrat, tempsTravail, gardes, remuneration, mobilite }`,
`pratiques[]`, `specialites[]`, `recherche[]`,
`formation{ ecole, anneeSortie, internat, desv, diplomeSup, habilitation }`, `langues[]`,
`experiences[]` (`{ poste, structure, periode, duree, description }`),
`competences[]` (`{ espece, famille, acte, niveau }`, niveau recopié verbatim ; le regroupement, le
tri et les décomptes sont automatiques). `ANONYME` (booléen) précède le bloc.

Fichiers produits : `CV-Prenom-Nom-SaRecrute.pdf` (nominatif) et `CV-anonyme-SR-XXXXX-SaRecrute.pdf`
(anonymisé : le nom de fichier voyage avec la pièce jointe, il ne porte jamais de nom de personne),
référence `SR-` + les 5 derniers caractères du record (jusqu'au 28/10/2026 : `SR-<année>-<initiales>`,
abandonnée parce que les initiales se lisaient sur le dossier anonymisé), `SR-MODELE` pour le modèle
vierge.

## La charte graphique (relevée sur sarecrute.com)

```css
--sr-cream:      #F8F4EA   /* texte clair sur l'en-tête */
--sr-forest:     #203832   /* en-tête, texte principal, titres */
--sr-green:      #426354   /* aplats, bandeau, lentille du logo */
--sr-sage:       #6E9278   /* anneau clair du logo, filets */
--sr-muted:      #64736E   /* texte secondaire, dates */
--sr-terracotta: #C87355   /* filets de section, frise du parcours, le « R » de SaRecrute */
--sr-gold:       #DCA85E   /* sur-titre de l'en-tête, tiers droit du filet */
--sr-wash:       #EEF2EF   /* sauge à 12 % : bandeau des repères, étiquettes */
```

Titres et nom en **Fraunces** (600, `letter-spacing: -0.02em`, fallback Georgia) — la référence
était en Lora ; Fraunces est la police du site et du wordmark ; corps en **Inter** (400 à 700,
italique pour les structures). Micro-labels en capitales espacées (0,09 à 0,16 em). Logo en SVG
inline : deux anneaux qui se chevauchent (lentille `#426354`, anneaux `#6E9278` et `#C87355`),
wordmark « SaRecrute » en Fraunces 600 avec **le R en terracotta**. Le terracotta n'entre jamais
dans le bilan de compétences.

Pied : filet fin, « SaRecrute · Recrutement vétérinaire · France · Suisse · Espagne · Belgique » à
gauche, « sarecrute.com · Réf. » à droite (et « Profil anonymisé » sur l'anonymisé).

## L'anonymisation (deux dossiers par run depuis le 28/10/2026)

Chaque run produit le nominatif (« CV IA ») **et** l'anonymisé (« CV IA anonyme »,
`fld457VMpd1CHCAxY`, créé le 28/10/2026), sous la même référence. C'est le standard du métier pour
diffuser un profil avant accord de mise en relation : sans ça, le cabinet se fait court-circuiter.
Décision d'Alex du 28/10/2026, sur le modèle de la référence : **aucun nom** (le « prénom +
initiale » d'avant, « Margot F. », est abandonné).

- **Le bloc est vidé par le script, pas masqué par le template** (`cv_candidat.py anonymiser`) :
  prénom, nom, coordonnées et structures du parcours sont mis à vide dans
  `candidat-anonyme.json`, les « intitulé (structure) » de la ligne des stages perdent leur
  parenthèse, et deux stages devenus identiques n'en font plus qu'un. Ce qui n'est pas dans le bloc
  ne peut pas fuiter par le texte du PDF, ses métadonnées ou le HTML.
- **Le template** met le titre métier (`titre`, rédigé par la routine) à la place du nom, sur deux
  lignes équilibrées (`text-wrap: balance`), « Profil confidentiel » en sur-titre, aucune
  coordonnée, et un titre de PDF sans nom (« Profil vétérinaire anonyme — SR-XXXXX »).
- **Garde-fou** : `etat.json` porte la liste `interdits` (prénom, chaque mot du nom, nom d'usage
  compris, mail, téléphone, toutes les structures du parcours brut). `anonymiser` liste ce qui en
  reste, `render --anonyme` refuse le dossier tant qu'un terme y figure (mot entier, sans casse).
  La routine ôte le reste à la main — elle retire, elle ne remplace jamais par une description que
  la base ne donne pas — et relit aussi villes et personnes que la liste ne connaît pas. Testé le
  28/10/2026 : une structure glissée dans une description est bien refusée, et le nominatif part
  seul avec la raison dans la note.
- **Ce qui reste** : l'école et l'année (la référence les gardait), le cadre recherché, domaines,
  langues, compétences, et le parcours sans structure. À noter : le mail de présentation anonyme
  (`routines/mail-presentation-candidature.md`) retire aussi l'école ; les deux règles divergent sur
  ce point.

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
Lecarpentier. Le script réécrit donc chaque champ après dépôt (nouvelle pièce seule plus les pièces
étrangères), puis écrit les deux champs et le statut en un seul PATCH. Ne jamais confondre `CV IA`
(`fldDfGvVlyid0xacE`, le dossier nominatif) ni `CV IA anonyme` (`fld457VMpd1CHCAxY`) avec `CV`
(`fldsj2ukrpjPzu5ox`, le CV d'origine du candidat, qui n'est jamais une source). La dernière ligne
de `CV IA - Note` donne la référence : c'est par elle que la recherche d'Airtable retrouve la fiche
quand une clinique rappelle au sujet d'un dossier anonymisé.

## Ce qui a été laissé avec la compétence manuelle

La Partie 1 du PROMPT.md de Léo — analyse et scoring du vivier (grille sur 100, Top 8) et lecture
d'un CV PDF par pdf.js dans la pane — n'a pas été reprise dans la routine : elle ne se déclenche pas
par un bouton. Elle est dans l'historique git (`remote-skills/creer-cv-candidat/PROMPT.md`, dernière
version 0.5.0 au commit `ce68857`).
