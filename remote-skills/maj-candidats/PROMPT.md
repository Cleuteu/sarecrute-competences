**maj-candidats — version 0.1.0 (2026-10-29)**

> Corps de la mise à jour des candidats du site SaRecrute. Exécuté chaque nuit par la routine
> cloud `maj-offres-site` (`routines/maj-offres-site.md`), qui clone ce dépôt sur `main`.
> **Pour déployer une modification** : éditer ce fichier (ou `scripts/`, `assets/`) sur `main`,
> mettre à jour la ligne de version ci-dessus, régénérer les manifests (`python3 tools/manifests.py`),
> pousser `main` (la routine le lit dès la nuit suivante), puis `git push origin main:stable`.

# Mise à jour des candidats du site SaRecrute

Tient à jour la page publique `candidats.html` (profils anonymes de vétérinaires en recherche, pour
les cliniques) et le panneau « Candidats » de la section « Nos nouvelles offres / candidats » de
l'accueil, à partir de l'Airtable **PROD** (`appP0W2ISytaNyAhG`). Lecture seule : on n'écrit rien
dans Airtable.

**Périmètre publié** (décision d'Alex du 28/10/2026) : candidat « En recherche active », pas
embauché via SaRecrute, qui n'a pas signalé avoir trouvé, avec un **signe de vie de moins de 3 mois**
et **au moins un compte rendu d'appel** (Communications « Transcript text », ou champ Transcripts de
la fiche). Les dates de modification Airtable ne servent à rien (mises à jour en masse) : le signe de
vie est calculé par `fetch_candidats.py` (création, posts « Vétérinaire cherche poste », communications,
présentations, entretiens, réponses à une proposition, entrées datées des notes hors relances sans
réponse). Pas d'accord du candidat à demander : une carte anonyme à l'échelle du département n'est
pas reconnaissable (arbitrage d'Alex du 28/10/2026).

## Fichiers

| Fichier | Rôle |
|---|---|
| `candidats.html` | la page, régénérée en entier à partir de `offres.html` (en-tête, CSS, pied de page) |
| `index.html` (dépôt Pages) / `site_sarecrute_v4.html` (local) | panneau « Candidats » entre `<!-- NOUVEAUX CANDIDATS :` et `<!-- /NOUVEAUX CANDIDATS -->` : les 8 derniers candidats appelés |
| `.candidats-state.json` | état versionné dans le dépôt Pages, **public** (le dépôt l'est) : par identifiant opaque, la description publiée, l'empreinte de ses sources, les réglages de carte, la date de mise en ligne ; `retenus` (candidats publiables gardés hors ligne, motif générique) ; `anciens` (réglages de carte des candidats sortis, pour un retour). **Rien qui ne soit déjà sur la page** : ni nom, ni identifiant Airtable, ni note, ni ce qu'on a choisi de ne pas afficher. |
| `~/.sarecrute/maj-candidats/work/` | travail de la nuit, **données personnelles** (noms, sources de rédaction) : rien de ce dossier ne quitte la machine ni n'entre dans un dépôt |

**Aucune référence n'est affichée** (décision d'Alex du 29/10/2026), ni sur le site ni sur les dossiers
CV. Chaque candidat a un **identifiant opaque** (10 caractères hexadécimaux, empreinte de l'identifiant
Airtable complet) : clé de l'état, des données de la page et du lien `candidats?profil=…` de l'accueil.
Il ne se recalcule pas depuis l'ancienne référence `SR-XXXXX` des dossiers déjà envoyés aux cliniques :
une clinique qui garde un tel dossier ne peut pas relier la carte publique à la personne. Le bouton
« Ce profil m'intéresse » envoie un mail qui reprend le titre, les zones et la description de la carte.
Les libellés de titres viennent de `../maj-offres/assets/titre_specialites.json`.

## Étapes

### 1. Lire Airtable et voir ce qui change

```bash
python3 <skill>/scripts/fetch_candidats.py
```

Écrit dans `work/` : `candidats.json`, `dossiers/REF.json` (sources validées, carte, termes interdits),
`todo.json` (descriptions à écrire : `nouveau`, `retour` ; à relire : `source modifiée` quand les
sources, la carte affichée ou les termes interdits ont changé, `contrôle` quand la description en ligne
échoue au contrôle du jour), `diff.json` (ajouts, retraits avec motif, revues, retenus). Si l'état est
absent alors que la page existe, le script s'arrête : ne le contourne pas, restaure l'état depuis
l'historique du dépôt Pages. Les champs de carte (titre, zones, contrat, disponibilité…) se
recalculent seuls chaque nuit : seules les descriptions demandent un travail.

### 2. Écrire les descriptions

Pour chaque entrée de `todo.json`, ouvre son dossier et rédige **une** description. Pour une entrée
`source modifiée`, relis `description_actuelle` à la lumière du dossier : garde-la mot pour mot si
chacune de ses affirmations est encore portée par le dossier et respecte les règles ci-dessous, sinon
corrige seulement l'élément en cause. Pour une entrée `contrôle`, réécris l'élément que visent ses
`alertes`. **Toute entrée de `todo.json` reçoit une ligne dans `work/descriptions.json`**
(`{ "<identifiant>": "…" }`, l'identifiant du todo), y compris une description inchangée : c'est ce qui marque la relecture comme
faite. Une ligne à `null` retire le candidat ce soir (voir « 3. Contrôler »).

Le dossier donne la carte **telle qu'elle est affichée** (`carte_publique`, réglages appliqués) et
`pastilles_non_affichees` : des spécialités volontairement absentes de la carte. **Ne les cite jamais**
dans la description, ni elles ni rien qui les évoque.

**Format.** Exactement 3 segments séparés par « · » (espace, point médian, espace), 120 à 230
caractères, sans point final. Style nominal **sans sujet** : pas de « il/elle », pas de prénom, et
**aucun accord genré** (« Autonome en… », « Expérience de… », « Recherche… », jamais « formée »,
« diplômé(e) »). Majuscule au début de chaque segment seulement, hors acronymes (NAC, CDI, CDD, ASV,
DESV, CES, IRM, TPLO, CT).
- Segment 1 : ce que le candidat fait réellement, en actes concrets (« Autonome en consultation,
  chirurgie de convenance et échographie abdominale », « Vêlages, césariennes et suivi d'élevage laitier »).
- Segment 2 : un trait de parcours utile à une clinique, sans lieu ni structure (« Expérience en
  structure d'urgence et en clinique de référé », « Plusieurs années en mixte à dominante rurale »).
- Segment 3 : ce que le candidat cherche dans sa prochaine structure (type de clinique, encadrement,
  ambiance, gardes, évolution), sans répéter la zone, le contrat ni la date, déjà sur la carte.

**Sources.** Uniquement `sources_validees` du dossier (profil IA, profil du recruteur, compétences,
expériences, champs). Jamais un transcript, un CV ou un post. N'invente rien, n'extrapole pas.
« Autonome » seulement si la source le dit ; un acte « Ponctuel » ou « En apprentissage » n'est jamais
« maîtrisé ». Dans le doute, omets.

**Anonymat — règle absolue, la page est publique.** Rien ne doit permettre de reconnaître la personne,
même pour un confrère, un ancien employeur ou un camarade de promo :
- aucun terme de la liste `interdits` du dossier (sans accents ni casse, fragments compris) ;
- aucun nom propre : personne, école, université, pays ou ville de formation, nationalité, structure,
  groupe, employeur passé ou actuel, ville, département, région ou pays ;
- **aucun chiffre** : ni date, ni année, ni durée chiffrée, ni âge ; aucune langue parlée ;
- **rien qui décrive le poste en cours** (fonctions, organisation, part d'activité, encadrement,
  service monté, spécialité exercée au quotidien dans la structure actuelle) : l'employeur actuel lit
  la page et ne sait pas forcément que son vétérinaire cherche. Une compétence générale reste (« autonome
  en échographie abdominale ») ; une description du poste non (« forte part d'urgences »,
  « encadrement d'équipe ») ;
- aucun internat, diplôme ou formation rare, aucun acte ou parcours qui singularise une petite promo
  (« première promotion », « ancien militaire », un titre rare) ;
- rien de la vie privée (conjoint, enfants, santé, loisirs, origine, déménagement, raisons personnelles),
  aucune rémunération ni prétention.

**Points faibles.** Jamais publiés tels quels ; un acte à progresser devient une attente (« Recherche
une équipe qui accompagne la montée en chirurgie »).

**Ton.** Concret, entre confrères, terre-à-terre. Pas de vocabulaire marketing (« passionné »,
« dynamique », « motivé », « profil idéal », « pépite », « valoriser », « opportunité »), pas de superlatif.
Varie les ouvertures : « Autonome en… » et « Recherche une équipe… » reviennent déjà sur beaucoup de cartes.

### 3. Contrôler

```bash
python3 <skill>/scripts/check_descriptions.py
```

⛔ = à réécrire, puis relancer. Le script attrape les recopiages et le format, pas le sens. **Relis
ensuite chaque description toi-même, en adversaire** : mets-toi à la place de l'employeur actuel, d'un
ancien collègue, d'un camarade de promo qui croise la carte (titre, zones, pastilles, niveau) avec le
texte : peut-il reconnaître la personne ? Chaque affirmation est-elle portée par le dossier ? Rien ne
contredit la carte (gardes, contrat, niveau) ? Regarde aussi la carte elle-même : une zone devenue
étroite (un seul département) avec une pastille rare peut désigner le poste actuel. **Un doute qui ne se
lève pas en retirant l'élément douteux = `null` pour ce candidat** dans `descriptions.json` : un nouveau
candidat n'est pas publié, un candidat déjà en ligne est retiré ce soir, et le compte rendu le signale à
Sarah et Alex. N'omets jamais simplement la ligne d'une carte en ligne qui te pose problème : elle
resterait en ligne. Mieux vaut un candidat en attente qu'un candidat reconnu.

### 4. Appliquer

```bash
python3 <skill>/scripts/apply_candidats.py --dry-run   # contrôle
python3 <skill>/scripts/apply_candidats.py             # écrit
```

Régénère `candidats.html`, le panneau de l'accueil et l'état. Retire les candidats sortis du
périmètre, publie les nouveaux décrits, garde les autres. Écrit `work/apply.json` (publiés ce soir,
retirés, en attente, descriptions changées).

### 5. Vérifier

Même contrôle que les offres : JavaScript valide et balises équilibrées dans `candidats.html` et la
page d'accueil (`node`, cf. PROMPT.md de maj-offres, section 5). Puis
`python3 <skill>/scripts/check_descriptions.py --state` : repasse toutes les descriptions en ligne.

## Réglages manuels (dans `.candidats-state.json`)

- `candidats.REF.ajustements` : `titre`, `pratiques`, `contrat`, `experience` (remplacent la valeur
  Airtable sur la carte) et `specialites` (**liste positive** des pastilles affichées ; une spécialité
  Airtable absente de la liste n'apparaît pas). Hérités des relectures du 28/10/2026, conservés d'une nuit
  à l'autre, et gardés dans `anciens` si le candidat sort puis revient. On n'écrit jamais dans ce fichier
  public ce qu'on cache ni pourquoi.
- `retenus.REF` : candidat publiable gardé hors ligne, avec un motif **générique** (« recherche à
  reconfirmer »). Sur demande d'Alex ou d'une recruteuse (un candidat qui demande à ne plus apparaître,
  par exemple), depuis le dossier local du site : `./deploy.sh --sync`, ajouter l'identifiant du candidat (champ `ref` de `work/candidats.json`, à côté de son nom) à `retenus`
  dans `.candidats-state.json`, `python3 <skill>/scripts/fetch_candidats.py` puis
  `python3 <skill>/scripts/apply_candidats.py` (les nouveaux candidats de la nuit restent en attente),
  puis `./deploy.sh --candidats-locaux`. Le dépôt Pages étant public, les versions passées de la carte
  restent dans son historique.

## Pièges connus

- **Libellés de zones** : Airtable écrit « 20 - Corse-du-Sud », « Province de Bruxelles », « Canton de
  Neuchatel », « Nouvelle calédonie » ; la carte attend « Corse-du-Sud (2A) », « Région de
  Bruxelles-Capitale », « Canton de Neuchâtel », « Nouvelle-Calédonie ». `zone()` les aligne ; une zone
  de département ou de canton sans contour arrête `apply_candidats.py` (sinon le comptage casse).
- **Mayotte** est codée 974 dans le select Airtable, comme La Réunion : `zone()` la remet en 976.
- **Panneau de l'accueil** : les marqueurs doivent exister ; la routine des offres ne touche que le
  carrousel des offres (repéré par son identifiant et son indentation, à ne pas modifier).
- **La page dit « liste actualisée chaque jour »** : si la routine s'arrête plusieurs nuits, c'est faux.
- **Contrôle renforcé** (`check_descriptions.py`) : outre les termes du dossier et leurs dérivés
  (« rennaise » pour Rennes), il bloque internat, nationalités et gentilés, nombres en lettres, marqueurs
  du poste actuel (« actuel », « en charge de », « encadrement d'équipe »…) et « ancien… ». « Médecine
  interne » passe, « médecine générale et interne » non : écrire « médecine interne » en entier.
