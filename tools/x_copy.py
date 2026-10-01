#!/usr/bin/env python3
"""X投稿.md -> x_<slug>_コピー用.html (one page per issue, copy button per post).

usage: python3 tools/x_copy.py daily/<date>/X投稿.md [outdir]
X投稿.md: issues separated by a line '---'; each starts with '# ...（...：<slug>...）'
and has posts as '## <label>' sections. Writes next to the md unless outdir is given.
"""
import base64, html, os, re, sys

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(src)
text = open(src, encoding='utf-8').read()

PAGE = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>X投稿：{slug}</title>
<style>
:root{{color-scheme:light}}
body{{margin:0;background:#F3EFE6;color:#1F2420;font-family:-apple-system,'Hiragino Sans','Noto Sans JP',sans-serif;line-height:1.8}}
.top{{background:#1F2420;color:#F3EFE6;padding:12px 16px;font-size:13px;font-weight:600}}
.wrap{{max-width:720px;margin:0 auto;padding:18px 16px 60px}}
.box{{background:#FBF9F4;border:1px solid #DDD5C5;border-radius:14px;padding:14px 16px;margin-bottom:16px}}
.lbl{{font-size:12px;font-weight:700;color:#9E4E2B;letter-spacing:.05em}}
.txt{{white-space:pre-wrap;word-break:break-all;margin:6px 0 10px;font-size:16px}}
.n{{font-size:12px;color:#6B6E66}}
button{{font:inherit;font-size:14px;font-weight:700;border:0;border-radius:999px;padding:8px 18px;background:#E8946C;color:#1F2420;cursor:pointer}}
button.done{{background:#7FC48C}}
img{{width:100%;border-radius:10px;display:block;margin-top:6px}}
</style></head><body>
<div class="top">{head}</div>
<div class="wrap">
<div class="box"><div class="lbl">添付する画像</div><img src="{img}" alt="x_{slug}.png"><div class="n">x_{slug}.png（長押しで保存）</div></div>
{boxes}
</div>
<script>
document.querySelectorAll('button[data-copy]').forEach(function(b){{
  b.addEventListener('click',function(){{
    var el=document.getElementById(b.getAttribute('data-copy')), ok=false, t=b.textContent;
    try{{ var r=document.createRange(); r.selectNodeContents(el); var s=getSelection(); s.removeAllRanges(); s.addRange(r); ok=document.execCommand('copy'); s.removeAllRanges(); }}catch(e){{}}
    if(!ok && navigator.clipboard){{ navigator.clipboard.writeText(el.innerText); }}
    b.textContent='コピーしました'; b.classList.add('done');
    setTimeout(function(){{ b.textContent=t; b.classList.remove('done'); }},1600);
  }});
}});
</script></body></html>
"""

written = []
for block in re.split(r'^---\s*$', text, flags=re.M):
    m = re.search(r'^#\s+(.+)$', block, flags=re.M)
    if not m:
        continue
    head = m.group(1).strip()
    sm = re.search(r'[：:]\s*([a-z0-9-]+)', head)
    if not sm:
        continue
    slug = sm.group(1)
    parts = re.split(r'^##\s+(.+)$', block, flags=re.M)
    boxes = []
    for i in range(1, len(parts), 2):
        label, body = parts[i].strip(), parts[i + 1].strip('\n').strip()
        if not body:
            continue
        pid = f'p{i // 2 + 1}'
        boxes.append(
            f'<div class="box"><div class="lbl">{html.escape(label)}</div>'
            f'<div class="txt" id="{pid}">{html.escape(body)}</div>'
            f'<button data-copy="{pid}">コピー</button> <span class="n">{len(body)}字</span></div>')
    ip = os.path.join(os.path.dirname(src), f'x_{slug}.png')
    img = ('data:image/png;base64,' + base64.b64encode(open(ip, 'rb').read()).decode()) if os.path.exists(ip) else f'x_{slug}.png'
    path = os.path.join(out, f'x_{slug}_コピー用.html')
    open(path, 'w', encoding='utf-8').write(
        PAGE.format(slug=slug, img=img, head=html.escape(head), boxes='\n'.join(boxes)))
    written.append(path)

print('\n'.join(written))
