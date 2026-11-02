"""Rule tests for the Raditz behaviours (Set 2 levels), Offensive Guard and the Drills used by the Raditz decks."""
import unittest

from sim import behaviors as B
from sim.cardmodel import Card
from sim.tests.test_rules import RECS, cid, game, spec

LEVELS = ['True Saiyan', 'Confident', 'Angered', 'Triumphant']


def raditz(level, mastery='Red Enraged Mastery', filler='Orange Torching Drill'):
    g, a, b = game(spec('R', 'Raditz', LEVELS, mastery, filler))
    a.level = level
    return g, a, b


def card(name): return Card(RECS[cid(name)])


class RaditzLevels(unittest.TestCase):
    def test_level_1_power_attacks_reveals_two_banishes_one_and_raises_anger(self):
        g, a, b = raditz(1)
        n, ban, hand, anger = len(a.deck), len(a.banished), len(a.hand), a.anger
        self.assertTrue(B.mp_behavior('Raditz', 'True Saiyan').power(a, b))
        self.assertEqual(len(a.deck), n - 2)
        self.assertEqual((len(a.banished) - ban, len(a.hand) - hand), (1, 1))
        self.assertEqual(a.anger, anger + 1)
        self.assertFalse(B.mp_behavior('Raditz', 'True Saiyan').power(a, b))       # once per turn

    def test_level_2_planning_play_destroys_one_card_but_gives_no_anger(self):
        g, a, b = raditz(2)
        d = card('Orange Torching Drill')
        a.hand.append(d)
        n = len(b.deck)
        g.planning(a, b)
        self.assertEqual((n - len(b.deck), a.anger), (1, 0))
        self.assertIn(d, a.drills)

    def test_level_2_entering_play_in_combat_also_raises_anger(self):
        g, a, b = raditz(2)
        g.in_combat = True
        n = len(b.deck)
        B.enter_play(a, card('Orange Crashing Drill'))        # its own text destroys 1 more during combat
        self.assertEqual(a.anger, 1)
        self.assertEqual(n - len(b.deck), 2)

    def test_level_1_has_no_enters_play_effect(self):
        g, a, b = raditz(1)
        g.in_combat = True
        n = len(b.deck)
        B.enter_play(a, card('Orange Hiding Drill'))
        self.assertEqual((n - len(b.deck), a.anger), (0, 0))

    def test_level_3_makes_the_opponent_discard_a_random_card_once_per_turn(self):
        g, a, b = raditz(3)
        b.hand = [card('Red Energy Blast') for _ in range(3)]
        beh = B.mp_behavior('Raditz', 'Angered')
        beh.entering_combat(a, b, False)
        self.assertEqual((len(b.hand), len(b.discard)), (2, 1))
        beh.entering_combat(a, b, False)
        self.assertEqual(len(b.hand), 2)

    def test_level_4_rejuvenates_on_entering_play_and_fetches_once_per_combat_on_a_critical_effect(self):
        g, a, b = raditz(4, filler='Orange Hiding Drill')
        g.in_combat = True
        a.discard = [card('Red Energy Blast')]
        deck = len(a.deck)
        B.enter_play(a, card('Orange Aura Drill'))
        self.assertEqual((len(a.discard), len(a.deck)), (0, deck + 1))               # one card Rejuvenated
        a.drills = []
        a.cb['used'] = set()
        drills = len(a.drills)
        a.crit_effect()
        self.assertEqual(len(a.drills), drills + 1)                                   # searched a Drill from the Life Deck into play
        a.crit_effect()
        self.assertEqual(len(a.drills), drills + 1)                                   # only the first critical effect each combat


class RaditzCards(unittest.TestCase):
    def test_offensive_guard_places_a_drill_from_hand_once_per_combat_and_is_banished_on_advance(self):
        g, a, b = raditz(2)
        og = card("Raditz's Offensive Guard")
        a.attached.append(og)
        a.hand = [card('Orange Hiding Drill'), card('Orange Aura Drill')]
        a.cb['used'] = set()
        g.in_combat = True
        self.assertTrue(B.CARD_PASSIVE["Raditz's Offensive Guard"].power(a, b))
        self.assertEqual((len(a.hand), len(a.drills)), (1, 1))
        self.assertFalse(B.CARD_PASSIVE["Raditz's Offensive Guard"].power(a, b))      # once per combat
        a.change_level(+1)
        self.assertEqual(a.attached, [])
        self.assertIn(og, a.banished)

    def test_torching_drill_only_triggers_for_drills_entering_during_combat(self):
        g, a, b = raditz(1)
        a.drills.append(card('Orange Torching Drill'))
        n = len(b.deck)
        B.enter_play(a, card('Orange Hiding Drill'))
        self.assertEqual(n - len(b.deck), 0)
        g.in_combat = True
        B.enter_play(a, card('Orange Aura Drill'))
        self.assertEqual(n - len(b.deck), 1)

    def test_celebration_searches_the_deck_for_a_styled_drill(self):
        g, a, b = raditz(1, mastery='Orange Retribution Mastery', filler='Orange Hiding Drill')
        ex = B.CARD_EXTRA['Orange Celebration']
        self.assertTrue(ex['can_use'](a, b, None))
        ex['use'](a, b, None)
        self.assertTrue(any(d.name == 'Orange Hiding Drill' for d in a.drills))

    def test_saiyan_analysis_drill_means_four_anger_to_advance_levels_1_to_3_only(self):
        g, a, b = raditz(1, mastery='Saiyan Rampaging Mastery')
        self.assertEqual(a.anger_needed(), 4)                                        # Rampaging alone: 5 - 1
        a.drills.append(card('Saiyan Analysis Drill'))
        self.assertEqual(a.anger_needed(), 4)                                        # not lower than the Mastery's minimum of 4
        a.drills.append(card('Saiyan Analysis Drill'))
        self.assertEqual(a.anger_needed(), 4)                                        # copies do not stack (UNVERIFIED)
        a.level = 4
        self.assertEqual(a.anger_needed(), 5)

    def test_orange_disaster_drill_adds_two_stages_and_one_anger_to_styled_physical_attacks(self):
        g, a, b = raditz(1, mastery='Orange Retribution Mastery')
        a.drills.append(card('Orange Disaster Drill'))
        atk = card('Orange Collision')
        self.assertEqual(sum(x.stage_bonus(a, atk, b) for x in a.behaviors()), 2)
        anger = a.anger
        for x in a.behaviors():
            x.on_play(a, b, atk)
        self.assertEqual(a.anger, anger + 1)


if __name__ == '__main__':
    unittest.main()
