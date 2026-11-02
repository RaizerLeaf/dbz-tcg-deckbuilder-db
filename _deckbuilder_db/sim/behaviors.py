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
    def on_ally_rejuvenated(self, p): pass
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
ALLY_PASSIVE = {}          # (card name, subtitle) -> Behavior of an Ally while it is in play (Allies share names, so the subtitle is part of the key)
MODELLED_ALLIES = {'Cell Jr.'}   # Allies the AI knows how to use; every other Ally is still never played
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


def ally_passive(name, sub):
    def deco(cls):
        ALLY_PASSIVE[(name, sub)] = cls()
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
# Cell Jr. (Villain, Set 7) and the Ally cards its decks use
#
# Level 1 allows 3 copies of each Cell Jr. Ally. All four levels spend Cell Jr. Allies FROM HAND (discard / Rejuvenate / banish),
# so hand Allies are fuel; Trapped is the one Ally the AI plays (its Continuous adds 1 to every destroy effect).
# NOT MODELLED: Escaping/Unrelenting Powers in play (Allies only act when the MP is at most 1 stage above 0), Allies being
# damaged or redirected to, critical effects discarding Allies, Blue Waiting Drill's "whenever you play an Ally, Rejuvenate 1".
# =================================================================================================================
def is_cj(c): return c.ctype == 'Ally' and c.name == 'Cell Jr.'
def cj_in(zone): return [x for x in zone if is_cj(x)]
def _sub(c): return c.rec.get('subtitle')


def _worth_stopping(card):
    """The AI only spends a stop on an attack that matters (same rule as Blue Protective)."""
    return (card.at or 0) + card.stage_flat >= 2 or card.life >= 2 or card.life_at or 'base_stage' in CARD_EXTRA.get(card.name, {})


def pick_ally(p, cands):
    """Which Ally the owner picks when a search lets him choose: a design not yet in play, Trapped first (its Continuous is the one that matters)."""
    in_play = {_sub(a) for a in p.allies}
    order = {'Trapped': 0, 'Escaping': 1, 'Unrelenting': 2}
    return min(cands, key=lambda c: (_sub(c) in in_play, order.get(_sub(c), 3)))


def play_ally(p, c, zone):
    zone.remove(c)
    p.allies.append(c)
    p.log(f'  {p.label}: Ally {c.name} - {_sub(c)} enters play')


def ally_leaves_play(p, c, how='banish'):
    """An Ally in play leaves it. Escaping: 'when this card is leaving play, you may banish it to destroy the top card' (always taken)."""
    p.allies.remove(c)
    if _sub(c) == 'Escaping':
        p.banished.append(c)
        p.destroy_opp(1)
    elif how == 'banish':
        p.banished.append(c)
    else:
        p.deck.append(c)


def plan_allies(p, o):
    """Planning Step: play Trapped from hand if no Trapped is in play (one is enough; the other Allies stay in hand as fuel)."""
    for c in list(p.hand):
        if is_cj(c) and _sub(c) == 'Trapped' and not any(_sub(a) == 'Trapped' for a in p.allies):
            play_ally(p, c, p.hand)


def _spend_order(c): return {'Unrelenting': 0, 'Escaping': 1, 'Trapped': 2}.get(_sub(c), 3)
def spend_ally(p):
    """The Cell Jr. Ally to spend from hand: the least useful one first (Unrelenting, Escaping, then Trapped)."""
    a = cj_in(p.hand)
    return min(a, key=_spend_order) if a else None


def discard_from_hand(p, c):
    p.hand.remove(c)
    p.discard.append(c)
    p.log(f'    ({p.label} discards {c.name} - {_sub(c)} from hand)')
    p.note_discard(c)


_CONT_PRIORITY = ['Blue Waiting Drill', 'Cell Jr.', 'Black Viewing Drill', 'Blue Biting Drill']


def fetch_continuous(p):
    """Level 1 HIT: search the Life Deck for a card with a [Continuous] effect and play it (Drill -> Drills in play, Ally -> Allies in play)."""
    cands = [x for x in p.deck if '[Continuous]' in x.text and x.ctype in ('Drill', 'Ally')]
    cands = [x for x in cands if not (x.ctype == 'Ally' and not is_cj(x))]
    if not cands:
        return None
    def rank(x):
        if x.ctype == 'Ally':          # a design already in play is not fetched again (Trapped would stack: unverified); Trapped before Escaping before Unrelenting
            if _sub(x) in {_sub(a) for a in p.allies}:
                return 98
            return {'Trapped': 1, 'Escaping': 60, 'Unrelenting': 70}.get(_sub(x), 80)
        return _CONT_PRIORITY.index(x.name) if x.name in _CONT_PRIORITY else 50
    c = min(cands, key=rank)
    p.deck.remove(c)
    p.rng.shuffle(p.deck)
    if c.ctype == 'Ally':
        p.allies.append(c)
    else:
        p.drills.append(c)
    p.log(f'  {p.label}: Taunting HIT plays {c.name}')
    return c


CJ_L1 = synthetic('Taunting', 'POWER: [Attack] Physical attack. DAMAGE: 4 stages.')
CJ_L2 = synthetic('On the Move', 'POWER: [Attack] Physical attack.')
CJ_L3 = synthetic('Oppressive', 'POWER: [Attack] Physical attack. DAMAGE: 1 life card.')


@mp('Cell Jr.', 'Taunting')
class CellJrL1(Behavior):
    """POWER: physical attack, 4 stages. You may discard a Cell Jr. Ally from hand: it cannot be stopped. HIT: search the Life Deck for a [Continuous] card and play it."""
    def has_power(self, p): return True

    def power(self, p, opp):
        if not once_turn(p, 'cj_l1'):
            return False
        a = spend_ally(p)
        p.tf['cj_unstop'] = a is not None
        if a is not None:
            discard_from_hand(p, a)
        p.attack(opp, power=CJ_L1)
        p.tf['cj_unstop'] = False
        return True

    def unstoppable(self, p, card): return card is CJ_L1 and p.tf.get('cj_unstop', False)

    def after_hit(self, p, opp, card, removed):
        if card is CJ_L1:
            fetch_continuous(p)


@mp('Cell Jr.', 'On the Move')
class CellJrL2(Behavior):
    """Continuous: once per combat discard a Cell Jr. Ally from hand to stop an attack. POWER: physical attack, 5 + X stages, X = Cell Jr. personalities in your discard pile."""
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'cj_l2'):
            p.attack(opp, power=CJ_L2)
            return True
        return False

    def defend_power(self, p, atk, card, kind):
        a = spend_ally(p)
        if a is not None and _worth_stopping(card) and once(p, 'cj_l2_stop'):
            discard_from_hand(p, a)
            return True
        return False



@mp('Cell Jr.', 'Oppressive')
class CellJrL3(Behavior):
    """Continuous: Rejuvenate a Cell Jr. Ally from hand to stop a physical or energy attack (as often as you have Allies).
    POWER: physical attack, 1 life card; first search the discard pile for 2 Cell Jr. Allies and Rejuvenate them. HIT: search the Life Deck for a Cell Jr. Ally and put it in hand."""
    def has_power(self, p): return True

    def power(self, p, opp):
        if not once_turn(p, 'cj_l3'):
            return False
        for x in cj_in(p.discard)[:2]:
            p.log(f'  {p.label}: Oppressive Rejuvenates {x.name} - {_sub(x)} from the discard pile')
            p.rejuv_ally(x, p.discard)
        p.attack(opp, power=CJ_L3)
        return True

    def after_hit(self, p, opp, card, removed):
        if card is CJ_L3 and removed > 0:
            fetch_from_deck(p, is_cj)

    def defend_power(self, p, atk, card, kind):
        a = spend_ally(p)
        if a is not None and _worth_stopping(card):
            p.log(f'    ({p.label} Rejuvenates {a.name} - {_sub(a)} from hand to stop {card.name})')
            p.rejuv_ally(a, p.hand)
            return True
        return False


@mp('Cell Jr.', 'Confident')
class CellJrL4(Behavior):
    """Action during combat (as often as you have Allies): banish a Cell Jr. Ally from hand to destroy the top 3 cards of the opponent's Life Deck.
    Your physical attacks without AT base damage deal +3 stages (only attacks that already deal stage damage get it in this engine)."""
    def stage_bonus(self, p, card, opp): return 3 if card.phys and card.at is None else 0
    def has_power(self, p): return bool(cj_in(p.hand))

    def power(self, p, opp):
        a = spend_ally(p)
        if a is None:
            return False
        p.hand.remove(a)
        p.banished.append(a)
        p.log(f'  {p.label}: banishes {a.name} - {_sub(a)} from hand')
        p.destroy_opp(3)
        return True


@ally_passive('Cell Jr.', 'Trapped')
class CjTrapped(Behavior):
    """While you control 1 Ally, your effects that destroy cards from the top of the opponent's Life Deck are increased by 1 (UNVERIFIED: two Trapped in play stack)."""
    def destroy_amount(self, p, n): return n + 1 if n > 0 else n


# ---- Masteries used with Cell Jr. -------------------------------------------------------------------------------------
@mastery('Blue Tag Team Mastery')
class BlueTagTeam(Behavior):
    """Start of the opponent's first turn: search for an Ally and put it into play (UNVERIFIED timing: done at game start). Instant POWER at the end of combat:
    Rejuvenate an Ally from your Banished Zone (once per turn). 'Cannot be discarded by critical damage effects' is not modelled (the engine's critical effects never discard Allies)."""
    def on_game_start(self, p):
        a = [x for x in p.deck if x.ctype == 'Ally' and (is_cj(x) or p.mp_name != 'Cell Jr.')]
        if a:
            c = pick_ally(p, a)
            p.deck.remove(c)
            p.rng.shuffle(p.deck)
            p.allies.append(c)
            p.log(f'  {p.label}: Tag Team puts {c.name} - {_sub(c)} into play')

    def end_of_combat(self, p, opp):
        a = [x for x in p.banished if x.ctype == 'Ally']
        if a and once_turn(p, 'tagteam'):
            p.log(f'  {p.label}: Tag Team Rejuvenates {a[0].name} - {_sub(a[0])} from the Banished Zone')
            p.rejuv_ally(a[0], p.banished)


@mastery('Black Perceptive Mastery')
class BlackPerceptive(Behavior):
    """Continuous: your Styled attacks gain 'HIT: destroy an opponent's Setup or Drill'. POWER: destroy the top card of your Life Deck to destroy the top card of the opponent's;
    if they destroyed a Physical or Energy Combat card your MP gains 4 stages, otherwise raise anger 1 (raising a player's anger is assumed to be your own)."""
    def has_power(self, p): return len(p.deck) > 15

    def power(self, p, opp):
        if len(p.deck) > 15 and once_turn(p, 'perceptive'):
            p.mill(1)
            before = len(opp.discard)
            p.destroy_opp(1)
            hit = any(c.ctype in ('Physical Combat', 'Energy Combat') for c in opp.discard[before:])
            p.log(f'  {p.label}: Perceptive POWER ({"+4 stages" if hit else "+1 anger"})')
            if hit:
                p.gain_stages(4)
            else:
                p.raise_anger(1)
            return True
        return False

    def after_hit(self, p, opp, card, removed):
        if card.style and card.style == p.styled() and card.card_id.split(':')[0] != 'synthetic':
            if opp.drills:
                opp.discard.append(opp.drills.pop())
            elif opp.setups:
                opp.discard.append(opp.setups.pop())


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
    return x is not None


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
def _visiting(p, o, c):
    if not _fetch_discard(p, is_cj):          # a Cell Jr. Ally first, else the top card of the discard pile
        _fetch_discard(p, lambda x: True)


def _fetch_discard_found(p, pred):
    return find_in(reversed(p.discard), pred) is not None


_x('Visiting the Past', use=_visiting,
   can_use=lambda p, o, c: bool(p.discard) and (p.mp_name != 'Cell Jr.' or _fetch_discard_found(p, is_cj)))
_x("Time Is A Warrior's Tool", defend=lambda p, atk, x, c: atk.cb.update(stopall=True))
_x('Black Duck', defend=lambda p, atk, x, c: (p.lose_card(p.deck.pop(0), 'destroy') if p.deck else None,
                                              p.destroy_opp(2) if p.rng.random() < 3 / max(3, len(p.deck)) else None))
_x('Black Running Guard', defend=lambda p, atk, x, c: p.destroy_opp(2) if c.style != atk.styled() else None)
_x('Black Flinch', defend=lambda p, atk, x, c: p.cb.update(next_life=p.cb['next_life'] + 4))
_x('Black Upward Dodge', defend=lambda p, atk, x, c: p.cb.update(next_life=p.cb['next_life'] + 4))
_x('Villainous Visage', on_damaged=lambda p, atk, x, removed: (p.hand.remove(x), p.banished.append(x), p.destroy_opp(2 * removed)))

# ---- Cell Jr. decks (Blue Tag Team / Red Ascension / Black Perceptive) -------------------------------------------------
_x('On the Move', base_stage=lambda p, o, c: 5 + len(cj_in(p.discard)))


def _surround(p, o, c):
    """Search the Life Deck for 2 Cell Jr. Allies and put them into play; the card is shuffled into the Life Deck after use."""
    for _ in range(2):
        a = [x for x in p.deck if is_cj(x)]
        if a:
            x = pick_ally(p, a)
            p.deck.remove(x)
            p.allies.append(x)
    p.deck.append(c)
    p.rng.shuffle(p.deck)
    c.keep = True


def _swarm_hit(p, o, c, removed):
    """HIT: banish any number of Cell Jr. Allies in play (all of them); the opponent destroys the top X cards, X = Allies banished (counts as your effect, owner ruling)."""
    n = 0
    for a in list(p.allies):
        if is_cj(a):
            ally_leaves_play(p, a, 'banish')
            n += 1
    if n:
        p.destroy_opp(n)


_x("Cell Jr.'s Surround", use=_surround, can_use=lambda p, o, c: any(is_cj(x) for x in p.deck) and len(p.allies) < 3)
_x("Cell Jr.'s Swarm", hit=_swarm_hit)
CARD_VALUE.update({'Cell Jr.': 9, "Cell Jr.'s Swarm": 5})


def _arrest_now(p, o, c):
    """Rejuvenate 3 Allies from your discard pile (before the damage); each one is a Rejuvenate of an Ally."""
    for x in [x for x in p.discard if x.ctype == 'Ally'][-3:]:
        p.rejuv_ally(x, p.discard)


def _arrest_hit(p, o, c, removed):
    a = [x for x in p.deck if x.ctype == 'Ally' and is_cj(x)]
    if a:
        x = pick_ally(p, a)
        p.deck.remove(x)
        p.allies.append(x)
        p.rng.shuffle(p.deck)


def _restraint(p, o, c):
    """Search the Life Deck for up to 3 Allies and banish them; the opponent destroys X, X = Allies in your Banished Zone."""
    for _ in range(3):
        a = [x for x in p.deck if x.ctype == 'Ally']
        if not a:
            break
        x = a[0]
        p.deck.remove(x)
        p.banished.append(x)
    p.rng.shuffle(p.deck)
    p.destroy_opp(sum(1 for x in p.banished if x.ctype == 'Ally'))


def _discharge_hit(p, o, c, removed):
    """HIT: Rejuvenate an Ally you control to search the discard pile for an Ally and play it."""
    if p.allies:
        x = p.allies[0]
        p.allies.remove(x)
        p.discard.append(x)                     # it must leave play first; Rejuvenating it puts it at the bottom of the Life Deck
        p.rejuv_ally(x, p.discard)
        a = [y for y in p.discard if y.ctype == 'Ally']
        if a:
            y = pick_ally(p, a)
            p.discard.remove(y)
            p.allies.append(y)


def _lunge(p, o, c):
    """Search the top 5 cards of the Life Deck for a Setup or Drill and place it into play."""
    top = [x for x in p.deck[:5] if x.ctype in ('Drill', 'Setup')]
    if top:
        pri = ['Blue Waiting Drill', 'Blue Biting Drill']
        x = min(top, key=lambda z: pri.index(z.name) if z.name in pri else 9)
        p.deck.remove(x)
        (p.drills if x.ctype == 'Drill' else p.setups).append(x)
    rest = p.deck[:4]
    del p.deck[:4]
    p.deck.extend(rest)


def _dominance(p, o, c):
    """Advance or lower your MP to Level 2; place up to 2 Drills from the discard pile into play (cannot win by MPPV that turn: not modelled)."""
    while p.level < 2:
        p.change_level(+1)
    while p.level > 2:
        p.change_level(-1)
    for _ in range(2):
        d = find_in(reversed(p.discard), lambda x: x.ctype == 'Drill')
        if d is None:
            break
        p.discard.remove(d)
        p.drills.append(d)


_x('Blue Arrest', immediate=_arrest_now, hit=_arrest_hit)
_x('Blue Restraint', use=_restraint, can_use=lambda p, o, c: any(x.ctype == 'Ally' for x in p.deck))
_x('Blue Discharge', immediate=lambda p, o, c: p.raise_anger(2), hit=_discharge_hit, can_use=lambda p, o, c: bool(p.allies))
_x('Blue Slash', hit=lambda p, o, c, r: p.destroy_opp(max(0, 6 - o.anger)))
_x('Blue Challenging Strike', immediate=lambda p, o, c: p.cb.update(destroy_bonus=p.cb['destroy_bonus'] + 1))   # real card: until the end of your NEXT turn (only this combat here)
_x('Blue Lunge', immediate=_lunge)
_x('Blue Dominance', use=_dominance, can_use=lambda p, o, c: p.level < 2)
_x('Blue Head Knock', immediate=lambda p, o, c: setattr(o, 'anger', 0))
_x('Blue Defensive Stance', defend=lambda p, atk, x, c: p.raise_anger(1))          # 'raise or lower a player's anger 1 level' (own)


@passive('Blue Waiting Drill')
class WaitingDrill(Behavior):
    """Whenever you Rejuvenate an Ally, destroy the top 2 cards of the opponent's Life Deck. ('Whenever you play an Ally, Rejuvenate 1' is not modelled.)"""
    def on_ally_rejuvenated(self, p):
        got = p.destroy_opp(2)
        p.log(f'    (Waiting Drill: Ally Rejuvenated -> opponent destroys {got})')


@passive('Blue Biting Drill')
class BitingDrill(Behavior):
    """Your attacks deal +2 power stages of damage. (The anger-0 mill sentence is not modelled.)"""
    def stage_bonus(self, p, card, opp): return 2


# ---- Black / Red cards of the Cell Jr. decks ----------------------------------------------------------------------------
def _command(p, o, c):
    """Banish the top 5 cards of the opponent's discard pile; if fewer than 5 were banished, the opponent destroys the top 3 cards of his Life Deck."""
    n = 0
    while n < 5 and o.discard:
        o.banished.append(o.discard.pop())
        n += 1
    if n < 5:
        p.destroy_opp(3)


def _discard_banish_anger(p, c):
    """'If this card is discarded from your hand, you may banish it to raise your anger 2 levels' (Black Command)."""
    if c in p.discard:
        p.discard.remove(c)
        p.banished.append(c)
        p.raise_anger(2)


def _wilt(p, o, c):
    """Instant: +1 to a destroy effect, then the card goes to the bottom of the Life Deck. Simplified: +1 to my next destroy effect this combat (UNVERIFIED)."""
    p.cb['next_destroy_bonus'] += 1
    p.deck.append(c)
    c.keep = True


def _foreshadowing(p, o, c):
    x = len({z.ctype for z in o.banished})
    if x:
        p.destroy_opp(x)
        p.gain_stages(x)


_x('Black Command', use=_command, can_use=lambda p, o, c: True)
CARD_DISCARD_TRIGGER['Black Command'] = _discard_banish_anger
CARD_DISCARD_TRIGGER['Black Corruption'] = lambda p, c: p.opp.mill(2, 'banish')      # discarded by one of your effects: banish the top 2 of his Life Deck
_x('Black Pop-Up', use=lambda p, o, c: p.destroy_opp(1))        # the 'name a card' critical-effect gamble is not modelled
_DESTROYERS = {'Black Command', 'Black Taunt', 'Black Pop-Up', 'Black Confinement', 'Black Invitation', 'Black Foreshadowing', 'Black Drain'}
_x('Black Wilt', use=_wilt, can_use=lambda p, o, c: not p.cb['next_destroy_bonus'] and (
    any(x.name in _DESTROYERS for x in p.hand if x is not c) or ('perceptive' not in p.tf and p.mastery == 'Black Perceptive Mastery')
    or (p.mp_name == 'Cell Jr.' and p.level == 4 and bool(cj_in(p.hand)))))
_x('Black Foreshadowing', use=_foreshadowing, can_use=lambda p, o, c: bool(o.banished))
_x('Red Chop', base_stage=lambda p, o, c: 3 + p.anger)


@passive('Black Viewing Drill')
class ViewingDrill(Behavior):
    """After your opponent discards a card from his hand by a card effect during combat, destroy the top card of his Life Deck."""
    def on_card_discarded(self, p):
        if p.game.last_discarder is p.opp:
            p.destroy_opp(1)


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


def _attack_ok(a, d, x):
    gate = CARD_EXTRA.get(x.name, {}).get('can_use')
    return x.cost <= a.stage and (gate is None or gate(a, d, x))


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
    pool = [s for s in a.setups if not s.is_atk] + [x for x in a.hand if x.ctype == 'Event']
    for c in sorted(pool, key=lambda z: -a.value(z)):
        if _usable(a, d, c):
            use_card(a, d, c)
            return True
    # attacks: from hand, or a Setup in play whose POWER is an attack (activated, then discarded like an Event)
    atks = [(x, False) for x in a.hand if x.is_atk and _attack_ok(a, d, x)] + [(s, True) for s in a.setups if s.is_atk and _attack_ok(a, d, s)]
    if not atks:
        return False
    c, from_setup = max(atks, key=lambda z: a.value(z[0]) - z[0].cost * 0.5)
    if not from_setup:
        return a.attack(d, card=c)
    a.setups.remove(c)
    ok = a.attack(d, power=c)
    (a.banished if c.banish_after else a.discard).append(c)
    return ok
