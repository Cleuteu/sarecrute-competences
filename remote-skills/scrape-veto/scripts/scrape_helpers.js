/* ============================================================================
 * scrape-veto — helpers à injecter dans la page Facebook via javascript_tool.
 *
 * Usage : Read ce fichier, puis passe TOUT son contenu comme `text` à
 * javascript_tool (action javascript_exec). Après une navigation (reload,
 * clic qui part en permalink…), le window est vidé → RÉ-INJECTE ce fichier.
 *
 * Fournit sur window :
 *   __decodeTS(anchor)   -> string  : décode un timestamp de post (SVG, obfusqué
 *                          ou clair) ; s'appuie sur __decodeTSSvg / __decodeTSGeom
 *   __isTsAnchor(anchor) -> bool    : cette ancre est-elle le timestamp d'un POST ?
 *                          (rejette les ancres de commentaire)
 *   __parseTS(str)       -> {iso, ageH} : "24 min" / "Le 20 juin à 19:41" -> date
 *   __harvestAll()       -> [{author, authorUrl, decoded, iso, ageH, pid, body, comments[]}]
 *   __profileUrl(anchor) -> string  : lien de profil FB depuis une ancre de nom
 *   __store, __merge()   : accumulateur persistant AUTO-RÉPARANT (garde le corps
 *                          le plus long → corrige la troncature "Voir plus")
 *   __expandPostText()   -> n  : clique les "Voir plus" des posts
 *   __expandCommentText()-> n  : idem DANS les commentaires (jamais "Voir plus de
 *                          commentaires", qui navigue et viderait le store)
 *   __expandVisible(pad) -> n  : idem __expandPostText mais borné au viewport
 *                          (obligatoire sur les fils longs : sinon timeout CDP)
 *   __commentFull(art)   -> string : texte INTÉGRAL d'un commentaire (tous ses
 *                          paragraphes, pas seulement le premier)
 *   __purgeStubs()       -> [..] : retire les doublons tronqués non dépliables
 *   __purgeCommentStubs()-> [..] : idem pour les commentaires
 *   __storyToken(anchor) -> string : jeton __cft__ = identité du POST d'une ancre
 *   __inComment(el)      -> bool    : cet élément est-il DANS un commentaire ?
 *                          (borne les lectures author/authorUrl/body du post)
 *   __truncated()        -> [{author,iso,len}] : posts encore tronqués
 *   __truncatedComments()-> [{post,iso,name,len}] : commentaires encore tronqués
 *   __emptyBodies(borne) -> [{author,iso,permalink}] : posts au corps VIDE
 *                          (à contrôler avant l'export ; non bloquant)
 *   __exportBlocked(borne)-> '' ou raison : garde UNIQUE à appeler avant l'export
 *                          (purge les souches elle-même, cf. sa doc)
 *   __orphanComments     : nb de commentaires non rattachés au dernier harvest (leur
 *                          post n'était pas rendu — ils repasseront)
 *   __cleanBody(str)     -> string : corps nettoyé des marqueurs FB pour l'export
 * ========================================================================== */

window.__veto = window.__veto || {};

/* --- Décodage des timestamps de posts (anti-scraping FB) -------------------
 * TROIS régimes coexistent sur le fil, d'où l'ordre d'essai de __decodeTS :
 *
 * 1. SVG (majoritaire depuis août 2026) : l'ancre ne contient AUCUN texte, juste
 *    <svg><use href="#SvgTn"></svg> ; le libellé vit dans un <text id="SvgTn">
 *    ailleurs dans le document. innerText est vide et le décodage géométrique
 *    ci-dessous renvoie '' → sans __decodeTSSvg, plus AUCUN post n'est capté
 *    (constaté le 16 août 2026 : 8 posts sur 11 illisibles).
 * 2. Géométrique : FB mélange les caractères via CSS `order` dans un conteneur
 *    flex `overflow:hidden` de largeur fixe ; les leurres débordent (clippés).
 *    On garde les glyphes réellement DANS la boîte visible, triés par position.
 * 3. Texte en clair (« 8 août à 21:03 ») : innerText suffit. */
window.__decodeTSGeom = function (tsA) {
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

/* Régime SVG : suivre la CHAÎNE de <use href="#SvgTn"> jusqu'au <text> qui porte
 * le libellé.
 * ⚠️ Ne PAS se contenter d'un seul niveau : depuis le 23 août 2026 Facebook
 * intercale un maillon, `use -> <svg id> -> use -> <text>`. Le premier saut tombe
 * alors sur un <svg> vide, `textContent` ressort '' et le post n'est pas daté donc
 * pas capté du tout — constaté ce jour-là : 2 posts captés sur 11 dans « Emploi
 * vétérinaire et ASV », le reste du fil invisible. On parcourt donc les `use` en
 * largeur sur quelques niveaux, en mémorisant les ids déjà vus (le graphe peut
 * boucler), et on retient le premier texte que __parseTS sait dater. */
window.__decodeTSSvg = function (a) {
  const seen = new Set();
  let queue = Array.from(a.querySelectorAll('use'));
  for (let depth = 0; depth < 8 && queue.length; depth++) {
    const next = [];
    for (const u of queue) {
      const h = u.getAttribute('xlink:href') || u.getAttribute('href') || '';
      if (!h.startsWith('#')) continue;
      const id = h.slice(1);
      if (seen.has(id)) continue;
      seen.add(id);
      const t = document.getElementById(id);
      if (!t) continue;
      const s = (t.textContent || '').replace(/[͏​-‍⁠﻿­]/g, '').replace(/\s+/g, ' ').trim();
      if (s && window.__parseTS(s).iso) return s;
      for (const cu of t.querySelectorAll('use')) next.push(cu);
    }
    queue = next;
  }
  return null;
};

/* Essaie les trois régimes ; ne retient que ce que __parseTS sait dater.
 * Cache les décodages POSITIFS (WeakMap) : __merge re-décode les mêmes ancres à
 * chaque cycle et le décodage géométrique coûte un getComputedStyle par nœud. */
window.__tsCache = window.__tsCache || new WeakMap();
window.__decodeTS = function (a) {
  const hit = window.__tsCache.get(a);
  if (hit) return hit;
  let v = window.__decodeTSSvg(a);
  if (!v) {
    const g = window.__decodeTSGeom(a);
    if (g && window.__parseTS(g).iso) v = g;
    else {
      const t = (a.innerText || '').trim();
      v = (t.length <= 40 && window.__parseTS(t).iso) ? t : g;
    }
  }
  if (v && window.__parseTS(v).iso) window.__tsCache.set(a, v);
  return v;
};

/* --- Une ancre est-elle le timestamp d'un POST ? ---------------------------
 * Remplace l'ancien test `innerText.length >= 12` (qui supposait le texte
 * obfusqué présent dans le DOM : faux sous le régime SVG, où innerText est vide).
 * ⚠️ Le rejet des ancres situées DANS un commentaire est indispensable : les
 * commentaires portent eux aussi un href `?__cft__`. Sans ce filtre, chaque
 * commentaire devient un faux post ET, pire, la remontée de racine du vrai post
 * s'arrête sur lui — son corps ressort vide (constaté le 16 août 2026 :
 * 89 faux posts et 46 corps vides sur 265 entrées). */
window.__isTsAnchor = function (a) {
  const h = a.getAttribute('href') || '';
  if (!h.includes('__cft__')) return false;
  if (!(h.startsWith('?__cft__') || /\/(posts|permalink)\//.test(h) || /story_fbid=/.test(h))) return false;
  const art = a.closest('div[role="article"][aria-label]');
  if (window.__isCommentArticle(art)) return false;
  const d = window.__decodeTS(a);
  return !!(d && window.__parseTS(d).iso);
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
  // ⚠️ Les unités relatives COLLISIONNENT avec les noms de mois, qui commencent
  // eux aussi par un chiffre puis la même lettre :
  //   « 5 septembre » matchait `^\d+\s*s`   -> 5 secondes -> daté d'aujourd'hui ;
  //   « 20 juin »     matchait `^(\d+)\s*j` -> 20 jours   -> daté 20 jours avant.
  // Les deux passaient SILENCIEUSEMENT (l'iso ressortait valide, donc __isTsAnchor
  // acceptait l'ancre) et suffisaient à fausser la fenêtre entière. Les lookaheads
  // ci-dessous rejettent les mois sans gêner « 5 s », « 20 j », « 20 jours ».
  if (/^\d+\s*(?:s|sec)(?!ept)/i.test(s)) return { iso: isoOf(now), ageH: 0 };
  if (/^\d+\s*min/i.test(s)) return { iso: isoOf(now), ageH: 0.2 };
  if ((m = s.match(/^(\d+)\s*h/i))) { const h = +m[1]; return { iso: isoOf(new Date(now - h * 3600e3)), ageH: h }; }
  if ((m = s.match(/^(\d+)\s*j(?!anv|uin|uil)/i))) { const j = +m[1]; return { iso: isoOf(new Date(now - j * 86400e3)), ageH: j * 24 }; }
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

/* --- Texte INTÉGRAL d'un commentaire ---------------------------------------
 * ⚠️ Ne PAS lire seulement le premier `div[dir="auto"]` : un commentaire de
 * plusieurs paragraphes est alors amputé silencieusement — et pire, sans que
 * __truncatedComments ne le signale, puisque le fragment retenu ne finit pas par
 * « Voir plus ». Constaté le 23 août 2026 : « Bonjour. » au lieu de « Bonjour.
 * Je vous ai envoyé un message sur Messenger », soit une candidature illisible.
 * On joint donc tous les blocs de texte PROPRES à l'article du commentaire.
 *
 * ⚠️ Et ne PAS aspirer le texte des RÉPONSES imbriquées : sur un permalink (et
 * dès qu'un fil est déplié dans le feed), l'article d'un commentaire CONTIENT
 * ceux de ses réponses. Sans ce filtre, la réponse d'un tiers était recopiée
 * dans le commentaire parent et attribuée à son auteur — constaté le 31 août
 * 2026, où l'offre d'une clinique se retrouvait au nom d'un compte blacklisté.
 * On ne garde donc que les blocs dont l'article de commentaire le plus proche
 * EST celui qu'on lit ; les réponses sont récoltées pour elles-mêmes. */
window.__commentFull = function (art) {
  return Array.from(art.querySelectorAll('div[dir="auto"]'))
    .filter(d => d.closest('div[role="article"][aria-label]') === art)
    .map(d => (d.innerText || '').trim()).filter(t => t).join('\n');
};

/* --- Jeton de story : à quel POST appartient une ancre ? --------------------
 * Toutes les ancres d'un même post portent le MÊME `__cft__[0]=<jeton>` dans leur
 * href ; deux posts distincts ont deux jetons distincts (vérifié en live le
 * 25 août 2026 : 9 ancres du fil → 5 jetons → exactement les 5 posts affichés).
 * C'est ce qui permet de distinguer « une autre ancre du MÊME post » de « l'ancre
 * du post VOISIN » — distinction que le simple `x !== tsA` ne fait pas.
 * Renvoie '' si le href n'en porte pas (on retombe alors sur l'ancien test). */
window.__storyToken = function (a) {
  const h = a ? (a.getAttribute('href') || '') : '';
  return (h.match(/__cft__(?:\[\d+\])?=([^&]+)/) || [])[1] || '';
};

/* --- Cet élément appartient-il à un COMMENTAIRE et non au post ? -------------
 * La racine d'un post (cf. __harvestAll) englobe sa zone de commentaires : sans
 * ce filtre, `author`, `authorUrl` et `body` peuvent tous être lus CHEZ UN
 * COMMENTATEUR. `body` retient le bloc le plus long, donc un commentaire de
 * 135 caractères l'emporte sur un post de 125 — et aucun garde-fou ne le voit
 * (ni __truncated, ni __exportBlocked, ni les purges de souches : le texte
 * capté est complet, simplement il n'est pas celui du post).
 * Constaté le 31 août 2026, 2 cas sur 98 posts. Le pire fabriquait un faux post
 * attribué à la commentatrice alors que le vrai auteur était BLACKLISTÉ : une
 * annonce d'intermédiaire déjà arbitrée rentrait ainsi en base par la porte de
 * côté, et le commentaire perdait son rattachement. L'autre créait un doublon
 * du post d'un candidat, non dépliable donc bloquant à l'export.
 * On borne donc les TROIS lectures, pas seulement le corps. */
/* ⚠️ « Réponse de X au commentaire de Y » est un COMMENTAIRE, au même titre que
 * « Commentaire de X ». Tester le seul préfixe « Commentaire de » — ce que faisait
 * tout le fichier — laissait les articles de réponse passer pour des conteneurs de
 * POST : ils devenaient le `ownerArticle` d'un commentaire, ou le plafond de la
 * racine d'un post. D'où ce prédicat unique, à utiliser PARTOUT. */
window.__isCommentArticle = function (art) {
  return !!(art && /^(?:Commentaire|Réponse) de/i.test(art.getAttribute('aria-label') || ''));
};
window.__inComment = function (el) {
  const art = el && el.closest ? el.closest('div[role="article"][aria-label]') : null;
  return window.__isCommentArticle(art);
};

/* --- Récolte complète : posts + commentaires rattachés par CONTAINMENT ----- */
window.__harvestAll = function () {
  // Anchors de timestamp de post (cf. __isTsAnchor : les 3 régimes de rendu,
  // commentaires exclus)
  const allTs = Array.from(document.querySelectorAll('a')).filter(window.__isTsAnchor);
  // Jetons calculés UNE fois : la garde ci-dessous les relit dans une boucle
  // imbriquée, à chaque __merge, donc à chaque pas de scroll. Un regex par
  // comparaison sur un fil déroulé coûterait cher pour rien (cf. le timeout CDP
  // de 45 s qui a déjà mordu sur __expandPostText le 16 août 2026).
  const tokOf = new Map();
  for (const a of allTs) tokOf.set(a, window.__storyToken(a));
  // ⚠️ Un post PARTAGÉ (publication d'une page repartagée dans le groupe) porte
  // PLUSIEURS ancres — 5 sur le cas observé — car la carte imbriquée du post
  // d'origine a les siennes. Sans dédup par jeton, le même post produirait
  // autant d'entrées que d'ancres. On garde la première de chaque jeton.
  const tsAnchors = [];
  const vus = new Set();
  for (const a of allTs) {
    const t = tokOf.get(a);
    if (t && vus.has(t)) continue;
    if (t) vus.add(t);
    tsAnchors.push(a);
  }
  const postByAnchor = new Map();
  for (const tsA of tsAnchors) {
    const tok = tokOf.get(tsA);
    // Plafond dur : le div[role="article"] du post, quand il existe. La racine ne
    // doit JAMAIS en sortir — c'est le garde-fou qui reste valable même si deux
    // posts partageaient un jeton de story. (Dans « We need you » les posts n'ont
    // pas d'article ancêtre : le plafond ne s'applique pas, et c'est la garde par
    // jeton ci-dessous qui protège.)
    const art = (function (el) {
      let e = el.parentElement;
      while (e) {
        if (e.matches && e.matches('div[role="article"]') &&
            !window.__isCommentArticle(e)) return e;
        e = e.parentElement;
      }
      return null;
    })(tsA);
    let root = tsA;
    for (let i = 0; i < 14; i++) {
      const next = root.parentElement;
      if (!next) break;
      if (art && !art.contains(next)) break;
      // ⚠️ Ne JAMAIS laisser la racine d'un post engloutir le timestamp d'un AUTRE post :
      // sinon l'auteur et le corps peuvent être lus chez le voisin. (10 août 2026)
      // ⚠️ Mais s'arrêter sur une ancre du MÊME post (cas du post partagé) laissait
      // la racine au-dessus de la carte imbriquée : `body` ressortait VIDE, sans
      // aucun signal — ni __truncated ni __exportBlocked ne voient un corps vide.
      // (25 août 2026 : une offre de 1 677 caractères passait à la trappe.)
      // On ne coupe donc que sur une ancre d'un AUTRE jeton de story.
      const etrangere = allTs.some(x => x !== tsA && next.contains(x) &&
        (tok && tokOf.get(x) ? tokOf.get(x) !== tok : true));
      if (etrangere) break;
      root = next;
      if ((root.innerText || '').length > 500) break;
    }
    let author = '';
    // ⚠️ PAS root.querySelector : il renvoie le premier match en ordre DOM, qui
    // peut être un nom de COMMENTATEUR quand l'en-tête du post n'expose pas de
    // h2/h3 (cf. __inComment). On prend le premier match HORS commentaire.
    const strong = Array.from(root.querySelectorAll('h2 strong,h3 strong,h2 a,h3 a,strong'))
      .find(e => !window.__inComment(e));
    if (strong) author = (strong.innerText || '').trim().split('\n')[0];
    // NB: ne PAS retomber sur "Membre anonyme" via innerText (un commentateur
    // anonyme dans le conteneur fausserait l'auteur). On matche par corps.
    // Profil de l'auteur : l'ancre du header porte /groups/{gid}/user/{uid}/
    // (validé en live : présent sur 100 % des auteurs nommés, absent sur
    // "Membre anonyme" → discriminant naturel, on ne devine rien).
    // ⚠️ Si authorUrl est vide alors que `author` est non vide et non anonyme,
    // c'est que `author` vient du fallback `strong` (nom mal capté, souvent un
    // post sponsorisé) → signal de qualité sur le nom.
    const authorUrl = window.__profileUrl(
      Array.from(root.querySelectorAll('h2 a[href],h3 a[href]')).find(e => !window.__inComment(e)));
    // id du post : chiffres OU token pfbid…, depuis /posts/, /permalink/ ou story_fbid=
    // (le href de l'ancre de timestamp est vide sur les posts à timestamp obfusqué :
    //  on lit donc l'innerHTML du conteneur, où le permalink est toujours présent).
    const pid = (root.innerHTML.match(/\/(?:posts|permalink)\/(pfbid\w+|\d+)/) || [])[1]
             || (root.innerHTML.match(/story_fbid=(pfbid\w+|\d+)/) || [])[1] || '';
    const gid = window.__gid();
    const permalink = (gid && pid) ? `https://www.facebook.com/groups/${gid}/posts/${pid}/` : '';
    // Le corps est le bloc le plus LONG : les blocs des commentaires doivent donc
    // être écartés AVANT le tri, sinon un commentaire un peu bavard devient le corps.
    const blocks = Array.from(root.querySelectorAll('div[dir="auto"]'))
      .filter(d => !window.__inComment(d))
      .map(d => (d.innerText || '').trim()).filter(t => t.length > 2).sort((a, b) => b.length - a.length);
    const parsed = window.__parseTS(window.__decodeTS(tsA));
    postByAnchor.set(tsA, { author, authorUrl, decoded: window.__decodeTS(tsA), iso: parsed.iso, ageH: parsed.ageH, gid, pid, permalink, body: blocks[0] || '', comments: [] });
  }
  // Commentaires = div[role=article][aria-label="Commentaire de {Nom} il y a {temps}"]
  // ET les réponses « Réponse de {Nom} au commentaire de {Autre} il y a {temps} » :
  // un recruteur répond souvent DANS le fil plutôt qu'en commentaire de premier
  // niveau, et sa proposition a exactement la même valeur.
  const cArts = Array.from(document.querySelectorAll('div[role="article"][aria-label]')).filter(window.__isCommentArticle);
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
            !window.__isCommentArticle(e)) return e;
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
      // Repli — certains groupes ne rendent AUCUN div[role="article"] autour de
      // leurs posts : la recherche d'ownerArticle échoue alors pour 100 % des
      // commentaires (constaté le 23 août 2026 dans « WE NEED YOU!!! », dont tout
      // le vivier candidat passait donc par ce repli). C'est exactement la
      // situation où l'ancienne heuristique de proximité était la plus risquée :
      // elle « marchait » sans rien garantir, et c'est elle qui avait recopié des
      // commentaires sur le mauvais post le 10 août 2026.
      //
      // On remonte donc les parents du commentaire et on s'arrête au PREMIER
      // ancêtre qui englobe des ancres de timestamp de post :
      //   - exactement UNE  -> c'est le conteneur de son post, rattachement certain ;
      //   - PLUSIEURS       -> ambigu, on abandonne (le commentaire repassera).
      // Cette règle reste du containment strict. ⚠️ Ne JAMAIS la remplacer par
      // « le plus proche timestamp qui précède » (l'ancienne heuristique de
      // proximité, retirée ici) : le 10 août 2026 elle avait recopié le jeu de
      // commentaires de deux posts sur un post voisin qui ne les portait pas.
      let e = a.parentElement;
      while (e) {
        const contained = tsAnchors.filter(tsA => e.contains(tsA));
        if (contained.length === 1) { parent = postByAnchor.get(contained[0]); break; }
        if (contained.length > 1) break;   // ambigu : on préfère l'oubli au faux rattachement
        e = e.parentElement;
      }
    }
    if (!parent) { window.__orphanComments++; continue; }
    // « Commentaire de X il y a T » et « Réponse de X au commentaire de Y il y a T » :
    // on retient X (l'auteur du message), jamais Y (celui à qui il répond).
    const m = a.getAttribute('aria-label')
      .match(/^(?:Commentaire|Réponse) de (.+?)(?:\s+(?:au commentaire|à la réponse) de .+?)?(?:\s+il y a (.+))?$/i);
    const name = m ? m[1].trim() : '';
    // Profil du commentateur : on privilégie l'ancre dont le texte EST le nom du
    // commentaire (une réponse imbriquée pourrait sinon fournir la 1re ancre) ;
    // à défaut, la première ancre de profil de l'article.
    const cAnchors = Array.from(a.querySelectorAll('a[href*="/user/"],a[href*="profile.php?id="]'));
    const cA = cAnchors.find(x => (x.innerText || '').trim() === name) || cAnchors[0];
    parent.comments.push({ name, profileUrl: window.__profileUrl(cA), time: m && m[2] ? m[2].trim() : '', text: window.__commentFull(a) });
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

/* ⚠️ Pré-filtrer sur textContent, PAS innerText : innerText force un reflow par
 * bouton. Sur un fil déroulé (≈6700 boutons) l'appel passait de ~50 ms à ~3 s,
 * ce qui faisait sauter le timeout CDP de 45 s à chaque lot (16 août 2026). */
window.__expandPostText = function () {
  let n = 0;
  for (const b of document.querySelectorAll('div[role="button"],span[role="button"]')) {
    const tc = (b.textContent || '').trim();
    if (tc.length > 18 || !window.__EXPAND_RX.test(tc)) continue;
    if (b.closest('a')) continue;
    try { b.click(); n++; } catch (e) {}
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
    if (!window.__isCommentArticle(art)) continue;
    for (const b of art.querySelectorAll('div[role="button"],span[role="button"]')) {
      const tc = (b.textContent || '').trim();   // textContent : cf. __expandPostText
      if (tc.length > 18 || !window.__EXPAND_RX.test(tc)) continue;
      if (b.closest('a')) continue;
      try { b.click(); n++; } catch (e) {}
    }
  }
  return n;
};

/* --- Expansion bornée au viewport (fils longs) ------------------------------
 * __expandPostText parcourt TOUS les boutons du document. Passé ~50 000 px de fil
 * déroulé ça devient le poste de coût dominant d'un cycle et le lot entier finit
 * par dépasser le timeout CDP de 45 s (constaté le 23 août 2026). Même travail,
 * mais restreint à ce qui est proche de l'écran — donc au seul endroit où un
 * « Voir plus » a un intérêt, puisque le merge se fait sur ce qui est rendu.
 * `pad` doit rester >= la moitié du pas de scroll pour ne rien laisser passer. */
window.__expandVisible = function (pad) {
  pad = pad || 1200;
  let n = 0;
  const vh = innerHeight;
  for (const b of document.querySelectorAll('div[role="button"],span[role="button"]')) {
    const tc = (b.textContent || '').trim();
    if (tc.length > 18 || !window.__EXPAND_RX.test(tc)) continue;
    if (b.closest('a')) continue;
    const r = b.getBoundingClientRect();
    if (r.bottom < -pad || r.top > vh + pad) continue;
    try { b.click(); n++; } catch (e) {}
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

/* --- Posts du store dont le CORPS EST VIDE ----------------------------------
 * Un corps vide était le seul défaut de capture que rien ne signalait — et le
 * filtre __inComment le rend plus VISIBLE qu'avant : là où le texte d'un
 * commentaire prenait silencieusement la place du post, on obtient désormais
 * une chaîne vide, ce qui est franc mais ne se voit toujours pas tout seul.
 * ⚠️ Volontairement NON bloquant dans __exportBlocked : un post sans texte
 * existe pour de vrai (photo, lien seul, affiche) et bloquerait l'export
 * indéfiniment. C'est à la relecture de trancher : soit le post est vraiment
 * sans texte et on l'écarte, soit son corps n'a pas été rendu et il faut
 * remonter le lire dans la page — mais on ne pousse JAMAIS une entrée vide. */
window.__emptyBodies = function (borne) {
  return Object.values(window.__store)
    .filter(p => (!borne || (p.iso && p.iso >= borne)) && !(p.body || '').trim())
    .map(p => ({ author: p.author || '(anon)', iso: p.iso, permalink: p.permalink || '' }));
};

/* --- Purge des DOUBLONS parasites tronqués ----------------------------------
 * Un post capté pendant un rendu partiel peut entrer dans le store avec un corps
 * réduit à quelques dizaines de caractères (« Offre d'emploi – Vétérinaire Mixte
 * E… En voir plus »). Sa clé diffère de celle de la version complète — les 40
 * premiers caractères ne coïncident pas — donc __merge ne les réunit pas et le
 * store garde DEUX entrées pour un seul post. La tronquée n'est pas dépliable
 * (l'exemplaire affiché, lui, est déjà déplié : il ne reste plus de bouton à
 * cliquer), et elle bloque donc __exportBlocked indéfiniment.
 * On supprime une entrée tronquée dès qu'une autre entrée du MÊME auteur, non
 * tronquée, commence par le même texte : c'est le même post, en mieux.
 * À appeler avant le contrôle d'export. Renvoie la liste des entrées retirées. */
window.__purgeStubs = function () {
  const norm = x => (x || '').replace(/\s*(?:…\s*)?(?:En )?[Vv]oir plus\s*$/, '').replace(/\s+/g, ' ').trim();
  const byAuthor = {};
  for (const [k, p] of Object.entries(window.__store)) {
    (byAuthor[p.author || ''] = byAuthor[p.author || ''] || []).push([k, p]);
  }
  const removed = [];
  for (const list of Object.values(byAuthor)) {
    for (const [k, p] of list) {
      if (!window.__isTrunc(p.body)) continue;
      const pre = norm(p.body);
      if (pre.length < 12) continue;          // trop court pour identifier quoi que ce soit
      const covered = list.some(([k2, p2]) => k2 !== k && !window.__isTrunc(p2.body) &&
        norm(p2.body).startsWith(pre.slice(0, Math.min(pre.length, 30))));
      if (covered) {
        delete window.__store[k];
        removed.push({ author: p.author || '(anon)', iso: p.iso, len: (p.body || '').length });
      }
    }
  }
  return removed;
};

/* --- Idem pour les COMMENTAIRES ---------------------------------------------
 * Même mécanique, et elle manquait : la clé d'un commentaire est
 * `nom|texte[:40]`, donc la version TRONQUÉE et la version DÉPLIÉE tombent sur
 * deux clés différentes et coexistent dans `p.comments`. __exportBlocked reste
 * alors bloqué sur la souche alors que le texte complet est déjà dans le store —
 * et re-déplier ne débloque jamais rien, le message d'erreur ne bougeant pas
 * d'un lot à l'autre. Ça ressemble à un dépliage qui échoue ; c'est un doublon.
 * (Constaté le 25 août 2026 sur un « Bonjour,… Voir plus ».)
 * On supprime une entrée tronquée dès qu'une autre entrée du MÊME commentateur,
 * sous le MÊME post et non tronquée, commence par le même texte. */
window.__purgeCommentStubs = function () {
  const norm = x => (x || '').replace(/\s*(?:…\s*)?(?:En )?[Vv]oir plus\s*$/, '').replace(/\s+/g, ' ').trim();
  const removed = [];
  for (const p of Object.values(window.__store)) {
    const ents = Object.entries(p.comments || {});
    for (const [k, c] of ents) {
      if (!window.__isTrunc(c.text)) continue;
      const pre = norm(c.text);
      // ⚠️ Seuil BEAUCOUP plus bas que pour les posts : un commentaire tronqué se
      // réduit souvent à un mot (« Bonjour,… Voir plus » → « Bonjour, », 8 car.),
      // là où le seuil de 12 des posts le laisserait passer et bloquerait l'export.
      // Le risque est nul en pratique : il faut le MÊME commentateur, sous le MÊME
      // post, avec une version non tronquée qui commence pareil — et une souche
      // retirée à tort serait simplement re-captée au cycle suivant.
      if (pre.length < 4) continue;
      const covered = ents.some(([k2, c2]) => k2 !== k && (c2.name || '') === (c.name || '') &&
        !window.__isTrunc(c2.text) &&
        norm(c2.text).startsWith(pre.slice(0, Math.min(pre.length, 25))));
      if (covered) {
        delete p.comments[k];
        removed.push({ post: p.author || '(anon)', iso: p.iso, name: c.name, len: (c.text || '').length });
      }
    }
  }
  return removed;
};

/* --- Garde unique à appeler AVANT l'export ----------------------------------
 * Renvoie '' si l'export peut se faire, sinon la raison. Regroupe les deux
 * contrôles pour qu'on ne puisse plus en oublier un.
 * ⚠️ Purge d'abord les souches (posts ET commentaires) : ce sont des doublons
 * d'entrées déjà complètes dans le store, jamais dépliables, qui bloqueraient
 * l'export indéfiniment. La purge est faite ICI plutôt que laissée à l'appelant
 * pour qu'on ne puisse pas l'oublier — c'est de l'auto-réparation, au même titre
 * que le « garde le corps le plus long » de __merge.
 * Usage : const stop = window.__exportBlocked('2026-08-07'); if (stop) return stop; */
window.__exportBlocked = function (borne) {
  window.__purgeStubs();
  window.__purgeCommentStubs();
  const inWin = p => !borne || (p.iso && p.iso >= borne);
  const tp = window.__truncated().filter(inWin);
  const tc = window.__truncatedComments().filter(inWin);
  if (tp.length) return 'STOP — ' + tp.length + ' post(s) tronqué(s) : ' + JSON.stringify(tp);
  if (tc.length) return 'STOP — ' + tc.length + ' commentaire(s) tronqué(s) : ' + JSON.stringify(tc);
  return '';
};

/* --- Nettoyage du corps pour l'export (retire les marqueurs FB finaux) ------ */
window.__cleanBody = b => (b || '').replace(/\s+/g, ' ').replace(/\s*(?:…\s*)?(?:En )?[Vv]oir (?:plus|moins)\s*$/, '').trim();

/* --- ARRÊT SUR LE DERNIER POST DÉJÀ SCRAPPÉ ---------------------------------
 * Facebook ne donne PAS l'heure de publication : « 3 j » couvre 24 h entières.
 * S'arrêter sur la seule date oblige donc à redérouler tout le dernier jour déjà
 * en base — sur un groupe actif, la moitié du scrape pour zéro nouveauté.
 * On reconnaît plutôt les posts DÉJÀ EN BASE à leur texte, exactement comme le
 * fait `sec_sig()` d'airtable_push.py : mêmes 80 premiers caractères, même
 * normalisation. `__seenInit` reçoit ces empreintes (chargées en §0 depuis
 * Airtable), `__tailKnown` dit si la queue du fil est entièrement connue.
 *
 * ⚠️ Le critère est « K posts consécutifs connus », jamais un seul : une simple
 * republication en tête de fil arrêterait sinon le scrape immédiatement. Et il
 * reste doublé du critère de date (cf. SKILL.md §2), qui prend le relais si le
 * dernier post scrappé a été supprimé et n'est donc plus jamais rencontré. */
window.__seen = window.__seen || new Set();
window.__seenInit = function (prefixes) {
  window.__seen = new Set(prefixes || []);
  return window.__seen.size;
};
/* 48 caractères : assez pour identifier un post sans ambiguïté, et 40 % plus
 * court à injecter que les 80 de `sec_sig` (la charge utile passe de ~17 Ko à
 * ~8,5 Ko sur un groupe actif, donc en un seul appel `javascript_tool` au lieu
 * de deux). ⚠️ Le script du §0 DOIT tronquer à la même longueur. */
window.__SIG_LEN = 48;
window.__sig = b => window.__cleanBody(b).toLowerCase().slice(0, window.__SIG_LEN);
window.__tailKnown = function (n, borne) {
  n = n || 3;
  const ps = window.__harvestAll().filter(p => p.iso && (p.body || '').trim()).slice(-n);
  if (ps.length < n || !window.__seen.size) return false;
  return ps.every(p => window.__seen.has(window.__sig(p.body)) && (!borne || p.iso <= borne));
};
/* Ce que la fenêtre courante apporte de NOUVEAU (pour le résumé §6). */
window.__unseen = function (borne) {
  return Object.values(window.__store)
    .filter(p => p.iso && (!borne || p.iso >= borne) && !window.__seen.has(window.__sig(p.body)))
    .length;
};

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
