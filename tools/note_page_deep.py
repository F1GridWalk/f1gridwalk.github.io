#!/usr/bin/env python3
"""Build the note paste page (Artifact HTML) for one DEEP issue with the FULL 理由と背景 from the site.
usage: python3 note_page_deep.py <deep json> <outdir> <part label> <key> <eye opts comma> <teaser html or ''>
Charts must already be rendered to <outdir>/img/<key>-c1.png ... in page order; eye images at img/<key>-eye-<opt>.png."""
import json, sys, html, re
src, out, part, key, opts, teaser = sys.argv[1:7]
e = html.escape
D = json.load(open(src, encoding='utf-8'))
slug = D['slug']; url = f'https://f1gridwalk.github.io/deep/{slug}/'
circ = '①②③④⑤⑥'
steps = []  # (kind, payload, label)
cur = []
def flush(label):
    global cur
    if cur: steps.append(('rich', ''.join(cur), label)); cur = []
cur.append(f'<p>{e(D["dek"])}</p>')
cur.append(f'<p>全文と表は F1 Grid Walk で → <a href="{url}?utm_source=note&amp;utm_campaign={slug}">{url}?utm_source=note&amp;utm_campaign={slug}</a></p>')
cur.append('<h2>先に結論</h2>' + ''.join(f'<p>{circ[i]} {e(q)}</p>' for i, q in enumerate(D['quick'])))
cur.append('<h2>理由と背景</h2>')
n = 0; seg = 1
for s in D['sections']:
    cur.append(f'<h3>{e(s["h"])}</h3>')
    for b in s['body']:
        if 'p' in b: cur.append(f'<p>{e(b["p"])}</p>')
        elif 'quote' in b: cur.append(f'<blockquote><p>「{e(b["quote"])}」（{e(b.get("who",""))}）</p></blockquote>')
        elif 'view' in b: cur.append(f'<p>{e(b["view"])}</p>')
        elif 'chart' in b:
            flush(f'本文 その{seg}'); seg += 1; n += 1
            steps.append(('img', f'img/{key}-c{n}.png', b['chart']['title'], f'{part}_図{n}_{b["chart"]["title"]}.png'))
if teaser: cur.append(teaser)
cur.append('<h2>続きは F1 Grid Walk で</h2><p>サイトの記事では、グラフに指で触ると数字が出ます。「データと記録」の表と、出典の一覧もあります。</p>')
cur.append(f'<p><strong>DEEP GRID セパンのタイヤ {part}「{e(D["title"].split("】")[-1])}」</strong></p><p><a href="{url}">{url}</a></p>')
cur.append('<p>━━━━━━━━━━</p><p><strong>F1 Grid Walk では、世界のF1ニュースを毎日日本語でまとめています。</strong></p><p>海外の記事の要約を、毎日載せています。</p><p>ほかの海外記事も読みたい方は、F1 Grid Walkへ。</p><p><a href="https://f1gridwalk.github.io/">https://f1gridwalk.github.io/</a></p><p>━━━━━━━━━━</p>')
cur.append(''.join(f'<p><a href="{s["url"]}">出典：{e(s["name"])}</a></p>' for s in D['sources']))
flush(f'本文 その{seg}')
tags = '#F1 #F1jp #DEEPGRID #セパン #マレーシア #タイヤ #ピレリ #F1解説 #フォーミュラ1 #モータースポーツ #F1ニュース #海外F1 #F1好きと繋がりたい #F1GridWalk'
H = []
k = 1
eyes = ''.join(f'<div class="opt"><img src="img/{key}-eye-{o}.png" alt="見出し画像 案{o}"><div class="ol"><b>案{o}</b><button class="cp dl" data-img="img/{key}-eye-{o}.png" data-name="{part}_見出し画像_{o}.png">ダウンロード</button></div></div>' for o in opts.split(','))
H.append(f'<li class="st im"><div class="hd"><span class="no">{k}</span><b>見出し画像（1つ選ぶ）</b><em>画像</em></div><div class="opts">{eyes}</div></li>'); k += 1
H.append(f'<li class="st"><div class="hd"><span class="no">{k}</span><b>タイトル</b></div><div class="bx" id="t">{e(D["title"])}</div><button class="cp" data-plain="t">タイトルをコピー</button></li>'); k += 1
for i, st in enumerate(steps):
    if st[0] == 'rich':
        H.append(f'<li class="st"><div class="hd"><span class="no">{k}</span><b>{st[2]}</b></div><div class="bx tall" id="r{i}">{st[1]}</div><button class="cp" data-rich="r{i}">{st[2]}をコピー</button></li>')
    else:
        H.append(f'<li class="st im"><div class="hd"><span class="no">{k}</span><b>{e(st[2])}</b><em>画像</em></div><img src="{st[1]}" alt="{e(st[2])}"><button class="cp dl" data-img="{st[1]}" data-name="{e(st[3])}">画像をダウンロード</button></li>')
    k += 1
H.append(f'<li class="st"><div class="hd"><span class="no">{k}</span><b>ハッシュタグ</b></div><div class="bx" id="g">{tags}</div><button class="cp" data-plain="g">ハッシュタグをコピー</button></li>')
json.dump({'title': D['title'], 'steps_html': ''.join(H), 'body_html': ''.join(st[1] if st[0]=='rich' else f'<figure><img src="{st[1]}"></figure>' for st in steps)}, open(f'{out}/_{key}.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('steps', k)
