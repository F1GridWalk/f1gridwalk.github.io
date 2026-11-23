"""Lab (not on the public site): fetch one session's laps into a small JSON for the comparison prototype.
Usage: python lab/fetch_race.py 2026 "Las Vegas" R
Tries FastF1 first (laps, tyres, pit stops, positions); if that fails, Jolpica (laps and positions only).
Data: Formula 1 timing via FastF1 / Jolpica. Fan, non-commercial analysis."""
import json, os, sys, urllib.request

year, gp, kind = int(sys.argv[1]), sys.argv[2], sys.argv[3]
os.makedirs('lab/data', exist_ok=True)
out = {'year': year, 'gp': gp, 'session': kind}
try:
    import fastf1
    os.makedirs('cache', exist_ok=True)
    fastf1.Cache.enable_cache('cache')
    s = fastf1.get_session(year, gp, kind)
    s.load(laps=True, telemetry=False, weather=False, messages=False)
    out['source'] = 'FastF1'
    out['event'] = str(s.event['EventName'])
    out['date'] = str(s.date)
    res = []
    for _, r in s.results.iterrows():
        res.append({'abbr': r['Abbreviation'], 'num': str(r['DriverNumber']), 'name': r['FullName'], 'team': r['TeamName'],
                    'color': '#' + str(r['TeamColor'] or '888888'), 'pos': None if r['Position'] != r['Position'] else int(r['Position']),
                    'grid': None if r['GridPosition'] != r['GridPosition'] else int(r['GridPosition']), 'status': str(r['Status'])})
    out['drivers'] = res
    laps = []
    for _, l in s.laps.iterrows():
        t = l['LapTime']
        laps.append({'d': l['Driver'], 'n': int(l['LapNumber']), 't': None if t != t else round(t.total_seconds(), 3),
                     'c': None if l['Compound'] != l['Compound'] else str(l['Compound']), 's': None if l['Stint'] != l['Stint'] else int(l['Stint']),
                     'life': None if l['TyreLife'] != l['TyreLife'] else int(l['TyreLife']),
                     'pin': l['PitInTime'] == l['PitInTime'], 'pout': l['PitOutTime'] == l['PitOutTime'],
                     'p': None if l['Position'] != l['Position'] else int(l['Position']), 'ts': str(l['TrackStatus']), 'ok': bool(l['IsAccurate'])})
    out['laps'] = laps
except Exception as ex:
    print('FastF1 failed:', repr(ex)[:300])
    rnd = int(sys.argv[4]) if len(sys.argv) > 4 else None
    if not rnd:
        raise
    base = f'https://api.jolpi.ca/ergast/f1/{year}/{rnd}'
    get = lambda u: json.load(urllib.request.urlopen(u, timeout=30))
    laps, off = [], 0
    while True:
        j = get(f'{base}/laps.json?limit=100&offset={off}')
        races = j['MRData']['RaceTable']['Races']
        if not races:
            break
        for L in races[0]['Laps']:
            for tm in L['Timings']:
                m, sec = tm['time'].split(':') if ':' in tm['time'] else ('0', tm['time'])
                laps.append({'d': tm['driverId'], 'n': int(L['number']), 't': round(int(m) * 60 + float(sec), 3), 'p': int(tm['position'])})
        off += 100
        if off >= int(j['MRData']['total']):
            break
    out['source'] = 'Jolpica'
    out['laps'] = laps
fn = f'lab/data/{year}-{gp.lower().replace(" ", "")}-{kind}.json'
json.dump(out, open(fn, 'w'), ensure_ascii=False, separators=(',', ':'))
print('wrote', fn, len(out['laps']), 'laps', out['source'])
