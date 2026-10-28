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
//   __tvStart()   → « lancé » ; liste toutes les pages puis lit chaque fiche, une requête à la fois
//   __tvStatus()  → avancement ; à la fin, etat = « terminé » et fichier = nom du download
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

  window.__tvStart = function () {
    if (window.__tvState && window.__tvState.etat === 'en cours') return 'déjà en cours';
    const st = window.__tvState = {etat: 'en cours', pages: 0, cartes: [], profils: {}, faits: 0};
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
        // 2) Chaque fiche : le <main>, débarrassé de ce qui ne porte pas de texte utile. Une fiche
        //    refusée (« Vous n'avez pas accès à la page profil ») revient sur la liste : r.url le dit.
        for (const c of st.cartes) {
          const r = await fetch(c.url, {credentials: 'include'});
          const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
          const m = doc.querySelector('main') || doc.body;
          m.querySelectorAll('svg,script,style,img,form,template').forEach(x => x.remove());
          st.profils[c.id] = {url: r.url, status: r.status, html: m.innerHTML.replace(/\s+/g, ' ')};
          st.faits++;
        }
        st.quota_fin = (await window.__tvCheck()).quota;
        const jour = new Date().toISOString().slice(0, 10);
        const data = {collecte_le: jour, total_annonce: st.total, acces_fin: st.acces_fin,
                      quota_debut: st.quota_debut, quota_fin: st.quota_fin, cartes: st.cartes, profils: st.profils};
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
    return {etat: s.etat, total: s.total, pages: s.pages, cartes: s.cartes.length, fiches: s.faits,
            acces_fin: s.acces_fin, quota_debut: s.quota_debut, quota_fin: s.quota_fin, fichier: s.fichier};
  };
  return 'helpers TÉMAVet injectés';
})();
