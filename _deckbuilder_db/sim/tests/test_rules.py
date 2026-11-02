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


CJ_MP = ['Taunting', 'On the Move', 'Oppressive', 'Confident']


def ally(sub):
    return Card(RECS[{'Trapped': 'S07_BST_76', 'Escaping': 'S07_BST_77', 'Unrelenting': 'S07_BST_78'}[sub]])


def cj_game(mastery='Blue Tag Team Mastery', level=1, filler='Blue Slash'):
    g, a, b = game(spec('CJ', 'Cell Jr.', CJ_MP, mastery, filler), spec('OP', 'Nappa', ['Rested', 'Smirking', 'Overconfident', 'Enraged'],
                                                                      'Saiyan Rampaging Mastery', 'Saiyan Wrist Block'))
    a.level = level
    return g, a, b


class CellJr(unittest.TestCase):
    """Cell Jr.'s four levels, the Cell Jr. Allies and the cards of the three Cell Jr. decks."""
    def test_on_the_move_deals_5_plus_cell_jr_personalities_in_the_discard_pile(self):
        g, a, b = cj_game(level=2)
        a.discard = [ally('Trapped'), ally('Escaping'), ally('Unrelenting'), Card(RECS[cid('Blue Slash')])]
        self.assertEqual(B.CARD_EXTRA['On the Move']['base_stage'](a, b, B.CJ_L2), 8)

    def test_trapped_in_play_adds_one_to_destroy_effects(self):
        g, a, b = cj_game()
        before = len(b.deck)
        a.destroy_opp(2)
        self.assertEqual(before - len(b.deck), 2)
        a.allies.append(ally('Trapped'))
        before = len(b.deck)
        a.destroy_opp(2)
        self.assertEqual(before - len(b.deck), 3)
        a.allies = [ally('Escaping')]          # only Trapped has the Continuous
        before = len(b.deck)
        a.destroy_opp(2)
        self.assertEqual(before - len(b.deck), 2)

    def test_waiting_drill_destroys_2_per_ally_rejuvenated(self):
        g, a, b = cj_game()
        a.drills.append(Card(RECS[cid('Blue Waiting Drill')]))
        a.discard = [ally('Escaping'), ally('Unrelenting')]
        before = len(b.deck)
        for x in list(a.discard):
            a.rejuv_ally(x, a.discard)
        self.assertEqual(before - len(b.deck), 4)
        self.assertEqual([x.name for x in a.deck[-2:]], ['Cell Jr.', 'Cell Jr.'])     # Rejuvenated Allies go to the bottom of the Life Deck

    def test_taunting_discards_an_ally_to_make_the_attack_unstoppable(self):
        g, a, b = cj_game()
        a.hand = [ally('Escaping')]
        tool = Card(RECS[cid("Time Is A Warrior's Tool")])
        b.hand = [tool]
        b.stage = 5
        B.mp_behavior('Cell Jr.', 'Taunting').power(a, b)
        self.assertEqual(len(a.discard), 1)           # the Ally was the cost
        self.assertEqual(b.hand, [tool])               # the defense was never used
        self.assertLess(b.stage, 5)                    # 4 stages of damage went through

    def test_taunting_hit_plays_a_continuous_card_from_the_life_deck(self):
        g, a, b = cj_game()
        a.deck = [Card(RECS[cid('Blue Slash')]), Card(RECS[cid('Blue Waiting Drill')])] + a.deck
        B.mp_behavior('Cell Jr.', 'Taunting').after_hit(a, b, B.CJ_L1, 1)
        self.assertEqual([d.name for d in a.drills], ['Blue Waiting Drill'])

    def test_oppressive_rejuvenates_a_hand_ally_to_stop_a_physical_or_energy_attack_repeatedly(self):
        g, a, b = cj_game(level=3)
        a.hand = [ally('Escaping'), ally('Unrelenting')]
        atk = Card(RECS[cid('Red Energy Blast')])      # 4 life cards
        self.assertTrue(a.defend(b, atk))
        self.assertTrue(a.defend(b, atk))
        self.assertFalse(a.defend(b, atk))
        self.assertEqual(a.hand, [])
        self.assertEqual(len([x for x in a.deck[-2:] if x.name == 'Cell Jr.']), 2)

    def test_on_the_move_stops_one_attack_per_combat(self):
        g, a, b = cj_game(level=2)
        a.hand = [ally('Escaping'), ally('Unrelenting')]
        atk = Card(RECS[cid('Red Energy Blast')])
        self.assertTrue(a.defend(b, atk))
        self.assertFalse(a.defend(b, atk))
        self.assertEqual(len(a.discard), 1)            # discarded, not Rejuvenated: it counts for the 5 + X attack

    def test_confident_banishes_a_hand_ally_to_destroy_3(self):
        g, a, b = cj_game(level=4)
        a.hand = [ally('Escaping')]
        before = len(b.deck)
        self.assertTrue(B.mp_behavior('Cell Jr.', 'Confident').power(a, b))
        self.assertEqual(before - len(b.deck), 3)
        self.assertEqual(len(a.banished), 1)
        self.assertFalse(B.mp_behavior('Cell Jr.', 'Confident').power(a, b))      # no Ally left in hand

    def test_the_ai_plays_trapped_but_keeps_other_allies_as_fuel(self):
        g, a, b = cj_game()
        a.hand = [ally('Trapped'), ally('Escaping')]
        B.plan_allies(a, b)
        self.assertEqual([x.rec['subtitle'] for x in a.allies], ['Trapped'])
        self.assertEqual([x.rec['subtitle'] for x in a.hand], ['Escaping'])

    def test_tag_team_starts_with_an_ally_and_rejuvenates_a_banished_one(self):
        g, a, b = cj_game()
        a.deck = [ally('Escaping'), ally('Trapped')] + a.deck
        B.mastery_behavior('Blue Tag Team Mastery').on_game_start(a)
        self.assertEqual([x.rec['subtitle'] for x in a.allies], ['Trapped'])
        a.banished = [ally('Unrelenting')]
        B.mastery_behavior('Blue Tag Team Mastery').end_of_combat(a, b)
        self.assertEqual(a.banished, [])
        self.assertEqual(a.deck[-1].rec['subtitle'], 'Unrelenting')

    def test_setup_attacks_are_performed_and_discarded_and_setup_defenses_stop(self):
        g, a, b = cj_game()
        ki = Card(RECS[cid('Blue Ki Build Up')])
        a.setups, a.stage = [ki], 10
        a.tf['cj_l1'] = True                 # Taunting already used this turn, so the AI turns to the Setup
        before = len(b.deck)
        self.assertTrue(B.choose_action(a, b))
        self.assertGreater(before - len(b.deck), 0)
        self.assertEqual((a.setups, ki in a.discard), ([], True))
        block = Card(RECS[cid('Blue Blockade')])
        b.setups = [block]
        self.assertTrue(b.defend(a, Card(RECS[cid('Red Energy Blast')])))
        self.assertEqual(b.setups, [])

    def test_blue_overcharge_prevents_only_the_next_attack(self):
        g, a, b = cj_game()
        oc = Card(RECS[cid('Blue Overcharge')])
        b.hand = [oc]
        atk = Card(RECS[cid('Red Energy Blast')])      # 4 life cards
        self.assertFalse(b.defend(a, atk))             # not a stop
        self.assertIn('prevent_once', b.cb)
        before = len(b.deck)
        a.stage = 10
        a.hand.append(atk)
        a.attack(b, card=atk)
        self.assertEqual(before - len(b.deck), 1)      # 4 life cards - 3 prevented

    def test_visiting_the_past_fetches_a_cell_jr_ally_first(self):
        g, a, b = cj_game()
        a.discard = [ally('Escaping'), Card(RECS[cid('Blue Slash')])]
        B.CARD_EXTRA['Visiting the Past']['use'](a, b, None)
        self.assertEqual([x.name for x in a.hand], ['Cell Jr.'])

    def test_black_perceptive_power_destroys_one_card_of_each_deck(self):
        g, a, b = cj_game('Black Perceptive Mastery')
        mine, theirs = len(a.deck), len(b.deck)
        self.assertTrue(B.mastery_behavior('Black Perceptive Mastery').power(a, b))
        self.assertEqual((mine - len(a.deck), theirs - len(b.deck)), (1, 1))
        self.assertTrue(a.anger == 1 or a.stage == 9)                  # 5 + 4 stages if a Physical/Energy Combat card was destroyed, else 1 anger

    def test_surround_swarm_and_arrest_cards_work_together(self):
        g, a, b = cj_game()
        a.deck = [ally('Trapped'), ally('Escaping'), ally('Unrelenting')] + a.deck
        sur = Card(RECS[cid("Cell Jr.'s Surround")])
        B.CARD_EXTRA["Cell Jr.'s Surround"]['use'](a, b, sur)
        self.assertEqual(sorted(x.rec['subtitle'] for x in a.allies), ['Escaping', 'Trapped'])
        self.assertIs(sur.keep, True)
        before = len(b.deck)
        B.CARD_EXTRA["Cell Jr.'s Swarm"]['hit'](a, b, None, 1)        # banishes 2 Allies: destroy 2 (+1 Trapped) + Escaping's own 1
        self.assertEqual(a.allies, [])
        self.assertGreaterEqual(before - len(b.deck), 3)


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
