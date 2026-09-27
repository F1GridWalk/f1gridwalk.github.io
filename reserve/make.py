import html
import sys, importlib
M = importlib.import_module(sys.argv[1]); TITLE, TAGS, B = M.TITLE, M.TAGS, M.B; P = sys.argv[2]
e = html.escape
# ---- plain text ----
t = ["【タイトル】", TITLE, "", "【本文】（■＝大見出しにする行）", ""]
for b in B:
    k = b[0]
    if k == "h2": t += ["■ " + b[1], ""]
    elif k == "list": t += ["・" + x for x in b[1]] + [""]
    elif k == "bold": t += ["【太字】" + b[1], ""]
    else: t += [b[1], ""]
t += ["【ハッシュタグ】", TAGS, ""]
open(f"note_{P}_原稿.txt", "w", encoding="utf-8").write("\n".join(t))
# ---- html for copy & paste ----
body = []
for b in B:
    k = b[0]
    if k == "h2": body.append(f"<h2>{e(b[1])}</h2>")
    elif k == "list": body.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in b[1]) + "</ul>")
    elif k == "bold": body.append(f"<p><strong>{e(b[1])}</strong></p>")
    elif k == "quote": body.append(f"<blockquote><p>{e(b[1])}</p></blockquote>")
    elif k == "url": body.append(f'<p><a href="{e(b[1])}">{e(b[1])}</a></p>')
    else: body.append(f"<p>{e(b[1])}</p>")
page = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>note用原稿：{e(TITLE)}</title>
<style>
:root{{color-scheme:light}}
body{{margin:0;background:#F3EFE6;color:#1F2420;font-family:-apple-system,'Hiragino Sans','Noto Sans JP',sans-serif;line-height:1.8}}
.bar{{position:sticky;top:0;z-index:5;background:#1F2420;color:#F3EFE6;padding:12px 16px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.bar b{{flex-basis:100%;font-size:13px;font-weight:600;opacity:.85}}
.bar button{{font:inherit;font-size:14px;font-weight:700;border:0;border-radius:999px;padding:8px 16px;background:#E8946C;color:#1F2420;cursor:pointer}}
.bar button.done{{background:#7FC48C}}
.wrap{{max-width:720px;margin:0 auto;padding:18px 16px 60px}}
.box{{background:#FBF9F4;border:1px solid #DDD5C5;border-radius:14px;padding:14px 16px;margin-bottom:16px}}
.lbl{{font-size:12px;font-weight:700;color:#9E4E2B;letter-spacing:.1em}}
#title{{font-size:20px;font-weight:800;margin:4px 0 0}}
#tags{{margin:4px 0 0}}
#body h2{{font-size:20px;margin:30px 0 8px;border-left:4px solid #9E4E2B;padding-left:10px}}
#body p{{margin:0 0 14px}}
#body blockquote{{margin:0 0 14px;padding:4px 14px;border-left:3px solid #DDD5C5;color:#3A3E37}}
#body a{{color:#1F5E8A;word-break:break-all}}
.how{{font-size:13.5px}}
.how li{{margin-bottom:4px}}
</style></head><body>
<div class="bar"><b>ボタンを押してコピー → noteに貼り付け</b>
<button data-copy="title">タイトル</button><button data-copy="body">本文</button><button data-copy="tags">ハッシュタグ</button></div>
<div class="wrap">
<div class="box how"><div class="lbl">使い方</div><ol>
<li>noteで「投稿」→「テキスト」を開く</li>
<li>見出し画像に「note_{P}_見出し画像.png」を設定</li>
<li>上の「タイトル」を押して、noteのタイトル欄に貼り付け</li>
<li>「本文」を押して、noteの本文に貼り付け（大見出し・太字・引用・リンクもそのまま入ります）</li>
<li>公開設定でハッシュタグを貼り付けて公開</li>
<li>公開する前にClaudeに一言。サイトの答え合わせのページを同時に公開します</li></ol>
<p style="margin:0">※ 貼り付けたあと見出しが普通の文字になっていたら、その行を選んで「大見出し」にしてください。URLだけの行は、noteがリンクカードにしてくれます。</p></div>
<div class="box"><div class="lbl">タイトル</div><div id="title">{e(TITLE)}</div></div>
<div class="box"><div class="lbl">ハッシュタグ</div><div id="tags">{e(TAGS)}</div></div>
<div class="box"><div class="lbl">本文</div><div id="body">{"".join(body)}</div></div>
</div>
<script>
function copyEl(el, btn){{
  var ok=false;
  try{{ var r=document.createRange(); r.selectNodeContents(el); var s=window.getSelection(); s.removeAllRanges(); s.addRange(r); ok=document.execCommand('copy'); s.removeAllRanges(); }}catch(e){{}}
  if(!ok && navigator.clipboard){{ navigator.clipboard.writeText(el.innerText); ok=true; }}
  var t=btn.textContent; btn.textContent=ok?'コピーしました':'長押しで選択してコピーしてください'; btn.classList.add('done');
  setTimeout(function(){{ btn.textContent=t; btn.classList.remove('done'); }},1600);
}}
document.querySelectorAll('[data-copy]').forEach(function(b){{ b.addEventListener('click',function(){{ copyEl(document.getElementById(b.getAttribute('data-copy')), b); }}); }});
</script></body></html>'''
open(f"note_{P}_コピー用.html", "w", encoding="utf-8").write(page)
