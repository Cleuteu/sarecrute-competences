---
name: creer-clinique-offre
description: >-
  Crée dans l'Airtable de recrutement vétérinaire (base prod « Recrutement vétérinaire ») la
  clinique et l'offre d'emploi correspondant à une annonce que le recruteur colle dans Claude,
  puis prépare le premier contact : brouillon Gmail si la clinique a une adresse mail, sinon
  message Messenger à copier-coller. Se déclenche quand l'utilisateur colle une annonce
  vétérinaire ou demande de « créer la clinique et l'offre », « ajouter cette annonce dans
  Airtable », « enregistrer cette offre », « nouvelle clinique + offre », ou formulation
  équivalente.
---

# Créer une clinique et son offre d'emploi depuis une annonce

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`** (un tarball : PROMPT.md et les fichiers
qui l'accompagnent datent tous du même commit, jamais de mélange de versions) :

```bash
DEST="<scratchpad de session>/creer-clinique-offre-remote"   # tout dossier temporaire de session convient, hors du plugin
mkdir -p "$DEST" && curl -fsSL https://github.com/Cleuteu/sarecrute-competences/archive/refs/heads/stable.tar.gz \
  | tar xz -C "$DEST" --strip-components=3 "sarecrute-competences-stable/remote-skills/creer-clinique-offre"
```

Si un dossier d'une exécution précédente existe déjà, repars d'un dossier neuf : un mélange
ancien/nouveau serait pire qu'une copie périmée.

**2. Si le téléchargement échoue** (réseau, 404, archive vide, `PROMPT.md` absent de `$DEST`) :
**ARRÊTE.** Explique ce qui a échoué à l'utilisateur. Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire — créer une clinique ou une offre avec des champs devinés coûte plus cher à rattraper que ne rien créer.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>`, « le dossier de la compétence » ou des chemins relatifs
`scripts/…` / `references/…`, c'est `$DEST`. L'annonce collée par le recruteur s'applique telle quelle.
