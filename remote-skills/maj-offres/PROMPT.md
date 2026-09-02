**maj-offres — version 0.1.1 (2026-09-02)**

> Ce fichier est le corps de la compétence `maj-offres` du plugin `sarecrute-admin`. Il
> n'est **pas** installé chez l'utilisateur : le stub `SKILL.md` du plugin le télécharge depuis la
> branche `stable` de ce dépôt à chaque exécution, avec `scripts/` et `assets/` (un `MANIFEST` liste les fichiers du
> snapshot et leur version commune : le stub vérifie qu'elle est celle de ce PROMPT.md).
>
> **Pour déployer une modification** : éditer ce fichier (ou `scripts/` et `assets/`) sur
> `main`, mettre à jour la ligne de version ci-dessus, régénérer les manifests
> (`python3 tools/manifests.py`), puis avancer la branche de déploiement :
> `git push origin main:stable` (compter jusqu'à cinq minutes de cache côté `raw`). Aucun republish du plugin, aucun `plugin update` chez
> l'utilisateur.
>
> Le stub, lui, ne change presque jamais : n'y toucher que pour son `description` (déclenchement)
> — et là, bump du plugin + republish + `plugin update` redeviennent nécessaires.

# Mise à jour des offres du site SaRecrute

Synchronise les offres publiées sur le site avec l'Airtable **PROD** (`appP0W2ISytaNyAhG`).

**Périmètre publié** : offre non archivée **ET** clinique au statut commercial « Signé ». Rien d'autre.

**Où tourner.** Les commandes se lancent **depuis le dossier du site** (celui qui contient `offres.html`, `site_sarecrute_v4.html` et `deploy.sh`) : les scripts le détectent par le dossier courant. Sinon, exporte `SARECRUTE_SITE=/chemin/du/site`. `<skill>` désigne ci-dessous le dossier de cette compétence (indiqué au chargement) — **ne code jamais son chemin en dur**, il change à chaque `claude plugin update`. Les scripts n'écrivent rien dedans : le dossier de travail est `~/.sarecrute/maj-offres/work/` (surchargeable par `MAJ_OFFRES_WORK`).

**Règle absolue — anonymat.** Aucune information permettant d'identifier une clinique ne sort : ni nom de structure, ni ville, ni nom de personne, ni e-mail, ni téléphone, ni code postal, ni chiffre précis (taille d'équipe, surface, salaire). La localisation publiée s'arrête **au département** (ou au pays hors France). Les notes Airtable sont de la matière première interne : on en extrait des qualités génériques, on ne les recopie jamais.

## Fichiers touchés

| Fichier | Rôle |
|---|---|
| `offres.html` | tableau `const OFFRES` (toutes les offres) |
| `site_sarecrute_v4.html` | cartes du carousel + `const OFFRES_TEASER` (uniquement les offres taguées « Nouvelle offre ») |
| `.offres-state.json` | (dans le dossier du site) état persistant : description + empreinte du texte source par offre. **Non déployé** (`deploy.sh` ne copie que `index.html`, `offres.html`, les SEO et `images/`). Sert à savoir quelles descriptions existent déjà et lesquelles doivent être réécrites. |

## Ressources bundlées

- `scripts/paths.py` — résout le dossier du site, le dossier de travail et l'état persistant. Importé par les trois autres. **Si un script réclame le dossier du site, corrige `SARECRUTE_SITE` ou le dossier courant — ne réintroduis pas de chemin absolu.**
- `scripts/fetch_offres.py` — lit Airtable, calcule le diff, écrit `work/`
- `scripts/check_anonymat.py` — garde-fou anonymat (bloquant)
- `scripts/apply_offres.py` — régénère les deux pages HTML
- `assets/dept_centroids.json` — centroïdes par département + pays étrangers, pour les points de la carte. Un point **par département** (toutes les offres d'un même département partagent le même point) : c'est volontaire, ça empêche de deviner la commune.
- `assets/titre_specialites.json` — **source unique de vérité** des libellés : composition des titres, canonisation des pratiques, libellés du filtre, libellés d'expérience. Pour changer un libellé, on édite ce fichier et on relance `apply_offres.py` — on ne modifie jamais les tables à la main dans le HTML.

## Titres des offres

Composés par `fetch_offres.py` d'après `assets/titre_specialites.json` :

| Cas | Règle | Exemple |
|---|---|---|
| Spécialité **requise** | remplace la pratique | `Urgences` → « Vétérinaire Urgentiste » |
| Sinon | pratique(s) canonisées, dédupliquées | « Vétérinaire canin/rural » |
| `Internat` en statut contractuel | ajoute le suffixe, **garde** la pratique | « Vétérinaire canin en Clinicat » |

Les **spécialités optionnelles sont ignorées** — c'est délibéré. Elles décrivent un plus apprécié, pas la nature du poste : s'en servir produirait « Vétérinaire en management » sur des postes de médecine générale (plusieurs offres ont `Management` en optionnelle).

Conséquence pratique : un poste manifestement spécialisé gardera « Vétérinaire canin » si la spécialité n'est renseignée qu'en optionnelle. Ce n'est pas un bug du script mais une fiche Airtable à compléter — signale-le à l'utilisateur plutôt que de forcer le titre.

## Filtre « Pratiques » de offres.html

Deux mécanismes distincts, à ne pas confondre :

1. **Le contenu du menu** est calculé à l'exécution dans `offres.html`, depuis les données affichées : d'abord les pratiques présentes, puis les **spécialités requises présentes**. Le menu ne contient donc **jamais** que des valeurs réellement utilisées par au moins une offre — les autres spécialités de la base n'apparaissent pas. Rien à maintenir ici.
2. **Les libellés affichés** viennent de `PRATIQUE_LABELS`, que `apply_offres.py` **réinjecte** depuis `assets/titre_specialites.json` (`pratiques_filtre`). Les spécialités s'affichent sous leur nom Airtable (« Neurologie », « Urgences »).

Le filtre matche pratique **ou** spécialité : `o.pratiques.includes(v) || o.specialite === v`. Une offre spécialisée reste donc listée sous sa pratique (un poste de neuro apparaît sous « Neurologie » et sous « Canin ») — c'est voulu, ça reste de la canine.

**Si une nouvelle valeur de pratique apparaît dans Airtable** : ajoute-la dans `pratiques_titre` **et** `pratiques_filtre` de l'asset, puis relance `apply_offres.py`. Sans ça elle s'affichera brute et en minuscules dans le titre. Le champ Airtable contient des doublons et coquilles (`volailles` / `Vollaile`, `Rurale`) : `pratiques_canon` les normalise à la lecture, complète-le au besoin.

## Étapes

### 1. Lire Airtable et voir ce qui change

```bash
python3 <skill>/scripts/fetch_offres.py
```

Écrit dans `~/.sarecrute/maj-offres/work/` (le script affiche le chemin) :
- `airtable.json` — les offres publiables, champs normalisés + textes sources (`_src`) et identifiants internes (`_clinique`, `_ville`, `_veto`, `_cp`)
- `todo.json` — celles qui ont besoin d'une description
- `diff.json` — ajouts / retraits / descriptions à revoir
- `blocklist.json` — noms de cliniques, villes, personnes et domaines de toute la base (pour le contrôle)

Annonce le diff à l'utilisateur (combien d'ajouts, de retraits, de descriptions à écrire) avant de continuer.

Si `diff.json` ne montre **aucun** changement et que `todo.json` est vide : dis-le et arrête-toi là, il n'y a rien à faire.

### 2. Écrire les descriptions

Pour chaque entrée de `todo.json`, lis `source.annonce`, `source.notes_offre` et `source.notes_clinique`, puis rédige **une description de 2 à 3 éléments** séparés par ` · `.

Ce qu'on veut : les qualités qui donnent envie et aident à se situer.
> `Plateau technique complet (radio, écho, labo) · Chirurgie tissus mous et orthopédie · Pas de garde ni astreinte`
> `Formation assurée, débutants bienvenus · Pôle référé en plein essor · Logement possible`
> `Gardes exclusivement rurales, jamais d'appel pour les animaux de compagnie · Véhicule et téléphone fournis`

Registre : factuel et terre-à-terre, comme le reste du site. Pas de superlatif marketing.

**Interdits** (le contrôle de l'étape 3 les bloque) :
- nom de clinique, de groupe, de ville, de personne
- e-mail, URL, téléphone, code postal
- tout nom propre en milieu de phrase (hors acronymes métier et pays/régions)
- chiffres précis. `100 % canine` et `24h/24` passent ; « 3 vétérinaires », « 400 m² », « 3 100 € » non.

Les entrées dont `raison` vaut `source modifiée` ont déjà une `description_actuelle` : relis-la à la lumière de la nouvelle source et ne la change que si l'information a réellement bougé.

Écris le résultat dans `work/descriptions.json` :
```json
{ "AbC123": "Plateau technique complet · Débutants bienvenus, formation assurée · Pas de garde" }
```

Une offre sans aucun texte source (listée dans `diff.json` → `sans_texte_source`) n'a pas de description : c'est normal, sa carte s'affiche sans ce bloc. Ne l'invente pas.

### 3. Contrôler l'anonymat

```bash
python3 <skill>/scripts/check_anonymat.py
```

- `⛔ BLOQUANT` → corrige `work/descriptions.json` et relance. **Ne passe pas à l'étape 4 tant que le script sort en code 1.**
- `ℹ à vérifier` (chiffres) → relis toi-même : si le chiffre restreint la structure, retire-le.

Le script attrape les recopiages littéraux ; il ne juge pas le sens. Relis les descriptions même quand il est vert.

### 4. Appliquer

```bash
python3 <skill>/scripts/apply_offres.py --dry-run   # contrôle
python3 <skill>/scripts/apply_offres.py             # écrit
```

Le script trie par date de création décroissante, calcule le tag « Nouvelle offre », régénère les deux pages et met `.offres-state.json` à jour.

**Tag « Nouvelle offre »** : offres créées dans les 30 derniers jours ; **si elles sont moins de 5, on complète avec les plus récentes pour en avoir toujours 5 au minimum**. Réglable : `--window-days`, `--min-new`.

Le carousel de l'accueil affiche exactement les offres taguées.

### 5. Vérifier

```bash
for f in offres.html site_sarecrute_v4.html; do
  node -e "
  const h=require('fs').readFileSync('$f','utf8');
  [...h.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m,i)=>{
    try{new Function(m[1])}catch(e){console.log('$f JS err',i,e.message)}});
  const c=(r)=>(h.match(r)||[]).length;
  console.log('$f', 'div',c(/<div/g)+'/'+c(/<\/div>/g), 'article',c(/<article/g)+'/'+c(/<\/article>/g));"
done
```

JS valide et balises équilibrées attendus. Puis aperçu local (`python3 -m http.server` dans le dossier du site) pour vérifier de visu : cartes bien alignées, carousel rempli, tags au bon endroit, points sur la carte.

Contrôle utile aussi : `python3 <skill>/scripts/check_anonymat.py --state` repasse **toutes** les descriptions enregistrées, pas seulement les nouvelles.

### 6. Déployer — seulement sur accord explicite

**Avant de lancer le script**, si tu as écrit quelque chose dans Airtable pendant cette session (une pratique ajoutée, une spécialité corrigée), **relis la valeur maintenant** — pas au moment de l'écriture. Un `fetch` a pu passer entre les deux, et surtout la valeur a pu être défaite dans la base (voir Pièges connus) :

```bash
python3 -c "import json,os; a=json.load(open(os.path.expanduser('~/.sarecrute/maj-offres/work/airtable.json'))); o=[x for x in a if x['ref']=='REF'][0]; print(o['titre'], o['pratiques'], o['specialite'])"
```

```bash
./deploy.sh
```

**Ne déploie jamais sans que l'utilisateur l'ait demandé.** Présente d'abord le récapitulatif (ajouts, retraits, descriptions modifiées, offres taguées) et attends son feu vert.

### 7. Contrôler la mise en ligne

Le déploiement pousse un commit ; **le build GitHub Pages est asynchrone** (~40 s, parfois plusieurs minutes). Tant qu'il n'est pas passé, `sarecrute.com` renvoie l'ancien contenu **avec `age: 0`** — ce n'est pas un cache, c'est l'origine qui sert encore l'ancien build. Ne conclus donc jamais « c'est en ligne » sur la seule réussite de `deploy.sh`.

```bash
# le contenu réellement poussé, hors CDN
curl -s https://raw.githubusercontent.com/Cleuteu/sarecrute/main/offres.html | grep -o '"ref":"REF","titre":"[^"]*"'
# l'état du build
gh api repos/Cleuteu/sarecrute/pages/builds --jq '.[0] | "\(.status) \(.commit[0:7])"'
# puis attendre la version servie — chaîne PROPRE AU RECORD, jamais un libellé partagé
until curl -s https://sarecrute.com/offres.html | grep -q '"ref":"REF","titre":"LE TITRE ATTENDU"'; do sleep 15; done
```

⚠️ Le motif d'attente doit contenir la **ref**. Greper un titre seul (« Vétérinaire rural/canin ») matche d'autres offres qui le portent déjà : la boucle sort immédiatement et ne prouve rien.

## Pièges connus

- **API Airtable** : `returnFieldsByFieldId=true` est obligatoire, sinon les champs reviennent indexés par nom et tous les filtres échouent silencieusement (0 offre publiable, ou pire : aucun filtrage). La clé est dans `~/.zshrc` (`AIRTABLE_API_KEY`).
- **Le statut « Signé » est porté par la clinique**, pas par l'offre : c'est le lookup `Status commercial (from Clinique)`. Une offre non archivée d'une clinique en discussion ne doit pas être publiée.
- **Deux champs texte pour l'annonce** : la table Offres porte à la fois `Texte de publication` (`fldideBaQV8ILp2zJ`, richText) et `Annonce` (`fldLIH3nwT4p9uhHC`, multilineText). La plupart des offres remplissent les deux, mais certaines n'ont que `Annonce` — `fetch_offres.py` prend `Texte de publication` en source primaire et **se replie sur `Annonce` seulement si elle est vide**. Ne concatène pas les deux : ça changerait l'empreinte de toutes les offres qui ont les deux champs et les signalerait à tort « source modifiée ». Si une offre ressort dans `sans_texte_source` alors qu'un texte existe visiblement dans Airtable, c'est ce genre de champ parallèle qu'il faut aller chercher.
- **`experience`** : la donnée brute vaut `1 à 2 ans`, affichée `Semi-autonome`. La table vit dans `assets/titre_specialites.json` (`experience`) : `apply_offres.py` la réinjecte dans `offres.html` **et** l'applique lui-même aux cartes statiques de l'accueil. Un seul endroit à éditer.
- **Spécialités requises vs optionnelles** : ne jamais basculer sur les optionnelles pour les titres (cf. section Titres). Le champ requis est `fldfxUJuNO2kkstGq`.
- **Whitelist de publication** : `apply_offres.py` ne recopie dans le HTML que les champs de `PUBLIC_FIELDS`. Ne l'élargis pas sans réfléchir — le champ `Rémunération` d'Airtable, par exemple, contient des notes internes brutes (« PAS DE COLLAB ») et n'a rien à faire dans la page.
- **Les refs Airtable peuvent commencer par un chiffre** (`45LCzL`, `02xA70`) : les clés de `OFFRES_TEASER` sont donc **écrites entre guillemets** par `apply_offres.py`. Sans ça le bloc `<script>` de l'accueil — traductions incluses — ne parse plus du tout, et la page d'accueil casse en silence. Corrigé le 19 août 2026 ; contrôle systématique à l'étape 5.
- **Une valeur écrite dans Airtable n'est pas une valeur acquise** : l'historique d'annulation est **partagé à l'échelle de la base**, donc le Cmd+Z d'un autre collaborateur peut défaire une écriture faite par API quelques minutes plus tôt. Vécu le 19 août 2026 : une pratique ajoutée à une offre a été annulée pendant qu'un recruteur archivait des fiches, le `fetch` suivant a relu l'ancienne valeur, et le site est parti avec l'ancien titre. Aucune automation n'était en cause (aucune ne surveille `Pratiques requises`) — vérifiable avec `list_automations` avant d'accuser un script. D'où le contrôle de dernière minute à l'étape 6. Si une valeur revient une seconde fois à son état d'origine, ce n'est plus un accident : demande à l'utilisateur avant de la réécrire, un humain la veut peut-être ainsi.
- **Le tag est une donnée, pas une date en dur** : `offres.html` lit `o.isNew`. Ne réintroduis pas de seuil de date codé dans le HTML, il devient faux au fil du temps.
