// Rendu PDF du dossier de présentation candidat par Playwright (Chromium), avec mesure de l'état
// de la page AVANT impression : échelle retenue, mode chips/compact, débordement, polices.
//
// Usage : node cv_pdf.js <dossier.html> <sortie.pdf> [apercu.png]
// Variable : PW_MODULE = chemin du module playwright (défaut : « playwright », résolu depuis le cwd).
// Sortie : une ligne JSON sur stdout. Code 0 si le PDF est écrit, 1 sinon.
//
// Pourquoi Playwright et pas `chrome --print-to-pdf` : on peut lire l'état de la page (le `--scale`
// que la routine d'auto-ajustement a retenu, et si elle déborde encore) — ce qu'un print-to-pdf
// aveugle ne dit pas. Le PDF et l'aperçu PNG sortent de la même page, donc du même état.

const path = require("path");
const { chromium } = require(process.env.PW_MODULE || "playwright");

(async () => {
  const [html, pdf, png] = process.argv.slice(2);
  if (!html || !pdf) {
    console.log(JSON.stringify({ erreur: "usage : node cv_pdf.js <dossier.html> <sortie.pdf> [apercu.png]" }));
    process.exit(1);
  }
  // Dans le conteneur des routines, Playwright ne peut pas télécharger son navigateur (proxy) :
  // on lui donne le Chromium préinstallé (CV_CHROME, posé par cv_candidat.py preparer).
  const exe = process.env.CV_CHROME;
  const b = await chromium.launch({ args: ["--no-sandbox", "--disable-gpu"],
                                    ...(exe ? { executablePath: exe } : {}) });
  const p = await b.newPage({ viewport: { width: 794, height: 1123 } });
  await p.goto("file://" + path.resolve(html), { waitUntil: "networkidle" });
  await p.evaluate(() => document.fonts.ready);
  // La passe forcée du template tombe à 2 s : on attend qu'elle soit passée.
  await p.waitForTimeout(2600);
  const etat = await p.evaluate(() => {
    const PAGE = document.getElementById("page");
    const FIT = document.getElementById("fit");
    const overflow =
      (FIT && FIT.scrollHeight > FIT.clientHeight + 1) ||
      (PAGE && PAGE.scrollHeight > PAGE.clientHeight + 1);
    function contenu(id) {
      const c = document.getElementById(id);
      if (!c) return 0;
      const t = c.getBoundingClientRect().top, d = c.lastElementChild;
      return d ? Math.round(d.getBoundingClientRect().bottom - t) : 0;
    }
    const cols = document.querySelector(".cols");
    const foot = document.querySelector("footer");
    return {
      scale: getComputedStyle(document.documentElement).getPropertyValue("--scale").trim(),
      mode: document.querySelector(".grp.compact") ? "compact" : "chips",
      overflow: !!overflow,
      fonts: document.fonts.status,
      // Fraunces n'est chargée qu'en graisses 500 et 600 : un check à la graisse par défaut (400)
      // répond faux alors que la police est là. On interroge la graisse réellement utilisée.
      inter: document.fonts.check("400 12px Inter"),
      fraunces: document.fonts.check("600 12px Fraunces"),
      colonneDispo: cols ? Math.round(cols.getBoundingClientRect().height) : 0,
      contenuAside: contenu("aside"),
      contenuMain: contenu("main"),
      piedVisible: !!(foot && PAGE && foot.getBoundingClientRect().bottom <= PAGE.getBoundingClientRect().bottom + 1),
      nbActes: document.querySelectorAll(".li").length,
      titre: document.title
    };
  });
  if (png) await p.screenshot({ path: png, fullPage: false });
  await p.pdf({ path: pdf, preferCSSPageSize: true, printBackground: true,
                margin: { top: "0", right: "0", bottom: "0", left: "0" } });
  await b.close();
  console.log(JSON.stringify(etat));
})().catch((e) => {
  console.log(JSON.stringify({ erreur: String(e && e.message ? e.message : e) }));
  process.exit(1);
});
