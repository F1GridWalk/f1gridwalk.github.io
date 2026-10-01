#!/usr/bin/env python3
"""Make note + X assets for a daily column.
usage: python3 tools/col_assets.py lens/<slug>.json <outdir>
writes <outdir>/note_<slug>_コピー用.html, note_<slug>_原稿.txt, note_<slug>_見出し画像.png (1280x670), x_<slug>.png (1920x1080)
needs node + playwright (NODE_PATH=$(npm root -g))."""
import html, json, os, subprocess, sys
e = html.escape
HERE = os.path.dirname(os.path.abspath(__file__))
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
L = json.load(open(src, encoding='utf-8'))
slug = L['slug']; P = slug; TITLE = L['title']
FLAG = {'イギリス':'gb','イタリア':'it','ドイツ':'de','スペイン':'es','フランス':'fr','オランダ':'nl','ブラジル':'br','オーストリア':'at','アメリカ':'us','日本':'jp','ポルトガル':'pt','ベルギー':'be','スイス':'ch','メキシコ':'mx','アルゼンチン':'ar','オーストラリア':'au','カナダ':'ca','フィンランド':'fi','デンマーク':'dk','ポーランド':'pl'}
regions = []
for s in L.get('extraSources', []):
    r = s.get('region')
    if r and r != '日本' and r not in regions: regions.append(r)
STD_TAGS = '#F1 #フォーミュラ1 #モータースポーツ #F1ニュース #海外F1 #F1好きと繋がりたい #F1GridWalk #WORLDMEDIALENS'
_t = []
for x in ((L.get('noteTags') or '') + ' ' + STD_TAGS).split():
    if x.startswith('#') and x not in _t: _t.append(x)
TAGS = ' '.join(_t)
url = f'https://f1gridwalk.github.io/lens/{slug}/'
B = [list(b) for b in L['body']]
if L.get('note') and L.get('type') != 'column':
    B.append(['p', '※ ' + L['note']])  # columns: no Japanese-check line (owner's decision, 1 Oct 2026)
# entrance to the site right after the column, before the sources (owner's request, 1 Oct 2026)
B.append(['p', '━━━━━━━━━━'])
B.append(['bold', 'F1 Grid Walk では、世界のF1ニュースを毎日日本語でまとめています。'])
B.append(['p', '海外の記事の見出しと要約を、1日4回更新しています。'])
B.append(['url', 'https://f1gridwalk.github.io/'])
B.append(['p', 'このコラムはサイトでも読めます（投票もこちら）。' if L.get('mystery') else 'このコラムはサイトでも読めます。'])
B.append(['url', url])
B.append(['p', '━━━━━━━━━━'])
for s in L.get('extraSources', []):
    B.append(['p', f'出典：{s["source"]}（{s.get("region","")}）'])
    B.append(['url', s['url']])
# plain text
t = ['【タイトル】', TITLE, '', '【本文】（■＝大見出しにする行）', '']
for k, x in B:
    t += (['■ ' + x, ''] if k == 'h2' else ['【太字】' + x, ''] if k in ('bold', 'ask') else [x, ''])
t += ['【ハッシュタグ】', TAGS, '']
open(os.path.join(out, f'note_{P}_原稿.txt'), 'w', encoding='utf-8').write('\n'.join(t))
body = []
for k, x in B:
    if k == 'h2': body.append(f'<h2>{e(x)}</h2>')
    elif k in ('bold', 'ask'): body.append(f'<p><strong>{e(x)}</strong></p>')
    elif k == 'quote': body.append(f'<blockquote><p>{e(x)}</p></blockquote>')
    elif k == 'url': body.append(f'<p><a href="{e(x)}">{e(x)}</a></p>')
    else: body.append(f'<p>{e(x)}</p>')
ns = {'e': e, 'TITLE': TITLE, 'TAGS': TAGS, 'P': P, 'body': body}
exec(open(os.path.join(HERE, 'note_page.part'), encoding='utf-8').read(), ns)
open(os.path.join(out, f'note_{P}_コピー用.html'), 'w', encoding='utf-8').write(ns['page'])
# header images
h1 = L.get('eyeHtml') or L.get('titleHtml') or e(TITLE)
flags = ''.join(f'<span data-c="{FLAG.get(r,"xx")}"></span>' for r in regions[:4]) + (f'<b>{e("・".join(regions[:4]))}の記事から</b>' if regions else '')
tpl = open(os.path.join(HERE, 'eye_template.html'), encoding='utf-8').read()
h = (tpl.replace('{{BIG}}', e(L.get('big', ''))).replace('{{EY}}', 'WORLD MEDIA LENS · コラム')
        .replace('{{H1}}', h1).replace('{{SUB}}', e(L.get('eyeSub') or L.get('dek', '')[:40])).replace('{{FLAGS}}', flags))
if len(e(TITLE)) > 34 and not L.get('eyeHtml'):
    h = h.replace('font-size:66px', 'font-size:52px')
h2 = h.replace('height:670px', 'height:720px').replace('top:70px', 'top:88px')
if L.get('eye'):
    # new click-friendly layouts (owner's choice, 1 Oct 2026); see eye_layouts.py
    import re, sys as _s
    _s.path.insert(0, HERE)
    import eye_layouts
    fcss = '\n'.join(re.findall(r'^\[data-c=.*$', tpl, flags=re.M))
    fl = ''.join(f'<i data-c="{FLAG.get(r,"xx")}"></i>' for r in regions[:4])
    if not L['eye'].get('foot') and regions:
        L['eye']['foot'] = '・'.join(regions[:4]) + 'の記事から'
    h = eye_layouts.render(L, fl, 670, fcss)
    h2 = eye_layouts.render(L, fl, 720, fcss)
p1 = os.path.join(out, f'_eye_{P}.html'); open(p1, 'w', encoding='utf-8').write(h)
p2 = os.path.join(out, f'_eyex_{P}.html'); open(p2, 'w', encoding='utf-8').write(h2)
js = f"""const {{ chromium }} = require('playwright');
(async()=>{{const b=await chromium.launch();
let p=await b.newPage({{viewport:{{width:1280,height:670}}}}); await p.goto('file://{p1}'); await p.waitForTimeout(400); await p.screenshot({{path:{json.dumps(os.path.join(out, f'note_{P}_見出し画像.png'))}}});
p=await b.newPage({{viewport:{{width:1280,height:720}},deviceScaleFactor:1.5}}); await p.goto('file://{p2}'); await p.waitForTimeout(400); await p.screenshot({{path:{json.dumps(os.path.join(out, f'x_{P}.png'))}}});
await b.close();}})();"""
jp = os.path.join(out, '_render.js'); open(jp, 'w').write(js)
env = dict(os.environ); env['NODE_PATH'] = subprocess.check_output(['npm', 'root', '-g'], text=True).strip()
subprocess.run(['node', jp], check=True, env=env)
for f in (p1, p2, jp): os.remove(f)
print('ok', out)
