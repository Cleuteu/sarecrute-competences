# Tests

Ces tests ne sont **pas** embarqués dans les plugins (ils vivent hors de `plugins/`, donc rien
n'est installé chez les recruteurs). Ils épinglent des bugs de `scrape-veto` qui ont tous été
**silencieux** — ils ne provoquaient aucune erreur, juste des données fausses en base.

```bash
node tests/troncature.test.mjs                      # aucune dépendance
python3 tests/fusion_commentaires.test.py           # aucune dépendance
npm i --no-save jsdom@22 && node tests/attribution_commentaires.test.js
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

Lancés contre la version d'avant le 10 août 2026, ils échouent respectivement sur 1 et 6 cas.
