// Épingle la lecture incrémentale de la CV-thèque TÉMAVet (scrape-veto 0.17.1, 28/10/2026).
//
// Au premier passage, temavet_cvtheque.js chargeait les 151 fiches à chaque collecte, avec la session
// recruteur de Sarah. La liste étant triée par date de mise à jour, il s'arrête désormais après trois
// fiches connues d'affilée revenues à leur date en base — sauf pour les fiches inconnues, toujours lues
// où qu'elles soient. La liste, elle, est lue en entier (c'est elle qui donne les disparus).
//
// Le serveur est simulé : fetch renvoie des pages de liste et des fiches synthétiques.
const fs = require('fs');
const { JSDOM, VirtualConsole } = require('jsdom');   // npm i --no-save jsdom@22
const SRC = fs.readFileSync(require('path').join(__dirname, '..', 'remote-skills/scrape-veto/scripts/temavet_cvtheque.js'), 'utf8');

let ok = 0, ko = 0;
const t = (l, got, want) => { const p = JSON.stringify(got) === JSON.stringify(want); p ? ok++ : ko++;
  console.log((p ? '  ok    ' : '  ECHEC ') + l + (p ? '' : `\n          obtenu=${JSON.stringify(got)}\n          attendu=${JSON.stringify(want)}`)); };

const ORIGINE = 'https://job.temavet.fr';
// Huit profils, du plus récemment mis à jour au plus ancien, quatre par page de liste.
const MAJ = {1: '28/10/2026', 2: '27/10/2026', 3: '24/10/2026', 4: '22/10/2026', 5: '20/10/2026', 6: '18/10/2026',
             7: '16/10/2026', 8: '15/10/2026'};
const iso = d => d.split('/').reverse().join('-');
const PAGES = {1: [1, 2, 3, 4], 2: [5, 6, 7, 8]};

// Jour de la ronde (n° modulo 7) : 3 par défaut, aucun des n° 5 à 8 n'y tombe (5, 6, 0, 1).
async function collecte(connus, jour = 3) {
  const vc = new VirtualConsole();   // le clic de téléchargement « navigue » vers un blob : jsdom s'en plaint, sans effet
  const dom = new JSDOM('<body></body>', { url: ORIGINE + '/CV-theque/veterinaire', runScripts: 'outside-only', virtualConsole: vc });
  const w = dom.window;
  const lues = [];
  let telecharge = null;
  w.fetch = async url => {
    const u = new URL(url, ORIGINE);
    let html = '';
    if (u.pathname === '/CV-theque/veterinaire' && !u.searchParams.get('page'))
      html = '<h1>8 CV de vétérinaires</h1><div>Votre accès prendra fin le: <span>20/11/26</span></div>'
           + '<p>Limite de téléchargement de CV quotidien : 8 / 30</p>';
    else if (u.pathname === '/CV-theque/veterinaire')
      html = (PAGES[u.searchParams.get('page')] || []).map(n =>
        `<a href="${ORIGINE}/users/veterinaire/${n}"><div>Profil ${n}</div><div>Praticien</div></a>`).join('');
    else {
      const n = u.pathname.split('/').pop();
      lues.push(+n);
      html = `<main><div class="text-base font-semibold"> Profil ${n} </div>`
           + `<div> Dernière mise à jour : ${MAJ[n]} </div></main>`;
    }
    return { url: u.href, status: 200, text: async () => html };
  };
  w.Date.now = () => (jour + 0.5) * 86400000;
  w.URL.createObjectURL = () => 'blob:' + ORIGINE + '/x';
  w.URL.revokeObjectURL = () => {};
  w.HTMLAnchorElement.prototype.click = function () { telecharge = this.download; };
  w.eval(SRC);
  w.__tvStart(connus === undefined ? undefined : { connus });
  while (w.__tvState.etat === 'en cours') await new Promise(r => setTimeout(r, 2));
  const st = w.__tvStatus();
  w.close();
  return { st, lues, telecharge };
}

(async () => {
  const tous = Object.fromEntries(Object.entries(MAJ).map(([n, d]) => [n, iso(d)]));
  const sauf = (o, ...ids) => Object.fromEntries(Object.entries(o).filter(([n]) => !ids.includes(+n)));

  console.log('\npremier passage : rien en base, tout est lu');
  let r = await collecte();
  t('les 8 fiches sont chargées', r.lues, [1, 2, 3, 4, 5, 6, 7, 8]);
  t('la liste entière est lue', [r.st.cartes, r.st.pages], [8, 2]);
  t('export téléchargé', [r.st.etat, r.telecharge && r.telecharge.startsWith('temavet_cv_')], ['terminé', true]);

  console.log('\npassage suivant : un nouveau profil en tête, le reste inchangé');
  r = await collecte(sauf(tous, 1));
  t('le nouveau, puis trois connus inchangés, puis arrêt', r.lues, [1, 2, 3, 4]);
  t('les fiches non rechargées sont comptées', [r.st.fiches, r.st.sautees, r.st.connus], [4, 4, 7]);
  t('la liste reste lue en entier (disparus)', r.st.cartes, 8);

  console.log('\nune fiche inconnue plus bas dans la liste (profil réapparu) : lue quand même');
  r = await collecte(sauf(tous, 1, 7));
  t('n°7 inconnu, lu malgré l\'arrêt', r.lues, [1, 2, 3, 4, 7]);

  console.log('\nun profil connu mis à jour remet le compteur à zéro');
  r = await collecte(Object.assign(sauf(tous, 1), { 3: '2026-09-01' }));
  t('2 inchangé, 3 changé (compteur à zéro), puis 4, 5, 6 inchangés', r.lues, [1, 2, 3, 4, 5, 6]);

  console.log('\nla ronde du jour relit une fiche connue au-delà de l\'arrêt');
  r = await collecte(sauf(tous, 1), 5);
  t('n°5 (5 modulo 7 = jour 5) relu, les autres sautés', [r.lues, r.st.sautees], [[1, 2, 3, 4, 5], 3]);

  console.log('\nconnus vide (premier passage explicite) : tout est lu');
  r = await collecte({});
  t('les 8 fiches', r.lues.length, 8);

  console.log(`\n${ok} ok, ${ko} échec(s)`);
  process.exit(ko ? 1 : 0);
})();
