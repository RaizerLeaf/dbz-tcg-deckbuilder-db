/* DBZ TCG Deck Helper: page logic. All rules live in core.js (tested against the Python tools). No network calls except loading ./data/*.json. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  let data, parts;

  function el(tag, props, children) {
    const e = document.createElement(tag);
    Object.keys(props || {}).forEach((k) => { if (k === 'text') e.textContent = props[k]; else if (k === 'class') e.className = props[k]; else e.setAttribute(k, props[k]); });
    (children || []).forEach((c) => e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c));
    return e;
  }

  function copy(text, btn) {
    const done = () => { const old = btn.textContent; btn.textContent = 'Copied'; setTimeout(() => { btn.textContent = old; }, 1500); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done));
    else fallbackCopy(text, done);
  }
  function fallbackCopy(text, done) {
    const t = el('textarea'); t.value = text; document.body.appendChild(t); t.select();
    try { document.execCommand('copy'); done(); } catch (e) { alert('Copy failed: select the text and copy it by hand.'); }
    document.body.removeChild(t);
  }
  function download(name, text) {
    const a = el('a', { href: URL.createObjectURL(new Blob([text], { type: 'text/markdown' })), download: name });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  // ---- tabs ---------------------------------------------------------------------------------------------------
  const tabs = ['pack', 'check', 'browse'];
  function show(which) {
    tabs.forEach((t) => {
      $('t-' + t).setAttribute('aria-selected', String(t === which));
      $('p-' + t).hidden = t !== which;
    });
  }

  // ---- pack tab -----------------------------------------------------------------------------------------------
  function selectedStyles() { return Array.from(document.querySelectorAll('#styles input:checked')).map((i) => i.value); }
  function currentPack() {
    const mp = $('mp').value;
    const styles = selectedStyles();
    const all = styles.length === 6;
    return DBZ.buildPack(parts, mp || null, all && !mp ? [] : styles);
  }
  function refreshPack() {
    const text = currentPack();
    const tokens = Math.floor(text.length / 4);
    const mp = $('mp').value;
    $('size').textContent = 'About ' + tokens.toLocaleString() + ' tokens (' + Math.round(text.length / 1024) + ' KB)' +
      (tokens > 45000 ? '. That may be too big for a free chat: pick one MP and 2 or 3 styles.' : '.');
    $('starter').textContent = 'Follow the instructions at the top of the attached file. I want to build a deck for ' + (mp || '[tell me which MP]') +
      '. Compare 2 or 3 styles first, then build the 60-card list in the format the file asks for.';
  }
  function initPack() {
    const sel = $('mp');
    sel.appendChild(el('option', { value: '', text: 'All MPs (full pack)' }));
    const seen = {};
    data.mps.forEach((g) => { if (!seen[g.name]) { seen[g.name] = true; sel.appendChild(el('option', { value: g.name, text: g.name })); } });
    ['Black', 'Blue', 'Namekian', 'Orange', 'Red', 'Saiyan'].forEach((s) => {
      const cb = el('input', { type: 'checkbox', value: s, checked: 'checked' });
      cb.addEventListener('change', refreshPack);
      $('styles').appendChild(el('label', {}, [cb, s]));
    });
    sel.addEventListener('change', () => {
      if (sel.value) { document.querySelectorAll('#styles input').forEach((i) => { i.checked = false; }); }   // light pack: user picks styles
      else document.querySelectorAll('#styles input').forEach((i) => { i.checked = true; });
      refreshPack();
    });
    $('all-styles').addEventListener('click', () => { document.querySelectorAll('#styles input').forEach((i) => { i.checked = true; }); refreshPack(); });
    $('no-styles').addEventListener('click', () => { document.querySelectorAll('#styles input').forEach((i) => { i.checked = false; }); refreshPack(); });
    $('copy-pack').addEventListener('click', (e) => copy(currentPack(), e.target));
    $('dl-pack').addEventListener('click', () => download('deckbuilder_pack' + ($('mp').value ? '_' + $('mp').value.replace(/\W+/g, '_') : '') + '.md', currentPack()));
    $('copy-starter').addEventListener('click', (e) => copy($('starter').textContent, e.target));
    refreshPack();
  }

  // ---- check tab ----------------------------------------------------------------------------------------------
  function listItems(items, cls) {
    return el('ul', {}, items.map((t) => el('li', { class: cls, text: t })));
  }
  function render(code, deck, problems) {
    const out = $('result');
    out.textContent = '';
    const chk = DBZ.checkDeck(data_, deck);
    const errors = problems.concat(chk.errors);
    let total = 0; Object.keys(deck.cards).forEach((id) => { total += deck.cards[id]; });
    const g = DBZ.mpGroup(data_, deck);
    const head = el('div', { class: 'box' }, [
      el('h3', { text: deck.name + ' - ' + (g ? g.name + ' (' + g.alignment + ')' : deck.mpName) + ', ' + data_.masteries[deck.mastery].name + ', ' + total + ' cards' }),
      el('p', { class: errors.length ? 'err' : 'ok', text: errors.length ? errors.length + ' problem(s) to fix' : 'No rule errors found' })]);
    out.appendChild(head);
    if (code) {
      const box = el('div', { class: 'box' }, [el('h3', { text: 'Deck code (paste into the deck-builder app)' }), el('div', { class: 'codebox', text: code })]);
      const b = el('button', { type: 'button', text: 'Copy deck code' });
      b.addEventListener('click', (e) => copy(code, e.target));
      box.appendChild(b);
      out.appendChild(box);
    }
    if (errors.length) out.appendChild(el('div', { class: 'box' }, [el('h3', { text: 'Errors' }), listItems(errors, 'err')]));
    if (chk.warnings.length) out.appendChild(el('div', { class: 'box' }, [el('h3', { text: 'Warnings (the owner\'s deck-building defaults)' }), listItems(chk.warnings, 'warn')]));
    const rows = Object.keys(deck.cards).map((id) => data_.cards[id]).sort((a, b) => (a.type < b.type ? -1 : a.type > b.type ? 1 : a.name < b.name ? -1 : 1));
    out.appendChild(el('div', { class: 'box' }, [el('h3', { text: 'Cards' }), el('ul', {}, rows.map((c) => el('li', { text: deck.cards[c.id] + ' x ' + c.disp + ' (' + c.type + ')' })))]));
    if (deck.mpLevels) out.appendChild(el('div', { class: 'box' }, [el('h3', { text: 'MP levels' }), el('ul', {}, deck.mpLevels.map((c, i) => el('li', { text: 'L' + (i + 1) + ' ' + data_.mpPrint[c].p.sub + ' (' + c + ')' })))]));
  }
  let data_;
  function initCheck() {
    $('do-check').addEventListener('click', () => {
      const res = DBZ.convert(data_, $('list').value);
      const out = $('result');
      if (res.error) { out.textContent = ''; out.appendChild(el('div', { class: 'box' }, [el('h3', { text: 'Cannot read the list' }), listItems(res.error, 'err')])); return; }
      render(res.code, DBZ.decodeCode(data_, res.code), res.problems);
    });
    $('do-decode').addEventListener('click', () => {
      const out = $('result');
      try { const code = $('list').value.trim(); render(code, DBZ.decodeCode(data_, code), []); }
      catch (e) { out.textContent = ''; out.appendChild(el('div', { class: 'box' }, [el('h3', { text: 'Cannot decode' }), listItems([e.message], 'err')])); }
    });
  }

  // ---- browse tab ---------------------------------------------------------------------------------------------
  function initBrowse() {
    const styles = {}, types = {};
    data.cards.forEach((c) => { styles[c.style] = 1; types[c.type] = 1; });
    Object.keys(styles).sort().forEach((s) => $('bstyle').appendChild(el('option', { value: s, text: s })));
    Object.keys(types).sort().forEach((s) => $('btype').appendChild(el('option', { value: s, text: s })));
    let limit = 60;
    function draw() {
      const q = DBZ.norm($('q').value), st = $('bstyle').value, ty = $('btype').value;
      const hits = data.cards.filter((c) => (!st || c.style === st) && (!ty || c.type === ty) && (!q || DBZ.norm(c.disp + ' ' + c.text).indexOf(q) >= 0));
      $('bcount').textContent = hits.length + ' cards' + (hits.length > limit ? ' (showing ' + limit + ')' : '');
      const box = $('cards'); box.textContent = '';
      hits.slice(0, limit).forEach((c) => box.appendChild(el('div', { class: 'card' }, [
        el('b', { text: c.disp }),
        el('small', { text: [c.type, c.style, c.lim < 3 ? 'limit ' + c.lim : '', c.named ? 'Named ' + c.named : '', c.restr.length ? c.restr.join(', ') + ' only' : ''].filter(Boolean).join(' | ') }),
        el('div', { text: c.text })])));
      if (hits.length > limit) { const b = el('button', { type: 'button', text: 'Show 60 more' }); b.addEventListener('click', () => { limit += 60; draw(); }); box.appendChild(b); }
    }
    ['q', 'bstyle', 'btype'].forEach((id) => $(id).addEventListener('input', () => { limit = 60; draw(); }));
    draw();
  }

  tabs.forEach((t) => $('t-' + t).addEventListener('click', () => show(t)));
  Promise.all([fetch('data/cards.json').then((r) => r.json()), fetch('data/pack_parts.json').then((r) => r.json())]).then((r) => {
    data = r[0]; parts = r[1];
    data_ = new DBZ.Data(data);
    initPack(); initCheck(); initBrowse();
  }).catch((e) => {
    document.querySelector('main').insertBefore(el('p', { class: 'err', text: 'Could not load the card data (' + e + '). If you opened this file from disk, serve the folder with a local web server or use the hosted page.' }), document.querySelector('main').firstChild);
  });
})();
