// Épingle un bug SILENCIEUX du 1er septembre 2026 : `b.click()` nu ne déplie pas
// certains « En voir plus » de commentaires. Sur « We need you », deux commentaires
// sont restés figés sur « … En voir plus » après une quinzaine de cycles
// __expandCommentText() + __merge() : __exportBlocked() bloquait l'export sans
// moyen de le lever, et rien ne l'expliquait (bouton trouvé, clic bien émis).
// Ces boutons React n'écoutent pas le click DOM — ils écoutent la séquence pointer.
const fs = require('fs');
const { JSDOM } = require('jsdom');   // npm i --no-save jsdom@22
const SRC = fs.readFileSync(require('path').join(__dirname, '..', 'remote-skills/scrape-veto/scripts/scrape_helpers.js'), 'utf8');

let ok = 0, ko = 0;
const t = (l, got, want) => { const p = JSON.stringify(got) === JSON.stringify(want); p ? ok++ : ko++;
  console.log((p ? '  ok    ' : '  ECHEC ') + l + (p ? '' : `\n          obtenu=${JSON.stringify(got)}\n          attendu=${JSON.stringify(want)}`)); };

// Le fixture : un commentaire dont l'expander n'écoute QUE pointerdown (cas FB réel),
// et un post dont l'expander écoute le click classique (cas qui marchait déjà).
const dom = new JSDOM(`<body>
  <div role="article" id="post">
    <div dir="auto">Annonce tronquee</div>
    <div role="button" id="btnPost">En voir plus</div>
    <div role="article" aria-label="Commentaire de Sylvie Coca il y a 2 heures">
      <div dir="auto">Bonjour nous avons un poste a pourvoir a Poitiers,… En voir plus</div>
      <div role="button" id="btnCom">En voir plus</div>
    </div>
  </div>
</body>`, { url: 'https://www.facebook.com/groups/123/?sorting_setting=CHRONOLOGICAL', runScripts: 'outside-only', pretendToBeVisual: true });
const w = dom.window;
Object.defineProperty(w.Element.prototype, 'innerText', {
  configurable: true, get() { return this.textContent; }
});
// jsdom ne fait pas de layout : __realClick lit getBoundingClientRect pour clientX/Y.
w.Element.prototype.getBoundingClientRect = function () {
  return { x: 10, y: 10, left: 10, top: 10, right: 90, bottom: 30, width: 80, height: 20 };
};
w.eval(SRC);

const d = w.document;
let comOuvert = false, postOuvert = false;
// ⚠️ pointerdown SEULEMENT : c'est ce que b.click() n'atteignait pas.
d.getElementById('btnCom').addEventListener('pointerdown', () => { comOuvert = true; });
d.getElementById('btnPost').addEventListener('click', () => { postOuvert = true; });

t('__realClick est exposé sur window', typeof w.__realClick, 'function');
if (typeof w.__realClick !== 'function') {          // sinon la suite crashe et masque le rapport
  console.log('\n  → helpers sans __realClick : version antérieure à 0.14.1, rien d\'autre à tester.');
  console.log(`\n${ok} ok, ${ko} échec(s)`);
  process.exit(1);
}
t('__realClick renvoie true quand le clic part', w.__realClick(d.getElementById('btnCom')), true);
t('bouton qui n\'écoute QUE pointerdown : déclenché (b.click() nu échouait)', comOuvert, true);

// Remise à zéro, puis on repasse par les expanders eux-mêmes.
comOuvert = false;
t('__expandCommentText déplie le commentaire', w.__expandCommentText(), 1);
t('  → le handler pointerdown a bien reçu l\'événement', comOuvert, true);

t('__expandPostText compte les deux boutons du document', w.__expandPostText(), 2);
t('  → le click classique reste déclenché (pas de régression)', postOuvert, true);

// __expandVisible : même exigence, bornée au viewport (le rect ci-dessus est à l'écran).
postOuvert = false; comOuvert = false;
t('__expandVisible clique aussi via la séquence pointer', w.__expandVisible(1200) >= 1, true);
t('  → pointerdown reçu', comOuvert, true);

// Garde-fou de non-régression sur la SOURCE : aucun `b.click()` nu ne doit revenir.
t('aucun b.click() nu ne subsiste dans les helpers', /\bb\.click\(\)\s*;/.test(SRC), false);

console.log(`\n${ok} ok, ${ko} échec(s)`);
process.exit(ko ? 1 : 0);
