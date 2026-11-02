"""Card-, MP- and Mastery-specific behaviour for the simulator, plus the simple AI that picks actions.

Everything here is hand-written from the card text in cards.json. To add a card: put a function in CARD_EXTRA (or a
Behavior in CARD_PASSIVE for Drills/Dragon Balls that stay in play), then run `python -m sim coverage "<deck code>"`.
MP levels and Masteries are Behavior subclasses registered with @mp(...) / @mastery(...).
"""
import re
from .cardmodel import synthetic

STYLES = ('Black', 'Blue', 'Namekian', 'Orange', 'Red', 'Saiyan')


class Behavior:
    """Hooks the engine calls. All defaults do nothing. `p` is the player the behavior belongs to."""
    def on_game_start(self, p): pass
    def anger_modify(self, p, n, in_combat): return n
    def anger_needed(self, p): return None
    def on_anger_raised(self, p): pass
    def on_crit_effect(self, p): pass
    def on_crit_damage(self, p, opp): pass
    def on_advance(self, p): pass
    def on_rejuvenate(self, p): pass
    def on_shuffle_in(self, p): pass
    def on_gain_stages(self, p, n): pass
    def on_card_discarded(self, p): pass
    def on_play(self, p, opp, card): pass
    def on_drill_played(self, p, opp, card): pass
    def on_stopped(self, p, opp, card): pass
    def on_stop_made(self, p, opp, card): pass
    def stage_bonus(self, p, card, opp): return 0
    def life_bonus(self, p, card, opp): return 0
    def incoming_life(self, p, card, atk): return 0
    def incoming_stage(self, p, card, atk): return 0
    def crit_threshold(self, p): return None
    def own_crit_threshold(self, p): return None     # my attacks count as critical from this many life cards
    def adv_anger_delta(self, p): return 0            # change to the anger I need to advance a level (Levels 1-3)
    def opp_adv_anger_min(self, p): return None       # anger my opponent needs to advance a level (Levels 1-3)
    def protect_balls(self, p): return False
    def pur_bonus(self, p): return 0
    def can_mppv(self, p): return True
    def keep_drills(self, p, old_level): return False
    def unstoppable(self, p, card): return False
    def unprevented(self, p, card, opp): return False
    def stage_scale(self, p, card, opp): return 1
    def destroy_amount(self, p, n): return n
    def after_destroy(self, p, got): pass
    def entering_combat(self, p, opp, defender): pass
    def end_of_combat(self, p, opp): pass
    def on_ball_entered(self, p): pass
    def has_power(self, p): return False
    def power(self, p, opp): return False
    def defend_power(self, p, atk, card, kind): return False
    def after_hit(self, p, opp, card, removed): pass


MP_BEH, MASTERY_BEH, CARD_PASSIVE = {}, {}, {}
CARD_EXTRA, CARD_LEAVE_DECK, CARD_DISCARD_TRIGGER, CARD_VALUE = {}, {}, {}, {}


def mp(name, sub):
    def deco(cls):
        MP_BEH[(name, sub)] = cls()
        return cls
    return deco


def mastery(name):
    def deco(cls):
        MASTERY_BEH[name] = cls()
        return cls
    return deco


def passive(*names):
    def deco(cls):
        for n in names:
            CARD_PASSIVE[n] = cls()
        return cls
    return deco


def mp_behavior(name, sub): return MP_BEH.get((name, sub))
def mastery_behavior(name): return MASTERY_BEH.get(name)


def behaviors_of_level(p, level):
    out = [MP_BEH.get((p.mp_name, p.levels[level - 1].name)), MASTERY_BEH.get(p.mastery)]
    return [b for b in out if b]


def style_of(mp_name, mastery_name):
    first = (mastery_name or '').split(' ')[0]
    return first if first in STYLES else None


def once(p, key):
    """True the first time per combat for this key."""
    if key in p.cb['used']:
        return False
    p.cb['used'].add(key)
    return True


def once_turn(p, key):
    if key in p.tf:
        return False
    p.tf[key] = True
    return True


def find_in(zone, pred):
    for x in zone:
        if pred(x):
            return x
    return None


def fetch_from_deck(p, pred, to='hand'):
    c = find_in(p.deck, pred)
    if c is None:
        return None
    p.deck.remove(c)
    p.rng.shuffle(p.deck)
    if to == 'hand':
        p.hand.append(c)
    elif to == 'drill':
        p.drills.append(c)
    elif to == 'ball':
        p.balls.append(c)
        for b in p.behaviors():
            b.on_ball_entered(p)
        p.check_dbv()
    return c


# =================================================================================================================
# Masteries
# =================================================================================================================
@mastery('Red Enraged Mastery')
class RedEnraged(Behavior):
    def on_crit_effect(self, p): p.raise_anger(1)

    def on_advance(self, p):
        p.draw(1)
        if p.hand:
            p.hand.sort(key=p.value)
            p.discard.append(p.hand.pop(0))


@mastery('Namekian Knowledge Mastery')
class NamekianKnowledge(Behavior):
    """Rejuvenate effects during combat and effects that shuffle cards into your Life Deck (shuffle_into_deck) raise anger 1;
    a Namek Dragon Ball entering play destroys the opponent's top card; Dragon Balls cannot be captured."""
    def on_rejuvenate(self, p): p.raise_anger(1)
    def on_shuffle_in(self, p): p.raise_anger(1)     # "shuffles cards into your Life Deck", via shuffle_into_deck()

    def on_ball_entered(self, p):
        if p.balls and p.balls[-1].name.startswith('Namek ') and p.opp is not None:
            p.opp.mill(1, 'destroy')

    def protect_balls(self, p): return True


@mastery('Black Devious Mastery')
class BlackDevious(Behavior):
    def stage_bonus(self, p, card, opp): return 1
    def life_bonus(self, p, card, opp): return 1
    def has_power(self, p): return len(p.hand) >= 2

    def power(self, p, opp):
        if len(p.hand) >= 2 and once_turn(p, 'devious'):
            p.hand.sort(key=p.value)
            h = p.hand.pop(0)
            p.discard.append(h)
            p.note_discard(h)
            if h.style == 'Black':
                opp.forced_discard()
            return True
        return False


@mastery('Orange Retribution Mastery')
class OrangeRetribution(Behavior):
    def on_game_start(self, p):
        fetch_from_deck(p, lambda c: c.ctype == 'Drill' and c.style == 'Orange' and '[Continuous]' not in c.text, 'drill')

    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'retribution'):
            p.cb['next_free'] = True
            p.raise_anger(2)
            if p.cb['changed']:
                fetch_from_deck(p, lambda c: c.ctype == 'Drill' and c.style == 'Orange', 'drill')
            return True
        return False


@mastery('Blue Protective Mastery')
class BlueProtective(Behavior):
    """Opponent needs 6 anger to advance a level (not MPPV on Level 4). Defense POWER: discard a Physical Combat card to stop an
    energy attack or an Energy Combat card to stop a physical attack; if the discarded card was Blue, lower the opponent's anger 1."""
    def opp_adv_anger_min(self, p): return 6

    def defend_power(self, p, atk, card, kind):
        if not ((card.at or 0) + card.stage_flat >= 2 or card.life >= 2 or card.life_at):
            return False
        want = 'Physical Combat' if kind == 'e' else 'Energy Combat'
        cands = [x for x in p.hand if x.ctype == want and not x.endurance]
        if not cands or not once_turn(p, 'blueprot'):
            return False
        cands.sort(key=lambda z: (z.style != 'Blue', p.value(z)))
        x = cands[0]
        p.hand.remove(x)
        p.discard.append(x)
        p.note_discard(x)
        if x.style == 'Blue':
            atk.lower_anger(1)
        return True


@mastery('Black Conflict Mastery')
class BlackConflict(Behavior):
    """Attacks that deal at least 4 life cards count as critical damage. POWER: discard a card; if Styled, raise anger 1 (chosen over +6 stages)."""
    def own_crit_threshold(self, p): return 4
    def has_power(self, p): return len(p.hand) >= 2

    def power(self, p, opp):
        if len(p.hand) >= 2 and once_turn(p, 'conflict'):
            p.hand.sort(key=p.value)
            h = p.hand.pop(0)
            p.discard.append(h)
            p.note_discard(h)
            if h.style == 'Black':
                p.raise_anger(1)
            return True
        return False


@mastery('Saiyan Rampaging Mastery')
class SaiyanRampaging(Behavior):
    """1 less anger to advance (min 4). Styled attacks gain 'HIT: you may raise your anger 1 level'. (Its Power is not modelled.)"""
    def adv_anger_delta(self, p): return -1

    def after_hit(self, p, opp, card, removed):
        if card.style and card.style == p.styled() and card.card_id.split(':')[0] != 'synthetic':
            p.raise_anger(1)


@mastery('Saiyan Dynamic Mastery')
class SaiyanDynamic(Behavior):
    """Begin on Level 2 (5 stages assumed). 6 anger to advance. Styled attacks without 'anger' printed gain 'Raise your anger 1 level'."""
    def on_game_start(self, p):
        p.level = 2

    def adv_anger_delta(self, p): return 1

    def on_play(self, p, opp, card):
        if card.style and card.style == p.styled() and 'anger' not in card.text.lower() and card.card_id.split(':')[0] != 'synthetic':
            p.raise_anger(1)


@mastery('Red Ascension Mastery')
class RedAscension(Behavior):
    """Critical effect: gain 2 stages. End of each combat: raise anger 1. POWER: banish top card of Life Deck to raise anger 1; if Red, opponent skips next action."""
    def on_crit_effect(self, p): p.gain_stages(2)
    def end_of_combat(self, p, opp): p.raise_anger(1)
    def has_power(self, p): return len(p.deck) > 20

    def power(self, p, opp):
        if p.deck and once_turn(p, 'ascension'):
            c = p.deck.pop(0)
            p.banished.append(c)
            p.raise_anger(1)
            if c.style == 'Red':
                opp.skip += 1
            return True
        return False


# =================================================================================================================
# Trunks
# =================================================================================================================
SWORDMASTER = synthetic('Swordmaster', 'POWER: [Attack] Physical attack. DAMAGE: 8 stages.')


@mp('Trunks', 'Dashing')
class TrunksDashing(Behavior):
    def anger_modify(self, p, n, in_combat): return n * 2 if in_combat else n


@mp('Trunks', 'Protective')
class TrunksProtective(Behavior):
    def keep_drills(self, p, old_level): return old_level == 1

    def entering_combat(self, p, opp, defender):
        if not defender and not any(d.style == 'Freestyle' for d in p.drills):
            if fetch_from_deck(p, lambda c: c.ctype == 'Drill' and c.style == 'Freestyle', 'drill'):
                p.cb['searched'] = True

    def on_play(self, p, opp, card):
        if card.sword:
            p.rejuv(1)


@mp('Trunks', 'Frenzied')
class TrunksFrenzied(Behavior):
    def on_play(self, p, opp, card):
        if card.named and card.card_id.split(':')[0] != 'synthetic':
            p.crit_effect()

    def defend_power(self, p, atk, card, kind):
        if kind == 'p' and once_turn(p, 'frenzied'):
            sw = find_in(p.banished, lambda c: c.sword)
            if sw:
                p.banished.remove(sw)
                p.deck.append(sw)
                p.raise_anger(1)
            return True
        return False


@mp('Trunks', 'Swordmaster')
class TrunksSwordmaster(Behavior):
    def has_power(self, p): return True

    def power(self, p, opp):
        if not p.cb['attacked_hand'] and once_turn(p, 'swordmaster'):
            return p.attack(opp, power=SWORDMASTER)
        return False


@mp('Trunks', 'Defiant')
class TrunksDefiant(Behavior):
    def has_power(self, p): return True

    def power(self, p, opp):
        cand = [x for x in p.discard if x.is_atk and (x.style == p.styled() or x.sword)]
        if p.hand and cand and once_turn(p, 'defiant'):
            h = sorted(p.hand, key=p.value)[0]
            p.hand.remove(h)
            p.deck.append(h)
            x = max(cand, key=p.value)
            p.discard.remove(x)
            p.hand.append(x)
            opp.skip += 1
            return True
        return False


@mp('Trunks', 'Energy Charged')
class TrunksEnergyCharged(Behavior):
    def entering_combat(self, p, opp, defender): p.draw(1)


@mp('Trunks', 'Overpowering')
class TrunksOverpowering(Behavior):
    def stage_bonus(self, p, card, opp): return 5


@mp('Trunks', 'Bold')
class TrunksBold(Behavior):
    def stage_bonus(self, p, card, opp): return 2


@mp('Trunks', 'Overwhelming')
class TrunksOverwhelming(Behavior):
    def unstoppable(self, p, card): return card.sword

    def on_play(self, p, opp, card):
        if card.sword:
            p.raise_anger(1)

    def has_power(self, p): return p.anger >= 3

    def power(self, p, opp):
        if p.anger >= 3 and once_turn(p, 'overwhelming'):
            p.raise_anger(2)
            return True
        return False


# =================================================================================================================
# Piccolo (Premiere levels, Composed from Evolution)
# =================================================================================================================
STOIC = synthetic('Stoic', 'POWER: [Attack] Energy attack costing 1 stage. DAMAGE: 3 life cards. Rejuvenate 1.')
FUSED = synthetic('Fused', 'POWER: [Attack] Energy attack costing 2 stages. DAMAGE: 7 life cards.')


@mp('Piccolo', 'Stoic')
class PiccoloStoic(Behavior):
    def has_power(self, p): return p.stage >= 1

    def power(self, p, opp):
        if p.stage >= 1 and once_turn(p, 'stoic'):
            return p.attack(opp, power=STOIC)
        return False


@mp('Piccolo', 'Composed')
class PiccoloComposed(Behavior):
    def on_gain_stages(self, p, n): p.raise_anger(1)
    def on_rejuvenate(self, p): p.raise_anger(1)


@mp('Piccolo', 'Combat Stance')
class PiccoloCombatStance(Behavior):
    def has_power(self, p): return bool(p.hand)

    def power(self, p, opp):
        if p.hand and once_turn(p, 'stance'):
            h = p.forced_discard()
            if h is not None:
                p.rejuv(2)
                opp.mill(2)
                if h.style == p.styled():
                    p.draw(1)
                    p.crit_effect()
            return True
        return False


@mp('Piccolo', 'Unleashed')
class PiccoloUnleashed(Behavior):
    def life_bonus(self, p, card, opp): return 2

    def on_crit_damage(self, p, opp):
        if once(p, 'unleashed'):
            fetch_from_deck(p, lambda c: c.ctype == 'Dragon Ball', 'ball')


@mp('Piccolo', 'Fused')
class PiccoloFused(Behavior):
    def crit_threshold(self, p): return 7
    def has_power(self, p): return p.stage >= 2

    def power(self, p, opp):
        if p.stage >= 2 and once_turn(p, 'fused'):
            return p.attack(opp, power=FUSED)
        return False

    def after_hit(self, p, opp, card, removed):
        if card.name == 'Fused':
            p.rejuv(len(p.balls) + len(opp.balls))



# =================================================================================================================
# Nail (Set 2 levels)
# =================================================================================================================
NAIL_L1 = synthetic('Watchful', 'POWER: [Attack] Physical attack. DAMAGE: AT +2 life cards.')
NAIL_L4 = synthetic('Combat Ready', 'POWER: [Attack] Physical attack. DAMAGE: 7 stages.')


@mp('Nail', 'Watchful')
class NailL1(Behavior):
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'nail1'):
            return p.attack(opp, power=NAIL_L1)
        return False

    def on_stopped(self, p, opp, card):
        if card.name == 'Watchful':
            opp.mill(1)


@mp('Nail', 'Protector')
class NailL2(Behavior):
    def on_stopped(self, p, opp, card): opp.mill(2)

    def after_hit(self, p, opp, card, removed):
        if opp.endure_count:
            opp.mill(opp.endure_count, 'banish')


@mp('Nail', 'Unflinching')
class NailL3(Behavior):
    def stage_bonus(self, p, card, opp): return 3
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'nail3'):
            ball = find_in(p.hand, lambda c: c.ctype == 'Dragon Ball')
            if ball and not any(b.name == ball.name for b in p.balls):
                p.hand.remove(ball)
                p.balls.append(ball)
                ex = CARD_EXTRA.get(ball.name, {})
                if ex.get('immediate'):
                    ex['immediate'](p, opp, ball)
                p.check_dbv()
            p.raise_anger(1)
            return True
        return False


@mp('Nail', 'Combat Ready')
class NailL4(Behavior):
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'nail4'):
            return p.attack(opp, power=NAIL_L4)
        return False

    def after_hit(self, p, opp, card, removed):
        if card.name == 'Combat Ready':
            for ball in p.balls + opp.balls:
                ex = CARD_EXTRA.get(ball.name, {})
                if ex.get('immediate'):
                    ex['immediate'](p, opp, ball)
                    break


# =================================================================================================================
# Nappa (Set 2 levels). His deck drains the opponent's stages ("loses N stages"); the parser handles the unconditional ones.
# =================================================================================================================
NAPPA_L1 = synthetic('Rested', 'POWER: [Attack] Physical attack. DAMAGE: 3 stages.')            # also destroys an opponent's Ally (Allies are not simulated)
NAPPA_L3 = synthetic('Overconfident', 'POWER: [Attack] Physical attack. DAMAGE: 7 stages.')


class _NappaAttack(Behavior):
    card, key = None, ''
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, self.key):
            return p.attack(opp, power=self.card)
        return False


@mp('Nappa', 'Rested')
class NappaL1(_NappaAttack):
    card, key = NAPPA_L1, 'nappa1'


@mp('Nappa', 'Smirking')
class NappaL2(Behavior):
    def on_play(self, p, opp, card):
        # "whenever you perform an attack": all their personalities lose 2 stages if you changed levels this combat, otherwise their MP loses 1
        opp.lose_stages(2 if p.cb['changed'] else 1)


@mp('Nappa', 'Overconfident')
class NappaL3(_NappaAttack):
    card, key = NAPPA_L3, 'nappa3'

    def after_hit(self, p, opp, card, removed):
        if card.name == 'Overconfident' and opp.drills:        # HIT: banish a Drill or Ally
            opp.banished.append(opp.drills.pop())


@mp('Nappa', 'Enraged')
class NappaL4(Behavior):
    def stage_bonus(self, p, card, opp): return 4
    def unprevented(self, p, card, opp): return opp.power() == 0       # damage cannot be prevented while the opponent's MP is at power level 0

# =================================================================================================================
# Dr. Wheelo
# =================================================================================================================
@mp('Dr. Wheelo', 'Big Brain')
class WheeloL1(Behavior):
    def has_power(self, p): return p.anger <= 3

    def power(self, p, opp):
        if p.anger <= 3 and p.deck and once_turn(p, 'bigbrain'):
            p.lose_card(p.deck.pop(0), 'destroy')
            p.destroy_opp(2, noamp=True)
            p.anger = 3
            return True
        return False


@mp('Dr. Wheelo', 'Scheming')
class WheeloL2(Behavior):
    def life_bonus(self, p, card, opp): return 2
    def on_stop_made(self, p, opp, card): p.destroy_opp(1, noamp=True)


@mp('Dr. Wheelo', 'Confined')
class WheeloL3(Behavior):
    def destroy_amount(self, p, n): return n + 1

    def after_hit(self, p, opp, card, removed):
        if once(p, 'confined'):
            p.destroy_opp(2)
            p.rejuv(2)


@mp('Dr. Wheelo', 'Robotic')
class WheeloL4(Behavior):
    def destroy_amount(self, p, n): return n + 2
    def after_destroy(self, p, got): p.rejuv(2)


# =================================================================================================================
# Garlic Jr., Lord Slug, Krillin
# =================================================================================================================
@mp('Garlic Jr.', 'Commanding')
class GarlicL1(Behavior):
    def anger_needed(self, p): return 3
    def incoming_life(self, p, card, atk): return -1
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'garlic'):
            p.raise_anger(1)
            return True
        return False


@mp('Garlic Jr.', 'Crazed')
class GarlicL2(Behavior):
    def incoming_life(self, p, card, atk): return -2


@mp('Garlic Jr.', 'Observant')
class GarlicL3(Behavior):
    def incoming_life(self, p, card, atk): return -2
    def incoming_stage(self, p, card, atk): return -2

    def on_anger_raised(self, p):
        o = p.opp
        if o.balls and not any(b.protect_balls(o) for b in o.behaviors()):
            p.balls.append(o.balls.pop())
            p.check_dbv()


@mp('Garlic Jr.', 'Transformed')
class GarlicL4(Behavior):
    def incoming_life(self, p, card, atk): return 3
    def protect_balls(self, p): return True


SLUG_ATK = synthetic('Successful', 'POWER: [Attack] Physical attack. DAMAGE: AT +3 stages. HIT: Rejuvenate 2.')


@mp('Lord Slug', 'Aged')
class SlugL1(Behavior):
    def on_ball_entered(self, p): p.raise_anger(1, in_combat=False)

    def end_of_combat(self, p, opp):
        if not p.balls:
            fetch_from_deck(p, lambda c: c.ctype == 'Dragon Ball', 'ball')


@mp('Lord Slug', 'Successful')
class SlugL2(Behavior):
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'slug2'):
            return p.attack(opp, power=SLUG_ATK)
        return False


@mp('Lord Slug', 'Renewed')
class SlugL3(Behavior):
    def stage_bonus(self, p, card, opp): return 2


@mp('Lord Slug', 'Huge')
class SlugL4(Behavior):
    def can_mppv(self, p): return False

    def entering_combat(self, p, opp, defender):
        if not defender and once_turn(p, 'slug4'):
            fetch_from_deck(p, lambda c: c.ctype == 'Dragon Ball', 'ball')


KR_L1 = synthetic('Ready', 'POWER: [Attack] Energy attack costing 2 stages. DAMAGE: 4 life cards.')
KR_L2 = synthetic('Energetic', 'POWER: [Attack] Energy attack costing 3 stages. DAMAGE: 4 life cards.')
KR_L3 = synthetic('Ready For Battle', 'POWER: [Attack] Energy attack costing 2 stages. DAMAGE: 9 - X life cards.')


class _KrillinAttack(Behavior):
    card, key = None, ''
    def has_power(self, p): return p.stage >= self.card.cost

    def power(self, p, opp):
        if p.stage >= self.card.cost and once_turn(p, self.key):
            return p.attack(opp, power=self.card)
        return False


@mp('Krillin', 'Ready')
class KrillinL1(_KrillinAttack):
    card, key = KR_L1, 'kr1'

    def power(self, p, opp):
        if p.stage >= self.card.cost and once_turn(p, self.key):
            p.cb['armed_discard'] = True
            return p.attack(opp, power=self.card)
        return False

    def on_card_discarded(self, p):
        if p.cb['armed_discard']:
            p.cb['armed_discard'] = False
            p.crit_effect()
            p.raise_anger(2)


@mp('Krillin', 'Energetic')
class KrillinL2(_KrillinAttack):
    card, key = KR_L2, 'kr2'

    def after_hit(self, p, opp, card, removed):
        if card.name == 'Energetic':
            opp.forced_discard()


@mp('Krillin', 'Ready For Battle')
class KrillinL3(_KrillinAttack):
    card, key = KR_L3, 'kr3'


@mp('Krillin', 'Enraged')
class KrillinL4(Behavior):
    def unstoppable(self, p, card):
        if card.is_atk and card.style == p.styled() and 'kr4_first' not in p.tf:
            p.tf['kr4_first'] = True
            return True
        return False


# =================================================================================================================
# Vegeta (Hero): Evolution levels (Styled) and Awakening levels (non-Styled). Added for the Hero Vegeta deck comparison.
# =================================================================================================================
def nonstyled(p, c):
    """A non-Styled attack: any attack that is not of the player's Mastery style (Freestyle cards, Mastery/MP Powers)."""
    return bool(c.is_atk) and c.style != p.styled()


def modifiable(c):
    """False for an attack whose text says its damage cannot be modified (True Power)."""
    return 'cannot have its damage modified' not in c.text and 'damage cannot be modified' not in c.text


VG_EXPERIENCED = synthetic('Experienced', 'POWER: [Attack] Energy attack costing 1 stage. DAMAGE: 1 life card.')
VG_ON_THE_MOVE = synthetic('On the Move', 'POWER: [Attack] Physical attack. DAMAGE: 4 life cards.')


class _VegetaPower(Behavior):
    card, key = None, ''
    def has_power(self, p): return p.stage >= self.card.cost

    def power(self, p, opp):
        if p.stage >= self.card.cost and once_turn(p, self.key):
            return p.attack(opp, power=self.card)
        return False


@mp('Vegeta', 'Experienced')
class VegetaAW1(_VegetaPower):
    """L1: non-Styled attacks +2 life cards (and nothing else may modify them - not modelled). Power: 1-stage energy attack, 1 life card."""
    card, key = VG_EXPERIENCED, 'vg1'
    def life_bonus(self, p, card, opp): return 2 if nonstyled(p, card) and modifiable(card) else 0


@mp('Vegeta', 'Imposing')
class VegetaAW2(Behavior):
    """L2: non-Styled attacks +1 life card, damage cannot be prevented. Power: raise anger 1, gain 3 stages."""
    def life_bonus(self, p, card, opp): return 1 if nonstyled(p, card) and modifiable(card) else 0
    def unprevented(self, p, card, opp): return nonstyled(p, card)
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'vg2'):
            p.raise_anger(1)
            p.gain_stages(3)
            return True
        return False


@mp('Vegeta', 'Energized')
class VegetaAW3(Behavior):
    """L3: non-Styled attacks +3 life cards; the first stopped non-Styled attack each combat is used a second time (pays its cost again)."""
    def life_bonus(self, p, card, opp): return 3 if nonstyled(p, card) and modifiable(card) else 0

    def on_stopped(self, p, opp, card):
        if nonstyled(p, card) and card.card_id.split(':')[0] != 'synthetic' and once(p, 'vg3_second') and p.stage >= card.cost:
            p.attack(opp, power=card)


@mp('Vegeta', 'Pinnacle of Power')
class VegetaAW4(Behavior):
    """L4: non-Styled attacks cannot be stopped and deal +3 life cards."""
    def life_bonus(self, p, card, opp): return 3 if nonstyled(p, card) and modifiable(card) else 0
    def unstoppable(self, p, card): return nonstyled(p, card)


@mp('Vegeta', 'Calculating')
@mp('Vegeta', 'Super Saiyan')
class VegetaEvoPassive(Behavior):
    """Evolution L1/L3: converts Styled life-card damage into stage damage (or back); not modelled (a choice, not extra damage)."""


@mp('Vegeta', 'On the Move')
class VegetaEvo2(_VegetaPower):
    """L2: Power: physical attack, 4 life cards (no cost)."""
    card, key = VG_ON_THE_MOVE, 'vg2e'


@mp('Vegeta', 'Elite')
class VegetaEvo4(Behavior):
    """L4: the first Styled physical attack each combat cannot be stopped. (The energy HIT search is not modelled.)"""
    def unstoppable(self, p, card):
        if card.is_atk and card.phys and card.style == p.styled() and 'vg4_first' not in p.tf:
            p.tf['vg4_first'] = True
            return True
        return False


def life_adjust(p, opp, c):
    """Cross-card adjustments applied to life damage: Krillin's 9 - X, Earth Dragon Ball 1 (all attacks +1)."""
    adj = 0
    if c.name == 'Ready For Battle':
        adj -= len(opp.hand)
    if (c.life or c.life_at) and any(b.name == 'Earth Dragon Ball 1' for b in p.balls + opp.balls):
        adj += 1
    return adj


# =================================================================================================================
# Drills and Dragon Balls that stay in play
# =================================================================================================================
@passive('Orange Hoping Drill')
class HopingDrill(Behavior):
    def stage_bonus(self, p, card, opp): return 1

    def on_play(self, p, opp, card):
        if card.sword:
            opp.mill(1)


@passive('Orange Intimidating Drill')
class IntimidatingDrill(Behavior):
    def stage_bonus(self, p, card, opp): return 1


@passive('Orange Hiding Drill')
class HidingDrill(Behavior):
    def incoming_life(self, p, card, atk): return -2


@passive('Orange Aura Drill')
class AuraDrill(Behavior):
    def life_bonus(self, p, card, opp): return 2 if card.energy else 0


@passive('Orange Captivity Drill')
class CaptivityDrill(Behavior):
    def after_hit(self, p, opp, card, removed):
        if card.energy:
            p.raise_anger(1)
            p.gain_stages(3)


@passive('Orange Burning Aura Drill')
class BurningAuraDrill(Behavior):
    def defend_power(self, p, atk, card, kind): return kind == 'p' and once_turn(p, 'burning_aura')


@passive('Orange Steady Drill')
class SteadyDrill(Behavior):
    def defend_power(self, p, atk, card, kind): return kind == 'e' and once_turn(p, 'steady')


@passive('Aggressive Sword Drill')
class AggressiveSwordDrill(Behavior):
    def entering_combat(self, p, opp, defender):
        if not p.cb['searched'] and 'searched' not in p.tf:
            if fetch_from_deck(p, lambda c: c.sword):
                p.tf['searched'] = True


@passive('Orange Devouring Drill')
class DevouringDrill(Behavior):
    def on_drill_played(self, p, opp, card):
        dv = find_in(p.drills, lambda c: c.name == 'Orange Devouring Drill')
        if dv and card.name != 'Orange Devouring Drill':
            p.drills.remove(dv)
            p.banished.append(dv)
            p.change_level(+1)
            p.log(f'  {p.label}: Devouring Drill -> advance')


@passive('Namek Dragon Ball 1')
class Namek1(Behavior):
    def life_bonus(self, p, card, opp): return 1
    def protect_balls(self, p): return len(p.balls) > 1


@passive('Namek Dragon Ball 6')
class Namek6(Behavior):
    def pur_bonus(self, p): return 3
    def incoming_stage(self, p, card, atk): return -2


# =================================================================================================================
# Card effects beyond the parser (CARD_EXTRA entries: immediate / hit / use / defend / on_damaged / enters)
# =================================================================================================================
def _x(name, **kw): CARD_EXTRA.setdefault(name, {}).update(kw)


def _namek3(p, o, c):
    p.draw(3)
    for _ in range(2):
        nb = [x for x in p.hand if x.ctype != 'Dragon Ball']
        if nb:
            h = sorted(nb, key=p.value)[0]
            p.hand.remove(h)
            p.deck.append(h)
    p.raise_anger(1, in_combat=False)


def _namek5(p, o, c):
    p.gain_stages(5)
    p.raise_anger(1, in_combat=False)
    p.draw(1)
    p.rejuv(1, in_combat=False)


_x('Namek Dragon Ball 3', immediate=_namek3)
_x('Namek Dragon Ball 5', immediate=_namek5)
_x('Namek Dragon Ball 7', immediate=lambda p, o, c: p.destroy_opp(3, noamp=True))
_x('Earth Dragon Ball 2', immediate=lambda p, o, c: o.change_level(-1) if o.level > 1 else None)
_x('Earth Dragon Ball 3', immediate=lambda p, o, c: p.raise_anger(1, in_combat=False))
_x('Earth Dragon Ball 4', immediate=lambda p, o, c: p.destroy_opp(2, noamp=True))
_x('Earth Dragon Ball 5', immediate=lambda p, o, c: p.gain_stages(3))

_x('Red Shoulder Grab', immediate=lambda p, o, c: p.cb.update(crit_all=True))
_x('Red Clock', immediate=lambda p, o, c: p.crit_effect() if p.cb.get('sword_played') else None)
_x('Black Chomp', immediate=lambda p, o, c: p.cb.update(destroy_bonus=p.cb['destroy_bonus'] + 1))
_x('Black Choke', hit=lambda p, o, c, r: p.cb.update(next_destroy_bonus=p.cb['next_destroy_bonus'] + 2))
_x('Black Drain', immediate=lambda p, o, c: p.destroy_opp(1))
_x('Dashing Sword Attack', immediate=lambda p, o, c: setattr(o, 'stage', max(0, o.stage - 2)),
   hit=lambda p, o, c, r: _fetch_discard(p, lambda x: x.sword or x.named))
_x('Orange Truck Lift', hit=lambda p, o, c, r: _drill_from_discard(p))
_x('Orange Collision', hit=lambda p, o, c, r: _drill_from_discard(p))
_x('Orange Sword Chop', hit=lambda p, o, c, r: fetch_from_deck(p, lambda x: x.ctype == 'Event'))
_x('Black Barrage', hit=lambda p, o, c, r: o.forced_discard())
_x("Krillin's Solar Flare", hit=lambda p, o, c, r: setattr(o, 'skip', o.skip + 1))


def _fetch_discard(p, pred):
    x = find_in(reversed(p.discard), pred)
    if x:
        p.discard.remove(x)
        p.hand.append(x)


def _drill_from_discard(p):
    x = find_in(reversed(p.discard), lambda c: c.ctype == 'Drill')
    if x:
        p.discard.remove(x)
        p.drills.append(x)


def _overhead(p, o, c, r):
    if p.hand:
        p.hand.sort(key=p.value)
        h = p.hand.pop(0)
        p.discard.append(h)
        p.note_discard(h)
        p.crit_effect()


_x('Black Overhead Burst', hit=_overhead)


# ---- Events / Setups: `use` runs when the AI plays them; `can_use` gates them ------------------------------------
def _confinement(p, o, c):
    for flag in ('discarded', 'gained', 'raised'):
        if p.cb[flag]:
            p.destroy_opp(1)


def _revival(p, o, c):
    p.gain_stages(2)
    o.cb['noevents'] = True
    p.deck.append(c)
    p.rng.shuffle(p.deck)
    c.keep = True


def _confrontation(p, o, c):
    if o.hand:
        x = max(o.hand, key=o.value)
        o.hand.remove(x)
        o.deck.append(x)
        o.rng.shuffle(o.deck)


_x("Dr. Wheelo's History", use=lambda p, o, c: p.destroy_opp(3))
_x('Black Confinement', use=_confinement, can_use=lambda p, o, c: any(p.cb[f] for f in ('discarded', 'gained', 'raised')))
_x('Black Invitation', use=lambda p, o, c: p.destroy_opp(2))
_x('Black Taunt', use=lambda p, o, c: p.destroy_opp(o.anger + 1), can_use=lambda p, o, c: o.anger >= 1)
_x('Black Discovery', use=lambda p, o, c: p.destroy_opp(2))
_x("Dr. Wheelo's Revival", use=_revival)
_x('Black Haunting', use=lambda p, o, c: (p.rejuv(2), o.cb.update(nonstyled_lock=True)),
   can_use=lambda p, o, c: p.cb['destroyed_nonstyled'])
_x('Stare Down', use=lambda p, o, c: o.forced_discard())
_x('Confrontation', use=_confrontation)
_x('Orange Destruction', use=lambda p, o, c: o.mill(1 + len(p.drills)))
_x('Red Destiny', use=lambda p, o, c: p.cb.update(reduce_life=p.cb['reduce_life'] + 2, reduce_stage=p.cb['reduce_stage'] + 2))
_x('Red Blazing Aura', use=lambda p, o, c: p.cb.update(reduce_life=p.cb['reduce_life'] + 3, reduce_stage=p.cb['reduce_stage'] + 3))
_x('Red Burning Rage', use=lambda p, o, c: p.cb.update(burning=True, noend=True))
_x('Red Takeover', use=lambda p, o, c: p.crit_effect())
_x('Visiting the Past', use=lambda p, o, c: _fetch_discard(p, lambda x: True), can_use=lambda p, o, c: bool(p.discard))
_x("Time Is A Warrior's Tool", defend=lambda p, atk, x, c: atk.cb.update(stopall=True))
_x('Black Duck', defend=lambda p, atk, x, c: (p.lose_card(p.deck.pop(0), 'destroy') if p.deck else None,
                                              p.destroy_opp(2) if p.rng.random() < 3 / max(3, len(p.deck)) else None))
_x('Black Running Guard', defend=lambda p, atk, x, c: p.destroy_opp(2) if c.style != atk.styled() else None)
_x('Black Flinch', defend=lambda p, atk, x, c: p.cb.update(next_life=p.cb['next_life'] + 4))
_x('Black Upward Dodge', defend=lambda p, atk, x, c: p.cb.update(next_life=p.cb['next_life'] + 4))
_x('Villainous Visage', on_damaged=lambda p, atk, x, removed: (p.hand.remove(x), p.banished.append(x), p.destroy_opp(2 * removed)))

# ---- Saiyan stage-drain cards (Nappa's deck) ---------------------------------------------------------------------
def _attach(p, o, c):
    if not p.attached:            # a second Clench is not stacked (unverified how the real game stacks them)
        p.attached.append(c)
        c.keep = True


class _Clench(Behavior):
    """Saiyan Clench attached: attacks without AT base damage have their power stage damage doubled (only one doubling; order vs +stage modifiers is unverified)."""
    def stage_scale(self, p, card, opp): return 2


CARD_PASSIVE['Saiyan Clench'] = _Clench()
_x('Saiyan Clench', immediate=_attach)
_x('Saiyan Uppercut', base_stage=lambda p, o, c: 7 if p.power() > o.power() else 5)
_x('Saiyan Headbutt', base_stage=lambda p, o, c: 4 + 4 * sum(1 for x in p.discard + p.banished if x.name == 'Saiyan Headbutt'))
_x('Saiyan Charged Fist', immediate=lambda p, o, c: o.lose_stages(3, True) if p.power() > o.power() else None)
_x('Saiyan Focus', defend=lambda p, atk, x, c: atk.lose_stages(4, True) if p.discard and p.discard[0].style == p.styled() else None)
_x('Saiyan Emergence', use=lambda p, o, c: (setattr(c, 'keep', True), p.deck.append(c)) if o.power() == 0 else None)
_x('Saiyan Trap', use=lambda p, o, c: (setattr(c, 'keep', True), p.deck.append(c)))
_x("Nappa's Energized Charge", immediate=lambda p, o, c: p.cb.update(set0_on_change=True))
_x("I'll Dig Your Grave!", immediate=lambda p, o, c: p.cb.update(unprev_all=True))
_x("Nappa's Confidence", use=lambda p, o, c: o.banished.append(o.drills.pop()) if o.power() == 0 and o.drills else None)
_x('Saiyan Overpowering Aura Drill', enters=lambda p, o, c: _fetch_attach(p))
_x('Saiyan Body Blow', immediate=lambda p, o, c: _fetch_attach(p))


def _fetch_attach(p):
    """Search the Life Deck (or discard pile) for Saiyan Clench and place it into play attached."""
    c = find_in(p.deck, lambda x: x.name == 'Saiyan Clench') or find_in(p.discard, lambda x: x.name == 'Saiyan Clench')
    if c is not None and not p.attached:
        (p.deck if c in p.deck else p.discard).remove(c)
        p.attached.append(c)


CARD_VALUE.update({"Dr. Wheelo's History": 6, 'Black Confinement': 5, 'Black Invitation': 4, "Dr. Wheelo's Revival": 3, 'Black Taunt': 4})
NEVER_PLAY = {"Time Is A Warrior's Tool", 'Villainous Energy Sphere', 'Villainous Visage', "Piccolo's Weighted Clothing",
              'Heroic Energy Sphere'}


# ---- Hero Vegeta deck cards (Awakening / Red Ascension shell) ----------------------------------------------------
_SAIYAN_MPS = None


def _is_saiyan(p):
    """PanZ heritage list (mps.json -> panz_heritage.Saiyan); 'If your MP is a Saiyan'."""
    global _SAIYAN_MPS
    if _SAIYAN_MPS is None:
        import json
        from .cardmodel import DB
        _SAIYAN_MPS = {g['name'] for g in json.loads((DB / 'mps.json').read_text(encoding='utf-8'))['mps'] if g['panz_heritage'].get('Saiyan')}
    return p.mp_name in _SAIYAN_MPS


def _kamehameha(p, o, c):
    if _is_saiyan(p):                      # "If your MP is a Saiyan, this attack cannot be stopped and its damage cannot be prevented"
        c.unstoppable = c.unprev = True


def _banish_opp_discard(o, n):
    for _ in range(min(n, len(o.discard))):
        o.banished.append(o.discard.pop())


def _emergency(p, o, c):
    """Red Emergency: with 2+ anger, search the discard pile for 2 Drills, Rejuvenate one (bottom of the Life Deck) and place the other into play."""
    if p.anger >= 2:
        drills = [x for x in p.discard if x.ctype == 'Drill'][-2:]
        if drills:
            p.discard.remove(drills[-1])
            p.drills.append(drills[-1])
            if len(drills) > 1:
                p.discard.remove(drills[0])
                p.deck.append(drills[0])


# Galick Gun: "If you deal critical damage with this attack, you may use two critical effects instead of one" -> one extra effect (threshold fixed at 5 life cards).
_x("Vegeta's Galick Gun", hit=lambda p, o, c, removed: p.crit_effect() if removed >= 5 else None)
_x('Assisted Kamehameha', immediate=_kamehameha)
# True Power: "Use only if you have not performed an attack this combat. This attack cannot have its damage modified." (modifiable() keeps Vegeta's level bonuses off it)
_x('True Power', can_attack=lambda p, o, c: p.cb['attacks'] == 0)
_x('Android Headbutt', immediate=lambda p, o, c: p.raise_anger(1), hit=_overhead)    # "Raise or lower a player's anger 1" (raise own); HIT: discard a card for a critical effect
_x('Devastating Blow', immediate=lambda p, o, c: _banish_opp_discard(o, 3))
_x('Allied Blitz', immediate=lambda p, o, c: setattr(o, 'skip', o.skip + 1))          # only the opponent's next action after this attack; later energy attacks are not modelled
_x('Red Duck', defend=lambda p, atk, x, c: p.rejuv(p.anger))                          # Rejuvenate X, X = your anger
_x('Red Body Block', defend=lambda p, atk, x, c: p.cb.update(next_unprev=True))      # UNVERIFIED approximation: any next attack, not only non-Styled
_x('Enhanced Reflexes', defend=lambda p, atk, x, c: p.banished.append(p.deck.pop(0)) if p.deck else None)   # "Banish the top card of your Life Deck" (the Named-attack clause is not modelled)
_x('Red Flourish', use=lambda p, o, c: p.cb.update(crit_all=True))                    # UNVERIFIED approximation: energy attacks only in the text; the model applies it to every successful attack
_x('Red Emergency', use=_emergency)


@passive('Red Despair Drill')
class DespairDrill(Behavior):
    def life_bonus(self, p, card, opp): return p.anger if modifiable(card) else 0


@passive('Red Intimidation Drill')
class IntimidationDrill(Behavior):
    def on_crit_damage(self, p, opp):
        if once_turn(p, 'intimidation'):
            p.draw(1)


@passive('Red Hunting Drill')
class HuntingDrill(Behavior):
    def on_crit_damage(self, p, opp):
        if once(p, 'hunting'):
            p.destroy_opp(1)


# ---- discarded-by-effect triggers ------------------------------------------------------------------------------
CARD_DISCARD_TRIGGER['Red Sacrifice'] = lambda p, c: (p.raise_anger(2), p.cb.update(next_unprev=True))
CARD_DISCARD_TRIGGER['Red Restraint'] = lambda p, c: (p.raise_anger(1), p.gain_stages(3), p.cb.update(next_life=p.cb['next_life'] + 2))
CARD_DISCARD_TRIGGER["Piccolo's Weighted Clothing"] = lambda p, c: None   # listed so the AI prefers to discard it


def _revival_leaves(p, c):
    if c in p.discard:
        p.discard.remove(c)
    p.banished.append(c)
    p.log(f'    ({p.label} Revival triggers)')
    p.destroy_opp(3)


CARD_LEAVE_DECK["Dr. Wheelo's Revival"] = _revival_leaves


# ---- Nail decks (Red Enraged / Namekian Knowledge): cards whose effects the parser cannot read ------------------------
def shuffle_into_deck(p, cards):
    """Cards go into the owner's Life Deck and it is shuffled: ONE 'shuffle into your Life Deck' effect (Namekian Knowledge triggers once)."""
    cards = [c for c in cards if c is not None]
    if not cards:
        return
    p.deck.extend(cards)
    p.rng.shuffle(p.deck)
    for b in p.behaviors():
        b.on_shuffle_in(p)


def _dashing_attacking_hit(p, o, c, removed):
    c.keep = True                                   # HIT: shuffle this card into your Life Deck (it does not go to the discard pile)
    shuffle_into_deck(p, [c])


def _energy_guard(p, atk, x, c):                    # shuffle the top and bottom cards of your discard pile into your Life Deck
    cards = []
    if p.discard:
        cards.append(p.discard.pop())
    if p.discard:
        cards.append(p.discard.pop(0))
    shuffle_into_deck(p, cards)


def _crushing_slam(p, o, c):                        # shuffle the top 2 cards of your discard pile into your Life Deck
    shuffle_into_deck(p, [p.discard.pop() for _ in range(min(2, len(p.discard)))])


def _find_ball(p, o, c, removed=0):
    fetch_from_deck(p, lambda x: x.ctype == 'Dragon Ball', 'ball')


def _overtime(p, o, c):                             # (Rejuvenate 1 is parsed) destroy X = balls you control, search a Styled Energy Combat card
    p.destroy_opp(len(p.balls))
    fetch_from_deck(p, lambda x: x.ctype == 'Energy Combat' and x.style == p.styled())


# Red
_x('Red Duck', defend=lambda p, atk, x, c: p.rejuv(p.anger) if p.anger else None)               # Rejuvenate X, X = current anger
_x('Red Chop', base_stage=lambda p, o, c: 3 + p.anger)                                           # 3 + X stages, X = current anger (after its own +1)
_x('Red Right Blast', immediate=lambda p, o, c: p.cb.update(rj_draw=True))                      # next Rejuvenate by either player this combat: draw 1 (engine: Player.rejuv)
_x('Red Static Shot', immediate=lambda p, o, c: p.cb.update(noend=True))                        # UNVERIFIED simplification: applies to all my attacks, not only Styled ones
_x('Red Repel', defend=lambda p, atk, x, c: atk.lose_stages(1))
# Nail
_x("Nail's Dashing Attacking", hit=_dashing_attacking_hit)
# Namekian
_x('Namekian Chop', hit=lambda p, o, c, r: p.raise_anger(len(p.balls)) if p.balls else None)    # HIT: raise anger X, X = Dragon Balls you control
_x('Namekian Planned Attack', hit=_find_ball)                                                   # HIT: search for a Dragon Ball and place it into play
_x('Dragon Radar', use=_find_ball, can_use=lambda p, o, c: any(x.ctype == 'Dragon Ball' for x in p.deck))
_x('Namekian Energy Guard', defend=_energy_guard)
_x('Namekian Crushing Slam', immediate=_crushing_slam)
_x('Namekian Hybrid Defense', defend=lambda p, atk, x, c: p.rejuv(p.level))                     # Rejuvenate X cards, X = your MP's level
_x('Namekian Regeneration', use=lambda p, o, c: p.rejuv(4), can_use=lambda p, o, c: len(p.discard) >= 2)
_x('Namekian Protective Posture', rejuv_self=True)                                              # Rejuvenate this card after use (engine: Player.defend)
_x('Namekian Overtime', use=_overtime)
_x('Android Headbutt', immediate=lambda p, o, c: p.raise_anger(1))                              # "raise or lower a player's anger 1": the AI raises its own


# =================================================================================================================
# The simple AI
# =================================================================================================================
def use_card(p, o, c):
    """Play an Event from hand or activate a Setup in play."""
    ex = CARD_EXTRA.get(c.name, {})
    src = p.setups if c in p.setups else p.hand
    src.remove(c)
    p.raise_anger(c.anger_self)
    for _ in range(c.crit_now):
        p.crit_effect()
    o.lower_anger(c.anger_opp)
    if c.opp_lose:
        o.lose_stages(c.opp_lose, c.opp_lose_floor)
    if c.rej:
        p.rejuv(c.rej)
    if c.gain:
        p.gain_stages(c.gain)
    if c.draw:
        p.draw(1)
    c.keep = False
    if ex.get('use'):
        ex['use'](p, o, c)
    if not getattr(c, 'keep', False):
        (p.banished if c.banish_after else p.discard).append(c)
    p.log(f'  {p.label}: {c.name}')


use_setup = use_card


def _usable(p, o, c):
    if c.name in NEVER_PLAY:
        return False
    if o.cb['noevents'] and c.ctype == 'Event':
        return False
    ex = CARD_EXTRA.get(c.name, {})
    if ex.get('can_use') and not ex['can_use'](p, o, c):
        return False
    return bool(c.crit_now or c.anger_self or c.rej or c.gain or c.draw or c.opp_lose or ex.get('use'))


def choose_action(a, d):
    """One action for player `a` against `d`. Returns True if something was done (False = pass)."""
    for b in a.behaviors():
        if b.power(a, d):
            return True
    wc = find_in(a.discard, lambda c: c.name == "Piccolo's Weighted Clothing")
    if wc:                                   # banish from the discard pile: raise anger 2 (an action)
        a.discard.remove(wc)
        a.banished.append(wc)
        a.log(f'  {a.label}: Weighted Clothing banished (+2 anger)')
        a.raise_anger(2)
        return True
    pool = a.setups + [x for x in a.hand if x.ctype == 'Event']
    for c in sorted(pool, key=lambda z: -a.value(z)):
        if _usable(a, d, c):
            use_card(a, d, c)
            return True
    atks = [x for x in a.hand if x.is_atk and x.cost <= a.stage and CARD_EXTRA.get(x.name, {}).get('can_attack', lambda p, o, c: True)(a, d, x)]
    if not atks:
        return False
    c = max(atks, key=lambda z: a.value(z) - z.cost * 0.5)
    if d.cb['stopall'] and False:
        return False
    return a.attack(d, card=c)
