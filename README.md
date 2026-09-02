# Compétences Claude Code — SaRecrute

Marketplace de plugins Claude Code de SaRecrute (recrutement vétérinaire). Elle contient **deux
plugins indépendants** : on n'installe que celui dont on a besoin.

| Plugin | Pour qui | Compétences |
|---|---|---|
| `sarecrute-recruteur` | les recruteurs, au quotidien | `creer-clinique-offre`, `creer-candidat`, `dossier-candidat`, `creer-brouillons-facebook` |
| `sarecrute-admin` | le poste d'administration | `scrape-veto`, `maj-offres` |

## Installation — recruteurs

Dans un terminal, une fois :

```bash
claude plugin marketplace add Cleuteu/sarecrute-competences
claude plugin install sarecrute-recruteur@sarecrute-competences
```

Puis redémarrer Claude Code. Les compétences se déclenchent d'elles-mêmes quand la demande
correspond ; il n'y a pas de commande à retenir.

**Si tu préfères que Claude s'en occupe** — y compris la vérification des connecteurs et des
réglages système — donne-lui simplement ce lien et laisse-le dérouler :

```
https://raw.githubusercontent.com/Cleuteu/sarecrute-competences/main/ONBOARDING.md
```

C'est le guide [ONBOARDING.md](ONBOARDING.md) de ce dépôt. Aucun compte n'est nécessaire pour
l'ouvrir.

## Mise à jour

```bash
claude plugin update sarecrute-recruteur@sarecrute-competences
```

À relancer quand une correction est annoncée. Redémarrer Claude Code ensuite.

## Ce que contient le plugin `sarecrute-recruteur`

| Compétence | Ce qu'elle fait | On la déclenche en disant… |
|---|---|---|
| `creer-clinique-offre` | à partir d'une annonce collée dans Claude : crée la clinique et l'offre d'emploi dans Airtable, puis prépare le premier contact (brouillon Gmail, ou message Messenger à copier) | « crée la clinique et l'offre », ou simplement en collant l'annonce |
| `creer-candidat` | crée un candidat vétérinaire dans Airtable à partir d'un CV, d'une annonce de recherche, du transcript d'un appel ou d'un simple nom, puis enrichit sa fiche | « crée un candidat », « rentre ce CV », « ajoute-le au vivier » |
| `dossier-candidat` | analyse et score le vivier, et monte le **dossier de présentation A4** d'un candidat à la charte SaRecrute, à partir des seuls champs Airtable vérifiés | « fais le dossier de Margot », « sors-moi les bons profils », « montre-moi le modèle » |
| `creer-brouillons-facebook` | prépare un brouillon de publication Facebook par canal pour les publications du jour, texte + image, **sans publier** | « prépare les brouillons Facebook », « les publications du jour » |

Aucune n'envoie ni ne publie quoi que ce soit : elles préparent, le recruteur relit et
clique.

### Ce qu'il faut avoir branché

Les compétences s'appuient sur les connecteurs du compte Claude de chaque recruteur :

- **Airtable** — les quatre compétences du plugin recruteur ;
- **Gmail** — pour le brouillon de premier contact (`creer-clinique-offre`) ;
- **Google Drive** + **Claude in Chrome** — pour les visuels et les onglets Facebook
  (`creer-brouillons-facebook`) ;
- **Chrome installé sur le poste** — pour l'export PDF du dossier A4 (`dossier-candidat`) : rien à
  brancher côté Claude, c'est le navigateur local qui imprime.

Chaque recruteur travaille sous sa propre identité, lue dans `~/.sarecrute/recruteur.json`
(`%USERPROFILE%\.sarecrute\recruteur.json` sous Windows) :

```json
{ "responsable": "Prénom Nom", "email": "prenom@exemple.fr" }
```

Ce fichier est **local à la machine** : il n'est pas versionné et ne doit pas être partagé. Les
compétences le créent au premier lancement si besoin, en demandant qui utilise le poste.

## Ce que contient le plugin `sarecrute-admin`

À installer **uniquement sur le poste d'administration** — ce n'est pas un outil de recrutement au
quotidien, et il n'a pas sa place dans l'onboarding d'un recruteur :

```bash
claude plugin install sarecrute-admin@sarecrute-competences
```

| Compétence | Ce qu'elle fait | On la déclenche en disant… |
|---|---|---|
| `scrape-veto` | parcourt le groupe Facebook vétérinaire sur une fenêtre de temps (6 h par défaut), en tire les posts et les commentaires utiles, et les pousse dans la table « Posts scrappés » sans créer de doublon | « scrape les posts véto », « scrape veto 48h », « les posts d'aujourd'hui » |
| `maj-offres` | synchronise les offres publiées sur le site vitrine (page des offres + carousel de l'accueil) avec l'Airtable de prod : retire les offres archivées ou dont la clinique n'est plus « Signé », ajoute les nouvelles, rédige leurs descriptions **anonymisées** et pose le tag « Nouvelle offre » | « mets à jour les offres », « maj offres », « il y a une nouvelle offre » |

`maj-offres` écrit dans les fichiers du site, jamais dans Airtable, et **ne déploie qu'avec un accord
explicite**. Elle se lance depuis le dossier du site (ou avec `SARECRUTE_SITE` pointant dessus) et
travaille dans `~/.sarecrute/maj-offres/work/` : rien n'est écrit dans le dossier du plugin, qui est
réécrit à chaque mise à jour. Un garde-fou bloquant refuse toute description contenant un nom de
clinique, de ville ou de personne — la localisation publiée s'arrête au département.

`scrape-veto` ne publie ni n'envoie rien sur Facebook : elle lit le groupe et écrit dans Airtable. Ses
exigences sont plus techniques que celles du plugin recruteur :

- **Claude in Chrome** obligatoire — elle travaille dans le Chrome réel, où la session Facebook est
  déjà ouverte (le navigateur intégré est déconnecté de Facebook, le scrape y est impossible) ;
- **une clé d'API Airtable dans l'environnement du poste** (`AIRTABLE_API_KEY`) : l'écriture passe
  par `curl`, pas par le connecteur Airtable, parce que Facebook bloque les requêtes sortantes
  depuis sa page. Sur macOS/Linux la compétence relit la clé du shell ; ailleurs elle la demande.
  La clé ne doit jamais atterrir dans ce dépôt ;
- **`python3`** disponible sur le poste (pour `scripts/airtable_push.py`).

À savoir : Facebook cesse de charger dès que sa fenêtre Chrome passe en arrière-plan (Chrome y
suspend le rendu). La compétence le détecte et **ramène la fenêtre Chrome au premier plan
elle-même** pour repartir — elle va donc s'installer devant ce que tu fais pendant la collecte.
Sous Windows elle ne peut que réactiver la fenêtre, pas choisir l'onglet : si l'onglet du groupe
n'est pas l'onglet actif, elle demande de cliquer dessus.

## Pour qui maintient ce dépôt

Ce dépôt est la **source de vérité** des compétences distribuées. Toute correction se fait ici,
puis :

### Compétences « distantes » : toutes, depuis le 01/09/2026

Les **six compétences** des deux plugins n'embarquent plus leurs instructions dans le plugin : le `SKILL.md` installé est
un **stub** qui télécharge à chaque exécution un snapshot de
[`remote-skills/<compétence>/`](remote-skills/) (PROMPT.md + scripts + références) depuis la
**branche `stable`** de ce dépôt. Conséquences :

- **Corriger le prompt ou les scripts** : éditer `remote-skills/<compétence>/` sur `main`, monter
  la ligne de version en tête de `PROMPT.md`, régénérer les manifests (`python3 tools/manifests.py`),
  puis déployer en avançant la branche : `git push origin main:stable`. **Aucun bump de plugin,
  aucun `plugin update` chez personne** — la prochaine exécution tire la nouvelle version toute
  seule (l'exécution l'annonce, c'est la trace de ce qui a réellement tourné).
- **Le téléchargement passe par `raw.githubusercontent.com`, fichier par fichier**, guidé par le
  `MANIFEST` de chaque compétence (depuis le 02/09/2026). Le tarball `github.com/…/archive/…`
  utilisé avant est filtré par le proxy de sortie de Cowork (403 « access to this repository is
  not enabled for this session ») : les trois compétences recruteur y étaient inutilisables. Le
  `MANIFEST` porte la version du `PROMPT.md` ; le stub compare les deux après téléchargement,
  puisque `raw` ne garantit pas qu'un snapshot vienne d'un seul commit. **Un fichier ajouté à
  `remote-skills/` qui n'est pas dans le `MANIFEST` n'arrive pas chez l'utilisateur** — d'où le
  `python3 tools/manifests.py --check` des tests. Compter jusqu'à cinq minutes de cache côté `raw`
  après un push sur `stable`.
- `stable` est le cran de sûreté : on peut pousser sur `main` sans déployer. Ne jamais faire
  pointer le stub sur `main`.
- En cas d'échec de téléchargement, le stub **s'arrête** — pas de repli sur une copie locale.
  C'est voulu (même doctrine que la blacklist) : ne pas le « réparer ».
- Le paragraphe sur les versions ci-dessous ne concerne plus ces compétences que si l'on touche au
  **stub lui-même** ou à son frontmatter (`description`, déclenchement) — là, bump + republish +
  `plugin update` restent nécessaires. C'est le cas d'une compétence **nouvelle** : son stub doit
  arriver chez l'utilisateur une première fois, donc bump + republish + `plugin update`, **puis**
  `git push origin main:stable` pour que le corps existe. Les deux sont nécessaires.
- `creer-candidat` a une dépendance de plus : son `scripts/routine.py` télécharge la doctrine
  d'enrichissement depuis `routines/profil-ia-candidat.md` sur **`main`**, délibérément — c'est la
  branche que clone la routine cloud, et les deux chemins d'enrichissement doivent rester
  identiques. Et son `ville.py` est tiré du snapshot de `creer-clinique-offre`
  (`remote-skills/creer-clinique-offre/scripts/ville.py`, branche `stable`) : une seule copie,
  partagée par les deux compétences.

```bash
claude plugin validate .                       # manifeste marketplace
claude plugin validate plugins/sarecrute-recruteur
claude plugin validate plugins/sarecrute-admin
```

Les fixes de `scrape-veto` qui ont été **silencieux** (données fausses sans erreur) sont épinglés
par des tests, hors de `plugins/` pour ne rien embarquer chez les recruteurs — voir
[tests/README.md](tests/README.md) :

```bash
node tests/troncature.test.mjs
npm i --no-save jsdom@22 && node tests/attribution_commentaires.test.js
```

**Toute correction exige de monter `version`**, dans le `plugin.json` du plugin touché **et** dans
son entrée de `.claude-plugin/marketplace.json` — les deux doivent rester d'accord. Sans ce
changement de numéro, `claude plugin update` répond « already at the latest version » et ne tire
rien : le correctif reste sur GitHub et personne ne l'a. Prévenir ensuite les intéressés qu'il y a
une mise à jour à tirer.

⚠️ **Un numéro de version ne redescend jamais**, même quand la nouveauté est un retrait : un poste
déjà en 0.2.1 ne tirerait pas une 0.1.3 et garderait ce qu'on voulait lui enlever. C'est pourquoi
`sarecrute-recruteur` est passé en 0.3.0 en perdant `scrape-veto`, et non en 0.1.3.

**Une compétence n'est pas cachable dans un plugin** : `marketplace.json` n'a pas de réglage de
visibilité, et tout ce qu'un plugin embarque part avec lui. Le seul cloisonnement possible est
celui-ci — un plugin par public, chacun n'installant que le sien.

Ne pas coder de chemin en dur dans un `SKILL.md` : un plugin s'installe sous
`~/.claude/plugins/cache/sarecrute/<plugin>/<version>/skills/…`, dossier qui change à chaque
publication. Les ressources bundlées se désignent relativement au dossier de la compétence
(`scripts/…`, `references/…`).

Ce dépôt est public : il décrit des workflows et la structure d'une base Airtable, il ne contient
**aucun identifiant, jeton, coordonnée (e-mail, téléphone) ni donnée de candidat ou de clinique**.
Ne rien y ajouter de tel — les clés d'API vivent dans l'environnement local de chaque poste, les
identités des recruteurs dans `~/.sarecrute/recruteur.json`.

Seule exception assumée : `plugins/sarecrute-admin/skills/scrape-veto/references/auteurs_exclus.json`
nomme les auteurs dont les publications ne doivent jamais être collectées, dont les recruteuses
elles-mêmes. Des noms, rien d'autre — pas de coordonnées.
