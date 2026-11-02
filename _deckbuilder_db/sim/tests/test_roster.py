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

    def one_per_family(self):
        seen, out = set(), []
        for f in self.modelled():
            fam = R.family(load(str(DB / f)))
            if fam not in seen:
                seen.add(fam)
                out.append(f)
        return out

    def versions_of_one_deck(self):
        by = {}
        for f in self.modelled():
            by.setdefault(R.family(load(str(DB / f))), []).append(f)
        fam = [v for v in by.values() if len(v) >= 2]
        self.assertTrue(fam, 'the repository should contain two versions of the same deck (Orange Trunks)')
        return fam[0]

    def test_unmodelled_decks_are_refused(self):
        orig = R.unmodelled
        R.unmodelled = lambda spec: ['L1 Made Up Level']           # pretend the simulator lacks a level
        try:
            out = R.add(ALL[0], games=2)
        finally:
            R.unmodelled = orig
        self.assertEqual(out['status'], 'refused')
        self.assertEqual(R.read()['decks'], [])

    def test_roster_never_exceeds_its_cap_and_evicts_the_lowest(self):
        files = self.one_per_family()
        cap, orig = 5, R.MAX_ROSTER
        R.MAX_ROSTER = cap                                          # a small cap so the test does not need 26 decks
        try:
            self.assertGreater(len(files), cap)
            for f in files:
                R.add(f, games=2)
                self.assertLessEqual(len(R.read()['decks']), cap)
            r = R.read()
        finally:
            R.MAX_ROSTER = orig
        self.assertEqual(len(r['decks']), cap)
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

    def test_cached_pairs_are_reused_and_invalidated(self):
        files = self.one_per_family()[:3]
        for f in files:
            R.add(f, games=2)
        r = R.read()
        self.assertTrue(r['pairs'])
        out = R.add(files[0], games=2)                           # nothing changed: no re-ranking, same pairs
        self.assertFalse(out['re_ranked_everything'])
        r2 = R.read()
        self.assertEqual(r['pairs'], r2['pairs'])
        r2['sim_hash'] = 'stale'
        R.write(r2)
        self.assertTrue(R.add(files[0], games=2)['re_ranked_everything'])

    def test_only_one_version_of_a_deck_counts(self):
        versions = self.versions_of_one_deck()
        other = [f for f in self.one_per_family() if R.family(load(str(DB / f))) != R.family(load(str(DB / versions[0])))][:2]
        for f in other + versions:                                   # every version is added in turn
            R.add(f, games=4)
        r = R.read()
        on_roster = [d['file'] for d in r['decks'] if d['file'] in versions]
        self.assertEqual(len(on_roster), 1, 'exactly one version of the deck stays on the roster')
        older = [d for d in r['superseded'] if d['file'] in versions]
        self.assertEqual(len(older), len(versions) - 1)
        self.assertTrue(all(d['superseded_by'] == on_roster[0] for d in older))
        best = max(r['decks'] + older, key=lambda d: d['win_pct'] if d['file'] in versions else -1)
        self.assertEqual(best['file'], on_roster[0], 'the kept version is the best-ranked one')

    def test_versions_of_the_same_deck_do_not_play_each_other_in_the_ranking(self):
        versions = self.versions_of_one_deck()
        entries = [(f, load(str(DB / f))) for f in versions]
        cache = {}
        R.evaluate(entries, games=2, cache=cache)
        self.assertEqual(cache, {}, 'no pair is played between versions of one deck')

    def test_cap_default_is_25(self):
        self.assertEqual(R.MAX_ROSTER, 25)

    def test_playtest_is_capped(self):
        with self.assertRaises(ValueError):
            R.playtest(self.modelled()[0], n=R.PLAYTEST_MAX + 1)

    def test_playtest_plays_every_roster_deck_but_itself(self):
        files = self.one_per_family()[:4]
        for f in files:
            R.add(f, games=2)
        res = R.playtest(files[0], n=2)
        self.assertEqual({r['opponent'] for r in res['rows']}, set(files[1:]))


if __name__ == '__main__':
    unittest.main()
