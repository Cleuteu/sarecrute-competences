# Compétences Claude Code — SaRecrute

Marketplace de plugins Claude Code pour les recruteurs SaRecrute (recrutement vétérinaire).

## Installation

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
| `scrape-veto` | parcourt le groupe Facebook vétérinaire sur une fenêtre de temps (6 h par défaut), en tire les posts et les commentaires utiles, et les pousse dans la table « Posts scrappés » sans créer de doublon | « scrape les posts véto », « scrape veto 48h », « les posts d'aujourd'hui » |

Aucune ne publie ni n'envoie quoi que ce soit sur Facebook : les deux premières préparent, le
recruteur relit et clique ; `scrape-veto` ne fait que lire le groupe et écrire dans Airtable.

## Ce qu'il faut avoir branché

Les compétences s'appuient sur les connecteurs du compte Claude de chaque recruteur :

- **Airtable** — `creer-clinique-offre` et `creer-brouillons-facebook` ;
- **Gmail** — pour le brouillon de premier contact (`creer-clinique-offre`) ;
- **Google Drive** + **Claude in Chrome** — pour les visuels et les onglets Facebook
  (`creer-brouillons-facebook`).

`scrape-veto` a des exigences à part, plus techniques que les deux autres :

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

En pratique, c'est la compétence d'un poste d'administration plutôt que d'un poste de recrutement
au quotidien.

Chaque recruteur travaille sous sa propre identité, lue dans `~/.sarecrute/recruteur.json`
(`%USERPROFILE%\.sarecrute\recruteur.json` sous Windows) :

```json
{ "responsable": "Prénom Nom", "email": "prenom@exemple.fr" }
```

Ce fichier est **local à la machine** : il n'est pas versionné et ne doit pas être partagé. Les
compétences le créent au premier lancement si besoin, en demandant qui utilise le poste.

## Pour qui maintient ce dépôt

Ce dépôt est la **source de vérité** des compétences distribuées aux recruteurs. Toute correction
se fait ici, puis :

```bash
claude plugin validate .                       # manifeste marketplace
claude plugin validate plugins/sarecrute-recruteur
```

**Toute correction exige de monter `version`**, dans
`plugins/sarecrute-recruteur/.claude-plugin/plugin.json` **et** dans
`.claude-plugin/marketplace.json` — les deux doivent rester d'accord. Sans ce changement de
numéro, `claude plugin update` répond « already at the latest version » et ne tire rien : le
correctif reste sur GitHub et personne ne l'a. Prévenir ensuite les recruteurs qu'il y a une mise
à jour à tirer.

Ne pas coder de chemin en dur dans un `SKILL.md` : le plugin s'installe sous
`~/.claude/plugins/cache/sarecrute/sarecrute-recruteur/<version>/skills/…`, dossier qui change à
chaque publication. Les ressources bundlées se désignent relativement au dossier de la
compétence (`scripts/…`, `references/…`).

Ce dépôt est public : il décrit des workflows et la structure d'une base Airtable, il ne contient
**aucun identifiant, jeton, coordonnée (e-mail, téléphone) ni donnée de candidat ou de clinique**.
Ne rien y ajouter de tel — les clés d'API vivent dans l'environnement local de chaque poste, les
identités des recruteurs dans `~/.sarecrute/recruteur.json`.

Seule exception assumée : `skills/scrape-veto/references/auteurs_exclus.json` nomme les auteurs dont
les publications ne doivent jamais être collectées, dont les recruteuses elles-mêmes. Des noms, rien
d'autre — pas de coordonnées.
