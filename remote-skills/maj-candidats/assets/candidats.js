    // ============ CANDIDATS ============
    const CANDIDATS = __CANDIDATS__;
    // Contours des départements, cantons, provinces et du Luxembourg (Natural Earth, simplifiés) ;
    // coordonnées en millièmes de degré.
    const ZONES_GEO = __ZONES_GEO__;
    const GEO_PAS = 0.001;
    const CONTACT = "contact@sarecrute.com";

    const PRATIQUE_LABELS = {"Canine": "Canin", "Bovins": "Rural", "Allaitant": "Bovin allaitant", "Laitier": "Bovin laitier", "Ovin/Caprin": "Ovin / caprin", "Porcin": "Porcin", "Volailles": "Volailles", "Equine": "Équin", "NAC": "NAC"};
    const SPECIALITE_LABELS = {"Echographie": "Échographie"};
    const EXPERIENCE_LABELS = {"Etudiant": "Fin d'études", "1 à 2 ans": "Semi-autonome"};
    const EXPERIENCE_ORDER = ["Etudiant", "Débutant", "1 à 2 ans", "Autonome", "Spécialiste"];
    const GARDES_LABELS = {"Oui": "Acceptées", "Non": "Non souhaitées"};
    const experienceLabel = (e) => (e && EXPERIENCE_LABELS[e]) || e;
    const pratiqueLabel = (p) => PRATIQUE_LABELS[p] || SPECIALITE_LABELS[p] || p;
    const CANDIDAT_PAR_REF = Object.fromEntries(CANDIDATS.map((c) => [c.ref, c]));
    const SOURIS = window.matchMedia("(hover: hover)").matches;

    const PAYS_ORDER = ["France", "Suisse", "Belgique", "Luxembourg", "Espagne"];
    const zoneLabelPays = (label) => (label.startsWith("pays:") ? label.slice(5) : null);
    const estOutreMer = (label) => /\(97\d\)$/.test(label);

    // Toutes les zones connues : celles que citent les candidats et celles de la carte. Un
    // département que personne ne cite compte quand même les candidats ouverts à toute la France.
    const ZONES_INDEX = {};   // libellé -> zone (pays, niveau, coordonnées)
    CANDIDATS.forEach((c) => c.zones.forEach((z) => { if (!ZONES_INDEX[z.label]) ZONES_INDEX[z.label] = z; }));
    ZONES_GEO.forEach((g) => {
      if (!ZONES_INDEX[g.label]) ZONES_INDEX[g.label] = { label: g.label, pays: g.pays, niveau: g.niveau, lat: g.lat, lon: g.lon };
    });

    // Une zone de niveau « pays » couvre toutes les zones de ce pays, outre-mer excepté : un
    // candidat qui cherche « partout en Suisse » compte dans le canton de Fribourg, mais « toute la
    // France » ne vaut pas pour La Réunion.
    function candidatCouvre(c, zoneValue) {
      const pays = zoneLabelPays(zoneValue);
      if (pays) return c.zones.some((z) => z.pays === pays);
      const cible = ZONES_INDEX[zoneValue];
      return c.zones.some((z) => z.label === zoneValue ||
        (cible && z.niveau === "pays" && z.pays === cible.pays && !estOutreMer(zoneValue)));
    }

    const PAYS_ENTIER = {"France": "toute la France", "Suisse": "toute la Suisse", "Belgique": "toute la Belgique", "Espagne": "toute l'Espagne", "Luxembourg": "Luxembourg"};

    function resumeZones(c) {
      const labels = c.zones.map((z) => (z.niveau === "pays" ? PAYS_ENTIER[z.label] || z.label : z.label));
      labels[0] = labels[0].charAt(0).toUpperCase() + labels[0].slice(1);
      if (labels.length <= 4) return labels.join(", ");
      return `${labels.slice(0, 3).join(", ")} et ${labels.length - 3} autres zones`;
    }

    function zoneTete(c) {
      const pays = [...new Set(c.zones.map((z) => z.pays).filter(Boolean))];
      if (pays.length > 1) return pays.join(" · ");
      if (c.zones.length === 1) return c.zones[0].label;
      return pays[0] || "Plusieurs zones";
    }

    function contactUrl(c) {
      // Pas de référence : le profil se reconnaît à ce qu'en dit la carte (titre, zones, description).
      const subject = `Profil candidat : ${c.titre} — ${zoneTete(c)}`;
      const body = `Bonjour,\n\nCe profil nous intéresse :\n${c.titre} — ${resumeZones(c)} — disponibilité : ${c.disponibilite || "à préciser"}\n« ${c.description || ""} »\n\n- Structure :\n- Ville / département :\n- Poste proposé :\n- Téléphone :\n`;
      return `mailto:${CONTACT}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    }

    function candField(label, value) {
      if (!value) return "";
      return `
        <div class="offre-field">
          <span class="offre-field-label">${label}</span>
          <span class="offre-field-value">${value}</span>
        </div>
      `;
    }

    function renderCandidatCard(c) {
      const specs = c.specialites.map((s) => `<span class="offre-badge cand-spec">${pratiqueLabel(s)}</span>`).join("");
      const fields = [
        candField("Contrat souhaité", c.contrat.join(", ") || "Ouvert"),
        candField("Temps de travail", c.temps.join(", ")),
        candField("Gardes", GARDES_LABELS[c.gardes]),
        candField("Disponibilité", c.disponibilite || "À préciser"),
      ].join("");
      return `
        <article class="offre-card" data-ref="${c.ref}">
          <div class="offre-card-head">
            <span class="offre-loc">${zoneTete(c)}</span>
            ${c.experience ? `<span class="offre-badge-corner">${experienceLabel(c.experience)}</span>` : ""}
          </div>
          <h3>${c.titre}</h3>
          <p class="cand-zones"><b>Recherche :</b> ${resumeZones(c)}</p>
          <p class="offre-desc">${c.description || ""}</p>
          ${specs ? `<div class="offre-badges">${specs}</div>` : ""}
          <div class="offre-fields">${fields}</div>
          <a class="btn btn-primary" href="${contactUrl(c)}">Ce profil m'intéresse <span class="btn-arrow">→</span></a>
        </article>
      `;
    }

    // ============ FILTRES ============
    const zoneFiltre = () => document.getElementById("cand-filtre-zone").value;

    function populateFilters() {
      const zoneSel = document.getElementById("cand-filtre-zone");
      const parPays = {};
      Object.values(ZONES_INDEX).forEach((z) => {
        if (z.niveau === "pays" || !z.pays) return;
        (parPays[z.pays] = parPays[z.pays] || []).push(z.label);
      });
      const paysPresents = PAYS_ORDER.filter((p) => Object.values(ZONES_INDEX).some((z) => z.pays === p));
      const autres = Object.values(ZONES_INDEX).filter((z) => !z.pays).map((z) => z.label).sort();
      zoneSel.innerHTML = `<option value="">Zones</option>` +
        paysPresents.map((p) => {
          const sous = (parPays[p] || []).sort((a, b) => a.localeCompare(b, "fr"));
          return `<optgroup label="${p}"><option value="pays:${p}">${p} (toutes zones)</option>` +
            sous.map((l) => `<option value="${l}">${l}</option>`).join("") + `</optgroup>`;
        }).join("") +
        (autres.length ? `<optgroup label="Autres">${autres.map((l) => `<option value="${l}">${l}</option>`).join("")}</optgroup>` : "");

      const pratiques = [
        ...[...new Set(CANDIDATS.flatMap((c) => c.pratiques))].sort((a, b) => pratiqueLabel(a).localeCompare(pratiqueLabel(b), "fr")),
        ...[...new Set(CANDIDATS.flatMap((c) => c.specialites))].sort((a, b) => pratiqueLabel(a).localeCompare(pratiqueLabel(b), "fr")),
      ];
      const contrats = [...new Set(CANDIDATS.flatMap((c) => c.contrat))].sort();
      const experiences = EXPERIENCE_ORDER.filter((e) => CANDIDATS.some((c) => c.experience === e));
      const fill = (id, values, allLabel, labelFn) => {
        document.getElementById(id).innerHTML = `<option value="">${allLabel}</option>` +
          values.map((v) => `<option value="${v}">${labelFn ? labelFn(v) : v}</option>`).join("");
      };
      fill("cand-filtre-pratique", pratiques, "Pratiques et spécialités", pratiqueLabel);
      fill("cand-filtre-contrat", contrats, "Contrats");
      fill("cand-filtre-experience", experiences, "Expérience", experienceLabel);
    }

    // ============ FILTRES PARTAGEABLES PAR L'URL ============
    // candidats?zone=29  ·  candidats?pratique=rural  ·  candidats?zone=suisse&experience=debutant
    const FILTER_PARAMS = [
      { id: "cand-filtre-zone", param: "zone" },
      { id: "cand-filtre-pratique", param: "pratique" },
      { id: "cand-filtre-contrat", param: "contrat" },
      { id: "cand-filtre-experience", param: "experience" },
    ];
    const FILTER_IDS = FILTER_PARAMS.map((f) => f.id);
    const deaccent = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    const slugKey = (s) => deaccent(s).replace(/[^a-z0-9]/g, "");
    const slugUrl = (s) => deaccent(s).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    const deptNum = (v) => {
      const m = String(v).match(/\((\d+|2[AB])\)/);
      return m ? m[1].replace(/^0+(?=\d)/, "") : null;
    };

    function findOptionValue(select, raw) {
      const wanted = slugKey(raw);
      if (!wanted) return "";
      const opts = [...select.options].filter((o) => o.value);
      const num = /^(\d+|2[ab])$/.test(wanted) ? wanted.replace(/^0+(?=\d)/, "") : null;
      const match =
        opts.find((o) => slugKey(o.value) === wanted) ||
        opts.find((o) => slugKey(o.value.replace(/^pays:/, "")) === wanted) ||
        opts.find((o) => slugKey(o.textContent) === wanted) ||
        opts.find((o) => slugKey(o.value.replace(/\s*\((\d+|2[AB])\)\s*$/, "")) === wanted) ||
        opts.find((o) => slugKey(o.value.replace(/^(Canton|Province|Région) d(e |u |es |')/, "")) === wanted) ||   // « fribourg », « liege »
        (num ? opts.find((o) => String(deptNum(o.value)).toLowerCase() === num) : null);
      return match ? match.value : "";
    }

    function paramValue(select) {
      const opt = select.selectedOptions[0];
      if (!opt || !opt.value) return "";
      if (opt.value.startsWith("pays:")) return slugUrl(opt.value.slice(5));
      return (deptNum(opt.value) || "").toLowerCase() || slugUrl(opt.textContent) || slugUrl(opt.value);
    }

    function applyFiltersFromUrl() {
      const params = new URLSearchParams(location.search);
      FILTER_PARAMS.forEach(({ id, param }) => {
        const raw = params.get(param);
        if (!raw) return;
        const select = document.getElementById(id);
        const value = findOptionValue(select, raw);
        if (value) select.value = value;
      });
    }

    // ?liste=1 garde l'étape 2 quand on parcourt tous les candidats sans filtre.
    function syncUrlWithFilters() {
      const params = new URLSearchParams(location.search);
      FILTER_PARAMS.forEach(({ id, param }) => {
        const v = paramValue(document.getElementById(id));
        if (v) params.set(param, v);
        else params.delete(param);
      });
      if (modeListe && !FILTER_PARAMS.some(({ param }) => params.has(param))) params.set("liste", "1");
      else params.delete("liste");
      params.delete("profil");   // lu une fois à l'arrivée (lien d'une carte de l'accueil)
      const qs = params.toString();
      history.replaceState(history.state, "", qs ? `${location.pathname}?${qs}` : location.pathname);
    }

    // ============ DEUX ÉTAPES ============
    // Le recruteur arrive avec une question : « qui viendrait chez moi ? ». Étape 1 : la carte en
    // grand et un champ pour sa zone. Étape 2 : les candidats de cette zone, la carte à droite pour
    // en changer. Passer de l'une à l'autre ajoute une entrée d'historique : « Retour » ramène à la
    // carte au lieu de quitter la page.
    let modeListe = false;
    const urlDemandeListe = () => {
      const params = new URLSearchParams(location.search);
      return params.has("liste") || params.has("profil") || FILTER_PARAMS.some(({ param }) => params.get(param));
    };

    function ouvrirListe() {
      if (modeListe) return;
      history.pushState({ depuisAccueil: true }, "", location.href);
      modeListe = true;
    }

    function revenirAccueil() {
      if (history.state && history.state.depuisAccueil) {
        history.back();   // le popstate remet l'étape 1
        return;
      }
      FILTER_IDS.forEach((id) => { document.getElementById(id).value = ""; });
      modeListe = false;
      renderCandidats();
      document.getElementById("cand-accueil").scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function montrerResultats() {
      document.getElementById("cand-resultats").scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // Saisie libre : libellé, nom (même partiel), numéro de département ou code postal.
    function resoudreSaisie(texte) {
      const brut = texte.trim();
      if (!brut) return { erreur: "" };
      const select = document.getElementById("cand-filtre-zone");
      const options = [...select.options].filter((o) => o.value);
      const exact = options.find((o) => o.value === brut || o.textContent === brut);
      if (exact) return { value: exact.value };
      const cp = brut.replace(/\s/g, "");
      if (/^\d{5}$/.test(cp)) {
        const num = cp.startsWith("97") ? cp.slice(0, 3)
          : cp.startsWith("20") ? (Number(cp) < 20200 ? "2A" : "2B")
          : cp.slice(0, 2).replace(/^0/, "");
        const o = options.find((x) => deptNum(x.value) === num);
        return o ? { value: o.value } : { erreur: `Aucun département ne correspond au code postal ${cp}.` };
      }
      if (/^\d{4}$/.test(cp)) return { erreur: "Pour une clinique en Suisse ou en Belgique, tapez le nom du canton ou de la province." };
      const v = findOptionValue(select, brut);
      if (v) return { value: v };
      const cle = slugKey(brut);
      const debuts = options.filter((o) => !o.value.startsWith("pays:") &&
        slugKey(o.value.replace(/^(Canton|Province|Région) d(e |u |es |')/, "")).startsWith(cle));
      if (debuts.length === 1) return { value: debuts[0].value };
      return { erreur: debuts.length
        ? `Plusieurs zones commencent par « ${brut} » : choisissez-la dans la liste.`
        : `Aucune zone ne correspond à « ${brut} ».` };
    }

    function chercherZone() {
      const saisie = document.getElementById("cand-zone-saisie");
      const r = resoudreSaisie(saisie.value);
      document.getElementById("cand-recherche-msg").textContent = r.erreur || "";
      if (!r.value) return;
      saisie.value = "";
      choisirZone(r.value);
    }

    function titreResultats(zone, n) {
      const pays = zoneLabelPays(zone);
      const titre = !zone ? "Tous les candidats"
        : pays ? PAYS_ENTIER[pays].charAt(0).toUpperCase() + PAYS_ENTIER[pays].slice(1)
        : zone;
      const detail = !n ? "Aucun candidat pour ces critères pour l'instant"
        : zone ? `${n} candidat${pluriel(n)} prêt${pluriel(n)} à y travailler`
        : `${n} candidat${pluriel(n)}`;
      document.getElementById("cand-titre").textContent = titre;
      document.getElementById("cand-count").textContent = detail;
    }

    // La même carte Leaflet sert aux deux étapes : elle change de conteneur.
    function placerCarte() {
      const carte = document.getElementById("cand-carte");
      const cible = document.getElementById(modeListe ? "cand-carte-liste" : "cand-carte-accueil");
      if (carte.parentNode === cible) return;
      cible.appendChild(carte);
      if (!candMap) return;
      candMap.invalidateSize({ pan: false });
      cadrer(true);
    }

    function renderCandidats() {
      const zone = zoneFiltre();
      const pratique = document.getElementById("cand-filtre-pratique").value;
      const contrat = document.getElementById("cand-filtre-contrat").value;
      const experience = document.getElementById("cand-filtre-experience").value;
      // La carte suit tous les filtres sauf celui de zone ; la liste les suit tous.
      const horsZone = CANDIDATS.filter((c) =>
        (!pratique || c.pratiques.includes(pratique) || c.specialites.includes(pratique)) &&
        (!contrat || !c.contrat.length || c.contrat.includes(contrat)) &&   // « Ouvert » : tout contrat
        (!experience || c.experience === experience)
      );
      const filtered = zone ? horsZone.filter((c) => candidatCouvre(c, zone)) : horsZone;
      document.getElementById("candidats").classList.toggle("is-accueil", !modeListe);
      placerCarte();
      // La fiche survolée peut disparaître avec le filtre sans que « mouseleave » parte.
      finSurvol();
      const grid = document.getElementById("cand-grid");
      grid.classList.remove("cand-grid-survol");
      grid.innerHTML = filtered.length
        ? filtered.map(renderCandidatCard).join("")
        : '<div class="offre-empty">Aucun candidat ne correspond à ces critères pour le moment.</div>';
      titreResultats(zone, filtered.length);

      // Au doigt, toucher une fiche émet un mouseenter sans mouseleave : la carte resterait figée
      // sur ce candidat. Le survol des fiches est réservé aux souris.
      if (SOURIS) grid.querySelectorAll(".offre-card").forEach((card) => {
        const c = CANDIDAT_PAR_REF[card.getAttribute("data-ref")];
        if (!c) return;
        card.addEventListener("mouseenter", () => survol(c));
        card.addEventListener("mouseleave", finSurvol);
      });

      majCarte(horsZone, filtered);
      syncUrlWithFilters();
    }

    // ============ CARTE ============
    // Carte des zones de recherche, pas des adresses : chaque département (canton, province,
    // Luxembourg) est teinté selon le nombre de candidats prêts à y travailler, nombre écrit dedans
    // quand il y tient. La carte suit les filtres pratique, contrat et expérience, pas celui de
    // zone : la zone choisie y est cerclée et les autres restent lisibles pour en choisir une autre.
    // Survoler la fiche d'un candidat colore sa zone de recherche ; survoler un département met en
    // avant les fiches des candidats qui y cherchent ; cliquer un département le filtre.
    const PALIERS = [1, 2, 4, 7, 10];   // bas de chaque palier de couleur
    const TEINTES = ["#ECE8DE", "#D5E3D7", "#ABC7B1", "#7FA68A", "#557D63", "#2F4F40"];
    const palier = (n) => PALIERS.filter((p) => n >= p).length;   // 0 : personne
    const pluriel = (n) => (n > 1 ? "s" : "");

    let candMap = null;
    const zoneLayers = {};       // libellé -> polygone
    const zoneEtiquettes = {};   // libellé -> marqueur portant le nombre
    const zoneBornes = {};       // libellé -> emprise
    const zoneCounts = {};       // libellé -> candidats prêts à y travailler
    const zoneNommee = {};       // libellé -> candidats qui l'ont nommée (sans ceux « tout le pays »)
    let boundsMetropole = null;
    let zoneCadree;              // filtre de zone pour lequel la carte est cadrée
    let cadrageEnAttente = false;
    let zoneSurvolee = null;
    let noteTexte = "";

    const unionBornes = (liste) => liste.reduce((b, x) => b.extend(x), L.latLngBounds(liste[0].getSouthWest(), liste[0].getNorthEast()));
    const elDe = (label) => zoneLayers[label] && zoneLayers[label].getElement();
    const etiquetteDe = (label) => zoneEtiquettes[label] && zoneEtiquettes[label].getElement();

    // Encarts : Paris et la petite couronne, trop petits sur la carte de France, et l'outre-mer,
    // loin du cadre. Petites cartes SVG tirées des mêmes contours, qui répètent la teinte, le nombre,
    // le survol et le clic de la grande carte.
    const ENCARTS = [
      { titre: "Paris et petite couronne", grand: true, zones: ["Paris (75)", "Hauts-de-Seine (92)", "Seine-Saint-Denis (93)", "Val-de-Marne (94)"] },
      { titre: "Guadeloupe", zones: ["Guadeloupe (971)"] },
      { titre: "Martinique", zones: ["Martinique (972)"] },
      { titre: "Guyane", zones: ["Guyane (973)"] },
      { titre: "La Réunion", zones: ["La Réunion (974)"] },
      { titre: "Mayotte", zones: ["Mayotte (976)"] },
    ];
    const SVG_NS = "http://www.w3.org/2000/svg";
    const ZONES_GEO_LABELS = new Set(ZONES_GEO.map((g) => g.label));
    const encartChemins = {};    // libellé -> path de l'encart
    const encartNombres = {};    // libellé -> text du nombre dans l'encart
    // Tous les tracés et tous les nombres d'une zone : grande carte et encart.
    const elsDe = (label) => [elDe(label), encartChemins[label]].filter(Boolean);
    const etiquettesDe = (label) => [etiquetteDe(label), encartNombres[label]].filter(Boolean);

    function construireEncarts() {
      const conteneur = document.getElementById("cand-encarts");
      const geo = Object.fromEntries(ZONES_GEO.map((g) => [g.label, g]));
      ENCARTS.forEach((e) => {
        const zones = e.zones.filter((l) => geo[l]);
        if (!zones.length) return;
        // Projection équirectangulaire corrigée de la latitude moyenne : assez juste à cette échelle.
        const pts = zones.flatMap((l) => geo[l].poly.flatMap((poly) => poly[0]));
        const lats = pts.map(([, y]) => y * GEO_PAS);
        const k = Math.cos(((Math.min(...lats) + Math.max(...lats)) / 2) * Math.PI / 180);
        const proj = ([x, y]) => [x * GEO_PAS * k, -y * GEO_PAS];
        const emprise = (liste) => {
          const xy = liste.map(proj);
          const xs = xy.map((q) => q[0]), ys = xy.map((q) => q[1]);
          return { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
        };
        const tout = emprise(pts);
        const marge = Math.max(tout.w, tout.h) * 0.06;
        const fig = document.createElement("figure");
        fig.className = `cand-encart${e.grand ? " cand-encart-grand" : ""}`;
        const legende = document.createElement("figcaption");
        legende.textContent = e.titre;
        const svg = document.createElementNS(SVG_NS, "svg");
        svg.setAttribute("viewBox", [tout.x - marge, tout.y - marge, tout.w + 2 * marge, tout.h + 2 * marge].map((v) => v.toFixed(4)).join(" "));
        svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
        const nombres = [];
        // Outre-mer : toute la vignette (légende comprise) est la cible, l'île seule est trop petite
        // au doigt. Paris et petite couronne : une cible par département.
        const unique = zones.length === 1;
        const brancher = (el, l) => {
          const value = geo[l].niveau === "pays" ? `pays:${geo[l].pays}` : l;
          el.tabIndex = 0;
          el.setAttribute("role", "button");
          el.classList.add("cand-encart-cible");
          el.dataset.zone = l;
          if (SOURIS) {
            el.addEventListener("mouseenter", (ev) => { survolZone(l); montrerInfoEncart(l, ev); });
            el.addEventListener("mousemove", placerInfoEncart);
            el.addEventListener("mouseleave", () => { finSurvolZone(l); cacherInfoEncart(); });
          }
          el.addEventListener("focus", () => { survolZone(l); montrerInfoEncart(l, null, el); });
          el.addEventListener("blur", () => { finSurvolZone(l); cacherInfoEncart(); });
          el.addEventListener("click", (ev) => {
            if (ev.detail > 1) return;
            cacherInfoEncart();
            choisirZone(value);
          });
          el.addEventListener("keydown", (ev) => {
            if (ev.key !== "Enter" && ev.key !== " ") return;
            ev.preventDefault();
            cacherInfoEncart();
            choisirZone(value);
          });
        };
        if (unique) brancher(fig, zones[0]);
        zones.forEach((l) => {
          const g = geo[l];
          const path = document.createElementNS(SVG_NS, "path");
          path.setAttribute("d", g.poly.map((poly) => poly.map((ring) =>
            "M" + ring.map((q) => proj(q).map((v) => v.toFixed(4)).join(",")).join("L") + "Z").join("")).join(""));
          path.setAttribute("class", "cand-zone");
          path.setAttribute("fill", TEINTES[0]);
          path.setAttribute("fill-rule", "evenodd");
          if (!unique) brancher(path, l);
          svg.appendChild(path);
          encartChemins[l] = path;
          const [tx, ty] = proj([g.lon / GEO_PAS, g.lat / GEO_PAS]);
          const texte = document.createElementNS(SVG_NS, "text");
          texte.setAttribute("x", tx.toFixed(4));
          texte.setAttribute("y", ty.toFixed(4));
          texte.setAttribute("class", "cand-encart-num");
          texte.setAttribute("aria-hidden", "true");
          const ez = emprise(g.poly.flatMap((poly) => poly[0]));
          texte.dataset.zone = l;
          texte.dataset.w = ez.w;
          texte.dataset.h = ez.h;
          nombres.push(texte);
          encartNombres[l] = texte;
        });
        nombres.forEach((n) => svg.appendChild(n));   // au-dessus de tous les tracés
        fig.append(legende, svg);
        conteneur.appendChild(fig);
      });
    }

    // Les nombres des encarts : taille de police ramenée en pixels, nombre écrit s'il tient.
    function majEncarts() {
      const paysFiltre = zoneLabelPays(zoneFiltre());
      document.querySelectorAll(".cand-encart svg").forEach((svg) => {
        const r = svg.getBoundingClientRect();
        const vb = svg.viewBox.baseVal;
        const s = r.width && vb.width ? Math.min(r.width / vb.width, r.height / vb.height) : 0;
        svg.querySelectorAll("text").forEach((texte) => {
          const label = texte.dataset.zone;
          const n = zoneCounts[label] || 0;
          const tient = s && texte.dataset.w * s >= 16 && texte.dataset.h * s >= 11;
          texte.textContent = "";
          if (s) texte.setAttribute("font-size", (10.5 / s).toFixed(5));
          if (n && tient) {
            // Un nombre qui déborde de son tracé (croissant des Hauts-de-Seine) ne s'écrit pas :
            // l'infobulle et le nom accessible donnent toujours le compte.
            texte.textContent = String(n);
            const chemin = encartChemins[label];
            const b = texte.getBBox();
            const coins = [[b.x + b.width * 0.2, b.y + b.height * 0.2], [b.x + b.width * 0.8, b.y + b.height * 0.2],
              [b.x + b.width * 0.2, b.y + b.height * 0.8], [b.x + b.width * 0.8, b.y + b.height * 0.8]];
            if (chemin.isPointInFill && !coins.every(([x, y]) => chemin.isPointInFill(new DOMPoint(x, y)))) texte.textContent = "";
          }
          const cible = encartChemins[label].closest(".cand-encart-cible") || encartChemins[label];
          cible.setAttribute("aria-label", `${label}, ${n ? `${n} candidat${pluriel(n)} prêt${pluriel(n)} à y travailler` : "aucun candidat"}`);
          const hors = Boolean(paysFiltre) && ZONES_INDEX[label].pays !== paysFiltre;
          texte.classList.toggle("is-hors-filtre", hors);
          texte.classList.toggle("is-sombre", palier(n) >= 4 && !hors);
        });
      });
    }

    // Les encarts n'ont pas d'infobulle Leaflet : une infobulle à eux, qui suit la souris.
    const infoEncart = () => document.getElementById("cand-encart-tip");
    function montrerInfoEncart(label, ev, cible) {
      const tip = infoEncart();
      tip.innerHTML = zoneTooltip(label);
      tip.hidden = false;
      if (ev) placerInfoEncart(ev);
      else {
        const r = cible.getBoundingClientRect();
        placerInfoEncart({ clientX: r.left + r.width / 2, clientY: r.top });
      }
    }
    // Toujours hors des encarts, pour ne pas cacher ceux qu'on compare : à gauche de la colonne
    // (par-dessus la grande carte), ou au-dessus de la bande.
    function placerInfoEncart(ev) {
      const tip = infoEncart();
      const w = tip.offsetWidth, h = tip.offsetHeight;
      const bloc = document.getElementById("cand-encarts").getBoundingClientRect();
      const colonne = getComputedStyle(document.querySelector(".cand-carte-corps")).flexDirection === "row";
      const x = colonne ? bloc.left - w - 10 : ev.clientX - w / 2;
      const y = colonne ? ev.clientY - h / 2 : bloc.top - h - 8;
      tip.style.left = `${Math.max(8, Math.min(x, window.innerWidth - w - 8))}px`;
      tip.style.top = `${Math.max(8, Math.min(y, window.innerHeight - h - 8))}px`;
    }
    function cacherInfoEncart() {
      infoEncart().hidden = true;
    }

    // Passer une zone au premier plan, pour que son liseré ne soit pas recouvert par ses voisines.
    function auPremierPlan(label) {
      if (zoneLayers[label]) zoneLayers[label].bringToFront();
      const p = encartChemins[label];
      if (p) p.parentNode.insertBefore(p, p.parentNode.querySelector("text"));
    }

    // Zone cerclée : celle du filtre, ou le polygone d'un pays qui n'en a qu'un (Luxembourg).
    function estChoisie(label, zone) {
      const pays = zoneLabelPays(zone);
      return zone === label || Boolean(pays && ZONES_INDEX[label].niveau === "pays" && ZONES_INDEX[label].pays === pays);
    }

    function zoneTooltip(label) {
      const n = zoneCounts[label] || 0;
      const nationaux = n - (zoneNommee[label] || 0);
      const pays = ZONES_INDEX[label].pays;
      let html = `<h4>${label}</h4><p>${n ? `${n} candidat${pluriel(n)} prêt${pluriel(n)} à y travailler` : "Aucun candidat pour ces critères"}</p>`;
      if (nationaux > 0 && ZONES_INDEX[label].niveau !== "pays") {
        html += `<p class="cand-tip-detail">dont ${nationaux} ouvert${pluriel(nationaux)} à ${PAYS_ENTIER[pays]}</p>`;
      }
      const geste = !n ? ""
        : !modeListe ? "Cliquez pour voir les profils"
        : estChoisie(label, zoneFiltre()) ? "Cliquez pour retirer ce filtre"
        : `Cliquez pour voir ${n === 1 ? "ce profil" : `ces ${n} profils`}`;
      if (geste) html += `<p class="cand-tip-geste">${geste}</p>`;
      return `<div class="offre-map-popup">${html}</div>`;
    }

    function initMap() {
      const mapEl = document.getElementById("offres-map");
      if (!mapEl || typeof L === "undefined") return;
      // Le clic filtre : pas de zoom au double-clic. Au doigt, glisser fait défiler la page.
      candMap = L.map(mapEl, {
        scrollWheelZoom: false, doubleClickZoom: false, dragging: !L.Browser.mobile, zoomSnap: 0.25,
      }).setView([46.6, 3], 5);
      candMap.attributionControl.addAttribution("Contours : Natural Earth");

      const metropole = [];
      ZONES_GEO.forEach((g) => {
        const latlngs = g.poly.map((poly) => poly.map((ring) => ring.map(([x, y]) => [y * GEO_PAS, x * GEO_PAS])));
        const layer = L.polygon(latlngs, {
          className: "cand-zone", color: "#FFFDF8", weight: 1, fillColor: TEINTES[0], fillOpacity: 1,
        });
        layer.bindTooltip(() => zoneTooltip(g.label), { sticky: true, direction: "top", offset: [0, -10], className: "cand-zone-tip" });
        if (SOURIS) {   // au doigt, pas de mouseout : la zone touchée resterait « survolée »
          layer.on("mouseover", () => survolZone(g.label));
          layer.on("mouseout", () => finSurvolZone(g.label));
        }
        layer.on("click", (e) => {
          // Le second clic d'un double-clic retirerait le filtre que le premier vient de poser.
          if (e.originalEvent && e.originalEvent.detail > 1) return;
          choisirZone(g.niveau === "pays" ? `pays:${g.pays}` : g.label);
        });
        layer.addTo(candMap);
        zoneLayers[g.label] = layer;
        zoneBornes[g.label] = layer.getBounds();
        if (!estOutreMer(g.label)) metropole.push(zoneBornes[g.label]);
        zoneEtiquettes[g.label] = L.marker([g.lat, g.lon], {
          icon: L.divIcon({ className: "cand-zone-num", html: "", iconSize: [28, 16], iconAnchor: [14, 8] }),
          interactive: false, keyboard: false,
        }).addTo(candMap);
      });
      boundsMetropole = unionBornes(metropole);
      construireEncarts();

      // Légende sous la carte, pas dessus : elle cachait le Sud-Ouest sur téléphone.
      const bornes = PALIERS.map((p, i) => {
        const fin = PALIERS[i + 1] && PALIERS[i + 1] - 1;
        return fin === undefined ? `${p}+` : fin === p ? `${p}` : `${p}–${fin}`;
      });
      document.getElementById("cand-legende").innerHTML =
        `<span class="cand-legende-titre">Candidats prêts à y travailler :</span>` +
        ["0", ...bornes].map((b, i) => `<span class="cand-legende-pas"><i style="background:${TEINTES[i]}"></i>${b}</span>`).join("");

      candMap.on("zoomend", majEtiquettes);
      document.getElementById("cand-map-note").addEventListener("click", (e) => {
        const bouton = e.target.closest("[data-zone]");
        if (bouton) choisirZone(bouton.getAttribute("data-zone"));
      });
      // La hauteur de la carte suit celle de la note (pastilles, survol) : Leaflet doit le savoir.
      if (window.ResizeObserver) {
        new ResizeObserver(() => {
          candMap.invalidateSize({ pan: false });
          majEtiquettes();
        }).observe(mapEl);
        new ResizeObserver(majEncarts).observe(document.getElementById("cand-encarts"));
      }
      requestAnimationFrame(() => {
        candMap.invalidateSize();
        cadrer(true);
      });
      window.addEventListener("resize", () => {
        candMap.invalidateSize();
        majEtiquettes();
      });
    }

    // Depuis l'étape 1, choisir une zone ouvre ses candidats ; à l'étape 2, recliquer la zone
    // choisie retire le filtre.
    function choisirZone(value) {
      const select = document.getElementById("cand-filtre-zone");
      if (zoneSurvolee && !SOURIS) finSurvolZone(zoneSurvolee);
      if (candMap) candMap.eachLayer((l) => l.closeTooltip && l.closeTooltip());
      if (!modeListe) {
        ouvrirListe();
        select.value = value;
        renderCandidats();
        montrerResultats();
        return;
      }
      select.value = select.value === value ? "" : value;
      renderCandidats();
      // La liste raccourcit : si l'on avait défilé, ramener au titre plutôt que sur le pied de page.
      if (document.getElementById("cand-resultats").getBoundingClientRect().top < 0) montrerResultats();
    }

    function majCarte(horsZone, filtered) {
      const zone = zoneFiltre();
      const paysFiltre = zoneLabelPays(zone);
      Object.keys(ZONES_INDEX).forEach((label) => {
        zoneCounts[label] = horsZone.filter((c) => candidatCouvre(c, label)).length;
        zoneNommee[label] = horsZone.filter((c) => c.zones.some((z) => z.label === label)).length;
      });
      majNote(horsZone, filtered, zone);
      if (!candMap) return;
      Object.entries(zoneLayers).forEach(([label, layer]) => {
        const teinte = TEINTES[palier(zoneCounts[label])];
        layer.setStyle({ fillColor: teinte });
        if (encartChemins[label]) encartChemins[label].setAttribute("fill", teinte);
        elsDe(label).forEach((el) => {
          el.classList.toggle("is-choisie", estChoisie(label, zone));
          el.classList.toggle("is-hors-filtre", Boolean(paysFiltre) && ZONES_INDEX[label].pays !== paysFiltre);
        });
      });
      Object.keys(zoneLayers).filter((l) => estChoisie(l, zone)).forEach(auPremierPlan);
      // La note vient de changer de hauteur : mesurer la carte avant de la cadrer.
      candMap.invalidateSize({ pan: false });
      majEtiquettes();
      cadrer(false);
      // Un filtre changé pendant le survol d'un département : infobulle et fiches à jour.
      if (zoneSurvolee) {
        const tip = zoneLayers[zoneSurvolee].getTooltip();
        if (tip && zoneLayers[zoneSurvolee].isTooltipOpen()) tip.update();
        if (!infoEncart().hidden) infoEncart().innerHTML = zoneTooltip(zoneSurvolee);
        survolZone(zoneSurvolee);
      }
    }

    // Le nombre ne s'écrit que si la zone est assez grande à l'écran et ne recouvre pas celui d'une
    // zone plus grande (Paris, petite couronne et petits cantons : au survol, en zoomant, ou en
    // tapant leur nom dans le champ de l'étape 1).
    function majEtiquettes() {
      if (!candMap) return;
      const paysFiltre = zoneLabelPays(zoneFiltre());
      const poses = [];
      const taille = (label) => {
        const b = zoneBornes[label];
        const nw = candMap.latLngToContainerPoint(b.getNorthWest());
        const se = candMap.latLngToContainerPoint(b.getSouthEast());
        return { w: se.x - nw.x, h: se.y - nw.y };
      };
      Object.keys(zoneEtiquettes)
        .map((label) => ({ label, ...taille(label) }))
        .sort((a, b) => b.w * b.h - a.w * a.h)
        .forEach(({ label, w, h }) => {
          const el = etiquetteDe(label);
          if (!el) return;
          const n = zoneCounts[label] || 0;
          const p = candMap.latLngToContainerPoint(zoneEtiquettes[label].getLatLng());
          const boite = { x: p.x - 11, y: p.y - 7, w: 22, h: 14 };
          const libre = !poses.some((q) => boite.x < q.x + q.w && q.x < boite.x + boite.w && boite.y < q.y + q.h && q.y < boite.y + boite.h);
          const ecrit = n && w >= 26 && h >= 18 && libre;
          if (ecrit) poses.push(boite);
          el.textContent = ecrit ? String(n) : "";
          const hors = Boolean(paysFiltre) && ZONES_INDEX[label].pays !== paysFiltre;
          el.classList.toggle("is-hors-filtre", hors);
          el.classList.toggle("is-sombre", palier(n) >= 4 && !hors);
        });
      majEncarts();
    }

    // Leaflet abandonne sans rien dire un cadrage lancé pendant une animation de zoom : il est
    // relancé au moveend qui la termine, avec l'état de ce moment-là. On ne recadre que si le
    // filtre de zone a changé : changer de pratique ou de contrat ne déplace pas la carte.
    function cadrer(force) {
      if (!candMap) return;
      const zone = zoneFiltre();
      if (!force && zone === zoneCadree) return;
      if (candMap._animatingZoom) {
        if (!cadrageEnAttente) {
          cadrageEnAttente = true;
          candMap.once("moveend", () => {
            cadrageEnAttente = false;
            cadrer(true);
          });
        }
        return;
      }
      zoneCadree = zone;
      const pays = zoneLabelPays(zone);
      let bornes = boundsMetropole;
      let maxZoom = 7;
      if (pays) {
        const parts = Object.keys(zoneLayers).filter((l) => ZONES_INDEX[l].pays === pays && !estOutreMer(l)).map((l) => zoneBornes[l]);
        if (parts.length) bornes = unionBornes(parts);
        if (parts.length === 1) maxZoom = 8;   // le Luxembourg, plus petit qu'un département
      } else if (zoneBornes[zone] && !estOutreMer(zone)) {
        bornes = zoneBornes[zone];
        maxZoom = 7.5;   // assez près pour la zone, assez loin pour voir ses voisines
      }
      candMap.stop();
      candMap.fitBounds(bornes, { padding: [24, 24], maxZoom });
    }

    // Sous la carte : ce qu'elle ne montre pas d'elle-même. Les candidats ouverts à tout un pays
    // (comptés dans chacune de ses zones) et les zones sans contour (Polynésie, Nouvelle-Calédonie)
    // en pastilles cliquables ; l'outre-mer a ses encarts.
    function majNote(horsZone, filtered, zone) {
      const parts = [];
      if (zone && !zoneLabelPays(zone) && !zoneLayers[zone] && candMap) {
        parts.push(`${filtered.length} candidat${pluriel(filtered.length)} — zone hors carte`);
      }
      const nationaux = ["France", "Suisse", "Belgique"]
        .map((p) => [p, horsZone.filter((c) => c.zones.some((z) => z.niveau === "pays" && z.pays === p)).length])
        .filter(([, n]) => n)
        .map(([p, n], i) => (i ? `${n} à ${PAYS_ENTIER[p]}` : `${n} ouvert${pluriel(n)} à ${PAYS_ENTIER[p]}`));
      if (nationaux.length) parts.push(`Comptés dans chaque zone de leur pays : ${nationaux.join(", ")}`);
      const loin = Object.keys(ZONES_INDEX)
        .filter((l) => !ZONES_GEO_LABELS.has(l) && ZONES_INDEX[l].niveau !== "pays" && zoneCounts[l])
        .sort((a, b) => a.localeCompare(b, "fr"));
      if (loin.length) {
        parts.push(`Hors du cadre : ${loin.map((l) => `<button type="button" class="cand-om${zone === l ? " is-choisie" : ""}" data-zone="${l}">${l.replace(/\s*\(\d+\)$/, "")} ${zoneCounts[l]}</button>`).join(" ")}`);
      }
      noteTexte = parts.join("<br>");
      const note = document.getElementById("cand-map-note");
      note.innerHTML = noteTexte;
      note.classList.remove("is-hover");
    }

    // Survol d'une fiche : sa zone de recherche garde sa teinte, le reste s'estompe. Si elle est
    // entièrement hors du cadre (outre-mer), la note la nomme.
    function survol(c) {
      finSurvol();
      if (!candMap) return;
      const couvertes = Object.keys(zoneLayers).filter((l) => candidatCouvre(c, l));
      document.getElementById("cand-carte").classList.add("cand-survol");
      couvertes.forEach((l) => {
        elsDe(l).forEach((el) => el.classList.add("is-couvert"));
        etiquettesDe(l).forEach((el) => el.classList.add("is-couvert"));
      });
      const vue = candMap.getBounds();
      if (!couvertes.some((l) => encartChemins[l] || vue.intersects(zoneBornes[l]))) {
        const note = document.getElementById("cand-map-note");
        note.textContent = `Zone de recherche hors du cadre : ${resumeZones(c)}`;
        note.classList.add("is-hover");
      }
    }

    function finSurvol() {
      if (!candMap) return;
      const carte = document.getElementById("cand-carte");
      carte.classList.remove("cand-survol");
      carte.querySelectorAll(".is-couvert").forEach((el) => el.classList.remove("is-couvert"));
      const note = document.getElementById("cand-map-note");
      if (note.classList.contains("is-hover")) {
        note.innerHTML = noteTexte;
        note.classList.remove("is-hover");
      }
    }

    // Survol d'un département : les fiches des candidats qui y cherchent passent au premier plan.
    function survolZone(label) {
      zoneSurvolee = label;
      elsDe(label).forEach((el) => el.classList.add("is-survol"));
      auPremierPlan(label);
      const grid = document.getElementById("cand-grid");
      grid.classList.add("cand-grid-survol");
      grid.querySelectorAll(".offre-card").forEach((card) => {
        const c = CANDIDAT_PAR_REF[card.getAttribute("data-ref")];
        card.classList.toggle("is-zone-hover", Boolean(c && candidatCouvre(c, label)));
      });
    }

    function finSurvolZone(label) {
      zoneSurvolee = null;
      elsDe(label).forEach((el) => el.classList.remove("is-survol"));
      // garder le liseré de la zone choisie au-dessus de ses voisines
      Object.keys(zoneLayers).filter((l) => estChoisie(l, zoneFiltre())).forEach(auPremierPlan);
      const grid = document.getElementById("cand-grid");
      grid.classList.remove("cand-grid-survol");
      grid.querySelectorAll(".is-zone-hover").forEach((card) => card.classList.remove("is-zone-hover"));
    }

    // Arrivée depuis une carte « Nos nouveaux candidats » de l'accueil (?profil=<identifiant opaque>) : la liste
    // complète, la fiche amenée à l'écran et soulignée quelques secondes.
    const refCible = new URLSearchParams(location.search).get("profil");

    // L'étape se décide avant de créer la carte : Leaflet doit naître dans un conteneur visible.
    populateFilters();
    applyFiltersFromUrl();
    modeListe = urlDemandeListe();
    document.getElementById("candidats").classList.toggle("is-accueil", !modeListe);
    placerCarte();
    initMap();
    renderCandidats();
    const ficheCible = refCible && [...document.querySelectorAll(".offre-card")].find((c) => c.dataset.ref === refCible);
    if (ficheCible) {
      ficheCible.classList.add("is-cible");
      // Saut immédiat (le site défile en douceur, trop lent sur quarante fiches), une fois les
      // polices chargées pour que la position soit la bonne.
      document.fonts.ready.then(() => ficheCible.scrollIntoView({ block: "center", behavior: "instant" }));
      setTimeout(() => ficheCible.classList.remove("is-cible"), 4000);
    }

    document.getElementById("cand-zones-liste").innerHTML = [...document.getElementById("cand-filtre-zone").options]
      .filter((o) => o.value && !o.value.startsWith("pays:"))
      .map((o) => `<option value="${o.value}"></option>`).join("");
    document.getElementById("cand-tout-voir").textContent = `ou parcourir les ${CANDIDATS.length} candidats sans choisir de zone`;
    document.getElementById("cand-recherche").addEventListener("submit", (e) => {
      e.preventDefault();
      chercherZone();
    });
    // Une suggestion choisie dans la liste déroulante vaut validation.
    document.getElementById("cand-zone-saisie").addEventListener("input", (e) => {
      document.getElementById("cand-recherche-msg").textContent = "";
      const v = e.target.value;
      if ([...document.getElementById("cand-filtre-zone").options].some((o) => o.value && o.value === v)) chercherZone();
    });
    document.getElementById("cand-tout-voir").addEventListener("click", () => {
      ouvrirListe();
      renderCandidats();
      montrerResultats();
    });
    document.getElementById("cand-changer").addEventListener("click", revenirAccueil);
    window.addEventListener("popstate", () => {
      FILTER_IDS.forEach((id) => { document.getElementById(id).value = ""; });
      applyFiltersFromUrl();
      modeListe = urlDemandeListe();
      renderCandidats();
    });

    FILTER_IDS.forEach((id) => document.getElementById(id).addEventListener("change", renderCandidats));
    document.getElementById("cand-reset").addEventListener("click", () => {
      FILTER_IDS.forEach((id) => { document.getElementById(id).value = ""; });
      renderCandidats();
    });
