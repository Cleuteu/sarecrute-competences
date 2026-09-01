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

**1. Télécharge le snapshot de la branche `stable`** (un tarball : PROMPT.md, scripts et
références datent tous du même commit, jamais de mélange de versions) :

```bash
DEST="<scratchpad de session>/creer-candidat-remote"   # tout dossier temporaire de session convient, hors du plugin
mkdir -p "$DEST" && curl -fsSL https://github.com/Cleuteu/sarecrute-competences/archive/refs/heads/stable.tar.gz \
  | tar xz -C "$DEST" --strip-components=3 "sarecrute-competences-stable/remote-skills/creer-candidat"
```

Si un dossier d'une exécution précédente existe déjà, repars d'un dossier neuf : un mélange
ancien/nouveau serait pire qu'une copie périmée.

**2. Si le téléchargement échoue** (réseau, 404, archive vide, `PROMPT.md` absent de `$DEST`) :
**ARRÊTE.** Explique ce qui a échoué à l'utilisateur. Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire — créer un candidat à moitié, avec des champs
devinés, coûte plus cher que ne pas le créer.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>`, « le dossier de la compétence » ou des chemins relatifs
`scripts/…` / `references/…`, c'est `$DEST`. Ce que l'utilisateur a fourni (CV, annonce collée,
transcript, ou seulement un nom) s'applique tel quel.
