"""The browser code (docs/core.js) must give the same answers as the Python tools. Needs `node`; skipped without it.
Run from _deckbuilder_db/:  python -m unittest discover -s friends/tests -t .   (after python friends/build_site.py)"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DB = Path(__file__).resolve().parent.parent.parent
ROOT = DB.parent
sys.path.insert(0, str(DB / 'friends'))
sys.path.insert(0, str(DB / 'scripts'))
import build_pack as bp          # noqa: E402
import list_to_code as l2c       # noqa: E402
import deckcode as dc            # noqa: E402
from tests.test_friends import deck_to_list, sample_codes   # noqa: E402

NODE = shutil.which('node')


def run_js(job):
    r = subprocess.run([NODE, str(DB / 'friends' / 'tests' / 'parity_harness.js'), str(ROOT)], input=json.dumps(job), capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


@unittest.skipUnless(NODE and (ROOT / 'docs' / 'core.js').exists(), 'needs node and a built docs/ (python friends/build_site.py)')
class Parity(unittest.TestCase):
    def test_codes_decode_check_and_re_encode_like_python(self):
        codes = [c for _, c in sample_codes()]
        js = run_js({'codes': codes})['codes']
        for (name, code), j in zip(sample_codes(), js):
            d = dc.decode(code)
            err, warn = dc.check(d)
            self.assertNotIn('exception', j, name)
            self.assertEqual(j['errors'], err, name)
            self.assertEqual(j['warnings'], warn, name)
            self.assertEqual(j['again'], code, name)
            self.assertEqual(j['total'], sum(d['cards'].values()), name)

    def test_lists_convert_to_the_same_code_and_errors(self):
        lists = [deck_to_list(c) for _, c in sample_codes()]
        js = run_js({'lists': lists})['lists']
        for (name, code), j in zip(sample_codes(), js):
            self.assertEqual(j['code'], code, name)

    def test_bad_lists_get_the_same_rule_errors(self):
        cases = ["MP: Nail\nMastery: Black Devious Mastery\n3 Goku's Search\n1 Stare Down\n4 Black Lunge\n2 Orange Uppercut\n3 Namek Dragon Ball 1\n1 Earth Dragon Ball 1",
                 "MP: Dr. Wheelo\nMastery: Saiyan Rampaging Mastery\n3 Dr. Wheelo's History\n1 Confrontation",
                 "MP: Trunks (Awakening)\nMastery: Red Enraged Mastery\nLevels: Dashing, Frenzied, Energy Charged, Overwhelming\n3 Trunks' Sword Slash\n1 Vegeta [EV-U93]"]
        js = run_js({'lists': cases})['lists']
        for text, j in zip(cases, js):
            res, problems = l2c.convert(text)
            code, g, d = res
            err, warn = dc.check(dc.decode(code))
            self.assertEqual(j['code'], code)
            self.assertEqual(sorted(j['errors']), sorted(err), text)
            self.assertEqual(j['warnings'], warn)
            self.assertEqual(len(j['problems']), len(problems))

    def test_packs_match_the_python_pack_builder(self):
        picks = [(None, None), ('Trunks', ['Red', 'Orange']), ('Nail', ['Black', 'Namekian']), ('Vegeta', ['Red'])]
        js = run_js({'packs': [{'mp': m, 'styles': s} for m, s in picks]})['packs']
        for (mp, styles), text in zip(picks, js):
            with tempfile.TemporaryDirectory() as t:
                bp.build(mp=mp, styles=styles, outdir=t)
                self.assertEqual(text, (Path(t) / 'deckbuilder_pack.md').read_text(encoding='utf-8'), (mp, styles))


class SingleFile(unittest.TestCase):
    def test_single_file_page_is_self_contained(self):
        html = (ROOT / 'docs' / 'deck-helper.html').read_text(encoding='utf-8')
        self.assertIn('window.DBZ_INLINE', html)
        self.assertNotIn('src="core.js"', html)
        self.assertNotIn('href="style.css"', html)
        import re
        self.assertEqual(re.findall(r'<script[^>]*\ssrc=', html), [])
        self.assertEqual(re.findall(r'<link[^>]*\shref=', html), [])


class Fresh(unittest.TestCase):
    def test_docs_match_the_sources(self):
        """Fails when cards.json / the site sources changed but `python friends/build_site.py` was not re-run."""
        import io
        import contextlib
        import build_site
        with tempfile.TemporaryDirectory() as t:
            with contextlib.redirect_stdout(io.StringIO()):
                build_site.main(out=t)
            for f in sorted(p for p in Path(t).rglob('*') if p.is_file()):
                rel = f.relative_to(t)
                mine = ROOT / 'docs' / rel
                self.assertTrue(mine.exists(), f'docs/{rel} is missing: run python friends/build_site.py')
                self.assertEqual(mine.read_bytes(), f.read_bytes(), f'docs/{rel} is out of date: run python friends/build_site.py (from _deckbuilder_db/)')


if __name__ == '__main__':
    unittest.main()
