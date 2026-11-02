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
    def on_opp_advance(self, p, opp): pass             # my opponent's MP advanced a level (Broly Levels 1-3 drain stages)
    def banish_damage(self, p, card): return False      # damage dealt by my attack `card` is banished instead of destroyed (Broly Level 4)
    def on_rejuvenate(self, p): pass
    def on_shuffle_in(self, p): pass
    def on_ally_rejuvenated(self, p): pass
    def rejuv_amount(self, p, n): return n                 # in-combat Rejuvenate amount before it is applied (Lord Slug Level 3 doubles the first one)
    def on_gain_stages(self, p, n): pass
    def on_card_discarded(self, p): pass
    def on_play(self, p, opp, card): pass
    def on_drill_played(self, p, opp, card): pass
    def on_enters_play(self, p, opp, card): pass       # one of your Setups or Drills entered play (played, searched or placed); p.game.in_combat tells when
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
    def on_turn_start(self, p, mine): pass            # start of every turn, for both players (mine = it is p's turn)
    def protect_allies(self, p): return False         # True = opponent's critical effects cannot discard my Allies
    def on_ally_entered(self, p, card): pass          # one of my Allies entered play (card.played True = 'play', False = 'place into play')


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
        enter_play(p, c)
    elif to == 'setup':
        enter_play(p, c)
    elif to == 'ball':
        p.balls.append(c)
        for b in p.behaviors():
            b.on_ball_entered(p)
        p.check_dbv()
    return c


def enter_play(p, card):
    """A Drill or Setup enters play for `p` by an effect (search, 'place into play'). The planning-step play is in engine.py."""
    (p.drills if card.ctype == 'Drill' else p.setups).append(card)
    ex = CARD_EXTRA.get(card.name, {})
    if ex.get('enters'):
        ex['enters'](p, p.opp, card)
    for b in p.behaviors():
        b.on_enters_play(p, p.opp, card)


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
    """[Continuous]: Whenever one of your effects during combat Rejuvenates or shuffles cards into your Life Deck, raise your anger 1 level.
    After a Namek Dragon Ball enters play under your control, destroy the top card of your opponent's Life Deck. While you control 1 Dragon Ball, it cannot be captured by a critical damage effect.
    Modelled: +1 anger per in-combat Rejuvenate effect (`on_rejuvenate`, once per effect, not per card; UNVERIFIED), the Sudden Blast shuffle counts as one trigger, a Namek ball entering mills 1
    (also when it enters through Planning or a search; captured balls do not count), one ball cannot be captured."""
    def on_rejuvenate(self, p): p.raise_anger(1)
    def on_shuffle_in(self, p): p.raise_anger(1)     # effects that shuffle cards into your Life Deck, via shuffle_into_deck()

    def on_ball_entered(self, p):
        if p.balls and p.balls[-1].name.startswith('Namek Dragon Ball'):
            p.destroy_opp(1, noamp=True)

    def protect_balls(self, p): return len(p.balls) == 1


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


@mastery('Orange Adaptive Mastery')
class OrangeAdaptive(Behavior):
    """Your Drills are not discarded when you advance or lower a level. Your energy attacks deal +1 life card. At the end of any combat in which you used
    a critical damage effect, search your discard pile for a Styled Drill and place it into play. (UNVERIFIED: the end of combat still counts as 'during combat'.)"""
    def keep_drills(self, p, old_level): return True
    def life_bonus(self, p, card, opp): return 1 if card.energy else 0
    def on_crit_effect(self, p): p.cb['adaptive_crit'] = True

    def end_of_combat(self, p, opp):
        if p.cb.get('adaptive_crit'):
            x = find_in(reversed(p.discard), lambda c: c.ctype == 'Drill' and c.style is not None and c.style == p.styled())
            if x is not None:
                p.discard.remove(x)
                enter_play(p, x)


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
    def adv_anger_delta(self, p):
        # Saiyan Analysis Drill (also 1 less) is modelled as 'need 4'; together with this Mastery the minimum of 4 holds (UNVERIFIED how the real game combines them)
        return 0 if any(d.name == 'Saiyan Analysis Drill' for d in p.drills) else -1

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
# Broly (Set 6 levels: Survivor, Determined, Legendary, Relentless). All four are modelled from the printed text.
# "Reveal N attack cards from your hand" is a free condition (revealing costs nothing): the AI always takes the option when it can.
# NOT MODELLED: Level 3's "all of your opponent's personalities lose 7 stages" only hits the MP (Allies are not stage-tracked for this).
# =================================================================================================================
BROLY_L1 = synthetic('Survivor', 'POWER: [Attack] Physical attack. Raise your anger 1 level. DAMAGE: 4 stages.')
BROLY_L3 = synthetic('Legendary', 'POWER: [Attack] Physical attack. DAMAGE: 4 stages.')


def _attack_cards_in_hand(p, n):
    return sum(1 for x in p.hand if x.is_atk) >= n


def _banish_opp_support(o, ally=False):
    """Banish every Setup and Drill (and Ally if `ally`) the opponent has in play."""
    n = 0
    for z in (o.setups, o.drills):
        while z:
            o.banished.append(z.pop())
            n += 1
    if ally:
        for a in list(my_allies(o)):
            o.leave_play(a, 'banish')
            n += 1
    return n


class _BrolyBase(Behavior):
    drain = 0            # stages the opponent's MP loses after it advances
    phys_bonus = 0

    def on_opp_advance(self, p, opp):
        if self.drain:
            opp.lose_stages(self.drain)

    def stage_bonus(self, p, card, opp):
        # "Physical attacks performed by this personality": not an Ally's attack
        return self.phys_bonus if (card.phys and getattr(p, 'cur_ally', None) is None) else 0


@mp('Broly', 'Survivor')
class BrolyL1(_BrolyBase):
    drain = 5
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'broly1'):
            return p.attack(opp, power=BROLY_L1)
        return False

    def on_play(self, p, opp, card):
        if card.name == 'Survivor' and _attack_cards_in_hand(p, 2):      # may reveal 2 attack cards: banish the top card of his Life Deck
            opp.mill(1, 'banish')


@mp('Broly', 'Determined')
class BrolyL2(_BrolyBase):
    drain, phys_bonus = 7, 2
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'broly2'):
            opp.mill(1, 'banish')
            if _attack_cards_in_hand(p, 2) and (opp.setups or opp.drills):
                z = opp.setups if opp.setups else opp.drills
                opp.banished.append(z.pop())
            return True
        return False


@mp('Broly', 'Legendary')
class BrolyL3(_BrolyBase):
    drain, phys_bonus = 7, 3
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'broly3'):
            return p.attack(opp, power=BROLY_L3)
        return False

    def on_play(self, p, opp, card):
        if card.name == 'Legendary' and _attack_cards_in_hand(p, 2):     # may reveal 2 attack cards: draw a card
            p.draw(1)


@mp('Broly', 'Relentless')
class BrolyL4(_BrolyBase):
    phys_bonus = 4
    def has_power(self, p): return True
    def banish_damage(self, p, card): return bool(card.phys and getattr(p, 'cur_ally', None) is None)
    def entering_combat(self, p, opp, defender): p.cb['noend'] = True       # the opponent cannot use Endurance

    def power(self, p, opp):
        if once_turn(p, 'broly4'):
            opp.mill(2, 'banish')
            if _attack_cards_in_hand(p, 4):
                _banish_opp_support(opp, ally=True)
            return True
        return False


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

    def rejuv_amount(self, p, n):
        # "The first time during combat one of your effects shuffles or Rejuvenates cards from your discard pile into your Life Deck, double that amount."
        # Only Rejuvenate is doubled here; the shuffle half of the text (Namekian Sudden Blast) is not. UNVERIFIED: whether a card-by-card pick (Airborne Attack) is doubled too (modelled as yes).
        return 2 * n if once(p, 'slug3_double') else n


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
    def on_turn_start(self, p, mine):
        """Goku decks (ALLY_MODEL Allies): done at the start of the opponent's first turn, as the card says. Also: while you control exactly 1 Ally it cannot be
        discarded by critical damage effects (protect_allies). The Cell Jr. decks keep the game-start timing below."""
        if p.mp_name == 'Goku' and not mine and not p.gf.get('tag_team'):
            p.gf['tag_team'] = True
            search_ally(p, ('deck',), 3)

    def protect_allies(self, p): return len(p.allies) == 1

    def on_game_start(self, p):
        if p.mp_name == 'Goku':
            return
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
    if c.name == 'Namekian Dragon Blast':          # DAMAGE: 4 + X life cards, X = Dragon Balls in play (anyone's)
        adj += len(p.balls) + len(opp.balls)
    if (c.life or c.life_at) and any(b.name == 'Earth Dragon Ball 1' for b in p.balls + opp.balls):
        adj += 1
    return adj



# =================================================================================================================
# Allies (only the Allies listed in ALLY_MODEL are ever played; all other Allies stay inert, as before)
# =================================================================================================================
# Rulebook 3.0: Allies enter at 3 stages above 0, gain their own PUR in the Planning Step, act (Power / attack / defend) only when the MP is
# at most 1 stage above 0 (or a card says otherwise), use their own Power Level on the Attack Table and pay energy costs from their own stages.
# NOT MODELLED: damage redirected to Allies, Allies as targets of "banish a Drill or Ally" effects, Ally Continuous powers other than those listed.
_VEGETA_ATK = synthetic('Ally Vegeta', 'POWER: [Attack] Energy attack costing 1 stage. DAMAGE: AT +0 life cards.')
_CHAOZU_ATK = synthetic('Ally Chaozu', 'POWER: [Attack] Energy attack costing 4 stages. DAMAGE: 7 life cards.')
_TENSHIN_ATK = synthetic('Ally Tenshinhan', 'POWER: [Attack] Energy attack costing 2 stages. DAMAGE: 3 life cards.')
_YAMCHA_ATK = synthetic('Ally Yamcha', 'POWER: [Attack] Energy attack costing 1 stage. DAMAGE: 3 life cards.')
# value = how much the AI wants this Ally when it can choose; attack = the Ally's POWER attack; defend = the kind of attack its POWER stops
ALLY_MODEL = {
    'Vegeta': dict(value=4.0, attack=_VEGETA_ATK, defend=None),                 # Set 4 Vegeta (Goku): attack AT life cards for 1 stage; hand-stop below
    'Chaozu': dict(value=7.0, attack=_CHAOZU_ATK, defend=None, shuffle_after=True),   # UNVERIFIED timing: shuffled back right after the attack
    'Tenshinhan': dict(value=3.5, attack=_TENSHIN_ATK, defend=None),
    'Yamcha': dict(value=3.2, attack=_YAMCHA_ATK, defend=None),
    'Chichi': dict(value=2.5, attack=None, defend='p', free_for=('Goku', 'Gohan', 'Goten')),
    'Piccolo': dict(value=1.0, attack=None, defend='e', free_for=('Gohan',)),
}


def ally_model(card):
    m = ALLY_MODEL.get(card.name)
    if m is not None and card.name == 'Vegeta' and not card.text.startswith('(If your MP is Goku'):
        return None                                   # the Villains-only Set 2 Vegeta is not modelled
    return m


def ally_value(a): return ALLY_MODEL[a.name]['value']


def my_allies(p):
    """Allies in play that belong to this model (the Cell Jr. Allies in p.allies are handled by their own code and have no stages)."""
    return [a for a in p.allies if a.name in ALLY_MODEL and hasattr(a, 'astage')]


def ally_may_act(p, a):
    m = ALLY_MODEL[a.name]
    return p.stage <= 1 or a.name in p.cb['ally_free'] or p.mp_name in m.get('free_for', ())


def search_ally(p, where=('deck',), stage=3, played=False, names=None):
    """Search the given zones for an Ally not already in play and put it into play. Returns the Ally or None."""
    cands = []
    for z in where:
        for x in getattr(p, z):
            if x.ctype == 'Ally' and ally_model(x) and not any(a.name == x.name for a in p.allies) and (names is None or x.name in names):
                cands.append((z, x))

    def score(zx):
        m = ally_model(zx[1])
        return m['value'] if m['attack'] is None or m['attack'].cost <= stage else 0.5
    if not cands:
        return None
    z, x = max(cands, key=score)
    getattr(p, z).remove(x)
    if z == 'deck':
        p.rng.shuffle(p.deck)
    p.put_ally(x, stage, played)
    return x


def rejuv_ally_from(p, ally_card):
    """Rejuvenate an Ally from the discard pile / Banished Zone to the bottom of the Life Deck (Player.rejuv_ally fires on_ally_rejuvenated)."""
    p.rejuv_ally(ally_card, p.discard if ally_card in p.discard else p.banished)


def best_attacker(p):
    """The Ally in play with an affordable attack and the highest value (None if there is none)."""
    c = [a for a in my_allies(p) if ALLY_MODEL[a.name]['attack'] is not None and ALLY_MODEL[a.name]['attack'].cost <= a.astage]
    return max(c, key=ally_value) if c else None


def ally_can_attack(p, o):
    """At declaration time: could an Ally attack without any free-action card (MP at most 1 stage above 0)?"""
    return p.stage <= 1 and any(a for a in my_allies(p) if ALLY_MODEL[a.name]['attack'] is not None and f'aatk_{a.name}' not in p.tf
                                and ALLY_MODEL[a.name]['attack'].cost <= a.astage)


def ally_attack(p, o):
    """One Ally attack action (each Ally's Power once per turn). Returns True if an Ally attacked."""
    c = [a for a in my_allies(p) if ALLY_MODEL[a.name]['attack'] is not None and f'aatk_{a.name}' not in p.tf and ally_may_act(p, a)
         and ALLY_MODEL[a.name]['attack'].cost <= a.astage]
    if not c:
        return False
    a = max(c, key=ally_value)
    p.tf[f'aatk_{a.name}'] = True
    m = ALLY_MODEL[a.name]
    p.log(f'  {p.label}: Ally {a.name} attacks')
    ok = p.attack(o, power=m['attack'], ally=a)
    if ok and m.get('shuffle_after') and a in p.allies:
        p.leave_play(a, 'deck')
    return ok


def ally_defend(p, atk, c, kind):
    """An Ally (or Vegeta from the hand when the MP is Goku) stops an attack. Same size threshold as a hand defense."""
    if not ((c.at or 0) + c.stage_flat >= 2 or c.life >= 2 or c.life_at):
        return False
    if p.mp_name == 'Goku' and 'vegeta_stop' not in p.cb['used'] and not any(a.name == 'Vegeta' for a in my_allies(p)):
        v = find_in(p.hand, lambda x: x.ctype == 'Ally' and ally_model(x) and x.name == 'Vegeta')
        if v is not None:
            p.cb['used'].add('vegeta_stop')            # once per combat
            p.hand.remove(v)
            p.put_ally(v, 2)                           # placed at 2 stages above 0 (the card says 'place this card into play')
            p.log(f'    ({p.label} places Vegeta from the hand to stop it)')
            return True
    for a in my_allies(p):
        if ALLY_MODEL[a.name]['defend'] == kind and ally_may_act(p, a) and f'adef_{a.name}' not in p.tf:
            p.tf[f'adef_{a.name}'] = True
            p.log(f'    ({p.label} stops it with Ally {a.name})')
            return True
    return False


# Attack cards that may be played to stop an attack instead of attacking (text: "You may play this card to stop a physical attack instead of as an attack").
ALT_STOP = {'Blue Arm Blast': 'p', 'Blue Round Throw': 'e'}


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
        enter_play(p, x)


# ---- Orange Uppercut / Orange Enraged Bash: situational searches (owner: pick what the current situation needs) -------------
def _mppv_threat(opp):
    """The opponent is close to winning by MPPV (or to advancing a level fast): anger-lowering cards are what I need."""
    return (opp.level == 4 and opp.anger >= 3) or opp.anger >= 4


def _energy_need(p, opp, c):
    """How much the current situation wants this Styled Energy Combat card (used by Orange Uppercut's search)."""
    v = p.value(c)
    lower = c.anger_opp + c.anger_opp_hit
    if _mppv_threat(opp):
        v += 10 * (lower >= 2) + 4 * (lower >= 1) + c.anger_self
    if (opp.balls or B_has_ally(opp)) and (c.crit_now or c.crit_hit):
        v += 8                      # a critical damage effect captures a Dragon Ball / discards an Ally (Dragon Ball Victory decks)
    if not any(x.is_def for x in p.hand) and c.is_def and 'e' in c.stops:
        v += 6                      # nothing to block with
    if c.cost and p.stage - 2 < c.cost:
        v -= 6                      # could not afford it after paying for the search
    return v


def B_has_ally(opp):
    return bool(my_allies(opp))


def _uppercut(p, o, c):
    if p.stage < 3:
        return
    style = p.styled()
    cands = [x for x in p.deck if x.ctype == 'Energy Combat' and style and x.style == style]
    if not cands:
        return
    x = max(cands, key=lambda z: _energy_need(p, o, z))
    p.stage -= 2
    p.deck.remove(x)
    p.rng.shuffle(p.deck)           # a search shuffles the Life Deck (Rulebook 3.0)
    p.hand.append(x)
    p.cb['searched'] = True


def _drill_need(p, opp, c):
    v = p.value(c)
    if c.name == 'Orange Devouring Drill':
        v += 12 if p.level < 4 else -20     # a level-up only helps below Level 4
    if p.level == 4 or opp.level == 4:
        v += 6 * bool(c.name in ('Orange Burning Aura Drill', 'Orange Steady Drill'))
    elif c.name in ('Orange Burning Aura Drill', 'Orange Steady Drill'):
        v += 2
    return v


def _rejuvenate_drill(p, zone):
    cands = [x for x in zone if x.ctype == 'Drill']
    if not cands:
        return
    x = max(cands, key=lambda z: _drill_need(p, p.opp, z))
    zone.remove(x)
    p.deck.append(x)                # Rejuvenate: bottom of the Life Deck; the next search shuffles it back in
    for b in p.behaviors():
        b.on_rejuvenate(p)
    if any(d.name == 'Orange Intimidating Drill' for d in p.drills) and once(p, 'intimidating'):
        p.rng.shuffle(p.deck)
        p.draw(1)


_x('Orange Uppercut', immediate=_uppercut)
_x('Orange Enraged Bash', immediate=lambda p, o, c: _rejuvenate_drill(p, p.discard),
   hit=lambda p, o, c, r: _rejuvenate_drill(p, p.banished))


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
    """Whenever you Rejuvenate an Ally, destroy the top 2 cards of the opponent's Life Deck. 'Whenever you play an Ally, Rejuvenate 1' is modelled for the Goku
    Allies only (on_ally_entered with card.played), not for the Cell Jr. Allies."""
    def on_ally_entered(self, p, card):
        if getattr(card, 'played', False):
            p.rejuv(1)

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
# ---- Namekian / Lord Slug cards (Dragon Ball search, Rejuvenate X, Wall Breaker, ...) ------------------------------------------
BALL_ORDER = [1, 6, 5, 3, 7, 2, 4]          # which ball a search takes first (the AI picks the best one it can)


def _ball_no(c): return int(c.name.rsplit(' ', 1)[1])


def _ball_candidates(p, namek_only=False, max_no=None):
    """Dragon Balls in p's Life Deck that may enter play: no ball with the same name already in play under p (rule of the game)."""
    names = {b.name for b in p.balls}
    out = [c for c in p.deck if c.ctype == 'Dragon Ball' and c.name not in names]
    if namek_only:
        out = [c for c in out if c.name.startswith('Namek Dragon Ball')]
    if max_no is not None:
        out = [c for c in out if _ball_no(c) <= max_no]
    return out


def _put_ball(p, o, c, play):
    """Put ball c (already removed from its zone) into play. play=True: it was *played*, so its immediate effects are used; play=False: *placed into play*, no immediate effects."""
    p.balls.append(c)
    if play:
        ex = CARD_EXTRA.get(c.name, {})
        if ex.get('immediate'):
            ex['immediate'](p, o, c)
    for b in p.behaviors():
        b.on_ball_entered(p)
    p.check_dbv()


def _fetch_ball(p, o, play, namek_only=False, max_no=None, count=1):
    """Search the Life Deck for Dragon Ball(s) and play (immediate effects) or place them into play. Returns how many entered."""
    n = 0
    for _ in range(count):
        cands = _ball_candidates(p, namek_only, max_no)
        if not cands:
            break
        c = min(cands, key=lambda x: BALL_ORDER.index(_ball_no(x)) if _ball_no(x) in BALL_ORDER else 9)
        p.deck.remove(c)
        p.rng.shuffle(p.deck)
        _put_ball(p, o, c, play)
        n += 1
    return n


def _balls_in_play(p, o): return len(p.balls) + len(o.balls)


# "Search ... for a Dragon Ball and play it" (the text says *play*: immediate effects are used)
_x('Dragon Radar', use=lambda p, o, c: _fetch_ball(p, o, True), can_use=lambda p, o, c: bool(_ball_candidates(p)))
_x('Namekian Dragon Clan', use=lambda p, o, c: _fetch_ball(p, o, True, count=2 if p.level == 4 else 1), can_use=lambda p, o, c: bool(_ball_candidates(p)))
_x('Namekian Disturbance', use=lambda p, o, c: _fetch_ball(p, o, True, namek_only=True, max_no=p.level),
   can_use=lambda p, o, c: bool(_ball_candidates(p, True, p.level)))
# HIT: "search ... for a Dragon Ball and place it into play" (no immediate effects)
_x('Namekian Planned Attack', hit=lambda p, o, c, r: _fetch_ball(p, o, False))
_x('Namekian Dash', hit=lambda p, o, c, r: _fetch_ball(p, o, False))     # the optional "reveal a ball to look at the opponent's hand" is not modelled (no hidden information)


def _growth(p, o, c):
    """Namekian Growth: play a Dragon Ball from your hand, or Rejuvenate 4 (the Level 3+ 'search for a Styled card instead' option is not modelled)."""
    names = {b.name for b in p.balls}
    ball = next((x for x in p.hand if x.ctype == 'Dragon Ball' and x.name not in names), None)
    if ball is not None:
        p.hand.remove(ball)
        _put_ball(p, o, ball, True)
    else:
        p.rejuv(4)


_x('Namekian Growth', use=_growth, can_use=lambda p, o, c: len(p.discard) >= 3 or any(x.ctype == 'Dragon Ball' and x.name not in {b.name for b in p.balls} for x in p.hand))


# Rejuvenate X / Rejuvenate from the discard pile
_x('Namekian Dragon Blast', hit=lambda p, o, c, r: p.rejuv(_balls_in_play(p, o)))          # HIT: Rejuvenate X, X = Dragon Balls in play (anyone's)
_x('Namekian Overhead Blast', hit=lambda p, o, c, r: p.rejuv(p.level))                      # HIT: Rejuvenate X, X = your MP's level
_x('Namekian Hybrid Defense', defend=lambda p, atk, x, c: p.rejuv(p.level))                 # Choose X cards in your discard pile and Rejuvenate them, X = your MP's level
_x('Namekian Regeneration', use=lambda p, o, c: p.rejuv(4), can_use=lambda p, o, c: len(p.discard) >= 3)   # top or bottom 4 (the model takes the top 4)
_x("Lord Slug's Regeneration", can_use=lambda p, o, c: len(p.discard) >= 3)                 # the AI plays it proactively; "use after taking damage" and "may advance or lower 1 level" are not modelled
_x('Namekian Airborne Attack', immediate=lambda p, o, c: p.rejuv(1, pred=lambda x: x.style != p.styled()))   # search the discard pile for a non-Styled card and Rejuvenate it


def _protective_posture(p, atk, x, c):
    """Rejuvenate this card after use: it goes back to the bottom of the Life Deck instead of the discard pile."""
    x.keep = True
    p.deck.append(x)
    for b in p.behaviors():
        b.on_rejuvenate(p)


_x('Namekian Protective Posture', defend=_protective_posture)


def _sudden_blast(p, o, c, removed):
    """HIT: choose 4 cards in your discard pile, banish 2, shuffle the rest into your Life Deck (counts as one 'shuffles cards into your Life Deck' trigger; the Slug L3 doubling is not applied to it)."""
    pick = [p.discard.pop() for _ in range(min(4, len(p.discard)))]
    p.banished.extend(pick[:2])
    p.deck.extend(pick[2:])
    p.rng.shuffle(p.deck)
    if pick[2:]:
        for b in p.behaviors():
            b.on_rejuvenate(p)


_x('Namekian Sudden Blast', hit=_sudden_blast)


def _second_use(p, o, c, removed):
    """Namekian Onslaught: with 2 or more Dragon Balls the attack stays in play and is used a second time this combat (the model uses it again at once)."""
    if len(p.balls) >= 2 and once(p, 'onslaught2'):
        p.attack(o, power=c)


_x('Namekian Onslaught', hit=_second_use)


def _draw_bottom_discard(p, o, c):
    """Red Relaxation: 'Draw the bottom card of your discard pile.' (the discard pile's bottom is index 0; new discards are appended on top)."""
    if p.discard:
        p.hand.append(p.discard.pop(0))


_x('Red Relaxation', use=_draw_bottom_discard)


def _fusion(p, o, c):
    p.gain_stages(10)
    p.draw(1)
    if p.hand and p.hand[-1].style == p.styled():
        p.rejuv(2)


_x('Namekian Fusion', use=_fusion, can_use=lambda p, o, c: p.stage <= 6)


def _overtime(p, o, c):
    """Rejuvenate 1 (parsed), destroy X cards from the opponent's Life Deck (X = Dragon Balls you control), search for a Styled Energy Combat card."""
    p.destroy_opp(len(p.balls))
    fetch_from_deck(p, lambda x: x.style == p.styled() and x.ctype == 'Energy Combat')


_x('Namekian Overtime', use=_overtime)


def _namek4(p, o, c):
    for _ in range(2):                       # destroy up to 2 Setups or Drills (the model destroys the opponent's)
        if o.drills:
            o.discard.append(o.drills.pop())
        elif o.setups:
            o.discard.append(o.setups.pop())


_x('Namek Dragon Ball 4', immediate=_namek4)


def _optic_blast(p, o, c, removed):
    """HIT: capture a Dragon Ball (not if its owner's effect protects it); a captured Namek ball destroys the top 3 cards of the opponent's Life Deck, an Earth ball draws a card."""
    if o.balls and not any(b.protect_balls(o) for b in o.behaviors()):
        ball = o.balls.pop()
        p.balls.append(ball)
        p.check_dbv()
        if ball.name.startswith('Namek'):
            p.destroy_opp(3, noamp=True)
        else:
            p.draw(1)


_x('Optic Blast', hit=_optic_blast)


class _WallBreaker(Behavior):
    """Wall Breaker attached to this player's MP: this player cannot gain anger; the card is banished when this player deals critical damage."""
    def anger_modify(self, p, n, in_combat): return 0

    def on_crit_damage(self, p, opp):
        for c in [x for x in p.attached if x.name == 'Wall Breaker']:
            p.attached.remove(c)
            opp.banished.append(c)


CARD_PASSIVE['Wall Breaker'] = _WallBreaker()


def _wall_breaker(p, o, c):
    if not any(x.name == 'Wall Breaker' for x in o.attached):        # a second copy would change nothing (unverified how copies stack)
        o.attached.append(c)
        c.keep = True


_x('Wall Breaker', immediate=_wall_breaker)
# Villainous Energy Beam: "damage from this attack is banished" is not modelled (the cards leave the Life Deck either way; only the opponent's discard pile differs).
# Korin and every other Ally: Allies are not simulated.


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



# =================================================================================================================
# Goku (Set 7 Awakening Training / Determined, Set 4 Evolution Calm / Dashing) and Blue Tag Team
# =================================================================================================================
GOKU_CALM = synthetic('Goku Calm', 'POWER: [Attack] Energy attack. DAMAGE: 6 life cards.')


@mp('Goku', 'Training')
class GokuL1(Behavior):
    """[Continuous]: your attacks deal +1 life card. [Instant] POWER: use when entering combat: draw a card (once per turn)."""
    def life_bonus(self, p, card, opp): return 1

    def entering_combat(self, p, opp, defender):
        if once_turn(p, 'goku_train'):
            p.draw(1)


@mp('Goku', 'Determined')
class GokuL2(Behavior):
    """[Continuous]: your attacks +1 life card, opponent's attacks -1 life card. POWER: draw the bottom card of your discard pile; you may
    discard a card from your hand to use a critical damage effect (the AI always does)."""
    def life_bonus(self, p, card, opp): return 1
    def incoming_life(self, p, card, atk): return -1
    def has_power(self, p): return 'goku_det' not in p.tf and bool(p.discard or p.hand)

    def power(self, p, opp):
        if (p.discard or p.hand) and once_turn(p, 'goku_det'):
            if p.discard:
                p.hand.append(p.discard.pop(0))
            if p.hand:
                p.hand.sort(key=p.value)
                h = p.hand.pop(0)
                p.discard.append(h)
                p.note_discard(h)
                p.crit_effect()
            return True
        return False


def _calm_search(p, o, c):
    a = search_ally(p, ('deck', 'discard'), 3, played=True)       # "search ... for an Ally and play it"
    if a is not None:
        p.cb['ally_free'].add(a.name)                             # "that Ally can make actions regardless of your MP's power stage this combat"


@mp('Goku', 'Calm')
class GokuL3(Behavior):
    """POWER: [Attack] energy attack, 6 life cards; search Life Deck or discard pile for an Ally and play it (it may act this combat).
    HIT: if your next attack this combat is performed by an Ally it cannot be stopped."""
    def has_power(self, p): return 'goku_calm' not in p.tf

    def power(self, p, opp):
        if once_turn(p, 'goku_calm'):
            return p.attack(opp, power=GOKU_CALM)
        return False

    def after_hit(self, p, opp, card, removed):
        if card is GOKU_CALM:
            p.cb['ally_unstop'] = True


@mp('Goku', 'Dashing')
class GokuL4(Behavior):
    """POWER: search Life Deck, discard pile or Banished Zone for an Ally and place it into play at its highest power stage. Choose one of your
    Allies in play: for the rest of combat it may act whatever the MP's stage and its attacks deal +4 life cards."""
    def has_power(self, p): return 'goku_dash' not in p.tf

    def power(self, p, opp):
        if not once_turn(p, 'goku_dash'):
            return False
        got = search_ally(p, ('deck', 'discard', 'banished'), 10)
        pick = best_attacker(p) or (max(my_allies(p), key=ally_value) if my_allies(p) else None)
        if pick is not None:
            p.cb['ally_free'].add(pick.name)
            p.cb['ally_life'][pick.name] = p.cb['ally_life'].get(pick.name, 0) + 4
        return got is not None or pick is not None


# ---- Ally-related cards --------------------------------------------------------------------------------------------
def _heroic_plan(p, o, c):
    if search_ally(p, ('deck',), 3) is None:
        fetch_from_deck(p, lambda x: x.ctype == 'Drill', 'drill')


def _battle_readiness(p, o, c):
    search_ally(p, ('deck',), 3)
    search_ally(p, ('discard',), 3)


def _goku_search(p, o, c):
    if search_ally(p, ('deck',), 3) is None:
        fetch_from_deck(p, lambda x: x.ctype == 'Drill', 'drill')
    p.rejuv(2)                                                     # "Search your discard pile for 2 cards and Rejuvenate them"


def _goku_discharge_hit(p, o, c, removed):
    x = find_in(p.discard, lambda y: y.ctype == 'Ally' and ally_model(y) and not any(a.name == y.name for a in p.allies))
    if x is not None and my_allies(p):
        a = min(my_allies(p), key=ally_value)
        p.leave_play(a, 'deck')
        for b in p.behaviors():
            b.on_ally_rejuvenated(p)
        p.discard.remove(x)
        p.put_ally(x, 3, True)


def _kiss(p, o, c):
    a = best_attacker(p)
    if a is not None:
        p.cb['ally_free'].add(a.name)
        p.cb['ally_kiss'].add(a.name)


_x('Heroic Plan', use=_heroic_plan)
_x('Blue Battle Readiness', use=_battle_readiness)
_x('Blue Taming Technique', use=lambda p, o, c: search_ally(p, ('deck',), 4))         # the optional Styled-Setup discard is not modelled
_x("Goku's Search", use=_goku_search)
_x('Overpowering Attack', immediate=lambda p, o, c: search_ally(p, ('deck', 'discard'), 5))
_x('Blue Arrest', hit=lambda p, o, c, r: (search_ally(p, ('deck',), 3, played=True), _arrest_hit(p, o, c, r)))   # immediate (Rejuvenate 3 Allies from the discard pile) is the shared _arrest_now above; each hit finds nothing for the other deck's Allies
_x('Blue Discharge', hit=lambda p, o, c, r: _goku_discharge_hit(p, o, c, r) if p.mp_name == 'Goku' else _discharge_hit(p, o, c, r), can_attack=lambda p, o, c: bool(p.allies))
_x('Blue Kiss', use=_kiss, can_use=lambda p, o, c: best_attacker(p) is not None)
_x('Blue Defensive Stance', defend=lambda p, atk, x, c: p.raise_anger(1))              # "raise or lower a player's anger 1": the AI raises its own
_x('Ally Tenshinhan', hit=lambda p, o, c, r: p.draw(1))


def _yamcha_hit(p, o, c, r):
    """HIT: shuffle a Setup, Drill or Ally in play into its owner's Life Deck (the AI picks an opponent's Drill, then Setup, then Ally). UNVERIFIED target choice."""
    for zone in (o.drills, o.setups):
        if zone:
            x = zone.pop()
            o.deck.append(x)
            o.rng.shuffle(o.deck)
            return
    if my_allies(o):
        o.leave_play(max(my_allies(o), key=ally_value), 'deck')


_x('Ally Yamcha', hit=_yamcha_hit)
_x('Goku Calm', immediate=_calm_search)
# Saiyan Overhead Kick: "Search your Life Deck or discard pile for a Saiyan Ally and place it into play at 5 stages above 0."
# UNVERIFIED: only Vegeta counts as a Saiyan Ally here (Rulebook 3.0 lists Vegeta among the Saiyan personalities; Chaozu, Tenshinhan, Yamcha, Chichi, Piccolo are not on it).
SAIYAN_ALLIES = ('Vegeta',)
_x('Saiyan Overhead Kick', immediate=lambda p, o, c: search_ally(p, ('deck', 'discard'), 5, names=SAIYAN_ALLIES))


@passive('Blue Lifting Drill')
class BlueLiftingDrill(Behavior):
    """[Continuous]: your attacks +1 life card; whenever one of your attacks is stopped, lower your opponent's anger 1."""
    def life_bonus(self, p, card, opp): return 1
    def on_stopped(self, p, opp, card): opp.lower_anger(1)


@passive('Blue Transportation Drill')
class BlueTransportationDrill(Behavior):
    """[Instant]: when an Ally enters play under your control during combat and it is the only Ally you control, draw a card."""
    def on_ally_entered(self, p, card):
        if p.game.in_combat and len(p.allies) == 1:
            p.draw(1)


CARD_VALUE.update({"Dr. Wheelo's History": 6, 'Black Confinement': 5, 'Black Invitation': 4, "Dr. Wheelo's Revival": 3, 'Black Taunt': 4})
NEVER_PLAY = {"Time Is A Warrior's Tool", 'Villainous Energy Sphere', 'Villainous Visage', "Piccolo's Weighted Clothing",
              'Heroic Energy Sphere'}



# =================================================================================================================
# Raditz (Set 2 levels). Engine: every Setup or Drill that enters play (planning, search, "place into play") feeds Level 2 and Level 4.
# NOT MODELLED / simplified (the text-only parts): Raditz's Offensive Guard's "banish from hand to stop an attack"; Orange Crashing Drill's
# "leaving play" trigger; Red Integration's "revealed from your hand" trigger; Raditz's Dirty Tactics.
# =================================================================================================================
RADITZ_L1 = synthetic('True Saiyan', 'POWER: [Attack] Physical attack. DAMAGE: 1 life card.')


def _drill_or_setup(c): return c.ctype in ('Drill', 'Setup')


@mp('Raditz', 'True Saiyan')
class RaditzL1(Behavior):
    """POWER: Physical attack, 1 life card. Reveal the top 2 cards of your Life Deck, put 1 into your hand and banish the other. Raise your anger 1 level.
    UNVERIFIED: the reveal and the anger happen even if the attack is stopped (the printed text lists them after DAMAGE)."""
    def has_power(self, p): return True

    def power(self, p, opp):
        if not once_turn(p, 'raditz1'):
            return False
        p.attack(opp, power=RADITZ_L1)
        if len(p.deck) >= 2:
            top = [p.deck.pop(0), p.deck.pop(0)]
            top.sort(key=p.value)
            p.banished.append(top[0])          # banished from your own Life Deck (it shortens your deck)
            p.hand.append(top[1])
        p.raise_anger(1)
        return True


@mp('Raditz', 'Confident')
class RaditzL2(Behavior):
    """[Continuous] Whenever one of your Setups or Drills enters play, destroy the top card of your opponent's Life Deck.
    Whenever one of your Setups or Drills enters play during combat, raise your anger 1 level."""
    def on_enters_play(self, p, opp, card):
        p.destroy_opp(1)
        p.log(f'    ({p.label}: {card.name} enters play -> Confident destroys 1' + (', +1 anger)' if p.game.in_combat else ')'))
        if p.game.in_combat:
            p.raise_anger(1)


@mp('Raditz', 'Angered')
class RaditzL3(Behavior):
    """[Instant] POWER: Use when entering combat. Your opponent discards a random card from his hand. UNVERIFIED: used when attacking and when defending, once per turn."""
    def entering_combat(self, p, opp, defender):
        if opp.hand and once_turn(p, 'raditz3'):
            c = opp.hand.pop(p.rng.randrange(len(opp.hand)))
            opp.discard.append(c)
            opp.note_discard(c)
            p.log(f'  {p.label}: Angered -> {opp.label} discards {c.name} at random')


def _rejuv_choice(p):
    """Rejuvenate a chosen card from the discard pile (the most valuable one goes to the bottom of the Life Deck)."""
    if p.discard:
        c = max(p.discard, key=p.value)
        p.discard.remove(c)
        p.deck.append(c)
        if p.game.in_combat:
            for b in p.behaviors():
                b.on_rejuvenate(p)


@mp('Raditz', 'Triumphant')
class RaditzL4(Behavior):
    """[Continuous] Whenever one of your Setups or Drills enters play, choose a card in your discard pile and Rejuvenate it.
    The first time you use a critical damage effect each combat, you may search your Life Deck or discard pile for a Setup or Drill and place it into play."""
    def on_enters_play(self, p, opp, card):
        p.log(f'    ({p.label}: {card.name} enters play -> Triumphant Rejuvenates a card)')
        _rejuv_choice(p)

    def on_crit_effect(self, p):
        if not once(p, 'raditz4'):
            return
        for zone in (p.deck, p.discard):
            c = find_in(zone, lambda x: x.ctype == 'Drill') or find_in(zone, lambda x: x.ctype == 'Setup')
            if c is not None:
                zone.remove(c)
                if zone is p.deck:
                    p.rng.shuffle(p.deck)
                enter_play(p, c)
                return


def _attach_og(p, o, c):
    """Raditz's Offensive Guard: attaches to the MP after the attack (UNVERIFIED: also if the attack is stopped). One copy attached at a time."""
    if not any(x.name == "Raditz's Offensive Guard" for x in p.attached):
        p.attached.append(c)
        c.keep = True


@passive("Raditz's Offensive Guard")
class OffensiveGuard(Behavior):
    """Attached: once per combat, as an action, place a Setup or Drill from your hand into play. Banished when you change levels (advancing is modelled)."""
    def has_power(self, p): return any(_drill_or_setup(x) for x in p.hand)

    def power(self, p, opp):
        c = find_in(p.hand, lambda x: x.ctype == 'Drill') or find_in(p.hand, lambda x: x.ctype == 'Setup')
        if c is None or not once(p, 'og_place'):
            return False
        p.hand.remove(c)
        p.log(f'  {p.label}: Offensive Guard places {c.name} into play')
        enter_play(p, c)
        return True

    def on_advance(self, p):
        og = find_in(p.attached, lambda x: x.name == "Raditz's Offensive Guard")
        if og is not None:
            p.attached.remove(og)
            p.banished.append(og)


_x("Raditz's Offensive Guard", immediate=_attach_og)


# ---- Orange Drills / Setups that put Drills into play, and Drill passives used by the Raditz decks ----------------
def _styled_drill(p): return lambda c: c.ctype == 'Drill' and c.style is not None and c.style == p.styled()


def _celebration(p, o, c): fetch_from_deck(p, _styled_drill(p), 'drill')


def _encouragement(p, o, c):
    x = find_in(reversed(p.discard), _styled_drill(p))
    if x is not None:
        p.discard.remove(x)
        enter_play(p, x)
    if p.cb['changed']:
        fetch_from_deck(p, _styled_drill(p), 'drill')


def _integration(p, o, c):
    d = find_in(p.deck, lambda x: x.ctype == 'Drill')
    if d is not None:
        fetch_from_deck(p, lambda x: x is d, 'drill')
    else:
        _drill_from_discard(p)


_x('Orange Celebration', use=_celebration, can_use=lambda p, o, c: find_in(p.deck, _styled_drill(p)) is not None)
_x('Orange Encouragement', use=_encouragement)
_x('Red Integration', use=_integration,
   can_use=lambda p, o, c: find_in(p.deck, lambda x: x.ctype == 'Drill') is not None or find_in(p.discard, lambda x: x.ctype == 'Drill') is not None)
def _freezing_beam(p, o, c):
    x = find_in(reversed(p.discard), lambda d: d.ctype == 'Drill') or find_in(reversed(p.banished), lambda d: d.ctype == 'Drill')
    if x is not None:
        (p.discard if x in p.discard else p.banished).remove(x)
        enter_play(p, x)


_x('Red Freezing Beam', immediate=_freezing_beam)
_x('Red Chop', base_stage=lambda p, o, c: 3 + p.anger)          # DAMAGE: 3 +X stages, X = your current anger level
_x('Orange Refocus', defend=lambda p, atk, x, c: _drill_from_discard(p))
_x('Orange Crashing Drill', enters=lambda p, o, c: p.destroy_opp(1) if p.game.in_combat else None)   # leaving-play trigger not modelled


@passive('Orange Torching Drill')
class TorchingDrill(Behavior):
    def on_enters_play(self, p, opp, card):
        if card.ctype == 'Drill' and p.game.in_combat:
            p.destroy_opp(1)


def _styled_phys(p, card): return card.phys and card.style is not None and card.style == p.styled() and card.card_id.split(':')[0] != 'synthetic'


@passive('Orange Disaster Drill')
class DisasterDrill(Behavior):
    """Your Styled physical attacks deal +2 stages of damage and gain 'Raise your anger 1 level.'"""
    def stage_bonus(self, p, card, opp): return 2 if _styled_phys(p, card) else 0

    def on_play(self, p, opp, card):
        if _styled_phys(p, card):
            p.raise_anger(1)


@passive('Orange Joint Restraint Drill')
class JointRestraintDrill(Behavior):
    def stage_bonus(self, p, card, opp): return 2 if card.phys else 0


@passive('Orange Crying Drill')
class CryingDrill(Behavior):
    """POWER: Raise your anger 1 level (once per turn per Drill name: Orange Retribution's rule). The shuffle-away action is not modelled."""
    def has_power(self, p): return True

    def power(self, p, opp):
        if once_turn(p, 'crying'):
            p.raise_anger(1)
            return True
        return False


@passive('Saiyan Analysis Drill')
class AnalysisDrill(Behavior):
    """You need 1 less anger to advance a personality level. UNVERIFIED: copies do not stack (modelled as 'need 4' once) and Level 4 MPPV is unchanged."""
    def anger_needed(self, p): return 4 if p.level < 4 else None


@passive('Saiyan Unleashing Drill')
class UnleashingDrill(Behavior):
    """Your energy attacks deal +2 stages of damage and your physical attacks deal +1 life card."""
    def stage_bonus(self, p, card, opp): return 2 if card.energy else 0
    def life_bonus(self, p, card, opp): return 1 if card.phys else 0


@passive('Saiyan Protection Drill')
class ProtectionDrill(Behavior):
    """Your opponent's attacks deal -1 stage and -1 life card of damage. (The Endurance-Rejuvenate clause is not modelled.)"""
    def incoming_life(self, p, card, atk): return -1
    def incoming_stage(self, p, card, atk): return -1


@passive('Saiyan Anguish Drill')
class AnguishDrill(Behavior):
    """POWER: if your MP is level 2 or lower, raise your anger 1 level. (The 'opponent passed' bonus and the banish-a-Setup action are not modelled.)"""
    def has_power(self, p): return p.level <= 2

    def power(self, p, opp):
        if p.level <= 2 and once_turn(p, 'anguish'):
            p.raise_anger(1)
            return True
        return False
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


# Red
_x('Red Right Blast', immediate=lambda p, o, c: p.cb.update(rj_draw=True))                      # next Rejuvenate by either player this combat: draw 1 (engine: Player.rejuv)
_x('Red Static Shot', immediate=lambda p, o, c: p.cb.update(noend=True))                        # UNVERIFIED simplification: applies to all my attacks, not only Styled ones
_x('Red Repel', defend=lambda p, atk, x, c: atk.lose_stages(1))
# Nail
_x("Nail's Dashing Attacking", hit=_dashing_attacking_hit)
# Namekian
_x('Namekian Chop', hit=lambda p, o, c, r: p.raise_anger(len(p.balls)) if p.balls else None)    # HIT: raise anger X, X = Dragon Balls you control
_x('Namekian Energy Guard', defend=_energy_guard)
_x('Namekian Crushing Slam', immediate=_crushing_slam)


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
    if x.ctype == 'Ally' and ally_model(x):          # modelled Allies attack from play, never from the hand
        return False
    ex = CARD_EXTRA.get(x.name, {})
    gate, can_attack = ex.get('can_use'), ex.get('can_attack')       # can_use: cards that are also Events/Setups; can_attack: attack cards with a condition
    return x.cost <= a.stage and (gate is None or gate(a, d, x)) and (can_attack is None or can_attack(a, d, x))


def choose_action(a, d):
    """One action for player `a` against `d`. Returns True if something was done (False = pass)."""
    for b in a.behaviors():
        if b.power(a, d):
            return True
    if ally_attack(a, d):
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
