---
name: insta-follow-veto
description: S'abonne en série aux profils Instagram du vivier SaRecrute partagé sur Drive, en pilotant le Chrome de l'utilisateur, et tient à jour la liste d'abonnements de la recruteuse pour ne jamais réapprocher deux fois la même personne. Compétence à invocation manuelle : elle ne se déclenche que sur appel explicite.
disable-model-invocation: true
---

# S'abonner en série aux profils Instagram du vivier

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`**, fichier par fichier depuis
`raw.githubusercontent.com`, en suivant le `MANIFEST` de la compétence (PROMPT.md et assets y sont
listés avec la version qu'ils partagent) :

```bash
SKILL="insta-follow-veto"
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
**ARRÊTE.** Explique ce qui a échoué à l'utilisateur. Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire : un abonnement part instantanément, notifie une vraie personne et ne s'annule pas.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>` ou « le dossier de la compétence », c'est `$DEST`. Ce que
l'utilisateur a demandé s'applique tel quel.
