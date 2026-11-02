// Optional UI smoke test for the page (needs Playwright, which is preinstalled in Claude Code sessions).
//   NODE_PATH=$(npm root -g) node friends/tests/browser_smoke.js [path to docs/deck-helper.html]
// Opens the single-file page from disk at phone width, walks the four steps, and fails on console errors, external requests or horizontal scroll.
const { chromium } = require('playwright');
const path = require('path');
const file = path.resolve(process.argv[2] || path.join(__dirname, '..', '..', '..', 'docs', 'deck-helper.html'));
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 420, height: 900 } });
  const problems = [];
  p.on('console', (m) => { if (m.type() === 'error') problems.push('console: ' + m.text()); });
  p.on('pageerror', (e) => problems.push('pageerror: ' + e.message));
  p.on('request', (r) => { if (!/^(file|data|blob):/.test(r.url())) problems.push('external request: ' + r.url()); });
  await p.goto('file://' + file);
  await p.waitForSelector('#mp option:nth-child(5)', { state: 'attached' });            // options are never "visible" to Playwright
  const must = (cond, msg) => { if (!cond) problems.push(msg); };
  must(await p.locator('#s3').isHidden(), 'step 3 should be hidden until an MP and a style are chosen');
  await p.selectOption('#mp', 'Trunks');
  await p.check('#styles input[value="Red"]');
  await p.check('#styles input[value="Orange"]');
  must(await p.locator('#s3').isVisible(), 'step 3 should appear after choosing an MP and a style');
  must(/tokens/.test(await p.textContent('#size')), 'size line missing');
  await p.fill('#list', "MP: Nail\nMastery: Black Devious Mastery\n3 Goku's Search\n1 Time Is A Warrior's Tool");
  await p.click('#do-check');
  const res = await p.textContent('#result');
  must(/Named Goku, MP is Nail/.test(res) && /D1\./.test(res), 'deck check should flag the Named card and show a deck code');
  const [dl] = await Promise.all([p.waitForEvent('download'), p.click('#dl-info')]);
  must(/dbz_card_info_Trunks\.md/.test(dl.suggestedFilename()), 'download name');
  must(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'horizontal scroll at 420px');
  await b.close();
  if (problems.length) { console.error('FAIL\n' + problems.join('\n')); process.exit(1); }
  console.log('browser smoke test OK');
})();
