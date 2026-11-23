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
    out = {'year': year, 'gp': gp, 'session': kind}
def get(u, tries=3):
    import time
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'f1gridwalk-lab'}), timeout=60))
        except Exception as ex:
            print('  retry', i + 1, u, repr(ex)[:120]); time.sleep(5)
    raise RuntimeError('could not read ' + u)
if 'laps' not in out:
  try:  # OpenF1 (historical data is free)
    ses = [x for x in get(f'https://api.openf1.org/v1/sessions?year={year}&session_name=Race') if gp.lower().replace(' ', '') in (x.get('location', '') + x.get('circuit_short_name', '') + x.get('country_name', '')).lower().replace(' ', '')]
    print('OpenF1 sessions:', [(x.get('session_key'), x.get('location')) for x in ses])
    sk = ses[-1]['session_key']
    drv = get(f'https://api.openf1.org/v1/drivers?session_key={sk}')
    out['drivers'] = [{'abbr': d['name_acronym'], 'num': str(d['driver_number']), 'name': d.get('full_name'), 'team': d.get('team_name'), 'color': '#' + (d.get('team_colour') or '888888')} for d in drv]
    ab = {d['driver_number']: d['name_acronym'] for d in drv}
    st = get(f'https://api.openf1.org/v1/stints?session_key={sk}')
    pits = get(f'https://api.openf1.org/v1/pit?session_key={sk}')
    pos = get(f'https://api.openf1.org/v1/position?session_key={sk}')
    lp = get(f'https://api.openf1.org/v1/laps?session_key={sk}')
    out['source'] = 'OpenF1'; out['stints'] = [{'d': ab.get(x['driver_number']), 'c': x.get('compound'), 's': x.get('stint_number'), 'a': x.get('lap_start'), 'b': x.get('lap_end'), 'age': x.get('tyre_age_at_start')} for x in st]
    out['pits'] = [{'d': ab.get(x['driver_number']), 'n': x.get('lap_number'), 'dur': x.get('pit_duration')} for x in pits]
    out['laps'] = [{'d': ab.get(x['driver_number']), 'n': x.get('lap_number'), 't': x.get('lap_duration'), 'pout': bool(x.get('is_pit_out_lap')), 's1': x.get('duration_sector_1'), 's2': x.get('duration_sector_2'), 's3': x.get('duration_sector_3'), 'st': x.get('st_speed')} for x in lp]
    out['positions'] = [{'d': ab.get(x['driver_number']), 'at': x.get('date'), 'p': x.get('position')} for x in pos]
  except Exception as ex:
    print('OpenF1 failed:', repr(ex)[:300])
if 'laps' not in out:
    rnd = int(sys.argv[4]) if len(sys.argv) > 4 else None
    if not rnd:
        raise
    base = f'https://api.jolpi.ca/ergast/f1/{year}/{rnd}'
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
