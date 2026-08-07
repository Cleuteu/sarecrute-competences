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
et destinée à un **canal Facebook dont l'URL est renseignée**, préparer un brouillon dans un
onglet Chrome (texte de l'annonce + image du Drive), **sans jamais publier**. L'utilisateur
relira et cliquera lui-même sur « Publier ».

La compétence est **multi-recruteur** : elle prépare les brouillons du recruteur qui la lance, sur
son ordinateur et avec son propre compte Facebook.

Prérequis, propres à chaque utilisateur :

- connecteurs **Airtable** et **Google Drive** connectés sur son compte Claude ;
- **Claude in Chrome** actif, Chrome ouvert et connecté à **son** compte Facebook ;
- être membre des groupes Facebook visés (sinon ces canaux seront signalés, voir étape 4) ;
- pour les images : soit une **session Cowork** (l'upload direct fonctionne, rien à régler), soit
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
   { "responsable": "Prénom Nom", "email": "prenom@exemple.fr" }
   ```
   S'il existe et que `responsable` est renseigné : l'utiliser **sans poser de question**, et
   indiquer en une ligne au début du compte rendu au nom de qui on travaille.

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
   - garder uniquement celles dont le **canal a une URL** (jointure via le nom du canal).

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
   # file_upload n'autorise que les fichiers des dossiers partagés avec la session
   # (uploads/outputs de la session, ou un dossier ouvert par l'utilisateur).
   # Un dossier temporaire système ($TMPDIR, /tmp) est REFUSÉ : ne jamais l'utiliser ici.
   # En Cowork, ces dossiers sont en chemin ABSOLU sous /mnt/user-data — le cwd est /home/claude,
   # donc les tester en relatif ne trouve rien. Les chemins absolus passent en premier.
   for c in /mnt/user-data/uploads /mnt/user-data/outputs outputs uploads; do
     [ -d "$c" ] && [ -w "$c" ] && { OUT="$c/pub_images"; break; }
   done
   OUT="${OUT:-pub_images}"   # à défaut : le répertoire de travail de la session
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

   Vérifié en session Cowork : `/mnt/user-data/uploads/pub_images/<nom>.png` est accepté du
   premier coup.

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

### Déroulé, pour chaque publication retenue

**Avant le tout premier onglet du run**, appeler une fois
`tabs_context_mcp` avec `createIfEmpty: true` : c'est cet appel qui crée le groupe d'onglets de la
session et renvoie son premier `tabId`. Sans lui, `tabs_create_mcp` échoue d'emblée
(« No tab group exists for this session yet ») — donc **à la première publication de chaque run**.
Le premier brouillon utilise le `tabId` ainsi renvoyé ; les suivants seulement passent par
`tabs_create_mcp`.

Ouvrir ensuite un **nouvel onglet** par publication (`tabs_create_mcp`), puis :

1. `navigate` vers l'URL du canal ; attendre ~3 s le chargement. **Pas de capture ici** :
   appeler `read_page` borné comme indiqué ci-dessus.
   - Le canal « Facebook perso » a pour URL `https://www.facebook.com/me` : Facebook redirige
     vers le profil du compte connecté dans Chrome, donc **vers le profil du recruteur qui
     lance la compétence**. C'est voulu — ne pas remplacer cette URL par un profil nommé.
   - Si l'arbre montre que le compte n'est **pas membre** du groupe ou n'a pas le droit d'y
     publier (bouton « Rejoindre le groupe », composeur absent, message d'autorisation) : ne pas
     insister, fermer l'onglet, et noter ce canal comme **« accès manquant »** pour le compte
     rendu. C'est le cas le plus fréquent quand un nouveau recruteur démarre.
2. Ouvrir le composeur — **par coordonnées, dès le premier essai** :
   - Prendre **une** capture (`screenshot`), y lire les coordonnées de la zone « Exprimez-vous… » /
     « Écrivez quelque chose à … », et cliquer par `coordinate`.
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
     `dialog "Créer une publication"` compte, vérifiée par `find`.
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
   - Sur un texte long, l'action `type` peut répondre « CDP sendCommand Input.dispatchKeyEvent
     timed out » **alors que la frappe a bien abouti**. Ne pas retaper d'emblée : vérifier d'abord
     (point suivant), sinon on obtient le texte en double.
5. **Vérifier que le texte est bien apparu** avec `read_page` borné au `ref` de la zone de texte
   (`ref_id` = ref du textbox, `depth: 3`, `max_chars: 2500`) : chaque paragraphe saisi y apparaît
   comme un nœud, ce qui permet de contrôler le contenu ligne par ligne pour ~1,5 Ko.
   **Ne pas utiliser `get_page_text`** sur Facebook : il renvoie tout le fil du groupe, bien plus
   cher qu'une capture. Ne pas utiliser de capture non plus.
   Sur les murs de profil, le champ ne capte parfois pas la frappe : si le texte est absent,
   recliquer et retaper. Ne pas continuer sans cette vérification.
6. Joindre l'image. S'il n'y a pas d'image pour cette publication, ne rien joindre et passer à
   la suite.

   **Choisir la méthode selon la session, en le vérifiant et non en le supposant** : si l'étape 3
   a pu écrire l'image dans un dossier `outputs/` ou `uploads/` de la session, utiliser
   `file_upload` (méthode A). Sinon, passer par le presse-papiers (méthode B).

   **Méthode A — `file_upload` (session Cowork)**

   C'est la voie à privilégier : rien n'est envoyé au système, le navigateur ne passe pas au
   premier plan, l'utilisateur garde sa machine.

   - **Appeler `file_upload` impérativement à l'intérieur de `browser_batch`.** Appelé seul,
     l'argument `paths` se perd en route et l'outil répond « expected array, received undefined » —
     ce n'est pas un décalage de version, juste cet appel-là qu'il faut éviter.
   - Utiliser le chemin **tel que le shell le voit** (étape 3), par exemple
     `/mnt/user-data/uploads/pub_images/<nom>.png`. Ne pas le convertir en chemin hôte.
   - **Choisir le bon champ** : un `find` renvoie typiquement **une dizaine** de champs
     `type=file`, un seul est le bon — celui nommé **« Photo/Vidéo »** appartenant au dialogue
     « Créer une publication ». Tous ceux nommés « Joignez une photo ou une vidéo » sont des zones
     de **commentaire** des posts environnants ; les utiliser attacherait l'image au post d'un
     autre membre.
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
     `<titre_onglet>` = un fragment du nom du groupe ou de la Page. Sous Windows on ne peut pas
     sélectionner un onglet depuis le shell : le script vise la fenêtre Chrome dont l'onglet
     **actif** porte ce titre. Joindre l'image **juste après avoir tapé le texte**, tant que
     l'onglet fraîchement créé est encore l'onglet actif ; ne pas repasser en fin de run pour
     rattraper toutes les images d'un coup.
   - macOS :
     ```
     <dossier_skill>/scripts/attach_image.sh "<fragment_url_onglet>" "<chemin_image>"
     ```
     `<fragment_url_onglet>` = l'identifiant numérique du groupe ou le slug de la Page, tel qu'il
     apparaît dans l'URL de l'onglet ; il sert à retrouver l'onglet et à le mettre au premier plan.
     Sortie 2 « Accessibilité refusée » : l'app Claude n'est pas cochée dans Réglages Système >
     Confidentialité et sécurité > Accessibilité. Le dire à l'utilisateur et poursuivre en texte
     seul ; ne pas boucler sur des tentatives.

   **Ne jamais essayer de coller avec `computer` action `key` (`ctrl+v` / `cmd+v`).** C'est une
   frappe synthétique : elle ne porte pas le presse-papiers, l'outil répond « Pressed 1 key » et
   **rien n'est collé**. Seul un raccourci envoyé par le script au niveau du système fonctionne.

   **Contrôler le résultat dans les deux cas** : `find` doit renvoyer une `image` **et** un bouton
   « Supprimer la pièce jointe de la publication ». Vérifier aussi que le texte déjà saisi n'a pas
   été remplacé (`read_page` borné au textbox).
7. **Ne pas cliquer sur « Publier ».** Laisser l'onglet ouvert.

Enchaîner ainsi, un onglet par publication — tous les onglets restent ouverts pour la relecture,
c'est voulu. Ne pas regrouper ni découper le run en lots.

## Étape 5 — Compte rendu

À la fin, récapituler :
- **au nom de quel recruteur** les brouillons ont été préparés ;
- le nombre de brouillons préparés et leurs destinations ;
- l'image utilisée par offre ;
- **la liste des publications sans image trouvée**, le cas échéant ;
- **la liste des canaux en « accès manquant »** (groupe non rejoint, pas de droit sur la Page),
  avec la consigne de demander l'accès avant le prochain lancement ;
- rappeler que rien n'a été publié et qu'il reste à cliquer sur « Publier » dans chaque onglet.

## Notes / pièges connus

- Le texte et l'image d'une offre sont partagés par tous ses canaux → télécharger l'image une
  seule fois et réutiliser le fichier local pour tous les onglets de la même offre.
- Toutes les destinations ne sont pas des groupes : « Annonces véto » (`/veto.annonce`) est une
  Page, « Facebook perso » (`/me`) est le profil du recruteur connecté. Le flux composeur est le
  même, seule la position de la zone de saisie change.
- Sur les 14 canaux ayant une URL, 12 sont des groupes partagés : un recruteur ne peut y publier
  que s'il en est membre. La Page « Annonces véto » demande en plus un rôle sur la Page.
- **Plusieurs navigateurs connectés = risque de publier sous le mauvais compte.** Appeler
  `list_connected_browsers` **avant** d'ouvrir le premier onglet. S'il y en a plus d'un, demander
  lequel via AskUserQuestion : une option par navigateur, plus une option « ouvrir une
  confirmation dans chaque Chrome » qui déclenche `switch_browser`. Ne jamais en choisir un soi-
  même. Le profil Chrome ne dit rien du compte Facebook actif : seul le nom affiché dans le
  composeur fait foi.
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
