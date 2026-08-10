/* ============================================================================
 * scrape-veto — helpers à injecter dans la page Facebook via javascript_tool.
 *
 * Usage : Read ce fichier, puis passe TOUT son contenu comme `text` à
 * javascript_tool (action javascript_exec). Après une navigation (reload,
 * clic qui part en permalink…), le window est vidé → RÉ-INJECTE ce fichier.
 *
 * Fournit sur window :
 *   __decodeTS(anchor)   -> string  : décode un timestamp de post obfusqué
 *   __parseTS(str)       -> {iso, ageH} : "24 min" / "Le 20 juin à 19:41" -> date
 *   __harvestAll()       -> [{author, authorUrl, decoded, iso, ageH, pid, body, comments[]}]
 *   __profileUrl(anchor) -> string  : lien de profil FB depuis une ancre de nom
 *   __store, __merge()   : accumulateur persistant AUTO-RÉPARANT (garde le corps
 *                          le plus long → corrige la troncature "Voir plus")
 *   __expandPostText()   -> n  : clique les "Voir plus" des posts
 *   __expandCommentText()-> n  : idem DANS les commentaires (jamais "Voir plus de
 *                          commentaires", qui navigue et viderait le store)
 *   __truncated()        -> [{author,iso,len}] : posts encore tronqués
 *   __truncatedComments()-> [{post,iso,name,len}] : commentaires encore tronqués
 *   __exportBlocked(borne)-> '' ou raison : garde UNIQUE à appeler avant l'export
 *   __orphanComments     : nb de commentaires non rattachés au dernier harvest (leur
 *                          post n'était pas rendu — ils repasseront)
 *   __cleanBody(str)     -> string : corps nettoyé des marqueurs FB pour l'export
 * ========================================================================== */

window.__veto = window.__veto || {};

/* --- Décodage des timestamps de posts (anti-scraping FB) -------------------
 * FB mélange les caractères du timestamp via CSS `order` dans un conteneur
 * flex `overflow:hidden` de largeur fixe. Les leurres débordent (clippés).
 * On garde uniquement les glyphes réellement DANS la boîte visible, triés par
 * position (haut->bas, gauche->droite). */
window.__decodeTS = function (tsA) {
  const flex = Array.from(tsA.querySelectorAll('*')).find(e => getComputedStyle(e).display === 'flex');
  if (!flex) return null;
  const fr = flex.getBoundingClientRect();
  const vis = Array.from(flex.children).map(k => {
    const r = k.getBoundingClientRect();
    return { t: k.textContent, left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: r.width };
  }).filter(k => k.w > 0 && k.left >= fr.left - 1 && k.right <= fr.right + 1 && k.top >= fr.top - 1 && k.bottom <= fr.bottom + 1);
  vis.sort((a, b) => Math.abs(a.top - b.top) > 3 ? a.top - b.top : a.left - b.left);
  return vis.map(v => v.t).join('').trim();
};

/* --- Conversion timestamp relatif/absolu -> date absolue (horloge du navigateur) */
window.__parseTS = function (s) {
  const MONTHS = { janvier: 0, 'février': 1, fevrier: 1, mars: 2, avril: 3, mai: 4, juin: 5, juillet: 6, 'août': 7, aout: 7, septembre: 8, octobre: 9, novembre: 10, 'décembre': 11, decembre: 11 };
  const pad = n => String(n).padStart(2, '0');
  const isoOf = d => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  // FB intercale des caractères invisibles (U+034F, zero-width, soft hyphen…)
  // ENTRE les glyphes du timestamp décodé ("1͏4͏ ͏h͏") → sans ce nettoyage,
  // TOUS les regex ci-dessous échouent et iso ressort null pour chaque post.
  s = (s || '').replace(/[͏​-‍⁠﻿­]/g, '').trim();
  const now = new Date();
  let m;
  if (/^\d+\s*(s|sec)/i.test(s)) return { iso: isoOf(now), ageH: 0 };
  if (/^\d+\s*min/i.test(s)) return { iso: isoOf(now), ageH: 0.2 };
  if ((m = s.match(/^(\d+)\s*h/i))) { const h = +m[1]; return { iso: isoOf(new Date(now - h * 3600e3)), ageH: h }; }
  if ((m = s.match(/^(\d+)\s*j/i))) { const j = +m[1]; return { iso: isoOf(new Date(now - j * 86400e3)), ageH: j * 24 }; }
  let hh = 12, mm = 0; const tm = s.match(/(\d{1,2}):(\d{2})/); if (tm) { hh = +tm[1]; mm = +tm[2]; }
  if (/hier/i.test(s)) { const d = new Date(now); d.setDate(d.getDate() - 1); d.setHours(hh, mm, 0, 0); return { iso: isoOf(d), ageH: (now - d) / 3600e3 }; }
  if ((m = s.match(/(\d{1,2})\s+([a-zéûôàêè]+)(?:\s+(\d{4}))?/i))) {
    const day = +m[1], mo = MONTHS[m[2].toLowerCase()];
    if (mo != null) { const y = m[3] ? +m[3] : now.getFullYear(); const d = new Date(y, mo, day, hh, mm, 0); return { iso: isoOf(d), ageH: (now - d) / 3600e3 }; }
  }
  return { iso: null, ageH: null };
};

/* --- Lien de profil FB depuis une ancre de nom (auteur ou commentateur) -----
 * FB rend les noms dans un groupe avec un href `/groups/{gid}/user/{uid}/…`
 * (parfois `/profile.php?id={uid}`). On renvoie l'URL de profil canonique
 * `https://www.facebook.com/{uid}` — validé en live : elle redirige vers le
 * profil réel (ex. → /mathilde.marcoin), donc directement exploitable par un
 * recruteur. Renvoie '' si l'ancre est absente (cas "Membre anonyme"). */
/* --- Groupe courant : id lu dans l'URL, jamais codé en dur ------------------
 * Le scrape couvre plusieurs groupes (un canal Airtable par groupe) : tout ce qui
 * dépend du groupe (permalink, rattachement du post à son canal) se déduit d'ici. */
window.__gid = () => (location.pathname.match(/\/groups\/(\d+)/) || [])[1] || '';

window.__profileUrl = function (a) {
  const h = a ? (a.getAttribute('href') || '') : '';
  const uid = (h.match(/\/user\/(\d+)/) || h.match(/profile\.php\?id=(\d+)/) || [])[1] || '';
  return uid ? 'https://www.facebook.com/' + uid : '';
};

/* --- Récolte complète : posts + commentaires rattachés par CONTAINMENT ----- */
window.__harvestAll = function () {
  // Anchors de timestamp de post = href contient __cft__ et décode en un temps
  const tsAnchors = Array.from(document.querySelectorAll('a')).filter(a => {
    const h = a.getAttribute('href') || '';
    if (!h.includes('__cft__')) return false;
    const t = (a.innerText || '').replace(/\s/g, '');
    if (!(t.length >= 12 && /[0-9]/.test(t))) return false;
    const d = window.__decodeTS(a);
    return d && /\d/.test(d);
  });
  const postByAnchor = new Map();
  for (const tsA of tsAnchors) {
    let root = tsA;
    for (let i = 0; i < 14; i++) {
      const next = root.parentElement;
      if (!next) break;
      // ⚠️ Ne JAMAIS laisser la racine d'un post engloutir le timestamp d'un AUTRE post :
      // sinon l'auteur et le corps peuvent être lus chez le voisin. (10 août 2026)
      if (tsAnchors.some(x => x !== tsA && next.contains(x))) break;
      root = next;
      if ((root.innerText || '').length > 500) break;
    }
    let author = '';
    const strong = root.querySelector('h2 strong,h3 strong,h2 a,h3 a,strong');
    if (strong) author = (strong.innerText || '').trim().split('\n')[0];
    // NB: ne PAS retomber sur "Membre anonyme" via innerText (un commentateur
    // anonyme dans le conteneur fausserait l'auteur). On matche par corps.
    // Profil de l'auteur : l'ancre du header porte /groups/{gid}/user/{uid}/
    // (validé en live : présent sur 100 % des auteurs nommés, absent sur
    // "Membre anonyme" → discriminant naturel, on ne devine rien).
    // ⚠️ Si authorUrl est vide alors que `author` est non vide et non anonyme,
    // c'est que `author` vient du fallback `strong` (nom mal capté, souvent un
    // post sponsorisé) → signal de qualité sur le nom.
    const authorUrl = window.__profileUrl(root.querySelector('h2 a[href],h3 a[href]'));
    // id du post : chiffres OU token pfbid…, depuis /posts/, /permalink/ ou story_fbid=
    // (le href de l'ancre de timestamp est vide sur les posts à timestamp obfusqué :
    //  on lit donc l'innerHTML du conteneur, où le permalink est toujours présent).
    const pid = (root.innerHTML.match(/\/(?:posts|permalink)\/(pfbid\w+|\d+)/) || [])[1]
             || (root.innerHTML.match(/story_fbid=(pfbid\w+|\d+)/) || [])[1] || '';
    const gid = window.__gid();
    const permalink = (gid && pid) ? `https://www.facebook.com/groups/${gid}/posts/${pid}/` : '';
    const blocks = Array.from(root.querySelectorAll('div[dir="auto"]')).map(d => (d.innerText || '').trim()).filter(t => t.length > 2).sort((a, b) => b.length - a.length);
    const parsed = window.__parseTS(window.__decodeTS(tsA));
    postByAnchor.set(tsA, { author, authorUrl, decoded: window.__decodeTS(tsA), iso: parsed.iso, ageH: parsed.ageH, gid, pid, permalink, body: blocks[0] || '', comments: [] });
  }
  // Commentaires = div[role=article][aria-label="Commentaire de {Nom} il y a {temps}"]
  const cArts = Array.from(document.querySelectorAll('div[role="article"][aria-label]')).filter(a => /^Commentaire de/i.test(a.getAttribute('aria-label') || ''));
  window.__orphanComments = 0;
  for (const a of cArts) {
    // Rattachement par le CONTENEUR du post (son propre div[role="article"]), et non
    // par proximité dans le flux.
    //
    // ⚠️ Pourquoi (bug corrigé le 10 août 2026) : la virtualisation de FB est PARTIELLE
    // — un commentaire peut rester rendu alors que l'ancre de timestamp de SON post ne
    // l'est plus. L'ancienne heuristique remontait alors au plus proche timestamp qui
    // précède, c'est-à-dire celui du post VOISIN : le même jeu de commentaires se
    // retrouvait dupliqué sur un post qui ne les portait pas. Un commentaire mal
    // rattaché est pire qu'un commentaire manquant (il fabrique un faux candidat sous
    // une annonce qui n'est pas la sienne), donc en cas de doute on ABANDONNE : le post
    // repassera à un cycle suivant, où son en-tête sera rendu.
    const ownerArticle = (function (el) {
      let e = el.parentElement;
      while (e) {
        if (e.matches && e.matches('div[role="article"]') &&
            !/^Commentaire de/i.test(e.getAttribute('aria-label') || '')) return e;
        e = e.parentElement;
      }
      return null;
    })(a);
    let parent = null;
    if (ownerArticle) {
      // Le 1er timestamp du conteneur est celui de son en-tête. Aucun ⇒ post non capté
      // à ce cycle : on ne devine pas.
      const own = tsAnchors.filter(x => ownerArticle.contains(x));
      if (own.length) parent = postByAnchor.get(own[0]);
      else { window.__orphanComments++; continue; }
    } else {
      // Repli (structure FB inattendue) : ancienne heuristique de proximité.
      let e = a.parentElement;
      while (e) {
        const contained = tsAnchors.filter(tsA => e.contains(tsA));
        if (contained.length) {
          const before = contained.filter(tsA => tsA.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING);
          const pick = (before.length ? before : contained);
          pick.sort((x, y) => (x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING) ? -1 : 1);
          parent = postByAnchor.get(pick[pick.length - 1]); break;
        }
        e = e.parentElement;
      }
    }
    if (!parent) { window.__orphanComments++; continue; }
    const m = a.getAttribute('aria-label').match(/^Commentaire de (.+?)(?: il y a (.+))?$/i);
    const da = a.querySelector('div[dir="auto"]');
    const name = m ? m[1].trim() : '';
    // Profil du commentateur : on privilégie l'ancre dont le texte EST le nom du
    // commentaire (une réponse imbriquée pourrait sinon fournir la 1re ancre) ;
    // à défaut, la première ancre de profil de l'article.
    const cAnchors = Array.from(a.querySelectorAll('a[href*="/user/"],a[href*="profile.php?id="]'));
    const cA = cAnchors.find(x => (x.innerText || '').trim() === name) || cAnchors[0];
    parent.comments.push({ name, profileUrl: window.__profileUrl(cA), time: m && m[2] ? m[2].trim() : '', text: da ? (da.innerText || '').trim() : '' });
  }
  return Array.from(postByAnchor.values());
};

/* --- Accumulateur persistant (survit à la virtualisation) ------------------
 * ⚠️ AUTO-RÉPARANT : __merge garde TOUJOURS le corps le plus long vu pour une
 * clé donnée. C'est ce qui corrige la troncature "Voir plus" : si un post est
 * capté tronqué (avant dépliage) puis re-capté déplié à un cycle suivant, la
 * version complète (plus longue) écrase la version tronquée. Ne JAMAIS revenir
 * à un merge qui fige le corps à la première capture — c'était le bug qui
 * laissait des posts tronqués en base.
 * La clé (auteur + 40 premiers caractères non-espace du corps) est stable entre
 * la version tronquée et la version complète, donc la mise à jour retombe bien
 * sur la même entrée. */
window.__store = window.__store || {};
window.__postKey = p => (p.author || '') + '|' + (p.body || '').replace(/\s+/g, '').slice(0, 40);
window.__isTrunc = b => /(?:…\s*)?(?:En )?[Vv]oir plus\s*$/.test((b || '').trim());
window.__merge = function () {
  for (const p of window.__harvestAll()) {
    const k = window.__postKey(p);
    const s = window.__store[k];
    if (!s) { window.__store[k] = { author: p.author, authorUrl: p.authorUrl, decoded: p.decoded, iso: p.iso, ageH: p.ageH, gid: p.gid, pid: p.pid, permalink: p.permalink, body: p.body, comments: {} }; }
    else {
      if (!s.gid && p.gid) s.gid = p.gid;                 // groupe d'où vient le post
      if (!s.pid && p.pid) s.pid = p.pid;                 // complète le pid quand dispo
      if (!s.permalink && p.permalink) s.permalink = p.permalink; // idem permalink
      if (!s.authorUrl && p.authorUrl) s.authorUrl = p.authorUrl; // idem profil auteur
      if (!s.iso && p.iso) { s.iso = p.iso; s.ageH = p.ageH; s.decoded = p.decoded; }
      // GARDE LE CORPS LE PLUS LONG → auto-corrige la troncature "Voir plus".
      // Un corps non-tronqué l'emporte toujours sur un corps tronqué ; sinon on
      // prend simplement le plus long.
      const cur = s.body || '', nw = p.body || '';
      const better = (window.__isTrunc(cur) && !window.__isTrunc(nw)) ||
                     (window.__isTrunc(cur) === window.__isTrunc(nw) && nw.length > cur.length);
      if (better) s.body = nw;
    }
    for (const c of p.comments) {
      const ck = (c.name || '') + '|' + (c.text || '').replace(/\s+/g, '').slice(0, 40);
      if (ck.replace(/\|/g, '').trim()) {
        // On écrase la capture précédente, mais sans PERDRE un profil déjà vu :
        // une re-capture partielle peut ressortir profileUrl vide.
        const prev = window.__store[k].comments[ck];
        if (prev && prev.profileUrl && !c.profileUrl) c.profileUrl = prev.profileUrl;
        window.__store[k].comments[ck] = c;
      }
    }
  }
  return Object.keys(window.__store).length;
};

/* --- Expansion SÛRE du contenu des posts (jamais les commentaires) ---------
 * ⚠️ Ne PAS cliquer "Voir plus de commentaires" / le compteur de commentaires :
 * ça navigue vers le permalink et vide le window. On ne déplie que le texte
 * tronqué des posts ("Voir plus" / "En voir plus"). */
window.__EXPAND_RX = /^(?:en )?voir plus$|^afficher la suite$|^afficher plus$/i;

window.__expandPostText = function () {
  let n = 0;
  for (const b of document.querySelectorAll('div[role="button"],span[role="button"]')) {
    if (b.closest('a')) continue;
    const t = (b.innerText || '').trim();
    if (window.__EXPAND_RX.test(t)) { try { b.click(); n++; } catch (e) {} }
  }
  return n;
};

/* --- Expansion du texte des COMMENTAIRES (sûre) -----------------------------
 * Complète __expandPostText, qui déplie au passage la plupart des commentaires mais
 * en laisse échapper (commentaire rendu après le clic, expander imbriqué dans une
 * réponse). Restreint aux boutons SITUÉS DANS un article de commentaire, avec le même
 * test de texte strict : « Voir plus de commentaires » et « N réponses » ne matchent
 * pas le regex, donc on ne déclenche jamais la navigation vers le permalink (qui
 * viderait window.__store). */
window.__expandCommentText = function () {
  let n = 0;
  for (const art of document.querySelectorAll('div[role="article"][aria-label]')) {
    if (!/^Commentaire de/i.test(art.getAttribute('aria-label') || '')) continue;
    for (const b of art.querySelectorAll('div[role="button"],span[role="button"]')) {
      if (b.closest('a')) continue;
      const t = (b.innerText || '').trim();
      if (window.__EXPAND_RX.test(t)) { try { b.click(); n++; } catch (e) {} }
    }
  }
  return n;
};

/* --- Anti-troncature : posts du store dont le corps est encore tronqué ------
 * À appeler AVANT l'export. S'il renvoie une liste non vide, il reste des
 * "Voir plus" non dépliés : re-scroller jusqu'à ces posts (ils sont classés du
 * plus récent au plus ancien, donc en général en haut du fil), ré-appeler
 * __expandPostText() + attendre ≥1,5 s + __merge(), et re-vérifier. */
window.__truncated = function () {
  return Object.values(window.__store)
    .filter(p => window.__isTrunc(p.body))
    .map(p => ({ author: p.author || '(anon)', iso: p.iso, len: (p.body || '').length }));
};

/* --- Idem pour les COMMENTAIRES du store -----------------------------------
 * __truncated() ne regardait que les posts : un commentaire pouvait partir en base
 * figé sur « … Voir plus » sans qu'aucun garde-fou ne le signale (constaté le
 * 10 août 2026). À vérifier AUSSI avant l'export — cf. __exportBlocked(). */
window.__truncatedComments = function () {
  const out = [];
  for (const p of Object.values(window.__store)) {
    for (const c of Object.values(p.comments || {})) {
      if (window.__isTrunc(c.text)) {
        out.push({ post: p.author || '(anon)', iso: p.iso, name: c.name, len: (c.text || '').length });
      }
    }
  }
  return out;
};

/* --- Garde unique à appeler AVANT l'export ----------------------------------
 * Renvoie '' si l'export peut se faire, sinon la raison. Regroupe les deux
 * contrôles pour qu'on ne puisse plus en oublier un.
 * Usage : const stop = window.__exportBlocked('2026-08-07'); if (stop) return stop; */
window.__exportBlocked = function (borne) {
  const inWin = p => !borne || (p.iso && p.iso >= borne);
  const tp = window.__truncated().filter(inWin);
  const tc = window.__truncatedComments().filter(inWin);
  if (tp.length) return 'STOP — ' + tp.length + ' post(s) tronqué(s) : ' + JSON.stringify(tp);
  if (tc.length) return 'STOP — ' + tc.length + ' commentaire(s) tronqué(s) : ' + JSON.stringify(tc);
  return '';
};

/* --- Nettoyage du corps pour l'export (retire les marqueurs FB finaux) ------ */
window.__cleanBody = b => (b || '').replace(/\s+/g, ' ').replace(/\s*(?:…\s*)?(?:En )?[Vv]oir (?:plus|moins)\s*$/, '').trim();

/* --- __alive : le rendu tourne-t-il vraiment ? -------------------------------
 * Chrome suspend requestAnimationFrame et bride les timers dès que sa fenêtre
 * est masquée (typiquement derrière l'app Claude). Le fil FB reste alors sur
 * 2-3 posts + des skeletons, scrollHeight ne bouge plus, et RIEN ne le signale :
 * ça ressemble à un blocage Facebook alors que c'est du throttling de rendu.
 * frames ≈ 0 (frozen) ⇒ ramener Chrome au premier plan (scripts/focus_chrome.sh),
 * puis re-tester. Spoofer visibilityState ne sert à rien : c'est le rendu qui
 * est suspendu, pas seulement le flag.
 * Usage : await window.__alive();   // ~1 s */
window.__alive = function (ms) {
  ms = ms || 800;
  return new Promise(resolve => {
    let frames = 0, stop = false;
    const tick = () => { if (!stop) { frames++; requestAnimationFrame(tick); } };
    requestAnimationFrame(tick);
    const h0 = document.body.scrollHeight;
    const t0 = Date.now();
    setTimeout(() => {
      stop = true;
      const dt = Date.now() - t0;
      resolve({
        frozen: frames < 5,
        frames: frames,
        fps: Math.round(frames / (dt / 1000)),
        visibility: document.visibilityState,
        focused: document.hasFocus(),
        articles: document.querySelectorAll('div[role="article"]').length,
        height: document.body.scrollHeight,
        heightDelta: document.body.scrollHeight - h0,
        stored: Object.keys(window.__store || {}).length
      });
    }, ms);
  });
};

/* --- __chrono : le fil est-il vraiment trié du plus récent au plus ancien ? --
 * `?sorting_setting=CHRONOLOGICAL` n'est pas garanti : Facebook peut retomber sur
 * le tri par pertinence (et l'Url enregistrée d'un canal, elle, ne trie rien du
 * tout). Un fil non chronologique casse SILENCIEUSEMENT la fenêtre temporelle :
 * le critère d'arrêt « la queue a franchi la borne » n'a plus de sens, et on
 * conclut « fin du fil » sur un vieux post remonté par l'algorithme.
 * À appeler après le 1er merge, AVANT de lancer les cycles.
 * inversions > 1 ⇒ ne pas collecter : corriger le tri d'abord. */
window.__chrono = function (n) {
  const ps = window.__harvestAll().filter(p => p.iso).slice(0, n || 8);
  const isos = ps.map(p => p.iso);
  let inversions = 0;
  for (let i = 1; i < isos.length; i++) if (isos[i] > isos[i - 1]) inversions++;
  // Le paramètre compte AUTANT que les dates observées : des dates décroissantes
  // par chance (peu de posts, tri par pertinence qui remonte du récent) ne prouvent
  // rien. Sans le paramètre, on re-navigue — c'est déterministe et ça ne coûte rien.
  const param = /sorting_setting=CHRONOLOGICAL/i.test(location.search);
  return {
    ok: param && isos.length >= 2 && inversions <= 1,
    inversions: inversions,
    isos: isos,
    url: location.pathname + location.search,
    tri: param ? 'param présent' : 'PARAM ABSENT'
  };
};

'helpers scrape-veto injectés';
