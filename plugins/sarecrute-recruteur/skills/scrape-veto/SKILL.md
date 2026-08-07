---
name: scrape-veto
description: Scrape les posts du groupe Facebook vétérinaire (fenêtre temporelle paramétrable, 6h par défaut) + commentaires pertinents, et pousse tout dans Airtable "Posts scrappés" en déduplicant. Args possibles ex. "aujourd'hui", "48h", "2 derniers jours".
---

# Scrape Veto

Scraper les posts du groupe Facebook vétérinaire (tri chronologique) sur une **fenêtre temporelle**, en extraire les commentaires pertinents, et pousser chaque entrée dans Airtable **sans créer de doublon**.

**Fenêtre** : lue depuis les arguments (ex. `aujourd'hui`, `48h`, `2 derniers jours`, `6h`). Défaut = **6 dernières heures**. L'horloge de référence est celle du **navigateur** (`new Date()` dans la page), pas la date système — vérifie-la au début.

**Navigateur — OBLIGATOIRE** : utilise le **Chrome réel de l'utilisateur** via les outils `mcp__claude-in-chrome__*` (session Facebook déjà connectée). **N'utilise PAS** le navigateur in-app (`mcp__Claude_Browser__*` / `preview_start`) : il n'a pas de session FB → page déconnectée, scrape impossible. Au départ : `list_connected_browsers` → `select_browser` → `tabs_create_mcp` (nouvel onglet dédié) → `navigate`.

## Principes (à respecter — c'est ce qui rend le scrape fiable et rapide)

1. **Accumulateur persistant en page.** Le DOM de FB est virtualisé (4-5 posts en mémoire). On ne lit jamais « ce qui est à l'écran à la fin » : on appelle `__merge()` **à chaque pas de scroll** pour fusionner dans `window.__store`. Tout en dépend.
2. **Tout en JS dans la page.** 1 seul screenshot au départ (vérifier chargement + pas de captcha), puis **zéro**. Lecture/scroll/clic via `javascript_tool`. Les données obfusquées se **reconstruisent** (cf. timestamps), on ne survole/screenshote pas.
3. **Batcher.** Mettre 5-7 cycles `scroll → wait → expand → merge` dans **un seul** appel `javascript_tool` avec des `await` internes. ~6× moins d'appels. Lots petits (5-7) pour survivre aux déconnexions de l'extension. ⚠️ `javascript_tool` coupe à **45 s** (« CDP timed out ») : au-delà de ~4 cycles (≈2,5 s chacun) le lot dépasse. Le timeout n'annule PAS le travail déjà fait dans la page — refais simplement un `__merge()` court pour relire l'état, et redescends à 3-4 cycles par appel.
4. **Relations par containment, pas par ordre DOM.** Les commentaires sont rattachés à leur post via l'ancêtre commun (le helper le fait), jamais par proximité dans le flux.
5. **Capturer / juger / écrire séparément.** Capture mécanique en page (auteur, date, corps, id) → jugement à la relecture (classification, pertinence) → écriture via **Bash+curl** (le `fetch` en page est bloqué par la CSP de Facebook).
7. **Sortir les données par download blob, jamais par lecture tronquée.** La sortie de `javascript_tool` est tronquée (~950 car/appel), donc ne lis JAMAIS les corps par tranches pour les stocker (tu perdrais le texte long). À la fin de la collecte, exporte tout `window.__store` (filtré fenêtre) en **Blob → download** vers `~/Downloads`, puis lis le fichier avec `Read`/Bash : **contenu intégral, zéro troncature, zéro transcription**. (Le slice-reading ne sert qu'à un aperçu rapide, jamais à alimenter `Contenu complet`.)
6. **Idempotence.** Le push déduplique contre la base → le skill est **relançable** autant de fois qu'on veut.

## Ressources bundlées

- **`scripts/scrape_helpers.js`** — Read ce fichier, injecte tout son contenu via `javascript_tool`. Fournit `__decodeTS`, `__parseTS`, `__harvestAll`, `__store`/`__merge`, `__expandPostText`, `__profileUrl`. **Ré-injecte après toute navigation** (le window est vidé).
- **`scripts/airtable_push.py`** — pousse un `records.json` en upsert-merge. Voir §5.
- **`references/matching_vocab.json`** — valeurs select valides (Zones/Statuts/Temps) + mapping `macro_regions` → départements. Source de vérité pour remplir les champs de matching (cf. §3). Régénérable depuis la base si le vocab change.
- **`references/auteurs_exclus.json`** — liste des auteurs/pages à **toujours exclure**, quel que soit le contenu du post. Voir §3 Exclure. Si tu identifies un nouvel auteur à bannir durablement, ajoute-le **dans le dépôt source** (`Cleuteu/sarecrute-competences`) et non dans le dossier installé : celui-ci est réécrit à chaque `claude plugin update`, l'ajout serait perdu. Signale-le à l'utilisateur au lieu de modifier la copie locale.

## Étapes

### 1. Ouvrir le groupe + injecter les helpers

Navigue vers `https://www.facebook.com/groups/318289868699508/?sorting_setting=CHRONOLOGICAL`.
1 screenshot pour vérifier (tri chronologique, pas de captcha). Ensuite plus aucun screenshot.
Attends ~2,5 s, puis Read `scripts/scrape_helpers.js` (relatif au dossier de la compétence) et injecte son contenu. Vérifie l'heure du navigateur (`new Date().toString()` peut être bloqué à l'affichage — concatène-le à une string courte si besoin) et calcule la borne de la fenêtre.

### 2. Collecter par cycles (scroll + merge)

Boucle dans **un seul** appel JS (répète si besoin), ex. :
```javascript
await (async function(){
  for (let i=0;i<6;i++){
    window.__expandPostText();                    // 1) déplier les "Voir plus"
    await new Promise(r=>setTimeout(r,1500));      // 2) laisser l'expansion se faire (≥1,5 s)
    window.__merge();                              // 3) MERGE APRÈS expansion (sinon on fige du tronqué)
    window.scrollBy(0,2600);
    await new Promise(r=>setTimeout(r,950));
  }
  window.__merge();
  const ps=Object.values(window.__store);
  const isos={}; ps.forEach(p=>isos[p.iso]=(isos[p.iso]||0)+1);
  return JSON.stringify({stored:ps.length, byIso:isos,
    tail: window.__harvestAll().slice(-6).map(p=>p.author+'/'+p.iso+'/'+p.decoded.replace(/\s/g,''))});
})();
```

**Critère d'arrêt** : continuer tant que la queue (`tail`) n'a pas franchi la borne.
- ✅ S'arrêter quand **2-3 posts consécutifs** sont clairement hors fenêtre (`iso`/`ageH` au-delà de la borne) **ET** que `stored` ne croît plus entre deux lots.
- ✅ Au moins ~15 cycles cumulés sur un groupe actif avant de conclure.
- ⚠️ Ne jamais s'arrêter sur un seul timestamp ambigu.

Note : `__parseTS` met midi par défaut pour les dates sans heure ; quand l'heure est présente (« Le 20 juin à 19:41 ») elle est exacte. Pour une borne fine (« aujourd'hui », 48h), filtre sur `iso`/`ageH` calculé.

### 2 bis. Vérifier qu'AUCUN post n'est tronqué (OBLIGATOIRE avant export)

Le merge est auto-réparant (il garde le corps le plus long), mais un post jamais déplié reste tronqué. **Avant d'exporter**, contrôle qu'il ne reste aucun « Voir plus » non déplié :
```javascript
JSON.stringify(window.__truncated());   // -> [] attendu
```
- Si la liste est **vide** → OK, passe à l'export.
- Si **non vide** : ces posts (souvent les plus récents, en haut du fil) ont été captés avant dépliage. Remonte jusqu'à eux (`window.scrollTo(0,0)` puis re-descends par petits pas de ~650 px), en refaisant `__expandPostText()` → attendre **≥1,5 s** → `__merge()` à chaque pas, puis **re-vérifie `__truncated()`**. Répète jusqu'à `[]`. Ne jamais exporter tant que ce n'est pas vide.

> **Permalinks — limite connue.** Sur le fil, FB n'injecte l'id du post (donc le permalink reconstructible via `p.permalink`) que pour **~40 % des posts**. Testé et **écarté** pour débloquer le reste : le `.click()` JS sur la date ne navigue **que** pour les posts déjà résolus (n'apporte rien) ; le **hover** ne résout rien (`isTrusted=false`) ; l'attente/dwell non plus ; le fiber React n'expose pas de props lisibles. Donc ~60 % retombent sur l'URL de recherche (repli prévu). Seule piste restante non testée : le menu « … » → « Copier le lien » par post.
>
> **À ne pas confondre avec le profil de l'auteur** (`p.authorUrl`), qui lui est disponible sur **100 %** des auteurs nommés : il vient de l'ancre du header (`/groups/{gid}/user/{uid}/`), pas de l'id du post. Aucun clic ni navigation nécessaire.

⚠️ C'est la garantie que `Contenu complet` sera intégral. La cause historique des posts tronqués en base était un merge qui figeait le corps à la première capture (avant dépliage) — c'est corrigé dans `scripts/scrape_helpers.js`, mais cette vérification reste le filet de sécurité.

### 3. Exporter la fenêtre (download blob) puis filtrer + classifier

**D'abord, sors les données de la page** (le contenu doit être **complet**, la sortie JS est tronquée à ~950 car). Utilise `__cleanBody` pour retirer les marqueurs FB finaux (« Voir plus »/« Voir moins »). Dans un `javascript_tool`, construis la fenêtre et déclenche un download :
```javascript
(function(){
  const trunc = window.__truncated();
  if (trunc.length) return 'STOP — '+trunc.length+' post(s) encore tronqué(s), NE PAS exporter : '+JSON.stringify(trunc);
  const win = Object.values(window.__store).filter(p=>p.iso && p.iso>='<borne YYYY-MM-DD>');
  const data = win.map(p=>({author:p.author, authorUrl:p.authorUrl, iso:p.iso, pid:p.pid, permalink:p.permalink,
    body:window.__cleanBody(p.body),                                  // corps INTÉGRAL, marqueurs FB retirés
    comments:Object.values(p.comments).map(c=>({name:c.name,profileUrl:c.profileUrl,time:c.time,text:(c.text||'').replace(/\s+/g,' ').trim()}))}));
  const blob=new Blob([JSON.stringify(data)],{type:'application/json'});
  const url=URL.createObjectURL(blob); const a=document.createElement('a');
  a.href=url; a.download='veto_scrape.json'; document.body.appendChild(a); a.click();
  setTimeout(()=>{URL.revokeObjectURL(url);a.remove();},2000);
  return 'download '+data.length+' posts';
})();
```
Puis copie/lis le fichier localement : `cp ~/Downloads/veto_scrape.json <scratchpad>/` puis `Read`. Tu disposes alors du **texte intégral** de chaque post + commentaires, sans troncature ni transcription base64.

Filtre la fenêtre sur `iso` (ou `ageH`) et classe depuis ce fichier local.

#### Exclure (ne PAS compter comme offre) :
- **Auteur blacklisté** : Read `references/auteurs_exclus.json` (bundlé) en début de classification. Si `p.author` (ou la signature/coordonnées en fin de post) matche une entrée de la liste (insensible à la casse, substring) → exclu d'office, **sans lire le contenu pour juger de la pertinence**.
- Pas une annonce d'emploi vétérinaire (ni « cherche poste », ni « cherche vétérinaire »).
- Question générale, partage d'article, sondage, RH sans annonce, formation, appel à thèse/sondage, **offre ASV** sans lien vétérinaire.
- Si exclu → ignorer aussi ses commentaires.
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
- **Date du post** : `iso` (YYYY-MM-DD).
- **Lien du post** : utilise **`p.permalink`** tel quel (reconstruit à la capture depuis l'id du post : `…/groups/318289868699508/posts/{pid}/`) — c'est un vrai lien qui ouvre le post. **N'utilise une URL de recherche `…/search?q=<mots-clés url-encodés>` qu'en dernier recours**, si `p.permalink` ET `p.pid` sont vides. (Validé en live : le permalink se reconstruit depuis l'`innerHTML` du conteneur, y compris sur les posts à timestamp obfusqué où le href de l'ancre est vide.)
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
- Champs : Prénom/Nom du commentateur ; **Profil Facebook** = `c.profileUrl` (celui du **commentateur**, jamais celui du post parent ; vide si absent) ; Date = date du commentaire (sinon du post) ; Lien = même que le parent ; Zone (du commentaire, sinon du parent) ; Contenu (texte, ou « Candidature/Proposition en MP ») ; **Type de post inversé** vs parent ; Pratiques/Spécialités déduites (sinon du parent) ; **Type d'entrée** = `Commentaire` ; **Post source** = `{Auteur du post} - {résumé court}` ; Expérience ; Nom de la clinique si recruteur.
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

**Couverture par défaut (sûre)** : `__merge()` n'attrape que les commentaires affichés (« plus pertinents ») au fil du scroll. **NE PAS cliquer « Voir plus de commentaires »** ni le compteur de commentaires : ça navigue vers le permalink et vide le window.

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

Idempotent : re-scraper un post déjà fusionné ne change rien (garde par section `[date] lien`). `--dry` affiche le plan (CRÉER / MAJ). Push par lots de 10.

### 6. Résumé final

- Fenêtre couverte (avec heures).
- Posts scrappés / retenus / exclus (avec raisons).
- Commentaires pertinents (candidats / cliniques).
- Doublons ignorés (par le dédup).
- **Nouveaux enregistrements réellement créés.**
- Mentionne si la couverture commentaires est partielle (défaut) ou exhaustive.
