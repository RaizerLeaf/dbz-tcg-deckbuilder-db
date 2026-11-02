"""Tests for the friend-access tools. Run from _deckbuilder_db/:  python -m unittest discover -s friends/tests -t ."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent      # _deckbuilder_db/
sys.path.insert(0, str(ROOT / 'friends'))
sys.path.insert(0, str(ROOT / 'scripts'))
import build_pack as bp          # noqa: E402
import list_to_code as l2c       # noqa: E402
import deckcode as dc            # noqa: E402
import cardnames                 # noqa: E402


def deck_to_list(code):
    d = dc.decode(code)
    lines = [f"Name: {d['name']}", f"MP: {d['mp_name']}"]
    if d['mp_levels']:
        lines.append('Levels: ' + ', '.join(dc.BY_ID[i]['subtitle'] for i in d['mp_levels']))
    lines.append(f"Mastery: {dc.BY_ID[d['mastery']]['card_name']}")
    for i, n in sorted(d['cards'].items(), key=lambda kv: dc.BY_ID[kv[0]]['card_name']):
        lines.append(f"{n} {cardnames.DISPLAY[i]}")
    return '\n'.join(lines)


def sample_codes():
    out = []
    for folder in ('sim/decks', 'decks'):
        for f in sorted((ROOT / folder).glob('*.txt')):
            out.append((f.name, f.read_text(encoding='utf-8').strip().splitlines()[0]))
    return out


class Pack(unittest.TestCase):
    def test_pack_contains_only_panz_sets_1_to_7_cards_that_exist(self):
        for c in bp.pool_cards():
            self.assertTrue(1 <= c['set_number'] <= 7, c['card_name'])
            self.assertEqual(c['era'], 'PanZ')
            self.assertNotIn('_RST', c['card_id'])

    def test_every_card_name_appears_once(self):
        names = [c['card_name'] for c in bp.pool_cards()]
        dup = {n for n in names if names.count(n) > 1}
        # Allies can share a name (two Vegetas); anything else must be unique
        for n in dup:
            self.assertTrue(all(c['card_type'] == 'Ally' for c in bp.pool_cards() if c['card_name'] == n), n)

    def test_light_pack_is_much_smaller(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            full = bp.build(outdir=t + '/full')['tokens_est']['whole pack']
            light = bp.build(mp='Trunks', styles=['Red', 'Orange'], outdir=t + '/light')['tokens_est']['whole pack']
        self.assertLess(light, full * 0.6)

    def test_pack_has_the_defaults_and_instructions(self):
        text = (ROOT / 'friends' / 'INSTRUCTIONS.md').read_text(encoding='utf-8')
        self.assertIn("Time Is A Warrior's Tool", text)
        self.assertIn('Confrontation', text)


class ListToCode(unittest.TestCase):
    def test_round_trip_every_sample_deck(self):
        codes = sample_codes()
        self.assertTrue(codes)
        for name, code in codes:
            res, problems = l2c.convert(deck_to_list(code))
            self.assertIsNotNone(res, (name, problems))
            self.assertEqual(problems, [], name)
            self.assertEqual(res[0], code, name)

    def test_unknown_card_is_reported_with_suggestions(self):
        _, code = sample_codes()[0]
        text = deck_to_list(code) + '\n1 Red Hrl'
        res, problems = l2c.convert(text)
        self.assertTrue(any('Red Hrl' in p for p in problems))

    def test_named_card_in_the_wrong_deck_is_an_error(self):
        text = "MP: Nail\nMastery: Black Devious Mastery\n3 Goku's Search"
        res, problems = l2c.convert(text)
        code, g, d = res
        err, _ = dc.check(dc.decode(code))
        self.assertTrue(any("Goku's Search" in e and 'Named' in e for e in err), err)

    def test_missing_mp_or_mastery_is_a_clear_error(self):
        self.assertIn('no "MP:" line', l2c.convert('3 Red Hurl')[1][0])
        self.assertIn('Mastery', l2c.convert('MP: Nail\nMastery: Nope Mastery')[1][0])


if __name__ == '__main__':
    unittest.main()
