/* Deck-code encoder / decoder / checker and deck-list parser, ported from scripts/deckcode.py and friends/list_to_code.py.
   Pure functions, no DOM, so Node can test them against the Python originals (friends/tests/test_site.py). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DBZ = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function norm(s) {
    return s.replace(/[’‘]/g, "'").replace(/[“”]/g, '"').replace(/\s+/g, ' ').trim().toLowerCase();
  }
  // Python: urllib.parse.quote(s, safe='').replace('.', '%2E')
  function quote(s) {
    return encodeURIComponent(s).replace(/[!'()*]/g, function (c) { return '%' + c.charCodeAt(0).toString(16).toUpperCase(); }).replace(/\./g, '%2E');
  }
  function unquote(s) { try { return decodeURIComponent(s); } catch (e) { return s; } }

  function Data(raw) {
    this.raw = raw;
    this.cards = {};      // id -> card (canonical, non-MP, non-Mastery)
    this.masteries = {};  // id -> mastery
    raw.cards.forEach((c) => { this.cards[c.id] = c; });
    raw.masteries.forEach((m) => { this.masteries[m.id] = m; });
    this.byCode = {};     // app code -> {kind, id}
    raw.cards.forEach((c) => { this.byCode[c.code] = { kind: 'card', id: c.id }; });
    raw.masteries.forEach((m) => { this.byCode[m.code] = { kind: 'mastery', id: m.id }; });
    Object.keys(raw.alias).forEach((code) => {
      const id = raw.alias[code];
      this.byCode[code] = { kind: this.masteries[id] ? 'mastery' : 'card', id: id, nonFirst: true };
    });
    this.mpPrint = {};    // app code -> {group, level, p}
    raw.mps.forEach((g, gi) => {
      Object.keys(g.levels).forEach((lv) => {
        g.levels[lv].forEach((p) => { this.mpPrint[p.code] = { g: gi, level: lv, p: p }; });
      });
    });
    this.nameIndex = {};  // normalised display or bare name -> [ids]
    raw.cards.forEach((c) => {
      [norm(c.disp), norm(c.name)].forEach((k) => {
        (this.nameIndex[k] = this.nameIndex[k] || []);
        if (this.nameIndex[k].indexOf(c.id) < 0) this.nameIndex[k].push(c.id);
      });
    });
    this.masteryByName = {};
    raw.masteries.forEach((m) => { this.masteryByName[norm(m.name)] = m; });
  }

  function decodeCode(data, code) {
    const p = code.trim().split('.');
    if (p[0] !== 'D1' || p.length < 5) throw new Error('not a D1 deck code');
    const m = data.byCode[p[3]];
    if (!m || m.kind !== 'mastery') throw new Error('unknown Mastery code ' + p[3]);
    const deck = { name: unquote(p[1]), mpName: unquote(p[2]), mastery: m.id, mpLevels: null, cards: {}, warnings: [] };
    if (m.nonFirst) deck.warnings.push(data.masteries[m.id].name + ': the app may not know ' + p[3] + ', use ' + data.masteries[m.id].code);
    let rest = p.slice(4);
    if (rest.length && rest[0].charAt(0) === '_') {
      deck.mpLevels = rest.shift().slice(1).split('_').map((k) => {
        if (!data.mpPrint[k]) throw new Error('unknown MP printing code ' + k);
        return k;
      });
    }
    rest.forEach((t) => {
      const i = t.indexOf('*');
      const k = i < 0 ? t : t.slice(0, i);
      const n = i < 0 ? 1 : parseInt(t.slice(i + 1), 10);
      const hit = data.byCode[k];
      if (!hit || hit.kind !== 'card') throw new Error('unknown card code ' + k);
      if (hit.nonFirst) deck.warnings.push(data.cards[hit.id].name + ': the app may not know ' + k + ', use ' + data.cards[hit.id].code);
      deck.cards[hit.id] = (deck.cards[hit.id] || 0) + n;
    });
    return deck;
  }

  function encode(data, name, mpName, masteryId, cards, levelCodes) {
    const parts = ['D1', quote(name), quote(mpName), data.masteries[masteryId].code];
    if (levelCodes && levelCodes.length) parts.push('_' + levelCodes.join('_'));
    const toks = Object.keys(cards).filter((id) => cards[id] > 0).map((id) => data.cards[id].code + (cards[id] > 1 ? '*' + cards[id] : ''));
    toks.sort();
    return parts.concat(toks).join('.');
  }

  function mpGroup(data, deck) {
    const mps = data.raw.mps;
    if (deck.mpLevels) {
      const gs = {};
      deck.mpLevels.forEach((c) => { gs[data.mpPrint[c].g] = true; });
      const ids = Object.keys(gs);
      if (ids.length === 1) return mps[ids[0]];
    }
    const base = deck.mpName.replace(/\s*\(.*\)$/, '');
    const hits = mps.filter((g) => g.name === base);
    return hits.length === 1 ? hits[0] : null;
  }

  function checkDeck(data, deck) {
    const err = [], warn = deck.warnings.slice();
    const g = mpGroup(data, deck);
    if (!g) return { errors: ['cannot find the MP group for ' + JSON.stringify(deck.mpName).replace(/"/g, "'")], warnings: warn };
    const mp = g.name, align = g.alignment;
    const mastery = data.masteries[deck.mastery];
    if ((mastery.style === 'Saiyan' || mastery.style === 'Namekian') && !g.heritage[mastery.style]) err.push(mp + ' is not on the ' + mastery.style + ' heritage list');
    if (deck.mpLevels) {
      deck.mpLevels.forEach((code, idx) => {
        const lv = String(idx + 1);
        const ok = g.levels[lv].some((p) => p.code === code);
        if (!ok) err.push('MP printing ' + code + ' is not ' + mp + ' Level ' + lv);
      });
    }
    let total = 0;
    Object.keys(deck.cards).forEach((id) => { total += deck.cards[id]; });
    if (total !== 60) err.push(total + ' cards, not 60');
    const names = {};
    const other = align === 'Villain' ? 'Heroes' : 'Villains';
    Object.keys(deck.cards).forEach((id) => {
      const c = data.cards[id];
      names[c.name] = (names[c.name] || 0) + deck.cards[id];
      if (c.restr.indexOf(other) >= 0) err.push(c.name + ': ' + other + ' only');
      c.restr.forEach((r) => {
        if (/Mastery$/.test(r) && r !== mastery.name) err.push(c.name + ': ' + r + ' only');
      });
      if (c.style !== 'Freestyle' && c.style !== mastery.style) err.push(c.name + ': ' + c.style + ' card, but the Mastery is ' + mastery.style + " (all Styled cards must match the Mastery's style)");
      if (c.named && c.named !== mp) err.push(c.name + ': Named ' + c.named + ', MP is ' + mp);
      if (c.type === 'Ally' && (c.align === 'Hero' || c.align === 'Villain') && c.align !== align) err.push(c.name + ': ' + c.align + ' Ally in a ' + align + ' deck');
      if (c.type === 'Ally' && (g.noAlly || []).indexOf(c.name) >= 0) err.push(c.name + ': Ally with the MP name');
    });
    Object.keys(names).forEach((nm) => {
      const id = Object.keys(deck.cards).filter((i) => data.cards[i].name === nm)[0];
      const lim = data.cards[id].lim;
      if (names[nm] > lim) err.push(nm + ' x' + names[nm] + ', limit ' + lim);
    });
    const sets = {};
    Object.keys(names).forEach((nm) => { if (nm.indexOf(' Dragon Ball ') >= 0) sets[nm.split(' Dragon Ball')[0]] = true; });
    if (Object.keys(sets).length > 1) err.push('more than one Dragon Ball set: [' + Object.keys(sets).sort().map((s) => "'" + s + "'").join(', ') + ']');
    if ((names["Time Is A Warrior's Tool"] || 0) !== 1) warn.push("Time Is A Warrior's Tool is not x1");
    const want = align === 'Hero' ? 'Confrontation' : 'Stare Down';
    if ((names[want] || 0) < 2) warn.push('fewer than 2 ' + want);
    return { errors: err, warnings: warn };
  }

  // ---- plain-text list -> deck code ------------------------------------------------------------------------
  function lev(a, b) {
    const m = a.length, n = b.length;
    const d = [];
    for (let i = 0; i <= m; i++) { d[i] = [i]; }
    for (let j = 1; j <= n; j++) d[0][j] = j;
    for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    return d[m][n];
  }
  function closeMatches(word, pool, n) {
    return pool.map((w) => ({ w: w, s: 1 - lev(word, w) / Math.max(word.length, w.length, 1) }))
      .filter((x) => x.s >= 0.6).sort((a, b) => b.s - a.s).slice(0, n).map((x) => x.w);
  }

  function parseList(data, textBlock) {
    const d = { name: 'Deck', mp: null, levels: null, mastery: null, cards: {}, unknown: [], ambiguous: [] };
    const pool = Object.keys(data.nameIndex);
    textBlock.split(/\r?\n/).forEach((raw) => {
      const line = raw.trim().replace(/^`+|`+$/g, '').trim();
      if (!line || /^(total|```|#)/i.test(line)) return;
      let m = line.match(/^(name|mp|levels|mastery)\s*:\s*(.+)$/i);
      if (m) {
        const k = m[1].toLowerCase(), v = m[2].trim();
        if (k === 'name') d.name = v;
        else if (k === 'mp') {
          const q = v.match(/^(.*?)\s*\(([^)]*)\)\s*$/);
          if (q && /^(hero|villain)$/i.test(q[2].trim())) d.mp = { base: q[1].trim(), align: q[2].trim(), app: null };
          else if (q) d.mp = { base: q[1].trim(), align: null, app: v };
          else d.mp = { base: v, align: null, app: null };
        } else if (k === 'levels') d.levels = v.split(/[,;/]/).map((x) => x.trim()).filter(Boolean);
        else d.mastery = v;
        return;
      }
      m = line.match(/^(\d+)\s*x?\s+(.+?)\s*$/i);
      if (!m) { d.unknown.push({ line: line, close: [] }); return; }
      const n = parseInt(m[1], 10), nm = m[2];
      const hits = data.nameIndex[norm(nm)];
      if (!hits) d.unknown.push({ line: line, close: closeMatches(norm(nm), pool, 3).map((k) => data.cards[data.nameIndex[k][0]].disp) });
      else if (hits.length > 1) d.ambiguous.push({ line: line, ids: hits.slice().sort() });
      else d.cards[hits[0]] = (d.cards[hits[0]] || 0) + n;
    });
    return d;
  }

  function convert(data, textBlock) {
    const d = parseList(data, textBlock);
    if (!d.mp) return { error: ['no "MP:" line'] };
    const groups = data.raw.mps.filter((g) => norm(g.name) === norm(d.mp.base) && (!d.mp.align || g.alignment.toLowerCase() === d.mp.align.toLowerCase()));
    if (groups.length !== 1) {
      return { error: ['MP ' + JSON.stringify(d.mp.base).replace(/"/g, "'") + ': ' + (groups.length ? 'exists as Hero and Villain, write "MP: ' + d.mp.base + ' (Hero)" or "(Villain)"' : 'not found')] };
    }
    const g = groups[0];
    const mastery = data.masteryByName[norm(d.mastery || '')];
    if (!mastery) {
      const close = closeMatches(norm(d.mastery || ''), Object.keys(data.masteryByName), 3).map((k) => data.masteryByName[k].name);
      return { error: ['Mastery ' + JSON.stringify(d.mastery).replace(/"/g, "'") + ' not found' + (close.length ? '; close: ' + JSON.stringify(close) : '')] };
    }
    let levelCodes = null;
    if (d.levels) {
      if (d.levels.length !== 4) return { error: ['"Levels:" needs exactly 4 names'] };
      levelCodes = [];
      for (let i = 0; i < 4; i++) {
        const lv = String(i + 1);
        const cands = g.levels[lv].filter((p) => norm(p.sub || '') === norm(d.levels[i]));
        if (!cands.length) return { error: [g.name + ' has no Level ' + lv + ' called ' + JSON.stringify(d.levels[i]).replace(/"/g, "'") + ' in Sets 1-7'] };
        cands.sort((a, b) => (a.set - b.set) || (a.order - b.order) || (a.id < b.id ? -1 : 1));
        levelCodes.push(cands[0].code);
      }
    }
    const problems = [];
    d.unknown.forEach((u) => problems.push('unknown card line ' + JSON.stringify(u.line).replace(/"/g, "'") + (u.close.length ? ' (close: ' + JSON.stringify(u.close) + ')' : '')));
    d.ambiguous.forEach((a) => problems.push('ambiguous name ' + JSON.stringify(a.line).replace(/"/g, "'") + ': write the code in brackets, e.g. ' + a.ids.map((i) => data.cards[i].disp).join(' or ')));
    const code = encode(data, d.name, d.mp.app || g.name, mastery.id, d.cards, levelCodes);
    return { code: code, group: g, parsed: d, problems: problems };
  }

  // ---- pack assembly (mirrors friends/build_pack.py: build()) ------------------------------------------------------
  const STYLES = ['Black', 'Blue', 'Namekian', 'Orange', 'Red', 'Saiyan', 'Freestyle'];
  function title(s) { return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase(); }
  function buildPack(parts, mp, styles) {
    styles = styles || [];
    const chosen = STYLES.filter((s) => s === 'Freestyle' || !styles.length || styles.indexOf(s) >= 0);
    const mpsText = mp ? (parts.mpsByName[mp] || parts.mpsHeader) : parts.mpsAll;
    let mast = parts.masteries;
    if (styles.length) {
      const keep = {};
      styles.forEach((s) => { keep[title(s)] = true; });
      mast = mast.split('\n').filter((l) => l.indexOf('|') < 0 || keep[l.split('|')[1].trim()] || l.indexOf('Format') === 0).join('\n') + '\n';
    }
    const files = [mpsText, mast].concat(chosen.map((s) => parts.cards[s]));
    const scope = (!mp && !styles.length) ? 'FULL pack: every MP and every style.'
      : 'LIGHT pack for ' + (mp || 'all MPs') + '; styles included: ' + chosen.join(', ') + ' (ask me to rebuild the pack if you want to compare another style).';
    return parts.instructions + '\n' + scope + '\n\n' + files.join('\n');
  }

  return { Data: Data, norm: norm, quote: quote, decodeCode: decodeCode, encode: encode, mpGroup: mpGroup, checkDeck: checkDeck, parseList: parseList, convert: convert, buildPack: buildPack, STYLES: STYLES };
});
