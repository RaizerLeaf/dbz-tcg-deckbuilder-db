"""Card model: parses the numbers the engine needs out of a card's text, and reports which sentences are modelled.

The parser only understands the common building blocks (damage, stage cost, anger, stops, Endurance, Rejuvenate, draw,
stage gain, "use a critical damage effect"). Anything else is either hand-coded in behaviors.py (CARD_EXTRA etc.) or
reported as unmodelled by `coverage()`.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

DB = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def all_records():
    return json.loads((DB / 'cards.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def records_by_id():
    return {c['card_id']: c for c in all_records()}


def text_of(rec):
    return (rec.get('text_current') or rec.get('text_as_printed') or '').replace('\n', ' ')


def ctype_of(rec):
    return rec.get('card_type_current') or rec['card_type']


def _amt(s, pat):
    tot = 0
    for m in re.finditer(pat + r'(?: (\d+))?', s):
        tot += int(m[1]) if m[1] else 1
    return tot


def synthetic(name, text, ctype='Main Personality', style=None):
    """A Card built from a bare text, used for MP/Mastery Power attacks."""
    return Card({'card_id': 'synthetic:' + name, 'card_name': name, 'card_type': ctype, 'style': style,
                 'text_current': text, 'text_as_printed': text, 'is_named': False})


class Card:
    """One physical card in a deck. Never shared between decks or games."""

    def __init__(self, rec):
        t = text_of(rec)
        self.rec = rec
        self.card_id = rec['card_id']
        self.name = rec['card_name']
        self.text = t
        self.ctype = ctype_of(rec)
        self.style = rec.get('style')
        head, _, hit = t.partition('HIT:')
        self.head, self.hit = head, hit
        m = re.search(r'ENDURANCE (\d+)', t)
        self.endurance = int(m[1]) if m else 0
        self.is_def = '[Defense]' in t and ('Stops' in t or bool(re.search(r'Prevent all damage from an? (?:physical|energy) attack', t)))
        self.is_atk = '[Attack]' in t
        low = t.lower()
        self.phys = self.is_atk and 'physical attack' in low
        self.energy = self.is_atk and 'energy attack' in low
        if self.is_atk and not (self.phys or self.energy):
            self.energy = self.ctype == 'Energy Combat'
            self.phys = not self.energy
        parts_dmg = re.split(r'DAMAGE:', head, maxsplit=1, flags=re.I)
        s = parts_dmg[1] if len(parts_dmg) > 1 else ''
        self.at = None
        self.stage_flat = 0
        self.life = 0
        self.life_at = False
        m = re.match(r'\s*AT ?\+ ?(\d+) stages', s)
        if m: self.at = int(m[1])
        elif re.match(r'\s*AT stages', s): self.at = 0
        m = re.match(r'\s*(\d+) stages', s)
        if m: self.stage_flat = int(m[1])
        m = re.match(r'\s*(\d+) life cards?', s)
        if m: self.life = int(m[1])
        m = re.match(r'\s*AT ?\+ ?(\d+) life cards', s)
        if m: self.life_at, self.life = True, int(m[1])
        if re.match(r'\s*3 stages \+AT life', s): self.stage_flat, self.life_at, self.life = 3, True, 0
        m = re.match(r'\s*AT ?\+ ?\d+ stages and \+(\d+) life cards', s)
        if m: self.life = int(m[1])          # e.g. Saiyan Direct Strike: AT +3 stages and +2 life cards
        m = re.search(r'DAMAGE: (\d+) - X life cards', t)
        if m: self.life = int(m[1])          # Krillin Ready For Battle; the X part is handled in behaviors
        m = re.search(r'costing (\d+) stages?', t)
        self.cost = int(m[1]) if m else 0
        self.anger_self = _amt(head, r'[Rr]aise your anger')
        self.anger_hit = _amt(hit, r'[Rr]aise your anger')
        self.anger_opp = _amt(head, r"[Ll]ower your opponent's anger")
        self.anger_opp_hit = _amt(hit, r"[Ll]ower your opponent's anger")
        self.stops = set()
        if self.is_def:
            m = re.search(r'Stops an? ([^.]*?)attack', t)
            kinds = m[1].lower() if m else ''
            if 'physical' in kinds: self.stops.add('p')
            if 'energy' in kinds: self.stops.add('e')
            if not m and 'Stops an attack' in t: self.stops = {'p', 'e'}
            m2 = re.search(r'Prevent all damage from an? (physical|energy) attack', t)
            if m2: self.stops.add('p' if m2[1] == 'physical' else 'e')      # approximated as a stop
        m = re.search(r'(?:MP gains|[Gg]ain) (\d+) stages', head)
        self.gain = int(m[1]) if m else 0
        self.crit_now = len(re.findall(r'[Uu]se a critical damage effect', head))
        self.crit_hit = 'critical damage effect' in hit
        self.sword = 'Sword' in self.name or "considered to have \"Sword\"" in t
        self.named = bool(rec.get('is_named'))   # includes cards only 'considered Named for your effects'
        self.opp_lose, self.opp_lose_floor = 0, False
        for sent in sentences(head):
            if sent.startswith(('If', 'Whenever', 'After', 'You may', '(')):
                continue
            m = (re.search(r"[Yy]our opponent(?:'s MP)? loses? (\d+) stages", sent) or re.search(r"[Aa]ll of your opponent's personalities lose (\d+) stages", sent)
                 or re.search(r'That personality loses (\d+) stages', sent))
            if m:
                self.opp_lose += int(m[1])
                self.opp_lose_floor = self.opp_lose_floor or 'minimum of 0' in sent
        m = re.search(r'Rejuvenate (\d+)', head)
        self.rej = int(m[1]) if m else 0
        self.draw = 'Draw a card' in head
        self.banish_after = 'Banish after use' in t
        self.instant_entering = 'when entering combat' in low
        self.unstoppable = any('cannot be stopped' in x and not x.startswith(('If', 'You may', 'Unless')) for x in sentences(head))
        self.unprev = any('cannot be prevented' in x and not x.startswith(('If', 'You may', 'Unless')) and 'this combat' not in x
                          for x in sentences(head))

    def __repr__(self):
        return self.name


# ---- coverage -------------------------------------------------------------------------------------------------
_SKIP = re.compile(r'^\(?(?:Limit \d per deck|Banish after use|(?:Heroes|Villains) only|Villains only|Heroes only)[^)]*\)?\.?$', re.I)
_PARSED = [
    r'^\[?(?:Attack|Defense|Continuous|Instant)\]?:?$', r'^(?:POWER:?)$', r'^ENDURANCE \d+\.?$',
    r'(?:Physical|Energy) [Aa]ttack', r'DAMAGE:?', r'costing \d+ stages?', r'[Rr]aise your anger',
    r"[Ll]ower your opponent's anger", r'Stops an? (?:physical|energy)', r'Stops a physical or energy',
    r'(?:MP gains|[Gg]ain) \d+ stages', r'Rejuvenate \d+', r'Draw a card', r'[Uu]se a critical damage effect',
    r"(?:opponent(?:'s MP)?|personalities|personality) loses? \d+ stages|lose \d+ stages", r'Prevent all damage from an? (?:physical|energy) attack',
    r'^\(?Banish after use', r'^HIT:?$',
]
_PARSED_RE = re.compile('|'.join(_PARSED))


def sentences(text):
    t = re.sub(r'\s+', ' ', text).strip()
    parts = re.split(r'(?<=[.!?\)])\s+', t)
    return [p.strip() for p in parts if p.strip()]


def coverage(card, hand_coded_names):
    """-> (parsed, hand_coded, unmodelled) lists of sentences for one card."""
    parsed, hand, un = [], [], []
    for s in sentences(card.text):
        if _SKIP.match(s) or _PARSED_RE.search(s):
            parsed.append(s)
        elif card.name in hand_coded_names:
            hand.append(s)
        else:
            un.append(s)
    return parsed, hand, un
