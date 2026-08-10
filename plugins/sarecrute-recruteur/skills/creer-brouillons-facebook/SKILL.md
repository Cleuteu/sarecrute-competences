---
name: creer-brouillons-facebook
description: >-
  Prépare des brouillons de publication Facebook (texte + image, sans publier) à partir des
  publications prévues aujourd'hui dans l'Airtable de recrutement vétérinaire (base prod
  "Recrutement vétérinaire"). Se déclenche quand l'utilisateur demande de "préparer les
  brouillons Facebook", "faire les publications du jour", "poster les annonces véto",
  "préparer les publications Facebook", "brouillons Facebook du jour" ou formulation
  équivalente. Ouvre un onglet Chrome par publication, colle le texte, joint l'image du
  Drive, et laisse l'utilisateur cliquer sur Publier.
---

# Créer les brouillons Facebook du jour

Objectif : pour chaque publication vétérinaire **prévue aujourd'hui**, **non encore publiée**,
et destinée à un **groupe Facebook dont l'URL est renseignée**, préparer un brouillon dans un
onglet Chrome (texte de l'annonce + image du Drive), **sans jamais publier**. L'utilisateur
relira et cliquera lui-même sur « Publier ».

**Groupes uniquement.** Les canaux qui sont des murs de profil (`/me`, `/veto.annonce`) sont
écartés : leur composeur se comporte différemment et n'est pas encore fiabilisé. Ils sont
signalés au recruteur pour reprise manuelle, jamais tentés (voir étape 2).

La compétence est **multi-recruteur** : elle prépare les brouillons du recruteur qui la lance, sur
son ordinateur et avec son propre compte Facebook.

Prérequis, propres à chaque utilisateur :

- connecteurs **Airtable** et **Google Drive** connectés sur son compte Claude ;
- **Claude in Chrome** actif, Chrome ouvert et connecté à **son** compte Facebook ;
- être membre des groupes Facebook visés (sinon ces canaux seront signalés, voir étape 4) ;
- pour les images : soit une session disposant de **dossiers partagés** sous `/mnt/user-data`
  (l'upload direct fonctionne, rien à régler), soit le script de repli livré dans `scripts/`
  (`attach_image.ps1` sous Windows, `attach_image.sh` sous macOS) — et, sous macOS uniquement,
  l'app Claude cochée dans Réglages Système > Confidentialité et sécurité > Accessibilité.
  Sans l'un ou l'autre, les brouillons partent en texte seul.

Le **texte**, lui, ne dépend d'aucun de ces prérequis : il passe par un événement `paste`
synthétique (étape 4), qui n'utilise ni le presse-papiers système ni le focus fenêtre.

Fonctionne sous macOS, Linux et Windows.

## Ordre de grandeur

Mesuré en production sur un run de 12 brouillons : **~0,6 appel d'outil par brouillon**, zéro
capture d'écran, ~30 s par lot de 3. La version précédente de cette compétence coûtait
**21 à 37 appels et 5 à 10 min par brouillon**. Si vous dépassez 2 appels par brouillon, c'est
que vous avez quitté la procédure de l'étape 4 — relisez-la plutôt que d'improviser un rattrapage.

## Constantes Airtable (base prod)

- Base « Recrutement vétérinaire » : `appP0W2ISytaNyAhG`
- Table « Publications » : `tblzKMXlCBH21hbJy`
  - Date de publication : `fldgV9Lx0qoPiG5Ry`
  - Publié ? (case à cocher) : `fldOrR0E0zGE3nq6F`
  - Responsable de l'offre : `fld0PBN7RvLtXb2Is` (renvoie name + email du responsable)
  - Texte de publication : `fldSxzwwTK3r1vTvC` ⚠️ lookup **dépouillé du formatage** — ne pas
    l'utiliser pour le texte de l'annonce (voir l'encadré plus bas)
  - url image publication : `fldZBl35fPmU2hwlq` (URL Google Drive de l'image)
  - Canal de diffusion (lien) : `fldqWJMsjBtXNyoXJ`
  - Canal de diffusion (select) : `fldV6UXLBrPZbMOtp`
  - Offre d'emploi : `fldhs2J4wBl1n158S`
  - Campagne (lien) : `fld5QZIprrcfxj2Wa`
- Table « Canaux de diffusion » : `tbluH5M2sogAN85dl`
  - Name : `fld7CI02D2KVamZ8L`
  - Url : `fldMTvyWFYYVqz6zG` (une URL renseignée = canal Facebook à traiter)
- Table « Campagnes » : `tblxR2zyXPE1v6AjO`
  - Offre d'emploi (lien) : `fld102PkKCm0GDU4q`
- Table « Offres d'emploi » : `tblVZva5yHSCnucsK`
  - **Texte de publication (richText) : `fldideBaQV8ILp2zJ`** ← la seule source du texte

Les champs `Texte de publication`, `url image publication`, `Responsable de l'offre`,
`Offre d'emploi` de la table Publications sont des lookups : lire la valeur dans
`cellValuesByFieldId[<fld>].valuesByLinkedRecordId[<recId>][0]`.

> **Ne jamais lire le texte de l'annonce dans le lookup `fldSxzwwTK3r1vTvC`.**
> Le champ d'origine est du **richText** et contient du Markdown (`**gras**`, `## titre`,
> puces `- `, sous-puces indentées). **Le lookup renvoie ce texte dépouillé de tout son
> formatage** — c'est la même chaîne, moins les marqueurs, donc rien ne signale la perte.
> Constaté en production : des semaines de publications sont parties sans le gras voulu par le
> recruteur, sans que personne ne voie d'erreur.
> Le texte se lit **uniquement** sur `tblVZva5yHSCnucsK.fldideBaQV8ILp2zJ`, atteint via
> Publications → Campagne → Offre (voir étape 2, point 4).
>
> Attention aux clés de `valuesByLinkedRecordId` du lookup : ce sont des IDs de **Campagnes**,
> pas d'Offres. Les passer à la table Offres renvoie `records: []` sans erreur.

## Étape 1 — Identifier le recruteur qui lance la compétence

Chaque recruteur ne prépare **que ses propres** publications. L'identité est mémorisée sur son
poste, pour ne poser la question qu'une seule fois.

1. Lire le fichier de config `$HOME/.sarecrute/recruteur.json`
   (sous Windows : `%USERPROFILE%\.sarecrute\recruteur.json` — `$HOME` y renvoie déjà).
   Format :
   ```json
   { "responsable": "Prénom Nom", "email": "prenom@exemple.fr",
     "navigateurDeviceId": "acfe93e7-2ce7-45e6-8e1b-1a4889876eaa" }
   ```
   S'il existe et que `responsable` est renseigné : l'utiliser **sans poser de question**, et
   indiquer en une ligne au début du compte rendu au nom de qui on travaille.

   `navigateurDeviceId` est facultatif et sert à l'étape 4 (choix du navigateur). Il est écrit
   au premier run qui a dû poser la question ; son absence n'empêche rien.

2. S'il n'existe pas, construire la liste des recruteurs possibles depuis Airtable :
   `list_records_for_table` sur `tblzKMXlCBH21hbJy`, **`fieldIds` limité au seul**
   `fld0PBN7RvLtXb2Is` (Responsable de l'offre), filtré sur les 30 derniers jours
   (`{"operator":"isWithin","operands":["fldgV9Lx0qoPiG5Ry",{"mode":"pastNumberOfDays","numberOfDays":30,"timeZone":"Europe/Paris"}]}`),
   **et `pageSize: 100`**. Puis dédupliquer les couples nom + email obtenus.

   Ces trois bornes ne sont pas décoratives : sur 90 jours et sans `pageSize`, la table renvoie
   ~455 enregistrements soit près de 200 Ko, **au-delà de la limite de contexte** — l'appel échoue
   et la compétence s'arrête avant d'avoir rien fait. C'est le cas de tout **nouveau recruteur**,
   puisque c'est justement quand `recruteur.json` est absent qu'on passe ici. Ne jamais élargir la
   fenêtre ni demander de champ supplémentaire à cet appel-là.

   Si malgré tout la réponse dépasse la limite et se retrouve sauvegardée dans un fichier, ne pas
   la relire avec l'outil de lecture : extraire les responsables au shell, par exemple
   ```bash
   jq -r '[.records[].cellValuesByFieldId["fld0PBN7RvLtXb2Is"].valuesByLinkedRecordId // {}
           | .[] | .[0] | select(.!=null) | (.name+" <"+.email+">")] | unique[]' "<chemin_json>"
   ```

3. Poser la question avec AskUserQuestion. **Pré-sélectionner** l'entrée dont l'email correspond
   à celui du compte Claude de l'utilisateur, s'il y a une correspondance. Laisser la possibilité
   de saisir un nom absent de la liste.

   Grouper cette question avec celle du navigateur (étape 4) et celle du feu vert (étape 2.5) :
   AskUserQuestion accepte jusqu'à 4 questions par appel, et chaque appel séparé coûte une
   attente humaine complète.

4. Écrire le choix dans `$HOME/.sarecrute/recruteur.json` (créer le dossier au besoin) et le dire
   à l'utilisateur, en précisant qu'il peut modifier ou supprimer ce fichier pour changer
   d'identité. Ce fichier est **local à la machine** : ne jamais le versionner ni le partager.

Ne traiter les publications de **tous** les responsables que si l'utilisateur le demande
explicitement ; ce n'est jamais le comportement par défaut.

## Étape 2 — Récupérer les publications du jour

1. Lister les canaux avec URL : `list_records_for_table` sur `tbluH5M2sogAN85dl`
   (champs Name + Url). Construire une correspondance `nom du canal → URL`. Ne garder que les
   canaux dont l'Url est non vide (ce sont les destinations Facebook).
2. Lister les publications : `list_records_for_table` sur `tblzKMXlCBH21hbJy` avec le filtre :
   - Date de publication = aujourd'hui : `{"operator":"=","operands":["fldgV9Lx0qoPiG5Ry",{"mode":"today","timeZone":"Europe/Paris"}]}`
   - ET Publié ? = false : `{"operator":"=","operands":["fldOrR0E0zGE3nq6F",false]}`

   Champs à demander : **uniquement** Responsable de l'offre (`fld0PBN7RvLtXb2Is`) et Canal de
   diffusion (select) (`fldV6UXLBrPZbMOtp`), avec `pageSize: 100`. C'est le strict nécessaire au
   filtrage du point 3, et ça tient dans le contexte même sur une journée chargée.

   Ne demander ici **ni** `Offre d'emploi`, **ni** `url image publication`, **ni** `Canal de
   diffusion (lien)`, **ni** `Texte de publication` : ce sont des lookups au format verbeux
   `valuesByLinkedRecordId`. Mesuré en production, les demander tous porte la réponse à ~900
   caractères par publication — soit ~55 Ko pour 61 publications, **au-delà de la limite de
   contexte**. L'appel échoue alors d'un bloc, avant qu'on ait rien fait.

   Ces deux appels (canaux + publications) sont indépendants : les lancer dans le même tour.
3. Filtrer côté client :
   - garder uniquement les publications du **responsable identifié à l'étape 1** (sauf demande
     explicite de traiter tout le monde) ; comparer sur l'email quand il est disponible, le nom
     seul étant plus fragile (homonymes, orthographe) ;
   - garder uniquement celles dont le **canal a une URL** (jointure via le nom du canal) ;
   - garder uniquement les canaux qui sont des **groupes**, c'est-à-dire dont l'URL contient
     `/groups/`. Les autres (murs de profil) sont **hors périmètre** — voir ci-dessous.

   **Périmètre : groupes uniquement.** Sur les 14 canaux ayant une URL, 12 sont des groupes et
   2 sont des murs de profil : « Facebook perso » (`/me`, le mur du recruteur) et « Annonces
   véto » (`/veto.annonce`, le journal d'un tiers — c'est un profil personnel avec ~4 900
   ami(e)s, pas une Page).

   Le composeur d'un mur de profil ne se comporte pas comme celui d'un groupe : le dialogue
   modal « Créer une publication » se replie de lui-même en composeur inline, l'image ne
   s'attache pas, et parmi la dizaine de champs « Photo/Vidéo » de la page le bon est ambigu —
   avec le risque de joindre l'image au post d'un autre membre.

   Tant que ce flux n'est pas maîtrisé, **ne pas tenter ces canaux**. Les lister explicitement
   dans le compte rendu final comme « hors périmètre, à faire à la main » : ils ne doivent pas
   disparaître silencieusement de la sélection.

   Si aucune publication ne reste après filtrage, le dire clairement (« rien à publier
   aujourd'hui pour <nom> ») et s'arrêter là — ne pas élargir le périmètre de sa propre
   initiative.
4. Récupérer le contenu, sur les **seules publications retenues**, en trois appels enchaînés.
   Pas de filtre ni de `pageSize` : les `recordIds` suffisent.

   1. `list_records_for_table` sur `tblzKMXlCBH21hbJy`, `recordIds` = les IDs retenus au point 3,
      `fieldIds` = Offre d'emploi (`fldhs2J4wBl1n158S`), url image publication
      (`fldZBl35fPmU2hwlq`), **Campagne (`fld5QZIprrcfxj2Wa`)**.
      → donne le nom de l'offre, l'URL de l'image, et l'ID de la campagne.
   2. `list_records_for_table` sur `tblxR2zyXPE1v6AjO` (Campagnes), `recordIds` = les IDs de
      campagne **dédupliqués**, `fieldIds` = `fld102PkKCm0GDU4q`.
      → donne l'ID de l'offre d'emploi.
   3. `list_records_for_table` sur `tblVZva5yHSCnucsK` (Offres d'emploi), `recordIds` = les IDs
      d'offre **dédupliqués**, `fieldIds` = `fldideBaQV8ILp2zJ`.
      → donne le **Markdown source**, avec son gras et sa structure.

   Deux appels de plus qu'une lecture par lookup, et c'est le prix du formatage : c'est le seul
   chemin qui restitue le `**gras**` et l'indentation des sous-puces. La déduplication maintient
   le coût bas : une douzaine de publications ne fait en général que 7 à 9 offres distinctes,
   parce que le texte est partagé par tous les canaux d'une même offre.

   **Conserver la chaîne Markdown telle quelle**, associée à son ID d'offre. Ne pas la
   reformater, ne pas la recopier à la main, ne pas la « nettoyer ». Elle sera passée verbatim au
   convertisseur de l'étape 4, qui est le seul endroit où elle a le droit d'être transformée.

   > **Ne jamais retranscrire une annonce.** Constaté en production : un agent qui recompose les
   > textes dans son propre message perd les puces, aplatit les niveaux d'indentation, et
   > remplace les apostrophes courbes `’` par des droites `'`. Rien de tout cela n'apparaît dans
   > une relecture rapide, et le recruteur découvre les dégâts après publication.
5. Présenter à l'utilisateur la liste des brouillons à préparer (offre × canal), regroupée par
   offre, avec l'image associée, et demander son feu vert. **Signaler dès ici** les publications
   sans image et les canaux hors périmètre : l'utilisateur doit pouvoir arbitrer avant qu'on
   ouvre le moindre onglet.

## Étape 3 — Télécharger les images (une seule fois par image)

**Quand.** Démarrer les téléchargements **dès que la liste du point 4 de l'étape 2 est connue**,
c'est-à-dire *avant* de présenter la liste et *sans attendre* le feu vert. Le téléchargement Drive
et le décodage ne touchent pas au navigateur : ils ne rentrent en conflit avec rien, et le temps
de lecture de l'utilisateur est autant de pris.

Le texte et l'image d'une offre étant partagés par tous ses canaux, une douzaine de publications
ne représente en général que 7 à 9 images distinctes : **dédupliquer par ID de fichier Drive**
avant de télécharger quoi que ce soit.

**Lancer tous les `download_file_content` dans un seul tour**, pas en série : ils sont
indépendants. Mesuré : 8 images en un tour, contre une à deux minutes perdues en série.

Pour chaque URL Drive distincte trouvée dans `url image publication` :

1. Extraire l'ID du fichier depuis l'URL (`.../file/d/<ID>/...`).
2. Appeler `download_file_content(fileId=<ID>)`. Le résultat (base64) dépasse la limite de
   contexte et est **automatiquement sauvegardé dans un fichier `.txt`** : récupérer le chemin
   indiqué dans le message d'erreur.
   - **Ne jamais lire ce `.txt`** avec l'outil de lecture de fichiers, ni en afficher le contenu :
     un visuel fait 2 à 3 Mo, son base64 saturerait le contexte pour rien.
   - Si l'appel échoue en **permission refusée** ou fichier introuvable : le compte Google de
     l'utilisateur n'a pas accès au Drive partagé contenant le dossier « Publications ». Ne pas
     réessayer : signaler qu'il doit demander l'accès en **Lecteur**, et continuer en texte seul.
3. Décoder en image **sans charger le base64 en mémoire**, et **sans coder aucun chemin en dur**.

   Le dossier de sortie doit être un dossier que `file_upload` accepte : uniquement `uploads` et
   `outputs` de la session (ou un dossier ouvert par l'utilisateur). `working` est **refusé** bien
   qu'il soit lisible par l'agent, et un dossier temporaire système aussi. En Cowork, seul
   `working` existe parfois : **on crée le dossier, on ne se demande pas s'il existe.**

   Le script ci-dessous mappe les fichiers par l'`id` Drive contenu dans chaque JSON, et non par
   l'ordre des réponses : quand 8 téléchargements partent dans le même tour, les horodatages des
   `.txt` ne sont pas monotones et un mappage positionnel intervertit les images.

   ```bash
   D="<dossier_des_txt>"; OUT=""
   if [ -d /mnt/user-data ]; then
     for c in /mnt/user-data/outputs /mnt/user-data/uploads; do
       [ -d "$c" ] && [ -w "$c" ] && { OUT="$c/pub_images"; break; }
     done
     OUT="${OUT:-/mnt/user-data/outputs/pub_images}"   # aucun n'existe : on crée outputs
   else
     # Pas de dossier de session partagé. Le shell tourne sur la machine du recruteur — c'est le
     # cas d'un poste macOS ou Windows, MAIS AUSSI de certaines sessions Cowork dont le shell est
     # l'hôte. Ne pas se fier au nom « Cowork » : seul ce test compte.
     # Ici la méthode d'attache sera TOUJOURS la B. Nom neutre, surtout PAS `outputs` ni
     # `uploads` : ces noms ont déjà fait croire à un agent que la méthode A était disponible.
     OUT="sarecrute_pub_images"
   fi
   mkdir -p "$OUT"

   python3 - "$D" "$OUT" <<'PY'
   import base64, json, sys, glob, os
   d, out = sys.argv[1], sys.argv[2]
   names = { "<idDrive1>": "<nom1>", "<idDrive2>": "<nom2>" }   # à générer depuis Airtable
   for f in glob.glob(os.path.join(d, "mcp-Google_Drive-download_file_content-*.txt")):
       try: j = json.load(open(f))
       except Exception: continue
       if j.get("id") in names:
           dst = os.path.join(out, names[j["id"]] + ".png")
           open(dst, "wb").write(base64.b64decode(j["content"]))
           print("OK", names[j["id"]], os.path.getsize(dst), dst)
   PY
   ```

   Sous Windows sans shell POSIX, l'équivalent PowerShell (`[Convert]::FromBase64String` sur
   `(Get-Content -Raw ... | ConvertFrom-Json).content`), en écrivant dans `%TEMP%` — ce qui
   convient à la méthode B et serait refusé par `file_upload`, mais ce cas ne se présente pas :
   un poste Windows sans Git Bash n'est pas une session à dossiers partagés.
4. Mémoriser le chemin **absolu tel que le shell le voit**. C'est ce chemin-là qu'attend
   `file_upload` : l'outil transfère lui-même les octets, il ne demande pas au poste d'ouvrir le
   fichier. **Ne pas le convertir en chemin hôte** (`/Users/...`, `C:\...`) : il serait refusé.

   Vérifié en production : `/mnt/user-data/outputs/pub_images/<nom>.png` est accepté du premier
   coup. Sont refusés `/mnt/user-data/working/...` et `/home/claude/...`.

Si une image est introuvable (URL vide, ID invalide, échec du décodage) : ne pas bloquer, noter la
publication comme « sans image » et continuer.

## Étape 4 — Créer les brouillons

### Ce qui a été mesuré, et qu'il ne faut pas redécouvrir

Sept faits établis en run réel. Les ignorer coûte 20 à 30 appels par brouillon.

1. **Le composeur n'est jamais dans le viewport au chargement.** La page d'un groupe s'ouvre sur
   la bannière ; le composeur est sous la ligne de flottaison. Toute procédure du type
   « une capture, lis les coordonnées, clique » enchaîne donc capture → scroll → recapture →
   clic, et les clics à l'aveugle atterrissent sur l'icône **Messenger** en haut à droite.
2. **Un `.click()` DOM ouvre le composeur de façon déterministe.** C'est le clic par `ref` de
   l'outil `computer` qui ne fonctionne pas : il donne le focus mais n'active pas. Le clic par
   coordonnées marche aussi, mais exige la capture dont on veut se passer.
3. **`computer type` déclenche un timeout CDP de 30 s** (« Input.dispatchKeyEvent timed out »)
   dès que le composeur contient du texte, et le découpage par paragraphe n'y change rien. La
   frappe **aboutit** malgré le timeout — mais celui-ci **interrompt le `browser_batch`**, ce qui
   est le vrai coût : toutes les actions suivantes du lot sont perdues.
4. **Un événement `paste` synthétique fonctionne** avec l'éditeur Lexical de Facebook : texte
   complet, ordre correct, un seul appel, aucun timeout. C'est la méthode de saisie.
5. **`document.execCommand('insertText')` est interdit** : il désordonne les blocs Lexical
   (constaté : texte de 566 caractères ressorti à 1000, paragraphes intervertis).
6. **`form_input` est inutilisable** sur le composeur : « Element type "DIV" is not a supported
   form input ». Ne pas l'essayer.
7. **Le champ fichier n'est pas le bouton « Photo/Vidéo ».** Ce sont deux éléments distincts. Un
   `ref` de bouton passé à `file_upload` échoue, et **cliquer** le bouton ouvre la boîte de
   dialogue native du système — que CDP ne voit pas, ne peut pas fermer, et que l'utilisateur
   doit annuler à la main. Ne cliquer ni l'un ni l'autre, jamais.

### Choix du navigateur

Appeler `list_connected_browsers` **avant** d'ouvrir le premier onglet. S'il y en a plus d'un,
demander lequel via AskUserQuestion : une option par navigateur, plus l'option « ouvrir une
confirmation dans chaque Chrome ». Ne jamais en choisir un soi-même.

- **Les noms « Browser N » ne sont pas stables** : ils se renumérotent quand un navigateur se
  déconnecte, et le nom donné en cliquant « Connect » n'est pas repris. Les `deviceId` sont
  stables : c'est l'id qu'on mémorise dans `navigateurDeviceId`, et c'est sur l'id qu'on vérifie.
  Si `select_browser` renvoie un nom différent de celui affiché dans la liste, ce n'est pas une
  erreur — revérifier avec `list_connected_browsers` que l'id retenu est bien présent.
- **`switch_browser` ne diffuse qu'aux navigateurs *autres* que celui déjà sélectionné.** S'il
  n'y en a pas, il répond « No other browsers available to switch to » : ce n'est pas une panne,
  il faut simplement repasser par `select_browser` avec un id de la liste.
- Aux runs suivants, si l'id mémorisé figure toujours dans `list_connected_browsers`, le proposer
  **en première option et pré-sélectionné**. La question reste obligatoire dès qu'il y a plusieurs
  navigateurs ; la mémorisation fait gagner la recherche du bon, pas la question.
- Le profil Chrome ne dit rien du compte Facebook actif : **seul le nom affiché dans le composeur
  fait foi**, et il est vérifié à chaque brouillon (voir le garde-fou ci-dessous).

### Phase 1 — ouvrir et charger tous les onglets

1. `tabs_context_mcp` avec `createIfEmpty: true` : c'est cet appel qui crée le groupe d'onglets et
   renvoie son premier `tabId`. Sans lui, `tabs_create_mcp` échoue (« No tab group exists »). Le
   premier brouillon utilise ce `tabId`.
2. Créer les N−1 onglets restants avec `tabs_create_mcp`. **Ne pas mettre `tabs_create_mcp` dans
   un `browser_batch`** : il y échoue avec « No tab available ». Les appeler en parallèle dans un
   même tour, ce qui revient au même en temps.
3. **Lancer les N navigations dans un seul `browser_batch`**, avec **une seule** attente de ~8 s à
   la fin — et non une attente par onglet. Les pages chargent en parallèle côté navigateur : on
   paie un temps de chargement au lieu de N. Vérifié sur 12 onglets.
4. **Aucune capture d'écran**, ni ici ni ailleurs.

### Phase 2 — texte et image, par lots de 3 onglets

Le traitement d'un brouillon tient en **deux actions**, et `browser_batch` accepte un `tabId`
différent par action : on traite donc **3 onglets par appel**. Pas de sous-agents — ils ne
servaient qu'à confiner les captures, qui n'existent plus.

**Appel A — pour 3 onglets : 3 × `javascript_tool` (ouvrir + vérifier + coller), puis 3 × `find`.**

Le script, identique pour chaque onglet à `MD` près. `MD` est **la chaîne Markdown brute
d'Airtable**, collée sans retouche ; les fonctions `mdToHtml` / `mdToText` en font le reste.

```js
const MD = "<Markdown brut d'Airtable, verbatim, sauts de ligne en \n>";

// --- Markdown Airtable -> HTML pour le composeur Facebook ---
const esc    = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const spaces = s => s.replace(/ {2,}/g, m => '&nbsp;'.repeat(m.length));  // HTML écrase les espaces multiples
const inline = s => spaces(esc(s)).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
const mdToHtml = md => md.replace(/\r/g,'').split(/\n{2,}/)
  .map(bl => bl.split('\n')
      .map(l => l.replace(/^#{1,6}\s*/,''))                     // titres : marqueur retiré
      .map(l => { const m = l.match(/^( +)/);                   // indentation des sous-puces
                  return m ? '&nbsp;'.repeat(m[1].length) + inline(l.slice(m[1].length))
                           : inline(l); })
      .join('<br>'))                                            // <br> = saut de ligne serré
  .filter(b => b.length)
  .map(b => '<p>' + b + '</p>').join('');                       // <p> = saut de paragraphe
const mdToText = md => md.replace(/\r/g,'')
  .replace(/^#{1,6}\s*/gm,'').replace(/\*\*(.+?)\*\*/g,'$1');   // repli texte brut

const f = () => [...document.querySelectorAll('div[role="dialog"]')]
                  .find(d => d.querySelector('div[contenteditable="true"]'));
let dlg = f();
if (!dlg) {
  const rx = /Exprimez-vous|Écrivez quelque chose|Créez une publication/i;
  const t = [...document.querySelectorAll('div[role="button"]')]
              .find(e => rx.test(e.textContent || '') && (e.textContent || '').length < 80);
  if (!t) throw new Error('COMPOSEUR_INTROUVABLE');
  t.scrollIntoView({block: 'center'});
  t.click();
  await new Promise(r => setTimeout(r, 2500));
  dlg = f();
}
if (!dlg) throw new Error('DIALOGUE_NON_OUVERT');
if (!/<Prénom du recruteur>/i.test(dlg.innerText.slice(0, 200)))
  throw new Error('MAUVAIS_COMPTE :: ' + dlg.innerText.slice(0, 120));
const box = dlg.querySelector('div[contenteditable="true"]');
if (box.innerText.trim()) throw new Error('COMPOSEUR_NON_VIDE');
box.focus();
const dt = new DataTransfer();
dt.setData('text/plain', mdToText(MD));   // repli
dt.setData('text/html',  mdToHtml(MD));   // c'est celui-ci que Lexical utilise
box.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
await new Promise(x => setTimeout(x, 1500));
const out = box.innerText || '';
({onglet: '<nom du groupe>', attendu: mdToText(MD).trim().length, obtenu: out.length,
  gras: box.querySelectorAll('b,strong').length, fin: out.slice(-40)})
```

**Fournir les deux formats.** Lexical préfère `text/html` et ignore `text/plain` quand les deux
sont présents ; `text/plain` ne sert que de filet si Facebook change de comportement. Vérifié en
production sur une annonce réelle : **11 passages en gras conservés** (nœuds `<strong>`,
`font-weight: 600`), esperluette de « Conditions & évolution » correctement échappée, apostrophes
courbes `’` intactes, sous-puces `    - Associé junior` indentées, et `innerText` **identique à la
structure de la source** — plus aucune inflation des sauts de ligne.

`gras` dans le retour doit être **> 0** dès que l'annonce contient du `**` ; à 0, c'est que
`text/html` n'a pas été pris et il faut le signaler plutôt que de publier du texte plat.

Ce script porte lui-même les trois garde-fous, et c'est ce qui les rend fiables :

- **`MAUVAIS_COMPTE`** — le nom affiché dans le composeur doit correspondre au recruteur de
  l'étape 1. Le script **lève une exception**, ce qui arrête le `browser_batch` : aucune frappe ne
  peut partir sous le mauvais compte. Plus sûr qu'une vérification par lecture, qu'on peut oublier
  d'interpréter.
- **`COMPOSEUR_NON_VIDE`** — protège contre le doublon si un brouillon est rejoué.
- Le `dialog` est sélectionné par la **présence d'un `contenteditable`**, pas par son `aria-label`.
  Le composeur est en réalité imbriqué dans deux `div[role="dialog"]` dont un seul porte
  l'étiquette, et c'est l'autre qui contient le champ fichier. Sélectionner par `aria-label` vise
  le mauvais nœud.
- Ce chemin ne peut **pas** taper dans une zone de commentaire : on part du dialogue, jamais d'un
  `find` de textbox à l'échelle de la page.

Puis, dans le **même appel**, un `find` par onglet :
`find(query: "input type=file du dialogue Créer une publication")`. Il renvoie 2 ou 3 candidats et
**désigne explicitement celui du dialogue** — les autres appartiennent aux zones de commentaire
des posts voisins et joindraient l'image au post d'un autre membre. Retenir celui décrit comme
étant dans le dialogue (« Ajouter à votre publication », « Photo/Vidéo »). Ne pas utiliser
`read_page` pour ça : il renvoie le bouton, pas l'`input`.

**Appel B — 3 × `file_upload`, une attente, puis 3 × vérification.**

`file_upload` doit **impérativement** être appelé à l'intérieur d'un `browser_batch` : appelé
seul, l'argument `paths` se perd et l'outil répond « expected array, received undefined ».

```js
const d = [...document.querySelectorAll('div[role="dialog"]')]
            .find(x => x.querySelector('div[contenteditable="true"]'));
const b = d.querySelector('div[contenteditable="true"]');
const t = b.innerText || '';
const L = t.split('\n').filter(s => s.trim());
({o: '<nom du groupe>', len: t.length, l1: L[0].slice(0, 32),
  dup: t.split(L[0]).length - 1,
  img: d.querySelectorAll('img[src^="blob:"],img[src^="data:"]').length})
```

`dup` doit valoir **1** (sinon le texte a été saisi deux fois) et `img` **1** (0 pour les
publications sans image). Prévoir ~5 s d'attente entre l'upload et la vérification.

Les appels A et B de lots différents se combinent : un même `browser_batch` peut porter les
uploads du lot précédent et les collages du lot suivant.

**En cas de refus de `file_upload` pour une raison de partage de session** (« requires a non-empty
`paths` array of files the user has shared with this session », ou toute variante parlant de
fichiers partagés) : basculer **immédiatement** en méthode B, dès le premier refus, sans réessayer
et sans chercher d'autre chemin. La bascule vaut pour **tout le reste du run**.

**Ne jamais demander au recruteur de connecter ou de partager un dossier.** Constaté en
production : un agent l'a fait, le recruteur a connecté un dossier, `file_upload` a refusé de plus
belle, et le run est resté bloqué en texte seul — alors que le script de la méthode B attendait
dans `scripts/`. Un dossier connecté n'est pas un dossier de session : cette porte ne s'ouvre pas.

### Méthode B — presse-papiers (repli hors dossiers partagés)

Ne concerne que **l'image** : le texte passe par l'événement `paste` de la phase 2, qui n'a besoin
de rien. Cette méthode passe le navigateur au premier plan et envoie une vraie frappe : elle
monopolise la machine quelques secondes par image. **Prévenir l'utilisateur en début de run** qu'il
ne doit pas taper pendant ces quelques secondes — et ne pas l'avertir du tout en méthode A, où il
n'y a rien à subir. En méthode B, **traiter les onglets un par un** : le presse-papiers est une
ressource unique et deux collages simultanés enverraient l'image dans le mauvais onglet, sans
erreur visible.

Le curseur doit être dans la zone de texte : appeler le script juste après le collage du texte.

- Windows :
  ```
  powershell -sta -ExecutionPolicy Bypass -File <dossier_skill>\scripts\attach_image.ps1 -TitleFragment "<titre_onglet>" -ImagePath "<chemin_image>"
  ```
  `<titre_onglet>` = un fragment du nom du groupe. Sous Windows on ne peut pas sélectionner un
  onglet depuis le shell : le script vise la fenêtre Chrome dont l'onglet **actif** porte ce titre.
- macOS :
  ```
  <dossier_skill>/scripts/attach_image.sh "<fragment_url_onglet>" "<chemin_image>"
  ```
  `<fragment_url_onglet>` = l'identifiant numérique du groupe. Sortie 2 « Accessibilité refusée » :
  l'app Claude n'est pas cochée dans Réglages Système > Confidentialité et sécurité >
  Accessibilité. Le dire à l'utilisateur et poursuivre en texte seul ; ne pas boucler.

**Ne jamais essayer de coller avec `computer` action `key` (`ctrl+v` / `cmd+v`).** C'est une frappe
synthétique : elle ne porte pas le presse-papiers, l'outil répond « Pressed 1 key » et rien n'est
collé.

### Absence d'accès à un groupe

Si le script lève `COMPOSEUR_INTROUVABLE`, c'est en général que le compte n'est pas membre du
groupe (bouton « Rejoindre le groupe » à la place du composeur). Ne pas insister : fermer
l'onglet, noter le canal comme **« accès manquant »** pour le compte rendu, et continuer. C'est le
cas le plus fréquent quand un nouveau recruteur démarre.

### Ne jamais publier

Ne pas cliquer sur « Publier ». Laisser tous les onglets ouverts pour la relecture — c'est voulu.
Ne jamais cocher « Publié ? » dans Airtable.

## Étape 5 — Compte rendu

Récapituler :

- **au nom de quel recruteur** les brouillons ont été préparés ;
- le nombre de brouillons préparés et leurs destinations, groupés par offre, avec l'image utilisée ;
- **les publications sans image trouvée** ;
- **les canaux en « accès manquant »** (groupe non rejoint), avec la consigne de demander l'accès
  avant le prochain lancement ;
- **les publications écartées parce que leur canal est un mur de profil** (`/me`,
  `/veto.annonce`), présentées comme « à faire à la main » et non comme un échec ;
- **les coquilles repérées dans le texte Airtable** — les signaler, ne **jamais** les corriger de
  sa propre initiative : c'est la copie du recruteur, et deviner une correction est une
  modification silencieuse de son annonce ;
- **si des annonces contenaient du gras**, rappeler que sa conservation après publication reste à
  confirmer (voir les notes) — l'utilisateur peut le vérifier sur son premier post ;
- rappeler que rien n'a été publié et qu'il reste à cliquer sur « Publier » dans chaque onglet.

## Notes / pièges connus

- **Interligne — résolu par `text/html`, ne pas revenir en arrière.** En collant du
  `text/plain`, Lexical fait de chaque `\n` un paragraphe : un `\n` ressort en `\n\n` et un `\n\n`
  en cinq sauts, et le texte est nettement plus aéré que dans Airtable. Avec `text/html`, `<br>`
  donne un saut serré et `<p>` un saut de paragraphe : la structure est restituée exactement.
  C'est la raison principale d'utiliser le HTML, indépendamment même du gras.
- **Ne pas retirer les tirets « - » des listes.** Une version antérieure le prescrivait, au motif
  que Facebook les transformait en puces avec un tiret en double. C'était vrai de la **frappe**,
  où Lexical applique l'autoformatage Markdown ; ça ne l'est pas du **collage**, qui ne déclenche
  pas l'autoformatage. Collés, les `- ` restent littéraux et rendent exactement la liste
  d'Airtable. Les retirer, c'est s'écarter de la source pour rien.
- **Les espaces multiples sont écrasés en HTML.** Le convertisseur les rétablit en `&nbsp;`, aussi
  bien pour l'indentation en début de ligne que pour les doubles espaces internes. Sans ça,
  « ≥ 3  d'expérience » ressort avec un seul espace.
- **Le gras après publication n'est pas vérifié.** Ce qui est établi, c'est que le composeur le
  conserve comme un vrai nœud `<strong>` (et non comme du texte avec des astérisques). Le rendu
  du post **publié** n'a pas pu être contrôlé, la compétence ne publiant jamais. À faire confirmer
  par le recruteur sur sa première publication. Si le gras devait sauter à la publication, le
  collage HTML reste malgré tout supérieur au texte brut pour les sauts de ligne.
- **Pas de gras Unicode.** La tentation est de convertir `**gras**` en caractères mathématiques
  (𝗴𝗿𝗮𝘀). À écarter : ces blocs Unicode **ne couvrent pas les lettres accentuées**, donc en
  français « 𝘃é𝘁é𝗿𝗶𝗻𝗮𝗶𝗿𝗲 » et « 𝗥𝗛Ô𝗡𝗘 » sortent en gras panaché — mesuré à ~5 % des lettres des
  passages en gras, mais présentes dans presque tous les titres. S'y ajoutent l'illisibilité pour
  les lecteurs d'écran et la recherche Facebook qui ne retrouve plus ces mots.
- Le texte et l'image d'une offre sont partagés par tous ses canaux → télécharger l'image une
  seule fois et réutiliser le fichier local pour tous les onglets de la même offre.
- Sur les 14 canaux ayant une URL, 12 sont des groupes — les seuls traités — et un recruteur ne
  peut y publier que s'il en est membre. Les 2 autres sont des murs de profil, écartés à
  l'étape 2. « Annonces véto » n'est **pas une Page** malgré son usage : c'est un profil personnel
  (~4 900 ami(e)s), et y publier revient à écrire sur le journal d'un tiers.
- **Ce qui reste à résoudre pour les murs de profil**, le jour où on voudra les réintégrer : le
  dialogue modal se replie en composeur inline, l'image ne s'attache pas, et le champ
  « Photo/Vidéo » à viser est ambigu. Rien n'a encore été trouvé qui fonctionne — ne pas écrire de
  procédure ici avant de l'avoir vérifiée sur un run réel. Deux cas sont sans doute à distinguer :
  son propre mur (`/me`), qui a déjà fonctionné par le passé, et le journal d'un tiers
  (`/veto.annonce`), qui est celui qui a échoué.
- **La boîte de dialogue native de sélection de fichier est irrécupérable.** Si elle s'ouvre (par
  un clic sur « Photo/Vidéo » ou sur un `input[type=file]`), CDP ne la voit pas, ne peut pas la
  fermer, et continue de répondre normalement — on ne s'en aperçoit donc pas. Le seul remède est
  de ne jamais l'ouvrir ; si c'est arrivé, le dire à l'utilisateur pour qu'il l'annule à la main.
- Si Chrome répond « not connected », suivre les consignes de l'outil (attendre/réessayer).
- Ne jamais publier ; ne jamais cocher « Publié ? » dans Airtable.
