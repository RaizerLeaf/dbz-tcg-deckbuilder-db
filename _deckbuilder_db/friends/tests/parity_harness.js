// Node harness: reads a JSON job on stdin, runs core.js on the built docs/ data, prints JSON results. Used by test_site.py.
const fs = require('fs');
const path = require('path');
const root = process.argv[2];                       // repo root (contains docs/)
const DBZ = require(path.join(root, 'docs', 'core.js'));
const data = new DBZ.Data(JSON.parse(fs.readFileSync(path.join(root, 'docs', 'data', 'cards.json'), 'utf8')));
const parts = JSON.parse(fs.readFileSync(path.join(root, 'docs', 'data', 'pack_parts.json'), 'utf8'));
const job = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = { lists: [], codes: [], packs: [] };
(job.lists || []).forEach((t) => {
  const r = DBZ.convert(data, t);
  if (r.error) { out.lists.push({ error: r.error }); return; }
  const deck = DBZ.decodeCode(data, r.code);
  const c = DBZ.checkDeck(data, deck);
  out.lists.push({ code: r.code, problems: r.problems.map((p) => p.replace(/ \(close:.*$/, '')), errors: c.errors, warnings: c.warnings });
});
(job.codes || []).forEach((code) => {
  try {
    const deck = DBZ.decodeCode(data, code);
    const c = DBZ.checkDeck(data, deck);
    out.codes.push({ errors: c.errors, warnings: c.warnings, total: Object.values(deck.cards).reduce((a, b) => a + b, 0), again: DBZ.encode(data, deck.name, deck.mpName, deck.mastery, deck.cards, deck.mpLevels) });
  } catch (e) { out.codes.push({ exception: e.message }); }
});
(job.packs || []).forEach((p) => { out.packs.push(DBZ.buildPack(parts, p.mp, p.styles)); });
process.stdout.write(JSON.stringify(out));
