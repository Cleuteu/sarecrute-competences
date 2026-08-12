---
name: scrape-veto
description: Scrape les posts des groupes Facebook vétérinaires cochés « Scraper les posts » dans Airtable (fenêtre temporelle paramétrable, 6h par défaut) + commentaires pertinents, et pousse tout dans "Posts scrappés" en déduplicant, chaque entrée rattachée à son canal. Args possibles ex. "aujourd'hui", "48h", "2 derniers jours", ou le nom d'un groupe pour n'en faire qu'un.
---

# Scrape Veto

Scraper les posts des **groupes Facebook vétérinaires** (tri chronologique) sur une **fenêtre temporelle**, en extraire les commentaires pertinents, et pousser chaque entrée dans Airtable **sans créer de doublon**, **rattachée au groupe d'où elle vient**.

**Sources** : elles ne sont **pas** dans ce fichier. Ce sont les enregistrements de la table **« Canaux de diffusion »** (`tbluH5M2sogAN85dl`, base `appP0W2ISytaNyAhG`) dont la case **`Scraper les posts`** est cochée **et** dont l'`Url` contient `/groups/<id>`. On peut donc ajouter une source sans republier le plugin. Un argument nommant un groupe (« scrape veto emploi véto 48h ») restreint à celui-là.

**Fenêtre** : lue depuis les arguments (ex. `aujourd'hui`, `48h`, `2 derniers jours`, `6h`). Défaut = **6 dernières heures**. L'horloge de référence est celle du **navigateur** (`new Date()` dans la page), pas la date système — vérifie-la au début.

**Navigateur — OBLIGATOIRE** : utilise le **Chrome réel de l'utilisateur** via les outils `mcp__claude-in-chrome__*` (session Facebook déjà connectée). **N'utilise PAS** le navigateur in-app (`mcp__Claude_Browser__*` / `preview_start`) : il n'a pas de session FB → page déconnectée, scrape impossible. Au départ : `list_connected_browsers` → `select_browser` → `tabs_create_mcp` (nouvel onglet dédié) → `navigate`.

## Principes (à respecter — c'est ce qui rend le scrape fiable et rapide)

1. **Accumulateur persistant en page.** Le DOM de FB est virtualisé (4-5 posts en mémoire). On ne lit jamais « ce qui est à l'écran à la fin » : on appelle `__merge()` **à chaque pas de scroll** pour fusionner dans `window.__store`. Tout en dépend.
2. **Fenêtre Chrome visible, sinon rien ne charge.** Chrome masqué (derrière l'app Claude, minimisé) = `requestAnimationFrame` suspendu et timers bridés : le fil reste sur 2-3 posts + skeletons et `scrollHeight` se fige, **sans erreur**. Le scrape se contrôle donc avec `__alive()` et se **réveille tout seul** en ramenant l'onglet au premier plan (cf. §1 bis) — ne demande jamais à l'utilisateur de le faire à la main avant d'avoir essayé.
3. **Tout en JS dans la page.** 1 seul screenshot au départ (vérifier chargement + pas de captcha), puis **zéro**. Lecture/scroll/clic via `javascript_tool`. Les données obfusquées se **reconstruisent** (cf. timestamps), on ne survole/screenshote pas.
4. **Batcher.** Mettre 5-7 cycles `scroll → wait → expand → merge` dans **un seul** appel `javascript_tool` avec des `await` internes. ~6× moins d'appels. Lots petits (5-7) pour survivre aux déconnexions de l'extension. ⚠️ `javascript_tool` coupe à **45 s** (« CDP timed out ») : au-delà de ~4 cycles (≈2,5 s chacun) le lot dépasse. Le timeout n'annule PAS le travail déjà fait dans la page — refais simplement un `__merge()` court pour relire l'état, et redescends à 3-4 cycles par appel.
5. **Relations par containment, pas par ordre DOM.** Les commentaires sont rattachés à leur post via l'ancêtre commun (le helper le fait), jamais par proximité dans le flux.
6. **Capturer / juger / écrire séparément.** Capture mécanique en page (auteur, date, corps, id) → jugement à la relecture (classification, pertinence) → écriture via **Bash+curl** (le `fetch` en page est bloqué par la CSP de Facebook).
7. **Sortir les données par download blob, jamais par lecture tronquée.** La sortie de `javascript_tool` est tronquée (~950 car/appel), donc ne lis JAMAIS les corps par tranches pour les stocker (tu perdrais le texte long). À la fin de la collecte, exporte tout `window.__store` (filtré fenêtre) en **Blob → download** vers `~/Downloads`, puis lis le fichier avec `Read`/Bash : **contenu intégral, zéro troncature, zéro transcription**. (Le slice-reading ne sert qu'à un aperçu rapide, jamais à alimenter `Contenu complet`.)
8. **Un groupe à la fois, l'origine notée à chaque fois.** `window.__store` est vidé à chaque navigation : on collecte, on vérifie, on **exporte groupe par groupe**, et chaque entrée part avec le `recId` de son canal. Ne jamais mélanger deux groupes dans un même export ni dans un même `records.json` sans que chaque ligne porte son canal.
9. **Idempotence.** Le push déduplique contre la base → le skill est **relançable** autant de fois qu'on veut.

## Ressources bundlées

- **`scripts/scrape_helpers.js`** — Read ce fichier, injecte tout son contenu via `javascript_tool`. Fournit `__decodeTS`, `__parseTS`, `__harvestAll`, `__store`/`__merge`, `__expandPostText`, `__expandCommentText`, `__truncated`, `__truncatedComments`, `__exportBlocked` (garde unique avant export), `__profileUrl`, `__gid` (id du groupe courant, jamais codé en dur), `__alive`, `__chrono` (contrôle du tri), `__orphanComments` (compteur). **Ré-injecte après toute navigation** (le window est vidé).
- **`scripts/airtable_push.py`** — pousse un `records.json` en upsert-merge. Voir §5.
- **`scripts/focus_chrome.sh`** (macOS) / **`scripts/focus_chrome.ps1`** (Windows) — ramènent l'onglet du scrape au premier plan pour réveiller le rendu. Voir §1 bis.
- **`references/matching_vocab.json`** — valeurs select valides (Zones/Statuts/Temps) + mapping `macro_regions` → départements. Source de vérité pour remplir les champs de matching (cf. §3). Régénérable depuis la base si le vocab change.
- **`references/auteurs_exclus.json`** — liste des auteurs/pages à **toujours exclure**, quel que soit le contenu du post. Voir §3 Exclure. Si tu identifies un nouvel auteur à bannir durablement, ajoute-le **dans le dépôt source** (`Cleuteu/sarecrute-competences`) et non dans le dossier installé : celui-ci est réécrit à chaque `claude plugin update`, l'ajout serait perdu. Signale-le à l'utilisateur au lieu de modifier la copie locale.

## Étapes

### 0. Lire les canaux à scraper (Airtable)

**Avant d'ouvrir Chrome.** Récupère la clé (cf. §5.1), puis liste les canaux :

```bash
curl -s -H "Authorization: Bearer $AIRTABLE_API_KEY" \
  "https://api.airtable.com/v0/appP0W2ISytaNyAhG/tbluH5M2sogAN85dl?pageSize=100" \
  | python3 -c 'import json,re,sys
for r in json.load(sys.stdin)["records"]:
    f=r["fields"]; g=re.search(r"/groups/(\d+)", f.get("Url","") or "")
    if f.get("Scraper les posts") and g:
        print(r["id"], g.group(1), f.get("Name"), sep="\t")'
```

Tu obtiens `recId`, id de groupe et nom pour chaque source. L'`Url` du canal n'est **jamais** l'URL de scrape : elle décrit où l'on publie, on n'en extrait que l'id (cf. §1). Règles :
- **Ne scrape que ce qui sort de cette requête.** Un canal coché sans `/groups/<id>` (Instagram, LinkedIn, `facebook.com/me`, une page) n'est pas scrapable : **signale-le et passe**, ne tente pas de deviner une URL.
- Si un argument nomme un groupe, filtre sur son `Name` (insensible à la casse, sous-chaîne) ; si rien ne matche, dis-le et arrête plutôt que de tout scraper.
- Si la liste est vide, arrête et explique qu'aucun canal n'est coché.
- Annonce à l'utilisateur les groupes retenus **avant** de commencer (Chrome va passer devant, cf. §1 bis).

Puis déroule §1 → §4 **pour chaque groupe, l'un après l'autre**, et pousse à la fin (un `records.json` par groupe, ou un seul fichier si chaque ligne porte son `Canaux`).

### 1. Ouvrir le groupe + injecter les helpers

Navigue vers `https://www.facebook.com/groups/<id du groupe>/?sorting_setting=CHRONOLOGICAL` (l'id vient de §0 — **aucun groupe en dur**).

⚠️ **N'ouvre JAMAIS l'`Url` du canal telle quelle.** Ce champ sert à la publication : il pointe l'accueil du groupe, donc un fil trié **par pertinence**, où les posts récents ne sont pas en haut. On n'en garde que l'id, et on reconstruit l'URL avec le tri chronologique. Même règle si l'`Url` contient déjà des paramètres : on les jette.
1 screenshot pour vérifier (tri chronologique, pas de captcha) **au premier groupe seulement** ; pour les suivants, `__alive()` suffit à confirmer que la page a chargé.
Attends ~2,5 s, puis Read `scripts/scrape_helpers.js` (relatif au dossier de la compétence) et injecte son contenu. Vérifie l'heure du navigateur (`new Date().toString()` peut être bloqué à l'affichage — concatène-le à une string courte si besoin) et calcule la borne de la fenêtre.

### 1 bis. Vérifier que le rendu tourne — et réveiller la page tout seul

Juste après l'injection, **avant** le premier cycle :

```javascript
await window.__alive();     // ~1 s : {frozen, fps, visibility, articles, height, ...}
```

- `frozen: false` (fps ≈ 20-60) → enchaîne sur les cycles.
- `frozen: true` (fps ≈ 0, `visibility: "hidden"`) → **la fenêtre Chrome est masquée : remets-la au premier plan toi-même**, sans rien demander à l'utilisateur :

```bash
bash <dossier_skill>/scripts/focus_chrome.sh                      # macOS
# Windows : powershell -ExecutionPolicy Bypass -File <dossier_skill>/scripts/focus_chrome.ps1
```

  Puis **re-teste `__alive()`**. Le rendu repart en général dès que l'onglet est visible, sans rechargement.
  - Si `frozen: false` mais que le fil est resté bloqué (`articles` ≤ 3, `heightDelta` nul après un scroll d'essai) → recharge la page (`location.reload()`), attends ~2,5 s, **ré-injecte les helpers** (le window est vidé) et re-teste.
  - Si `frozen: true` **après** le passage au premier plan → là seulement, dis à l'utilisateur ce qui bloque (fenêtre Chrome minimisée sur un autre bureau/espace, session verrouillée, écran de veille) et ce qu'il doit faire.
  - Sous Windows, le script ne peut pas sélectionner l'onglet (limite de la plateforme) : s'il répond que l'onglet du scrape n'est pas l'onglet actif, demande à l'utilisateur de cliquer dessus.

⚠️ Ne laisse pas Chrome repasser en arrière-plan pendant la collecte : chaque `focus_chrome.sh` interrompt ce que l'utilisateur est en train de faire. Préviens-le en une ligne au début que la fenêtre Chrome va rester devant, et regroupe les réveils plutôt que de les répéter.

### 1 ter. Vérifier que le tri est chronologique (OBLIGATOIRE avant de collecter)

Le paramètre d'URL ne suffit pas : Facebook peut retomber sur le tri par pertinence. Après un premier `__merge()` :

```javascript
window.__merge(); JSON.stringify(window.__chrono());   // {ok, inversions, isos, url, tri}
```

- `ok: true` → lance les cycles.
- `ok: false` (plus d'une inversion dans les dates, ou `tri: "PARAM ABSENT"`) → **ne collecte pas** : la fenêtre temporelle n'aurait plus de sens et le critère d'arrêt conclurait « fin du fil » sur un vieux post remonté par l'algorithme. Re-navigue avec le paramètre, attends le chargement, ré-injecte les helpers, `__merge()` et re-teste. Si c'est encore faux au 2ᵉ essai, **passe ce groupe** en le signalant dans le résumé final plutôt que de ramener des données dont la fenêtre est fausse.
- Une seule inversion est tolérée : un post épinglé apparaît en tête sans que le reste du fil soit désordonné.

### 2. Collecter par cycles (scroll + merge)

Boucle dans **un seul** appel JS (répète si besoin), ex. :
```javascript
await (async function(){
  for (let i=0;i<6;i++){
    window.__expandPostText(); window.__expandCommentText();   // 1) déplier les "Voir plus"
    await new Promise(r=>setTimeout(r,1500));      // 2) laisser l'expansion se faire (≥1,5 s)
    window.__merge();                              // 3) MERGE APRÈS expansion (sinon on fige du tronqué)
    window.scrollBy(0,2600);
    await new Promise(r=>setTimeout(r,950));
  }
  window.__merge();
  const ps=Object.values(window.__store);
  const isos={}; ps.forEach(p=>isos[p.iso]=(isos[p.iso]||0)+1);
  return JSON.stringify({stored:ps.length, byIso:isos,
    hidden: document.visibilityState==='hidden',   // true ⇒ page gelée, cf. §1 bis
    orphans: window.__orphanComments,              // commentaires non rattachés à ce cycle (normal, ils repassent)
    tail: window.__harvestAll().slice(-6).map(p=>p.author+'/'+p.iso+'/'+p.decoded.replace(/\s/g,''))});
})();
```

**Un lot qui n'ajoute rien = suspicion de gel, pas une fin de fil.** Si `stored` n'a pas bougé et que la queue n'a pas avancé, appelle `await window.__alive()` **avant** de conclure quoi que ce soit :
- `frozen: true` → réveille la page (§1 bis) puis **reprends les cycles** ; le travail déjà en `window.__store` est intact.
- `frozen: false` → c'est un vrai plateau : applique le critère d'arrêt ci-dessous.

**Critère d'arrêt** : continuer tant que la queue (`tail`) n'a pas franchi la borne.
- ✅ S'arrêter quand **2-3 posts consécutifs** sont clairement hors fenêtre (`iso`/`ageH` au-delà de la borne) **ET** que `stored` ne croît plus entre deux lots **ET** que `__alive()` confirme que le rendu tourne (`frozen: false`).
- ✅ Au moins ~15 cycles cumulés sur un groupe actif avant de conclure.
- ⚠️ Ne jamais s'arrêter sur un seul timestamp ambigu.

Note : `__parseTS` met midi par défaut pour les dates sans heure ; quand l'heure est présente (« Le 20 juin à 19:41 ») elle est exacte. Pour une borne fine (« aujourd'hui », 48h), filtre sur `iso`/`ageH` calculé.

### 2 bis. Vérifier qu'AUCUN post NI commentaire n'est tronqué (OBLIGATOIRE avant export)

Le merge est auto-réparant (il garde le corps le plus long), mais un post jamais déplié reste tronqué. **Avant d'exporter**, contrôle qu'il ne reste aucun « Voir plus » non déplié — **posts ET commentaires** :
```javascript
JSON.stringify({stop: window.__exportBlocked('<borne YYYY-MM-DD>'),
                posts: window.__truncated(), coms: window.__truncatedComments()});
```
- `stop` **vide** → OK, passe à l'export.
- `stop` **non vide** : ces entrées (souvent les plus récentes, en haut du fil) ont été captées avant dépliage. Remonte jusqu'à elles (`window.scrollTo(0,0)` puis re-descends par petits pas de ~650 px), en refaisant `__expandPostText()` **et `__expandCommentText()`** → attendre **≥1,5 s** → `__merge()` à chaque pas, puis **re-vérifie**. Répète jusqu'à `stop` vide. Ne jamais exporter tant que ce n'est pas le cas.

⚠️ `__truncated()` seul ne suffit pas : il ne regarde que les **posts**. Un commentaire figé sur « Bonjour,… Voir plus » passait donc en base sans aucun signal (constaté le 10 août 2026). Utilise `__exportBlocked(borne)`, qui contrôle les deux — et qui filtre sur la fenêtre, pour ne pas te bloquer sur un vieux post hors périmètre qui ne sera pas exporté.

> **Permalinks — limite connue.** Sur le fil, FB n'injecte l'id du post (donc le permalink reconstructible via `p.permalink`) que pour **~40 % des posts**. Testé et **écarté** pour débloquer le reste : le `.click()` JS sur la date ne navigue **que** pour les posts déjà résolus (n'apporte rien) ; le **hover** ne résout rien (`isTrusted=false`) ; l'attente/dwell non plus ; le fiber React n'expose pas de props lisibles. Donc ~60 % retombent sur l'URL de recherche (repli prévu). Seule piste restante non testée : le menu « … » → « Copier le lien » par post.
>
> **À ne pas confondre avec le profil de l'auteur** (`p.authorUrl`), qui lui est disponible sur **100 %** des auteurs nommés : il vient de l'ancre du header (`/groups/{gid}/user/{uid}/`), pas de l'id du post. Aucun clic ni navigation nécessaire.

⚠️ C'est la garantie que `Contenu complet` sera intégral. La cause historique des posts tronqués en base était un merge qui figeait le corps à la première capture (avant dépliage) — c'est corrigé dans `scripts/scrape_helpers.js`, mais cette vérification reste le filet de sécurité.

### 3. Exporter la fenêtre (download blob) puis filtrer + classifier

**D'abord, sors les données de la page** (le contenu doit être **complet**, la sortie JS est tronquée à ~950 car). Utilise `__cleanBody` pour retirer les marqueurs FB finaux (« Voir plus »/« Voir moins »). Dans un `javascript_tool`, construis la fenêtre et déclenche un download :
```javascript
(function(){
  const stop = window.__exportBlocked('<borne YYYY-MM-DD>');   // posts ET commentaires
  if (stop) return stop;
  const win = Object.values(window.__store).filter(p=>p.iso && p.iso>='<borne YYYY-MM-DD>');
  const data = win.map(p=>({author:p.author, authorUrl:p.authorUrl, iso:p.iso, gid:p.gid||window.__gid(), pid:p.pid, permalink:p.permalink,
    body:window.__cleanBody(p.body),                                  // corps INTÉGRAL, marqueurs FB retirés
    comments:Object.values(p.comments).map(c=>({name:c.name,profileUrl:c.profileUrl,time:c.time,text:(c.text||'').replace(/\s+/g,' ').trim()}))}));
  const blob=new Blob([JSON.stringify(data)],{type:'application/json'});
  const url=URL.createObjectURL(blob); const a=document.createElement('a');
  a.href=url; a.download='veto_'+window.__gid()+'.json'; document.body.appendChild(a); a.click();   // un fichier par groupe
  setTimeout(()=>{URL.revokeObjectURL(url);a.remove();},2000);
  return 'download '+data.length+' posts';
})();
```
Puis copie/lis le fichier localement : `cp ~/Downloads/veto_<gid>.json <scratchpad>/` puis `Read`. Tu disposes alors du **texte intégral** de chaque post + commentaires, sans troncature ni transcription base64.

Filtre la fenêtre sur `iso` (ou `ageH`) et classe depuis ce fichier local.

#### Exclure (ne PAS compter comme offre) :
- **Auteur blacklisté** : Read `references/auteurs_exclus.json` (bundlé) en début de classification. Si `p.author` (ou la signature/coordonnées en fin de post) matche une entrée de la liste (insensible à la casse, substring) → exclu d'office, **sans lire le contenu pour juger de la pertinence**.
- Pas une annonce d'emploi vétérinaire (ni « cherche poste », ni « cherche vétérinaire »).
- Question générale, partage d'article, sondage, RH sans annonce, formation, appel à thèse/sondage, **offre ASV** sans lien vétérinaire.
- **Intermédiaire de recrutement, ou groupe de cliniques** : cabinet de recrutement, chasseur de têtes, RH/recruteur d'un groupe (Univet, Mon Véto, Qovetia, Smartemis…), **et aussi une clinique appartenant à un groupe même quand elle recrute pour elle-même**. On ne veut que les annonces de **cliniques indépendantes** — un intermédiaire ne donne pas accès à la clinique et pollue la géographie, et une offre de groupe n'est pas commercialisable. Voir le §Détecter un intermédiaire ci-dessous.
- Si exclu pour **non-pertinence** (les motifs ci-dessus, hors blacklist) → ignorer aussi ses commentaires.
- ⚠️ **La blacklist, elle, s'applique à l'auteur — jamais au post en tant que contenant.** Elle se teste **entrée par entrée**, sur `p.author` comme sur chaque `c.author` :
  - **Post d'un auteur blacklisté** → pas d'entrée pour le post…
  - …mais **ses commentaires restent à traiter normalement**. Un candidat qui postule sous l'annonce d'un cabinet concurrent est une information **précieuse** : on apprend qu'il cherche un poste. Le commentaire entre en base avec les règles habituelles (§Commentaires pertinents), y compris l'intégralité du post parent blacklisté dans `Contenu complet` — c'est le contexte de sa candidature.
  - **Commentaire d'un auteur blacklisté** sous le post d'un tiers (« envoyez-moi un MP pour discuter de votre recherche ») → **pas d'entrée** pour ce commentaire ; le post parent et les autres commentaires ne sont pas affectés.
  - Constaté le 11 août 2026 : les deux sens étaient faux — un cabinet blacklisté entrait en base en commentant, et les candidatures sous ses annonces étaient jetées.
#### Détecter un intermédiaire de recrutement (cabinet, chasseur de têtes, RH de groupe)

Signal principal, et il est fiable : **un même auteur qui publie des postes dans des zones
géographiquement distinctes.** Une clinique recrute pour elle-même, donc à **un seul endroit** ;
seul un intermédiaire recrute à Béziers, Ferney-Voltaire et La Souterraine le même mois.

- Compare les **départements** des annonces d'un même auteur, sur la fenêtre **et** contre ce qui
  est déjà en base pour lui (le `Contenu complet` de son record empile ses posts précédents).
- ⚠️ **Neutralise les mentions de proximité avant de compter** : « à 1h de Paris », « 15 min des
  Sables d'Olonne », « 10 min du RER B », « à 25 min de Nancy et de Metz » citent un département
  voisin **pour situer**, pas un second poste. Compté naïvement, ça transforme toute clinique bien
  desservie en faux positif (testé : c'est le principal générateur de bruit).
- **Départements limitrophes** (73/74, 16/17, 81/82…) = une clinique en zone frontière, **pas** un
  intermédiaire. Le signal ne vaut que pour des zones **éloignées**.
- Signaux d'appui, jamais suffisants seuls : aucune clinique nommée, contact exclusivement « en MP »,
  formulations « je recrute **pour** une clinique », « nous **accompagnons** des cliniques
  partenaires », « nos équipes de X et Y », « voici **nos** postes ouverts ».

**Que faire** : ne pousse pas ses annonces, et **préviens l'utilisateur dans le résumé final** —
auteur, nombre d'annonces, départements constatés, extrait — pour qu'il tranche.

⛔ **N'ajoute JAMAIS personne à `auteurs_exclus.json` sans son accord explicite, demandé au
préalable.** Détecter, c'est ton travail ; bannir, c'est le sien. Tu présentes les éléments, il
répond, et seulement ensuite tu écris dans le fichier — dans le **dépôt source**, jamais dans la
copie installée (cf. §Ressources bundlées). Vaut aussi pour la suppression de ses entrées déjà
en base : proposer, pas exécuter.

Un même groupe peut employer **plusieurs** recruteurs qui postent pour les mêmes cliniques :
signale le rapprochement quand tu le vois, il y a plusieurs entrées à proposer.

**Le nom du groupe est lui-même une bonne entrée de blacklist** (Univet, Mon Véto, Qovetia,
Smartemis, Fovéa-Vet…) : on ne rentre **aucune** offre de groupe, y compris celle d'une de ses
cliniques qui recrute pour elle-même. Une entrée d'enseigne couvre d'un coup tous ses recruteurs,
présents et futurs, sans attendre qu'ils se signalent par leur géographie.
- Le marqueur le plus fiable est le **domaine mail ou le site carrière** en signature
  (`@smartemis.com`, `veterinaire-monveto.com`, `smartemisfrance.teamtailor.com`) — il est présent
  même quand le nom du groupe n'apparaît nulle part dans le texte, et il ne produit pas de faux
  positif. Préfère-le au nom commercial quand les deux existent.
- Attention aux **tournures banales** : « mon véto » se dit couramment. Une entrée d'enseigne
  ambiguë ne s'applique qu'à l'auteur, à la signature ou à une URL, jamais au milieu d'une phrase.
- Une clinique de groupe se présente souvent comme « structure indépendante » : ne te fie pas à
  cette formule, regarde la signature.

- ⚠️ **Ne JAMAIS pousser un post exclu dans Airtable, même avec `"Non pertinent": true`.** Ce champ est réservé au **recruteur** (usage manuel côté Airtable) — le scrape ne doit jamais l'écrire. Un post jugé non pertinent avant l'envoi est simplement **ignoré** (pas d'entrée créée), pas loggé. Mentionne-le uniquement dans le résumé final (compte + raison courte).

#### Classer candidat vs clinique (à ne PAS rater — sinon ça pollue le matching)
Le `Type de post` conditionne tout. Décide sur le **sens du texte**, pas sur l'auteur :
- → **`Clinique cherche vétérinaire`** : 1re personne du pluriel ou nom de structure (« **Nous recrutons** », « la clinique recherche un(e) vétérinaire », « poste à pourvoir », « rejoignez notre équipe »), signature/coordonnées de clinique, mention d'un contrat proposé (« CDI/collaboration libérale à pourvoir »). ⚠️ Un particulier peut poster ce type d'annonce — c'est bien `Clinique cherche vétérinaire` (ex. « Nous recrutons… COLLABORATION LIBÉRALE »).
- → **`Vétérinaire cherche poste`** : 1re personne du singulier qui parle de **soi** (« je recherche un poste/remplacement », « diplômé(e) en… je cherche », « disponible pour des remplacements »).
- ⚠️ **Pas de troisième option.** Le champ `Type de post` ne prend que ces deux valeurs — jamais `Autre`. En cas de doute réel entre les deux, ne force jamais `Vétérinaire cherche poste` par défaut ; **exclus le post** (cf. §Exclure ci-dessus, même traitement qu'un post non pertinent — pas d'entrée créée, mentionné uniquement dans le résumé final).

#### Champs d'un post retenu :
- **Prénom / Nom** : depuis l'auteur (clinique/page → Prénom vide, Nom = nom de la page). « Membre anonyme » → vides. ⚠️ Matche les posts par **corps**, pas par auteur (l'auteur peut être mal capté). Soigne cette capture : le push en dérive le `candidat_key` pour fusionner les re-posts d'une même personne (cf. §5). Ne « répare » pas un nom tronqué en inventant — laisse tel quel (le push le traitera comme non fusionnable).
- **`candidat_key`** : **ne pas le renseigner** — le push le calcule depuis Prénom+Nom.
- **Profil Facebook** : `p.authorUrl` tel quel (`https://www.facebook.com/{uid}`, reconstruit depuis l'ancre du header — validé en live : redirige vers le profil réel). **Vide pour « Membre anonyme »** (FB ne rend alors aucune ancre) — laisse vide, ne devine jamais. ⚠️ Si `authorUrl` est vide alors que l'auteur est nommé, c'est que la capture de l'auteur est retombée sur le fallback `strong` (souvent un post sponsorisé) : **vérifie le nom** avant de pousser, ou exclus le post s'il s'agit d'une pub.
- **Canaux** : `["<recId du canal>"]`, le canal de §0 dont le `gid` correspond à celui du post (`p.gid`). **Obligatoire sur chaque ligne**, post comme commentaire — c'est ce qui donne l'origine du contenu. Le push refuse un `recId` inconnu et n'en crée jamais ; il écrit aussi le nom du canal dans l'en-tête de la section (`[date] lien · Canal`), donc l'origine reste lisible post par post même après fusion de plusieurs groupes sur une même personne.
- **Date du post** : `iso` (YYYY-MM-DD).
- **Lien du post** : utilise **`p.permalink`** tel quel (reconstruit à la capture depuis l'id du groupe courant et celui du post : `…/groups/{gid}/posts/{pid}/`) — c'est un vrai lien qui ouvre le post. **N'utilise une URL de recherche `…/search?q=<mots-clés url-encodés>` qu'en dernier recours**, si `p.permalink` ET `p.pid` sont vides. (Validé en live : le permalink se reconstruit depuis l'`innerHTML` du conteneur, y compris sur les posts à timestamp obfusqué où le href de l'ancre est vide.)
- **Zone de recherche**, **Contenu complet** = le **texte INTÉGRAL du post** (jamais tronqué ni résumé — c'est pour ça qu'on passe par le download blob), **Type de post** (`Vétérinaire cherche poste` | `Clinique cherche vétérinaire`).
- **Pratiques** ⊆ {Canine, Bovins, Equine, NAC, Allaitant, Laitier, Ovin/Caprin, Porcin, Loups, Volailles}.
- **Spécialités** ⊆ {Chirurgie, Urgences, Echographie, Orthopédie, Ophtalmologie, Laboratoire, Ostéopathie, Management, Cardiologie, Reproduction, Oncologie, Neurologie, Médecine interne}.
- **Type d'entrée** = `Post`. **Post source** vide. **Nom de la clinique** si type clinique.
- **Expérience** (cf. règles ci-dessous).

⚠️ **Ne jamais inventer de nouvelle valeur** de champ select (Pratiques/Spécialités/Type/Expérience). Si rien ne colle, laisse vide.

#### Champs de matching (post `Vétérinaire cherche poste`)
Renseigne **uniquement** avec des valeurs de **`references/matching_vocab.json`** (bundlé). Laisse vide si non dit — ne devine pas. Le push ignore de toute façon toute valeur hors vocab.
- **Zones de recherche** (multiselect) : normalise la zone libre + le texte en **départements/pays**.
  - Code entre parenthèses (« (69) », « (31/82) ») ou ville → le département (`69 - Rhône`, `31 - Haute-Garonne`…).
  - **Macro-région → toujours développer en départements** via `macro_regions` du vocab (ex. « Sud-Ouest » → NA+Occitanie ; « Bourgogne » → 21/58/71/89 ; « Massif Central », « Quart Sud-Est »…). Pas de seuil.
  - « Toute la France » / **« mobile »** / aucune contrainte → `France`.
  - Frontalier / pays → la valeur pays (`Belgique`, `Suisse`…), + cantons/provinces si précisés.
- **Statuts contractuels** (multiselect) : `CDI`, `CDD` (⚠️ **remplacement / missions / vacation = CDD**), `Association`, `Collaboration libérale`, `Internat` (⚠️ **clinicat = Internat**), `Prophylaxie`, `Achat/Vente de clinique`. « poste » générique sans mot-clé contrat → **laisse vide**.
- **Type de temps de travail** : `Temps plein` / `Temps partiel` (les deux si « plein ou partiel »).
- **Date de disponibilité** (YYYY-MM-DD) : si vague, **1er jour estimé** — « septembre » → `2026-09-01` ; « fin d'année » → `2026-12-01` ; « semaine 42 » → lundi de la semaine ISO 42. Sinon vide.
- **Rayon accepté (km)** : convertis « X km » / « X min » (≈ X km) en nombre, si mentionné.
- **Contrat court** (checkbox) : le candidat cherche une mission de **moins d'un mois**. Coché ⇒ le post est **exclu du matching** avec les offres, donc à trancher avec soin. Renseigne-le **explicitement (true ou false) sur toute entrée `Vétérinaire cherche poste`**, jamais vide (c'est un scalaire : le push fait gagner le post le plus récent, un champ omis figerait l'ancienne valeur).
  - ✅ **Coche** si une **durée explicite < 1 mois** est donnée : dates bornées (« du 24 au 28 août », « semaine du 27 juillet », « du 28 septembre au 23 octobre »), « 2-3 semaines max », « la semaine prochaine », « les deux dernières semaines d'août ».
  - ✅ **Coche** si, sans durée, le **vocabulaire est clairement ponctuel** : « vacations », « quelques jours », « gardes de nuit », « week-ends de garde », « astreintes », « rempla **court** », « courtes durées », « 10-15 jours par mois en renfort », semaines ISO isolées (« semaines 39, 42, 43 »).
  - ❌ **Ne coche pas** si la durée annoncée est **≥ 1 mois** (CDD 2 mois, « juillet et août », « mi-septembre à fin octobre », saison de vêlage), ni sur « **remplacements** » / « missions » **seul** sans durée ni vocabulaire ponctuel — dans le doute, laisse `false` (le coché exclut du matching, le non-coché laisse le recruteur juger).
  - ⚠️ Un **temps partiel durable** (mi-temps à l'année, « consultations le samedi 1 semaine sur 2 ») n'est **pas** un contrat court : c'est un petit volume, pas une courte durée.
  - ⚠️ **Jamais hérité par un commentaire** depuis son post parent (contrairement à Zones/Statuts/Temps/Expérience) : un candidat qui commente une annonce courte ne cherche pas forcément du court, et cocher à tort le sort de tout le matching. Coche uniquement si **le commentaire lui-même** le dit.

#### Commentaires pertinents (cf. §4 pour la capture)
- Sous « Clinique cherche vétérinaire » → **candidat** (profil, dispo, zone, compétences) — y compris « MP envoyé » → contenu = `Candidature en MP`.
- Sous « Vétérinaire cherche poste » → **clinique/recruteur** (propose poste/zone/contrat) — y compris « je t'envoie un MP » → contenu = `Proposition en MP`.
- **Ignorer** : encouragements (« Bravo », « Courage », « Ne pas hésiter »), tags d'un tiers sans info, questions/critiques sans recrutement, et **les commentaires de l'auteur sur son propre post**.
- Champs : **Canaux** = celui du post parent (un commentaire vient forcément du même groupe) ; Prénom/Nom du commentateur ; **Profil Facebook** = `c.profileUrl` (celui du **commentateur**, jamais celui du post parent ; vide si absent) ; Date = date du commentaire (sinon du post) ; Lien = même que le parent ; Zone (du commentaire, sinon du parent) ; Contenu (texte, ou « Candidature/Proposition en MP ») ; **Type de post inversé** vs parent ; Pratiques/Spécialités déduites (sinon du parent) ; **Type d'entrée** = `Commentaire` ; **Post source** = `{Auteur du post} - {résumé court}` ; Expérience ; Nom de la clinique si recruteur.
- **Tout commentaire conservé — inclure l'INTÉGRALITÉ du post parent** : le `Contenu complet` du commentaire = le **texte du commentaire** (ou « Candidature/Proposition en MP ») **suivi de l'intégralité du post parent**. Le post parent est l'entrée de `__store`/export qui **porte** ce commentaire (son `body`) — jamais à re-scrapper séparément. Format :
  ```
  {texte du commentaire}

  ━━━ Post commenté — {auteur du post} ({date}) ━━━
  {body intégral du post parent}
  ```
  Ainsi un commentaire est toujours exploitable seul (le lien FB pointe le parent, mais son texte est déjà là).
- **Commentaire candidat (sous une annonce clinique)** — en plus : **hérite des caractéristiques du post parent** — `Zones de recherche`, `Statuts contractuels`, `Type de temps de travail`, `Expérience`, `Pratiques`, `Spécialités` (**jamais `Contrat court`**, cf. §Champs de matching) — mêmes règles d'extraction/vocab que pour un post. **Sauf** indication **contraire explicite** du commentaire (sa valeur prime ; s'il réserve/exclut sans alternative, laisse le champ vide).

#### Règles Expérience (singleSelect)
- **Etudiant** : école/stage/carte verte en attente de diplôme.
- **Débutant** : jeune diplômé, < 1 an, « débutant accepté », « carte verte acceptée ».
- **1 à 2 ans** : 1-2 ans explicitement.
- **Autonome** : expérimenté/autonome/senior/3 ans+ — **défaut** quand de l'expérience est requise sans durée précise.
- **Spécialiste** : très pointu / +7 ans / expertise — **rare**, seulement si explicite.
- Vide si aucune info.

### 4. Commentaires — capture

Les commentaires sont déjà récoltés par `__harvestAll`/`__merge` (champ `comments` de chaque post), via `div[role="article"][aria-label="Commentaire de {Nom} il y a {temps}"]`.

**Couverture par défaut (sûre)** : `__merge()` n'attrape que les commentaires affichés (« plus pertinents ») au fil du scroll. **NE PAS cliquer « Voir plus de commentaires »** ni le compteur de commentaires : ça navigue vers le permalink et vide le window. (`__expandCommentText()` est sûr : il ne clique que l'expander de texte *à l'intérieur* d'un commentaire, dont le libellé exact ne matche jamais « Voir plus de commentaires ».)

**Rattachement — ce qui est garanti et ce qui ne l'est pas.** Un commentaire est rattaché au post via **son propre conteneur `div[role="article"]`**, jamais par proximité dans le flux. Si le conteneur ne contient aucune ancre de timestamp — la virtualisation de FB est **partielle**, le commentaire peut être rendu alors que l'en-tête de son post ne l'est plus — le commentaire est **abandonné** pour ce cycle et compté dans `__orphanComments` ; il repassera à un cycle suivant. **Un `orphans` non nul dans le retour d'un lot est normal, ce n'est pas une erreur.**

⚠️ Ne rétablis jamais un repli « plus proche timestamp qui précède » comme mécanisme principal : le 10 août 2026 il a recopié le jeu de commentaires de deux posts sur un post voisin qui ne les portait pas. Un commentaire mal rattaché est **pire** qu'un commentaire manquant — il fabrique un faux candidat sous une annonce qui n'est pas la sienne, et le `Post source` comme le post parent recopié dans `Contenu complet` deviennent faux. En cas de doute à la relecture, vérifie la cohérence du contenu (un commentaire sur des fiches de révision n'appartient pas à une annonce d'emploi) et écarte.

**Couverture exhaustive (optionnelle, plus lente)** : pour les posts à fort engagement, ouvrir le **permalink** du post dans l'onglet (`…/posts/{pid}/`) où **tous** les commentaires sont visibles sans virtualisation, ré-injecter `scripts/scrape_helpers.js`, `__merge()`, puis revenir au feed. Ne le faire que si l'utilisateur veut la couverture complète.

### 5. Pousser dans Airtable (Bash + curl, déduplication)

1. **Clé API** — dans l'ordre : si `$AIRTABLE_API_KEY` est déjà dans l'environnement, l'utiliser ;
   sinon sur macOS/Linux la relire du shell
   (`export AIRTABLE_API_KEY=$(grep AIRTABLE_API_KEY ~/.zshrc | head -1 | sed 's/.*="\(.*\)"/\1/')`) ;
   sinon (Windows, ou clé absente) **demander la clé à l'utilisateur** et l'exporter pour la session —
   ne jamais l'écrire dans un fichier du dépôt ni dans `records.json`.
2. Écris les enregistrements jugés dans un fichier `records.json` (liste de `{"fields": {...}}`), **hors du dossier de la compétence** (scratchpad de session).
3. `python3 <dossier_skill>/scripts/airtable_push.py records.json --dry` puis sans `--dry`.

Le script fait un **upsert-merge par personne** (ne renseigne pas `candidat_key`, il le calcule) :
- **Nom fiable** (`candidat_key` non vide) → si la personne existe déjà (toutes dates confondues), il **met à jour** son enregistrement : le nouveau post est empilé **en haut** de `Contenu complet` (séparateur `──────────`, en-tête `[date] lien`), et les champs scalaires (Date, Zone, Pratiques…) prennent les valeurs du **post le plus récent**. Sinon il crée.
- **Nom anonyme / non fiable** (vide, « Membre anonyme », tout en capitales, marqueurs orga, surnom tronqué type *Lmd/Drc/Vie*) → **pas de fusion** : création, sauf si **exactement la même publication** est déjà en base.
- **Cross-post identique entre deux groupes** → aucune section nouvelle (la signature d'une section est *date + corps*, pas le lien), mais une **origine** nouvelle : le script ajoute alors le canal manquant sans toucher au contenu ni aux champs scalaires (ligne `⊕ CANAL` en `--dry`). Vaut dans les deux régimes ci-dessus, y compris quand les deux exemplaires arrivent dans le même `records.json`.

Idempotent : re-scraper un post déjà fusionné ne change rien (garde par section `[date] lien`). `--dry` affiche le plan (CRÉER / MAJ / ⊕ CANAL). Push par lots de 10.

**La fusion par personne vaut pour les DEUX types de post**, clinique comprise : une clinique qui
republie son annonce, la reformule ou ouvre un second poste au même endroit doit rester **un seul
enregistrement**. C'est le régime par défaut, ne le contourne pas.

Deux garde-fous, à appliquer **avant** d'écrire dans `records.json` :

- **Annonce vraiment différente ⇒ entrée séparée.** Une clinique peut recruter en mars, puis
  chercher un **autre** vétérinaire en septembre — c'est une nouvelle annonce, pas un re-post. À
  séparer quand le poste change (espèce/pratique, contrat, spécialité) **ou** que plusieurs mois
  séparent les deux publications sans continuité de texte. À fusionner quand c'est le même poste
  reformulé, relancé ou remonté. Dans le doute, **fusionne** : deux sections empilées dans un même
  record restent lisibles, alors qu'un doublon éclaté fausse les décomptes de prospection.
  ⚠️ Après §Détecter un intermédiaire, un même auteur postant dans **des départements éloignés**
  n'est pas ce cas de figure : ne l'éclate pas en plusieurs entrées, **exclus-le et signale-le**.
- **Vérifie contre ce qui est déjà en base**, pas seulement contre la fenêtre courante : le
  `Contenu complet` du record existant contient l'historique des sections de cet auteur, c'est
  là que se voit un « même poste qu'en juin ».

Historique (11 août 2026) : `candidat_key` avait été conçu pour les posts candidat et appliqué tel
quel aux posts clinique. Sur 681 posts clinique, ça avait produit **34 records agrégeant des
annonces sans rapport** (pire cas : 20 sections / 18 offres distinctes) — tous des intermédiaires
de recrutement, désormais exclus à la source. La clé reste la bonne pour de vraies cliniques.

⚠️ **Le script s'arrête si `references/matching_vocab.json` est introuvable** et que `records.json` porte un champ select protégé (`Zones de recherche`, `Statuts contractuels`, `Type de temps de travail`) : sans vocabulaire, une valeur mal orthographiée créerait une option Airtable. Ne « répare » jamais ça en retirant le contrôle — corrige le chemin. (Avant le 10 août 2026 un `except` silencieux désactivait le garde-fou sans le dire.)

### 6. Résumé final

- Fenêtre couverte (avec heures).
- **Un décompte par groupe** (et les canaux cochés qui n'ont pas pu être scrapés, avec la raison).
- Posts scrappés / retenus / exclus (avec raisons).
- Commentaires pertinents (candidats / cliniques).
- Doublons ignorés (par le dédup).
- **Nouveaux enregistrements réellement créés.**
- **Intermédiaires de recrutement suspectés** (§Détecter un intermédiaire) : un bloc à part, jamais
  noyé dans le décompte des exclusions. Pour chacun : auteur, nombre d'annonces, **départements
  constatés**, un extrait, et le rapprochement s'il partage des cliniques avec un autre auteur.
  Termine par la question explicite : faut-il l'ajouter à `auteurs_exclus.json` et supprimer ses
  entrées existantes ? C'est une décision de l'utilisateur, pas la tienne.
- Mentionne si la couverture commentaires est partielle (défaut) ou exhaustive.
