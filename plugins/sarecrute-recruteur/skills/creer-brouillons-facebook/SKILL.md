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
  (l'upload direct fonctionne, rien à régler), soit
  le script de repli livré avec la compétence dans `scripts/` (`attach_image.ps1` sous Windows,
  `attach_image.sh` sous macOS) — et, sous macOS uniquement, l'app Claude cochée dans Réglages
  Système > Confidentialité et sécurité > Accessibilité. Sans l'un ou l'autre, les brouillons
  partent en texte seul.

Fonctionne sous macOS, Linux et Windows (voir étapes 3 et 4 pour les différences d'outillage).

## Constantes Airtable (base prod)

- Base « Recrutement vétérinaire » : `appP0W2ISytaNyAhG`
- Table « Publications » : `tblzKMXlCBH21hbJy`
  - Date de publication : `fldgV9Lx0qoPiG5Ry`
  - Publié ? (case à cocher) : `fldOrR0E0zGE3nq6F`
  - Responsable de l'offre : `fld0PBN7RvLtXb2Is` (renvoie name + email du responsable)
  - Texte de publication : `fldSxzwwTK3r1vTvC`
  - url image publication : `fldZBl35fPmU2hwlq` (URL Google Drive de l'image)
  - Canal de diffusion (lien) : `fldqWJMsjBtXNyoXJ`
  - Canal de diffusion (select) : `fldV6UXLBrPZbMOtp`
  - Offre d'emploi : `fldhs2J4wBl1n158S`
- Table « Canaux de diffusion » : `tbluH5M2sogAN85dl`
  - Name : `fld7CI02D2KVamZ8L`
  - Url : `fldMTvyWFYYVqz6zG` (une URL renseignée = canal Facebook à traiter)

Les champs `Texte de publication`, `url image publication`, `Responsable de l'offre`,
`Offre d'emploi` sont des lookups : lire la valeur dans
`cellValuesByFieldId[<fld>].valuesByLinkedRecordId[<recId>][0]`.

## Étape 1 — Identifier le recruteur qui lance la compétence

Chaque recruteur ne prépare **que ses propres** publications. L'identité est mémorisée sur son
poste, pour ne poser la question qu'une seule fois.

1. Lire le fichier de config `$HOME/.sarecrute/recruteur.json`
   (sous Windows : `%USERPROFILE%\.sarecrute\recruteur.json` — `$HOME` y renvoie déjà).
   Format :
   ```json
   { "responsable": "Prénom Nom", "email": "prenom@exemple.fr",
     "navigateurDeviceId": "ec5b0aec-e90b-4731-aa83-d5a0bd84d91b" }
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
   contexte**. L'appel échoue alors d'un bloc, avant qu'on ait rien fait. Un recruteur tourne
   à une vingtaine de publications par jour en régime normal, mais un retour de congés ou un
   report en cascade suffit à passer la quarantaine, et le plafond est là.
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
   ami(e)s, pas une Page, contrairement à ce que cette compétence a longtemps affirmé).

   Le composeur d'un mur de profil ne se comporte pas comme celui d'un groupe : le dialogue
   modal « Créer une publication » se replie de lui-même en composeur inline, l'image ne
   s'attache pas, et parmi la dizaine de champs « Photo/Vidéo » de la page le bon est ambigu —
   avec le risque de joindre l'image au post d'un autre membre. Constaté en run réel sur
   `/veto.annonce`, alors que les quatre groupes du même run ont réussi du premier coup.

   Tant que ce flux n'est pas maîtrisé, **ne pas tenter ces canaux**. Les lister explicitement
   dans le compte rendu final comme « hors périmètre, à faire à la main » : ils ne doivent pas
   disparaître silencieusement de la sélection, le recruteur a encore à les traiter lui-même.

   Si aucune publication ne reste après filtrage, le dire clairement (« rien à publier
   aujourd'hui pour <nom> ») et s'arrêter là — ne pas élargir le périmètre de sa propre
   initiative.
4. Second appel, sur les **seules publications retenues** : `list_records_for_table` sur la même
   table, `recordIds` = les IDs retenus au point 3, `fieldIds` = Offre d'emploi
   (`fldhs2J4wBl1n158S`), url image publication (`fldZBl35fPmU2hwlq`), Texte de publication
   (`fldSxzwwTK3r1vTvC`). Pas de filtre ni de `pageSize` ici : les `recordIds` suffisent.

   C'est là, et seulement là, qu'arrivent le texte des annonces et les URL d'images — pour la
   poignée de publications qu'on va réellement traiter, pas pour toutes celles du jour.

   Si cette réponse dépasse malgré tout la limite (beaucoup de publications retenues, textes
   longs), ne pas relire le `.txt` sauvegardé avec l'outil de lecture : l'extraire au shell comme
   à l'étape 1.
5. Présenter à l'utilisateur la liste des brouillons à préparer (offre × canal), regroupée par
   offre, avec l'image associée. Attendre son feu vert avant d'ouvrir des onglets.

## Étape 3 — Télécharger les images (une seule fois par image)

**Quand.** Démarrer les téléchargements **dès que la liste du point 4 de l'étape 2 est connue**,
c'est-à-dire *avant* de présenter la liste et *sans attendre* le feu vert. Le téléchargement Drive
et le décodage ne touchent pas au navigateur : ils ne rentrent en conflit avec rien, et le temps
de lecture de l'utilisateur est autant de pris. Les enchaîner après le feu vert, en série et avant
le premier onglet, ajoute une à deux minutes d'attente pure.

**Dans quel ordre, et jusqu'où attendre.** Télécharger dans l'**ordre de consommation** des
brouillons, et lancer le brouillon N dès que **son** image à lui est sur disque — ne pas attendre
que toutes soient prêtes. Le contrôle tient en un test d'existence (`[ -s "$DST" ]`) avant de
lancer le sous-agent du brouillon. Une publication dont l'image n'est pas encore là ne bloque pas
celles qui précèdent.

Le texte et l'image étant partagés par tous les canaux d'une même offre, une dizaine de
publications ne représente en général que 5 à 7 images distinctes : dédupliquer par ID de fichier
Drive avant de télécharger quoi que ce soit.

Pour chaque URL Drive distincte trouvée dans `url image publication` :

1. Extraire l'ID du fichier depuis l'URL (`.../file/d/<ID>/...`).
2. Appeler `download_file_content(fileId=<ID>)` du connecteur Google Drive. Le résultat
   (base64) dépasse la limite de contexte et est **automatiquement sauvegardé dans un fichier
   `.txt`** : récupérer le chemin indiqué dans le message d'erreur.
   - **Ne jamais lire ce `.txt`** avec l'outil de lecture de fichiers, ni en afficher le contenu :
     un visuel fait 2 à 3 Mo, son base64 saturerait le contexte pour rien. Il ne doit être
     traversé que par la commande shell de l'étape suivante.
   - Si l'appel échoue en **permission refusée** ou fichier introuvable, ce n'est pas un problème
     technique : le compte Google de l'utilisateur n'a pas accès au **Drive partagé** contenant le
     dossier « Publications ». Ne pas réessayer, ne pas
     chercher d'autre chemin : signaler à l'utilisateur qu'il doit demander l'accès en
     **Lecteur** à ce dossier, et continuer les publications **en texte seul**.
3. Décoder en image, sans charger le base64 en mémoire. **Ne coder aucun chemin en dur** : le
   dossier de sortie et les outils disponibles varient selon l'environnement (sandbox Cowork,
   macOS, Linux, Windows).

   Avec un shell POSIX (macOS, Linux, Git Bash sous Windows) :
   ```bash
   SRC="<chemin_txt>"; NOM="<nom>"

   # Dossier de sortie : IMPÉRATIVEMENT un dossier que file_upload accepte.
   # file_upload n'autorise QUE les dossiers `uploads` et `outputs` de la session (ou un dossier
   # ouvert par l'utilisateur). `working` est REFUSÉ, bien qu'il soit lisible par l'agent :
   # CLAUDE_ADDITIONAL_DIRECTORIES gouverne l'accès en lecture, pas ce que file_upload accepte.
   # Vérifié en run réel — ne pas le remettre dans les candidats.
   # Un dossier temporaire système ($TMPDIR, /tmp) est REFUSÉ : ne jamais l'utiliser ici.
   #
   # En Cowork, l'arbre partagé est /mnt/user-data (cf. CLAUDE_ADDITIONAL_DIRECTORIES) et le cwd
   # est /home/claude, que file_upload REFUSE. Ne pas se contenter de tester l'existence des
   # sous-dossiers : selon les sessions, seul `working` existe, et une sonde qui ne teste que
   # `uploads`/`outputs` retombe alors sur le cwd — l'upload échoue, il faut tout diagnostiquer
   # et rejouer le brouillon. Mesuré : ce seul aller-retour a doublé la durée du 1er brouillon.
   # Donc en Cowork on CRÉE le dossier, on ne se demande pas s'il existe.
   if [ -d /mnt/user-data ]; then
     for c in /mnt/user-data/outputs /mnt/user-data/uploads; do
       [ -d "$c" ] && [ -w "$c" ] && { OUT="$c/pub_images"; break; }
     done
     OUT="${OUT:-/mnt/user-data/outputs/pub_images}"   # aucun n'existe : on crée outputs
   else
     # Pas de dossier de session partagé : /mnt/user-data n'existe pas (et n'est pas créable sans
     # droits root). Le shell tourne alors sur la machine du recruteur — c'est le cas d'un poste
     # macOS ou Windows, MAIS AUSSI de certaines sessions Cowork, où le shell est l'hôte et non un
     # conteneur. Ne pas se fier au nom « Cowork » pour trancher : seul ce test compte.
     #
     # Ici la méthode d'attache est TOUJOURS la B — le script lit le fichier localement, il n'a
     # pas à être partagé avec la session. On écrit donc dans un dossier au nom neutre, surtout
     # PAS `outputs` ni `uploads` : ces deux noms ont servi de critère de choix de la méthode A,
     # et les réutiliser ici a déjà fait tenter file_upload à un agent, qui a échoué puis demandé
     # au recruteur de partager un dossier — alors que le script attendait à côté.
     OUT="sarecrute_pub_images"
   fi
   mkdir -p "$OUT"; DST="$OUT/$NOM.png"

   # décodage : jq si présent, sinon python3 (jq n'est pas fourni par défaut sous Windows)
   if command -v jq >/dev/null 2>&1; then
     jq -r '.content' "$SRC" | base64 -d > "$DST"
   else
     python3 -c 'import base64,json,sys; open(sys.argv[2],"wb").write(base64.b64decode(json.load(open(sys.argv[1]))["content"]))' "$SRC" "$DST"
   fi

   # vérifier, puis afficher le chemin ABSOLU (c'est lui qu'il faudra donner à file_upload)
   [ -s "$DST" ] || echo "ECHEC decodage $NOM"
   command -v file >/dev/null 2>&1 && file "$DST"
   printf '%s/%s\n' "$(cd "$(dirname "$DST")" && pwd)" "$(basename "$DST")"
   ```

   Si aucun shell POSIX n'est disponible (Windows sans Git Bash), l'équivalent PowerShell. Il
   écrit dans `%TEMP%`, ce qui convient à la **méthode B** (le script lit le fichier localement)
   mais serait refusé par `file_upload` — ce cas ne se présente pas, un poste Windows sans Git
   Bash n'étant pas une session Cowork :
   ```powershell
   $OUT = Join-Path $env:TEMP 'pub_images'; New-Item -ItemType Directory -Force -Path $OUT | Out-Null
   $dst = Join-Path $OUT '<nom>.png'
   $j = Get-Content -Raw '<chemin_txt>' | ConvertFrom-Json
   [IO.File]::WriteAllBytes($dst, [Convert]::FromBase64String($j.content))
   Write-Output $dst
   ```
4. Mémoriser le chemin **tel que le shell le voit**, celui affiché par la commande ci-dessus.
   C'est ce chemin-là qu'attend `file_upload` : l'outil transfère lui-même les octets vers le
   navigateur, il ne demande pas au poste d'ouvrir le fichier. **Ne pas le convertir en chemin
   hôte** (`/Users/...`, `C:\...`) : un chemin hôte serait refusé.

   Vérifié en run réel : `/mnt/user-data/outputs/pub_images/<nom>.png` et son équivalent sous
   `uploads` sont acceptés du premier coup. Sont refusés, eux, `/mnt/user-data/working/...` et
   `/home/claude/...` — ce dernier étant le symptôme d'une sonde de dossier tombée dans le repli.

   Si l'outil refuse malgré tout le fichier, le problème est le **dossier**, pas la forme du
   chemin : l'image a été écrite hors des dossiers partagés avec la session. Reprendre le
   point 3 plutôt que d'essayer d'autres écritures du même chemin.

Si une image est introuvable (URL vide, ID invalide, échec du téléchargement, décodage en échec) :
ne pas bloquer, noter la publication comme « sans image » et continuer.

## Étape 4 — Créer un brouillon par publication

### Règle de coût — à respecter avant tout

Les captures d'écran sont le premier poste de coût de cette compétence, et **elles restent dans
le contexte** : une capture prise au 3ᵉ brouillon est refacturée à chaque tour jusqu'à la fin du
run. Le coût croît donc de façon quadratique avec le nombre de publications.

Par conséquent :

- **Vérifier par le texte, pas par l'image.** `read_page` renvoie un arbre d'accessibilité avec des
  poignées `ref_N`, et `computer` accepte `ref` au lieu de `coordinate`. `find` cherche dans le
  dernier arbre lu. Toutes les **vérifications** passent par là : présence du dialogue, contenu
  saisi, pièce jointe.
- **Toujours borner `read_page`** : `filter: "interactive"` et un `max_chars` de l'ordre de 8000.
  L'arbre complet d'une page Facebook est énorme — non borné, il coûte plus cher qu'une capture.
  Une fois le composeur trouvé, se limiter à son sous-arbre avec `ref_id` et `depth: 2`.
- **Exactement une capture par publication**, et seulement pour ouvrir le composeur (étape 4,
  point 2) : c'est le seul geste que les `ref` ne réussissent pas. Un `screenshot` plein écran est
  ici le bon outil — il faut voir la mise en page pour situer le composeur. Pas de capture pour
  quoi que ce soit d'autre.
- **Traiter chaque publication dans un sous-agent** (un par publication, **séquentiellement**).
  Les arbres et captures restent dans le contexte du sous-agent ; il ne remonte qu'une ligne de
  résultat : canal, texte posé (oui/non), image jointe (oui/non), anomalie éventuelle. C'est ce
  qui empêche le contexte principal d'enfler. Ne pas lancer les sous-agents en parallèle : ils
  piloteraient le même navigateur et se marcheraient dessus.

### Règle de temps — un coût fixe par sous-agent, à ne pas payer dix fois

Mesuré sur un run réel : ~180 s et ~133 s pour un brouillon sain, en 12 à 16 appels — soit une
dizaine de secondes par aller-retour. Le temps est **étalé sur les allers-retours**, pas concentré
dans une action lente : le levier est donc d'en faire moins, pas d'en accélérer un.

- **Un seul `ToolSearch` par sous-agent**, listant d'emblée tous les outils Chrome dont il aura
  besoin (`select:` accepte une liste séparée par des virgules). Un appel par outil, c'est un
  aller-retour perdu à chaque fois, multiplié par le nombre de publications.
- **Lui passer ce qu'il sait déjà** : le `tabId` de son onglet, l'URL du canal, le texte à saisir,
  le chemin de l'image. Il ne doit rien redécouvrir — ni relire Airtable, ni rechercher le canal.
- **Créer tous les onglets en une fois**, pas un par tour de boucle : chaque `tabs_create_mcp`
  isolé est un aller-retour complet. Constaté sur un run réel : 5 onglets créés en 4 appels
  séparés, et les téléchargements Drive enchaînés en série alors que l'étape 3 prescrit le
  contraire depuis la 0.3.2. Ces deux écarts coûtent 1 à 2 min par run — les consignes
  d'ordonnancement de l'étape 3 ne sont pas facultatives.
- **Grouper en `browser_batch` ce qui est sûr** : le clic dans le champ de texte suivi de la
  frappe, ou la navigation suivie de l'attente. **Ne jamais y fusionner une vérification et
  l'action qui la suit** — en particulier taper le texte puis joindre l'image dans un même batch.
  La frappe échoue de deux façons connues et silencieuses (timeout de `type` alors qu'elle a
  abouti ; mur de profil qui ne capte pas la saisie), et un batch attacherait alors l'image à un
  composeur vide sans que rien ne le signale. La vérification reste un appel à part, toujours.

Ce qui reste **incompressible** : les brouillons ne sont pas parallélisables (même navigateur,
`ref` invalidés, presse-papiers unique en méthode B, et surtout une seule connexion CDP). La
durée croît linéairement avec le nombre de publications.

**Compter ~3 min par brouillon**, soit ~30 min pour une dizaine. Mesuré sur 5 brouillons :
3,3 min de moyenne avant les corrections ci-dessus, ~2,5 min attendues après. Ne pas promettre
mieux à l'utilisateur — les versions précédentes annonçaient 2,5 min et se trompaient.

**Une piste non tranchée** : sur ce même run, le coût par appel a doublé du 1ᵉʳ au 5ᵉ brouillon
(9,5 s → 20,4 s) à nombre d'appels constant, ce qui suggère une taxe liée aux onglets Facebook
laissés vivants. Mais la série n'est pas monotone (9,5 / 16,1 / 11,2 / 18,4 / 20,4) et 5 points
bruités ne suffisent pas à conclure. À mesurer sur une dizaine avant d'en tirer quoi que ce soit.
Ne **pas** « publier et fermer au fur et à mesure » pour y remédier : la compétence ne publie
jamais. Si la taxe se confirme, la réponse est de découper le run en lots avec relecture humaine
entre deux.

### Déroulé, pour chaque publication retenue

**Avant le tout premier onglet du run**, appeler une fois
`tabs_context_mcp` avec `createIfEmpty: true` : c'est cet appel qui crée le groupe d'onglets de la
session et renvoie son premier `tabId`. Sans lui, `tabs_create_mcp` échoue d'emblée
(« No tab group exists for this session yet ») — donc **à la première publication de chaque run**.
Le premier brouillon utilise le `tabId` ainsi renvoyé ; les suivants seulement passent par
`tabs_create_mcp`.

Ouvrir ensuite un **nouvel onglet** par publication (`tabs_create_mcp`), puis :

1. **En un seul `browser_batch`** : `navigate` vers l'URL du canal, une attente de ~3 s, puis la
   capture d'écran du point 2. Un aller-retour au lieu de trois.

   **Pas de `read_page` ici.** Il servait à vérifier l'appartenance au groupe, or la capture
   qu'on prend de toute façon juste après montre déjà le bouton « Rejoindre le groupe » quand il
   est là. Lire les deux informations sur la même image.
   - Toutes les URL traitées ici contiennent `/groups/` : les murs de profil ont été écartés au
     filtrage de l'étape 2. Si une URL sans `/groups/` arrive jusqu'ici, c'est que le filtre a
     été contourné — ne pas la traiter.
   - Si la capture montre que le compte n'est **pas membre** du groupe ou n'a pas le droit d'y
     publier (bouton « Rejoindre le groupe », composeur absent, message d'autorisation) : ne pas
     insister, fermer l'onglet, et noter ce canal comme **« accès manquant »** pour le compte
     rendu. C'est le cas le plus fréquent quand un nouveau recruteur démarre.
2. Ouvrir le composeur — **par coordonnées, dès le premier essai** :
   - Sur la capture prise au point 1, lire les coordonnées de la zone « Exprimez-vous… » /
     « Écrivez quelque chose à … » et cliquer par `coordinate`. A marché du premier coup
     4 fois sur 5 sur le run mesuré.
   - **Grouper ce clic et la lecture qui le vérifie dans un seul `browser_batch`** : les
     coordonnées écrites dans un batch se réfèrent à la capture prise *avant* l'appel, donc celle
     du point 1 — c'est valide. Si le clic échoue, le batch s'arrête et le signale ; s'il n'ouvre
     rien, la lecture ne montre pas de dialogue. Dans les deux cas c'est détecté, jamais supposé.
   - La lecture en question : **un** `read_page` borné (`filter: "interactive"`, `max_chars: 8000`). Il sert
     à quatre choses d'un coup : confirmer la présence du `dialog "Créer une publication"`,
     récupérer le `ref` du `textbox`, celui du bouton « Photo/Vidéo » qui servira au point 6, et
     le `ref` du dialogue lui-même — c'est ce dernier qui permettra de borner les lectures
     suivantes par `ref_id`. **Ne pas refaire de `find` pour le champ image.**
   - **Ce n'est pas le repli, c'est la voie normale**, contrairement au reste de la compétence qui
     travaille par `ref`. Mesuré sur un groupe et sur un profil : **le clic par `ref` n'ouvre
     jamais le composeur**. `computer` répond « Clicked on element ref_N », `find` renvoie ensuite
     le même bouton avec un `ref` renuméroté, et rien ne s'est passé — les `ref` sont invalidés par
     la réhydratation de Facebook plus vite qu'on ne s'en sert. Deux clics `ref` par publication,
     c'est deux à trois allers-retours perdus pour rien : commencer directement par la capture
     coûte moins cher que d'y venir après avoir échoué.
   - **Une seule capture par publication**, et uniquement pour ce clic-là. Tout le reste
     (vérification du dialogue, du texte, de l'image) se fait par `read_page` borné.
   - **Une fois le dialogue ouvert, revenir aux `ref`** : ceux obtenus dans le dialogue sont
     fiables et servent pour la frappe et la pièce jointe.
   - **Ne jamais interpréter un clic « réussi » comme une preuve** — seule la présence du
     `dialog "Créer une publication"` compte, lue dans le `read_page` ci-dessus.
   - Ce que la capture montre en prime, et qui explique certains échecs : une fenêtre **Messenger**
     ouverte peut recouvrir la colonne de droite, et une bannière d'approbation admin décaler le
     composeur vers le bas. Lire les coordonnées sur l'image plutôt que les supposer.
   - Le dialogue est trouvé quand `find` renvoie un `dialog "Créer une publication"` **et** un
     `textbox`. C'est ce `textbox` qui reçoit la frappe.
   - **Piège : ne jamais taper dans une zone de commentaire.** `find` peut renvoyer un
     `textbox "Écrivez un commentaire…"` appartenant au post d'un autre membre. Y taper l'annonce
     la posterait en commentaire sous la publication de quelqu'un d'autre. N'accepter qu'un
     `textbox` situé **dans** le dialogue « Créer une publication ».
   - **Contrôler la destination** avant de taper : `find` le sélecteur d'audience et vérifier qu'il
     indique le groupe (par exemple « Partage avec Groupe public »). Sur un groupe public, le
     placeholder peut afficher « Créez une publication publique… » : ce n'est pas le composeur de
     profil, c'est normal.
3. **Vérifier au nom de qui le composeur va publier**, avant de taper quoi que ce soit : le
   dialogue affiche le nom du compte Facebook connecté. S'il ne correspond pas au recruteur
   identifié à l'étape 1, **ne rien saisir** — c'est le signe qu'on pilote la mauvaise fenêtre
   Chrome (voir les notes sur les navigateurs multiples). Fermer l'onglet et régler ça d'abord.
4. Cliquer dans le champ de texte du composeur (par `ref`), puis **taper le texte** de l'annonce.
   - **Nettoyer le texte** : retirer les tirets « - » en début de ligne des listes
     (Facebook les transforme en puces et laisse le tiret en double). Garder emojis et sauts de ligne.
   - **Taper le texte par morceaux, dans un seul `browser_batch`** : un `left_click` sur le
     `ref` du textbox, puis une action `type` **par paragraphe**. Le tout part en un aller-retour,
     et chaque morceau reste largement sous la deadline CDP.

     C'est le correctif du poste de coût le plus cher du run. Mesuré sur 5 brouillons : envoyer
     l'annonce entière (~1 500 caractères) en un seul `type` déclenche « CDP sendCommand
     Input.dispatchKeyEvent timed out » **4 fois sur 5**, l'outil attendant sa deadline complète
     alors que la frappe a déjà abouti. Le seul brouillon épargné est aussi le plus rapide du
     run (94 s contre 134 à 286 s).
   - Si un timeout survient malgré tout, **ne pas retaper d'emblée** : la frappe a
     probablement abouti. Vérifier d'abord (point suivant), sinon on obtient le texte en double.
     Cette règle a évité 4 doublons sur le run mesuré — elle reste valable après le découpage.
5. **Vérifier que le texte est bien apparu** avec `read_page` borné au `ref` de la zone de texte
   (`ref_id` = ref du textbox, `depth: 3`, `max_chars: 2500`) : chaque paragraphe saisi y apparaît
   comme un nœud, ce qui permet de contrôler le contenu ligne par ligne pour ~1,5 Ko.
   **Ne pas utiliser `get_page_text`** sur Facebook : il renvoie tout le fil du groupe, bien plus
   cher qu'une capture. Ne pas utiliser de capture non plus.
   Si le texte est absent, recliquer et retaper. Ne pas continuer sans cette vérification.
6. Joindre l'image. S'il n'y a pas d'image pour cette publication, ne rien joindre et passer à
   la suite.

   **Le critère est l'existence d'un dossier de session partagé, et rien d'autre** :

   - **`/mnt/user-data` existe** → **méthode A**, `file_upload`.
   - **sinon** → **méthode B**, le script presse-papiers. Sans exception, et sans essayer
     `file_upload` d'abord.

   C'est exactement le test fait à l'étape 3, et l'image a déjà été écrite en conséquence.

   **Ne pas trancher sur le nom de la session.** « Être en Cowork » ne garantit pas la méthode A :
   certaines sessions Cowork ont pour shell la machine du recruteur, sans `/mnt/user-data`, et
   `file_upload` y refuse tout. **Ne pas trancher non plus sur le nom du dossier de sortie** :
   une machine peut avoir un dossier `outputs` local sans que ce soit un dossier de session.

   Ce que ça évite, constaté en production chez un recruteur sous Windows en session Cowork :
   `file_upload` refuse le chemin de session comme le chemin Windows, l'agent en conclut qu'il
   manque un partage et demande au recruteur de connecter un dossier — puis constate que même un
   dossier connecté ne suffit pas. Le run reste bloqué en texte seul alors que le script de la
   méthode B était livré avec la compétence et n'avait besoin d'aucun partage. Quand
   `file_upload` refuse **le chemin de session lui-même**, il n'y a rien à débloquer : c'est le
   signe qu'on n'est pas dans un environnement à dossiers partagés, et la réponse est la
   méthode B, pas un partage supplémentaire.

   **Méthode A — `file_upload` (session à dossiers partagés)**

   C'est la voie à privilégier : rien n'est envoyé au système, le navigateur ne passe pas au
   premier plan, l'utilisateur garde sa machine.

   - **Appeler `file_upload` impérativement à l'intérieur de `browser_batch`.** Appelé seul,
     l'argument `paths` se perd en route et l'outil répond « expected array, received undefined » —
     ce n'est pas un décalage de version, juste cet appel-là qu'il faut éviter.
   - Utiliser le chemin **tel que le shell le voit** (étape 3), par exemple
     `/mnt/user-data/uploads/pub_images/<nom>.png`. Ne pas le convertir en chemin hôte.
   - **Choisir le bon champ — sans `find`.** Le `ref` du bouton **« Photo/Vidéo »** figure déjà
     dans le `read_page` borné au sous-arbre du dialogue, fait au point 2. Le réutiliser.

     **Ne pas faire un `find` des champs `type=file` à l'échelle de la page** : il en renvoie
     typiquement une dizaine, dont un seul est le bon. Tous ceux nommés « Joignez une photo ou
     une vidéo » sont des zones de **commentaire** des posts environnants, et les utiliser
     attacherait l'image au post d'un autre membre. Se limiter au sous-arbre du dialogue
     supprime l'ambiguïté au lieu de demander de trancher entre dix candidats — c'est à la fois
     un aller-retour de moins et un risque de moins.
   - Si l'outil répond « requires a non-empty `paths` array of files the user has shared with
     this session », le fichier n'est pas dans un dossier partagé : ce n'est pas un problème de
     Drive, ne pas retélécharger l'image. Après deux échecs, basculer sur la méthode B.
   - Si l'échec porte sur le chemin (fichier introuvable), c'est l'étape 3 qu'il faut corriger.

   **Méthode B — presse-papiers (repli hors Cowork)**

   Utilise le script installé lors de l'installation. Le curseur doit déjà être dans la zone de
   texte — il y est après l'étape 4. Cette méthode **passe le navigateur au premier plan et envoie
   une vraie frappe** : elle monopolise la machine quelques secondes par image, donc ne l'employer
   que si la méthode A n'est pas disponible.

   - Windows :
     ```
     powershell -sta -ExecutionPolicy Bypass -File <dossier_skill>\scripts\attach_image.ps1 -TitleFragment "<titre_onglet>" -ImagePath "<chemin_image>"
     ```
     `<titre_onglet>` = un fragment du nom du groupe. Sous Windows on ne peut pas
     sélectionner un onglet depuis le shell : le script vise la fenêtre Chrome dont l'onglet
     **actif** porte ce titre. Joindre l'image **juste après avoir tapé le texte**, tant que
     l'onglet fraîchement créé est encore l'onglet actif ; ne pas repasser en fin de run pour
     rattraper toutes les images d'un coup.
   - macOS :
     ```
     <dossier_skill>/scripts/attach_image.sh "<fragment_url_onglet>" "<chemin_image>"
     ```
     `<fragment_url_onglet>` = l'identifiant numérique du groupe, tel qu'il
     apparaît dans l'URL de l'onglet ; il sert à retrouver l'onglet et à le mettre au premier plan.
     Sortie 2 « Accessibilité refusée » : l'app Claude n'est pas cochée dans Réglages Système >
     Confidentialité et sécurité > Accessibilité. Le dire à l'utilisateur et poursuivre en texte
     seul ; ne pas boucler sur des tentatives.

   **Ne jamais essayer de coller avec `computer` action `key` (`ctrl+v` / `cmd+v`).** C'est une
   frappe synthétique : elle ne porte pas le presse-papiers, l'outil répond « Pressed 1 key » et
   **rien n'est collé**. Seul un raccourci envoyé par le script au niveau du système fonctionne.

   **Contrôler le résultat dans les deux cas, en UN seul appel** : un `read_page` borné au
   sous-arbre du dialogue (`ref_id` du dialogue, `depth: 3`) montre à la fois l'`image`, le bouton
   « Supprimer la pièce jointe de la publication » et le texte déjà saisi — donc aussi qu'il n'a
   pas été remplacé. Ne pas faire `find` **puis** `read_page` : c'est un aller-retour pour rien.
7. **Ne pas cliquer sur « Publier ».** Laisser l'onglet ouvert.

Enchaîner ainsi, un onglet par publication — tous les onglets restent ouverts pour la relecture,
c'est voulu. Ne pas regrouper ni découper le run en lots.

## Étape 5 — Compte rendu

À la fin, récapituler :
- **au nom de quel recruteur** les brouillons ont été préparés ;
- le nombre de brouillons préparés et leurs destinations ;
- l'image utilisée par offre ;
- **la liste des publications sans image trouvée**, le cas échéant ;
- **la liste des canaux en « accès manquant »** (groupe non rejoint), avec la consigne de
  demander l'accès avant le prochain lancement ;
- **la liste des publications écartées parce que leur canal est un mur de profil** (`/me`,
  `/veto.annonce`), présentées comme « à faire à la main » et non comme un échec : elles restent
  à la charge du recruteur, il doit savoir lesquelles ;
- rappeler que rien n'a été publié et qu'il reste à cliquer sur « Publier » dans chaque onglet.

## Notes / pièges connus

- Le texte et l'image d'une offre sont partagés par tous ses canaux → télécharger l'image une
  seule fois et réutiliser le fichier local pour tous les onglets de la même offre.
- Sur les 14 canaux ayant une URL, 12 sont des groupes partagés — les seuls traités par cette
  compétence — et un recruteur ne peut y publier que s'il en est membre. Les 2 autres sont des
  murs de profil, écartés au filtrage de l'étape 2 : « Facebook perso » (`/me`) et « Annonces
  véto » (`/veto.annonce`). Ce dernier n'est **pas une Page** malgré son usage : c'est un profil
  personnel (~4 900 ami(e)s), et y publier revient à écrire sur le journal d'un tiers.
- **Ce qui reste à résoudre pour les murs de profil**, le jour où on voudra les réintégrer : le
  dialogue modal se replie en composeur inline, l'image ne s'attache pas, et le champ
  « Photo/Vidéo » à viser est ambigu. Rien n'a encore été trouvé qui fonctionne — ne pas écrire
  de procédure ici avant de l'avoir vérifiée sur un run réel. Deux cas sont sans doute à
  distinguer : son propre mur (`/me`), qui a déjà fonctionné par le passé, et le journal d'un
  tiers (`/veto.annonce`), qui est celui qui a échoué.
- **Plusieurs navigateurs connectés = risque de publier sous le mauvais compte.** Appeler
  `list_connected_browsers` **avant** d'ouvrir le premier onglet. S'il y en a plus d'un, demander
  lequel via AskUserQuestion : une option par navigateur, plus une option « ouvrir une
  confirmation dans chaque Chrome » qui déclenche `switch_browser`. Ne jamais en choisir un soi-
  même. Le profil Chrome ne dit rien du compte Facebook actif : seul le nom affiché dans le
  composeur fait foi.

  **Mémoriser le choix** dans `navigateurDeviceId` de `recruteur.json` (étape 1) dès qu'un
  navigateur a été retenu, et s'en servir aux runs suivants : si l'id mémorisé figure toujours
  dans `list_connected_browsers`, le proposer **en première option et pré-sélectionné**, plutôt
  que de repartir d'une liste neuve. S'il a disparu (Chrome réinstallé, extension repairée),
  redemander normalement et réécrire l'id.

  Deux limites constatées, à ne pas contourner. D'abord, la question reste obligatoire dès qu'il
  y a plus d'un navigateur connecté : la mémorisation fait gagner la recherche du bon, pas la
  question elle-même — l'option « ouvrir une confirmation dans chaque Chrome » coûte en revanche
  jusqu'à deux minutes d'attente humaine, et c'est elle qu'on évite. Ensuite, **c'est bien l'id
  qu'il faut mémoriser, pas le nom** : le nom donné en cliquant « Connect » n'est pas repris par
  `list_connected_browsers`, qui continue d'afficher « Browser 1 » / « Browser 2 ». Les
  `deviceId`, eux, sont restés stables d'un appel à l'autre et à travers un `switch_browser`.
- Si Chrome répond « not connected », suivre les consignes de l'outil (attendre/réessayer).
- Deux étapes dépendent du système : le décodage des images (étape 3) et leur collage
  (étape 4). Sous Windows, `jq` n'est pas installé par défaut et `base64`/`file` n'existent que
  via Git Bash ; le collage passe par PowerShell au lieu d'AppleScript. Les replis prévus
  couvrent ces cas ; ne pas revenir à une commande unique supposant un environnement Unix.
- **Méthode B uniquement** : le collage passe le navigateur au premier plan et envoie une vraie
  frappe, ce qui monopolise la machine quelques secondes par image. Le reste du run (chargement,
  saisie des textes, vérifications) passe par CDP et n'a pas besoin du focus. Prévenir
  l'utilisateur en début de run qu'il ne doit pas taper pendant ces quelques secondes, plutôt que
  de lui demander de ne pas toucher à sa machine du début à la fin. En méthode A, ne pas
  l'avertir de quoi que ce soit : il n'y a rien à subir.
- **Ne pas paralléliser les publications**, quelle que soit la méthode : les sous-agents
  piloteraient le même navigateur et leurs `ref` s'invalideraient mutuellement. En méthode B
  s'ajoute le presse-papiers, ressource unique : deux collages simultanés enverraient l'image
  dans le mauvais onglet, sans erreur visible.
- Ne jamais publier ; ne jamais cocher « Publié ? » dans Airtable.
