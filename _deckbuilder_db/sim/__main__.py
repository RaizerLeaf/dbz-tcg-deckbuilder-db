"""Command line: python -m sim <command> ...   (run from _deckbuilder_db/)

  run A B [-n 1000] [--seed 1] [--no-mppv-a] [--no-mppv-b]   many games, alternating who goes first
  bo3 A B [--seed 1]                                        a best-of-3 with the full play log
  game A B [--seed 1] [--first a|b]                         one game with the full play log
  coverage CODE                                             which parts of the deck the simulator models
  playtest DECK [-n 20]                                     play a deck against every roster deck (20 games each, 50 at most): for deck building
  roster [add FILE | rebuild]                               the test-deck roster (best 25 decks, one version per MP + Mastery); `add` ranks a finished deck into it
A and B are deck codes or paths to decks/*.txt files.
"""
import argparse
import collections
from . import behaviors as B
from .cardmodel import Card, coverage
from .engine import Game
from .loader import load
from . import roster as R


def play(a, b, seed, first):
    g = Game(a, b, seed=seed, first=first)
    return g.run(), g


def cmd_run(args):
    a, b = load(args.a, args.no_mppv_a), load(args.b, args.no_mppv_b)
    res = collections.Counter()
    how = collections.Counter()
    byfirst = collections.Counter()
    turns = 0
    for i in range(args.n):
        first = i % 2
        r, g = play(a, b, args.seed + i, first)
        key = 'draw' if r.winner == 'draw' else ('A' if r.winner == g.players[0].label else 'B')
        res[key] += 1
        how[(key, r.reason)] += 1
        byfirst[(['A', 'B'][first], key)] += 1
        turns += r.turns
    n = args.n
    print(f'{a.name}  vs  {b.name}   ({n} games, first player alternates)')
    print(f'  A wins {100 * res["A"] / n:.1f}%   B wins {100 * res["B"] / n:.1f}%   draws {100 * res["draw"] / n:.1f}%   average {turns / n:.1f} turns total')
    for (k, why), v in sorted(how.items()):
        print(f'  {k} by {why}: {v}')
    print(f'  A wins going first {byfirst[("A", "A")]} / {n // 2 + n % 2}, B wins going first {byfirst[("B", "B")]} / {n // 2}')


def cmd_game(args):
    a, b = load(args.a, args.no_mppv_a), load(args.b, args.no_mppv_b)
    first = 0 if args.first == 'a' else 1
    r, g = play(a, b, args.seed, first)
    print('\n'.join(r.logs))
    print(f'==> {r.winner} wins by {r.reason} on turn {r.turns}')


def cmd_bo3(args):
    a, b = load(args.a, args.no_mppv_a), load(args.b, args.no_mppv_b)
    score = {0: 0, 1: 0}
    first, g_no = 0, 0
    while max(score.values()) < 2 and g_no < 3:
        r, g = play(a, b, args.seed + g_no, first)
        g_no += 1
        print(f'===== GAME {g_no}: {g.players[first].label} goes first =====')
        print('\n'.join(r.logs))
        winner = 0 if r.winner == g.players[0].label else 1
        score[winner] += 1
        print(f'==> {r.winner} wins by {r.reason} on turn {r.turns} (series {a.name} {score[0]} - {score[1]} {b.name})\n')
        first = 1 - winner


def cmd_coverage(args):
    from .cardmodel import records_by_id
    s = load(args.a)
    recs = records_by_id()
    hand = set(B.CARD_EXTRA) | set(B.CARD_PASSIVE) | set(B.CARD_LEAVE_DECK) | set(B.CARD_DISCARD_TRIGGER)
    copies = collections.Counter(s.card_ids)
    tot = collections.Counter()
    unm = []
    for cid, n in sorted(copies.items(), key=lambda kv: recs[kv[0]]['card_name']):
        c = Card(recs[cid])
        if c.ctype == 'Ally' and c.name in B.MODELLED_ALLIES:
            if c.rec.get('subtitle') == 'Unrelenting':     # Allies only act when the MP is at most 1 stage above 0; the AI never does that
                unm.append((c.name, n, ['Unrelenting: POWER attack in play is never used (Allies act only when the MP is at most 1 stage above 0)']))
                tot['unmodelled'] += n
            else:
                tot['hand'] += n * len(coverage(c, {c.name})[1] or [0])
            continue
        if c.ctype == 'Ally':
            unm.append((c.name, n, ['Allies are not simulated (never played)']))
            tot['unmodelled'] += n
            continue
        parsed, hc, un = coverage(c, hand)
        tot['parsed'] += n * len(parsed)
        tot['hand'] += n * len(hc)
        tot['unmodelled'] += n * len(un)
        if un:
            unm.append((c.name, n, un))
    print(f'{s.name}: MP {s.mp_name}, Mastery {s.mastery_name}')
    for lv, i in enumerate(s.level_ids, 1):
        name = recs[i]['subtitle']
        ok = (s.mp_name, name) in B.MP_BEH
        print(f'  L{lv} {name:18} {"modelled" if ok else "NOT MODELLED (text ignored)"}')
    print(f'  Mastery {s.mastery_name}: {"modelled" if s.mastery_name in B.MASTERY_BEH else "NOT MODELLED (text ignored)"}')
    allc = sum(tot.values()) or 1
    print(f'  card sentences (counting copies): {tot["parsed"]} parsed, {tot["hand"]} hand-coded, {tot["unmodelled"]} unmodelled '
          f'-> {100 * (tot["parsed"] + tot["hand"]) / allc:.0f}% modelled')
    print('  unmodelled card text:')
    for name, n, sents in unm:
        print(f'    {n}x {name}: ' + ' | '.join(sents))


def cmd_playtest(args):
    try:
        res = R.playtest(args.a, args.n, args.allow_unmodelled)
    except ValueError as e:
        raise SystemExit('playtest refused: ' + str(e))
    print(f"{res['deck']} against the roster ({args.n} games each, first player alternates)")
    if res['unmodelled']:
        print('  WARNING, NOT MODELLED (text ignored): ' + ', '.join(res['unmodelled']))
    tot_w = tot_g = 0
    for r in res['rows']:
        tot_w += r['wins']
        tot_g += r['games']
        how = ', '.join(f'{k} {v}' for k, v in sorted(r['how'].items()))
        t = f"{r['avg_turn_of_wins']}" if r['avg_turn_of_wins'] is not None else '-'
        print(f"  vs {r['opp_name']:<26} ({r['opponent']}): wins {r['wins']:>2}/{r['games']}  avg turn of its wins {t:>5}   [{how}]")
    if not res['rows']:
        print('  the roster is empty or only contains this deck: run `python -m sim roster rebuild`')
        return
    worst = min(res['rows'], key=lambda r: r['wins'])
    print(f'  overall {100 * tot_w / tot_g:.0f}% over {tot_g} games. Read a play log of the worst matchup:')
    print(f"    python -m sim game {args.a} {worst['opponent']} --seed 1")


def cmd_roster(args):
    if args.action == 'rebuild':
        r = R.rebuild()
    elif args.action == 'add':
        if not args.file:
            raise SystemExit('usage: python -m sim roster add decks/<name>.txt')
        out = R.add(args.file)
        if out['status'] == 'refused':
            raise SystemExit('roster add refused: ' + out['reason'])
        print(f"{args.file}: {out['status']}" + (f" at rank {out['rank']} of {out['roster_size']}" if out['rank'] else '') + f" (win rate {out['win_pct']}% in the round robin)"
              + ('  [the simulator or card data changed: everyone was re-ranked]' if out['re_ranked_everything'] else ''))
        for f in out['replaced']:
            print(f"  replaces an older version of the same deck ({out['family']}): {f}")
        for d in out['evicted']:
            print(f"  retired from the roster: {d['file']} ({d['win_pct']}%)")
        r = R.read()
    else:
        r = R.read()
    print(f"Test-deck roster (top {r['max']} by round-robin win rate; {r['games_per_pair']} games per pair)")
    for i, d in enumerate(r['decks'], 1):
        t = d['avg_turn_of_wins'] if d['avg_turn_of_wins'] is not None else '-'
        print(f"  {i:>2}. {d['win_pct']:>5}%  turn {t:>5}  {d['file']:<36} {d['mp']} / {d['mastery']}")
    for d in r.get('retired', []):
        print(f"  retired: {d['win_pct']:>5}%  {d['file']}")
    for d in r.get('superseded', []):
        print(f"  older version (same MP + Mastery): {d['win_pct']:>5}%  {d['file']}  <- replaced by {d['superseded_by']}")
    for d in r.get('skipped_unmodelled', []):
        print(f"  not rankable (NOT MODELLED): {d['file']}: {', '.join(d['unmodelled'])}")


def main():
    ap = argparse.ArgumentParser(prog='python -m sim', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name, fn in (('run', cmd_run), ('bo3', cmd_bo3), ('game', cmd_game), ('coverage', cmd_coverage)):
        sp = sub.add_parser(name)
        sp.add_argument('a')
        if name != 'coverage':
            sp.add_argument('b')
            sp.add_argument('--no-mppv-a', action='store_true')
            sp.add_argument('--no-mppv-b', action='store_true')
            sp.add_argument('--seed', type=int, default=1)
        if name == 'run':
            sp.add_argument('-n', type=int, default=1000)
        if name == 'game':
            sp.add_argument('--first', choices=['a', 'b'], default='a')
        sp.set_defaults(fn=fn)
    sp = sub.add_parser('playtest')
    sp.add_argument('a')
    sp.add_argument('-n', type=int, default=R.PLAYTEST_DEFAULT)
    sp.add_argument('--allow-unmodelled', action='store_true')
    sp.set_defaults(fn=cmd_playtest)
    sp = sub.add_parser('roster')
    sp.add_argument('action', nargs='?', default='show', choices=['show', 'add', 'rebuild'])
    sp.add_argument('file', nargs='?')
    sp.set_defaults(fn=cmd_roster)
    args = ap.parse_args()
    args.fn(args)


main()
