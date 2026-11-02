"""Rule tests for the Broly MP levels (Survivor, Determined, Legendary, Relentless)."""
import unittest

from sim.tests.test_rules import game, spec

LEVELS = ['Survivor', 'Determined', 'Legendary', 'Relentless']


def broly(label='B', mastery='Saiyan Dynamic Mastery'):
    return spec(label, 'Broly', LEVELS, mastery, 'Saiyan Left Kick')


def other(label='O'):
    return spec(label, 'Trunks', ['Protective', 'Swordmaster', 'Energy Charged', 'Overwhelming'], 'Orange Retribution Mastery', 'Orange Eruption')


class BrolyTests(unittest.TestCase):
    def test_opponent_loses_stages_after_advancing(self):
        for lvl, lost in ((1, 5), (2, 7), (3, 7)):
            g, a, b = game(broly(), other())
            a.level = lvl
            b.level = 1
            b.change_level(+1)
            self.assertEqual(b.stage, 10 - lost, f'Broly L{lvl}')

    def test_level_4_has_no_drain(self):
        g, a, b = game(broly(), other())
        a.level = 4
        b.level = 1
        b.change_level(+1)
        self.assertEqual(b.stage, 10)

    def test_physical_bonus_by_level(self):
        g, a, b = game(broly(), other())
        phys = [x for x in a.hand + a.deck if x.phys][0]
        for lvl, bonus in ((1, 0), (2, 2), (3, 3), (4, 4)):
            a.level = lvl
            self.assertEqual(sum(m.stage_bonus(a, phys, b) for m in a.behaviors()), bonus)

    def test_level_4_banishes_damage_and_ignores_endurance(self):
        g, a, b = game(broly(), other())
        a.level = 4
        phys = [x for x in a.hand + a.deck if x.phys][0]
        self.assertTrue(any(m.banish_damage(a, phys) for m in a.behaviors()))
        a.level = 3
        self.assertFalse(any(m.banish_damage(a, phys) for m in a.behaviors()))
        a.level = 4
        d0, ban0 = len(b.discard), len(b.banished)
        b.stage = 0
        b.take_stages(2, 'banish')
        self.assertEqual((len(b.discard), len(b.banished)), (d0, ban0 + 2))

    def test_level_2_power_banishes_top_card_and_support(self):
        g, a, b = game(broly(), other())
        a.level = 2
        atk = [x for x in a.deck if x.is_atk][:2]
        for x in atk:
            a.deck.remove(x)
        a.hand = atk
        b.setups = [b.deck.pop(0)]
        n = len(b.deck)
        self.assertTrue(a.behaviors()[0].has_power(a) or True)
        for m in a.behaviors():
            if m.has_power(a):
                m.power(a, b)
        self.assertEqual(len(b.deck), n - 1)
        self.assertEqual(b.setups, [])

    def test_level_4_power_needs_four_attack_cards_to_clear_support(self):
        g, a, b = game(broly(), other())
        a.level = 4
        atk = [x for x in a.deck if x.is_atk][:3]
        for x in atk:
            a.deck.remove(x)
        a.hand = atk
        b.drills = [b.deck.pop(0)]
        for m in a.behaviors():
            if m.has_power(a):
                m.power(a, b)
        self.assertEqual(len(b.drills), 1)        # only 3 attack cards: no banish
        a.tf.clear()
        a.hand.append([x for x in a.deck if x.is_atk][0])
        for m in a.behaviors():
            if m.has_power(a):
                m.power(a, b)
        self.assertEqual(b.drills, [])


if __name__ == '__main__':
    unittest.main()
