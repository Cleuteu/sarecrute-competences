// Épingle le traitement des liens Markdown par le convertisseur de `creer-brouillons-facebook`.
//
// Bug d'origine (run du 01/09/2026, 2 annonces sur 5) : `mdToHtml` / `mdToText` ne prévoyaient
// rien pour `[texte](url)`. Une adresse écrite dans Airtable sous la forme
// `[sarah.vet@sarecrute.com](mailto:sarah.vet@sarecrute.com)` partait dans le brouillon Facebook
// avec ses crochets et son `mailto:` en clair. Bug silencieux : le brouillon se crée, la
// vérification `dup`/`img` passe, le gras est là — seul un humain qui relit voit la coquille.
//
// Le test lit les fonctions DANS le PROMPT.md (corps distant de la compétence),
// pour qu'il casse si quelqu'un les y modifie.
//
//   node tests/liens_markdown.test.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const md = readFileSync(
  join(root, 'remote-skills/creer-brouillons-facebook/PROMPT.md'), 'utf8');

const src = md.slice(md.indexOf('const esc    ='), md.indexOf('const f = () =>'));
if (!src.includes('mdToText')) throw new Error('convertisseur introuvable dans PROMPT.md');
const { mdToHtml, mdToText } = new Function(src + ';return {mdToHtml, mdToText};')();

let ko = 0;
const ok = (name, cond, got) => {
  if (cond) return console.log('  ok  ', name);
  ko++; console.log('  KO  ', name, '\n        obtenu:', JSON.stringify(got));
};

// Ce que le navigateur affichera : innerText approximé depuis le HTML produit.
const visible = html => html
  .replace(/<\/p><p>/g, '\n\n').replace(/<br>/g, '\n').replace(/<\/?[a-z]+>/g, '')
  .replace(/&nbsp;/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');

console.log('\nliens mailto / tel — le texte seul, jamais le schéma');
{
  const s = 'Contact : [sarah.vet@sarecrute.com](mailto:sarah.vet@sarecrute.com)';
  const h = mdToHtml(s), t = mdToText(s);
  ok('html sans crochets ni mailto:', !/[[\]]|mailto:/.test(h), h);
  ok('html garde l\'adresse',          h.includes('sarah.vet@sarecrute.com'), h);
  ok('text sans crochets ni mailto:', !/[[\]]|mailto:/.test(t), t);
  const tel = mdToText('Tel : [06 12 34 56 78](tel:+33612345678)');
  ok('tel: aplati aussi',              tel === 'Tel : 06 12 34 56 78', tel);
}
{
  // texte différent de l'adresse : on garde le texte, l'adresse est perdue — c'est voulu,
  // Facebook n'accepte pas de lien cliquable au collage et « Écrivez-nous (mailto:...) » serait pire.
  const t = mdToText('[Écrivez-nous](mailto:contact@sarecrute.com)');
  ok('texte conservé', t === 'Écrivez-nous', t);
}

console.log('\nliens http — l\'URL reste visible entre parenthèses');
{
  const s = 'Voir [notre site](https://sarecrute.com/offres)';
  const h = mdToHtml(s), t = mdToText(s);
  ok('html : texte (url)', visible(h) === 'Voir notre site (https://sarecrute.com/offres)', visible(h));
  ok('text : texte (url)', t === 'Voir notre site (https://sarecrute.com/offres)', t);
}
{
  // `link` doit tourner AVANT `esc` : sinon l'esperluette de l'URL sort non échappée.
  const h = mdToHtml('[postuler](https://sarecrute.com/o?ref=fb&utm=grp)');
  ok('& de l\'URL échappé', h.includes('&amp;utm=grp') && !/&utm=/.test(h), h);
}
{
  // gras à l'intérieur du libellé : `link` d'abord, `**` ensuite.
  const h = mdToHtml('[**Postuler ici**](https://sarecrute.com)');
  ok('gras préservé dans le libellé',
     h.includes('<b>Postuler ici</b> (https://sarecrute.com)'), h);
}

console.log('\ncohérence mdToHtml / mdToText — le contrôle de longueur du run en dépend');
for (const [nom, s] of [
  ['annonce avec mailto', '## Vétérinaire canin\n\n**CDI** à Rouen\n\n- Salaire  attractif\n    - Associé junior\n\nContact : [sarah.vet@sarecrute.com](mailto:sarah.vet@sarecrute.com)'],
  ['annonce avec lien',   'Conditions & évolution\n\n[Le poste](https://sarecrute.com/o/12) vous attend'],
  ['annonce sans lien',   '## Titre\n\n**Gras** et  espaces\n- puce'],
]) {
  const v = visible(mdToHtml(s)), t = mdToText(s);
  ok(nom + ' : attendu == obtenu',
     v.trim().replace(/ /g, ' ') === t.trim(), { visible: v, text: t });
}

console.log('\nnon-régression — rien d\'autre ne bouge');
{
  const h = mdToHtml('## Titre\n\n**Gras**, ≥ 3  ans\n    - Sous-puce');
  ok('titre dépouillé de #',  !h.includes('#'), h);
  ok('gras en <b>',            h.includes('<b>Gras</b>'), h);
  ok('double espace en &nbsp;',h.includes('&nbsp;&nbsp;'), h);
  ok('indentation conservée',  h.includes('&nbsp;&nbsp;&nbsp;&nbsp;- Sous-puce'), h);
  const brut = 'Un texte sans le moindre lien, avec des (parenthèses) et des [crochets] isolés.';
  ok('crochets isolés intacts', mdToText(brut) === brut, mdToText(brut));
}

console.log(ko ? `\n${ko} test(s) en échec\n` : '\nTous les tests passent\n');
process.exit(ko ? 1 : 0);
