"""Orange Uppercut and Orange Enraged Bash: the search/Rejuvenate choice depends on the situation (owner, 2026-11-02)."""
import unittest

from sim import behaviors as B
from sim.cardmodel import Card
from sim.tests.test_rules import RECS, cid, game, spec

LEVELS = ['Protective', 'Swordmaster', 'Energy Charged', 'Overwhelming']


def card(name): return Card(RECS[cid(name)])


def trunks():
    g, a, b = game(spec('T', 'Trunks', LEVELS, 'Orange Retribution Mastery', 'Orange Eruption'))
    a.deck = [card('Orange Precise Shot'), card('Orange Eruption'), card('Orange Immense Blast'), card('Orange Redirection')] + a.deck[:20]
    a.hand = []
    return g, a, b


def uppercut(a, b): B.CARD_EXTRA['Orange Uppercut']['immediate'](a, b, card('Orange Uppercut'))


class Uppercut(unittest.TestCase):
    def test_against_an_mppv_threat_it_fetches_the_anger_lowering_card(self):
        g, a, b = trunks()
        b.level, b.anger, a.stage = 4, 4, 8
        n = len(a.deck)
        uppercut(a, b)
        self.assertEqual([c.name for c in a.hand], ['Orange Eruption'])
        self.assertEqual((a.stage, len(a.deck)), (6, n - 1))           # paid 2 stages, searched the Life Deck

    def test_against_dragon_balls_it_fetches_the_critical_effect_card(self):
        g, a, b = trunks()
        b.balls = [card('Namek Dragon Ball 1')]
        a.stage = 8
        a.hand = [card('Orange Redirection')]                          # already holding a block
        uppercut(a, b)
        self.assertIn('Orange Immense Blast', [c.name for c in a.hand])

    def test_with_no_block_in_hand_and_no_threat_it_fetches_a_block(self):
        g, a, b = trunks()
        a.deck = [card('Orange Redirection'), card('Orange Precise Shot')] + a.deck[:20]
        a.stage = 8
        uppercut(a, b)
        self.assertEqual([c.name for c in a.hand], ['Orange Redirection'])

    def test_needs_stages_to_pay(self):
        g, a, b = trunks()
        a.stage = 2
        uppercut(a, b)
        self.assertEqual((a.hand, a.stage), ([], 2))

    def test_search_shuffles_the_life_deck(self):
        g, a, b = trunks()
        a.stage = 8
        top = [c for c in a.deck]
        uppercut(a, b)
        self.assertNotEqual([c for c in a.deck], [c for c in top if c not in a.hand])


class EnragedBash(unittest.TestCase):
    def bash(self, a, zone): B._rejuvenate_drill(a, zone)

    def test_below_level_4_it_recycles_devouring_drill_to_the_bottom(self):
        g, a, b = trunks()
        a.level = 2
        a.banished = [card('Orange Burning Aura Drill'), card('Orange Devouring Drill')]
        self.bash(a, a.banished)
        self.assertEqual(a.deck[-1].name, 'Orange Devouring Drill')
        self.assertEqual([c.name for c in a.banished], ['Orange Burning Aura Drill'])

    def test_on_level_4_it_prefers_a_defensive_drill(self):
        g, a, b = trunks()
        a.level = 4
        a.discard = [card('Orange Devouring Drill'), card('Orange Burning Aura Drill')]
        self.bash(a, a.discard)
        self.assertEqual(a.deck[-1].name, 'Orange Burning Aura Drill')

    def test_intimidating_drill_shuffles_and_draws_once_per_combat(self):
        g, a, b = trunks()
        a.drills = [card('Orange Intimidating Drill')]
        a.discard = [card('Orange Hoping Drill'), card('Orange Steady Drill')]
        n = len(a.hand)
        self.bash(a, a.discard)
        self.bash(a, a.discard)
        self.assertEqual(len(a.hand) - n, 1)


if __name__ == '__main__':
    unittest.main()
