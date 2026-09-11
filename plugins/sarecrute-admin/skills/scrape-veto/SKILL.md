---
name: scrape-veto
description: Scrape les posts des groupes Facebook vétérinaires cochés « Scraper les posts » dans Airtable (fenêtre temporelle paramétrable, 6h par défaut) + commentaires pertinents, et pousse tout dans "Posts scrappés" en déduplicant, chaque entrée rattachée à son canal. Args possibles ex. "aujourd'hui", "48h", "2 derniers jours", ou le nom d'un groupe pour n'en faire qu'un.
---

# Scrape Veto

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`** par `git clone` du dépôt (un clone = un
commit, 1,6 Mo) et prends-y `remote-skills/$SKILL/` ; si git est refusé, deuxième essai fichier
par fichier depuis `raw.githubusercontent.com`, en suivant le `MANIFEST` de la compétence :

```bash
SKILL="scrape-veto"
REPO="https://github.com/Cleuteu/sarecrute-competences"
BASE="https://raw.githubusercontent.com/Cleuteu/sarecrute-competences/stable/remote-skills/$SKILL"
TMP="$(mktemp -d)"; DEST="$TMP/$SKILL-remote"   # toujours un dossier neuf : jamais de mélange ancien/nouveau
if GIT_TERMINAL_PROMPT=0 git clone -q --depth 1 --branch stable "$REPO" "$TMP/repo" 2>"$TMP/git.err"; then
  if [ -f "$TMP/repo/remote-skills/$SKILL/PROMPT.md" ]; then
    mv "$TMP/repo/remote-skills/$SKILL" "$DEST"
    echo "snapshot $SKILL $(sed -n 's/^version=//p' "$DEST/MANIFEST") (git $(git -C "$TMP/repo" rev-parse --short HEAD)) dans $DEST"
  else echo "ÉCHEC : $SKILL absent de remote-skills sur stable"; fi
else
  echo "git clone refusé ($(tr '\n' ' ' <"$TMP/git.err" | cut -c1-200)) — deuxième essai par raw"
  mkdir -p "$DEST"
  if curl -fsSL "$BASE/MANIFEST" -o "$DEST/MANIFEST"; then
    for f in $(grep -v '^version=' "$DEST/MANIFEST"); do
      mkdir -p "$DEST/$(dirname "$f")" && curl -fsSL "$BASE/$f" -o "$DEST/$f" \
        || { echo "ÉCHEC : $f"; touch "$DEST/.echec"; break; }
    done
    V=$(sed -n 's/^version=//p' "$DEST/MANIFEST")
    [ ! -e "$DEST/.echec" ] && head -1 "$DEST/PROMPT.md" | grep -qF "version $V " \
      && echo "snapshot $SKILL $V (raw) dans $DEST" || echo "ÉCHEC : snapshot incomplet ou versions différentes"
  else echo "ÉCHEC : MANIFEST introuvable"; fi
fi
```

Pourquoi git d'abord : dans Cowork, le trafic `git` vers `github.com` passe par le **proxy GitHub
dédié** de la sandbox, indépendant de la liste des domaines autorisés, alors que les requêtes HTTP
brutes (`raw.githubusercontent.com`, mais aussi npm et PyPI) ont été coupées par le proxy de sortie
les 01/09, 10/09 et 11/09/2026 — chez toutes les recruteuses à la fois, quel que soit le réglage de
leur compte. Le tarball `github.com/…/archive/…` est lui aussi refusé (403 « access to this
repository is not enabled for this session ») : seul `git` emprunte le bon chemin. `raw` reste en
deuxième essai ; le `MANIFEST` et la comparaison de version entre lui et la première ligne du
`PROMPT.md` ne servent qu'à ce chemin-là, puisque `raw` sert chaque fichier séparément. Par `raw`, les
scripts `.sh` du snapshot n'ont pas de bit exécutable : toujours les lancer par `bash <chemin>`.

Ne jamais réutiliser le dossier d'une exécution précédente : un mélange ancien/nouveau serait
pire qu'une copie périmée.

**2. Si le téléchargement échoue** (git puis raw refusés — une ligne `ÉCHEC` : réseau, 404 sur le `MANIFEST` ou sur un fichier, `PROMPT.md` absent de `$DEST`, ou version du `PROMPT.md` différente de celle du `MANIFEST` — ce dernier cas est un déploiement en cours de propagation sur `raw`, réessayer cinq minutes plus tard) :
**ARRÊTE.** Explique ce qui a échoué à l'utilisateur. Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire — une version périmée qui tourne sans le dire est
exactement ce que ce système élimine.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>`, « le dossier de la compétence » ou des chemins relatifs
`scripts/…` / `references/…`, c'est `$DEST`. Les arguments passés à la compétence (fenêtre
temporelle, nom d'un groupe) s'appliquent tels quels.
