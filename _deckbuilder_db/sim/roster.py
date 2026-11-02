"""The test-deck roster: at most 10 decks that new decks are playtested against.

    python -m sim roster                      show the roster (and the retired decks)
    python -m sim roster add decks/x.txt      evaluate a finished deck; it joins if it ranks in the top 10, and the lowest-ranked deck is retired
    python -m sim roster rebuild              re-rank every deck in decks/ and sim/decks/ from scratch
    python -m sim playtest decks/x.txt [-n 20]   play a deck against every roster deck (20 games each by default, 50 at most)

Ranking = win rate over a round robin of the roster plus the candidate (30 games per pair, fixed seeds, first player alternating),
so the same inputs always give the same ranking. It is the simulator's opinion, not a measure of real strength. `roster.json` is
regenerable (`roster rebuild`); if two chats change it at once, resolve the conflict by re-running `roster rebuild`.
"""
import collections
import itertools
import json
from pathlib import Path

from . import behaviors as B
from .engine import Game
from .loader import load
from .cardmodel import records_by_id

DB = Path(__file__).resolve().parent.parent
ROSTER_FILE = Path(__file__).resolve().parent / 'roster.json'
MAX_ROSTER = 10
ROUND_ROBIN_GAMES = 30
PLAYTEST_DEFAULT, PLAYTEST_MAX = 20, 50
DECK_DIRS = ('decks', 'sim/decks')


def rel(path):
    p = Path(path)
    p = p if p.is_absolute() else (Path.cwd() / p)
    try:
        return p.resolve().relative_to(DB).as_posix()
    except ValueError:
        return p.as_posix()


def unmodelled(spec):
    """MP levels / Mastery the simulator ignores for this deck (a deck with any of these cannot be ranked fairly)."""
    recs = records_by_id()
    out = []
    for lv, i in enumerate(spec.level_ids, 1):
        if (spec.mp_name, recs[i]['subtitle']) not in B.MP_BEH:
            out.append(f"L{lv} {recs[i]['subtitle']}")
    if spec.mastery_name not in B.MASTERY_BEH:
        out.append(f'Mastery {spec.mastery_name}')
    return out


def read():
    if ROSTER_FILE.exists():
        return json.loads(ROSTER_FILE.read_text(encoding='utf-8'))
    return {'max': MAX_ROSTER, 'games_per_pair': ROUND_ROBIN_GAMES, 'decks': [], 'retired': []}


def write(r):
    ROSTER_FILE.write_text(json.dumps(r, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def evaluate(entries, games=ROUND_ROBIN_GAMES, seed=1000):
    """entries: [(key, spec)] -> {key: {'wins','games','pct','win_turns'}} from a round robin."""
    stat = {k: collections.Counter() for k, _ in entries}
    turns = {k: [] for k, _ in entries}
    for (ka, sa), (kb, sb) in itertools.combinations(entries, 2):
        for i in range(games):
            g = Game(sa, sb, seed=seed + i, first=i % 2)
            r = g.run()
            stat[ka]['games'] += 1
            stat[kb]['games'] += 1
            if r.winner == 'draw':
                continue
            w = ka if r.winner == g.players[0].label else kb
            stat[w]['wins'] += 1
            turns[w].append(r.turns)
    return {k: {'wins': stat[k]['wins'], 'games': stat[k]['games'],
                'pct': round(100 * stat[k]['wins'] / max(1, stat[k]['games']), 1),
                'win_turns': round(sum(turns[k]) / len(turns[k]), 1) if turns[k] else None} for k, _ in entries}


def _entry(key, spec, ev):
    return {'file': key, 'name': spec.name, 'mp': spec.mp_name, 'mastery': spec.mastery_name, 'win_pct': ev['pct'], 'avg_turn_of_wins': ev['win_turns']}


def rank_and_cut(entries, games):
    """Evaluate, rank by win rate (ties by file name), keep the top MAX_ROSTER. Returns (kept, dropped, evals)."""
    ev = evaluate(entries, games)
    specs = dict(entries)
    order = sorted(ev, key=lambda k: (-ev[k]['pct'], k))
    kept = [_entry(k, specs[k], ev[k]) for k in order[:MAX_ROSTER]]
    dropped = [_entry(k, specs[k], ev[k]) for k in order[MAX_ROSTER:]]
    return kept, dropped, ev


def rebuild(games=ROUND_ROBIN_GAMES):
    files = sorted(p.relative_to(DB).as_posix() for d in DECK_DIRS for p in (DB / d).glob('*.txt'))
    entries, skipped = [], []
    for f in files:
        spec = load(str(DB / f))
        bad = unmodelled(spec)
        if bad:
            skipped.append({'file': f, 'unmodelled': bad})
        else:
            entries.append((f, spec))
    kept, dropped, _ = rank_and_cut(entries, games)
    r = {'max': MAX_ROSTER, 'games_per_pair': games, 'decks': kept, 'retired': dropped, 'skipped_unmodelled': skipped}
    write(r)
    return r


def add(path, games=ROUND_ROBIN_GAMES):
    """Evaluate a finished deck against the roster. Returns a dict describing what happened."""
    key = rel(path)
    spec = load(str(DB / key))
    bad = unmodelled(spec)
    if bad:
        return {'status': 'refused', 'reason': 'these parts are NOT MODELLED, so the deck cannot be ranked fairly: ' + ', '.join(bad)
                + '. Add them to sim/behaviors.py first (sim/README.md, "Adding things").'}
    r = read()
    current = [d['file'] for d in r['decks']]
    entries = [(f, load(str(DB / f))) for f in current if f != key and (DB / f).exists()]
    entries.append((key, spec))
    kept, dropped, ev = rank_and_cut(entries, games)
    kept_files = [d['file'] for d in kept]
    evicted = [d for d in dropped if d['file'] != key]
    status = 'added' if key in kept_files else 'not added'
    r['decks'] = kept
    r['retired'] = [d for d in r.get('retired', []) if d['file'] not in kept_files and d['file'] != key] + dropped
    r['retired'] = list({d['file']: d for d in r['retired']}.values())
    r['games_per_pair'] = games
    write(r)
    return {'status': status, 'rank': (kept_files.index(key) + 1) if key in kept_files else None, 'win_pct': ev[key]['pct'], 'evicted': evicted,
            'roster_size': len(kept)}


def playtest(path, n=PLAYTEST_DEFAULT, allow_unmodelled=False):
    """Play a deck against every roster deck. Returns rows; raises ValueError for too many games or an unmodelled deck."""
    if n > PLAYTEST_MAX:
        raise ValueError(f'playtest is capped at {PLAYTEST_MAX} games per opponent (asked for {n}); large batches are for matchup testing: python -m sim run A B -n 1000')
    key = rel(path)
    spec = load(str(DB / key))
    bad = unmodelled(spec)
    if bad and not allow_unmodelled:
        raise ValueError('not modelled by the simulator: ' + ', '.join(bad) + '. Add them to sim/behaviors.py first (sim/README.md, "Adding things"), '
                         'or pass --allow-unmodelled if the owner agreed to a text-only check.')
    rows = []
    for d in read()['decks']:
        if d['file'] == key or not (DB / d['file']).exists():
            continue
        opp = load(str(DB / d['file']))
        wins, turns, how = 0, [], collections.Counter()
        for i in range(n):
            g = Game(spec, opp, seed=2000 + i, first=i % 2)
            r = g.run()
            if r.winner == g.players[0].label:
                wins += 1
                turns.append(r.turns)
                how['wins by ' + r.reason] += 1
            elif r.winner != 'draw':
                how['loses to ' + r.reason] += 1
        rows.append({'opponent': d['file'], 'opp_name': opp.name, 'opp_pct': d['win_pct'], 'wins': wins, 'games': n,
                     'avg_turn_of_wins': round(sum(turns) / len(turns), 1) if turns else None, 'how': dict(how)})
    return {'deck': spec.name, 'unmodelled': bad, 'rows': rows}
