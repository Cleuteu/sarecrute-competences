---
name: maj-offres
description: Met à jour les offres d'emploi publiées sur le site SaRecrute (offres.html + carousel de l'accueil) depuis l'Airtable de prod. Retire les offres archivées ou dont la clinique n'est plus "Signé", ajoute les nouvelles, réécrit les descriptions dont les notes/annonce ont changé, et pose le tag "Nouvelle offre" sur les plus récentes (minimum 5). Se déclenche sur "mets à jour les offres", "rafraîchis les offres du site", "il y a de nouvelles offres signées", "maj offres" ou formulation équivalente.
---

# Mise à jour des offres du site SaRecrute

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`** (un tarball : PROMPT.md et les fichiers
qui l'accompagnent datent tous du même commit, jamais de mélange de versions) :

```bash
DEST="<scratchpad de session>/maj-offres-remote"   # tout dossier temporaire de session convient, hors du plugin
mkdir -p "$DEST" && curl -fsSL https://github.com/Cleuteu/sarecrute-competences/archive/refs/heads/stable.tar.gz \
  | tar xz -C "$DEST" --strip-components=3 "sarecrute-competences-stable/remote-skills/maj-offres"
```

Si un dossier d'une exécution précédente existe déjà, repars d'un dossier neuf : un mélange
ancien/nouveau serait pire qu'une copie périmée.

**2. Si le téléchargement échoue** (réseau, 404, archive vide, `PROMPT.md` absent de `$DEST`) :
**ARRÊTE.** Explique ce qui a échoué à l'utilisateur. Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire — publier sur le site des offres construites avec une doctrine périmée (libellés, anonymat) est pire que ne rien publier, et le garde-fou anonymat vit dans les scripts téléchargés.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>` ou `<skill>`, « le dossier de la compétence » ou des chemins relatifs
`scripts/…` / `assets/…`, c'est `$DEST`. Le site et le dossier de travail se résolvent comme avant (`SARECRUTE_SITE` ou dossier courant, `~/.sarecrute/maj-offres/work/`) : rien ne s'écrit dans `$DEST`.
