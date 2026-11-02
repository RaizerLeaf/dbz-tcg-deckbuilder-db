"""The app knows each card by one printing (the first). These tests pin down how deckcode maps reprints (see scripts/audit_reprints.py, REPRINT_AUDIT.md)."""
import collections
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import deckcode as dc  # noqa: E402


class Reprints(unittest.TestCase):
    def test_redesigned_ally_reprint_maps_to_the_first_printing(self):
        # Tenshinhan C9 (Set 1, "(Heroes only.)") and EV-S60 (Set 4, redesigned layout) are one card; the app answered "Unknown card EV-S60".
        ids = {c['card_id']: dc.card_code(c) for c in dc.CARDS if c['card_name'] == 'Tenshinhan' and dc.ctype(c) == 'Ally' and c['set_number'] and c['set_number'] <= 7}
        self.assertEqual(sorted(ids.values()), ['C9', 'EV-S60'])
        self.assertEqual({dc.card_code(dc.BY_ID[dc.app_printing(i)]) for i in ids}, {'C9'})

    def test_allies_sharing_a_name_stay_separate_by_subtitle(self):
        by_name = collections.defaultdict(set)
        for c in dc.CARDS:
            if c['set_number'] and c['set_number'] <= 7 and '_RST' not in c['card_id'] and dc.ctype(c) == 'Ally':
                by_name[c['card_name']].add(dc.card_code(dc.BY_ID[dc.app_printing(c['card_id'])]))
        self.assertEqual({k: sorted(v) for k, v in by_name.items() if len(v) > 1},
                         {'Vegeta': ['EV-U93', 'HV-U72'], 'Cell Jr.': ['AW-U76', 'AW-U77', 'AW-U78']})

    def test_every_non_ally_name_is_one_card(self):
        by_name = collections.defaultdict(set)
        for c in dc.CARDS:
            if c['set_number'] and c['set_number'] <= 7 and '_RST' not in c['card_id'] and dc.ctype(c) not in ('Ally', 'Main Personality'):
                by_name[c['card_name']].add(dc.app_printing(c['card_id']))
        self.assertEqual([k for k, v in by_name.items() if len(v) > 1], [])

    def test_the_canonical_printing_is_the_earliest_of_each_card(self):
        for cid, canon in dc.CANONICAL.items():
            a, b = dc.BY_ID[cid], dc.BY_ID[canon]
            self.assertLessEqual((b['set_number'], dc._ORDER.get(b['collection'], 3)), (a['set_number'], dc._ORDER.get(a['collection'], 3)), cid)

    def test_every_deck_in_the_repository_uses_printings_the_app_knows(self):
        root = Path(__file__).resolve().parents[2]
        for f in sorted(list((root / 'decks').glob('*.txt')) + list((root / 'sim' / 'decks').glob('*.txt'))):
            d = dc.decode(f.read_text(encoding='utf-8').strip().splitlines()[0])
            off = [dc.card_code(dc.BY_ID[i]) for i in d['cards'] if dc.app_printing(i) != i]
            self.assertEqual(off, [], f'{f.name} uses reprints the app may not know')


if __name__ == '__main__':
    unittest.main()
