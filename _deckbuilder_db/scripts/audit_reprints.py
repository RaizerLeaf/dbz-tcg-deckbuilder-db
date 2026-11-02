"""Audit cards that share a name across Sets 1-7 (reprints, redesigned layouts, promos, different cards with one name).

    python scripts/audit_reprints.py            print the report (the committed copy is REPRINT_AUDIT.md)

The deck-code app knows each card by ONE printing (the first). `deckcode.app_printing` must therefore map every printing of the SAME card to one
code and keep DIFFERENT cards that share a name apart. This script lists, for every name with more than one printing:
  - how deckcode groups it (one code, or several codes) and whether that matches the data;
  - how each later printing's rules text differs from the first printing's (layout only / gender-neutral wording / real text change);
  - fields that disagree between printings (type, limit, Named, alignment, restrictions) and printings that carry text_current while others do not.
"""
import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deckcode as dc  # noqa: E402

NEUTRAL = {'her', 'or', 'it', 'their'}          # "his" -> "his or her" (Set 7 gender-neutral reprint wording)
ICONS = {'attack', 'defense', 'continuous', 'instant', 'power', 'damage', 'hit'}


def words(t):
    t = re.sub(r'\(Most Recent Printing\)', '', t or '', flags=re.I).lower().replace('\n', ' ')
    t = re.sub(r"[^a-z0-9' +\-]", ' ', t)
    return collections.Counter(t.split())


def classify(first, later):
    a, b = words(first), words(later)
    if a == b:
        return 'layout only'
    only_a, only_b = a - b, b - a
    rest = set(only_a) | set(only_b)
    if rest <= NEUTRAL | ICONS | {'his', 'him'}:
        return 'wording (his -> his or her / icon label)'
    return 'TEXT CHANGE'


def main():
    groups = collections.defaultdict(list)
    for c in dc.CARDS:
        s = c['set_number']
        if s and s <= 7 and '_RST' not in c['card_id'] and dc.ctype(c) != 'Main Personality':
            groups[c['card_name']].append(c)
    multi = {k: v for k, v in groups.items() if len(v) > 1}
    print(f'{len(groups)} card names in Sets 1-7 (excluding Main Personalities); {len(multi)} have more than one printing.\n')

    print('## 1. How deckcode groups same-name cards')
    for name, v in sorted(multi.items()):
        codes = sorted({dc.card_code(dc.BY_ID[dc.app_printing(c['card_id'])]) for c in v})
        if len(codes) > 1:
            kinds = {dc.ctype(c) for c in v}
            subs = sorted({c.get('subtitle') or '-' for c in v})
            print(f'- {name} ({"/".join(sorted(kinds))}): {len(codes)} separate cards, app codes {codes}; subtitles {subs}')
    print('  Allies are separated by SUBTITLE (CRD: "same name, but different subtitles"); every other card is one card per name.\n')

    print('## 2. Later printings whose text differs from the first printing')
    cnt = collections.Counter()
    rows = []
    for name, v in sorted(multi.items()):
        by_card = collections.defaultdict(list)
        for c in v:
            by_card[dc.app_printing(c['card_id'])].append(c)
        for first_id, prints in by_card.items():
            first = dc.BY_ID[first_id]
            for c in prints:
                if c['card_id'] == first_id:
                    continue
                k = classify(first['text_as_printed'], c['text_as_printed'])
                cnt[k] += 1
                if k != 'layout only':
                    rows.append((name, dc.card_code(first), dc.card_code(c), c['collection'], k))
    print('  ' + ', '.join(f'{k}: {n}' for k, n in cnt.items()))
    for r in rows:
        print(f'- {r[0]}: first {r[1]} vs {r[2]} ({r[3]}): {r[4]}')

    print('\n## 3. Fields that disagree between printings of one card')
    for fld, f in (('type', dc.ctype), ('style', lambda c: c.get('style')), ('alignment', lambda c: c.get('alignment')),
                   ('restrictions', lambda c: tuple(sorted(c.get('restrictions') or []))), ('is_named', lambda c: c.get('is_named')),
                   ('limit_per_deck', lambda c: c.get('limit_per_deck')), ('frozen', lambda c: c.get('frozen'))):
        for name, v in sorted(multi.items()):
            by_card = collections.defaultdict(list)
            for c in v:
                by_card[dc.app_printing(c['card_id'])].append(c)
            for prints in by_card.values():
                vals = collections.defaultdict(list)
                for c in prints:
                    vals[f(c)].append(dc.card_code(c))
                if len(vals) > 1:
                    print(f'- {fld}: {name}: {dict(vals)}')

    print('\n## 4. Text the deck builder reads (text_current if present) that differs between printings of one card')
    for name, v in sorted(multi.items()):
        by_card = collections.defaultdict(list)
        for c in v:
            by_card[dc.app_printing(c['card_id'])].append(c)
        for prints in by_card.values():
            texts = {tuple(sorted(words(dc.text(c)).elements())) for c in prints}
            partial = any(c.get('text_current') for c in prints) and not all(c.get('text_current') for c in prints)
            if len(texts) > 1 or partial:
                tag = 'text differs' if len(texts) > 1 else 'only some printings carry text_current (same words)'
                print(f"- {name}: {tag}: " + ', '.join(f"{dc.card_code(c)}[{'cur' if c.get('text_current') else 'printed'}]" for c in prints))


if __name__ == '__main__':
    main()
