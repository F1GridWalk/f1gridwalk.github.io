#!/usr/bin/env python3
"""One simple copy-paste page per issue: note (image, title, body, hashtags) + X (image, post, reply).

usage: python3 tools/post_kit.py daily/<date>
Reads daily/<date>/X投稿.md and note_<slug>_コピー用.html (made by col_assets.py),
writes daily/<date>/投稿セット_<slug>.html (images embedded, works as a single file).
"""
import base64, glob, html, os, re, sys

d = sys.argv[1]
e = html.escape


def b64(p):
    return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode() if os.path.exists(p) else ''


def x_posts(md, slug):
    if not os.path.exists(md):
        return []
    for block in re.split(r'^---\s*$', open(md, encoding='utf-8').read(), flags=re.M):
        m = re.search(r'^#\s+(.+)$', block, flags=re.M)
        if not m or slug not in m.group(1):
            continue
        parts = re.split(r'^##\s+(.+)$', block, flags=re.M)
        out = []
        for i in range(1, len(parts), 2):
            body = parts[i + 1].strip()
            if body:
                out.append((parts[i].strip(), body))
        return out
    return []


CSS = """
:root{color-scheme:light}
body{margin:0;background:#F3EFE6;color:#1F2420;font-family:-apple-system,'Hiragino Sans','Noto Sans JP',sans-serif;line-height:1.7}
.wrap{max-width:640px;margin:0 auto;padding:16px 16px 60px}
h1{font-size:15px;margin:0 0 4px;color:#6B6E66;font-weight:600}
h2{font-size:24px;margin:28px 0 12px;padding:10px 14px;border-radius:12px;color:#fff}
h2.note{background:#2CB696} h2.x{background:#111}
.step{background:#FBF9F4;border:1px solid #DDD5C5;border-radius:14px;padding:12px 14px;margin-bottom:12px}
.head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.lbl{font-size:18px;font-weight:800}
.lbl small{font-size:12px;font-weight:600;color:#6B6E66;margin-left:6px}
button{font:inherit;font-size:16px;font-weight:800;border:0;border-radius:999px;padding:10px 22px;background:#E8946C;color:#1F2420;cursor:pointer;white-space:nowrap}
button.done{background:#7FC48C}
.c{margin-top:8px;font-size:15px;white-space:pre-wrap;word-break:break-all}
.c.html{white-space:normal;max-height:180px;overflow:auto;border-top:1px dashed #DDD5C5;padding-top:6px}
.c.html h2{all:unset;display:block;font-weight:800;margin:10px 0 4px}
.c.html p{margin:0 0 8px}
img{width:100%;border-radius:10px;display:block;margin-top:8px}
.tip{font-size:13px;color:#6B6E66;margin-top:4px}
"""

JS = """
document.querySelectorAll('button[data-copy]').forEach(function(b){
  b.addEventListener('click',function(){
    var el=document.getElementById(b.getAttribute('data-copy')), ok=false;
    try{ var r=document.createRange(); r.selectNodeContents(el); var s=getSelection(); s.removeAllRanges(); s.addRange(r); ok=document.execCommand('copy'); s.removeAllRanges(); }catch(e){}
    if(!ok && navigator.clipboard){ navigator.clipboard.writeText(el.innerText); ok=true; }
    b.textContent=ok?'コピーした！':'長押しでコピー'; b.classList.add('done');
    setTimeout(function(){ b.textContent='コピー'; b.classList.remove('done'); },1600);
  });
});
"""

n = [0]


def step(label, inner, sub='', copy=True, cls='c'):
    n[0] += 1
    i = f'c{n[0]}'
    btn = f'<button data-copy="{i}">コピー</button>' if copy else ''
    return (f'<div class="step"><div class="head"><div class="lbl">{label}<small>{sub}</small></div>{btn}</div>'
            f'<div class="{cls}" id="{i}">{inner}</div></div>')


def img_step(label, src, name):
    return (f'<div class="step"><div class="lbl">{label}</div><img src="{src}" alt="{e(name)}">'
            f'<div class="tip">画像を長押し →「保存」</div></div>')


written = []
for notef in sorted(glob.glob(os.path.join(d, 'note_*_コピー用.html'))):
    slug = os.path.basename(notef)[5:-len('_コピー用.html')]
    src = open(notef, encoding='utf-8').read()
    title = re.search(r'<div id="title">(.*?)</div>', src, re.S).group(1)
    tags = re.search(r'<div id="tags">(.*?)</div>', src, re.S).group(1)
    body = re.search(r'<div id="body">(.*)</div>\s*</div>\s*</div>\s*<script>', src, re.S).group(1)
    n[0] = 0
    parts = [f'<h1>{e(slug)}</h1>', '<h2 class="note">note</h2>',
             img_step('① 見出し画像', b64(os.path.join(d, f'note_{slug}_見出し画像.png')), 'note'),
             step('② タイトル', title),
             step('③ 本文', body, '見出し付き', cls='c html'),
             step('④ ハッシュタグ', tags, '公開時に')]
    posts = x_posts(os.path.join(d, 'X投稿.md'), slug)
    if posts:
        parts += ['<h2 class="x">X</h2>', img_step('① 画像', b64(os.path.join(d, f'x_{slug}.png')), 'x')]
        names = ['② 投稿', '③ ②への返信', '④ 追い投稿', '⑤']
        for k, (label, text) in enumerate(posts):
            sub = '画像を付けて投稿' if k == 0 else ('自分の投稿に返信' if '返信' in label else label)
            parts.append(step(names[min(k, 3)], e(text), sub))
    page = (f'<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>投稿セット：{e(slug)}</title>'
            f'<style>{CSS}</style></head><body><div class="wrap">{"".join(parts)}</div><script>{JS}</script></body></html>')
    out = os.path.join(d, f'投稿セット_{slug}.html')
    open(out, 'w', encoding='utf-8').write(page)
    written.append(out)
print('\n'.join(written))
