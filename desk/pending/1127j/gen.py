import re,sys,json
def off(k,l1,l2,s):
    t=open('base_off.html').read()
    t=re.sub(r'<div class=l1>.*?</div>',f'<div class=l1>{l1}</div>',t,1)
    t=re.sub(r'<div class=l2>.*?</div>',f'<div class=l2><em>{l2}</em></div>',t,1)
    t=re.sub(r'<div class=s>.*?</div>',f'<div class=s>{s}</div>',t,1)
    open(k+'.html','w').write(t)
def world(k,l1,l2,s):
    t=open('base_world.html').read()
    t=re.sub(r'<div class=r>.*?</div></div>',f'<div class=r><div class=l>{l1}</div><div class=l><em>{l2}</em></div></div>',t,1)
    t=re.sub(r'<div class=s>.*?</div>',f'<div class=s>{s}</div>',t,1)
    open(k+'.html','w').write(t)
def deep(k,no,a,b,sub):
    t=open('base_deep.html').read()
    t=t.replace('<i>#40</i>',f'<i>#{no}</i>')
    t=re.sub(r'<h1>.*?</h1>',f'<h1>{a}<br><em>{b}</em></h1>',t,1)
    t=re.sub(r'<div class="sub">.*?</div>',f'<div class="sub">{sub}</div>',t,1)
    open(k+'.html','w').write(t)
for row in json.load(open(sys.argv[1])):
    {'off':off,'world':world,'deep':deep}[row[0]](*row[1:])
