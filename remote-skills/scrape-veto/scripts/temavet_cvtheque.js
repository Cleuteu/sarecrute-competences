// scrape-veto — collecte de la CV-thèque vétérinaire de TÉMAVet Job (job.temavet.fr), côté candidats.
//
// À injecter (contenu entier, via javascript_tool) dans un onglet ouvert sur
// https://job.temavet.fr/CV-theque/veterinaire, avec la session RECRUTEUR de l'utilisateur. Le helper
// ne CLIQUE sur rien : il lit la liste et chaque fiche par fetch (même origine, cookies de la
// session) et sort le tout par download blob vers ~/Downloads, comme pour Facebook. Le jugement et
// la préparation des records se font ensuite hors page, par temavet_cvtheque.py.
//
// ⚠️ Gestes interdits pendant le scrape :
//   - « Télécharger le CV » consomme le quota quotidien de la CV-thèque (30 par jour). La FICHE, elle,
//     ne le consomme pas : vérifié le 28/10/2026, 151 fiches lues par fetch, compteur inchangé. Le
//     quota est relu avant et après la collecte (quota_debut / quota_fin) pour que ça reste vrai.
//   - « Contacter ce candidat », « Proposer un poste », « Ajouter à mes CV favoris » : des gestes
//     visibles du candidat ou du compte, jamais depuis le scrape.
//
// Usage (javascript_tool coupe à 45 s, la collecte tourne donc en tâche de fond) :
//   __tvStart({connus: {...}}) → « lancé » ; lit toute la liste, puis les fiches, une requête à la fois.
//                    connus = n° → date de mise à jour des profils déjà en base, tel que l'imprime
//                    `temavet_cvtheque.py connus` ({} ou rien au premier passage : tout est lu).
//   __tvStatus()  → avancement ; à la fin, etat = « terminé » et fichier = nom du download
//
// Lecture incrémentale (0.17.1) : la liste est triée par date de mise à jour, la plus récente en tête
// (vérifié le 28/10/2026 : une seule inversion sur 150). Une fiche inconnue de la base se lit toujours,
// où qu'elle soit ; une fiche connue se lit jusqu'à ce que TROIS connues d'affilée reviennent à la date
// déjà en base — tout ce qui suit est plus ancien, donc déjà en base tel quel, et n'est pas rechargé
// (trois et non une : la petite inversion du tri ne doit pas arrêter la lecture trop tôt). La liste,
// elle, est toujours lue en entier : c'est elle qui dit quels profils ont disparu.
// Ronde : le tri ne suit pas exactement la date affichée (un profil mis à jour le 23/10 était classé
// parmi ceux de fin septembre), donc un profil modifié peut ne pas remonter. Chaque passage relit en
// plus les fiches connues dont le n° modulo 7 tombe sur le jour : en une semaine de passages
// quotidiens, toutes ont été relues, pour une vingtaine de fiches de plus par passage.
// Pas de pause par setTimeout entre les requêtes : Chrome bride les minuteries d'un onglet en
// arrière-plan (1 s, puis une par MINUTE après 5 min masqué) ; l'attente de chaque réponse suffit à
// espacer les requêtes. Un seul download par chargement de page : Chrome bloque sans prévenir le
// téléchargement automatique suivant. Pour relancer, recharger l'onglet d'abord.
(function () {
  const LISTE = '/CV-theque/veterinaire';
  const lignes = el => el.textContent.split('\n').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);

  // Session recruteur valide = la liste répond sur job.temavet.fr (sinon : redirection vers la page de
  // connexion profil.temavet.fr) ET affiche la date de fin d'accès. La phrase « Pour accéder aux CV des
  // candidats, vous pouvez souscrire… » s'affiche même avec un accès valide : elle ne prouve rien.
  // Les chiffres se lisent dans le TEXTE de la page : dans le HTML, la date de fin est dans son propre
  // <span> (« prendra fin le: <span>20/11/26</span> »).
  window.__tvCheck = async function () {
    const r = await fetch(LISTE, {credentials: 'include'});
    const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
    const t = (doc.body ? doc.body.textContent : '').replace(/\s+/g, ' ');
    const total = +((t.match(/(\d+) CV de vétérinaires/) || [])[1] || 0);
    const acces_fin = (t.match(/accès prendra fin le ?: ?([\d\/]+)/) || [])[1] || '';
    const quota = ((t.match(/quotidien ?: ?(\d+ ?\/ ?\d+)/) || [])[1] || '').replace(/\s+/g, '');
    return {ok: r.url.indexOf('job.temavet.fr' + LISTE) >= 0 && !!acces_fin, url: r.url, total, acces_fin, quota};
  };

  const dateDe = t => { const m = t.match(/Dernière mise à jour ?: ?(\d{2})\/(\d{2})\/(\d{4})/); return m ? m[3] + '-' + m[2] + '-' + m[1] : ''; };

  window.__tvStart = function (opts) {
    if (window.__tvState && window.__tvState.etat === 'en cours') return 'déjà en cours';
    const connus = (opts && opts.connus) || {};
    const st = window.__tvState = {etat: 'en cours', pages: 0, cartes: [], profils: {}, faits: 0, sautees: 0,
                                   connus: Object.keys(connus).length};
    (async () => {
      try {
        const chk = await window.__tvCheck();
        Object.assign(st, {total: chk.total, acces_fin: chk.acces_fin, quota_debut: chk.quota});
        if (!chk.ok) {
          st.etat = 'arrêt : pas de session recruteur TÉMAVet valide (' + chk.url + ')';
          return;
        }
        // 1) La liste, page par page (15 cartes par page), jusqu'à une page sans carte nouvelle.
        const vus = new Set();
        for (let p = 1; p <= 100; p++) {
          const h = await (await fetch(LISTE + '?page=' + p, {credentials: 'include'})).text();
          const doc = new DOMParser().parseFromString(h, 'text/html');
          const neufs = [...doc.querySelectorAll('a[href*="/users/veterinaire/"]')].filter(a => !vus.has(a.href));
          if (!neufs.length) break;
          for (const a of neufs) {
            vus.add(a.href);
            st.cartes.push({id: a.href.split('/').pop(), url: a.href, lignes: lignes(a)});
          }
          st.pages = p;
        }
        // 2) Les fiches, dans l'ordre de la liste : le <main>, débarrassé de ce qui ne porte pas de texte
        //    utile. Une fiche refusée (« Vous n'avez pas accès à la page profil ») revient sur la liste :
        //    r.url le dit.
        let memes = 0, arret = false;
        const ronde = Math.floor(Date.now() / 86400000) % 7;
        for (const c of st.cartes) {
          if (arret && connus[c.id] && +c.id % 7 !== ronde) { st.sautees++; continue; }
          const r = await fetch(c.url, {credentials: 'include'});
          const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
          const m = doc.querySelector('main') || doc.body;
          m.querySelectorAll('svg,script,style,img,form,template').forEach(x => x.remove());
          st.profils[c.id] = {url: r.url, status: r.status, html: m.innerHTML.replace(/\s+/g, ' ')};
          st.faits++;
          if (connus[c.id]) {
            memes = dateDe(m.textContent.replace(/\s+/g, ' ')) === connus[c.id] ? memes + 1 : 0;
            arret = memes >= 3;
          }
        }
        st.quota_fin = (await window.__tvCheck()).quota;
        const jour = new Date().toISOString().slice(0, 10);
        const data = {collecte_le: jour, total_annonce: st.total, acces_fin: st.acces_fin,
                      quota_debut: st.quota_debut, quota_fin: st.quota_fin, connus: st.connus, sautees: st.sautees,
                      cartes: st.cartes, profils: st.profils};
        const blob = new Blob([JSON.stringify(data)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'temavet_cv_' + jour + '.json';
        document.body.appendChild(a); a.click();
        setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 3000);
        st.fichier = a.download;
        st.etat = 'terminé';
      } catch (e) {
        st.etat = 'erreur : ' + e.message;
      }
    })();
    return 'lancé';
  };

  window.__tvStatus = function () {
    const s = window.__tvState;
    if (!s) return 'pas lancé';
    return {etat: s.etat, total: s.total, pages: s.pages, cartes: s.cartes.length, fiches: s.faits, sautees: s.sautees,
            connus: s.connus, acces_fin: s.acces_fin, quota_debut: s.quota_debut, quota_fin: s.quota_fin, fichier: s.fichier};
  };
  return 'helpers TÉMAVet injectés';
})();
