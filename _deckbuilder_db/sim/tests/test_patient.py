"""The opt-in 'patient' policy (--patient-a/-b): declare combat only on Level 4 with 4+ anger. Default behaviour must not change."""
import unittest

from sim.engine import Game
from sim.tests.test_rules import cid, mp_ids, spec
from sim.engine import Spec

LEVELS = ['Protective', 'Swordmaster', 'Energy Charged', 'Overwhelming']


def trunks(patient):
    return Spec('T', 'Trunks', mp_ids('Trunks', LEVELS), 'Orange Retribution Mastery', [cid('Orange Eruption')] * 60, False, patient)


class Patient(unittest.TestCase):
    def game(self, patient):
        g = Game(trunks(patient), spec('B', 'Trunks', LEVELS, 'Orange Retribution Mastery', 'Orange Eruption'), seed=1)
        a = g.players[0]
        a.hand = [a.deck.pop(0) for _ in range(3)]          # Orange Eruption: an affordable attack
        a.stage = 8
        return g, a, g.players[1]

    def test_default_policy_declares_combat_with_an_attack_in_hand(self):
        g, a, b = self.game(False)
        self.assertTrue(g.wants_combat(a, b))

    def test_patient_waits_below_level_4(self):
        g, a, b = self.game(True)
        self.assertFalse(g.wants_combat(a, b))
        a.level, a.anger = 4, 3
        self.assertFalse(g.wants_combat(a, b))

    def test_patient_declares_on_level_4_with_4_anger(self):
        g, a, b = self.game(True)
        a.level, a.anger = 4, 4
        self.assertTrue(g.wants_combat(a, b))


if __name__ == '__main__':
    unittest.main()
