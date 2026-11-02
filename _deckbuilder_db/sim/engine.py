"""Rules engine for the toy simulator. See sim/README.md for what is and is not modelled.

Rules implemented from Rulebook 3.0 (work/crd/rulebook.txt): turn order, Attack Table, stage damage overflowing into
Life Cards, Endurance, critical damage and its three effects, anger and levelling, Dragon Balls (bottom of deck, DBV),
Rejuvenate, destroy/banish, discard to one card, defender draws 3 on combat. Card-specific behaviour lives in behaviors.py.
"""
import random
from . import behaviors as B
from .cardmodel import Card, records_by_id

AT = {'A': [1, 0, 0, 0, 0, 0], 'B': [2, 1, 0, 0, 0, 0], 'C': [3, 2, 1, 0, 0, 0], 'D': [4, 3, 2, 1, 0, 0],
      'E': [5, 4, 3, 2, 1, 0], 'F': [6, 5, 4, 3, 2, 1]}
BRACKETS = 'ABCDEF'


def bracket(power):
    for i, top in enumerate((1000, 10000, 100000, 500000, 1500000)):
        if power < top:
            return i
    return 5


class Level:
    def __init__(self, rec):
        self.card_id, self.name, self.pur, self.track = rec['card_id'], rec['subtitle'], rec['pur'], rec['power_stages']
        self.text = rec.get('text_current') or rec.get('text_as_printed') or ''


class Spec:
    """Everything needed to build one player. Built by loader.py from a deck code."""

    def __init__(self, name, mp_name, level_ids, mastery_name, card_ids, no_mppv=False):
        self.name, self.mp_name, self.level_ids, self.mastery_name = name, mp_name, level_ids, mastery_name
        self.card_ids = card_ids          # list of card_id, one entry per copy (60)
        self.no_mppv = no_mppv


class Result:
    def __init__(self, winner, reason, turns, logs):
        self.winner, self.reason, self.turns, self.logs = winner, reason, turns, logs


class Player:
    def __init__(self, game, label, spec, rng):
        recs = records_by_id()
        self.game, self.label, self.spec, self.rng = game, label, spec, rng
        self.mp_name, self.mastery = spec.mp_name, spec.mastery_name
        self.levels = [Level(recs[i]) for i in spec.level_ids]
        self.deck = [Card(recs[i]) for i in spec.card_ids]
        rng.shuffle(self.deck)
        self.level, self.stage, self.anger = 1, 5, 0
        self.hand, self.discard, self.banished = [], [], []
        self.balls, self.drills, self.setups, self.attached = [], [], [], []
        self.allies = []                  # Allies in play (only Allies the AI knows how to use are ever played; see behaviors.plan_allies)
        self.skip = 0
        self.won = self.lost = False
        self.win_reason = None
        self.lockanger = False
        self.endure_count = 0
        self.opp = None
        self.tf, self.cb = {}, {}
        self.reset_combat()

    # ---- state helpers -----------------------------------------------------------------------------------
    def reset_combat(self):
        self.cb = dict(used=set(), stopall=False, crit_all=False, attacked_hand=False, changed=False, discarded=False,
                       gained=False, raised=False, destroyed_nonstyled=False, destroy_bonus=0, next_destroy_bonus=0,
                       next_life=0, next_free=False, reduce_life=0, reduce_stage=0, noend=False, burning=False,
                       noevents=False, nonstyled_lock=False, ball_search=False, searched=False, armed_discard=False,
                       sword_played=False, next_unprev=False, unprev_all=False, set0_on_change=False, attacks=0)

    def log(self, msg):
        self.game.log(msg)

    @property
    def lv(self):
        return self.levels[self.level - 1]

    def behaviors(self):
        out = [B.mp_behavior(self.mp_name, self.lv.name), B.mastery_behavior(self.mastery)]
        for c in self.drills + self.balls + self.setups + self.attached:
            b = B.CARD_PASSIVE.get(c.name)
            if b:
                out.append(b)
        for c in self.allies:
            b = B.ALLY_PASSIVE.get((c.name, c.rec.get('subtitle')))
            if b:
                out.append(b)
        return [b for b in out if b is not None]

    def power(self):
        return 0 if self.stage <= 0 else self.lv.track[10 - min(self.stage, 10)]

    def styled(self):
        return B.style_of(self.mp_name, self.mastery)

    # ---- cards moving -------------------------------------------------------------------------------------
    def draw(self, n=1):
        for _ in range(n):
            if not self.deck:
                self.lost = True
                return
            self.hand.append(self.deck.pop(0))

    def rejuv(self, n, in_combat=True, pred=None):
        """Rejuvenate n cards: discard pile -> bottom of the Life Deck. pred picks which cards (best value first); default is the top of the discard pile.
        In combat the amount goes through `rejuv_amount` (Lord Slug Level 3 doubling) and `on_rejuvenate` fires only if a card actually moved."""
        if n > 0 and in_combat:
            for b in self.behaviors():
                n = b.rejuv_amount(self, n)
        moved = 0
        for _ in range(n):
            src = [x for x in self.discard if pred(x)] if pred else self.discard
            if not src:
                break
            c = max(src, key=self.value) if pred else src[-1]
            self.discard.remove(c)
            self.deck.append(c)
            moved += 1
        if moved and in_combat:
            for b in self.behaviors():
                b.on_rejuvenate(self)

    def rejuv_ally(self, card, zone):
        """Rejuvenate one specific Ally: it leaves `zone` (hand, discard pile, Banished Zone or play) for the bottom of the Life Deck."""
        zone.remove(card)
        self.deck.append(card)
        for b in self.behaviors():
            b.on_ally_rejuvenated(self)
            b.on_rejuvenate(self)

    def lose_card(self, c, how):
        """A card left the top of the Life Deck. how: 'destroy' | 'damage' | 'banish'. Returns True if it counts."""
        if c.ctype == 'Dragon Ball':
            self.deck.append(c)
            return False
        if how == 'destroy' and self.opp is not None and c.style != self.styled():   # 'Styled' relative to the victim's deck (unverified)
            self.opp.cb['destroyed_nonstyled'] = True
        (self.banished if how == 'banish' else self.discard).append(c)
        extra = B.CARD_LEAVE_DECK.get(c.name)
        if extra and how in ('destroy', 'damage'):
            extra(self, c)
        return True

    def mill(self, n, how='destroy'):
        done, guard = 0, 0
        while done < n and self.deck and guard < 300:
            guard += 1
            if self.lose_card(self.deck.pop(0), how):
                done += 1
            elif all(x.ctype == 'Dragon Ball' for x in self.deck):
                self.lost = True
                break
        if not self.deck:
            self.lost = True
            self.log(f'  *** {self.label} Life Deck is empty')
        return done

    def take_life(self, n, ignore_end=False):
        removed, guard = 0, 0
        while n > 0 and self.deck and guard < 300:
            guard += 1
            c = self.deck.pop(0)
            if c.ctype == 'Dragon Ball':
                self.deck.append(c)
                if all(x.ctype == 'Dragon Ball' for x in self.deck):
                    self.lost = True
                    break
                continue
            n -= 1
            removed += 1
            if c.endurance and not ignore_end and not (self.opp and self.opp.cb['noend']):
                self.banished.append(c)
                n -= c.endurance
                self.endure_count += 1
            else:
                self.lose_card(c, 'damage')
        if not self.deck:
            self.lost = True
            self.log(f'  *** {self.label} Life Deck is empty')
        return removed

    def take_stages(self, d):
        if d <= 0:
            return 0
        self.stage -= d
        if self.stage < 0:
            left, self.stage = -self.stage, 0
            return self.take_life(left)
        return 0

    def lose_stages(self, n, floor0=False):
        """This MP loses n stages. At power level 0 the rest comes off the Life Deck (Rulebook 3.0) unless the card says 'to a minimum of 0'."""
        if n <= 0:
            return 0
        if floor0:
            self.stage = max(0, self.stage - n)
            return 0
        return self.take_stages(n)

    def gain_stages(self, n):
        self.cb['gained'] = True
        self.stage = min(10, self.stage + n)
        for b in self.behaviors():
            b.on_gain_stages(self, n)

    # ---- anger and levels ---------------------------------------------------------------------------------
    def anger_needed(self):
        need = 5
        for b in self.behaviors():
            r = b.anger_needed(self)
            if r is not None:
                need = min(need, r)
        if self.level < 4:      # Masteries that change the anger needed to ADVANCE a level (not for MPPV on Level 4)
            for b in self.behaviors():
                need = max(1, need + b.adv_anger_delta(self))
            if self.opp is not None:
                for b in self.opp.behaviors():
                    r = b.opp_adv_anger_min(self.opp)
                    if r:
                        need = max(need, r)
        return need

    def raise_anger(self, n, in_combat=True):
        if n <= 0 or self.lockanger:
            return
        for b in self.behaviors():
            n = b.anger_modify(self, n, in_combat)
        self.cb['raised'] = True
        self.anger += n
        for b in self.behaviors():
            b.on_anger_raised(self)
        if self.anger >= self.anger_needed():
            self.advance_by_anger()

    def lower_anger(self, n):
        self.anger = max(0, self.anger - n)

    def can_mppv(self):
        return (not self.spec.no_mppv) and all(b.can_mppv(self) for b in self.behaviors())

    def advance_by_anger(self):
        if self.level == 4:
            if self.can_mppv():
                self.won, self.win_reason = True, 'MPPV'
                self.log(f'  *** {self.label} wins by MPPV (5 anger on Level 4)')
            self.anger = 0
            self.stage = 10
            return
        self.anger = 0
        self.change_level(+1)

    def change_level(self, d):
        old = self.level
        self.level = max(1, min(4, self.level + d))
        if self.level == old:
            return
        self.stage = 10 if d > 0 else 5
        self.cb['changed'] = True
        if self.opp is not None and self.opp.cb['set0_on_change']:      # Nappa's Energized Charge
            self.stage = 0
        keep = any(b.keep_drills(self, old) for b in B.behaviors_of_level(self, old))
        if not keep:
            self.discard.extend(self.drills)
            self.drills = []
        if d > 0:
            for b in self.behaviors():
                b.on_advance(self)
        self.log(f'  [{self.label} -> L{self.level} {self.lv.name}]')

    def crit_effect(self):
        o = self.opp
        if o.balls and not any(b.protect_balls(o) for b in o.behaviors()):
            self.balls.append(o.balls.pop())
            self.log(f'    ({self.label} captures a Dragon Ball)')
            self.check_dbv()
        else:
            o.lower_anger(1)
        for b in self.behaviors():
            b.on_crit_effect(self)

    def check_dbv(self):
        if len(self.balls) >= 7 and len({c.name.split(' Dragon Ball')[0] for c in self.balls}) == 1:
            self.won, self.win_reason = True, 'DBV'
            self.log(f'  *** {self.label} wins by Dragon Ball Victory')

    # ---- destroy / discard effects ----------------------------------------------------------------------------
    def destroy_opp(self, n, noamp=False):
        o = self.opp
        if not noamp:
            n += self.cb['destroy_bonus'] + self.cb['next_destroy_bonus']
            self.cb['next_destroy_bonus'] = 0
            for b in self.behaviors():
                n = b.destroy_amount(self, n)
        got = o.mill(n)
        if not noamp:
            for b in self.behaviors():
                b.after_destroy(self, got)
        return got

    def forced_discard(self):
        """This player discards a card from hand by an opponent's effect (own choice)."""
        if not self.hand:
            return None
        pref = [x for x in self.hand if x.name in B.CARD_DISCARD_TRIGGER]
        c = pref[0] if pref else sorted(self.hand, key=self.value)[0]
        self.hand.remove(c)
        self.discard.append(c)
        self.note_discard(c)
        return c

    def note_discard(self, c):
        self.game.last_discarder = self            # lets a behavior tell whose card was discarded (Black Viewing Drill)
        self.cb['discarded'] = True
        self.opp.cb['discarded'] = True
        trig = B.CARD_DISCARD_TRIGGER.get(c.name)
        if trig:
            trig(self, c)
        for pl in (self, self.opp):
            for b in pl.behaviors():
                b.on_card_discarded(pl)

    # ---- value used by the simple AI -------------------------------------------------------------------------
    def value(self, c):
        v = (c.at or 0) * 2 + c.stage_flat + c.life * 2 + c.anger_self + (3 if c.is_def else 0) + (2 if c.crit_now else 0)
        v += B.CARD_VALUE.get(c.name, 0)
        if c.anger_self and self.level < 4 and self.anger + c.anger_self >= self.anger_needed():
            v += 8
        return v

    # ---- attacks ----------------------------------------------------------------------------------------------
    def at_value(self, opp):
        return AT[BRACKETS[bracket(self.power())]][bracket(opp.power())]

    def attack(self, opp, card=None, power=None):
        c = power or card
        cost = c.cost
        if self.cb['next_free'] and card is not None and card.style and card.style == self.styled():
            cost, self.cb['next_free'] = 0, False
        if cost > self.stage:
            return False
        self.stage -= cost
        self.cb['attacks'] += 1          # attacks performed this combat (True Power: 'use only if you have not performed an attack this combat')
        if card is not None:
            self.hand.remove(card)
            self.cb['attacked_hand'] = True
        if c.sword and card is not None:
            self.cb['sword_played'] = True
        for b in self.behaviors():
            b.on_play(self, opp, c)
        extra = B.CARD_EXTRA.get(c.name, {})
        self.raise_anger(c.anger_self)
        for _ in range(c.crit_now):
            self.crit_effect()
        opp.lower_anger(c.anger_opp)
        if c.gain:
            self.gain_stages(c.gain)
        if c.opp_lose:
            opp.lose_stages(c.opp_lose, c.opp_lose_floor)
        if extra.get('immediate'):
            extra['immediate'](self, opp, c)
        unstop = c.unstoppable or any(b.unstoppable(self, c) for b in self.behaviors())
        stopped = True if self.cb['stopall'] else (False if unstop else opp.defend(self, c))
        if stopped:
            self.log(f'  {self.label}: {c.name} -> stopped')
            for b in self.behaviors():
                b.on_stopped(self, opp, c)
            for b in opp.behaviors():
                b.on_stop_made(opp, self, c)
            self._finish(card, c)
            return True
        ds, life = 0, c.life
        if c.at is not None or c.stage_flat:
            ds = (self.at_value(opp) + c.at) if c.at is not None else c.stage_flat
        if extra.get('base_stage'):
            ds = extra['base_stage'](self, opp, c)
        if ds and c.at is None:
            for b in self.behaviors():
                ds *= b.stage_scale(self, c, opp)
        if c.life_at:
            life = self.at_value(opp) + c.life
        life = max(0, life + B.life_adjust(self, opp, c))
        if ds or c.at is not None:
            ds += sum(b.stage_bonus(self, c, opp) for b in self.behaviors())
        if life or c.life_at:
            life += sum(b.life_bonus(self, c, opp) for b in self.behaviors())
            life += self.cb['next_life']
            self.cb['next_life'] = 0
        for b in opp.behaviors():
            if life:
                life += b.incoming_life(opp, c, self)
            if ds:
                ds += b.incoming_stage(opp, c, self)
        life = max(0, life - opp.cb['reduce_life']) if life else 0
        ds = max(0, ds - opp.cb['reduce_stage']) if ds else 0
        pre = opp.cb.pop('prevent_once', None)          # Blue Overcharge: prevents N life cards and N stages of THIS attack only
        if pre:
            life, ds = max(0, life - pre[0]), max(0, ds - pre[1])
        opp.endure_count = 0
        ign = c.unprev or self.cb['next_unprev'] or self.cb['unprev_all'] or any(b.unprevented(self, c, opp) for b in self.behaviors())
        self.cb['next_unprev'] = False
        removed = opp.take_stages(ds) if ds else 0
        removed += opp.take_life(life, ignore_end=ign) if life else 0
        self.log(f'  {self.label}: {c.name} -> {ds} stage, {life} life ({removed} removed) | {opp.label} stage {opp.stage} deck {len(opp.deck)}')
        for x in [x for x in opp.hand if B.CARD_EXTRA.get(x.name, {}).get('on_damaged')]:
            if removed:
                B.CARD_EXTRA[x.name]['on_damaged'](opp, self, x, removed)
        thr = max([5] + [t for t in (b.crit_threshold(opp) for b in opp.behaviors()) if t])
        own = [t for t in (b.own_crit_threshold(self) for b in self.behaviors()) if t]
        if own:
            thr = min(thr, min(own))
        if (removed >= thr or self.cb['crit_all']) and (ds or life or c.at is not None):
            self.lockanger = False
            self.crit_effect()
            for b in self.behaviors():
                b.on_crit_damage(self, opp)
        self.raise_anger(c.anger_hit)
        opp.lower_anger(c.anger_opp_hit)
        if c.crit_hit:
            self.crit_effect()
        if c.rej:
            self.rejuv(c.rej)
        if c.rej_hit:
            self.rejuv(c.rej_hit)
        if extra.get('hit'):
            extra['hit'](self, opp, c, removed)
        self._finish(card, c)
        for b in self.behaviors():
            b.after_hit(self, opp, c, removed)
        return True

    def _finish(self, card, c):
        if card is not None and getattr(card, 'keep', False):
            card.keep = False            # attached to the MP / returned to the Life Deck by its own effect
            return
        if card is not None:
            (self.banished if c.banish_after else self.discard).append(card)

    # ---- defending ----------------------------------------------------------------------------------------------
    def defend(self, atk, c):
        kind = 'p' if c.phys else 'e'
        for b in self.behaviors():
            if b.defend_power(self, atk, c, kind):
                self.log(f'    ({self.label} stops it with an MP/Mastery power)')
                return True
        opts = [x for x in self.hand + self.setups if x.is_def and kind in x.stops]      # a Setup in play is activated and discarded like an Event
        if self.cb['nonstyled_lock']:
            opts = [x for x in opts if x.style == self.styled()]
        big = (c.at or 0) + c.stage_flat >= 2 or c.life >= 2 or c.life_at
        if not opts and big and not self.cb['nonstyled_lock']:
            part = [x for x in self.hand + self.setups if x.prevent and x.ctype in ('Event', 'Setup')]
            if part and 'prevent_once' not in self.cb:
                x = part[0]
                (self.setups if x in self.setups else self.hand).remove(x)
                self.cb['prevent_once'] = x.prevent
                if x.draw:
                    self.draw(1)
                (self.banished if x.banish_after else self.discard).append(x)
                self.log(f'    ({self.label} prevents {x.prevent[0]} life cards / {x.prevent[1]} stages with {x.name})')
            return False
        if not opts:
            return False
        if not big:
            return False
        x = sorted(opts, key=lambda z: (z.name == "Time Is A Warrior's Tool", -z.endurance))[0]
        (self.setups if x in self.setups else self.hand).remove(x)
        self.raise_anger(x.anger_self)
        atk.lower_anger(x.anger_opp)
        if x.opp_lose:
            atk.lose_stages(x.opp_lose, x.opp_lose_floor)
        if x.gain:
            self.gain_stages(x.gain)
        if x.rej:
            self.rejuv(x.rej)
        extra = B.CARD_EXTRA.get(x.name, {})
        if extra.get('defend'):
            extra['defend'](self, atk, x, c)
        if getattr(x, 'keep', False):
            x.keep = False            # returned to the Life Deck by its own effect (Namekian Protective Posture)
        else:
            (self.banished if x.banish_after else self.discard).append(x)
        self.log(f'    ({self.label} defends with {x.name})')
        return True


class Game:
    def __init__(self, spec_a, spec_b, seed=0, first=0):
        self.rng = random.Random(seed)
        self.logs = []
        self.last_discarder = None
        a, b = Player(self, spec_a.name, spec_a, self.rng), Player(self, spec_b.name, spec_b, self.rng)
        if a.label == b.label:
            a.label, b.label = a.label + ' (A)', b.label + ' (B)'
        a.opp, b.opp = b, a
        self.players = [a, b]
        self.first = first
        self.in_combat = False          # True while a combat is being resolved (used by 'enters play during combat' effects)
        for p in self.players:
            for beh in p.behaviors():
                beh.on_game_start(p)

    def log(self, msg):
        self.logs.append(msg)

    def run(self, max_turns=60):
        order = [self.players[self.first], self.players[1 - self.first]]
        for n in range(1, max_turns + 1):
            p, o = order[(n - 1) % 2], order[n % 2]
            self.turn(p, o, n)
            for q in self.players:
                if q.won:
                    return Result(q.label, q.win_reason, n, self.logs)
                if q.lost:
                    return Result(q.opp.label, 'Survival', n, self.logs)
        return Result('draw', 'turn limit', max_turns, self.logs)

    # ---- turn -------------------------------------------------------------------------------------------------
    def turn(self, p, o, n):
        p.tf, o.tf = {}, {}
        p.draw(3)
        if p.lost:
            return
        self.planning(p, o)
        self.log(f'T{n} {p.label}: hand {len(p.hand)} L{p.level} anger {p.anger} stage {p.stage} deck {len(p.deck)} | '
                 f'{o.label} L{o.level} anger {o.anger} stage {o.stage} deck {len(o.deck)}')
        declared = self.wants_combat(p, o)
        if declared:
            self.combat(p, o)
        for q in (p, o):
            while len(q.hand) > 1:
                q.hand.sort(key=q.value)
                q.discard.append(q.hand.pop(0))
        if not declared:
            p.rejuv(1, in_combat=False)

    def planning(self, p, o):
        while True:
            todo = [x for x in p.hand if x.ctype == 'Dragon Ball' and not any(b.name == x.name for b in p.balls)]
            if not todo:
                break
            c = todo[0]
            p.hand.remove(c)
            p.balls.append(c)
            ex = B.CARD_EXTRA.get(c.name, {})
            if ex.get('immediate'):
                ex['immediate'](p, o, c)
            p.log(f'  {p.label}: plays {c.name}')
            for b in p.behaviors():
                b.on_ball_entered(p)
            p.check_dbv()
        for c in [x for x in p.hand if x.ctype == 'Drill']:
            if c not in p.hand:
                continue
            p.hand.remove(c)
            for b in p.behaviors():
                b.on_drill_played(p, o, c)
            p.drills.append(c)
            ex = B.CARD_EXTRA.get(c.name, {})
            if ex.get('enters'):
                ex['enters'](p, o, c)
            for b in p.behaviors():
                b.on_enters_play(p, o, c)
        for c in [x for x in p.hand if x.ctype == 'Setup']:
            if c in p.hand:
                p.hand.remove(c)
                p.setups.append(c)
                for b in p.behaviors():
                    b.on_enters_play(p, o, c)
        B.plan_allies(p, o)
        pur = p.lv.pur + sum(b.pur_bonus(p) for b in p.behaviors())
        p.stage = min(10, p.stage + pur)

    def wants_combat(self, p, o):
        if any(x.is_atk and x.cost <= p.stage for x in p.hand):
            return True
        if p.setups or any(b.has_power(p) for b in p.behaviors()):
            return True
        return any(x.ctype == 'Event' and (x.crit_now or x.anger_self or x.rej or x.gain or x.draw) for x in p.hand)

    def combat(self, p, o):
        p.reset_combat()
        o.reset_combat()
        self.in_combat = True
        for b in p.behaviors():
            b.entering_combat(p, o, False)
        for s in [x for x in p.setups if x.instant_entering]:
            B.use_setup(p, o, s)
        for b in o.behaviors():
            b.entering_combat(o, p, True)
        o.draw(3)
        passes, actor, other, guard = 0, p, o, 0
        while passes < 2 and guard < 60 and not any(q.lost or q.won for q in self.players):
            guard += 1
            if actor.skip > 0:
                actor.skip -= 1
                actor, other = other, actor
                continue
            passes = 0 if B.choose_action(actor, other) else passes + 1
            actor, other = other, actor
        for q in (p, o):
            for b in q.behaviors():
                b.end_of_combat(q, q.opp)
        self.in_combat = False
