// Reproduit la structure FB (post = div[role=article] ; commentaire = div[role=article][aria-label^="Commentaire de"])
// et la VIRTUALISATION PARTIELLE : commentaire encore rendu alors que l'ancre de timestamp de SON post ne l'est plus.
const fs = require('fs');
const { JSDOM } = require('jsdom');   // npm i --no-save jsdom@22
const SRC = fs.readFileSync(require('path').join(__dirname, '..', 'plugins/sarecrute-admin/skills/scrape-veto/scripts/scrape_helpers.js'), 'utf8');

// href : la forme réelle des ancres de timestamp de post sur le fil. __isTsAnchor
// exige `?__cft__`, `/posts/` ou `story_fbid=` — un href quelconque portant
// « __cft__ » ne suffit pas (le fixture l'ignorait, et AUCUNE ancre n'était captée).
// ⚠️ Le jeton `__cft__` identifie le POST : deux posts distincts en ont deux
// différents, et TOUTES les ancres d'un même post partagent le leur (vérifié en
// live le 25/08/2026). Le fixture réutilisait un jeton unique pour tout le fil —
// irréaliste, et ça masquait le cas du post partagé. `tok` est donc un paramètre.
const ts = (txt, tok = 'AZW1') => `<a href="?__cft__[0]=${tok}"><span class="flexbox">${txt.split('').map(c => `<i>${c}</i>`).join('')}</span></a>`;

function build(postBAvecAncre) {
  const dom = new JSDOM(`<body><div id="feed">
    <div role="article" id="postA">
      <h2><a href="/groups/123/user/111/">Fatou Unvt</a></h2>
      ${ts('Le 7 aout a 15:31', 'AZpostA')}
      <div dir="auto">VETERINAIRE CANIN OU MIXTE - LE LUDE (72). Notre clinique recherche un veterinaire canin ou mixte pour renforcer son equipe en CDD de septembre 2026 a fevrier 2027.</div>
      <div role="article" aria-label="Commentaire de Mveto Pro il y a 21 heures"><div dir="auto">bonjour, possible d avoir plus de details ? merci</div></div>
    </div>
    <div role="article" id="postB">
      <h2><a href="/groups/123/user/222/">SparklyTulip723</a></h2>
      ${postBAvecAncre ? ts('Le 7 aout a 15:13', 'AZpostB') : '<!-- timestamp virtualise -->'}
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


// ---------------------------------------------------------------------------
// Groupe qui ne rend AUCUN div[role="article"] autour de ses posts (constaté le
// 23 août 2026 dans « WE NEED YOU!!! » : 22 commentaires orphelins, 0 rattaché).
// Le rattachement doit alors passer par la remontée « premier ancêtre qui englobe
// EXACTEMENT une ancre de post », et abandonner dès que c'est ambigu.
function buildNoArticle(comAmbigu) {
  const dom = new JSDOM(`<body><div id="feed">
    <div id="wrapA">
      <h2><a href="/groups/123/user/111/">Fatou Unvt</a></h2>
      ${ts('Le 7 aout a 15:31', 'AZpostA')}
      <div dir="auto">Notre clinique recherche un veterinaire canin ou mixte au Lude (72).</div>
      <div role="article" aria-label="Commentaire de Mveto Pro il y a 21 heures"><div dir="auto">Bonjour.</div><div dir="auto">Je vous ai envoye un message sur Messenger</div></div>
    </div>
    <div id="wrapB">
      <h2><a href="/groups/123/user/222/">SparklyTulip723</a></h2>
      ${ts('Le 7 aout a 15:13', 'AZpostB')}
      <div dir="auto">Je cherche un poste en canine dans le 72.</div>
      <div role="article" aria-label="Commentaire de Virginie Stv il y a 2 jours"><div dir="auto">On recrute a Sable-sur-Sarthe, MP</div></div>
    </div>
    ${comAmbigu ? '<div role="article" aria-label="Commentaire de Perdu Dansleflux il y a 1 heure"><div dir="auto">commentaire sans post identifiable</div></div>' : ''}
  </div></body>`, { url: 'https://www.facebook.com/groups/123/?sorting_setting=CHRONOLOGICAL', runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  Object.defineProperty(w.Element.prototype, 'innerText', {
    configurable: true, get() { return this.textContent; }
  });
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

// cas 4 — pas de div[role=article] parent : le repli par containment strict rattache
dom = buildNoArticle(false); posts = dom.window.__harvestAll(); map = {};
posts.forEach(p => map[p.author] = p.comments.map(c => c.name).sort());
t('sans role=article : 2 posts captés', posts.length, 2);
t('sans role=article : Fatou garde SON commentaire', map['Fatou Unvt'], ['Mveto Pro']);
t('sans role=article : Sparkly garde SON commentaire', map['SparklyTulip723'], ['Virginie Stv']);
t('sans role=article : aucun orphelin', dom.window.__orphanComments, 0);

// le texte du commentaire est INTÉGRAL (tous ses paragraphes, pas seulement le 1er)
const mveto = posts.find(p => p.author === 'Fatou Unvt').comments[0];
t('commentaire multi-paragraphes : texte complet',
  mveto.text, 'Bonjour.\nJe vous ai envoye un message sur Messenger');
t('__commentFull ne laisse pas le fragment passer pour non tronqué',
  dom.window.__isTrunc(mveto.text), false);

// cas 5 — commentaire dont le 1er ancêtre englobe DEUX posts : ambigu, donc abandonné
dom = buildNoArticle(true); posts = dom.window.__harvestAll();
const tous = posts.flatMap(p => p.comments.map(c => c.name));
t('ambigu : le commentaire perdu n\'est attribué à personne',
  tous.includes('Perdu Dansleflux'), false);
t('ambigu : les deux autres restent bien rattachés', tous.sort(), ['Mveto Pro', 'Virginie Stv']);
t('ambigu : compté comme orphelin', dom.window.__orphanComments, 1);

// ---------------------------------------------------------------------------
// __decodeTSSvg doit suivre la CHAÎNE d'indirections use -> svg -> use -> text
// (Facebook a intercalé un maillon le 23 août 2026 : sans ça, 2 posts sur 11).
function buildSvgChain(chaine) {
  const inner = chaine
    ? `<svg id="SvgA"><use xlink:href="#SvgB"></use></svg>
       <svg id="SvgB"><use xlink:href="#SvgC"></use></svg>
       <text id="SvgC">18 h</text>`
    : `<text id="SvgB">18 h</text><svg id="SvgA"><use xlink:href="#SvgB"></use></svg>`;
  const dom = new JSDOM(`<body><div id="feed">
    <div role="article">
      <h2><a href="/groups/123/user/111/">Clinique Test</a></h2>
      <a href="?__cft__[0]=AZW1"><svg><use xlink:href="#SvgA"></use></svg></a>
      <div dir="auto">Nous recrutons un veterinaire canin.</div>
    </div>
    ${inner}
  </div></body>`, { url: 'https://www.facebook.com/groups/123/?sorting_setting=CHRONOLOGICAL', runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  Object.defineProperty(w.Element.prototype, 'innerText', {
    configurable: true, get() { return this.textContent; }
  });
  w.eval(SRC);
  return dom;
}

dom = buildSvgChain(false);
t('SVG à un seul niveau : post capté', dom.window.__harvestAll().length, 1);
dom = buildSvgChain(true);
posts = dom.window.__harvestAll();
t('SVG en chaîne (use -> svg -> use -> text) : post capté', posts.length, 1);
t('SVG en chaîne : timestamp décodé', posts.length ? posts[0].decoded : null, '18 h');

// ---------------------------------------------------------------------------
// __purgeStubs : un doublon tronqué non dépliable ne doit pas bloquer l'export
dom = buildNoArticle(false);
{
  const w = dom.window;
  w.__store = {
    'Clinique X|Offredemploi-VeterinaireMixteE': { author: 'Clinique X', iso: '2026-08-20',
      body: "Offre d'emploi – Veterinaire Mixte\nE… En voir plus", comments: {} },
    'Clinique X|Offredemploi-VeterinaireMixteEntresole': { author: 'Clinique X', iso: '2026-08-20',
      body: "Offre d'emploi – Veterinaire Mixte\nEntre soleil et montagne, la clinique recrute.", comments: {} },
    'Clinique Y|Vraietroncature': { author: 'Clinique Y', iso: '2026-08-20',
      body: 'Vraie troncature jamais depliee ici… En voir plus', comments: {} }
  };
  // __exportBlocked purge LUI-MÊME les souches depuis la 0.9.2 : l'appelant ne
  // peut plus oublier de le faire. Il bloque donc encore, mais uniquement sur la
  // vraie troncature — plus sur le doublon parasite.
  const stop = w.__exportBlocked('2026-08-20');
  t('__exportBlocked bloque encore sur la VRAIE troncature', /Clinique Y/.test(stop), true);
  t('__exportBlocked ne bloque plus sur le doublon parasite', /Clinique X/.test(stop), false);
  t('la souche a été retirée du store',
    Object.values(w.__store).filter(p => p.author === 'Clinique X').length, 1);
  t('la version complète est celle qui reste',
    w.__isTrunc(Object.values(w.__store).find(p => p.author === 'Clinique X').body), false);
}

// ---------------------------------------------------------------------------
// __purgeCommentStubs : même mécanique, pour les COMMENTAIRES (25/08/2026).
// La clé d'un commentaire est `nom|texte[:40]` : version tronquée et version
// dépliée tombent sur deux clés distinctes et coexistent. Sans purge,
// __exportBlocked reste bloqué alors que le texte complet est déjà là.
dom = buildNoArticle(false);
{
  const w = dom.window;
  w.__store = {
    p1: { author: 'Laurine Vibert', iso: '2026-08-24', body: 'Annonce complète.', comments: {
      'Miek Vossn|Bonjour,': { name: 'Miek Vossn', text: 'Bonjour,… Voir plus' },
      'Miek Vossn|Bonjour,MPenvoyé,Bonnejournée': { name: 'Miek Vossn', text: 'Bonjour, MP envoyé, Bonne journée' }
    } },
    p2: { author: 'Autre post', iso: '2026-08-24', body: 'Annonce nette.', comments: {
      'Zoé Dubois|Bonjour,': { name: 'Zoé Dubois', text: 'Bonjour,… Voir plus' }
    } }
  };
  const removed = w.__purgeCommentStubs();
  t('__purgeCommentStubs retire la souche couverte', removed.map(r => r.name), ['Miek Vossn']);
  t('la version complète du commentaire est conservée',
    Object.keys(w.__store.p1.comments).length, 1);
  t('__purgeCommentStubs ne touche PAS une vraie troncature',
    Object.keys(w.__store.p2.comments).length, 1);
  t('__exportBlocked bloque sur la vraie troncature seule',
    /Zoé Dubois/.test(w.__exportBlocked('2026-08-20')), true);
}

// ---------------------------------------------------------------------------
// POST PARTAGÉ (25/08/2026) : quand une publication de page est repartagée dans
// le groupe, la carte imbriquée porte SES PROPRES ancres __cft__ — 5 au total sur
// le cas réel observé, toutes du même jeton. L'ancienne garde « le parent contient
// une AUTRE ancre ⇒ stop » coupait donc la racine au-dessus de la carte : `body`
// ressortait VIDE, sans aucun signal (ni __truncated ni __exportBlocked ne voient
// un corps vide). Une offre de 1 677 caractères passait à la trappe.
{
  const dom2 = new JSDOM(`<body><div id="feed">
    <div class="wrapper">
      <h2><a href="/groups/123/user/333/">Cabinet des 5 Calanques</a></h2>
      ${ts('Le 24 aout a 10:00', 'AZshare')}
      <div class="carte-partagee">
        ${ts('Le 20 aout a 09:00', 'AZshare')}
        <a href="?__cft__[0]=AZshare">lien interne</a>
        <div dir="auto">Le Cabinet Veterinaire des 5 Calanques recherche un veterinaire canin pour completer son activite. Temps partiel, statut au choix, a partir de janvier 2027.</div>
      </div>
    </div>
    <div class="wrapper">
      <h2><a href="/groups/123/user/444/">Voisin Duflux</a></h2>
      ${ts('Le 24 aout a 08:00', 'AZvoisin')}
      <div dir="auto">Annonce du post voisin, qui ne doit surtout pas etre aspiree par le post partage.</div>
    </div>
  </div></body>`, { url: 'https://www.facebook.com/groups/123/?sorting_setting=CHRONOLOGICAL', runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom2.window;
  Object.defineProperty(w.Element.prototype, 'innerText', {
    configurable: true, get() { return this.textContent; } });
  w.Element.prototype.getBoundingClientRect = function () {
    const isFlex = this.classList && this.classList.contains('flexbox');
    return isFlex ? { left: 0, right: 1000, top: 0, bottom: 10, width: 1000 }
                  : { left: 0, right: 10, top: 0, bottom: 10, width: 10 };
  };
  const cs2 = w.getComputedStyle.bind(w);
  w.getComputedStyle = (el) => (el.classList && el.classList.contains('flexbox'))
    ? { display: 'flex' } : cs2(el);
  w.eval(SRC);

  const posts = w.__harvestAll();
  t('post partagé : une seule entrée malgré 3 ancres du même jeton', posts.length, 2);
  const part = posts.find(p => /Calanques/.test(p.author || ''));
  t('post partagé : le corps N\'est plus vide', (part && part.body || '').length > 100, true);
  t('post partagé : c\'est bien le texte de la carte imbriquée',
    /5 Calanques recherche un veterinaire canin/.test(part && part.body || ''), true);
  const voisin = posts.find(p => /Voisin/.test(p.author || ''));
  t('post voisin : son corps reste le sien',
    /post voisin/.test(voisin && voisin.body || ''), true);
  t('post partagé : n\'a pas aspiré le voisin',
    /post voisin/.test(part && part.body || ''), false);
  t('__storyToken lit le jeton', w.__storyToken({ getAttribute: () => '?__cft__[0]=AZx&y=1' }), 'AZx');
}

console.log(`\n${ok} ok, ${ko} échec(s)`);
process.exit(ko ? 1 : 0);
