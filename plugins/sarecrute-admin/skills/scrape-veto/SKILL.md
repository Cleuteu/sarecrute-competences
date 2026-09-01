---
name: scrape-veto
description: Scrape les posts des groupes Facebook vétérinaires cochés « Scraper les posts » dans Airtable (fenêtre temporelle paramétrable, 6h par défaut) + commentaires pertinents, et pousse tout dans "Posts scrappés" en déduplicant, chaque entrée rattachée à son canal. Args possibles ex. "aujourd'hui", "48h", "2 derniers jours", ou le nom d'un groupe pour n'en faire qu'un.
---

# Scrape Veto

Les instructions de cette compétence ne sont **pas dans ce fichier** : elles vivent sur GitHub et
se téléchargent **à chaque exécution**, pour que la version exécutée soit toujours la dernière
déployée — sans `plugin update`.

## Exécution

**1. Télécharge le snapshot de la branche `stable`** (un tarball : PROMPT.md, scripts et
références datent tous du même commit, jamais de mélange de versions) :

```bash
DEST="<scratchpad de session>/scrape-veto-remote"   # tout dossier temporaire de session convient, hors du plugin
mkdir -p "$DEST" && curl -fsSL https://github.com/Cleuteu/sarecrute-competences/archive/refs/heads/stable.tar.gz \
  | tar xz -C "$DEST" --strip-components=3 "sarecrute-competences-stable/remote-skills/scrape-veto"
```

Si un dossier d'une exécution précédente existe déjà, repars d'un dossier neuf : un mélange
ancien/nouveau serait pire qu'une copie périmée.

**2. Si le téléchargement échoue** (réseau, 404, archive vide, `PROMPT.md` absent de `$DEST`) :
**ARRÊTE.** Explique ce qui a échoué à l'utilisateur. Ne te rabats sur aucune copie locale et
n'improvise aucune version dégradée de mémoire — une version périmée qui tourne sans le dire est
exactement ce que ce système élimine.

**3. Read `$DEST/PROMPT.md`** et annonce à l'utilisateur la **version** indiquée sur sa première
ligne avant de commencer.

**4. Exécute `$DEST/PROMPT.md` comme s'il était le corps de cette compétence.** Partout où il
mentionne `<dossier_skill>`, « le dossier de la compétence » ou des chemins relatifs
`scripts/…` / `references/…`, c'est `$DEST`. Les arguments passés à la compétence (fenêtre
temporelle, nom d'un groupe) s'appliquent tels quels.
