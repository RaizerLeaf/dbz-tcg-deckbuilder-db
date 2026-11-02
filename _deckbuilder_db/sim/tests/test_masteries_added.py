"""Rule tests for the Masteries added 2026-11-02: Blue Protective, Black Conflict, Saiyan Rampaging, Saiyan Dynamic, Red Ascension."""
import unittest

from sim.tests.test_rules import game, spec

LEVELS = ['Protective', 'Swordmaster', 'Energy Charged', 'Overwhelming']


def trunks(mastery, label='T'):
    return spec(label, 'Trunks', LEVELS, mastery, 'Orange Eruption')


class AngerToAdvance(unittest.TestCase):
    def test_blue_protective_makes_the_opponent_need_6_to_level_but_not_for_mppv(self):
        g, a, b = game(trunks('Orange Retribution Mastery'), trunks('Blue Protective Mastery', 'U'))
        a.level = 2
        self.assertEqual(a.anger_needed(), 6)          # owner ruling: only levelling is affected
        self.assertEqual(b.anger_needed(), 5)          # it does not slow its owner
        a.level = 4
        self.assertEqual(a.anger_needed(), 5)          # MPPV is still 5 anger on Level 4

    def test_saiyan_rampaging_needs_one_less_to_advance(self):
        g, a, b = game(trunks('Saiyan Rampaging Mastery'), trunks('Orange Retribution Mastery', 'U'))
        a.level = 1
        self.assertEqual(a.anger_needed(), 4)
        a.level = 4
        self.assertEqual(a.anger_needed(), 5)

    def test_saiyan_dynamic_begins_on_level_2_and_needs_6(self):
        g, a, b = game(trunks('Saiyan Dynamic Mastery'), trunks('Orange Retribution Mastery', 'U'))
        self.assertEqual(a.level, 2)
        self.assertEqual(a.anger_needed(), 6)

    def test_saiyan_rampaging_levels_up_at_4_anger(self):
        g, a, b = game(trunks('Saiyan Rampaging Mastery'), trunks('Orange Retribution Mastery', 'U'))
        a.raise_anger(4)
        self.assertEqual((a.level, a.anger), (2, 0))


class CriticalAndStages(unittest.TestCase):
    def test_black_conflict_counts_4_life_cards_as_critical(self):
        g, a, b = game(trunks('Black Conflict Mastery'), trunks('Orange Retribution Mastery', 'U'))
        self.assertEqual(min(x for x in (m.own_crit_threshold(a) for m in a.behaviors()) if x), 4)
        self.assertFalse([m for m in b.behaviors() if m.own_crit_threshold(b)])

    def test_red_ascension_gains_2_stages_on_a_critical_effect(self):
        g, a, b = game(trunks('Red Ascension Mastery'), trunks('Orange Retribution Mastery', 'U'))
        a.stage = 4
        a.crit_effect()
        self.assertEqual(a.stage, 6)


if __name__ == '__main__':
    unittest.main()
