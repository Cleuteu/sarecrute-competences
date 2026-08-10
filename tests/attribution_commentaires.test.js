// Reproduit la structure FB (post = div[role=article] ; commentaire = div[role=article][aria-label^="Commentaire de"])
// et la VIRTUALISATION PARTIELLE : commentaire encore rendu alors que l'ancre de timestamp de SON post ne l'est plus.
const fs = require('fs');
const { JSDOM } = require('jsdom');   // npm i --no-save jsdom@22
const SRC = fs.readFileSync(require('path').join(__dirname, '..', 'plugins/sarecrute-admin/skills/scrape-veto/scripts/scrape_helpers.js'), 'utf8');

const ts = (txt) => `<a href="/x?__cft__=1"><span class="flexbox">${txt.split('').map(c => `<i>${c}</i>`).join('')}</span></a>`;

function build(postBAvecAncre) {
  const dom = new JSDOM(`<body><div id="feed">
    <div role="article" id="postA">
      <h2><a href="/groups/123/user/111/">Fatou Unvt</a></h2>
      ${ts('Le 7 aout a 15:31')}
      <div dir="auto">VETERINAIRE CANIN OU MIXTE - LE LUDE (72). Notre clinique recherche un veterinaire canin ou mixte pour renforcer son equipe en CDD de septembre 2026 a fevrier 2027.</div>
      <div role="article" aria-label="Commentaire de Mveto Pro il y a 21 heures"><div dir="auto">bonjour, possible d avoir plus de details ? merci</div></div>
    </div>
    <div role="article" id="postB">
      <h2><a href="/groups/123/user/222/">SparklyTulip723</a></h2>
      ${postBAvecAncre ? ts('Le 7 aout a 15:13') : '<!-- timestamp virtualise -->'}
      <div dir="auto">Je cherche des fiches de revision et supports de cours recents pour me remettre dans le bain apres une periode d absence de la pratique clinique.</div>
      <div role="article" aria-label="Commentaire de Virginie Stv il y a 2 jours"><div dir="auto">J ai laisse toutes mes fiches en libre acces sur Quizlet, identifiant Virg_VT</div></div>
    </div>
  </div></body>`, { url: 'https://www.facebook.com/groups/123/?sorting_setting=CHRONOLOGICAL', runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  // jsdom n'implémente pas innerText (utilisé partout par __harvestAll) : on l'approxime.
  Object.defineProperty(w.Element.prototype, 'innerText', {
    configurable: true, get() { return this.textContent; }
  });
  // jsdom ne fait pas de layout : on rend getBoundingClientRect cohérent pour __decodeTS
  w.Element.prototype.getBoundingClientRect = function () {
    const isFlex = this.classList && this.classList.contains('flexbox');
    return isFlex ? { left: 0, right: 1000, top: 0, bottom: 10, width: 1000 }
                  : { left: 0, right: 10, top: 0, bottom: 10, width: 10 };
  };
  const cs = w.getComputedStyle.bind(w);
  w.getComputedStyle = (el) => (el.classList && el.classList.contains('flexbox'))
    ? { display: 'flex' } : cs(el);
  w.eval(SRC);
  return dom;
}

let ok = 0, ko = 0;
const t = (l, got, want) => { const p = JSON.stringify(got) === JSON.stringify(want); p ? ok++ : ko++;
  console.log((p ? '  ok    ' : '  ECHEC ') + l + (p ? '' : `\n          obtenu=${JSON.stringify(got)}\n          attendu=${JSON.stringify(want)}`)); };

// cas 1 — les deux posts entièrement rendus
let dom = build(true), posts = dom.window.__harvestAll(), map = {};
posts.forEach(p => map[p.author] = p.comments.map(c => c.name).sort());
t('cas nominal : 2 posts captés', posts.length, 2);
t('cas nominal : Fatou garde SON commentaire', map['Fatou Unvt'], ['Mveto Pro']);
t('cas nominal : Sparkly garde SON commentaire', map['SparklyTulip723'], ['Virginie Stv']);
t('cas nominal : aucun orphelin', dom.window.__orphanComments, 0);

// cas 2 — LE BUG : timestamp du post B virtualisé, son commentaire encore rendu
dom = build(false); posts = dom.window.__harvestAll(); map = {};
posts.forEach(p => map[p.author] = p.comments.map(c => c.name).sort());
t('virtualisation : seul le post A est capté', posts.length, 1);
t("virtualisation : le commentaire de B n'est PAS recopié sur A", map['Fatou Unvt'], ['Mveto Pro']);
t('virtualisation : commentaire orphelin compté, pas attribué', dom.window.__orphanComments, 1);

// cas 3 — la racine du post ne doit pas engloutir le voisin
dom = build(true); posts = dom.window.__harvestAll();
t('racine : les auteurs restent distincts', posts.map(p => p.author).sort(), ['Fatou Unvt', 'SparklyTulip723']);
t('racine : le corps de A ne contient pas le texte de B',
  /fiches de revision/.test(posts.find(p => p.author === 'Fatou Unvt').body), false);

console.log(`\n${ok} ok, ${ko} échec(s)`);
process.exit(ko ? 1 : 0);
