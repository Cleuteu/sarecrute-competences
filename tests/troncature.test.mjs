// Teste les garde-fous purs (sans DOM) : __isTrunc / __truncated / __truncatedComments / __exportBlocked
import fs from 'fs';
const src = fs.readFileSync(new URL('../remote-skills/scrape-veto/scripts/scrape_helpers.js', import.meta.url), 'utf8');
globalThis.window = globalThis;
globalThis.document = { querySelectorAll: () => [], querySelector: () => null,
  body:{scrollHeight:0}, visibilityState:'visible', hasFocus:()=>true, title:'' };
globalThis.location = { pathname:'/groups/123/', search:'?sorting_setting=CHRONOLOGICAL' };
globalThis.getComputedStyle = () => ({display:'block'});
globalThis.requestAnimationFrame = () => {};
globalThis.Node = { DOCUMENT_POSITION_FOLLOWING: 4 };
(0, eval)(src);

let ok = 0, ko = 0;
const t = (label, got, want) => {
  const pass = JSON.stringify(got) === JSON.stringify(want);
  pass ? ok++ : ko++;
  console.log((pass ? '  ok   ' : '  ECHEC') + ' ' + label + (pass ? '' : `\n         obtenu=${JSON.stringify(got)}\n         attendu=${JSON.stringify(want)}`));
};

t('__isTrunc détecte "… Voir plus"', window.__isTrunc('Bonjour,… Voir plus'), true);
t('__isTrunc détecte "En voir plus"', window.__isTrunc('Bonjour, En voir plus'), true);
t('__isTrunc laisse passer un texte normal', window.__isTrunc('Bonjour, mail envoyé'), false);

window.__store = {
  a: { author:'Clinique X', iso:'2026-08-09', body:'Annonce complète, rien à déplier.',
       comments: { c1:{name:'Zoé Dubois', text:'Bonjour,… Voir plus'} } },
  b: { author:'Vieux post', iso:'2026-07-01', body:'Corps tronqué… Voir plus', comments:{} },
  c: { author:'Clinique Y', iso:'2026-08-08', body:'Annonce nette.',
       comments: { c2:{name:'Paul', text:'mail envoyé'} } },
};

t('__truncated ne voit QUE les posts', window.__truncated().map(p=>p.author), ['Vieux post']);
t('__truncatedComments voit le commentaire tronqué', window.__truncatedComments().map(c=>c.name), ['Zoé Dubois']);
t('ancien garde-fou seul aurait laissé passer (dans la fenêtre)',
  window.__truncated().filter(p=>p.iso>='2026-08-07').length, 0);
t('__exportBlocked bloque sur le commentaire tronqué',
  /commentaire\(s\) tronqué/.test(window.__exportBlocked('2026-08-07')), true);
t('__exportBlocked ignore le post tronqué HORS fenêtre',
  /post\(s\) tronqué/.test(window.__exportBlocked('2026-08-07')), false);
t('__exportBlocked signale le post tronqué SANS borne',
  /post\(s\) tronqué/.test(window.__exportBlocked()), true);

delete window.__store.a.comments.c1;
t('__exportBlocked passe une fois le commentaire déplié', window.__exportBlocked('2026-08-07'), '');

console.log(`\n${ok} ok, ${ko} échec(s)`);
process.exit(ko ? 1 : 0);
