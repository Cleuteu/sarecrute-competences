---
name: creer-cv-candidat
description: >-
  Monte le « dossier de présentation candidat » A4 à la charte SaRecrute d'un vétérinaire du
  vivier Airtable, et analyse/score le vivier selon une grille de recruteur expert. Compétence à
  invocation manuelle : elle ne se déclenche que sur appel explicite.
disable-model-invocation: true
---

# Créer le CV / dossier de présentation d'un candidat

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`**, fichier par fichier depuis
`raw.githubusercontent.com`, en suivant le `MANIFEST` de la compétence (PROMPT.md et assets y sont
listés avec la version qu'ils partagent) :

```bash
SKILL="creer-cv-candidat"
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
du tarball, puisque `raw` sert chaque fichier séparément.

Ne jamais réutiliser le dossier d'une exécution précédente : un mélange ancien/nouveau serait
pire qu'une copie périmée.

**2. Si le téléchargement échoue** (une ligne `ÉCHEC` : réseau, 404 sur le `MANIFEST` ou sur un fichier, `PROMPT.md` absent de `$DEST`, ou version du `PROMPT.md` différente de celle du `MANIFEST` — ce dernier cas est un déploiement en cours de propagation sur `raw`, réessayer cinq minutes plus tard) :
**ARRÊTE.** Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire — surtout pas en reconstruisant le template A4 :
un dossier qui part chez une clinique cliente avec une mise en page approximative abîme la marque
plus sûrement que l'absence de dossier.

Puis, sans demander de diagnostic à l'utilisateur :

- si son message de lancement contient `debug`, afficher la sortie complète du bloc ci-dessus et
  s'arrêter là ;
- sinon, lui dire en deux lignes que la compétence n'a pas pu démarrer et qu'un mail pour Alex est
  prêt dans ses brouillons Gmail, à envoyer tel quel. Créer ce brouillon avec `create_draft` du
  connecteur Gmail, **sans l'envoyer** : `to` `alex@botyglot.com`, `subject`
  `[SaRecrute] Échec creer-cv-candidat (snapshot) — <JJ/MM/AAAA HH:MM>`, corps = la ligne `ÉCHEC` exacte, la
  sortie complète du bloc de téléchargement, et ce que l'utilisateur avait demandé. Sans connecteur
  Gmail, afficher ce corps dans un bloc de code précédé de « À envoyer à alex@botyglot.com ».

La procédure complète (ce qui compte comme incident, le modèle du mail) vit dans le snapshot
lui-même, `references/compte-rendu.md`, qu'on n'a justement pas pu lire : cette version courte
suffit.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer — une seule ligne, `creer-cv-candidat <version>`, rien d'autre : ce qui
s'écrit ensuite est réglé par `$DEST/references/compte-rendu.md`, que le corps applique.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>`, « le dossier de la compétence » ou des chemins relatifs `assets/…`,
c'est `$DEST`. Le template `assets/cv-template.html` s'y copie et s'y découpe : il ne se relit pas
en entier. Ce que l'utilisateur a demandé (analyse du vivier, dossier d'un candidat nommé, ou
modèle vierge) s'applique tel quel.
