---
name: dossier-candidat
description: >-
  Analyse et score les CV des candidats vétérinaires du vivier Airtable SaRecrute selon une grille
  de recruteur expert, puis génère le « dossier de présentation candidat » standardisé sur une
  seule page A4 à la charte SaRecrute, bâti exclusivement sur les champs Airtable vérifiés par les
  recruteuses (jamais le CV PDF, jamais le Profil IA). Se déclenche dès que l'utilisateur parle de
  CV, de dossier ou de fiche de présentation à envoyer à une clinique, de shortlist, de scoring,
  de « meilleurs profils », de mise en forme ou de refonte de CV, de template ou de modèle
  standard A4, du bilan de compétences par acte, ou qu'il demande d'analyser le vivier Airtable —
  même s'il ne mentionne ni SaRecrute, ni Airtable, ni A4, et même s'il formule ça simplement
  (« sors-moi les bons profils », « fais-moi un beau CV pour Margot », « qui est présentable chez
  les vétos ? », « montre-moi le modèle »). L'analyse seule et la génération de dossier seule sont
  deux moitiés indépendantes : l'une ou l'autre suffit à déclencher la compétence.
---

# Dossier de présentation candidat

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`**, fichier par fichier depuis
`raw.githubusercontent.com`, en suivant le `MANIFEST` de la compétence (PROMPT.md et assets y sont
listés avec la version qu'ils partagent) :

```bash
SKILL="dossier-candidat"
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
n'improvise aucune version dégradée de mémoire — surtout pas en reconstruisant le template A4 :
un dossier qui part chez une clinique cliente avec une mise en page approximative abîme la marque
plus sûrement que l'absence de dossier.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>`, « le dossier de la compétence » ou des chemins relatifs `assets/…`,
c'est `$DEST`. Le template `assets/cv-template.html` s'y copie et s'y découpe : il ne se relit pas
en entier. Ce que l'utilisateur a demandé (analyse du vivier, dossier d'un candidat nommé, ou
modèle vierge) s'applique tel quel.
