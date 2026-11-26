#!/usr/bin/env python3
"""Build the race analysis page (the Artifact the site imports) from lab data.

  python lab/page/make_page.py lab/data/2026-lusail-R.json lab/page/races/2026-lusail.json out.html

The race file (lab/page/races/<id>.json) holds only what a person chooses:
  name      "カタールGP"
  slug      "lusail-2026"            (the site's GP page: /gp/<slug>/)
  tz        3                        (local time offset from UTC, hours)
  news      {"climb": [title, path], "drop": [...], "sc": [...], "grid": [...]}   (DATA STORY and qualifying links; leave out if none)
  ev        [[lap, "text"], ...]     (marks on the charts; the script prints candidates from race control)
  presets   [["チームメイト", [["HAM","LEC"], ...]], ["注目の対決", [...]]]   (optional: made from the result if left out)
  story     [[title, text, "RUS", "gPos", "drop"], ...]   (optional: replaces the automatic DATA STORY cards)
  status    {"ALB": "dns"}           (optional: overrides; DNF/DNS/DSQ come from the OpenF1 result)
  updated   "2026-11-24T12:00:00+09:00"  (optional: only for data files fetched before the fetch time was saved)
Everything else comes from the data. The page has the same shape as before
(one <style>, markup in .wrap, one <script> with const D), so tools/gpdata_import.py on main still works.
"""
import datetime as dt, json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def ts(s):
    return dt.datetime.fromisoformat(s).timestamp()


def safety_cars(rc, N):
    """[[from, to, 'SC'|'VSC']] from race control messages."""
    out, open_ = [], {}
    for x in rc:
        m, n = (x.get('msg') or '').upper(), x.get('n')
        if n is None:
            continue
        kind = 'VSC' if 'VIRTUAL SAFETY CAR' in m else 'SC' if 'SAFETY CAR' in m else None
        if not kind:
            continue
        if 'DEPLOYED' in m and kind not in open_:
            open_[kind] = n
        elif kind in open_ and (('IN THIS LAP' in m) or ('ENDING' in m)):
            out.append([open_.pop(kind), n, kind])
    for kind, a in open_.items():
        out.append([a, N, kind])
    return sorted(out)


def main(data_path, race_path, out_path):
    d = json.load(open(data_path))
    R = json.load(open(race_path))
    names = json.load(open(os.path.join(HERE, 'drivers_2026.json')))['drivers']
    tpl = open(os.path.join(HERE, 'template.html')).read()

    res = {r['d']: r for r in d.get('result') or []}
    if not res:
        sys.exit('no session result in the data: run fetch_race.py again after the race is classified')
    laps = {}
    for l in d['laps']:
        laps.setdefault(l['d'], {})[l['n']] = l
    win = min(res.values(), key=lambda r: r['p'] or 99)['d']
    N = max(laps[win])
    abbrs = sorted({x['abbr'] for x in d['drivers']}, key=lambda a: (res.get(a, {}).get('p') or 99, -len([l for l in laps.get(a, {}).values() if l.get('t')]), a))
    info = {x['abbr']: x for x in d['drivers']}

    # grid = first position record (before the start)
    grid = {}
    for p in sorted(d['positions'], key=lambda p: p['at']):
        grid.setdefault(p['d'], p['p'])

    drivers = []
    for a in abbrs:
        nm = names.get(a)
        if not nm:
            print('WARNING: no Japanese name for', a, '- add it to lab/page/drivers_2026.json')
            nm = {'n': info[a]['name'].split()[-1].title(), 't': info[a]['team'], 'c': info[a].get('color') or '#888888'}
        drivers.append({'a': a, 'n': nm['n'], 't': nm['t'], 'c': nm['c'], 'f': res.get(a, {}).get('p'), 'g': grid.get(a)})

    # the time each car crossed the line at the end of each lap
    cross = {}
    for a in abbrs:
        ls, c = laps.get(a, {}), {}
        for n in range(1, N + 1):
            if n + 1 in ls and ls[n + 1].get('ds'):
                c[n] = ts(ls[n + 1]['ds'])
            elif n in ls and ls[n].get('ds') and ls[n].get('t'):
                c[n] = ts(ls[n]['ds']) + ls[n]['t']
        cross[a] = c
    G = {a: [None] * N for a in abbrs}
    X = {a: [None] * N for a in abbrs}
    for n in range(1, N + 1):
        r = sorted((c[n], a) for a, c in cross.items() if n in c)
        for k, (t, a) in enumerate(r):
            G[a][n - 1] = round(t - r[0][0], 1)
            X[a][n - 1] = k + 1
    # last lap: use the official gap where it agrees with the line-crossing time (penalised cars keep the on-track gap)
    for a in abbrs:
        g, o = res.get(a, {}).get('gap'), G[a][N - 1]
        if isinstance(g, (int, float)) and o is not None and abs(g - o) < 1.5:
            G[a][N - 1] = round(g, 1)

    scs = safety_cars(d.get('rc') or [], N)
    sc_main = next(([p[0], p[1]] for p in scs if p[2] == 'SC'), None)
    in_sc = lambda n: any(p[0] <= n <= p[1] + 1 for p in scs)
    pits = {a: [[p['n'], p['dur']] for p in d['pits'] if p['d'] == a] for a in abbrs}
    sec = {}
    for a in abbrs:
        pin = {p[0] for p in pits[a]}
        ok = [l for n, l in laps.get(a, {}).items() if n > 1 and l.get('t') and not l.get('pout') and n not in pin and not in_sc(n)]
        if not ok:
            continue
        m = st.median(l['t'] for l in ok)
        ok = [l for l in ok if l['t'] <= m * 1.05 and l.get('s1') and l.get('s2') and l.get('s3')]
        if len(ok) >= 5:
            sec[a] = [round(st.median(l[k] for l in ok), 3) for k in ('s1', 's2', 's3')]

    # qualifying (optional): <id>-Q.json beside the race file. [position, deciding time, 'Q3'|'Q2'|'Q1', gap to the best in that part]
    qpath = data_path.replace('-R.json', '-Q.json')
    Q = None
    if qpath != data_path and os.path.exists(qpath):
        Q = {}
        for r in json.load(open(qpath)).get('result') or []:
            q = r.get('q') if isinstance(r.get('q'), list) else [r.get('q')]
            gp = r.get('gap') if isinstance(r.get('gap'), list) else [r.get('gap')]
            k = max((i for i, v in enumerate(q) if v), default=None)
            if r['d'] in abbrs:
                g = gp[k] if k is not None and k < len(gp) else None
                Q[r['d']] = [r.get('p'), q[k] if k is not None else None, f'Q{k + 1}' if k is not None else None, g if isinstance(g, (int, float)) else None]
        print('qualifying:', qpath, len(Q), 'drivers')
    D = {'ev': f"{d['year']} {R['name']} 決勝", 'N': N, 'drivers': drivers,
         'lap': {a: [laps.get(a, {}).get(n, {}).get('t') for n in range(1, N + 1)] for a in abbrs},
         'pout': {a: [n for n, l in laps.get(a, {}).items() if l.get('pout')] for a in abbrs},
         'pit': pits,
         'st': {a: [[s['c'], s['a'], s['b']] for s in d['stints'] if s['d'] == a] for a in abbrs},
         'sp': {a: [laps.get(a, {}).get(n, {}).get('st') for n in range(1, N + 1)] for a in abbrs},
         'sc': sc_main, 'scs': scs, 'G': G, 'sec': sec, 'X': X}
    if Q:
        D['Q'] = Q

    # status from the result; a person can override
    status = {}
    for a in abbrs:
        r = res.get(a, {})
        k = 'dsq' if r.get('dsq') else 'dns' if r.get('dns') else 'dnf' if r.get('dnf') else None
        if k:
            status[a] = k
    status.update(R.get('status') or {})
    presets = R.get('presets')
    if not presets:  # teammates of the first three teams home, and the winner against second
        top, pairs = [], []
        for dr in drivers:
            if dr['t'] not in top:
                top.append(dr['t'])
        for t in top[:3]:
            p = [x['a'] for x in drivers if x['t'] == t]
            if len(p) == 2:
                pairs.append(p)
        presets = [['チームメイト', pairs], ['注目の対決', [[drivers[0]['a'], drivers[1]['a']]]]]
    race = {'gp': f"/gp/{R['slug']}/", 'news': R.get('news') or {}, 'status': status, 'ev': R.get('ev') or [], 'presets': presets}
    if R.get('story'):  # a person's DATA STORY in place of the automatic cards: [[title, text, abbr or '', chart id, news key], ...]
        race['story'] = R['story']

    # dates: lap 2 starts about when the leader finished lap 1
    start = laps[win].get(2, laps[win].get(1, {})).get('ds') or d['positions'][0]['at']
    t0 = dt.datetime.fromisoformat(start)
    jst = t0.astimezone(dt.timezone(dt.timedelta(hours=9)))
    loc = t0.astimezone(dt.timezone(dt.timedelta(hours=R.get('tz', 0))))
    part = '夜' if loc.hour >= 17 or loc.hour < 4 else '昼' if loc.hour >= 11 else '朝'
    local = f"現地は{loc.day}日の{part}" if loc.date() != jst.date() else f"現地も{loc.day}日"
    sub = f"決勝：{jst.year}年{jst.month}月{jst.day}日（日本時間。{local}） · {N}周 · 優勝 {drivers[0]['n']}"
    fetched = d.get('fetched')
    fetched = fetched or R.get('updated')  # older data files have no fetch time
    up = dt.datetime.fromisoformat(fetched).astimezone(dt.timezone(dt.timedelta(hours=9))) if fetched else dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    update = f"{up.year}年{up.month}月{up.day}日"
    session = f"の決勝セッション（session_key {d['session_key']}）。{update}に取得。" if d.get('session_key') else f"の決勝セッション。{update}に取得。"

    js = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = (tpl.replace('__DATA__', js(D)).replace('__RACE__', js(race))
            .replace('__TITLE__', f"{R['name']} ドライバー比較").replace('__H1__', f"{R['name']} 決勝を、図で見る")
            .replace('__SUB__', sub).replace('__UPDATE__', update).replace('__SESSION__', session))
    open(out_path, 'w').write(html)
    print('wrote', out_path, f'{len(html) // 1024} KB;', N, 'laps; winner', drivers[0]['n'], '; safety cars', scs)
    print('status:', status)

    # candidates for "ev" (a person picks; the page shows only what is in the race file)
    print('\nrace control candidates for "ev":')
    keys = ('PENALTY', 'SAFETY CAR DEPLOYED', 'RED FLAG', 'RETIRED', 'STOPPED', 'COLLISION', 'INCIDENT', 'RESUME', 'DISQUALIFIED')
    for x in d.get('rc') or []:
        m = x.get('msg') or ''
        if any(k in m.upper() for k in keys) and 'TRACK LIMITS' not in m.upper():
            print(f"  lap {x.get('n')}: {m[:110]}")
    # biggest position changes in one lap (no reason is written on the page)
    print('\nbiggest one-lap drops (outside safety cars):')
    drops = []
    for a in abbrs:
        for i in range(1, N):
            p0, p1 = X[a][i - 1], X[a][i]
            if p0 and p1 and p1 - p0 >= 3 and not in_sc(i + 1):
                drops.append((p1 - p0, i + 1, a, p0, p1))
    for k, n, a, p0, p1 in sorted(drops, reverse=True)[:8]:
        print(f'  lap {n}: {a} {p0} -> {p1}')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
