---
name: creer-candidat
description: >-
  Crée un candidat vétérinaire dans l'Airtable de recrutement (base prod « Recrutement
  vétérinaire ») à partir de ce que le recruteur a sous la main — un CV, une annonce de recherche
  copiée-collée, le transcript d'un appel téléphonique, ou simplement un nom et un prénom — puis
  l'enrichit (champs structurés, Profil IA, grille de compétences par acte) avec la doctrine de la
  routine « Enrichissement candidat », lue en ligne dans le dépôt plutôt que recopiée. Se
  déclenche quand l'utilisateur demande de « créer un candidat », « ajouter ce vétérinaire au
  vivier », « rentrer ce CV », « enregistrer ce candidat », « nouveau candidat », colle le
  transcript d'un appel candidat ou l'annonce d'un vétérinaire qui cherche un poste, ou
  formulation équivalente.
---

# Créer un candidat

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`**, fichier par fichier depuis
`raw.githubusercontent.com`, en suivant le `MANIFEST` de la compétence (PROMPT.md, scripts et
références y sont listés avec la version qu'ils partagent) :

```bash
SKILL="creer-candidat"
BASE="https://raw.githubusercontent.com/Cleuteu/sarecrute-competences/stable/remote-skills/$SKILL"
DEST="$(mktemp -d)/$SKILL-remote"   # toujours un dossier neuf : jamais de mélange ancien/nouveau
mkdir -p "$DEST"
if curl -fsSL "$BASE/MANIFEST" -o "$DEST/MANIFEST"; then
  for f in $(grep -v '^version=' "$DEST/MANIFEST"); do
    mkdir -p "$DEST/$(dirname "$f")" && curl -fsSL "$BASE/$f" -o "$DEST/$f" \
      || { echo "ÉCHEC : $f"; touch "$DEST/.echec"; break; }
  done
  V=$(sed -n 's/^version=//p' "$DEST/MANIFEST")
  [ ! -e "$DEST/.echec" ] && head -1 "$DEST/PROMPT.md" | grep -qF "version $V " \
    && echo "snapshot $SKILL $V dans $DEST" || echo "ÉCHEC : snapshot incomplet ou versions différentes"
else echo "ÉCHEC : MANIFEST introuvable"; fi
```

Pourquoi pas le tarball `github.com/…/archive/…` : depuis Cowork, `github.com` est filtré par le
proxy de sortie (403 « access to this repository is not enabled for this session ») alors que
`raw.githubusercontent.com` passe. Le `MANIFEST` remplace l'archive ; la comparaison de version
entre le `MANIFEST` et la première ligne du `PROMPT.md` remplace la garantie « un seul commit »
du tarball, puisque `raw` sert chaque fichier séparément. Les scripts `.sh` du snapshot n'ont pas
de bit exécutable : les lancer par `bash <chemin>`.

Ne jamais réutiliser le dossier d'une exécution précédente : un mélange ancien/nouveau serait
pire qu'une copie périmée.

**2. Si le téléchargement échoue** (une ligne `ÉCHEC` : réseau, 404 sur le `MANIFEST` ou sur un fichier, `PROMPT.md` absent de `$DEST`, ou version du `PROMPT.md` différente de celle du `MANIFEST` — ce dernier cas est un déploiement en cours de propagation sur `raw`, réessayer cinq minutes plus tard) :
**ARRÊTE.** Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire — créer un candidat à moitié, avec des champs
devinés, coûte plus cher que ne pas le créer.

Puis, sans demander de diagnostic à l'utilisateur :

- si son message de lancement contient `debug`, afficher la sortie complète du bloc ci-dessus et
  s'arrêter là ;
- sinon, lui dire en deux lignes que la compétence n'a pas pu démarrer et qu'un mail pour Alex est
  prêt dans ses brouillons Gmail, à envoyer tel quel. Créer ce brouillon avec `create_draft` du
  connecteur Gmail, **sans l'envoyer** : `to` `alex@botyglot.com`, `subject`
  `[SaRecrute] Échec creer-candidat (snapshot) — <JJ/MM/AAAA HH:MM>`, corps = la ligne `ÉCHEC` exacte, la
  sortie complète du bloc de téléchargement, et ce que l'utilisateur avait demandé. Sans connecteur
  Gmail, afficher ce corps dans un bloc de code précédé de « À envoyer à alex@botyglot.com ».

La procédure complète (ce qui compte comme incident, le modèle du mail) vit dans le snapshot
lui-même, `references/compte-rendu.md`, qu'on n'a justement pas pu lire : cette version courte
suffit.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer — une seule ligne, `creer-candidat <version>`, rien d'autre : ce qui
s'écrit ensuite est réglé par `$DEST/references/compte-rendu.md`, que le corps applique.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>`, « le dossier de la compétence » ou des chemins relatifs
`scripts/…` / `references/…`, c'est `$DEST`. Ce que l'utilisateur a fourni (CV, annonce collée,
transcript, ou seulement un nom) s'applique tel quel.
