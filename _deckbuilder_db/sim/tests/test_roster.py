"""Tests for the 10-deck test roster. Run from _deckbuilder_db/:  python -m unittest discover -s sim/tests -t ."""
import tempfile
import unittest
from pathlib import Path

from sim import roster as R
from sim.loader import load

DB = Path(__file__).resolve().parent.parent.parent
ALL = sorted(p.relative_to(DB).as_posix() for d in R.DECK_DIRS for p in (DB / d).glob('*.txt'))


class Roster(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._orig = R.ROSTER_FILE
        R.ROSTER_FILE = Path(self.tmp.name) / 'roster.json'

    def tearDown(self):
        R.ROSTER_FILE = self._orig
        self.tmp.cleanup()

    def modelled(self):
        return [f for f in ALL if not R.unmodelled(load(str(DB / f)))]

    def test_unmodelled_decks_are_refused(self):
        bad = [f for f in ALL if R.unmodelled(load(str(DB / f)))]
        if not bad:
            self.skipTest('every deck is modelled')
        out = R.add(bad[0], games=2)
        self.assertEqual(out['status'], 'refused')
        self.assertEqual(R.read()['decks'], [])

    def test_roster_never_exceeds_ten_and_evicts_the_lowest(self):
        files = self.modelled()
        self.assertGreaterEqual(len(files), 11, 'the repository should have at least 11 modelled decks for this test')
        for f in files:
            R.add(f, games=2)
            self.assertLessEqual(len(R.read()['decks']), R.MAX_ROSTER)
        r = R.read()
        self.assertEqual(len(r['decks']), R.MAX_ROSTER)
        self.assertTrue(r['retired'])
        lowest_kept = min(d['win_pct'] for d in r['decks'])
        for d in r['retired']:
            self.assertLessEqual(d['win_pct'], lowest_kept)
        # sorted best first
        pcts = [d['win_pct'] for d in r['decks']]
        self.assertEqual(pcts, sorted(pcts, reverse=True))

    def test_same_inputs_give_the_same_ranking(self):
        files = self.modelled()[:4]
        entries = [(f, load(str(DB / f))) for f in files]
        self.assertEqual(R.evaluate(entries, games=3), R.evaluate(entries, games=3))

    def test_playtest_is_capped(self):
        with self.assertRaises(ValueError):
            R.playtest(self.modelled()[0], n=R.PLAYTEST_MAX + 1)

    def test_playtest_plays_every_roster_deck_but_itself(self):
        files = self.modelled()[:4]
        for f in files:
            R.add(f, games=2)
        res = R.playtest(files[0], n=2)
        self.assertEqual({r['opponent'] for r in res['rows']}, set(files[1:]))


if __name__ == '__main__':
    unittest.main()
