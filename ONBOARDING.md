# Onboarding — Compétences recruteur SaRecrute

> **Claude** : si ce guide vient de t'être donné par l'utilisateur, déroule la section
> « Instructions pour Claude » plus bas, étape par étape. C'est une demande d'installation.

Bienvenue ! Ce guide installe sur ton ordinateur les compétences Claude des recruteurs SaRecrute :

- **créer une clinique et son offre** dans Airtable à partir d'une annonce que tu colles, puis
  préparer le premier contact ;
- **préparer tes brouillons de publication Facebook** du jour à partir de tes offres.

Aucune des deux n'envoie ni ne publie quoi que ce soit : elles préparent, tu relis, **c'est toi
qui cliques**.

Tu n'as rien à installer à la main : Claude s'en occupe en suivant les étapes ci-dessous.
Laisse-le dérouler et réponds à ses questions.

**Lance ces compétences depuis une session Cowork.** C'est là que les images des publications se
joignent toutes seules, sans que le navigateur ne vienne te voler l'écran. Hors Cowork ça
fonctionne aussi, mais par un copier-coller qui monopolise le premier plan quelques secondes par
image — et qui, sur Mac, demande une autorisation système.

---

## Instructions pour Claude

Exécute les étapes dans l'ordre. Après chaque étape, dis en une ligne si c'est bon ou ce qui
manque. Ne passe pas à l'étape suivante si la précédente bloque : explique à l'utilisateur ce
qu'il doit faire, en langage non technique — c'est un recruteur, pas un développeur.

### Étape 1 — Installer le plugin

Les compétences sont distribuées par une marketplace publique. **Ne jamais écrire un `SKILL.md`
à la main** : la source de vérité est le dépôt `Cleuteu/sarecrute-competences`, et toute copie
locale finirait par diverger.

Dans un terminal :

```bash
claude plugin marketplace add Cleuteu/sarecrute-competences
claude plugin install sarecrute-recruteur@sarecrute-competences
```

> **Si tu avais déjà installé le plugin avant le 18 août 2026**, il portait l'identifiant
> `sarecrute-recruteur@sarecrute`. La marketplace a été renommée : retire l'ancienne version
> avant de relancer les deux commandes ci-dessus, sinon les deux cohabitent.
>
> ```bash
> claude plugin uninstall sarecrute-recruteur@sarecrute
> claude plugin marketplace remove sarecrute
> ```

Puis redémarrer Claude Code. Vérifie ensuite que les deux compétences sont bien disponibles :
`creer-clinique-offre` et `creer-brouillons-facebook`. Si elles n'apparaissent pas, c'est le
redémarrage qui manque.

Le plugin ne contient que ces deux compétences. La marketplace en propose un second,
`sarecrute-admin` (collecte des posts du groupe Facebook) : il est réservé au poste
d'administration, **ne l'installe pas** et n'en parle pas au recruteur.

Les scripts dont la compétence a besoin sont livrés avec elle, il n'y a rien d'autre à écrire.

Pour la suite, en cas de correction annoncée : `claude plugin update sarecrute-recruteur@sarecrute-competences`, puis
redémarrer.

### Étape 2 — Vérifier le mode d'exécution

C'est ce qui détermine comment les images des publications seront jointes.

```bash
pwd
for d in /mnt/user-data/uploads /mnt/user-data/outputs outputs uploads; do
  [ -d "$d" ] && { touch "$d/.w" 2>/dev/null && rm -f "$d/.w" && echo "$d ECRIVABLE" || echo "$d lecture seule"; }
done
```

- Un de ces dossiers écrivable = session **Cowork**. Les images seront jointes directement par
  l'outil d'upload : aucun réglage système, aucune frappe envoyée au poste, et le recruteur garde
  sa machine pendant les runs. C'est le mode recommandé, et il n'y a rien de plus à faire.
- Tester l'écriture réellement, comme ci-dessus, plutôt que de se fier à un avertissement : en
  Cowork, `/mnt/user-data/uploads` a déjà été annoncé « read-only » par le système alors qu'il
  était bel et bien écrivable. Le `pwd` y vaut `/home/claude`, d'où l'inutilité de chercher ces
  dossiers en chemin relatif.
- **En Cowork, le système du poste ne compte pas** : le shell tourne dans un conteneur Linux, pas
  sur la machine du recruteur. Un recruteur sous Windows y dispose de `jq`, `base64` et `python3`
  sans rien installer.

Si aucun dossier n'est écrivable, on est hors Cowork : les images passeront par le presse-papiers.

- **Windows** : rien à autoriser, `powershell` est natif.
- **macOS** : l'app qui fait tourner Claude doit être cochée dans Réglages Système >
  Confidentialité et sécurité > **Accessibilité**, sinon le collage échoue avec « osascript n'est
  pas autorisé à envoyer de saisies (1002) ». C'est un réglage manuel : demande-le à
  l'utilisateur, tu ne peux pas l'accorder toi-même.
- Dans les deux cas, préviens que le navigateur passera devant quelques secondes à chaque image,
  et qu'il ne faut pas taper pendant ce court instant. Entre deux images, la machine est libre.

Dis à l'utilisateur en une phrase dans quel mode il est. S'il n'est pas en Cowork, signale-lui
qu'y lancer les compétences lui éviterait cette gêne.

### Étape 3 — Vérifier les connecteurs

Les compétences ont besoin de quatre accès. **Tu ne peux pas les brancher toi-même** : si l'un
manque, explique à l'utilisateur où aller (réglages des connecteurs de son compte Claude).

1. **Airtable** — teste l'accès en lecture : liste 1 seul record de la table des canaux de
   diffusion (base `appP0W2ISytaNyAhG`, table `tbluH5M2sogAN85dl`). En cas d'erreur de
   permission, il faut connecter Airtable avec un compte ayant accès à la base « Recrutement
   vétérinaire ».
2. **Gmail** — utilisé par `creer-clinique-offre` pour le brouillon de premier contact. Sans lui,
   cette compétence bascule sur un message à copier-coller : ce n'est pas bloquant, mais dis-le.
3. **Google Drive** — nécessaire aux visuels des publications. Deux vérifications, la seconde est
   celle qui compte :
   - l'outil de lecture de fichiers Drive est disponible ;
   - **l'accès au dossier des visuels** est effectif. Cherche dans le Drive le dossier nommé
     « Publications » (`mimeType = 'application/vnd.google-apps.folder' and title = 'Publications'`)
     et confirme qu'il ressort. Ce dossier est dans un **Drive partagé** : un compte peut avoir le
     connecteur branché et ne pas voir ce dossier pour autant.

     Si l'accès échoue, c'est bloquant pour les images (pas pour le texte) : l'utilisateur doit
     demander à être ajouté en **Lecteur** au Drive partagé contenant le dossier « Publications »,
     puis relancer cette étape. Dis-le explicitement plutôt que de continuer comme si de rien.
4. **Claude in Chrome** — l'extension doit être active et Chrome ouvert. Vérifie que tu peux
   lister les onglets.

### Étape 4 — Enregistrer l'identité du recruteur

Pour que les compétences ne traitent que **ses** publications. Elles savent le faire au premier
lancement, mais autant l'expédier maintenant :

1. Récupère depuis Airtable la liste des responsables des 3 derniers mois : table
   `tblzKMXlCBH21hbJy`, champ `Responsable de l'offre` (`fld0PBN7RvLtXb2Is`), filtre
   `{"operator":"isWithin","operands":["fldgV9Lx0qoPiG5Ry",{"mode":"pastNumberOfDays","numberOfDays":90,"timeZone":"Europe/Paris"}]}`.
   Déduplique les couples nom + email.
2. Demande à l'utilisateur qui il est (AskUserQuestion), en pré-sélectionnant l'entrée dont
   l'email correspond à celui de son compte Claude s'il y a une correspondance.
3. Écris le résultat dans `$HOME/.sarecrute/recruteur.json` (crée le dossier) :
   ```json
   { "responsable": "Prénom Nom", "email": "prenom@exemple.fr" }
   ```
   Sous Windows : `%USERPROFILE%\.sarecrute\recruteur.json`. Ce fichier est **local à la
   machine** : il ne doit être ni versionné ni partagé. Dis à l'utilisateur qu'il peut le
   modifier ou le supprimer pour changer d'identité.

### Étape 5 — Essai à blanc (sans ouvrir aucun onglet)

Sans lancer les compétences, vérifie que les données répondent : liste les publications
**datées d'aujourd'hui** et **non publiées** du responsable enregistré à l'étape 4
(table `tblzKMXlCBH21hbJy`, date `fldgV9Lx0qoPiG5Ry`, publié `fldOrR0E0zGE3nq6F` = false).

Annonce combien il y en a. S'il n'y en a aucune, c'est normal : dis-le sans en faire un problème.
**N'ouvre aucun onglet Facebook à cette étape.**

Précise aussi combien d'entre elles ont un visuel renseigné (champ `url image publication`,
`fldZBl35fPmU2hwlq`). Une publication sans visuel partira en texte seul et sera listée comme telle
dans le compte rendu — ce n'est pas une erreur d'installation. En revanche, si **aucune** image
n'est téléchargeable alors que les URLs sont renseignées, c'est le symptôme d'un accès Drive
manquant : revenir à l'étape 3.

### Étape 6 — Accès Facebook

Rappelle à l'utilisateur les conditions pour que ça marche le jour J :

- Chrome doit être connecté à **son** compte Facebook (c'est ce compte qui publiera). S'il a
  plusieurs fenêtres Chrome connectées à l'extension — par exemple un profil pro et un profil
  perso — la compétence demandera laquelle utiliser avant d'ouvrir quoi que ce soit : le profil
  Chrome ne dit rien du compte Facebook réellement connecté.
- Il doit être **membre des groupes** où ses annonces sont diffusées. Sur les 14 canaux
  configurés, 12 sont des groupes Facebook. S'il n'est pas membre, la compétence le signalera en
  fin de compte rendu au lieu d'échouer — il faudra demander l'accès à l'administrateur du groupe.

Le canal « Facebook perso » pointe vers `facebook.com/me` : il publiera donc sur **son** profil,
pas sur celui de quelqu'un d'autre. C'est voulu.

### Étape 7 — Conclure

Récapitule en quelques lignes : ce qui est installé, ce qui manque encore le cas échéant, et
comment s'en servir — il n'y a pas de commande à retenir, les compétences se déclenchent d'elles-
mêmes quand la demande correspond :

- « prépare les brouillons Facebook du jour » ;
- ou simplement en collant une annonce de clinique dans Claude.

Précise le mode détecté à l'étape 2 et la gêne à attendre pendant un run : aucune en Cowork,
quelques secondes de premier plan par image sinon.

Rappelle enfin que rien n'est jamais publié ni envoyé automatiquement, et qu'en cas de correction
annoncée il suffit de lancer `claude plugin update sarecrute-recruteur@sarecrute-competences` puis de redémarrer.
