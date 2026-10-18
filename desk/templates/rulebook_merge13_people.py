import json,sys
DRY='--dry' in sys.argv
PP='deep/people.json'; pj=json.load(open(PP,encoding='utf-8')); P=pj['people'] if isinstance(pj,dict) else pj
ppl=json.load(open(sys.argv[1],encoding='utf-8'))
old=[p['id'] for p in P]; err=[]
pid={p['id']:p for p in P}
for n in ppl.get('new',[]):
    if n['id'] in pid: err.append('dup person '+n['id'])
    n['checked']='2026-10-17'; P.append(n); pid[n['id']]=n
for q in ppl.get('patch',[]):
    if q['id'] not in pid: err.append('missing '+q['id']); continue
    pid[q['id']].update(q['fields']); pid[q['id']]['checked']='2026-10-17'
txt=json.dumps(ppl,ensure_ascii=False)
for p in P:
    txt=json.dumps([x for x in ppl.get('new',[])+ppl.get('patch',[]) if x['id']!=p['id']],ensure_ascii=False)
    for a in p.get('avoid',[]):
        if len(a)<=12 and a in txt: err.append('avoid name '+p['id']+':'+a)
if [p['id'] for p in P][:len(old)]!=old: err.append('ids changed')
print('\n'.join(err) or 'OK','people',len(P))
if not DRY: json.dump(pj,open(PP,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
