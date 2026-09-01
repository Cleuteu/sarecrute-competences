# Tests

Ces tests ne sont **pas** embarqués dans les plugins (ils vivent hors de `plugins/`, donc rien
n'est installé chez les recruteurs). Ils épinglent des bugs qui ont tous été **silencieux** — ils
ne provoquaient aucune erreur, juste des données fausses en base ou dans une publication.

```bash
node tests/troncature.test.mjs                      # aucune dépendance
python3 tests/fusion_commentaires.test.py           # aucune dépendance
npm i --no-save jsdom@22 && node tests/attribution_commentaires.test.js
node tests/expansion_clic.test.js                   # jsdom aussi
node tests/liens_markdown.test.mjs                  # aucune dépendance
```

(jsdom 22 et non la dernière : les versions récentes ne se chargent pas en CommonJS sous Node 20.)

## Ce que chacun protège

**`fusion_commentaires.test.py`** — un commentaire fusionnait « entre lui-même » par personne mais
jamais avec le **post** de cette personne : Sabine Marcillaud avait 3 enregistrements pour 1 seule
offre (son annonce + deux relances posées sous des posts de candidates). Le test épingle les quatre
pièges du nouveau régime : la cible de fusion est le **post** et pas le dernier commentaire, un
commentaire **comble** les champs vides de l'annonce sans écraser les siens, la section commentée
reste identifiable (`💬 COMMENTAIRE de X sous le post de Y`), et sa signature ignore ce marqueur —
sinon chaque re-scrape d'un commentaire d'avant le 20/08/2026 empilerait une section en double.

**`expansion_clic.test.js`** — `b.click()` nu ne déplie pas certains « En voir plus » de
commentaires : ces boutons React de Facebook n'ont aucun handler sur le click DOM, ils écoutent la
séquence pointer. Le 1er septembre 2026, deux commentaires de « We need you » sont restés tronqués
après une quinzaine de cycles `__expandCommentText()` + `__merge()` — `__exportBlocked()` bloquait
l'export **sans moyen de le lever**, et rien ne l'expliquait (le bouton était trouvé, le clic bien
émis). Le test rejoue un bouton qui n'écoute que `pointerdown`, exige que les trois expanders
passent par `__realClick`, vérifie que le click classique marche toujours, et interdit le retour
d'un `b.click()` nu dans la source.

**`troncature.test.mjs`** — `__truncated()` ne regarde que les **posts**. Un commentaire figé sur
« Bonjour,… Voir plus » passait donc l'export sans aucun signal. Le test vérifie que
`__truncatedComments()` le voit, que `__exportBlocked(borne)` bloque dessus, et qu'il ne bloque
**pas** sur un post tronqué hors fenêtre (qui ne sera pas exporté de toute façon).

**`attribution_commentaires.test.js`** — la virtualisation de Facebook est **partielle** : un
commentaire peut rester rendu alors que l'ancre de timestamp de *son* post ne l'est plus.
L'ancienne heuristique remontait alors au plus proche timestamp qui précède, c'est-à-dire celui du
post **voisin** : le même jeu de commentaires se retrouvait recopié sur un post qui ne le portait
pas, fabriquant un faux candidat sous une annonce qui n'était pas la sienne. Le test rejoue ce cas
exact et exige que le commentaire soit **abandonné** (compté dans `__orphanComments`) plutôt que
mal attribué. Il couvre aussi la racine du post, qui pouvait engloutir l'en-tête du voisin et
donner deux posts au même auteur.

Depuis le 23 août 2026 il couvre aussi trois pièges découverts en production :

- **Posts sans `div[role="article"]` ancêtre** (le cas de « WE NEED YOU!!! », dont tout le vivier
  candidat était concerné) : le rattachement doit passer par le containment strict — premier
  ancêtre englobant **exactement une** ancre de post — et **abandonner** dès que l'ancêtre en
  englobe plusieurs, là où l'ancienne heuristique de proximité attribuait au voisin.
- **Timestamps SVG chaînés** `use → svg → use → text` : Facebook a intercalé un maillon, et un
  décodage limité à un seul niveau ne datait plus les posts — donc ne les captait plus du tout.
- **`__purgeStubs`** : un doublon tronqué non dépliable ne doit plus bloquer `__exportBlocked`,
  sans pour autant masquer une vraie troncature.

Plus le texte **intégral** d'un commentaire : `__commentFull` joint tous ses paragraphes, là où la
lecture du seul premier `div[dir="auto"]` amputait silencieusement les candidatures — sans même
déclencher `__truncatedComments`, puisque le fragment retenu ne finit pas par « Voir plus ».

⚠️ Le fixture portait un `href="/x?__cft__=1"` qui ne passe pas `__isTsAnchor` (lequel exige
`?__cft__`, `/posts/` ou `story_fbid=`) : **aucune** ancre n'était captée et le fichier plantait
avant la fin. Corrigé le 23 août 2026 — si ce test se met à échouer en bloc, vérifier d'abord que
le fixture reflète toujours la forme réelle des ancres.

Lancés contre la version d'avant le 10 août 2026, les deux premiers échouent respectivement sur 1
et 6 cas ; contre celle d'avant le 23 août 2026, `attribution_commentaires` échoue sur 7 cas.

**`liens_markdown.test.mjs`** — le convertisseur Markdown → HTML de `creer-brouillons-facebook`
ne prévoyait rien pour `[texte](url)`. Deux annonces sur cinq écrivant l'adresse de contact en
`[sarah.vet@sarecrute.com](mailto:sarah.vet@sarecrute.com)`, le brouillon Facebook affichait les
crochets et le `mailto:` en clair. Rien ne le signalait : le brouillon se crée, le contrôle
`dup`/`img` passe, le gras est là. Le test lit les fonctions **dans le PROMPT.md** (corps distant, `remote-skills/`) et vérifie les
liens `mailto:`/`tel:` et http, le gras dans un libellé de lien, l'échappement du `&` d'une URL
(`link` doit tourner avant `esc`), la **cohérence `mdToHtml` / `mdToText`** — dont dépend le
contrôle de longueur `attendu` vs `obtenu` du run — et la non-régression du gras, des titres, de
l'indentation et des crochets isolés.
