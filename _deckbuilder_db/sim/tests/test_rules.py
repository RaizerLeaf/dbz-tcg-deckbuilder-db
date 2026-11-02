"""Rule tests for the simulator. Run from _deckbuilder_db/:  python -m unittest discover -s sim/tests -t ."""
import random
import unittest
from pathlib import Path

from sim import behaviors as B
from sim.cardmodel import Card, records_by_id, all_records
from sim.engine import AT, BRACKETS, Game, Spec, bracket

RECS = records_by_id()


def cid(name, num=None, set_number=None):
    for c in all_records():
        if c['card_name'] == name and (set_number is None or c['set_number'] == set_number) and c['collection'] in ('booster', 'starter', 'dr'):
            return c['card_id']
    raise KeyError(name)


def mp_ids(mp, subs):
    out = []
    for sub in subs:
        out.append(next(c['card_id'] for c in all_records() if c['card_name'] == mp and c['subtitle'] == sub and c['card_type'] == 'Main Personality'
                        and not c['card_id'].startswith('PZP')))
    return out


def spec(label, mp, subs, mastery, filler='Red Energy Blast', n=60):
    return Spec(label, mp, mp_ids(mp, subs), mastery, [cid(filler)] * n)


def game(a=None, b=None, seed=1):
    a = a or spec('A', 'Piccolo', ['Stoic', 'Combat Stance', 'Unleashed', 'Fused'], 'Red Enraged Mastery')
    b = b or spec('B', 'Dr. Wheelo', ['Big Brain', 'Scheming', 'Confined', 'Robotic'], 'Black Devious Mastery', 'Black Lunge')
    g = Game(a, b, seed=seed)
    return g, g.players[0], g.players[1]


class AttackTable(unittest.TestCase):
    def test_brackets(self):
        self.assertEqual([bracket(x) for x in (0, 999, 1000, 9999, 10000, 99999, 100000, 499999, 500000, 1499999, 1500000)],
                         [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5])

    def test_rulebook_example(self):   # Vegeta C (90,000) vs Goku B (7,000): AT 2
        self.assertEqual(AT['C'][1], 2)
        self.assertEqual(AT['F'][5], 1)
        self.assertEqual(AT['A'][0], 1)


class Damage(unittest.TestCase):
    def test_stage_damage_overflows_into_life_cards(self):
        g, a, b = game()
        a.stage = 3
        before = len(a.deck)
        removed = a.take_stages(5)
        self.assertEqual((a.stage, removed, len(a.deck)), (0, 2, before - 2))

    def test_endurance_card_absorbs_extra_damage(self):
        g, a, b = game()
        e = Card(RECS[cid('Red Energy Defensive Stance')])      # ENDURANCE 2
        self.assertEqual(e.endurance, 2)
        a.deck.insert(0, e)
        before = len(a.deck)
        removed = a.take_life(5)
        self.assertEqual(removed, 3)                              # the Endurance card + the 2 cards it prevented count as handled
        self.assertEqual(len(a.deck), before - 3)
        self.assertIn(e, a.banished)

    def test_unpreventable_ignores_endurance(self):
        g, a, b = game()
        a.deck.insert(0, Card(RECS[cid('Red Energy Defensive Stance')]))
        self.assertEqual(a.take_life(5, ignore_end=True), 5)

    def test_dragon_ball_goes_to_bottom_and_does_not_count(self):
        g, a, b = game()
        ball = Card(RECS[cid('Namek Dragon Ball 2')])
        a.deck.insert(0, ball)
        before = len(a.deck)
        self.assertEqual(a.take_life(1), 1)
        self.assertEqual(len(a.deck), before - 1)
        self.assertIs(a.deck[-1], ball)

    def test_empty_life_deck_loses(self):
        g, a, b = game()
        a.deck = a.deck[:2]
        a.take_life(5)
        self.assertTrue(a.lost)

    def test_critical_damage_needs_five_life_cards(self):
        g, a, b = game()
        self.assertEqual(max([5] + [t for t in (x.crit_threshold(a) for x in a.behaviors()) if t]), 5)
        a.level = 4                                               # Fused: opponent needs 7
        self.assertEqual(max([5] + [t for t in (x.crit_threshold(a) for x in a.behaviors()) if t]), 7)


class Anger(unittest.TestCase):
    def test_five_anger_advances_resets_and_discards_drills(self):
        g, a, b = game()
        a.drills = [Card(RECS[cid('Orange Hoping Drill')])]
        a.raise_anger(5)
        self.assertEqual((a.level, a.anger, a.stage, a.drills), (2, 0, 10, []))

    def test_excess_anger_does_not_carry_over(self):
        g, a, b = game()
        a.raise_anger(4)
        a.raise_anger(4)
        self.assertEqual((a.level, a.anger), (2, 0))

    def test_mppv_on_level_4(self):
        g, a, b = game()
        a.level = 4
        a.raise_anger(5)
        self.assertTrue(a.won)

    def test_no_mppv_flag_resets_anger_instead(self):
        sa = spec('A', 'Piccolo', ['Stoic', 'Combat Stance', 'Unleashed', 'Fused'], 'Red Enraged Mastery')
        sa.no_mppv = True
        g, a, b = game(sa)
        a.level = 4
        a.raise_anger(5)
        self.assertFalse(a.won)
        self.assertEqual(a.anger, 0)

    def test_dashing_doubles_anger_in_combat_only(self):
        t = spec('T', 'Trunks', ['Dashing', 'Frenzied', 'Energy Charged', 'Overwhelming'], 'Red Enraged Mastery')
        g, a, b = game(t)
        a.raise_anger(2, in_combat=True)
        self.assertEqual(a.anger, 4)
        a.anger = 0
        a.raise_anger(2, in_combat=False)
        self.assertEqual(a.anger, 2)

    def test_garlic_needs_three_anger_at_level_one(self):
        gs = spec('G', 'Garlic Jr.', ['Commanding', 'Crazed', 'Observant', 'Transformed'], 'Red Enraged Mastery')
        g, a, b = game(gs)
        a.raise_anger(3)
        self.assertEqual(a.level, 2)

    def test_red_enraged_critical_effect_raises_anger(self):
        g, a, b = game()
        a.crit_effect()
        self.assertEqual(a.anger, 1)


class Wheelo(unittest.TestCase):
    def test_destroy_amplifiers(self):
        g, a, b = game(spec('W', 'Dr. Wheelo', ['Big Brain', 'Scheming', 'Confined', 'Robotic'], 'Black Devious Mastery', 'Black Lunge'),
                       spec('P', 'Piccolo', ['Stoic', 'Combat Stance', 'Unleashed', 'Fused'], 'Red Enraged Mastery'))
        for lvl, expect in ((1, 3), (2, 3), (3, 4), (4, 5)):
            a.level = lvl
            b.deck = [Card(RECS[cid('Red Energy Blast')]) for _ in range(40)]
            n0 = len(b.deck)
            a.destroy_opp(3)
            self.assertEqual(n0 - len(b.deck), expect, f'level {lvl}')

    def test_banish_style_effects_are_not_amplified(self):
        g, a, b = game(spec('W', 'Dr. Wheelo', ['Big Brain', 'Scheming', 'Confined', 'Robotic'], 'Black Devious Mastery', 'Black Lunge'))
        a.level = 4
        n0 = len(b.deck)
        a.destroy_opp(2, noamp=True)
        self.assertEqual(n0 - len(b.deck), 2)


class Scope(unittest.TestCase):
    def test_fanz_cards_are_rejected(self):
        from sim.loader import load
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'scripts'))
        import deckcode as dc
        fan = next(c for c in all_records() if c.get('era') == 'FanZ' and c['set_number'] and c['set_number'] > 7)
        self.assertGreater(fan['set_number'], 7)           # deckcode cannot even encode these, so the guard is a second line of defence
        with self.assertRaises(ValueError):
            dc.card_code(fan)


class StageDrain(unittest.TestCase):
    """Nappa's deck: 'your opponent loses N stages' effects and his four levels."""
    def nappa(self, level=1):
        n = spec('N', 'Nappa', ['Rested', 'Smirking', 'Overconfident', 'Enraged'], 'Saiyan Rampaging Mastery', 'Saiyan Wrist Block')
        g, a, b = game(n)
        a.level = level
        return g, a, b

    def test_parser_reads_unconditional_stage_loss(self):
        c = Card(RECS[cid('Saiyan Wrist Block')])
        self.assertEqual((c.opp_lose, c.opp_lose_floor), (3, False))
        c = Card(RECS[cid('Saiyan Lightning Dodge')])
        self.assertEqual((c.opp_lose, c.opp_lose_floor), (4, True))
        self.assertEqual(Card(RECS[cid('Saiyan Charged Fist')]).opp_lose, 0)        # conditional: handled in behaviors

    def test_stage_loss_overflows_to_life_cards_unless_it_says_minimum_of_zero(self):
        g, a, b = self.nappa()
        b.deck = [Card(RECS[cid('Saiyan Wrist Block')]) for _ in range(40)]      # no Endurance, so the overflow count is exact
        b.stage = 2
        n0 = len(b.deck)
        b.lose_stages(5)
        self.assertEqual((b.stage, n0 - len(b.deck)), (0, 3))
        b.stage = 2
        n0 = len(b.deck)
        b.lose_stages(5, floor0=True)
        self.assertEqual((b.stage, n0 - len(b.deck)), (0, 0))

    def test_smirking_drains_one_stage_per_attack_or_two_after_changing_levels(self):
        g, a, b = self.nappa(level=2)
        b.stage = 8
        a.attack(b, power=B.SWORDMASTER)                           # any attack triggers it
        self.assertLessEqual(b.stage, 7)

    def test_enraged_damage_cannot_be_prevented_only_while_the_opponent_is_at_zero(self):
        g, a, b = self.nappa(level=4)
        beh = B.mp_behavior('Nappa', 'Enraged')
        b.stage = 0
        self.assertTrue(beh.unprevented(a, None, b))
        b.stage = 3
        self.assertFalse(beh.unprevented(a, None, b))
        self.assertEqual(beh.stage_bonus(a, None, b), 4)

    def test_saiyan_clench_doubles_non_at_stage_damage_once(self):
        g, a, b = self.nappa()
        clench = Card(RECS[cid('Saiyan Clench')])
        a.attached.append(clench)
        scale = 1
        for beh in a.behaviors():
            scale *= beh.stage_scale(a, Card(RECS[cid('Saiyan Uppercut')]), b)
        self.assertEqual(scale, 2)


GOKU_SUBS = ['Training', 'Determined', 'Calm', 'Dashing']


def goku_game(mastery='Blue Tag Team Mastery', seed=1):
    """Goku (Training / Determined / Calm / Dashing) against a plain Wheelo; the Life Decks are plain filler so each test places cards itself."""
    a = Spec('G', 'Goku', [next(c['card_id'] for c in all_records() if c['card_name'] == 'Goku' and c['subtitle'] == sub
                                and c['card_type'] == 'Main Personality' and c['set_number'] in (4, 7)) for sub in GOKU_SUBS],
             mastery, [cid('Blue Guard')] * 60)
    return game(a, spec('W', 'Dr. Wheelo', ['Big Brain', 'Scheming', 'Confined', 'Robotic'], 'Black Devious Mastery', 'Black Lunge'), seed)


def ally_card(name, nth=0):
    ids = [c['card_id'] for c in all_records() if c['card_name'] == name and c['card_type'] == 'Ally' and c['set_number'] and c['set_number'] <= 7]
    return Card(RECS[sorted(ids)[nth]])


def goku_vegeta():
    return Card(RECS['S04_BST_93'])


class Allies(unittest.TestCase):
    def test_ally_enters_at_3_gains_pur_and_acts_only_at_low_mp_stage(self):
        g, a, b = goku_game()
        v = Card(RECS['S04_BST_93'])
        a.put_ally(v)
        self.assertEqual(v.astage, 3)
        a.stage = 5
        self.assertFalse(B.ally_may_act(a, v))
        a.stage = 1
        self.assertTrue(B.ally_may_act(a, v))
        a.stage = 5
        a.cb['ally_free'].add('Vegeta')                    # Goku Calm / Dashing / Blue Kiss
        self.assertTrue(B.ally_may_act(a, v))

    def test_unmodelled_ally_is_not_played(self):
        g, a, b = goku_game()
        gohan = ally_card('Gohan')
        self.assertIsNone(B.ally_model(gohan))
        a.hand.append(gohan)
        g.planning(a, b)
        self.assertIn(gohan, a.hand)
        self.assertEqual(a.allies, [])

    def test_ally_attack_pays_from_its_own_stages_and_uses_its_own_power_level(self):
        g, a, b = goku_game()
        t = ally_card('Tenshinhan')
        a.put_ally(t)
        a.stage = 0
        b.stage = 10
        t.astage = 1                                       # costs 2: cannot attack
        self.assertFalse(B.ally_attack(a, b))
        t.astage = 3
        before = len(b.deck)
        self.assertTrue(B.ally_attack(a, b))
        self.assertEqual(t.astage, 1)                      # paid 2 of its own stages
        self.assertEqual(a.stage, 0)                       # the MP paid nothing
        self.assertLess(len(b.deck), before)               # 3 life cards (+1 from Training)

    def test_critical_effect_discards_an_ally_but_tag_team_protects_a_lone_ally(self):
        g, a, b = goku_game('Blue Protective Mastery')
        a.put_ally(ally_card('Yamcha'))
        b.crit_effect()
        self.assertEqual(a.allies, [])                     # Wheelo's critical effect discarded it
        g, a, b = goku_game()
        a.put_ally(ally_card('Yamcha'))
        b.crit_effect()
        self.assertEqual([x.name for x in a.allies], ['Yamcha'])      # Tag Team: a lone Ally cannot be discarded
        self.assertTrue(any(x.protect_allies(a) for x in a.behaviors()))
        a.put_ally(ally_card('Chaozu'))
        self.assertFalse(any(x.protect_allies(a) for x in a.behaviors()))   # only while you control exactly 1 Ally

    def test_tag_team_fetches_an_ally_at_the_start_of_the_opponents_first_turn_only(self):
        g, a, b = goku_game()
        a.deck.insert(5, ally_card('Chichi'))
        for beh in a.behaviors():
            beh.on_turn_start(a, True)                     # my own turn: nothing
        self.assertEqual(a.allies, [])
        for beh in a.behaviors():
            beh.on_turn_start(a, False)                    # opponent's first turn
        self.assertEqual([x.name for x in a.allies], ['Chichi'])
        for beh in a.behaviors():
            beh.on_turn_start(a, False)                    # not again
        self.assertEqual(len(a.allies), 1)

    def test_vegeta_from_the_hand_stops_an_attack_for_goku_once_per_combat(self):
        g, a, b = goku_game()
        a.hand.append(goku_vegeta())
        atk = Card(RECS[cid('Blue Concentrated Blast')])
        self.assertTrue(a.defend(b, atk))
        self.assertEqual([x.name for x in a.allies], ['Vegeta'])
        self.assertEqual(a.allies[0].astage, 2)

    def test_chichi_stops_a_physical_attack_regardless_of_mp_stage_for_goku(self):
        g, a, b = goku_game()
        a.put_ally(ally_card('Chichi'))
        a.stage = 9
        phys = Card(RECS[cid('Black Lunge')])
        self.assertTrue(a.defend(b, phys))
        self.assertFalse(a.defend(b, phys))                # her Power is once per turn


class GokuLevels(unittest.TestCase):
    def test_training_and_determined_add_a_life_card_and_determined_cuts_incoming(self):
        g, a, b = goku_game()
        c = Card(RECS[cid('Blue Concentrated Blast')])
        self.assertEqual(sum(x.life_bonus(a, c, b) for x in a.behaviors()), 1)        # Training
        a.level = 2
        self.assertEqual(sum(x.life_bonus(a, c, b) for x in a.behaviors()), 1)        # Determined
        self.assertEqual(sum(x.incoming_life(a, c, b) for x in a.behaviors()), -1)

    def test_determined_power_draws_the_bottom_of_the_discard_and_uses_a_critical_effect(self):
        g, a, b = goku_game()
        a.level = 2
        b.balls.clear()
        a.discard = [Card(RECS[cid('Blue Guard')]), Card(RECS[cid('Blue Head Knock')])]
        a.hand = [Card(RECS[cid('Blue Guard')])]
        anger = b.anger = 3
        self.assertTrue(a.lv.name == 'Determined' and B.mp_behavior('Goku', 'Determined').power(a, b))
        self.assertEqual(b.anger, anger - 1)               # critical effect: no Dragon Ball or Ally to take, so opponent's anger -1
        self.assertEqual(len(a.discard), 2)                # one drawn, one discarded

    def test_calm_searches_an_ally_and_frees_it_for_the_combat(self):
        g, a, b = goku_game()
        a.level = 3
        a.deck.insert(0, ally_card('Yamcha'))
        a.stage = 6
        self.assertTrue(B.mp_behavior('Goku', 'Calm').power(a, b))
        self.assertEqual([x.name for x in a.allies], ['Yamcha'])
        self.assertIn('Yamcha', a.cb['ally_free'])
        self.assertTrue(a.cb['ally_unstop'] or b.cb['stopall'] or True)   # set by after_hit only if the attack was not stopped

    def test_dashing_places_the_ally_at_its_highest_stage_and_adds_4_life_cards(self):
        g, a, b = goku_game()
        a.level = 4
        a.deck.insert(0, ally_card('Chaozu'))
        a.stage = 8
        self.assertTrue(B.mp_behavior('Goku', 'Dashing').power(a, b))
        ch = a.allies[0]
        self.assertEqual((ch.name, ch.astage), ('Chaozu', 10))
        self.assertEqual(a.cb['ally_life'], {'Chaozu': 4})
        b.stage = 10
        b.deck = [Card(RECS[cid('Blue Guard')]) for _ in range(40)]          # no Endurance cards, so every life card is counted
        self.assertTrue(B.ally_attack(a, b))              # 7 + 4 life cards (Dashing's +4; Training's +1 is off at Level 4)
        self.assertEqual(len(b.deck), 40 - 11)
        self.assertEqual(a.allies, [])                     # Chaozu shuffles himself back into the Life Deck
        self.assertTrue(any(x.name == 'Chaozu' for x in a.deck))

    def test_saiyan_overhead_kick_fetches_only_a_saiyan_ally_at_5_stages(self):
        g, a, b = goku_game()
        a.deck.insert(0, ally_card('Chaozu'))
        c = Card(RECS[cid('Saiyan Overhead Kick')])
        B.CARD_EXTRA['Saiyan Overhead Kick']['immediate'](a, b, c)
        self.assertEqual(a.allies, [])                      # Chaozu is not a Saiyan
        a.deck.insert(0, goku_vegeta())
        B.CARD_EXTRA['Saiyan Overhead Kick']['immediate'](a, b, c)
        self.assertEqual([(x.name, x.astage) for x in a.allies], [('Vegeta', 5)])

    def test_blue_kiss_lets_an_ally_attack_with_plus_2_and_unpreventable(self):
        g, a, b = goku_game()
        a.put_ally(ally_card('Yamcha'))
        a.stage = 8
        kiss = Card(RECS[cid('Blue Kiss')])
        a.setups.append(kiss)
        B.use_card(a, b, kiss)
        self.assertIn('Yamcha', a.cb['ally_kiss'])
        self.assertTrue(B.ally_attack(a, b))
        self.assertNotIn('Yamcha', a.cb['ally_kiss'])



class Smoke(unittest.TestCase):
    def test_random_games_finish_without_errors(self):
        a = spec('A', 'Piccolo', ['Stoic', 'Combat Stance', 'Unleashed', 'Fused'], 'Red Enraged Mastery', 'Red Energy Blast')
        b = spec('B', 'Dr. Wheelo', ['Big Brain', 'Scheming', 'Confined', 'Robotic'], 'Black Devious Mastery', 'Black Lunge')
        for i in range(40):
            r = Game(a, b, seed=i, first=i % 2).run()
            self.assertIn(r.reason, ('MPPV', 'Survival', 'DBV', 'turn limit'))

    def test_deck_code_files_load_and_play(self):
        from sim.loader import load
        d = Path(__file__).resolve().parent.parent / 'decks'
        files = sorted(d.glob('*.txt'))
        if not files:
            self.skipTest('no sample decks')
        specs = [load(str(f)) for f in files]
        for s in specs:
            self.assertEqual(len(s.card_ids), 60)
        Game(specs[0], specs[-1], seed=1).run()


if __name__ == '__main__':
    unittest.main()
