---
name: creer-brouillons-facebook
description: >-
  Prépare des brouillons de publication Facebook (texte + image, sans publier) à partir des
  publications prévues aujourd'hui dans l'Airtable de recrutement vétérinaire (base prod
  "Recrutement vétérinaire"). Se déclenche quand l'utilisateur demande de "préparer les
  brouillons Facebook", "faire les publications du jour", "poster les annonces véto",
  "préparer les publications Facebook", "brouillons Facebook du jour" ou formulation
  équivalente. Ouvre un onglet Chrome par publication, colle le texte, joint l'image du
  Drive, et laisse l'utilisateur cliquer sur Publier.
---

# Créer les brouillons Facebook du jour

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`** (un tarball : PROMPT.md et les fichiers
qui l'accompagnent datent tous du même commit, jamais de mélange de versions) :

```bash
DEST="<scratchpad de session>/creer-brouillons-facebook-remote"   # tout dossier temporaire de session convient, hors du plugin
mkdir -p "$DEST" && curl -fsSL https://github.com/Cleuteu/sarecrute-competences/archive/refs/heads/stable.tar.gz \
  | tar xz -C "$DEST" --strip-components=3 "sarecrute-competences-stable/remote-skills/creer-brouillons-facebook"
```

Si un dossier d'une exécution précédente existe déjà, repars d'un dossier neuf : un mélange
ancien/nouveau serait pire qu'une copie périmée.

**2. Si le téléchargement échoue** (réseau, 404, archive vide, `PROMPT.md` absent de `$DEST`) :
**ARRÊTE.** Explique ce qui a échoué à l'utilisateur. Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire — préparer des brouillons avec une procédure périmée fait perdre plus de temps au recruteur qu'un arrêt franc.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>`, « le dossier de la compétence » ou des chemins relatifs
`scripts/…`, c'est `$DEST`. Rien n'est publié : la compétence prépare, le recruteur clique.
