# Compétences Claude Code — SaRecrute

Marketplace de plugins Claude Code de SaRecrute (recrutement vétérinaire). Elle contient **deux
plugins indépendants** : on n'installe que celui dont on a besoin.

| Plugin | Pour qui | Compétences |
|---|---|---|
| `sarecrute-recruteur` | les recruteurs, au quotidien | `creer-clinique-offre`, `creer-brouillons-facebook` |
| `sarecrute-admin` | le poste d'administration | `scrape-veto` |

## Installation — recruteurs

Dans un terminal, une fois :

```bash
claude plugin marketplace add Cleuteu/sarecrute-competences
claude plugin install sarecrute-recruteur@sarecrute
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
claude plugin update sarecrute-recruteur
```

À relancer quand une correction est annoncée. Redémarrer Claude Code ensuite.

## Ce que contient le plugin `sarecrute-recruteur`

| Compétence | Ce qu'elle fait | On la déclenche en disant… |
|---|---|---|
| `creer-clinique-offre` | à partir d'une annonce collée dans Claude : crée la clinique et l'offre d'emploi dans Airtable, puis prépare le premier contact (brouillon Gmail, ou message Messenger à copier) | « crée la clinique et l'offre », ou simplement en collant l'annonce |
| `creer-brouillons-facebook` | prépare un brouillon de publication Facebook par canal pour les publications du jour, texte + image, **sans publier** | « prépare les brouillons Facebook », « les publications du jour » |

Aucune des deux n'envoie ni ne publie quoi que ce soit : elles préparent, le recruteur relit et
clique.

### Ce qu'il faut avoir branché

Les compétences s'appuient sur les connecteurs du compte Claude de chaque recruteur :

- **Airtable** — les deux compétences ;
- **Gmail** — pour le brouillon de premier contact (`creer-clinique-offre`) ;
- **Google Drive** + **Claude in Chrome** — pour les visuels et les onglets Facebook
  (`creer-brouillons-facebook`).

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
claude plugin install sarecrute-admin@sarecrute
```

| Compétence | Ce qu'elle fait | On la déclenche en disant… |
|---|---|---|
| `scrape-veto` | parcourt le groupe Facebook vétérinaire sur une fenêtre de temps (6 h par défaut), en tire les posts et les commentaires utiles, et les pousse dans la table « Posts scrappés » sans créer de doublon | « scrape les posts véto », « scrape veto 48h », « les posts d'aujourd'hui » |

Elle ne publie ni n'envoie rien sur Facebook : elle lit le groupe et écrit dans Airtable. Ses
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

```bash
claude plugin validate .                       # manifeste marketplace
claude plugin validate plugins/sarecrute-recruteur
claude plugin validate plugins/sarecrute-admin
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
