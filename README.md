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

## Ce qu'il faut avoir branché

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

## Pour qui maintient ce dépôt

Ce dépôt est la **source de vérité** des compétences distribuées aux recruteurs. Toute correction
se fait ici, puis :

```bash
claude plugin validate .                       # manifeste marketplace
claude plugin validate plugins/sarecrute-recruteur
```

Penser à monter `version` dans `plugins/sarecrute-recruteur/.claude-plugin/plugin.json` **et**
dans `.claude-plugin/marketplace.json` — les deux doivent rester d'accord — puis prévenir les
recruteurs qu'il y a une mise à jour à tirer.

Ce dépôt est public : il décrit des workflows et la structure d'une base Airtable, il ne contient
**aucun identifiant, jeton, coordonnée personnelle ni donnée de candidat ou de clinique**. Ne rien
y ajouter de tel — les clés d'API vivent dans l'environnement local de chaque poste, les identités
des recruteurs dans `~/.sarecrute/recruteur.json`.
