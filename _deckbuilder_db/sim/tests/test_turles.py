"""Turles's four PanZ levels (Set 3) and their printed text. Run from _deckbuilder_db/:  python -m unittest discover -s sim/tests -t ."""
import unittest

from sim import behaviors as B
from sim.cardmodel import Card
from sim.tests.test_rules import RECS, cid, game, spec

SUBS = ['Shadowy', 'Watchful', 'Triumphant', 'Conquering']


def turles(level):
    t = spec('T', 'Turles', SUBS, 'Saiyan Dynamic Mastery', 'Saiyan Clash')
    g, a, b = game(t)
    a.level = level
    b.deck = [Card(RECS[cid('Saiyan Wrist Block')]) for _ in range(40)]      # no Endurance, so counts are exact
    return g, a, b


class TurlesLevels(unittest.TestCase):
    def test_all_four_levels_are_registered(self):
        for sub in SUBS:
            self.assertIsNotNone(B.mp_behavior('Turles', sub), sub)

    def test_shadowy_styled_attack_gets_plus_two_and_is_unpreventable(self):
        g, a, b = turles(1)
        beh = B.mp_behavior('Turles', 'Shadowy')
        styled = Card(RECS[cid('Saiyan Clash')])
        plain = Card(RECS[cid('Red Energy Blast')])
        self.assertEqual(a.styled(), 'Saiyan')
        self.assertEqual((beh.stage_bonus(a, styled, b), beh.unprevented(a, styled, b)), (2, True))
        self.assertEqual((beh.stage_bonus(a, plain, b), beh.unprevented(a, plain, b)), (0, False))

    def test_watchful_attack_costs_two_and_deals_five_stages_then_opponent_pays_three(self):
        g, a, b = turles(2)
        a.stage, b.stage = 6, 9
        B.mp_behavior('Turles', 'Watchful').power(a, b)
        self.assertEqual(a.stage, 4)                       # cost 2
        self.assertEqual(b.stage, 9 - 5 - 3)               # 5 stages of damage, then pays 3 stages

    def test_watchful_without_three_stages_to_pay_gives_the_attacker_anger_and_a_critical_effect(self):
        g, a, b = turles(2)
        a.stage, b.stage, a.anger = 6, 5, 0
        B.mp_behavior('Turles', 'Watchful').power(a, b)
        self.assertEqual(b.stage, 0)                       # 5 stages of damage; cannot pay 3
        self.assertGreaterEqual(a.anger, 2)

    def test_triumphant_banishes_top_three_of_the_opponent_discard_pile(self):
        g, a, b = turles(3)
        b.discard = [Card(RECS[cid('Saiyan Wrist Block')]) for _ in range(5)]
        top = b.discard[-3:]
        self.assertTrue(B.mp_behavior('Turles', 'Triumphant').power(a, b))
        self.assertEqual((len(b.discard), len(b.banished)), (2, 3))
        self.assertEqual(b.banished, top[::-1])
        self.assertFalse(B.mp_behavior('Turles', 'Triumphant').power(a, b))       # once per turn

    def test_triumphant_continuous_is_plus_three_and_unpreventable(self):
        g, a, b = turles(3)
        beh = B.mp_behavior('Turles', 'Triumphant')
        c = Card(RECS[cid('Red Energy Blast')])
        self.assertEqual((beh.stage_bonus(a, c, b), beh.unprevented(a, c, b)), (3, True))

    def test_conquering_deals_x_stages_and_x_life_cards_and_turns_off_endurance(self):
        g, a, b = turles(4)
        b.stage, a.stage = 4, 5
        n0 = len(b.deck)
        self.assertTrue(B.mp_behavior('Turles', 'Conquering').power(a, b))
        self.assertTrue(a.cb['noend'])
        self.assertEqual(b.stage, 0)                       # X = 4 stages
        self.assertEqual(n0 - len(b.deck), 4)              # and X = 4 life cards


if __name__ == '__main__':
    unittest.main()
