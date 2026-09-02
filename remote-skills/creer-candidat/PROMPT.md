**creer-candidat — version 0.2.0 (2026-09-02)**

> Ce fichier est le corps de la compétence `creer-candidat` du plugin `sarecrute-recruteur`. Il
> n'est **pas** installé chez l'utilisateur : le stub `SKILL.md` du plugin le télécharge depuis la
> branche `stable` de ce dépôt à chaque exécution, avec `scripts/` et `references/` (un `MANIFEST` liste les fichiers du
> snapshot et leur version commune : le stub vérifie qu'elle est celle de ce PROMPT.md).
>
> **Pour déployer une modification** : éditer ce fichier (ou `scripts/`, `references/`) sur
> `main`, mettre à jour la ligne de version ci-dessus, régénérer les manifests
> (`python3 tools/manifests.py`), puis avancer la branche de déploiement :
> `git push origin main:stable` (compter jusqu'à cinq minutes de cache côté `raw`). Aucun republish du plugin, aucun `plugin update` chez
> l'utilisateur.
>
> Le stub, lui, ne change presque jamais : n'y toucher que pour son `description` (déclenchement)
> — et là, bump du plugin + republish + `plugin update` redeviennent nécessaires.

# Créer un candidat depuis un CV, une annonce, un transcript — ou juste un nom

Le recruteur apporte ce qu'il a. Une seule chose est obligatoire : **le nom**. Tout le reste est
optionnel et cumulable — un CV *et* un transcript d'appel valent mieux que l'un des deux.

Prérequis : connecteur **Airtable**. Pour joindre un CV en pièce jointe, la variable
d'environnement `AIRTABLE_API_KEY` (le MCP ne sait pas téléverser de pièce jointe).

Base **PROD** : `appP0W2ISytaNyAhG` · Candidats `tblPmkTaAjS9Yoovt` ·
Compétences `tblH8Zym1DNu7PN3c` · Actes `tblt32Afmq6vQ6FJS`.

## Ressources du snapshot

| Fichier | Rôle |
|---|---|
| `references/champs-candidat.md` | champs à remplir, IDs, valeurs de select, **et ce que chaque champ fait au matching** ; table `Recruteurs` (ÉTAPE 1) |
| `references/candidature.md` | l'offre visée : pratiques recopiées, contrôle du matching, création de la candidature (ÉTAPE 7) |
| `scripts/routine.py` | télécharge la doctrine d'enrichissement depuis le dépôt (ÉTAPE 6) |
| `scripts/cv.py` | retrouve le fichier d'un CV sur le disque, en extrait le texte, et le joint à la fiche |
| `scripts/ville.py` | résout la ville en département + CP — **absent du snapshot, à télécharger** |

`<dossier_skill>` = le `$DEST` dans lequel le stub a extrait ce snapshot. **Ne jamais coder de
chemin en dur** et ne jamais aller chercher un fichier dans le plugin installé : ce corps de
compétence ne vit pas dans le plugin.

`ville.py` appartient à `creer-clinique-offre` (compétence distante elle aussi depuis le
01/09/2026, son snapshot vit dans `remote-skills/creer-clinique-offre/`). Plutôt que d'en garder
une seconde copie qui dériverait, on le tire de la **même branche `stable`** que ce snapshot, et
seulement quand une ville est à résoudre :

```bash
curl -fsSL -o "<dossier_skill>/scripts/ville.py" \
  https://raw.githubusercontent.com/Cleuteu/sarecrute-competences/stable/remote-skills/creer-clinique-offre/scripts/ville.py
```

⚠️ Si ce téléchargement renvoie un 404 (fichier déplacé dans le dépôt), le symptôme est franc,
pas silencieux : le repli est d'écrire `county` à la main.

Écrire **par ID de champ**, **sans `typecast`**. Ne jamais ajouter de valeur à un champ select :
si la source ne rentre dans aucune valeur existante, laisser vide et le signaler.

## Étape 1 — Savoir au nom de qui on travaille

L'identité du recruteur alimente `Sourceur` et `Ajouté au CRM par` (et, à l'ÉTAPE 7, le
propriétaire de la candidature), sous la forme `{"email": "…"}` — l'e-mail du **collaborateur
Airtable**, la même personne partout, comme le fait la saisie à la main dans la base. Trois
sources, dans cet ordre, en s'arrêtant à la première qui répond :

1. **Le fichier local** `$HOME/.sarecrute/recruteur.json` (Windows :
   `%USERPROFILE%\.sarecrute\recruteur.json`) :
   ```json
   { "responsable": "Prénom Nom", "email": "prenom@exemple.fr" }
   ```
   S'il existe, l'utiliser **sans poser de question**. C'est le même fichier que
   `creer-clinique-offre`. **En session cloud (Cowork) il n'existe jamais** : `$HOME` est jeté à
   la fin de la session. Sa lecture qui échoue n'est pas une anomalie — ne rien signaler, ne pas le
   chercher ailleurs, passer au point 2.
2. **La table `Recruteurs`** (`tblDUpPwkuHYnAPyt`, champs dans `references/champs-candidat.md`).
   Lire les lignes **actives** avec `Nom`, `Email`, `Email compte Claude`. Comparer l'e-mail du
   compte Claude de l'utilisateur de la session à `Email compte Claude`, puis à `Email`, casse
   ignorée. **Une correspondance → c'est cette personne, sans question.** Aucune correspondance
   mais **une seule recruteuse active** → c'est elle, sans question, en le disant.
3. **Sinon, demander** avec AskUserQuestion parmi les recruteuses actives (jamais `Automations`),
   puis **mémoriser pour que la question ne se repose plus** :
   - écrire `Email compte Claude` (`fldaxrZ7PftpZQQfl`) sur la ligne `Recruteurs` choisie avec
     l'e-mail du compte Claude de la session — c'est le seul champ de cette table que la
     compétence écrit, et seulement s'il est vide ; c'est lui qui rend le point 2 suffisant au
     prochain lancement, y compris en session cloud ;
   - écrire le fichier local (créer le dossier), local à la machine, jamais versionné. Si
     l'écriture échoue (session cloud) : ne pas réessayer, ne pas en faire un incident, la table
     fait le travail.

Dire en une ligne, au début du compte rendu, au nom de qui on travaille **et d'où vient
l'identité** (fichier, compte Claude reconnu dans `Recruteurs`, seule recruteuse active, ou
choisie), et comment en changer : modifier le fichier, ou lancer la compétence en nommant la
recruteuse voulue.

⚠️ **Le fichier local définit l'identité de la machine, pas celle de la personne qui tape.** Si
le fichier dit Sarah, un candidat créé depuis ce poste est attribué à Sarah — même si c'est
quelqu'un d'autre qui lance la commande. C'est voulu : c'est le poste de travail d'une recruteuse.
Ne jamais essayer de deviner l'opérateur réel (utilisateur système, signature git) pour
« corriger » l'attribution quand le fichier existe, et ne jamais demander confirmation. Le compte
Claude n'entre en jeu qu'au point 2, quand il n'y a pas de fichier.

Si l'e-mail retenu n'est pas celui d'un collaborateur de la base, l'écriture des champs
collaborateur échoue : c'est le signal que la ligne `Recruteurs` porte un mauvais `Email` —
le dire, ne pas contourner.

## Étape 2 — Trier les sources

Chaque source a **une** destination. Ne jamais mélanger : la routine d'enrichissement les lit
séparément et ne leur accorde pas le même crédit (la parole > le CV > l'annonce promotionnelle).

| Ce qu'apporte le recruteur | Champ de destination | Traitement |
|---|---|---|
| Un CV (PDF, DOCX, texte collé) | `CV text` + pièce jointe `CV` | étape 3 |
| Une annonce de recherche du candidat (post Facebook, message, mail de candidature) | `Post` | verbatim **intégral**, jamais résumé |
| Un transcript d'appel | `Transcripts` | verbatim intégral |
| Rien, juste nom + prénom | — | fiche minimale, étape 6 sautée |

Trois règles de tri :

- **Le verbatim ne se retouche pas.** Ni résumé, ni reformulé, ni tronqué. Ces champs sont la
  matière première de l'enrichissement et la trace à laquelle un recruteur revient.
- ⚠️ **`Notes` ne s'écrit jamais.** C'est l'espace du recruteur : il y écrit ce qu'il a compris
  d'un appel, ses réserves, ses relances. Pas une ligne, pas un horodatage, pas un « contexte » —
  rien. Si une information de provenance mérite d'être conservée (date de réception du CV, date de
  l'appel), elle va dans l'en-tête daté de la source elle-même (`Transcripts`, `Post`, `CV text`),
  jamais dans `Notes`. `Notes du candidat` est réservé à ce que le candidat écrit lui-même et ne
  s'écrit pas non plus.
- **Une annonce de clinique n'est pas une source candidat.** Si le texte collé décrit un poste à
  pourvoir et non quelqu'un qui en cherche un, c'est `creer-clinique-offre` qu'il faut, pas cette
  compétence. Le dire et s'arrêter. Une seule exception, bornée et décrite à l'ÉTAPE 7 : quand le
  recruteur désigne **l'offre à laquelle le candidat postule**, les **espèces** de cette offre
  peuvent compléter sa fiche — jamais ses spécialités ni ses actes.

**Sans nom, on ne crée rien.** Un candidat sans nom porte `Anonyme #<n>` (formule) et devient
introuvable pour tout le monde. Si aucune source ne donne de nom, demander lequel avant d'écrire.

## Étape 3 — Le CV : le texte, et le fichier

Deux choses distinctes, et il faut deux gestes : le **texte** va dans `CV text`
(`fldFe8hgz5ekEHayv`), c'est lui que lit l'enrichissement ; le **fichier** va dans la pièce jointe
`CV` (`fldsj2ukrpjPzu5ox`), c'est lui que le recruteur ouvre et envoie à la clinique.

### Il faut un chemin sur le disque pour joindre le fichier

Le téléversement envoie des octets : il exige un fichier réel. Selon la façon dont le CV arrive,
on l'a ou on ne l'a pas.

| Comment le CV arrive | Fichier joignable ? |
|---|---|
| Le recruteur donne un chemin (`@~/Downloads/CV Dupont.pdf`, ou il l'écrit) | **oui**, directement |
| Le recruteur dépose le CV dans la conversation | **le contenu est lisible, pas forcément le fichier** — le retrouver, voir ci-dessous |
| Le recruteur colle le texte du CV | **non** : il n'y a pas de document, seulement du texte |

Quand il n'y a pas de chemin, chercher le fichier avant de renoncer — il est presque toujours sur
le disque, sous un nom qui contient celui du candidat :

```bash
python3 <dossier_skill>/scripts/cv.py --find "<Prénom Nom>"
```

Le script balaie Téléchargements, Bureau, Documents et le dossier courant, et classe les
résultats : d'abord ceux dont le nom de fichier contient le plus de morceaux du nom du candidat,
puis les plus récents. Un résultat dont `jetons_du_nom_trouves` est **vide** n'a rien à voir avec
le candidat — c'est un `cv.pdf` générique ou le CV de quelqu'un d'autre.

⚠️ **Ne jamais téléverser un fichier dont aucun jeton du nom ne correspond sans le faire
confirmer par le recruteur.** Joindre le CV d'un autre candidat à une fiche est une fuite de
données, et les dossiers de téléchargement d'un recruteur sont pleins de CV. En cas de doute :
proposer les fichiers trouvés et demander lequel est le bon, ou demander le chemin.

Si le fichier reste introuvable : remplir `CV text` et **le dire** — « le texte du CV est en base,
le fichier n'a pas été retrouvé, glissez-le dans le champ CV de la fiche ». Ne pas fabriquer un
PDF à partir du texte pour avoir quelque chose à joindre : ce serait un document qui n'existe pas,
que le recruteur enverrait à une clinique en croyant transmettre le CV du candidat.

### Le texte

```bash
python3 <dossier_skill>/scripts/cv.py --extract "<chemin du CV>"
```

Le texte extrait va dans `CV text` **tel quel**. Si le script sort en code 3 (aucun extracteur
disponible, ou CV scanné en image sans couche texte), lire le fichier avec l'outil Read et le
retranscrire fidèlement — sans reformuler, sans réordonner, sans « nettoyer » : les fautes et les
abréviations du CV font partie de l'information. Si le recruteur a collé le texte directement,
c'est déjà fait : le recopier tel quel.

### La pièce jointe

Elle se pose **après** la création du record, qui lui donne son recordId :

```bash
python3 <dossier_skill>/scripts/cv.py --upload "<chemin du CV>" --record recXXXXXXXXXXXXXX
```

Exige `AIRTABLE_API_KEY` (le MCP Airtable ne sait pas écrire de pièce jointe) et plafonne à 5 Mo.
Un échec n'annule rien : la fiche et `CV text` sont déjà en place — le signaler dans le compte
rendu, dire au recruteur de glisser le fichier à la main, et continuer.

## Étape 4 — Chercher un doublon avant de créer

Sur 1000 candidats, le même vétérinaire arrive facilement deux fois (un post Facebook converti en
mars, un CV envoyé en août). Chercher **avant** d'écrire, dans cet ordre :

1. **par nom normalisé** — `fullNameSearch` (`fldkPqxhISja7S1RU`) est une formule : `Noms` en
   minuscules, diacritiques retirés. Calculer la même forme pour le nom apporté (« Réhane
   Chiron Gonnon » → `rehane chiron gonnon`) et filtrer dessus. C'est la clé qu'utilise déjà le
   garde-fou doublon de « Convert post to candidat » : les deux normalisations se rencontrent
   telles quelles.
2. **par mail** (`fldmtHKu93RMqkVw6`) et **par téléphone** (`fldZ9229oPu876Ls2`) quand la source
   en donne — un nom peut être orthographié autrement, un mail rarement.
3. **par profil Facebook** (`fldtHMm6iexTdCfEk`) quand la source est un post.

⚠️ **Un filtre Airtable dont la valeur de comparaison est vide est ignoré** : le Find records
renvoie alors toute la table. Ne jamais lancer une recherche sur une clé vide — vérifier que la
valeur cherchée existe avant de construire le filtre.

**Si un homonyme sort :** ne pas créer. Montrer au recruteur la fiche trouvée (nom, ville, école,
année de sortie, date de création, sources déjà présentes) et lui demander s'il s'agit de la même
personne. Deux personnes portent parfois le même nom — c'est son arbitrage, pas le tien.

- **Même personne** → enrichir la fiche existante (étape 5-bis), ne rien créer.
- **Homonyme réel** → créer, et le dire dans le compte rendu pour que les deux fiches ne soient
  pas fusionnées plus tard par erreur.

## Étape 5 — Créer le candidat

Présenter d'abord au recruteur, champ par champ, ce qui va être écrit, en signalant ce qui reste
vide faute d'information. **Attendre son feu vert**, sauf si le recruteur a déjà dit d'aller au
bout sans repasser par lui.

Puis `create_records_for_table` sur `tblPmkTaAjS9Yoovt`. Valeurs posées d'office :

| Champ | ID | Valeur |
|---|---|---|
| `Prénom` / `Nom` | `fld1WR6pNpe8sAya6` / `fld6yzzWrqBZBtXly` | séparés — `Noms` est une formule |
| `Emploi recherché` | `fldizV1UoejwizYSq` | `Vétérinaire`, ou `ASV` si la source le dit |
| `Statut Recherche` | `fldOijG6rapbZUqMR` | `En recherche active` — **jamais vide, voir plus bas** |
| `Pays` | `fld7Yagembu2ZPNhU` | `France` sauf indication contraire |
| `Canal de contact` | `fldoXNvz9C6zQaiK6` | `Téléphone` après un appel, `Facebook` depuis un post, `Mail` si le CV est arrivé par mail, sinon `Pas contacté` |
| `Source du candidat` | `fldVyZvVmWllrD7ZT` | l'option qui correspond, **ou vide** : la liste est fermée (voir `references/champs-candidat.md`) |
| `Sourceur` + `Ajouté au CRM par` | `fldECFOFPFdxzzFFP` / `fldq8pztsTZBa0IK4` | `{"email": "<recruteur>"}` |

⚠️ **`Statut Recherche` vide rend le candidat invisible.** Le script de matching ne retient, côté
offre, que les candidats en `En recherche active` ou `En recherche passive` ; et la routine
nocturne de nettoyage supprime les paires des candidats « pas en recherche ». Un candidat créé
sans ce champ ne sera proposé à aucune clinique et personne ne verra pourquoi. C'est le seul champ
qu'on pose même sans aucune source.

Ne jamais écrire : `Notes` (`fld0s84U1HdrHKqkg`) ni `Notes du candidat` (`fld8WaHsnucNvdEqW`),
`Profil` (`fldlnO9d1ctGABT9v`, réservé au recruteur), `candidat_key` (la clé du scrape, pas la
nôtre), `Statut IA` à ce stade, ni aucune formule ou lookup (`Noms`, `fullNameSearch`, `Echelon`,
`county`, `latitude`, les rémunérations CC…).

### La ville, si on la connaît

`Ville` (`fldgnVDSacJdlzRG9`) et `CP` (`fldjFm8KKLcFNgyNb`) déclenchent
« Localisation Candidat [create]/[update] », donc `county`, `latitude`, `longitude` — donc le
matching à la distance. Résoudre l'orthographe avant d'écrire :

```bash
python3 <dossier_skill>/scripts/ville.py "<ville>" --cp <CP si connu>
```

(après l'avoir téléchargé — voir « Ressources » en tête. S'il reste introuvable, ne pas deviner
l'orthographe : écrire `county` à la main depuis le CP et le dire dans le compte rendu.)

Traiter la sortie comme du côté clinique : orthographe reconnue → écrire `Ville` telle que
renvoyée et laisser l'automation poser `county`/`CP` ; homonyme mal choisi → écrire `county` et
`CP` à la main ; commune absente du CSV (candidat étranger) → `county` à la main, et prévenir
qu'il n'y aura pas de coordonnées.

⚠️ **`Ville` est le domicile, jamais la zone de recherche.** « Je cherche sur la Côte d'Azur » ne
dit pas où la personne habite. Une ville fausse la déplace sur la carte et fausse toutes ses
distances : dans le doute, laisser vide et compter sur `Zones de recherche`.

**Puis relire la fiche** une dizaine de secondes plus tard : l'automation est asynchrone.
`county` rempli est la preuve que le géocodage a fonctionné.

### Étape 5-bis — Si la fiche existe déjà

Ajouter la source sans jamais écraser ce qui est là :

- `Transcripts` → **concaténer** à la suite, précédé d'une ligne de date (`— appel du 31/08/26 —`).
  Le champ est fait pour accumuler les entretiens.
- `Post` → ajouter une section à la suite, séparée par une ligne `──────────`, avec un en-tête
  `[YYYY-MM-DD]` : c'est la convention que la routine d'enrichissement sait découper.
- `CV text` → si le champ est vide, écrire ; s'il est rempli, ajouter à la suite sous un en-tête
  daté. Un CV plus récent ne remplace pas l'ancien, il s'ajoute.
- Les champs structurés déjà renseignés par un humain : **ne pas les toucher**. L'étape 6 s'en
  charge selon ses propres règles.

Ne pas retoucher `Statut Recherche` d'une fiche existante sans demander : un candidat passé en
`Pas en recherche` ou `Blacklisté` l'a été pour une raison.

## Étape 6 — Enrichir, avec la doctrine du dépôt

Cette étape n'est **pas** décrite ici. Elle est décrite une seule fois, dans le prompt de la
routine « Enrichissement candidat », versionné dans le dépôt. On le télécharge et on le suit :

```bash
python3 <dossier_skill>/scripts/routine.py
```

Le script écrit le prompt sur la sortie standard (et le met en cache dans `~/.sarecrute/`).
**Lire cette sortie en entier, puis l'appliquer au record créé à l'étape 5** — c'est elle qui fait
autorité sur l'extraction des champs structurés, la cotation des actes, les zones de recherche et
la rédaction du Profil IA. Ne pas la paraphraser, ne pas la résumer, ne pas trancher un cas limite
« au bon sens » alors qu'elle le traite.

⚠️ **`routine.py` lit la branche `main`, pas `stable` — c'est voulu, ne pas le « corriger ».** La
routine cloud « Enrichissement candidat » clone `main` à chaque run : c'est donc `main` qui définit
ce qu'un enrichissement produit aujourd'hui. Pointer ce script sur `stable` ferait diverger les
deux chemins d'enrichissement, et un candidat serait enrichi différemment selon qu'il est passé par
la compétence ou par le bouton d'interface. La règle « ne jamais pointer sur `main` » s'applique au
corps de la compétence, pas à cette doctrine partagée avec un autre consommateur.

Le prompt est écrit pour un run cloud déclenché par webhook. Six adaptations, et rien d'autre :

1. **Le recordId** est celui du candidat créé à l'étape 5. Il n'y a pas de message
   `recordId:rec…` à dépouiller.
2. **`Statut IA` = « En cours »** est posé par la couche appelante dans le run cloud. Ici il n'y a
   pas de couche appelante : ne pas l'écrire.
3. **`Statut IA` en fin d'étape** : `Exécuté` si l'enrichissement a effectivement tourné sur au
   moins une source. **Laisser vide s'il n'y avait aucune source** (cas « juste un nom ») — écrire
   `Exécuté` sur une fiche que personne n'a enrichie ferait croire au recruteur que le travail est
   fait et empêcherait quiconque de le lancer plus tard.
4. **Les champs de contact** que la routine ne remplit « que si vides » sont vides par
   construction sur une fiche qu'on vient de créer : aucun conflit. Sur une fiche existante
   (étape 5-bis), sa règle s'applique telle quelle.
5. **Le compte rendu final** de la routine (lignes de compétences créées / mises à jour / gelées,
   synonymes ajoutés, actes non reconnus) se reverse dans le compte rendu de l'étape 8. Ne pas
   l'omettre : ces deux dernières lignes sont le seul canal par lequel le référentiel `Actes`
   s'améliore.
6. **`Notes` reste interdit d'écriture**, comme partout ailleurs dans cette compétence. La routine
   ne le touche pas — elle écrit les champs de contact, les champs structurés, `Zones de recherche`
   et `Profil IA` — mais si une version future du prompt venait à l'inclure, cette règle-ci prime.

Sur une fiche fraîchement créée il n'y a aucune ligne de `Compétences`, donc aucune cotation
gelée : la logique de gel de la routine ne mord qu'à l'étape 5-bis, où elle est indispensable —
une correction de recruteur gagne toujours contre une extraction automatique.

**Si le téléchargement échoue** (pas de réseau, dépôt injoignable, pas de cache) : ne pas
improviser l'enrichissement de mémoire. La fiche et ses sources sont déjà en base, ce qui est
l'essentiel. Dire au recruteur d'ouvrir la fiche dans l'interface Airtable et de lancer le bouton
**« Enrichissement candidat »** — la routine cloud fera exactement ce travail. Laisser
`Statut IA` vide.

## Étape 7 — Si le candidat vise une offre précise : pratiques, contrôle, candidature

Cette étape ne tourne que si le recruteur a **désigné une offre** (« arrivée par mail sur l'annonce
Hedera », « elle postule chez X »). Sans offre nommée, la sauter en silence : on ne devine jamais
l'offre depuis le texte d'une source. Tout le détail (IDs, grilles, valeurs) est dans
`references/candidature.md` — le lire avant d'écrire. En résumé, dans l'ordre :

1. **Retrouver l'offre** non archivée par le nom de la clinique (et `Second name`). Plusieurs
   candidates → montrer et demander laquelle, c'est la seule question de l'étape. Aucune → le dire,
   proposer `creer-clinique-offre`, et sauter le reste de l'étape.
2. **Les espèces de l'offre → la fiche.** Postuler à un poste canin, c'est dire qu'on veut faire du
   canin : c'est une déclaration du candidat. `Pratiques requises` de l'offre → `Pratiques
   requises` **et** `Pratiques maitrisées` du candidat, **seulement si vides après l'ÉTAPE 6** (les
   sources du candidat priment, et une requise de plus exclut) ; `Pratiques optionnelles` de
   l'offre → `Pratiques optionnelles` du candidat, en ajout. Recopie 1 pour 1, vocabulaires
   identiques. ⚠️ **Espèces seulement** : ni les spécialités ni les actes de l'offre ne passent sur
   le candidat — ce qu'une clinique propose ne dit rien de ce qu'un candidat sait faire, c'est le
   « plateau technique » de la doctrine sous une autre forme.
3. **Ce que dirait le matching** — trois contrôles : `Expérience` du candidat contre `Expérience
   requise` (vide côté candidat = Débutant), double inclusion des pratiques, `county` de l'offre
   contre les zones ou la ville du candidat. Aucun n'est bloquant : le recruteur a décidé de
   présenter. Mais chaque écart est un ⚠️ dans le récapitulatif avant feu vert et dans le compte
   rendu — « 1 an d'expérience pour une offre qui demande 1 à 2 ans » est exactement ce que le
   recruteur veut voir avant de présenter.
4. **Créer la candidature**, après avoir vérifié qu'il n'en existe pas déjà une pour ce couple
   candidat × offre : `Candidat`, `Offre d'emploi`, `Propriétaire` = le recruteur de l'ÉTAPE 1,
   `Statut candidature`, `Prochaine action` et sa date selon la grille de `candidature.md` (le
   candidat a postulé lui-même → `Candidat postulé` / `Proposer le candidat à la clinique` /
   aujourd'hui). Le statut retenu s'affiche dans le récapitulatif avant feu vert, le recruteur le
   change en un mot ; pas de question séparée. Sur `En attente 1er retour candidat`, ne pas écrire
   la prochaine action : l'automation « Set 1ère relance » la pose. Jamais de `Notes`.
5. **Archiver la paire** de `Potentielles candidatures` pour ce couple si elle existe, sinon la
   même personne serait proposée deux fois.

## Étape 8 — Lancer le matching

Le rapprochement n'est pas automatique à la création. Dire au recruteur d'ouvrir la fiche du
candidat dans l'interface Airtable et de lancer le bouton de création des valeurs potentielles
(automation `Create potential values [InterfaceCandidat]`) pour confronter le candidat aux offres
ouvertes. À défaut, la routine nocturne de 3 h le fera, puisqu'elle balaie les candidats créés ou
modifiés dans les 24 h.

Si rien ne sort, reprendre `references/champs-candidat.md` dans l'ordre de la colonne « effet sur
le matching » : c'est presque toujours `Statut Recherche` vide, une pratique de trop en
« requises », ou aucune `Zone de recherche` sur un candidat sans ville.

## Étape 9 — Compte rendu

- la **version** de ce PROMPT.md, annoncée dès le début du run ;
- au nom de quel recruteur on a travaillé, et d'où vient cette identité (ÉTAPE 1) ;
- le candidat créé (ou la fiche existante enrichie), avec son recordId ;
- les sources déposées et où (`CV text` + pièce jointe, `Post`, `Transcripts`) ;
- `county` / coordonnées obtenus, ou le problème restant ;
- ce que l'enrichissement a produit : le compte rendu de la routine, tel qu'elle le formule ;
- si une offre était visée (ÉTAPE 7) : l'offre retrouvée, les pratiques posées depuis elle, les
  trois contrôles avec leurs ⚠️, la candidature créée (recordId, statut, prochaine action) ou
  celle qui existait déjà ;
- **les champs laissés vides faute d'information** — c'est la liste que le recruteur complétera
  après son premier appel ;
- le rappel de lancer le matching depuis l'interface.

## Pièges connus

- **`typecast` jamais.** Il créerait des valeurs de select parasites. Une écriture qui échoue sur
  une valeur inconnue est le comportement voulu.
- **Le MCP Airtable et les noms de champs accentués** : passer par les **IDs** (`fldXXX`) en
  lecture comme en écriture, y compris dans `fieldIds` et `sort` (qui attend `fieldId`, pas
  `field`). Il n'accepte pas `filterByFormula` — utiliser l'objet `filters` structuré, ni
  `maxRecords` — utiliser `pageSize`.
- **`Expérience` et `Années d'expérience` sont deux champs distincts.** `Expérience` (sélection
  unique) est le seul lu par le matching, et **vide y vaut « Débutant »**, donc exclusion des
  offres qui demandent mieux. `Années d'expérience` ne pilote que l'échelon et la rémunération
  convention collective. Quand une durée chiffrée existe, `Expérience` suit la grille de la base
  (moins d'un an → Débutant, 1 ou 2 ans → `1 à 2 ans`, 3 et plus → Autonome) : « exerce depuis un
  an » est `1 à 2 ans`, pas Débutant. L'automation « Expérience depuis les années d'expérience »
  l'imposerait de toute façon dès que le nombre d'années est écrit. Ne jamais déduire ni l'un ni
  l'autre de l'année de sortie.
- **Ne pas écrire `Régions de recherche`.** Ce champ de lien déclenche l'automation
  « Update Zones de Recherche (Candidat) », qui réécrit `Zones de recherche`. Écrire directement
  `Zones de recherche` (`fldacGQbzpkx88ULc`), comme le fait la routine.
- **`acceptable_distance_from_home (km)` n'est lu que depuis l'offre.** Quand le matching part de
  la fiche candidat, le script retombe sur 50 km en dur : élargir le rayon d'un candidat n'a
  d'effet que sur les rapprochements lancés depuis une offre ou par la nocturne côté offre. La
  vraie soupape, côté candidat, c'est `Zones de recherche`.
- **Dans le doute, la valeur la moins restrictive.** Un champ deviné exclut le candidat des offres
  en silence ; un champ vide est permissif partout sauf `Expérience` et `Statut Recherche`. Mieux
  vaut un match que le recruteur écarte qu'un poste que le candidat ne verra jamais.
- **Ne pas cocher `Contrat court`** sans que la source le dise : c'est un critère d'éligibilité du
  matching nocturne, pas un attribut décoratif.
