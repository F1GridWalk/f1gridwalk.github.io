import json,os,sys,re
os.chdir('/home/claude/f1gridwalk.github.io')
RB='/tmp/claude-0/-home-claude-f1gridwalk-github-io/32904842-827d-5d66-bae4-8e345913b90b/scratchpad/rb'
DRY=len(sys.argv)>1 and sys.argv[1]=='dry'
R='deep/rules.json'; d=json.load(open(R,encoding='utf-8'))
PP='deep/people.json'; pj=json.load(open(PP,encoding='utf-8')); P=pj['people'] if isinstance(pj,dict) else pj
old_ids=[t['id'] for t in d['terms']]; old_pids=[p['id'] for p in P]
new=json.load(open(RB+'/v12_a.json'))+json.load(open(RB+'/v12_b.json'))
patch=json.load(open(RB+'/v12_patch_a.json'))+json.load(open(RB+'/v12_patch_b.json')); ppl=json.load(open(RB+'/v12_people.json'))
rep={'リンブラッド':'リンドブラッド','ベン・スレイエム':'ビン・スライエム','アジャー':'ハジャー','ヴァスール':'バスール','ルイ・マルケ ス':'ルイ・マルケス'}
def fx(o):
    if isinstance(o,str):
        for a,b in rep.items(): o=o.replace(a,b)
        return o
    if isinstance(o,list): return [fx(i) for i in o]
    if isinstance(o,dict): return {k:fx(v) for k,v in o.items()}
    return o
new=fx(new); patch=fx(patch)
err=[]
ids=set(old_ids); terms={t['term'] for t in d['terms']}
for t in new:
    if t['id'] in ids: err.append('dup id '+t['id'])
    if t['term'] in terms: err.append('dup term '+t['term'])
    if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*',t['id']): err.append('bad id '+t['id'])
    ids.add(t['id']); terms.add(t['term'])
memo=re.compile('確かめられ|未確認|確認できなかった|確認中|TODO|要確認')
for t in new:
    if t['cat'] not in d['cats']: err.append('cat '+t['id'])
    if len(t.get('body',[]))<2: err.append('body '+t['id'])
    if not 3<=len(t.get('words',[]))<=6: err.append('words '+t['id'])
    if not t.get('src'): err.append('src '+t['id'])
    if memo.search(json.dumps([t['short'],t['body']],ensure_ascii=False)): err.append('memo '+t['id'])
    for s in t.get('see',[]):
        if s not in ids: err.append('see '+t['id']+'->'+s)
    for e in t.get('examples',[]):
        if not os.path.exists(e['u'].strip('/')+'/index.html'): err.append('ex '+t['id']+' '+e['u'])
    t['checked']='2026-10-13'
byid={t['id']:t for t in d['terms']}
for p in patch:
    t=byid.get(p['id'])
    if not t: err.append('patch missing '+p['id']); continue
    ex=t.setdefault('examples',[]); have={e['u'] for e in ex}
    for e in p.get('add_examples',[]):
        if not os.path.exists(e['u'].strip('/')+'/index.html'): err.append('pex '+p['id']+' '+e['u'])
        if e['u'] not in have: ex.append(e)
    if p.get('body_fix'):
        if len(p['body_fix'])<2: err.append('body_fix '+p['id'])
        if memo.search(json.dumps(p['body_fix'],ensure_ascii=False)): err.append('memo patch '+p['id'])
        t['body']=p['body_fix']
    if p.get('src_add'):
        s=t.setdefault('src',[]); su={x['url'] for x in s}
        s+= [x for x in p['src_add'] if x['url'] not in su]
    t['checked']='2026-10-13'
# people
pid={p['id']:p for p in P}
for n in ppl.get('new',[]):
    if n['id'] in pid: err.append('dup person '+n['id'])
    n['checked']='2026-10-13'; P.append(n); pid[n['id']]=n
for q in ppl.get('patch',[]):
    if q['id'] not in pid: err.append('person patch missing '+q['id']); continue
    pid[q['id']].update(q['fields']); pid[q['id']]['checked']='2026-10-13'
# name check: avoid strings
txt=json.dumps(new+patch,ensure_ascii=False)
for p in P:
    for a in p.get('avoid',[]):
        if len(a)<=12 and a in txt: err.append('avoid name '+a)
# ids unchanged
if [t['id'] for t in d['terms']][:len(old_ids)]!=old_ids: err.append('existing ids changed')
if [p['id'] for p in P][:len(old_pids)]!=old_pids: err.append('existing person ids changed')
print('\n'.join(err) or 'OK', 'new',len(new),'patch',len(patch),'people+',len(ppl.get('new',[])))
if not err and not DRY:
    d['terms']+=new; d['checked']='2026-10-13'
    json.dump(d,open(R,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    json.dump(pj,open(PP,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print('total',len(d['terms']),'people',len(P))
