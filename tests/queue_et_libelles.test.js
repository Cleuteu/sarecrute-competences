// Épingle deux défauts SILENCIEUX du scrape du 28 octobre 2026 (scrape-veto 0.16.5).
//
// 1. __expandCommentText ne cliquait pas trois « En voir plus » de commentaires : innerText
//    exact « En voir plus », mais textContent refusé par le test strict. __exportBlocked
//    bloquait, la remontée par pas de 650 px n'y changeait rien, il a fallu cliquer à la main.
// 2. __tailKnown(3, borne) ne se déclenchait pas : sur « We need you », le dernier post rendu
//    (Flo Ky, blacklisté donc absent de la base) suivait 7 posts connus d'affilée.
const fs = require('fs');
const { JSDOM } = require('jsdom');   // npm i --no-save jsdom@22
const SRC = fs.readFileSync(require('path').join(__dirname, '..', 'remote-skills/scrape-veto/scripts/scrape_helpers.js'), 'utf8');

let ok = 0, ko = 0;
const t = (l, got, want) => { const p = JSON.stringify(got) === JSON.stringify(want); p ? ok++ : ko++;
  console.log((p ? '  ok    ' : '  ECHEC ') + l + (p ? '' : `\n          obtenu=${JSON.stringify(got)}\n          attendu=${JSON.stringify(want)}`)); };

// Fixture : le texte caché (display:none) entre dans textContent mais pas dans innerText —
// c'est l'écart observé, quelle qu'en soit la forme exacte côté Facebook.
const dom = new JSDOM(`<body>
  <div role="article" aria-label="Commentaire de François Fauqueux il y a 2 jours">
    <div dir="auto">Hello, pas de poste pour l'instant mais passe te présenter!… En voir plus</div>
    <div role="button" id="cache">En voir plus<span style="display:none">a1b2c3d4e5f6g7</span></div>
  </div>
  <div role="article" aria-label="Réponse de Oceane Darbon il y a un jour">
    <a id="ancre"><div role="button" id="sansHref">En voir plus</div></a>
  </div>
  <div role="article" aria-label="Commentaire de Nicot Marie-Vinciane il y a un jour">
    <a href="/groups/1/posts/2/"><div role="button" id="lien">En voir plus</div></a>
    <div role="button" id="plusComs">Voir plus de commentaires<span style="display:none">zz</span></div>
    <div role="button" id="plusRep">Voir plus de réponses</div>
  </div>
</body>`, { url: 'https://www.facebook.com/groups/123/?sorting_setting=CHRONOLOGICAL', runScripts: 'outside-only', pretendToBeVisual: true });
const w = dom.window;
// innerText = texte visible : on saute les éléments display:none (jsdom ne l'implémente pas).
const visible = n => n.nodeType === 3 ? n.data
  : (n.nodeType === 1 && n.style && n.style.display === 'none') ? ''
  : Array.from(n.childNodes).map(visible).join('');
Object.defineProperty(w.Element.prototype, 'innerText', { configurable: true, get() { return visible(this); } });
w.Element.prototype.getBoundingClientRect = function () {
  return { x: 10, y: 10, left: 10, top: 10, right: 90, bottom: 30, width: 80, height: 20 };
};
w.eval(SRC);
const d = w.document;

console.log('\n__expandCommentText — libellé visible, jamais « Voir plus de commentaires »');
const clics = {};
for (const id of ['cache', 'sansHref', 'lien', 'plusComs', 'plusRep'])
  d.getElementById(id).addEventListener('pointerdown', () => { clics[id] = (clics[id] || 0) + 1; });
t('textContent pollué : le libellé visible est reconnu', w.__expanderLabel(d.getElementById('cache')), 'En voir plus');
t('« Voir plus de commentaires » : refusé même en lisant innerText', w.__expanderLabel(d.getElementById('plusComs')), '');
t('deux expanders cliqués (texte caché, <a> sans href)', w.__expandCommentText(), 2);
t('  → bouton au textContent pollué : cliqué', clics.cache, 1);
t('  → bouton dans un <a> sans href : cliqué', clics.sansHref, 1);
t('  → bouton dans un lien qui navigue : PAS cliqué', clics.lien, undefined);
t('  → « Voir plus de commentaires » : PAS cliqué', clics.plusComs, undefined);
t('  → « Voir plus de réponses » : PAS cliqué', clics.plusRep, undefined);

console.log('\n__tailKnown — n connus parmi les n+1 derniers, toujours à la borne ou avant');
const P = (author, iso, body) => ({ author, iso, body, comments: [] });
const known = ['Recherche poste mixte canine equine ou canine', 'On recrute un vétérinaire dans notre clinique',
  'Jeune vétérinaire diplômée en 2026 à la recherche', 'Bonjour vétérinaire autonome en chirurgie',
  'Cherche remplacement bonjour tout le monde', 'Suite à une morsure à la main ma consœur'];
w.__seenInit(known.map(b => w.__sig(b)));
const borne = '2026-10-26';
const tail = list => { w.__harvestAll = () => list; return w.__tailKnown(3, borne); };

t('cas réel : Flo Ky (blacklisté, absent) en DERNIER sous 3 connus → arrêt',
  tail([P('A', '2026-10-26', known[3]), P('B', '2026-10-26', known[4]), P('C', '2026-10-26', known[5]),
        P('Flo Ky', '2026-10-25', 'Post blacklisté jamais poussé en base')]), true);
t('inconnu intercalé au milieu → arrêt',
  tail([P('A', '2026-10-26', known[0]), P('X', '2026-10-25', 'Inconnu'), P('B', '2026-10-25', known[1]),
        P('C', '2026-10-25', known[2])]), true);
t('DEUX inconnus parmi les 4 derniers → pas d\'arrêt',
  tail([P('A', '2026-10-26', known[0]), P('X', '2026-10-25', 'Inconnu 1'), P('B', '2026-10-25', known[1]),
        P('Y', '2026-10-25', 'Inconnu 2')]), false);
t('republications du jour : connues mais au-dessus de la borne → pas d\'arrêt',
  tail([P('A', '2026-10-28', known[0]), P('B', '2026-10-28', known[1]), P('C', '2026-10-28', known[2]),
        P('D', '2026-10-26', known[3])]), false);
t('2 republications du jour + 2 connus à la borne → pas d\'arrêt',
  tail([P('A', '2026-10-28', known[0]), P('B', '2026-10-28', known[1]), P('C', '2026-10-26', known[2]),
        P('D', '2026-10-26', known[3])]), false);
t('seulement 3 posts rendus : règle stricte, un inconnu bloque',
  tail([P('A', '2026-10-26', known[0]), P('B', '2026-10-26', known[1]), P('X', '2026-10-25', 'Inconnu')]), false);
t('seulement 3 posts rendus, tous connus → arrêt',
  tail([P('A', '2026-10-26', known[0]), P('B', '2026-10-26', known[1]), P('C', '2026-10-25', known[2])]), true);
t('empreintes non chargées → jamais d\'arrêt', (w.__seenInit([]), tail([P('A', '2026-10-26', known[0]),
  P('B', '2026-10-26', known[1]), P('C', '2026-10-25', known[2]), P('D', '2026-10-25', known[3])])), false);

console.log(`\n${ok} ok, ${ko} échec(s)`);
process.exit(ko ? 1 : 0);
