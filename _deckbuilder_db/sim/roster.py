"""The test-deck roster: the best decks built so far, which new decks are playtested against (at most MAX_ROSTER, 25 at first).

    python -m sim roster                      show the roster (and the retired decks)
    python -m sim roster add decks/x.txt      rank a finished deck against the roster; it joins if it is in the top MAX_ROSTER and the lowest-ranked deck is retired
    python -m sim roster rebuild              re-rank every deck in decks/ and sim/decks/ from scratch
    python -m sim playtest decks/x.txt [-n 20]   play a deck against every roster deck (20 games each by default, 50 at most)

Only ONE version of a deck counts: a deck's family is its MP + Mastery (Orange Trunks V3/V4/V5 are one family). Only the best-ranked version of
each family stays on the roster; the others are listed as `superseded`. Decks of the same family do not play each other in the ranking.

Ranking = win rate over a round robin of the roster plus the candidate against decks of OTHER families (30 games per pair, fixed seeds, first player
alternating), so the same inputs always give the same ranking. Pair results are cached in roster.json (keyed by the decks' codes and a hash of the simulator and card data),
so `add` only plays the new deck against the existing roster; if the simulator or card data changed, everything is re-ranked. It is the simulator's
opinion, not a measure of real strength. roster.json is regenerable (`roster rebuild`); if two chats change it at once, resolve the conflict by re-running it.
"""
import collections
import hashlib
import json
from pathlib import Path

from . import behaviors as B
from .engine import Game
from .loader import load, read_code
from .cardmodel import records_by_id

SIM = Path(__file__).resolve().parent
DB = SIM.parent
ROSTER_FILE = SIM / 'roster.json'
MAX_ROSTER = 25
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


def family(spec):
    """Versions of one deck share a family: same MP (and alignment) and same Mastery."""
    align = records_by_id()[spec.level_ids[0]].get('alignment') or ''
    return f'{spec.mp_name} ({align}) + {spec.mastery_name}'


def sim_hash():
    """Changes whenever the simulator code or the card data changes: cached results are then stale."""
    h = hashlib.sha1()
    for f in ('engine.py', 'behaviors.py', 'cardmodel.py', 'loader.py'):
        h.update((SIM / f).read_bytes())
    h.update((DB / 'cards.json').read_bytes())
    return h.hexdigest()[:12]


def deck_hash(key):
    return hashlib.sha1(read_code(str(DB / key)).encode()).hexdigest()[:10]


def read():
    if ROSTER_FILE.exists():
        return json.loads(ROSTER_FILE.read_text(encoding='utf-8'))
    return {'max': MAX_ROSTER, 'games_per_pair': ROUND_ROBIN_GAMES, 'decks': [], 'retired': [], 'pairs': {}}


def write(r):
    ROSTER_FILE.write_text(json.dumps(r, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def _pair(ka, sa, kb, sb, games, cache, sh):
    """Results of ka vs kb (ka < kb), from the cache when it is still valid. -> {'w': [wa, wb], 't': [turns_a, turns_b]}"""
    key = f'{ka}|{kb}'
    ha, hb = deck_hash(ka), deck_hash(kb)
    e = cache.get(key)
    if e and e['h'] == [ha, hb] and e['g'] == games and e['sh'] == sh:
        return e
    w, t = [0, 0], [0, 0]
    for i in range(games):
        g = Game(sa, sb, seed=1000 + i, first=i % 2)
        r = g.run()
        if r.winner == 'draw':
            continue
        idx = 0 if r.winner == g.players[0].label else 1
        w[idx] += 1
        t[idx] += r.turns
    e = {'h': [ha, hb], 'g': games, 'sh': sh, 'w': w, 't': t}
    cache[key] = e
    return e


def evaluate(entries, games=ROUND_ROBIN_GAMES, cache=None, sh=None):
    """entries: [(key, spec)] -> {key: {'wins','games','pct','win_turns'}} from a round robin (pair results cached in `cache`)."""
    cache = {} if cache is None else cache
    sh = sh or sim_hash()
    wins, played, tsum = collections.Counter(), collections.Counter(), collections.Counter()
    ordered = sorted(entries, key=lambda e: e[0])
    fam = {k: family(sp) for k, sp in entries}
    for i, (ka, sa) in enumerate(ordered):
        for kb, sb in ordered[i + 1:]:
            if fam[ka] == fam[kb]:
                continue                     # versions of the same deck do not play each other
            e = _pair(ka, sa, kb, sb, games, cache, sh)
            wins[ka] += e['w'][0]; wins[kb] += e['w'][1]
            tsum[ka] += e['t'][0]; tsum[kb] += e['t'][1]
            played[ka] += games; played[kb] += games
    return {k: {'wins': wins[k], 'games': played[k], 'pct': round(100 * wins[k] / max(1, played[k]), 1),
                'win_turns': round(tsum[k] / wins[k], 1) if wins[k] else None} for k, _ in entries}


def _entry(key, spec, ev):
    return {'file': key, 'name': spec.name, 'mp': spec.mp_name, 'mastery': spec.mastery_name, 'win_pct': ev['pct'], 'avg_turn_of_wins': ev['win_turns']}


def rank_and_cut(entries, games, cache, sh):
    """Evaluate, rank by win rate (ties: the later file name wins), keep the best version of each family, then the top MAX_ROSTER.
    Returns (kept, dropped, superseded, evals)."""
    ev = evaluate(entries, games, cache, sh)
    specs = dict(entries)
    order = sorted(sorted(ev, reverse=True), key=lambda k: -ev[k]['pct'])          # stable: ties keep descending file-name order
    best, superseded = {}, []
    for k in order:
        f = family(specs[k])
        if f in best:
            e = _entry(k, specs[k], ev[k])
            e['superseded_by'] = best[f]
            superseded.append(e)
        else:
            best[f] = k
    candidates = [k for k in order if best[family(specs[k])] == k]
    kept = [_entry(k, specs[k], ev[k]) for k in candidates[:MAX_ROSTER]]
    dropped = [_entry(k, specs[k], ev[k]) for k in candidates[MAX_ROSTER:]]
    return kept, dropped, superseded, ev


def _prune(cache, keep_files):
    return {k: v for k, v in cache.items() if all(f in keep_files for f in k.split('|'))}


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
    cache, sh = {}, sim_hash()
    kept, dropped, superseded, _ = rank_and_cut(entries, games, cache, sh)
    r = {'max': MAX_ROSTER, 'games_per_pair': games, 'sim_hash': sh, 'decks': kept, 'retired': dropped, 'superseded': superseded, 'skipped_unmodelled': skipped,
         'pairs': _prune(cache, {d['file'] for d in kept})}
    write(r)
    return r


def add(path, games=ROUND_ROBIN_GAMES):
    """Rank a finished deck against the roster. Returns a dict describing what happened."""
    key = rel(path)
    spec = load(str(DB / key))
    bad = unmodelled(spec)
    if bad:
        return {'status': 'refused', 'reason': 'these parts are NOT MODELLED, so the deck cannot be ranked fairly: ' + ', '.join(bad)
                + '. Add them to sim/behaviors.py first (sim/README.md, "Adding things").'}
    r = read()
    sh = sim_hash()
    stale = r.get('sim_hash') != sh or r.get('games_per_pair') != games
    cache = {} if stale else dict(r.get('pairs', {}))
    entries = [(d['file'], load(str(DB / d['file']))) for d in r['decks'] if d['file'] != key and (DB / d['file']).exists()]
    entries.append((key, spec))
    kept, dropped, superseded, ev = rank_and_cut(entries, games, cache, sh)
    kept_files = [d['file'] for d in kept]
    sup_files = {d['file']: d for d in superseded}
    evicted = [d for d in dropped if d['file'] != key]
    if key in kept_files:
        status = 'added'
    elif key in sup_files:
        status = 'not added (a better version is on the roster)'
    else:
        status = 'not added'
    replaced = [d['file'] for d in superseded if d.get('superseded_by') == key]
    retired = [d for d in r.get('retired', []) if d['file'] not in kept_files and d['file'] != key] + dropped
    old_sup = [d for d in r.get('superseded', []) if d['file'] not in kept_files and d['file'] not in sup_files and d['file'] != key]
    fam_best = {family(sp): k for k, sp in entries if k in kept_files}
    for d in old_sup:                       # point older versions at the version that is on the roster now
        if (DB / d['file']).exists():
            d['superseded_by'] = fam_best.get(family(load(str(DB / d['file']))), d.get('superseded_by'))
    r.update({'max': MAX_ROSTER, 'games_per_pair': games, 'sim_hash': sh, 'decks': kept, 'retired': list({d['file']: d for d in retired}.values()),
              'superseded': old_sup + superseded, 'pairs': _prune(cache, set(kept_files))})
    write(r)
    return {'status': status, 'rank': (kept_files.index(key) + 1) if key in kept_files else None, 'win_pct': ev[key]['pct'], 'evicted': evicted,
            'replaced': replaced, 'family': family(spec), 'roster_size': len(kept), 're_ranked_everything': stale}


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
