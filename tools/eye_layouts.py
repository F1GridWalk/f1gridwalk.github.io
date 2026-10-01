"""Header-image layouts for columns (owner's choice, 1 Oct 2026: big, high-contrast, click-friendly).

Used by col_assets.py when the column JSON has an "eye" object. Every layout is 1280x670.
Common optional keys: "tag" (small label, default from gpLabel), "foot" (one line at the bottom, <=30 chars).
Text values may contain <em> (orange highlight) and <br>. Everything else is escaped by the writer.

layouts
  "headline": {"h1Html": "2 lines, <=13 chars each", "sub": "..."}                  plain big headline (A)
  "number":   {"num": "52", "unit": "%", "lines": ["減った","ドイツの","F1視聴者"]}   giant number + 2-3 short lines (E1)
  "bignum":   {"pre": "速度差", "num": "80", "unit": "km/h", "h1Html": "..."}         number in a phrase + 2 lines below (E4)
  "question": {"kicker": "海外の見出し「F2より遅い」", "h1Html": "...？", "note": "..."} question, optional small line above/below (E2, E5)
  "band":     {"band": "オコンの行き先", "rows": [{"label":"日本","c":"jp","text":"「…」"}, ...]}
              or {"band": "...", "h1Html": "..."}                                    name/team in an orange band (C, E3)
  "versus":   {"left": {"who","sub","quote"}, "right": {"who","sub","quote"}}         two sides, VS in the middle (B)
"""
import html

e = html.escape

CSS = """
body{margin:0}
.c{width:1280px;height:670px;position:relative;overflow:hidden;font-family:'Noto Sans CJK JP',sans-serif;background:#1F2420;color:#FFF}
.st{position:absolute;left:0;top:0;width:1280px;height:670px}
.tag{position:absolute;left:64px;top:52px;background:#E8946C;color:#1F2420;font-weight:900;font-size:26px;padding:6px 18px;border-radius:8px}
.foot{position:absolute;left:64px;bottom:48px;right:330px;font-size:26px;font-weight:700;color:#D9D4C8;display:flex;align-items:center;gap:10px;white-space:nowrap}
.foot i{display:inline-block;width:40px;height:27px;border-radius:5px;background:var(--flag);box-shadow:0 0 0 2px rgba(255,255,255,.18)}
.brand{position:absolute;right:64px;bottom:42px;font-family:Georgia,serif;font-size:30px;font-weight:700;color:#FFF}
.brand small{display:block;font-family:'Noto Sans CJK JP';font-size:12px;letter-spacing:.24em;font-weight:700;opacity:.7}
em{font-style:normal;color:#FFB089}
.fit,.st h1,.st .txt,.st .q{white-space:nowrap}
/* headline */
.hl h1{position:absolute;left:64px;right:64px;top:150px;margin:0;font-weight:900;font-size:92px;line-height:1.28;letter-spacing:-.03em}
.hl .sub{position:absolute;left:64px;right:64px;top:440px;font-size:34px;font-weight:700;color:#D9D4C8}
/* number */
.nm .num{position:absolute;left:56px;top:110px;font-family:Georgia,serif;font-weight:700;font-size:300px;line-height:1;color:#FFB089;letter-spacing:-8px}
.nm .num small{font-size:120px;letter-spacing:0}
.nm .txt{position:absolute;left:660px;right:64px;top:170px;font-weight:900;font-size:62px;line-height:1.3}
/* bignum */
.bn .num{position:absolute;left:64px;right:64px;top:110px;font-weight:900;font-size:120px;line-height:1.1}
.bn .num em{font-family:Georgia,serif;font-size:190px}
.bn h1{position:absolute;left:64px;right:64px;top:340px;margin:0;font-weight:900;font-size:60px;line-height:1.35}
/* question */
.qu .kick{position:absolute;left:64px;right:64px;top:118px;font-weight:900;font-size:42px;color:#D9D4C8}
.qu h1{position:absolute;left:64px;right:64px;top:200px;margin:0;font-weight:900;font-size:100px;line-height:1.22}
.qu.nokick h1{top:130px}
.qu .note{position:absolute;left:64px;right:64px;top:470px;font-size:34px;font-weight:700;color:#D9D4C8}
/* band */
.bd .band{position:absolute;left:0;top:60px;max-width:1150px;background:#E8946C;color:#1F2420;font-weight:900;font-size:110px;line-height:1;padding:16px 56px 20px 64px;border-radius:0 18px 18px 0}
.bd .row{position:absolute;left:64px;right:64px;font-weight:900;font-size:58px;line-height:1.3}
.bd .lab{display:inline-block;font-size:28px;padding:4px 14px;border-radius:6px;margin-right:18px;vertical-align:middle;background:#FFF;color:#1F2420}
.bd h1{position:absolute;left:64px;right:64px;top:250px;margin:0;font-weight:900;font-size:70px;line-height:1.3}
/* versus */
.vs-wrap{display:flex;height:100%}
.half{flex:1;padding:64px 56px 0;position:relative}
.half.l{background:#2C332E}.half.r{background:#E8946C;color:#1F2420;padding-left:96px}
.half.r em{color:#1F2420;text-decoration:underline}
.who{font-size:36px;font-weight:900}
.who small{display:block;font-size:22px;font-weight:700;opacity:.8;margin-top:4px}
.q{font-weight:900;font-size:70px;line-height:1.2;margin-top:30px}
.half.l .q{padding-right:40px}
.vsb{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:120px;height:120px;border-radius:50%;background:#1F2420;color:#FFF;font:900 52px Georgia,serif;display:flex;align-items:center;justify-content:center;border:6px solid #FFF}
.vs .brand{color:#1F2420}
"""

# shrink any [data-fit] element until it fits its box and stays inside the frame
FIT_JS = """
<script>
(function(){
  var H=document.querySelector('.st').getBoundingClientRect().bottom-40;
  document.querySelectorAll('[data-fit]').forEach(function(el){
    var fs=parseFloat(getComputedStyle(el).fontSize), n=0;
    while(n++<80 && fs>18 && (el.scrollWidth>el.clientWidth+1 || el.getBoundingClientRect().bottom>H)){
      fs-=2; el.style.fontSize=fs+'px';
      el.querySelectorAll('small,em').forEach(function(c){c.style.fontSize='';});
    }
  });
})();
</script>"""


def _t(v):
    """allow only <em>, </em>, <br> in text values"""
    s = e(v or '')
    for a, b in (('&lt;em&gt;', '<em>'), ('&lt;/em&gt;', '</em>'), ('&lt;br&gt;', '<br>'), ('&lt;br/&gt;', '<br>')):
        s = s.replace(a, b)
    return s


def render(L, flags_html, height=670, extra_css=''):
    E = L['eye']
    lay = E.get('layout', 'headline')
    tag = E.get('tag') or ('速報コラム' if L.get('kind') == 'breaking' else L.get('gpLabel', 'コラム'))
    foot = E.get('foot')
    foot_html = f'<div class="foot" data-fit>{flags_html}{(" " + _t(foot)) if foot else ""}</div>' if (foot or flags_html) else ''
    brand = '<div class="brand">Grid Walk<small>WORLD F1 DESK</small></div>'
    tagd = f'<div class="tag">{e(tag)}</div>'
    if lay == 'number':
        lines = '<br>'.join(_t(x) for x in E.get('lines', []))
        inner = (f'{tagd}<div class="num">{e(E["num"])}<small>{e(E.get("unit",""))}</small></div>'
                 f'<div class="txt" data-fit>{lines}</div>{foot_html}')
        cls = 'nm'
    elif lay == 'bignum':
        inner = (f'{tagd}<div class="num fit" data-fit>{_t(E.get("pre",""))}<em>{e(E["num"])}</em>{e(E.get("unit",""))}</div>'
                 f'<h1 data-fit>{_t(E.get("h1Html",""))}</h1>{foot_html}')
        cls = 'bn'
    elif lay == 'question':
        kick = E.get('kicker')
        inner = (tagd + (f'<div class="kick fit" data-fit>{_t(kick)}</div>' if kick else '')
                 + f'<h1 data-fit>{_t(E["h1Html"])}</h1>'
                 + (f'<div class="note fit" data-fit>{_t(E["note"])}</div>' if E.get('note') else '') + foot_html)
        cls = 'qu' + ('' if kick else ' nokick')
    elif lay == 'band':
        rows = E.get('rows')
        if rows:
            body = ''.join(f'<div class="row fit" data-fit style="top:{250 + 120 * i}px"><span class="lab">{e(r.get("label",""))}</span>{_t(r["text"])}</div>'
                           for i, r in enumerate(rows[:3]))
        else:
            body = f'<h1 data-fit>{_t(E.get("h1Html",""))}</h1>'
        inner = f'<div class="band fit" data-fit>{_t(E["band"])}</div>{body}{foot_html}'
        cls = 'bd'
    elif lay == 'versus':
        def side(k, d):
            return (f'<div class="half {k}"><div class="who">{e(d.get("who",""))}<small>{e(d.get("sub",""))}</small></div>'
                    f'<div class="q" data-fit>{_t(d.get("quote",""))}</div></div>')
        inner = f'<div class="vs-wrap">{side("l", E["left"])}{side("r", E["right"])}</div><div class="vsb">VS</div>'
        if foot:
            inner += f'<div class="foot" data-fit style="right:auto;max-width:520px">{_t(foot)}</div>'
        cls = 'vs'
    else:
        inner = (f'{tagd}<h1 data-fit>{_t(E.get("h1Html") or L.get("eyeHtml") or e(L["title"]))}</h1>'
                 + (f'<div class="sub fit" data-fit>{_t(E.get("sub") or L.get("eyeSub",""))}</div>') + foot_html)
        cls = 'hl'
    shift = 0 if lay == 'versus' else (height - 670) // 2
    st_h = height if lay == 'versus' else 670
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}{extra_css}</style></head><body>'
            f'<div class="c" style="height:{height}px"><div class="st {cls}" style="top:{shift}px;height:{st_h}px">{inner}{brand}</div>'
            f'</div>{FIT_JS}</body></html>')
