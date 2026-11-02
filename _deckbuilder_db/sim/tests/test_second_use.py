"""'This attack stays in play to be used a second time this combat' = the same as playing the card a second time from the hand (owner, 2026-11-02);
Red Relaxation: used when entering the next combat, draws the bottom card of the discard pile."""
import unittest

from sim import behaviors as B
from sim.cardmodel import Card
from sim.tests.test_rules import RECS, cid, game, spec


def card(name): return Card(RECS[cid(name)])


def setup():
    g, a, b = game(spec('A', 'Lord Slug', ['Aged', 'Successful', 'Renewed', 'Huge'], 'Red Enraged Mastery'))
    a.reset_combat(); b.reset_combat()
    a.stage = 10
    b.stage = 10
    b.deck = b.deck[:40]
    return g, a, b


class SecondUse(unittest.TestCase):
    def test_parsed(self):
        self.assertEqual(card('Red Double Strike').second, 'always')
        self.assertEqual(card('Red Shattering Leap').second, 'hit')
        self.assertIsNone(card('Namekian Onslaught').second)       # conditional on Dragon Balls: hand-coded, not read as a plain second use
        self.assertIsNone(card('Red Energy Blast').second)

    def test_double_strike_is_played_twice_and_raises_anger_twice(self):
        g, a, b = setup()
        c = card('Red Double Strike')
        a.hand = [c]
        a.anger = 0
        a.attack(b, card=c)
        self.assertEqual(a.cb['attacks'], 2)
        self.assertEqual(a.anger, 2)
        self.assertEqual(a.discard.count(c), 1)                    # the card itself went to the discard pile once
        self.assertIn('used a second time', '\n'.join(g.logs))

    def test_second_use_pays_the_cost_again(self):
        g, a, b = setup()
        c = card('Red Shattering Leap')                            # costs 1 stage
        a.hand = [c]
        a.stage = 10
        a.attack(b, card=c)
        self.assertEqual(a.cb['attacks'], 2)
        self.assertLessEqual(a.stage, 8 + 0)                       # paid twice (stage gains from other effects cannot exceed the cap)

    def test_no_second_use_when_it_cannot_be_paid(self):
        g, a, b = setup()
        c = card('Red Shattering Leap')
        a.hand = [c]
        a.stage = 1
        a.attack(b, card=c)
        self.assertEqual(a.cb['attacks'], 1)

    def test_hit_version_needs_a_hit(self):
        g, a, b = setup()
        c = card('Red Shattering Leap')
        a.hand = [c]
        a.cb['stopall'] = True                                     # stopped (the engine's stopall flag forces a stop): no HIT, no second use
        a.attack(b, card=c)
        self.assertEqual(a.cb['attacks'], 1)
        self.assertNotIn('used a second time', '\n'.join(g.logs))

    def test_plain_version_is_used_again_even_when_stopped(self):
        g, a, b = setup()
        c = card('Red Double Strike')
        a.hand = [c]
        a.cb['stopall'] = True
        a.attack(b, card=c)
        self.assertEqual(a.cb['attacks'], 2)


class RedRelaxation(unittest.TestCase):
    def test_draws_the_bottom_card_of_the_discard_pile(self):
        g, a, b = setup()
        bottom, top = card('Red Blazing Aura'), card('Red Blocking Hand')
        a.discard = [bottom, top]
        c = card('Red Relaxation')
        a.setups = [c]
        n = len(a.hand)
        B.use_setup(a, b, c)
        self.assertIn(bottom, a.hand)
        self.assertEqual(a.discard, [top])
        self.assertEqual(len(a.hand), n + 1)

    def test_used_on_entering_combat_when_attacking_and_when_defending(self):
        for atk_side in (True, False):
            g, a, b = setup()
            me, other = (a, b) if atk_side else (b, a)
            me.discard = [card('Red Blazing Aura')]
            c = card('Red Relaxation')
            me.setups = [c]
            g.combat(a, b)
            self.assertIn(c, me.banished, f'attacking={atk_side}')


if __name__ == '__main__':
    unittest.main()
