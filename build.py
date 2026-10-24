#!/usr/bin/env python3
"""Build static pages for F1 Grid Walk.

Reads articles.json (plus teams.json, circuits.json) and writes:
  news/<id>/index.html   one page per article (kept even after the article leaves articles.json)
  news/index.html        a plain-HTML list of every article page (crawlable without JavaScript)
  news/archive.json      the data behind the pages (merged every run, never shrinks)
  sitemap.xml            home + list + every article page

Run from the repository root:  python3 build.py
Only the Python standard library is used.
"""
import hashlib
import html
import json
import os
import re
import urllib.parse
from urllib.parse import quote
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://f1gridwalk.github.io'
JST = timezone(timedelta(hours=9))
OG_IMAGE = SITE + '/og-image.png?v=2'

KIND = {'primary': '一次情報', 'news': '報道', 'tech': '技術', 'rumor': '噂', 'fan': 'ファン投稿'}
KIND_TIP = {
    'primary': 'F1・FIA・チームなど当事者の公式発表',
    'news': '報道機関の記事',
    'tech': '技術の解説・分析記事',
    'rumor': '報道で出たうわさ・未確認の話',
    'fan': 'ファン掲示板で話題の投稿（未確認を含む）',
}
PRIMARY_SRC = re.compile(r'^(Formula1\.com|F1公式|FIA)(\s|$)', re.I)
LANG = {'en': '英語', 'it': 'イタリア語', 'de': 'ドイツ語', 'es': 'スペイン語', 'fr': 'フランス語',
        'pt': 'ポルトガル語', 'nl': 'オランダ語', 'pl': 'ポーランド語', 'fi': 'フィンランド語',
        'sv': 'スウェーデン語', 'da': 'デンマーク語', 'hu': 'ハンガリー語', 'zh': '中国語',
        'ko': '韓国語', 'ja': '日本語'}
KEEP = ('id', 'kind', 'primary', 'lang', 'region', 'source', 'provider', 'cat', 'circuit', 'teams', 'topic',
        'title', 'summary', 'orig', 'url', 'published')
ID_OK = re.compile(r'^[a-z0-9][a-z0-9-]{0,120}$')

e = lambda s: html.escape(str(s if s is not None else ''), quote=True)


# who publishes the summaries and columns (structured data for search engines)
PUBLISHER = {'@type': 'Organization', 'name': 'F1 Grid Walk', 'alternateName': 'F1グリッドウォーク', 'url': SITE + '/',
             'logo': {'@type': 'ImageObject', 'url': SITE + '/icon-512.png', 'width': 512, 'height': 512}}


def ld(obj):
    """One <script type="application/ld+json"> tag, safe inside HTML."""
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace('</', '<\\/') + '</script>\n'


def load(name, default=None):
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def write(rel, text):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    old = None
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            old = f.read()
    if old != text:
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    return False


def kind_of(a):
    k = a.get('kind') or 'news'
    if k == 'news' and (a.get('primary') or PRIMARY_SRC.match(a.get('source') or '')):
        return 'primary'
    return k if k in KIND else 'news'


def when(a):
    try:
        return datetime.fromisoformat(a['published'].replace('Z', '+00:00'))
    except Exception:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)


def jst_text(d):
    d = d.astimezone(JST)
    wd = '月火水木金土日'[d.weekday()]
    return f'{d.year}年{d.month}月{d.day}日({wd}) {d.hour:02d}:{d.minute:02d}'


def shared_css():
    """Flag colours and the logo, taken from index.html so both stay in step."""
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    m = re.search(r'\n(\[data-c="jp"\]\{.*?\n:root\[data-theme="dark"\] \.srcbadge::before\{[^\n]*\})', src, re.S)
    flags = m.group(1) if m else ''
    fm = re.search(r'var FLAG = (\{.*?\});', src, re.S)
    flag_map = {}
    if fm:
        for k, v in re.findall(r"'([^']+)':'([a-z]{2})'", fm.group(1)):
            flag_map[k] = v
    lm = re.search(r'<a class="brand"[^>]*>\s*(<svg.*?</svg>)', src, re.S)
    logo = lm.group(1) if lm else ''
    return flags, flag_map, logo


CSS = '''
/* phone: bottom tab bar (owner's choice A, 11 Oct 2026) */
.bt{display:none}
@media (max-width:520px){
.bt{display:grid;position:fixed;left:0;right:0;bottom:0;z-index:60;grid-template-columns:repeat(5,1fr);background:var(--paper);border-top:1px solid var(--line);padding:5px 4px calc(5px + env(safe-area-inset-bottom));box-shadow:0 -4px 16px rgba(0,0,0,.06)}
.bt a,.bt button{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-height:48px;font:inherit;font-size:11px;font-weight:700;line-height:1.2;color:var(--muted);background:none;border:0;text-decoration:none;cursor:pointer;padding:2px 0;-webkit-tap-highlight-color:transparent}
.bt svg{width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.bt .on{color:var(--ink)}
.bt .on svg{stroke-width:2.3}
body{padding-bottom:calc(66px + env(safe-area-inset-bottom))}
}
:root{--paper:#F3EFE6;--surface:#FBF9F4;--line:#DDD5C5;--ink:#1F2420;--ink-2:#3A3E37;--muted:#5B5F57;--moss:#1F2420;--clay:#9E4E2B;--on-ink:#FBF9F4;
--sans:'IBM Plex Sans JP','Hiragino Sans','Noto Sans JP','Yu Gothic',Meiryo,sans-serif;--logo:'Fraunces',Georgia,'Times New Roman',serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--paper:#191C18;--surface:#222620;--line:#353A32;--ink:#ECE7DC;--ink-2:#D3CEC2;--muted:#A5A99C;--moss:#ECE7DC;--clay:#E09A76;--on-ink:#191C18}}
:root[data-theme="dark"]{color-scheme:dark;--paper:#191C18;--surface:#222620;--line:#353A32;--ink:#ECE7DC;--ink-2:#D3CEC2;--muted:#A5A99C;--moss:#ECE7DC;--clay:#E09A76;--on-ink:#191C18}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.8;-webkit-font-smoothing:antialiased}
a{color:var(--ink);text-underline-offset:3px;text-decoration-thickness:1px}
.wrap{max-width:760px;margin:0 auto;padding:0 20px}
header{border-bottom:1px solid var(--line)}
header .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-block:14px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink)}
.brand svg{width:38px;height:38px;flex-shrink:0}
.brand b{display:block;font-family:var(--logo);font-weight:600;font-size:22px;line-height:1}
.brand small{display:block;font-size:8.5px;font-weight:700;letter-spacing:.2em;color:var(--muted);margin-top:4px}
.stamp-ring{fill:none;stroke:var(--moss)}.mark-line{fill:none;stroke:var(--ink);stroke-linecap:round;stroke-linejoin:round}.leaf{fill:var(--clay)}
.toplink{font-size:13px;color:var(--muted);white-space:nowrap}
.crumbs{font-size:12.5px;color:var(--muted);margin:22px 0 14px}
.crumbs a{color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;font-size:13px;color:var(--muted)}
.srcbadge{display:inline-flex;align-items:center;gap:7px;font-weight:700;color:var(--c,var(--ink-2))}
.srcbadge::before{content:"";width:15px;height:10px;border-radius:2px;flex-shrink:0;background:var(--flag,var(--c,var(--moss)));box-shadow:0 0 0 1px rgba(0,0,0,.14)}
.kind{display:inline-flex;align-items:center;padding:0 8px;border-radius:5px;font-size:11.5px;font-weight:700;letter-spacing:.06em;line-height:20px;white-space:nowrap;--k:var(--ink);border:1px solid var(--k);color:var(--k);background:color-mix(in srgb,var(--k) 9%,transparent)}
.kind.primary{--k:#2E6B3A}.kind.news{--k:#4B5261}.kind.tech{--k:#1F5E8A}.kind.rumor{--k:#B0532C}.kind.fan{--k:#7A4A93}
.kind.rumor,.kind.fan{border-style:dashed}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .kind.primary{--k:#7FC48C}:root:not([data-theme="light"]) .kind.news{--k:#B6BCC8}:root:not([data-theme="light"]) .kind.tech{--k:#7DB6E0}:root:not([data-theme="light"]) .kind.rumor{--k:#E8946C}:root:not([data-theme="light"]) .kind.fan{--k:#C39AD9}}
h1{font-size:clamp(24px,5.4vw,34px);line-height:1.45;margin:14px 0 10px;font-weight:700;letter-spacing:.01em}
.orig{font-size:13.5px;color:var(--muted);margin:0 0 20px}
.summary{font-size:17px;line-height:1.95;margin:0 0 22px}
.warn{font-size:13.5px;border:1px dashed var(--clay);color:var(--ink-2);padding:10px 14px;border-radius:10px;margin:0 0 22px}
.cta{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:2px 8px;min-height:56px;padding:12px 22px;border-radius:999px;background:var(--ink);color:var(--on-ink);font-weight:700;font-size:16px;text-decoration:none;text-align:center}
.cta:hover{color:var(--on-ink);opacity:.9}
.cta small{font-weight:500;opacity:.8;font-size:12.5px;white-space:nowrap}
.credit{font-size:12.5px;color:var(--muted);margin:12px 0 0;text-align:center}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin:26px 0 0}
.tags span,.tags a{font-size:12.5px;border:1px solid var(--line);border-radius:999px;padding:2px 12px;background:var(--surface)}
.tags a{color:var(--ink);text-decoration:none;font-weight:700}.tags a::after{content:" →";color:var(--clay)}
.share{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 0;align-items:center;font-size:13px;color:var(--muted)}
.share a,.share button{font:inherit;font-size:13px;color:var(--ink);border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:4px 14px;text-decoration:none;cursor:pointer}
section{margin:40px 0 0;padding-top:22px;border-top:1px solid var(--line)}
section h2{font-size:18px;margin:0 0 6px}
section .lead{font-size:14px;color:var(--ink-2);margin:0 0 14px}
ul.list{list-style:none;margin:0;padding:0}
ul.list li{padding:12px 0;border-bottom:1px solid var(--line)}
ul.list li:last-child{border-bottom:0}
ul.list .m{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center;font-size:12px;color:var(--muted)}
ul.list .kind{font-size:10px;line-height:16px;padding:0 5px}
ul.list a.t{display:block;font-weight:700;font-size:15.5px;line-height:1.6;margin-top:3px;text-decoration:none}
ul.list a.t:hover{text-decoration:underline}
.day{font-size:13px;font-weight:700;color:var(--muted);margin:26px 0 0;letter-spacing:.06em}
.kw{margin:26px 0 0;border:1px solid var(--line);border-radius:16px;background:var(--surface);padding:14px 16px 12px}
.kw-h{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:2px 10px;margin:0 0 4px;font-size:14px;font-weight:700}
.kw-h small{font-size:12px;font-weight:500;color:var(--muted)}
.kw-t{display:block;padding:10px 0;border-top:1px solid var(--line);color:var(--ink);text-decoration:none}
.kw-t b{font-size:15.5px}
.kw-t small{margin-left:8px;font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:0 8px;white-space:nowrap}
.kw-t span{display:block;font-size:14px;line-height:1.75;color:var(--ink-2);margin-top:2px}
.kw-t:hover b{text-decoration:underline;text-underline-offset:3px}
.kw-ph{margin:8px 0 6px;padding-top:10px;border-top:1px solid var(--line);font-size:12.5px;font-weight:700;color:var(--muted)}
.kw-p{display:flex;flex-wrap:wrap;gap:6px}
.kw-p a{font-size:13.5px;border:1px solid var(--line);border-radius:999px;padding:2px 12px;text-decoration:none;background:var(--paper);color:var(--ink)}
.kw-all{display:inline-block;margin-top:10px;font-size:13px;font-weight:700;color:var(--clay)}
.hubbox{display:block;margin:18px 0 0;padding:12px 14px;border:2px solid var(--ink);border-radius:14px;text-decoration:none;color:var(--ink)}
.hubbox small{display:block;font-size:12px;color:var(--clay);font-weight:700;letter-spacing:.08em}
.hubbox b{display:block;font-size:16px;line-height:1.6;margin-top:2px}
.hubbox span{display:block;font-size:13px;color:var(--muted);margin-top:2px}
footer{margin:56px 0 0;border-top:1px solid var(--line);padding:22px 0 40px;font-size:12px;color:var(--muted)}
footer p{margin:6px 0}
@media (max-width:600px){.summary{font-size:16px}.cta{font-size:15px}}
'''


BT_ICON = {'drv': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 15a8 8 0 0 1 16-1v3H4z"/><path d="M12 14h8M8 19h8"/></svg>', 'news': '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h8M8 17h5"/></svg>', 'data': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20V11M12 20V4M19 20v-7"/></svg>', 'col': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h8l4 4v12H6z"/><path d="M14 4v4h4M9 13h6M9 16.5h4"/></svg>', 'rule': '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6"/><path d="M16 16l4 4"/></svg>'}


def bottom_tabs(canonical):
    """Phone bottom tab bar on every page (owner's choice A, 11 Oct 2026)."""
    path = canonical.replace(SITE, '')
    cur = 'drv' if path.startswith(('/drivers/', '/deep/rules/person-')) else 'rule' if path.startswith('/deep/rules/') else ('news' if path.startswith(('/news/', '/gp/', '/teams/')) or path == '/' else ('col' if path.startswith(('/lens/', '/deep/', '/offgrid/', '/columns/')) else ''))
    items = [('news', '/#news', 'ニュース'), ('data', '/?v=data', 'データ'), ('col', '/columns/', 'コラム'), ('drv', '/drivers/', 'ドライバー'), ('rule', '/deep/rules/', '用語')]
    return ('<nav class="bt" aria-label="サイト内の移動">' + ''.join(
        f'<a href="{u}"' + (' class="on" aria-current="page"' if k == cur else '') + f' data-track="click/bt/{k}">{BT_ICON[k]}{t}</a>' for k, u, t in items) + '</nav>')


BASE_CSS_V = ''  # version of assets/base.css, set in main() once FLAGS is known (owner's OK, 23 Oct 2026)


def page(title, desc, canonical, body, extra_head='', og_type='article', og_image=None, og_size=(1200, 630)):
    og = og_image or OG_IMAGE
    return f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="alternate" type="application/rss+xml" title="F1 Grid Walk" href="/feed.xml">
<meta name="apple-mobile-web-app-title" content="Grid Walk">
<meta name="application-name" content="Grid Walk">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="F1 Grid Walk">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="{og_size[0] if og_image else 1200}">
<meta property="og:image:height" content="{og_size[1] if og_image else 630}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{og}">
{extra_head}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+JP:wght@400;500;700&family=Fraunces:opsz,wght@9..144,600&display=swap">
<link rel="stylesheet" href="/assets/base.css?v={BASE_CSS_V}">
</head>
<body>
<header><div class="wrap">
  <a class="brand" href="/" aria-label="F1 Grid Walk トップへ">{LOGO}<span><b>Grid Walk</b><small>WORLD F1 DESK</small></span></a>
  <a class="toplink" href="/">最新ニュースを見る →</a>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
  <p><a href="/">F1 Grid Walk</a> — 世界のF1ニュースを、日本語で。　<a href="/feed.xml">RSS</a></p>
  <p>記事の著作権は各媒体に帰属します。当サイトは見出しの翻訳と独自の短い要約、原文へのリンクを掲載しています。F1 Grid Walk は非公式のファンサイトで、Formula 1 および FIA とは関係ありません。</p>
</div></footer>
{bottom_tabs(canonical)}
<script data-goatcounter="https://gridwalk.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
<script>
document.addEventListener('click',function(ev){{
  var a=ev.target.closest&&ev.target.closest('[data-track]'); if(!a) return;
  try{{ if(window.goatcounter&&window.goatcounter.count) window.goatcounter.count({{path:a.getAttribute('data-track'),title:a.getAttribute('data-title')||'',event:true}}); }}catch(e){{}}
}});
var cp=document.getElementById('copy'),cu=(document.querySelector('link[rel=canonical]')||{{}}).href||location.href;
if(cp) cp.addEventListener('click',function(){{
  var done=function(){{cp.textContent='コピーしました';setTimeout(function(){{cp.textContent='リンクをコピー';}},1400);}};
  try{{navigator.clipboard.writeText(cu).then(done,function(){{window.prompt('このURLをコピーしてください',cu);}});}}catch(e){{window.prompt('このURLをコピーしてください',cu);}}
}});
</script>
</body>
</html>
'''


def item_li(a, flag_of):
    k = kind_of(a)
    return (f'<li><div class="m"><span class="kind {k}">{KIND[k]}</span>'
            f'<span class="srcbadge" data-c="{flag_of(a)}">{e(a["source"])}</span>'
            f'<time datetime="{e(a["published"])}">{e(jst_text(when(a)))}</time></div>'
            f'<a class="t" href="/news/{e(a["id"])}/">{e(a["title"])}</a></li>')


LANG_CODE = lambda k: (k or '').upper()


def short_jst(a):
    d = when(a).astimezone(JST)
    return f'{d.month}/{d.day} {d.hour:02d}:{d.minute:02d}'


def ext(url, text, cls=None):
    c = f' class="{cls}"' if cls else ''
    return f'<a{c} href="{e(url)}" target="_blank" rel="noopener noreferrer">{text}</a>'


def art(a, text, cls=None):
    """Link an article title to our own summary page (the original is linked from there)."""
    c = f' class="{cls}"' if cls else ''
    return f'<a{c} href="/news/{e(a["id"])}/">{text}</a>'


def static_card(a, flag_of):
    k = kind_of(a)
    return (f'<article class="card" data-c="{flag_of(a)}"><div class="card-meta">'
            f'<span class="kind {k}" title="{e(KIND_TIP[k])}">{KIND[k]}</span>'
            f'<span class="srcbadge" data-c="{flag_of(a)}">{e(a["source"])}</span>'
            f'<span class="rg">{e(a.get("region", ""))}</span>'
            f'<time datetime="{e(a["published"])}">{short_jst(a)}</time></div>'
            f'<h3>{art(a, e(a["title"]))}</h3><p>{e(a.get("summary", ""))}</p>'
            f'<div class="card-foot"><span class="cat">{e(a.get("cat") or "ニュース")}</span>{ext(a["url"], "原文へ ↗")}</div></article>')


def prerender_index(data, flag_of, flag_map_ref=None):
    """Write this week's story, the latest news and the latest tech pieces straight into index.html,
    so the top page can be read without JavaScript. The script replaces these blocks when it runs."""
    flag_map_ref = flag_map_ref or {}
    arts = [a for a in data.get('articles', []) if ID_OK.match(a.get('id', ''))]
    topics = data.get('topics') or {}
    now = datetime.now(timezone.utc)
    groups = {}
    for a in arts:
        if a.get('topic') and (now - when(a)).days < 7:
            groups.setdefault(a['topic'], []).append(a)
    best = None
    for key, items in groups.items():
        n = len({x['source'] for x in items})
        newest = max(when(x) for x in items)
        if n >= 2 and (best is None or n > best[1] or (n == best[1] and newest > best[2])):
            best = (key, n, newest, items)
    hero = []
    top_hub = latest_hub()
    if top_hub:  # 読み解き (formerly 話題のまとめ) replaces 今週の注目 at the top (owner's decision, 12 Oct 2026)
        H = top_hub
        by_id = {x['id']: x for x in arts}
        circ = next((by_id[o['id']].get('circuit') for o in H.get('outlets', []) if by_id.get(o['id'], {}).get('circuit')), '')
        S = H.get('story') or {}
        n_chars = sum(len(x[1]) for x in S.get('body', []) if x[0] == 'p')
        go_sub = f'約{round(n_chars / 100) * 100:,}字 · 約{max(1, round(n_chars / 500))}分で読めます' if n_chars else '共通点・違い・まだ分からないこと'
        hero.append(f'<div class="hubtop" id="hub-top" data-circuit="{e(circ or "")}">'
                    f'<div class="chips"><span class="chip-feature">STORY</span><span class="chip-cat">{e(H.get("gp", ""))} · F1 Grid Walk の独自記事</span></div>'
                    f'<h1 id="hero-title"><a href="/topics/{e(H["slug"])}/" data-track="click/top/hub">{e(H["title"])}</a></h1>'
                    + (f'<p class="hubtop-sub">{e(H["sub"])}</p>' if H.get('sub') and not S else '')
                    + (f'<p class="hubtop-ans"><b>読み比べて分かったこと</b>{e(H["answer"])}</p>' if H.get('answer') and not S else '')  # the story is the read (owner, 12 Oct 2026)
                    + (f'<p class="hubtop-hook">{e(S["hook"])}</p>' if S.get('hook') else '')  # the story's first line, instead of a word count (owner, 12 Oct 2026)
                    + f'<a class="hubtop-go" href="/topics/{e(H["slug"])}/" data-track="click/top/hub-go"><span>STORY を読む</span><b aria-hidden="true">→</b></a>'
                    + (f'<a class="hubtop-all" href="/topics/" data-track="click/top/hub-all">これまでの STORY（{len(HUBS)}本） →</a>' if len(HUBS) > 1 else '')
                    + '</div>')
    elif best:
        key, n, _, items = best
        info = topics.get(key, {})
        lens = info.get('lens') if isinstance(info.get('lens'), dict) and info['lens'].get('groups') else None
        by_id = {x['id']: x for x in arts}
        lead = next((x for x in items if x.get('featured')), items[0])
        nt = sorted([x for x in items if x.get('kind', 'news') in ('news', 'tech')], key=when)
        pick = next((x for x in items if x.get('featured')), nt[0] if nt else lead)
        media = [x for x in items if x.get('kind') != 'fan']
        n_media = len({x['source'] for x in media}) or n
        hero.append(f'<div class="chips"><span class="chip-feature">今週の注目</span><span class="chip-cat">世界の{n_media}媒体が報道</span></div>')
        hero.append('<div class="tw-sec" id="tw-facts">'
                    f'<h1 id="hero-title">{art(pick, e(info.get("title") or pick["title"]))}</h1>'
                    '</div>')
        li = []
        for x in sorted(media, key=when, reverse=True)[:3]:
            k = kind_of(x)
            lz = x.get('lens') or {}
            top = (f'<div class="tl-top"><span class="srcbadge" data-c="{flag_of(x)}">{e(x["source"])}</span>'
                   + (f'<span class="dot rgn">{e(x["region"])}</span>' if x.get('region') else '')
                   + f'<span class="dot">{e(LANG.get(x.get("lang"), LANG_CODE(x.get("lang"))))}</span>'
                   + (f'<span class="dot">{e(lz["type"])}</span>' if lz.get('type') else '') + '</div>')
            angle = ''
            if lz.get('lead') or lz.get('focus'):
                angle = '<div class="tl-angle"><b>主要焦点</b>' + e('／'.join(v for v in (lz.get('lead'), lz.get('focus')) if v)) + '</div>'
            prov = (f'<div class="tl-prov">掲載：<b>{e(x["source"])}</b>　記事提供：<b>{e(x["provider"])}</b></div>' if x.get('provider') else '')
            li.append(f'<li data-c="{flag_of(x)}">' + top
                      + art(x, f'<span class="kind {k}" style="margin-right:6px">{KIND[k]}</span>' + e(x['title']), 'tl-title')
                      + angle + prov + '</li>')
        arts_block = (f'<section class="tw-sec" id="tw-articles"><h2 class="tw-h">世界の記事<small>{n_media}媒体 · {len(media)}本</small></h2>'
                      '<ul class="trend-list tw-list">' + ''.join(li) + '</ul></section>')
        if lens and lens.get('guide'):  # 世界の見方 = only the 総評 guide (owner's decision, 3 Oct 2026)
            cols = []
            for gi, g in enumerate(lens['groups']):
                scope = g.get('scope', 'others')
                fc = flag_map_ref.get(g.get('region') or '', 'xx') if scope in ('country', 'outlet') else 'xx'
                flag = (f'<span class="lens-flag" data-c="{fc}"></span>' if scope in ('country', 'outlet') else '<span class="lens-flag icon"></span>')
                g_arts = [by_id[i] for i in g.get('ids') or [] if i in by_id]
                n_src = len({x['source'] for x in g_arts})
                small = (e(g.get('region')) if scope == 'outlet' and g.get('region') else
                         e(g.get('provider', '')) + '配信' if scope == 'wire' and g.get('provider') else
                         f'{n_src}媒体' if n_src > 1 else '')
                pts = ''.join(f'<li>{e(p)}</li>' for p in (g.get('points') or [])[:3])
                links = ''.join(f'<li data-c="{flag_of(x)}"><span class="srcbadge" data-c="{flag_of(x)}">{e(x["source"])}</span>{art(x, e(x["title"]))}</li>' for x in g_arts)
                cols.append(f'<article class="lens-col" data-c="{fc}"><div class="lens-who">{flag}{e(g.get("label", ""))}'
                            + (f'<small>{small}</small>' if small else '') + '</div>'
                            f'<p class="lens-focus"><small>焦点</small>{e(g.get("focus", ""))}</p>'
                            + (f'<ul class="lens-pts">{pts}</ul>' if pts else '')
                            + (f'<details class="lens-src"><summary>記事を見る</summary><ul>{links}</ul></details>' if links else '')
                            + '</article>')
            hero.append('<section class="tw-sec lens" id="tw-lens"><h2 class="tw-h tw-h-lens"><span class="tw-dot"></span>総評：読みたいことで選ぶ</h2>'
                        '</section>')
    else:
        a = next((x for x in arts if x.get('featured')), arts[0] if arts else None)
        if a:
            hero.append('<div class="chips"><span class="chip-feature">今日の一本</span></div>')
            hero.append(f'<h1 id="hero-title">{art(a, e(a["title"]))}</h1><p class="hero-sum">{e(a.get("summary", ""))}</p>')
    news = sorted([a for a in arts if a.get('kind', 'news') == 'news'], key=when, reverse=True)[:10]
    tech = sorted([a for a in arts if a.get('kind') == 'tech'], key=when, reverse=True)[:3]
    feed = ('<div class="grid">' + ''.join(static_card(a, flag_of) for a in news) + '</div>'
            '<p class="pre-more"><a href="/news/">すべてのニュースの一覧 →</a>　<a href="/gp/" data-track="click/top/gp">GPごと</a>　<a href="/teams/" data-track="click/top/teams">チームごと</a></p>') if news else ''
    techh = ('<div class="grid kgrid">' + ''.join(static_card(a, flag_of) for a in tech) + '</div>') if tech else ''

    p = os.path.join(ROOT, 'index.html')
    src = open(p, encoding='utf-8').read()
    out = src
    for name, block in (('hero', '\n'.join(hero)), ('feed', feed), ('tech', techh)):
        if not block:
            continue
        pat = re.compile(r'(<!--pre:' + name + r'-->).*?(<!--/pre:' + name + r'-->)', re.S)
        if not pat.search(out):
            print(f'build: marker pre:{name} not found in index.html, skipped')
            continue
        out = pat.sub(lambda m: m.group(1) + block + m.group(2), out, count=1)
    if out != src:
        with open(p, 'w', encoding='utf-8') as f:
            f.write(out)


# ---------------------------------------------------------------------------
# WORLD GRID: one long-form page per race, from lens/<slug>.json
# ---------------------------------------------------------------------------
LENS_CSS = '''
.ans-box{display:block;margin:6px 0 26px;padding:12px 14px;border:2px solid var(--ink);border-radius:14px;background:var(--surface);color:var(--ink);text-decoration:none}
.ans-box small{display:block;font-size:12px;font-weight:700;color:var(--clay);letter-spacing:.06em}
.ans-box b{display:block;font-size:16px;line-height:1.6;margin-top:2px}
.ans-box span{display:block;font-size:14px;line-height:1.7;color:var(--ink-2);margin-top:2px}
.ctag{display:inline-block;font-weight:800;font-size:11px;line-height:1;letter-spacing:.1em;padding:5px 10px;border-radius:999px;margin:0 0 7px;vertical-align:middle;white-space:nowrap}
.ctag-world{background:#E8946C;color:#1F2420}.ctag-deep{background:#8E2F3B;color:#FFFFFF}.ctag-off{background:#2F6B66;color:#FFFFFF}
.ctag-no{display:inline-block;margin:0 0 7px 8px;font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.06em;vertical-align:middle}

.gw-next{margin:30px 0 8px;padding:20px 18px 18px;border-radius:16px;background:var(--surface);border:1px solid var(--line);border-top:4px solid var(--clay)}
.gw-k{margin:0;font:700 12px/1 system-ui;letter-spacing:.2em;color:var(--clay);text-transform:uppercase}
.gw-next h2{margin:8px 0 6px;font-size:21px;line-height:1.4}
.gw-lead{margin:0 0 10px;font-size:14px;color:var(--muted)}
.gw-next ul{list-style:none;margin:0 0 16px;padding:0}
.gw-next li{padding:9px 0;border-top:1px solid var(--line)}
.gw-next li a{display:block;color:var(--ink);text-decoration:none;font-weight:600;font-size:15px;line-height:1.5}
.gw-next li small{color:var(--muted);font-size:12px}
.gw-btn{display:block;text-align:center;background:var(--ink);color:var(--on-ink);text-decoration:none;font-weight:700;font-size:16px;padding:14px 12px;border-radius:12px}
.gw-sub{display:block;text-align:center;margin-top:10px;font-size:14px;color:var(--clay);font-weight:600}
.more-cols{margin:30px 0 8px;padding:20px 18px 18px;border-radius:16px;background:var(--surface);border:1px solid var(--line);border-top:4px solid #E8946C}
.mc-k{margin:0;font:800 12px/1 system-ui;letter-spacing:.2em;color:#C46A3E}
.more-cols h2{margin:8px 0 10px;font-size:22px;line-height:1.4}
.more-cols ul{list-style:none;margin:0 0 16px;padding:0}
.more-cols li{border-top:1px solid var(--line)}
.more-cols li a{display:block;padding:12px 0;color:var(--ink);text-decoration:none}
.more-cols li b{display:block;font-family:'Noto Serif JP','Noto Serif CJK JP','Hiragino Mincho ProN','Yu Mincho',serif;font-weight:900;font-size:17px;line-height:1.5}
.more-cols li a:hover b{text-decoration:underline;text-underline-offset:3px}
.more-cols li small{display:block;margin-top:3px;color:var(--muted);font-size:12px}
.mc-btn{display:block;text-align:center;background:#E8946C;color:#1F2420;text-decoration:none;font-weight:800;font-size:16px;padding:14px 12px;border-radius:12px}
.mc-sub{display:block;text-align:center;margin-top:12px;font-size:13.5px;color:var(--muted);font-weight:600}
.lens-hero{margin:18px 0 0;background:#1F2420;color:#F3EFE6;border-radius:22px;padding:24px 20px 26px;position:relative;overflow:hidden}
.lens-hero::after{content:attr(data-big);position:absolute;right:-10px;bottom:-34px;font-family:Georgia,serif;font-size:128px;font-weight:700;color:rgba(255,255,255,.05);letter-spacing:-4px;pointer-events:none}
.lens-ey{font-size:11px;font-weight:800;letter-spacing:.26em;color:#E8946C}
.lens-hero h1{font-weight:900;font-size:clamp(24px,6.4vw,32px);line-height:1.45;margin:10px 0 12px;letter-spacing:.01em}
.lens-hero h1 em{font-style:normal;color:#E8946C}
.lens-hero .dek{margin:0 0 16px;font-size:14.5px;color:#D3CEC2}
.lens-hero .date{font-size:12px;color:#A5A99C;margin:0 0 14px}
.lens-stats{display:flex;gap:8px;flex-wrap:wrap;position:relative;z-index:1}
.lens-stats div{border:1px solid rgba(255,255,255,.2);border-radius:12px;padding:7px 12px;font-size:12px;color:#D3CEC2;line-height:1.35}
.lens-stats b{display:block;font-size:21px;color:#fff;font-family:Georgia,serif}
.lens-sec{margin:34px 0 0}
.lens-sh{display:flex;align-items:center;gap:10px;margin-bottom:4px}
.lens-sh .no{width:30px;height:30px;flex-shrink:0;border-radius:50%;background:#B0532C;color:#fff;font-weight:800;font-size:13px;display:flex;align-items:center;justify-content:center}
.lens-sh h2{margin:0;font-size:20px;font-weight:900;line-height:1.4}
.lens-lead{font-size:14px;color:var(--muted);margin:2px 0 16px}
.uc{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:16px 18px 12px;margin-bottom:14px}
.ucn{font-family:Georgia,serif;font-size:13px;font-weight:700;color:#B0532C;letter-spacing:.1em;margin-bottom:6px}
.ucm{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.ucm b{display:block;font-size:14px;line-height:1.25}.ucm small{font-size:11.5px;color:var(--muted)}
.bigflag{width:34px;height:23px;border-radius:4px;background:var(--flag,#999);box-shadow:0 0 0 1px rgba(0,0,0,.15);flex-shrink:0}
.ucm .kind{margin-left:auto}
.uc h3{font-size:19px;line-height:1.5;margin:0 0 8px;font-weight:900}
.uc p{font-size:15px;color:var(--ink-2);margin:0 0 12px;line-height:1.85}
.ucf{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;border-top:1px dashed var(--line);padding-top:10px}
.stamp{font-size:11px;font-weight:800;letter-spacing:.05em;color:#B0532C;border:2px solid #B0532C;border-radius:6px;padding:1px 8px;transform:rotate(-2deg);display:inline-block;background:color-mix(in srgb,#B0532C 8%,transparent)}
.ucf a{font-size:13.5px;font-weight:700}
.ucf .also{flex-basis:100%;font-size:12px;color:var(--muted)}
.lens-note{font-size:12.5px;color:var(--muted);background:color-mix(in srgb,var(--line) 45%,transparent);border-radius:12px;padding:10px 13px;margin:4px 0 0}
.quiz{background:#1F2420;color:#F3EFE6;border-radius:24px;padding:20px 16px 18px}
.qk{font-size:11px;font-weight:800;letter-spacing:.3em;color:#E8946C}
.quiz h3{font-weight:900;font-size:clamp(21px,5.6vw,26px);line-height:1.5;margin:6px 0 6px}
.quiz .qd{font-size:14px;color:#D3CEC2;margin:0 0 14px}
.ev{display:flex;gap:12px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:16px;padding:12px;margin-bottom:9px}
.evl{flex-shrink:0;min-width:34px;height:34px;padding:0 6px;border-radius:17px;background:#F3EFE6;color:#1F2420;font-weight:800;font-size:12px;display:flex;align-items:center;justify-content:center}
.ev h4{margin:0 0 4px;font-size:15.5px;line-height:1.55}
.ev p{margin:0 0 6px;font-size:13.5px;color:#C9C4B8;line-height:1.7}
.evs{display:flex;flex-wrap:wrap;gap:4px 12px}
.evs a{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:700;color:#ECE7DC;text-decoration:none}
.evs a::before{content:"";width:14px;height:9px;border-radius:2px;background:var(--flag,#999)}
.evs a:hover{text-decoration:underline}
.vote-q{margin:16px 0 8px;font-size:14px;font-weight:700;text-align:center}
.vote{display:grid;gap:8px}
.vote button{font:inherit;font-size:15px;font-weight:700;line-height:1.5;text-align:left;border:0;border-radius:14px;background:#B0532C;color:#fff;padding:12px 14px;cursor:pointer;display:flex;gap:10px;align-items:flex-start}
.vote button b{font-family:Georgia,serif;font-size:18px;line-height:1.3}
.vote button[aria-pressed="true"]{background:#F3EFE6;color:#1F2420;box-shadow:0 0 0 3px #E8946C inset}
.vote button:disabled{cursor:default}
.vote button:disabled:not([aria-pressed="true"]){opacity:.45}
.vh{text-align:center;font-size:12.5px;color:#C9C4B8;margin-top:8px}
.answer{margin-top:16px;background:var(--surface);border:2px solid var(--ink);border-radius:20px;padding:16px 16px 12px}
.js .answer{display:none}
.js .answer.open{display:block}
.answer h4{margin:0 0 8px;font-size:16px}
.answer h4 .tg{font-size:10.5px;font-weight:700;border:1px solid #86650F;color:#86650F;border-radius:5px;padding:0 6px;margin-left:6px;vertical-align:2px}
.answer ol{margin:0 0 10px;padding-left:1.3em;font-size:15px;line-height:1.85}
.answer ol li{margin-bottom:6px}
.answer .caveat{font-size:12.5px;color:var(--muted);border-top:1px dashed var(--line);padding-top:8px;margin:0}
.sdesk h2{font-size:15px;letter-spacing:.24em;margin:0 0 4px}
.sdesk .lens-lead{margin-bottom:8px}
.sdesk ul{list-style:none;margin:0;padding:0}
.sdesk li{display:flex;flex-wrap:wrap;align-items:center;gap:3px 10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:12px;color:var(--muted)}
.sdesk li a.t{flex-basis:100%;font-size:14.5px;font-weight:700;color:var(--ink);text-decoration:none;line-height:1.55}
.sdesk li a.t:hover{text-decoration:underline}
.sdesk li a.sum{margin-left:auto;font-size:12px;color:var(--muted)}
.col-body{margin:26px 0 0;font-size:16.5px;line-height:1.95;color:var(--ink)}
.col-body h2{font-size:21px;font-weight:900;line-height:1.5;margin:34px 0 10px;padding-left:12px;border-left:4px solid #B0532C}
.col-body p{margin:0 0 16px}
.col-body blockquote{margin:0 0 16px;padding:10px 16px;border-left:3px solid var(--line);background:color-mix(in srgb,var(--line) 30%,transparent);border-radius:0 12px 12px 0;color:var(--ink-2)}
.col-body blockquote p{margin:0}
.col-body .ask{font-weight:800;font-size:17.5px;margin-top:22px}
.lens-list{list-style:none;margin:0;padding:0}
.lens-list li{padding:14px 0;border-bottom:1px solid var(--line)}
.lens-list a{display:block;font-size:17px;font-weight:800;text-decoration:none}
.lens-list small{display:block;color:var(--muted);font-size:12.5px}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .lens-hero,:root:not([data-theme="light"]) .quiz{background:#0F110E;border:1px solid #353A32}}
'''

LENS_JS = '''<script>
document.documentElement.classList.add('js');
(function(){
  var q=document.getElementById('quiz'); if(!q) return;
  var slug=q.getAttribute('data-slug'), ans=document.getElementById('answer'), bs=q.querySelectorAll('.vote button');
  function pick(id, count){
    [].forEach.call(bs,function(b){ b.disabled=true; b.setAttribute('aria-pressed', String(b.getAttribute('data-c')===id)); });
    ans.classList.add('open'); var h=document.getElementById('vote-hint'); if(h) h.textContent='あなたの判定：'+id+'　↓ 証拠が示すこと';
    if(count){ try{ if(window.goatcounter&&window.goatcounter.count) window.goatcounter.count({path:'lens/'+slug+'/vote/'+id,title:'LENS投票 '+slug+' '+id,event:true}); }catch(e){}
      try{ localStorage.setItem('lens-vote-'+slug,id); }catch(e){} }
  }
  [].forEach.call(bs,function(b){ b.addEventListener('click',function(){ pick(b.getAttribute('data-c'), true); ans.scrollIntoView({behavior:'smooth',block:'start'}); }); });
  try{ var v=localStorage.getItem('lens-vote-'+slug); if(v) pick(v,false); }catch(e){}
})();
</script>'''


def lens_src_link(s, flag_map, region_of, cls=''):
    cc = flag_map.get(s.get('region') or region_of.get(s.get('source'), ''), 'xx')
    c = f' class="{cls}"' if cls else ''
    return (f'<a{c} data-c="{cc}" href="{e(s["url"])}" target="_blank" rel="noopener" '
            f'data-track="click/lens/{e(s.get("source",""))}">{e(s["source"])}</a>')


def lens_issue_blocks(L, slug, flag_map, region_of):
    B = []
    U = L['unreported']
    B.append('<section class="lens-sec"><div class="lens-sh"><span class="no">1</span><h2>日本では見当たらなかった話</h2></div>'
             f'<p class="lens-lead">{e(U.get("lead", "海外の記事にだけ書かれていた話です。"))}</p>')
    for i, it in enumerate(U['items'], 1):
        cc = flag_map.get(it.get('region', ''), 'xx')
        k = it.get('kind', 'news')
        also = ''
        if it.get('also'):
            also = '<span class="also">同じ話を伝えた媒体：' + '、'.join(lens_src_link(x, flag_map, region_of) for x in it['also']) + '</span>'
        B.append(f'<article class="uc">'
                 f'<div class="ucm"><span class="bigflag" data-c="{cc}"></span><div><b>{e(it["source"])}</b><small>{e(it.get("region", ""))} · {e(LANG.get(it.get("lang"), ""))}</small></div>'
                 f'<span class="kind {k}" title="{e(KIND_TIP.get(k, ""))}">{KIND.get(k, "報道")}</span></div>'
                 f'<h3>{e(it["headline"])}</h3><p>{e(it["body"])}</p>'
                 f'<div class="ucf">'
                 f'<a href="{e(it["url"])}" target="_blank" rel="noopener" data-track="click/lens/{e(slug)}/{i}">原文を読む（{e(it["source"])}）↗</a>{also}</div></article>')
    B.append(f'<p class="lens-note">{e(U["note"])}</p></section>')

    M = L['mystery']
    ev = ''
    for x in M['evidence']:
        links = ''.join(lens_src_link(s, flag_map, region_of) for s in x['sources'])
        ev += f'<div class="ev"><div class="evl">{e(x["label"])}</div><div><h4>{e(x["head"])}</h4><p>{e(x["body"])}</p><div class="evs">{links}</div></div></div>'
    ch = ''.join(f'<button type="button" data-c="{e(c["id"])}" aria-pressed="false"><b>{e(c["id"])}</b><span>{e(c["text"])}</span></button>' for c in M['choices'])
    A = M['answer']
    B.append('<section class="lens-sec"><div class="lens-sh"><span class="no">2</span><h2>' + e(M['title']) + '</h2></div>'
             f'<p class="lens-lead">{e(M["lead"])}</p>'
             f'<div class="quiz" id="quiz" data-slug="{e(slug)}"><div class="qk">WHO\'S RIGHT?</div><h3>{M["questionHtml"]}</h3><p class="qd">{e(M["setup"])}</p>'
             f'{ev}<p class="vote-q">あなたの判定は？</p><div class="vote">{ch}</div><p class="vh" id="vote-hint">選ぶと、証拠が示すことが表示されます</p></div>'
             f'<div class="answer" id="answer"><h4>{e(A["title"])}<span class="tg">分析</span></h4><ol>'
             + ''.join(f'<li>{e(p)}</li>' for p in A['points']) + f'</ol><p class="caveat">{e(A["caveat"])}</p></div></section>')

    return B


def site_entrance(arch, slug):
    """Entrance to the rest of the site right after a column's body (owner's OK, 1 Oct 2026)."""
    xs = sorted((a for a in arch['articles'].values() if a.get('kind') != 'fan'),
                key=lambda a: a.get('published', ''), reverse=True)[:3]
    li = ''.join(f'<li><a href="/news/{e(a["id"])}/" data-track="click/lens/{e(slug)}/entrance-news">{e(a["title"])}</a>'
                 f'<small>{e(a["source"])}</small></li>' for a in xs)
    return ('<section class="gw-next"><p class="gw-k">F1 Grid Walk</p>'
            '<h2>世界のF1ニュースを、毎日日本語で</h2>'
            '<p class="gw-lead">海外の記事の要約を、毎日載せています。いま届いているニュース：</p>'
            f'<ul>{li}</ul>'
            f'<a class="gw-btn" href="/" data-track="click/lens/{e(slug)}/entrance-top">今日のF1ニュースを見る →</a>'
            f'<a class="gw-sub" href="/lens/" data-track="click/lens/{e(slug)}/entrance-lens">ほかのコラムを読む</a></section>')



COL_TAG = {'world': 'WORLD GRID', 'deep': 'DEEP GRID', 'off': 'OFF GRID'}


def ctag(kind, no=''):
    """Coloured corner tag for column lists (owner's request, 6 Oct 2026): WORLD GRID orange, DEEP GRID burgundy, OFF GRID teal."""
    return f'<span class="ctag ctag-{kind}">{COL_TAG[kind]}</span>' + (f'<span class="ctag-no">{e(no)}</span>' if no else '')


def lens_kind(L):
    return 'off' if L.get('series') == 'offgrid' else 'world'


ALL_COLS = []  # every published column of the three corners, newest first (filled in build_lenses)


def collect_columns(all_lens):
    """WORLD GRID + OFF GRID (lens JSON) and DEEP GRID issues in one list, newest first (owner, 6 Oct 2026)."""
    global ALL_COLS
    out = []
    for p, s_, L in all_lens:
        out.append({'dt': p, 'kind': lens_kind(L), 'url': f'/lens/{s_}/', 'title': L['title'], 'sub': L.get('gpLabel', 'コラム'), 'no': '',
                    'txt': ' '.join([s_, L.get('gpLabel', ''), L.get('noteTags', ''), L['title']]), 'circuit': L.get('circuit'), 'teams': L.get('teams') or []})
    for D in DEEPS:
        out.append({'dt': datetime.fromisoformat(D['published']), 'kind': 'deep', 'url': f'/deep/{D["slug"]}/', 'title': D['title'], 'sub': '', 'no': deep_no(D),
                    'txt': ' '.join([D['slug'], D['title']]), 'circuit': D.get('circuit'), 'teams': D.get('teams') or []})
    out.sort(key=lambda x: x['dt'], reverse=True)
    ALL_COLS = out
    return out


def col_li(x, track):
    sub = ' · '.join(v for v in (x['sub'], jst_text(x['dt'])) if v)
    return (f'<li><a href="{e(x["url"])}" data-track="{e(track)}">{ctag(x["kind"], x["no"])}<b>{e(x["title"])}</b>'
            f'<small>{e(sub)}</small></a></li>')


def more_columns(cur_url, page='lens', n=8):
    """End of every column page: the newest other columns of all three corners, with corner tags (owner, 6 Oct 2026)."""
    others = [x for x in ALL_COLS if x['url'] != cur_url][:n]
    if not others:
        return f'<!--related:{cur_url}-->'
    k = 'mc' if page == 'lens' else 'md'
    sec = 'more-cols' if page == 'lens' else 'more-deep'
    li = ''.join(col_li(x, f'click/{page}/more{x["url"]}') for x in others)
    return (f'<!--related:{cur_url}--><section class="{sec}"><p class="{k}-k">COLUMNS</p><h2>ほかのコラムを読む</h2>'
            f'<ul>{li}</ul>'
            f'<a class="{k}-btn" href="/columns/" data-track="click/{page}/more-all">すべてのコラムを見る →</a>'
            f'<a class="{k}-sub" href="/" data-track="click/{page}/entrance-top">今日のF1ニュースを見る</a></section>')


ALLCOL_CSS = """
.col-legend{margin:6px 0 18px;font-size:13.5px;line-height:2.1;color:var(--ink-2)}
.col-legend .ctag{margin:0 8px 0 0}
.col-legend a{color:var(--ink);font-weight:700}
.col-list{list-style:none;margin:0;padding:0}
.col-list li{border-top:1px solid var(--line)}
.col-list li a{display:block;padding:14px 0;color:var(--ink);text-decoration:none}
.col-list li b{display:block;font-family:'Noto Serif JP','Noto Serif CJK JP','Hiragino Mincho ProN','Yu Mincho',serif;font-weight:900;font-size:17px;line-height:1.5}
.col-list li a:hover b{text-decoration:underline;text-underline-offset:3px}
.col-list li small{display:block;margin-top:3px;color:var(--muted);font-size:12px}
"""


def build_all_columns():
    """columns/index.html: every column of WORLD GRID, DEEP GRID and OFF GRID, newest first, with corner tags."""
    if not ALL_COLS:
        return []
    items = ''.join(col_li(x, 'click/columns' + x['url']) for x in ALL_COLS)
    body = ('<nav class="crumbs"><a href="/">トップ</a> › すべてのコラム</nav><h1>すべてのコラム</h1>'
            '<p class="lead">F1 Grid Walk のコラムを、新しい順にすべて並べています。</p>'
            + (('<section class="yk-mini"><p class="yk-mh"><b>STORY</b><span>コラムとは別の、F1 Grid Walk 独自の記事</span></p><ul>'
                + ''.join(f'<li><a href="/topics/{e(H["slug"])}/" data-track="click/columns-yk/{e(H["slug"])}">{e(H["title"])}</a></li>' for H in hubs_newest()[:3]) + '</ul>'
                + '<a class="yk-all" href="/topics/">すべての STORY →</a></section>') if HUBS else '')
            + 
            '<p class="col-legend">' + ctag('world') + '<span>世界の見方を、日本語で。 <a href="/lens/">一覧</a></span><br>'
            + ctag('deep') + '<span>ニュースの、その奥へ。 <a href="/deep/">一覧</a></span><br>'
            + ctag('off') + '<span>本筋の外の、F1こぼれ話。 <a href="/offgrid/">一覧</a></span></p>'
            f'<ul class="col-list">{items}</ul>')
    write('columns/index.html', page('F1コラム一覧｜海外報道の読み比べ・深掘り解説・こぼれ話｜F1グリッドウォーク', 'F1グリッドウォークのコラムを新しい順にすべて。海外報道の読み比べ（WORLD GRID）、ニュースの深掘り解説（DEEP GRID）、こぼれ話（OFF GRID）。',
                                     SITE + '/columns/', body, f'<style>{LENS_CSS}{ALLCOL_CSS}{YK_CSS}</style>\n', og_type='website'))
    return [(SITE + '/columns/', ALL_COLS[0]['dt'].isoformat(timespec='seconds'), 'daily', '0.8')]


def build_lenses(arch, flag_map):
    """Render lens/<slug>/index.html for every lens/<slug>.json, plus lens/index.html. Returns sitemap rows."""
    d = os.path.join(ROOT, 'lens')
    if not os.path.isdir(d):
        return []
    region_of = {}
    for a in arch['articles'].values():
        region_of.setdefault(a['source'], a.get('region'))
    lenses = []
    all_lens = []  # (published, slug, L) of every published issue, newest first, for the "other columns" list
    for fn in sorted(os.listdir(d)):
        if fn.endswith('.json'):
            L0 = load(os.path.join('lens', fn))
            if L0 and L0.get('slug') and ID_OK.match(L0['slug']) and not L0.get('draft') and L0.get('published'):
                all_lens.append((datetime.fromisoformat(L0['published']), L0['slug'], L0))
    all_lens.sort(key=lambda x: x[0], reverse=True)
    collect_columns(all_lens)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.json'):
            continue
        L = load(os.path.join('lens', fn))
        if not L or not L.get('slug') or not ID_OK.match(L['slug']):
            continue
        if L.get('draft'):
            # drafts are not published: remove any page built earlier
            old = os.path.join(ROOT, 'lens', L['slug'], 'index.html')
            if os.path.exists(old):
                os.remove(old)
                try: os.rmdir(os.path.dirname(old))
                except OSError: pass
            continue
        slug = L['slug']
        url = f'{SITE}/lens/{slug}/'
        # the source desk: every article on the topic we already carry, plus the extra sources used here
        desk, seen = [], set()
        topic_arts = sorted([a for a in arch['articles'].values() if a.get('topic') in (L.get('topics') or [L.get('topic')]) and a.get('kind') != 'fan'], key=when, reverse=True)
        for a in topic_arts:
            desk.append({'source': a['source'], 'region': a.get('region'), 'lang': a.get('lang'), 'title': a['title'], 'url': a['url'], 'page': f'/news/{a["id"]}/'})
        for s in L.get('extraSources', []) + [it for it in L.get('unreported', {}).get('items', [])]:
            desk.append({'source': s['source'], 'region': s.get('region'), 'lang': s.get('lang'), 'title': s.get('headline') or s.get('title'), 'url': s['url']})
        for x in L.get('mystery', {}).get('evidence', []):
            for s in x.get('sources', []):
                if s.get('title'):
                    desk.append({'source': s['source'], 'region': s.get('region'), 'lang': s.get('lang'), 'title': s['title'], 'url': s['url']})
        out = []
        for s in desk:
            if s['url'] in seen:
                continue
            seen.add(s['url']); out.append(s)
        desk = out
        n_src = len({s['source'] for s in desk})
        n_cty = len({(s.get('region') or region_of.get(s['source'])) for s in desk} - {None, ''})
        pub = datetime.fromisoformat(L['published'])

        B = []
        off = L.get('series') == 'offgrid'  # OFF GRID (余談 columns; owner, 3 Oct 2026): same page format, own corner
        sec_name, sec_url = ('OFF GRID', '/offgrid/') if off else ('WORLD GRID', '/lens/')
        B.append(f'<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › <a href="{sec_url}">{sec_name}</a> › {e(L["gpLabel"])}</nav>')
        B.append(f'<div class="lens-hero" data-big="{e(L.get("big", ""))}"><div class="lens-ey">{sec_name} · {e(L["gpLabel"])}</div>'
                 f'<h1>{L["titleHtml"]}</h1><p class="dek">{e(L["dek"])}</p><p class="date">{e(jst_text(pub))} 公開</p>'
                 '</div>')
        if L.get('type') == 'column':
            B.append('<div class="col-body">')
            # 事前の注目点 → 答え合わせ: a 読み解き that answers one of this preview's points (review of 12 Oct 2026)
            answers = {pv['h2']: (H, pv) for H in HUBS.values() for pv in H.get('preview', []) if pv.get('lens') == slug}
            open_h2 = None
            def answer_box(h2):
                if h2 not in answers:
                    return ''
                H, pv = answers[h2]
                d = pv.get('added', '')
                d = f'{int(d[5:7])}/{int(d[8:10])} ' if len(d) >= 10 else ''
                return (f'<a class="ans-box" href="/topics/{e(H["slug"])}/" data-track="click/lens/{e(slug)}/answer">'
                        f'<small>決勝のあとで（{d}追記）</small><b>この注目点は、どうなった？</b>'
                        f'<span>STORY「{e(H["title"])}」 →</span></a>')
            for blk in L['body']:
                k, t = blk[0], blk[1]
                if k == 'h2' and open_h2:
                    B.append(answer_box(open_h2))
                if k == 'h2':
                    open_h2 = t
                if k == 'h2': B.append(f'<h2>{e(t)}</h2>')
                elif k == 'quote': B.append(f'<blockquote><p>{site_links(e(t))}</p></blockquote>')
                elif k == 'bold': B.append(f'<p><strong>{site_links(e(t))}</strong></p>')
                elif k == 'ask': B.append(f'<p class="ask">{site_links(e(t))}</p>')
                else: B.append(f'<p>{site_links(e(t))}</p>')
            if open_h2:
                B.append(answer_box(open_h2))
            B.append('</div>')
            B.append(more_columns(f'/lens/{slug}/'))
            if L.get('note'):
                B.append(f'<p class="lens-note">{e(L["note"])}</p>')
            L.setdefault('unreported', {'items': []}); L.setdefault('mystery', {'evidence': []})
        else:
            B.extend(lens_issue_blocks(L, slug, flag_map, region_of))
            B.append(more_columns(f'/lens/{slug}/'))
        for D in DEEPS:
            if slug in (D.get('lensRelated') or []):
                B.append(deep_card(D, lead='なぜそうなった？を深く読む'))
                break
        B.append(rules_entry('lens'))
        rows = ''
        for s in desk:
            cc = flag_map.get(s.get('region') or region_of.get(s['source'], ''), 'xx')
            extra = f'<a class="sum" href="{e(s["page"])}">要約を読む</a>' if s.get('page') else ''
            rows += (f'<li><span class="srcbadge" data-c="{cc}">{e(s["source"])}</span><span>{e(LANG.get(s.get("lang"), ""))}</span>{extra}'
                     f'<a class="t" href="{e(s["url"])}" target="_blank" rel="noopener" data-track="click/lens/{e(slug)}/desk">{e(s["title"])} ↗</a></li>')
        B.append(f'<section class="lens-sec sdesk"><h2>SOURCE DESK</h2><p class="lens-lead">この記事のもとになった{len(desk)}本の記事（{n_src}媒体）。すべて原文に飛びます。</p><ul>{rows}</ul></section>')
        if L.get('noteUrl'):
            B.append(f'<p class="lens-note" style="margin-top:22px">この回の読みものはnoteでも公開しています → <a href="{e(L["noteUrl"])}" target="_blank" rel="noopener" data-track="click/lens/{e(slug)}/note">noteで読む ↗</a></p>')
        B.append('<p class="credit" style="text-align:left;margin-top:22px">要約と比較は F1 Grid Walk が各記事をもとに独自にまとめたものです。記事の著作権は各媒体に帰属します。</p>')

        title = f'{L["title"]}｜F1グリッドウォーク'
        head = f'<meta property="article:published_time" content="{e(L["published"])}">\n<style>{LENS_CSS}{DEEP_CSS if any(slug in (D.get("lensRelated") or []) for D in DEEPS) else ""}</style>\n'
        ogp = os.path.join(ROOT, 'lens', slug, 'og.png')  # the column's own header image, when present
        ogi = f'{SITE}/lens/{slug}/og.png?v={hashlib.md5(open(ogp, "rb").read()).hexdigest()[:8]}' if os.path.exists(ogp) else None
        head += ld({'@context': 'https://schema.org', '@type': 'Article', 'headline': L['title'], 'description': L['dek'],
                    'datePublished': L['published'], 'dateModified': L.get('updated') or L['published'], 'inLanguage': 'ja',
                    'image': [ogi or OG_IMAGE], 'mainEntityOfPage': url, 'author': PUBLISHER, 'publisher': PUBLISHER,
                    'articleSection': sec_name})
        head += ld({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'F1 Grid Walk', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': sec_name, 'item': SITE + sec_url},
            {'@type': 'ListItem', 'position': 3, 'name': L['title'], 'item': url}]})
        used = set()
        body_html = link_terms_html('\n'.join(B), used)
        head = MONO_FONT + head + f'<style>{RULES_ENTRY_CSS}{RULES_CSS if used else ""}</style>\n'
        write(f'lens/{slug}/index.html', page(title, L['dek'], url, body_html + term_assets(used) + LENS_JS, head, og_image=ogi, og_size=(1280, 670)))
        lenses.append((pub, slug, L, url))

    lenses.sort(key=lambda x: x[0], reverse=True)
    all_rows = lenses
    offs = [x for x in lenses if x[2].get('series') == 'offgrid']
    lenses = [x for x in lenses if x[2].get('series') != 'offgrid']
    off_rows = build_offgrid(offs)
    # link the newest lens from the top page (inside <!--pre:lens--> in index.html)
    ip = os.path.join(ROOT, 'index.html'); src = open(ip, encoding='utf-8').read()
    blk = ''
    if lenses:
        p0, s0, L0, u0 = lenses[0]
        # top page: LENS and DEEP GRID as two equal rows in one frame (owner's choice E, 3 Oct 2026)
        blk = (f'<a class="duo-row duo-lens" href="/lens/{e(s0)}/" data-track="click/top/lens"><span class="duo-q"><small>WORLD GRID</small><strong>世界の見方を、日本語で。</strong></span>'
               f'<b>{e(L0["title"])}&#8288;<i aria-hidden="true">→</i></b></a>')
    out = re.sub(r'(<!--pre:lens-->).*?(<!--/pre:lens-->)', lambda m: m.group(1) + blk + m.group(2), src, count=1, flags=re.S)
    if out != src:
        open(ip, 'w', encoding='utf-8').write(out)
    if not lenses:
        old = os.path.join(ROOT, 'lens', 'index.html')
        if os.path.exists(old):
            os.remove(old)
        return off_rows + [(u, p.isoformat(timespec='seconds'), None, '0.9') for p, s, L, u in all_rows]
    items = ''.join(f'<li>{ctag("world")}<a href="/lens/{e(s)}/">{e(L["title"])}</a><small>{e(L["gpLabel"])} · {e(jst_text(p))}</small></li>' for p, s, L, u in lenses)
    body = ('<nav class="crumbs"><a href="/">トップ</a> › WORLD GRID</nav><h1>WORLD GRID</h1>'
            '<p class="lead">毎朝7時のコラムと、レース週末の金・土・日に出すグランプリ特別号。世界の媒体の記事を読み比べて、日本語ではあまり語られない話と、見出しだけでは分からないことを届けます。</p>'
            f'<ul class="lens-list">{items}</ul>')
    write('lens/index.html', page('海外F1報道を読み比べるコラム WORLD GRID｜F1グリッドウォーク', 'イタリア、ドイツ、オランダ、スペイン……世界のF1報道を日本語で読み比べるコラム。日本語ではあまり語られない話と、見出しだけでは分からないことを、毎朝のコラムとグランプリ特別号で。',
                                  SITE + '/lens/', body, f'<style>{LENS_CSS}</style>\n', og_type='website'))
    return [(SITE + '/lens/', lenses[0][0].isoformat(timespec='seconds') if lenses else None, 'weekly', '0.8')] + off_rows + \
           [(u, p.isoformat(timespec='seconds'), None, '0.9') for p, s, L, u in all_rows]


OFFGRID_COPY = '本筋の外の、F1こぼれ話。'
OFFGRID_CSS = '''
.og-h{display:inline-block;margin:10px 0 0;padding:6px 16px;border-radius:10px;background:#2F6B66;color:#FFFFFF;letter-spacing:.06em}
.og-copy{margin:10px 0 4px;font-size:15px;color:var(--muted);font-weight:600}
.og-empty{margin:22px 0 0;padding:22px 18px;border:1px dashed var(--line);border-radius:16px;background:var(--surface);color:var(--ink-2);font-size:15px;line-height:1.9}
.og-empty a{color:var(--ink);font-weight:700}
'''


def build_offgrid(offs):
    """offgrid/index.html: the list of OFF GRID 余談 columns (lens JSON with "series": "offgrid").
    The corner exists before its first column, so the page shows a short "coming soon" note when empty."""
    if offs:
        items = ''.join(f'<li>{ctag("off")}<a href="/lens/{e(s)}/">{e(L["title"])}</a><small>{e(L["gpLabel"])} · {e(jst_text(p))}</small></li>' for p, s, L, u in offs)
        lst = f'<ul class="lens-list">{items}</ul>'
    else:
        lst = ('<p class="og-empty">最初のコラムは、まもなくここに載ります。<br>それまでは <a href="/lens/">WORLD GRID</a> と '
               '<a href="/deep/">DEEP GRID</a> のコラムをどうぞ。</p>')
    body = ('<nav class="crumbs"><a href="/">トップ</a> › OFF GRID</nav>'
            '<h1 class="og-h">OFF GRID</h1>'
            f'<p class="og-copy">{OFFGRID_COPY}</p>'
            '<p class="lead">ニュースの本筋からは少し外れるけれど、知るとF1がもっと面白くなる話。サーキットの小さな出来事や、記事の片すみにあった一言を拾います。</p>'
            + lst)
    write('offgrid/index.html', page('F1のこぼれ話コラム OFF GRID｜F1グリッドウォーク', 'グリッドの塗り直し、ドライバーの雨講座、ほうきにまたがったマーシャル……F1ニュースの本筋の外にある、知ると面白いこぼれ話のコラム。',
                                     SITE + '/offgrid/', body, f'<style>{LENS_CSS}{OFFGRID_CSS}</style>\n', og_type='website'))
    return [(SITE + '/offgrid/', offs[0][0].isoformat(timespec='seconds') if offs else None, 'weekly', '0.7')]



# ---------------------------------------------------------------- DEEP GRID
# deep/<slug>.json -> deep/<slug>/index.html, deep/index.html. "ニュースの、その奥へ。"
DEEP_COPY = 'ニュースの、その奥へ。'
DEEPS = []  # published issues, newest first (filled by load_deeps)

DEEP_CSS = '''
.ctag{display:inline-block;font-weight:800;font-size:11px;line-height:1;letter-spacing:.1em;padding:5px 10px;border-radius:999px;margin:0 0 7px;vertical-align:middle;white-space:nowrap}
.ctag-world{background:#E8946C;color:#1F2420}.ctag-deep{background:#8E2F3B;color:#FFFFFF}.ctag-off{background:#2F6B66;color:#FFFFFF}
.ctag-no{display:inline-block;margin:0 0 7px 8px;font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.06em;vertical-align:middle}

.more-deep{margin:30px 0 8px;padding:20px 18px 18px;border-radius:16px;background:var(--surface);border:1px solid var(--line);border-top:4px solid #8E2F3B}
.md-k{margin:0;font:600 12px/1 'Fraunces',Georgia,serif;letter-spacing:.24em;color:#8E2F3B}
.more-deep h2{margin:8px 0 10px;font-size:22px;line-height:1.4}
.more-deep ul{list-style:none;margin:0 0 16px;padding:0}
.more-deep li{border-top:1px solid var(--line)}
.more-deep li a{display:block;padding:12px 0;color:var(--ink);text-decoration:none}
.more-deep li b{display:block;font-family:'Noto Serif JP','Noto Serif CJK JP','Hiragino Mincho ProN','Yu Mincho',serif;font-weight:900;font-size:17px;line-height:1.5}
.more-deep li a:hover b{text-decoration:underline;text-underline-offset:3px}
.more-deep li small{display:block;margin-top:3px;color:var(--muted);font-size:12px}
.md-btn{display:block;text-align:center;background:#8E2F3B;color:#FFFFFF;text-decoration:none;font-weight:800;font-size:16px;padding:14px 12px;border-radius:12px}
.md-sub{display:block;text-align:center;margin-top:12px;font-size:13.5px;color:var(--muted);font-weight:600}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .md-k{color:#D98C96}}
:root[data-theme="dark"] .md-k{color:#D98C96}
.dg{--dgw:700px}
.dg-top{margin:26px 0 0;padding-top:10px;background:linear-gradient(var(--ink),var(--ink)) top/100% 3px no-repeat,linear-gradient(var(--ink),var(--ink)) 0 6px/100% 1px no-repeat}
.dg-label{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:4px 12px;padding-top:8px}
.dg-label b{font-family:var(--logo);font-weight:600;font-size:13px;letter-spacing:.32em;color:var(--ink)}
.dg-label b i{font-style:normal;color:var(--clay);letter-spacing:.12em;margin-left:6px}
.dg-label span{font-size:12px;color:var(--muted);letter-spacing:.12em}
.dg h1{font-size:clamp(26px,6vw,38px);line-height:1.4;margin:18px 0 12px;letter-spacing:.01em}
.dg-dek{font-size:16.5px;line-height:1.95;color:var(--ink-2);margin:0 0 14px}
.dg-meta{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--muted);margin:0 0 12px}
.dg-themes{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 18px}
.dg-themes span{font-size:12px;border:1px solid var(--line);border-radius:999px;padding:1px 11px;color:var(--ink-2)}
.dg-toc{display:flex;gap:8px;overflow-x:auto;padding:2px 0 12px;margin:0 0 6px;border-bottom:1px solid var(--line);scrollbar-width:none}
.dg-toc::-webkit-scrollbar{display:none}
.dg-toc a{flex:0 0 auto;font-size:13px;text-decoration:none;color:var(--ink);border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:4px 13px;white-space:nowrap}
.dg-layer{display:flex;align-items:center;gap:10px;margin:40px 0 14px;font-size:12px;font-weight:700;letter-spacing:.14em;color:var(--muted)}
.dg-layer .g{display:inline-flex;gap:3px}
.dg-layer .g i{width:14px;height:5px;border-radius:2px;background:var(--line)}
.dg-layer .g i.on{background:var(--clay)}
.dg-layer em{font-style:normal;color:var(--ink);font-size:15px;letter-spacing:.04em}
.dg-quick{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:6px 18px 6px 18px;margin:0}
.dg-quick ol{margin:0;padding:0;list-style:none;counter-reset:q}
.dg-quick li{counter-increment:q;position:relative;padding:12px 0 12px 34px;border-bottom:1px solid var(--line);font-size:15.5px;line-height:1.85}
.dg-quick li:last-child{border-bottom:0}
.dg-quick li::before{content:counter(q);position:absolute;left:0;top:13px;width:22px;height:22px;border-radius:50%;background:var(--ink);color:var(--on-ink);font-size:12px;font-weight:700;line-height:22px;text-align:center}
.dg-sec{margin:34px 0 0}
.dg-sec h2{display:flex;gap:12px;align-items:baseline;font-size:20px;line-height:1.5;margin:0 0 12px;padding-top:14px;border-top:1px solid var(--line)}
.dg-sec h2 .n{font-family:var(--logo);font-weight:600;font-size:15px;color:var(--clay);flex-shrink:0}
.dg p{font-size:16.5px;line-height:2;margin:0 0 16px}
.dg blockquote{margin:6px 0 18px;padding:2px 0 2px 16px;border-left:2px solid var(--ink)}
.dg blockquote p{margin:0 0 4px;font-weight:500}
.dg blockquote cite{font-style:normal;font-size:12.5px;color:var(--muted)}
.dg-view{border:1px dashed var(--clay);border-radius:12px;padding:12px 16px;margin:8px 0 16px}
.dg-view p{margin:0;font-size:15.5px}
details.dg-deep{margin:44px 0 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
details.dg-deep>summary{list-style:none;cursor:pointer;padding:16px 0}
details.dg-deep>summary::-webkit-details-marker{display:none}
details.dg-deep .dg-layer{margin:0 0 8px}
.dg-open{display:flex;align-items:center;justify-content:space-between;gap:12px;font-weight:700;font-size:15.5px}
.dg-open::after{content:"＋ 開く";flex-shrink:0;font-size:13px;border:1px solid var(--ink);border-radius:999px;padding:3px 12px}
details[open].dg-deep .dg-open::after{content:"－ 閉じる"}
.dg-deep-sub{display:block;font-size:13px;font-weight:400;color:var(--muted);margin-top:4px}
.dg-tw{overflow-x:auto;margin:4px 0 8px;-webkit-overflow-scrolling:touch}
.dg table{border-collapse:collapse;min-width:100%;font-size:14px;line-height:1.6}
.dg th,.dg td{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.dg thead th{background:var(--surface);font-size:12.5px;color:var(--ink-2);white-space:nowrap}
.dg tbody th{font-weight:700;white-space:nowrap}
.dg .tnote{font-size:12.5px;color:var(--muted);margin:0 0 16px;line-height:1.7}
.dg dl{margin:0}
.dg dt{font-weight:700;font-size:15px;margin:14px 0 2px}
.dg dd{margin:0;font-size:14.5px;line-height:1.85;color:var(--ink-2)}
.dg-src{font-size:13px;line-height:1.7;padding-left:20px;margin:0}
.dg-src li{margin:0 0 6px}
.dg-src small{color:var(--muted)}
.dg-hist{list-style:none;padding:0;margin:0;font-size:13.5px;color:var(--ink-2)}
.dg-hist time{font-weight:700;margin-right:10px}
.dg-end{margin:36px 0 0;padding-top:14px;border-top:1px solid var(--line)}
.dg-end h2{font-size:15px;letter-spacing:.06em;margin:0 0 8px}
.dg-end .k{font-family:var(--logo);font-weight:600;font-size:11.5px;letter-spacing:.3em;color:var(--clay);display:block;margin-bottom:2px}
.dg-fig{margin:10px 0 18px;padding:14px 14px 10px;background:var(--surface);border:1px solid var(--line);border-radius:14px;--cS:#D3302F;--cM:#E2AE00;--cH:#FBF9F4;--cI:#2E9447;--cW:#2F6FD0;--bar:#9E4E2B;--tS:#FFFFFF;--tM:#1F2420;--tH:#1F2420;--tI:#FFFFFF;--tW:#FFFFFF}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .dg-fig{--cS:#E5544C;--cM:#E9BC2A;--cH:#ECE7DC;--cI:#3FAE5C;--bar:#E09A76;--tS:#191C18;--tM:#191C18;--tH:#191C18;--tI:#191C18;--cW:#6B9BE8;--tW:#191C18}}
:root[data-theme="dark"] .dg-fig{--cS:#E5544C;--cM:#E9BC2A;--cH:#ECE7DC;--cI:#3FAE5C;--bar:#E09A76;--tS:#191C18;--tM:#191C18;--tH:#191C18;--tI:#191C18;--cW:#6B9BE8;--tW:#191C18}
.dg-fig figcaption{font-size:14.5px;font-weight:700;line-height:1.6;margin:0 0 8px}
.dg-fig svg{display:block;width:100%;height:auto;max-width:640px;font-family:var(--sans)}
.dg-fig .lg{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--ink-2);margin:0 0 6px}
.dg-fig .lg i{display:inline-block;width:14px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px;border:1px solid var(--ink)}
.dg-fig .fn{font-size:12px;color:var(--muted);line-height:1.7;margin:6px 0 0}
.dg-fig .t{fill:var(--ink);font-size:12px}.dg-fig .ts{fill:var(--muted);font-size:10.5px}.dg-fig .tv{fill:var(--ink);font-size:12px;font-weight:700}
.dg-fig .ax{stroke:var(--line);stroke-width:1}.dg-fig .mk{stroke:var(--muted);stroke-width:1;stroke-dasharray:3 3}
.dg-fig .sg:hover rect,.dg-fig .br:hover rect{opacity:.8}
.dg-fig .zs{display:grid;gap:8px;margin:8px 0 0;max-width:640px}
.dg-fig .zs b{display:block;font-size:13px}.dg-fig .zs span{display:block;font-size:12.5px;line-height:1.65;color:var(--ink-2)}
.dg-card{display:block;text-decoration:none;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin:8px 0}
.dg-card small{display:block;font-size:11.5px;letter-spacing:.14em;color:var(--muted);font-weight:700}
.dg-card b{display:block;font-size:15.5px;line-height:1.6;margin-top:2px}
.dg-list{list-style:none;margin:0;padding:0}
.dg-list li{padding:16px 0;border-bottom:1px solid var(--line)}
.dg-list a{text-decoration:none}
.dg-list small{display:block;font-family:var(--logo);font-weight:600;letter-spacing:.24em;font-size:12px;color:var(--clay)}
.dg-list b{display:block;font-size:18px;line-height:1.55;margin:4px 0}
.dg-list p{font-size:14px;line-height:1.85;color:var(--ink-2);margin:0}
.dg-from{display:block;margin:22px 0 0;padding:14px 16px 12px;text-decoration:none;color:var(--ink);background:linear-gradient(var(--ink),var(--ink)) top/100% 2px no-repeat,linear-gradient(var(--ink),var(--ink)) 0 5px/100% 1px no-repeat,var(--surface);border-radius:0 0 12px 12px}
.dg-from small{display:block;font-family:var(--logo);font-weight:600;font-size:11.5px;letter-spacing:.28em;color:var(--clay);margin-top:4px}
.dg-from b{display:block;font-size:15.5px;line-height:1.6;margin:2px 0}
.dg-from span{font-size:12.5px;color:var(--muted)}
.dg table.short td{white-space:nowrap}
@media (max-width:600px){.dg p{font-size:16px}.dg-sec h2{font-size:18.5px}
.dg table.stack thead{display:none}
.dg table.stack,.dg table.stack tbody,.dg table.stack tr,.dg table.stack th,.dg table.stack td{display:block;width:100%}
.dg table.stack tr{border-bottom:1px solid var(--line);padding:10px 0}
.dg table.stack th,.dg table.stack td{border:0;padding:2px 0}
.dg table.stack tbody th{font-size:15px;margin-bottom:4px}
.dg table.stack td::before{content:attr(data-h);display:block;font-size:11.5px;font-weight:700;color:var(--muted);letter-spacing:.04em}
.dg table.stack td+td{margin-top:6px}}
.dg-rel-l{list-style:none;margin:0;padding:0}
.dg-rel-l li{border-top:1px solid var(--line)}
.dg-rel-l li:first-child{border-top:0}
.dg-rel-l a{display:block;padding:10px 0;color:var(--ink);text-decoration:none}
.dg-rel-l small{display:block;font-size:12.5px;font-weight:700;color:var(--clay);line-height:1.6}
.dg-rel-l b{display:block;font-size:15.5px;line-height:1.6;margin-top:2px}
.dg-rel-l span{display:block;font-size:12px;color:var(--muted);margin-top:2px}
.dg-rel-l a:hover b{text-decoration:underline;text-underline-offset:3px}
'''


def load_deeps():
    """Read deep/*.json. Drafts are skipped (and any old page removed) unless PREVIEW_DRAFTS=1."""
    global DEEPS
    d = os.path.join(ROOT, 'deep')
    out = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.json'):
                continue
            D = load(os.path.join('deep', fn))
            if not D or not D.get('slug') or not ID_OK.match(D['slug']):
                continue
            if D.get('draft') and os.environ.get('PREVIEW_DRAFTS') != '1':
                old = os.path.join(d, D['slug'], 'index.html')
                if os.path.exists(old):
                    os.remove(old)
                    try: os.rmdir(os.path.dirname(old))
                    except OSError: pass
                continue
            out.append(D)
    out.sort(key=lambda D: D['published'], reverse=True)
    DEEPS = out
    return out


def deep_no(D):
    if D.get('noLabel'):  # e.g. 前編 / 後編 for a two-part issue (owner's request, 6 Oct 2026)
        return D['noLabel']
    return f'#{int(D.get("no", 0)):02d}'


def deep_for_article(a):
    """The newest DEEP GRID issue that goes deeper into this news article (same circuit, team or topic)."""
    for D in DEEPS:
        if (D.get('circuit') and a.get('circuit') == D['circuit']) or \
           (set(D.get('teams') or []) & set(a.get('teams') or [])) or \
           (a.get('topic') and a['topic'] in (D.get('topics') or [])):
            return D
    return None


def deep_card(D, cls='dg-from', lead='この話を、もっと深く'):
    return (f'<a class="{cls}" href="/deep/{e(D["slug"])}/" data-track="click/deep/{e(D["slug"])}/from">'
            f'<small>DEEP GRID {deep_no(D)}</small><b>{e(D["title"])}</b><span>{e(lead)} →</span></a>')


def deep_blocks(blocks, used=None):
    out = []
    for b in blocks:
        if 'p' in b:
            out.append('<p>' + (link_terms_html(site_links(e(b["p"])), used) if used is not None else site_links(e(b["p"]))) + '</p>')
        elif 'quote' in b:
            out.append(f'<blockquote><p>「{e(b["quote"])}」</p><cite>— {e(b.get("who", ""))}</cite></blockquote>')
        elif 'view' in b:
            out.append(f'<div class="dg-view"><p>{e(b["view"])}</p></div>')
        elif 'table' in b:
            t = b['table']
            hs = t.get('head', [])
            longest = max(len(c) for r in t['rows'] for c in r[1:])
            cls = 'stack' if len(hs) >= 3 and longest > 12 else ('short' if longest <= 12 else '')
            head = ''.join(f'<th scope="col">{e(h)}</th>' for h in hs)
            rows = ''.join('<tr>' + f'<th scope="row">{e(r[0])}</th>' + ''.join(f'<td data-h="{e(hs[j + 1] if j + 1 < len(hs) else "")}">{e(c)}</td>' for j, c in enumerate(r[1:])) + '</tr>' for r in t['rows'])
            out.append(f'<div class="dg-tw"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
                       + (f'<p class="tnote">{e(t["note"])}</p>' if t.get('note') else ''))
        elif 'chart' in b:
            out.append(deep_chart(b['chart']))
    return ''.join(out)


TYRE = {'S': ('ソフト', 'S'), 'M': ('ミディアム', 'M'), 'H': ('ハード', 'H'), 'I': ('インターミディエイト', 'I'), 'W': ('フルウェット', 'W'), '?': ('未発表', '?')}


def deep_chart(c):
    """Inline SVG chart for DEEP pages. kind 'stints' (tyre stints per driver) or 'hbar' (horizontal bars)."""
    W, lw = 400, c.get('labelWidth', 96)
    pw = W - lw - 12
    cap = f'<figcaption>{e(c.get("title", ""))}</figcaption>'
    note = f'<p class="fn">{e(c["note"])}</p>' if c.get('note') else ''
    g = []
    if c['kind'] == 'stints':
        laps, rows = c['laps'], c['rows']
        rh, gap, top = 22, 8, 22
        x = lambda lap: lw + (lap - 1) / laps * pw
        H = top + len(rows) * (rh + gap) + 22
        for m in c.get('marks', []):
            mx = x(m['lap'] + 0.5)
            g.append(f'<line class="mk" x1="{mx:.1f}" y1="{top - 4}" x2="{mx:.1f}" y2="{H - 20}"/>'
                     f'<text class="ts" x="{mx:.1f}" y="{top - 8}" text-anchor="middle">{e(m["label"])}</text>')
        for i, r in enumerate(rows):
            y = top + i * (rh + gap)
            g.append(f'<text class="t" x="0" y="{y + rh / 2 + 4:.1f}">{e(r["label"])}</text>')
            for k, a, z in r['stints']:
                x0, x1 = x(a) + 1, x(z + 1) - 1
                name = TYRE[k][0]
                fill = 'url(#dgq)' if k == '?' else f'var(--c{k})'
                txt = '' if x1 - x0 < 13 else f'<text x="{(x0 + x1) / 2:.1f}" y="{y + rh / 2 + 4:.1f}" text-anchor="middle" style="fill:var(--t{k if k != "?" else "H"});font-size:11px;font-weight:700">{TYRE[k][1]}</text>'
                g.append(f'<g class="sg"><title>{e(r["label"])}　{name}　{a}〜{z}周（{z - a + 1}周）</title>'
                         f'<rect x="{x0:.1f}" y="{y}" width="{x1 - x0:.1f}" height="{rh}" rx="4" fill="{fill}" stroke="var(--ink)" stroke-width="{1 if k in "H?" else 0}"/>{txt}</g>')
        for t in c.get('ticks', [1, 10, 20, 30, 40, 50, laps]):
            tx = x(t + 0.5) if t != 1 else x(1)
            g.append(f'<text class="ts" x="{tx:.1f}" y="{H - 6}" text-anchor="middle">{t}</text>')
        g.append(f'<text class="ts" x="{W}" y="{H - 6}" text-anchor="end"></text>')
        used = []
        for r in rows:
            for k, _, _ in r['stints']:
                if k not in used:
                    used.append(k)
        order = [k for k in 'ISMHW?' if k in used]
        lg = '<div class="lg">' + ''.join(
            f'<span><i style="background:{"repeating-linear-gradient(135deg,var(--line) 0 3px,transparent 3px 6px)" if k == "?" else f"var(--c{k})"}"></i>{e(TYRE[k][0])}（{TYRE[k][1]}）</span>' for k in order) + '<span>横軸は周回</span></div>'
        defs = '<defs><pattern id="dgq" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--surface)"/><line x1="0" y1="0" x2="0" y2="6" stroke="var(--muted)" stroke-width="2"/></pattern></defs>'
        svg = f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(c.get("title", ""))}">{defs}{"".join(g)}</svg>'
        return f'<figure class="dg-fig">{cap}{lg}{svg}{note}</figure>'
    if c['kind'] == 'hbar':
        rows = c['rows']
        rh, gap, top = 22, 10, 4
        vmax = max(r['v'] for r in rows) or 1
        vw = max(sum(7 if ch.isascii() else 12 for ch in r['text']) for r in rows) + 10
        H = top + len(rows) * (rh + gap)
        for i, r in enumerate(rows):
            y = top + i * (rh + gap)
            bw = max(2, r['v'] / vmax * (pw - vw))
            fill = f'var(--c{r["c"]})' if r.get('c') else 'var(--bar)'
            stroke = ' stroke="var(--ink)" stroke-width="1"' if r.get('c') == 'H' else ''
            g.append(f'<g class="br"><title>{e(r["label"])}　{e(r["text"])}</title>'
                     f'<text class="t" x="0" y="{y + rh / 2 + 4:.1f}">{e(r["label"])}</text>'
                     f'<rect x="{lw}" y="{y}" width="{bw:.1f}" height="{rh}" rx="4" fill="{fill}"{stroke}/>'
                     f'<text class="tv" x="{lw + bw + 6:.1f}" y="{y + rh / 2 + 4:.1f}">{e(r["text"])}</text></g>')
        lg = ''
        if c.get('legend'):
            lg = '<div class="lg">' + ''.join(f'<span><i style="background:var(--c{k})"></i>{e(TYRE[k][0])}</span>' for k in c['legend']) + '</div>'
        svg = f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(c.get("title", ""))}">{"".join(g)}</svg>'
        return f'<figure class="dg-fig">{cap}{lg}{svg}{note}</figure>'
    if c['kind'] == 'zones':
        zs = c['zones']
        zw = W / len(zs)
        H = 40
        for i, z in enumerate(zs):
            x0 = i * zw
            g.append(f'<rect x="{x0 + 1:.1f}" y="18" width="{zw - 2:.1f}" height="22" rx="4" fill="var(--c{z["c"]})"/>'
                     f'<text x="{x0 + zw / 2:.1f}" y="33" text-anchor="middle" style="fill:var(--t{z["c"]});font-size:12px;font-weight:700">{e(z["label"])}</text>')
        g.append(f'<text class="ts" x="0" y="11">{e(c.get("left", ""))}</text><text class="ts" x="{W}" y="11" text-anchor="end">{e(c.get("right", ""))}</text>')
        svg = f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(c.get("title", ""))}">{"".join(g)}</svg>'
        cols = ''.join(f'<div><b>{e(z["label"])}</b><span>{e(z["sub"])}</span></div>' for z in zs)
        return f'<figure class="dg-fig">{cap}{svg}<div class="zs" style="grid-template-columns:repeat({len(zs)},1fr)">{cols}</div>{note}</figure>'
    return ''


def deep_layer(n, name, title):
    g = ''.join(f'<i class="{"on" if i < n else ""}"></i>' for i in range(3))
    lead = f'{e(name)} · ' if name else ''
    return f'<div class="dg-layer"><span class="g" aria-hidden="true">{g}</span>{lead}<em>{e(title)}</em></div>'


def build_deeps(arch, flag_map):
    """Render deep/<slug>/index.html for every issue in DEEPS, plus deep/index.html. Returns sitemap rows."""
    region_of = {}
    for a in arch['articles'].values():
        region_of.setdefault(a['source'], a.get('region'))
    flag_of = lambda a: flag_map.get(region_of.get(a['source']) or '', 'xx')
    lens = {}
    ld_ = os.path.join(ROOT, 'lens')
    if os.path.isdir(ld_):
        for fn in os.listdir(ld_):
            if fn.endswith('.json'):
                L = load(os.path.join('lens', fn))
                if L and L.get('slug') and not L.get('draft'):
                    lens[L['slug']] = L
    rows = []
    for D in DEEPS:
        slug = D['slug']
        url = f'{SITE}/deep/{slug}/'
        pub = datetime.fromisoformat(D['published'])
        upd = D.get('updated') or D['published']
        text_len = len(''.join(D.get('quick', [])) + json.dumps(D.get('sections', []), ensure_ascii=False))
        mins = max(3, round(text_len / 600))
        B = [f'<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › <a href="/deep/">DEEP GRID</a> › {e(deep_no(D))}</nav>',
             '<article class="dg">',
             f'<div class="dg-top"><div class="dg-label"><b>DEEP GRID<i>{e(deep_no(D))}</i></b><span>{DEEP_COPY}</span></div></div>',
             f'<h1>{e(D["title"])}</h1>',
             f'<p class="dg-dek">{e(D["dek"])}</p>',
             f'<p class="dg-meta"><span>{e(jst_text(pub))} 公開</span>'
             + (f'<span>{e(jst_text(datetime.fromisoformat(upd)))} 更新</span>' if D.get('updated') else '')
             + f'<span>本文 約{mins}分</span></p>']
        if D.get('themes'):
            B.append('<div class="dg-themes">' + ''.join(f'<span>{e(t)}</span>' for t in D['themes']) + '</div>')
        B.append('<nav class="dg-toc" aria-label="目次"><a href="#quick">先に結論</a>'
                 + ''.join(f'<a href="#s{i + 1}">{e(s["h"])}</a>' for i, s in enumerate(D.get('sections', [])))
                 + ('<a href="#deep">データと記録</a>' if D.get('deep') else '') + '<a href="#sources">出典</a></nav>')
        used = set()
        B.append(f'<div id="quick">{deep_layer(1, "", "先に結論")}</div>')
        B.append('<div class="dg-quick"><ol>' + ''.join(f'<li>{e(q)}</li>' for q in D.get('quick', [])) + '</ol></div>')
        B.append(deep_layer(2, '', '理由と背景'))
        for i, s in enumerate(D.get('sections', [])):
            B.append(f'<div class="dg-sec" id="s{i + 1}"><h2>{e(s["h"])}</h2>{deep_blocks(s["body"], used)}</div>')
        if D.get('deep'):
            heads = '・'.join(s['h'].split('：')[0] for s in D['deep'][:3])
            B.append(f'<details class="dg-deep" id="deep"><summary>{deep_layer(3, "", "データと記録")}'
                     f'<span class="dg-open"><span>データ・規則・歴史を読む<span class="dg-deep-sub">{e(heads)} ほか</span></span></span></summary>')
            for s in D['deep']:
                B.append(f'<div class="dg-sec"><h2>{e(s["h"])}</h2>{deep_blocks(s["body"], used)}</div>')
            B.append('</details>')
        # 「この話の続きを読む」 straight after the body (review of 12 Oct 2026); then same GP and latest at the end.
        # Links out, by role (review of 12 Oct 2026): ① news that answers this issue's questions (max 2, with why),
        # ② other news from the same Grand Prix, ③ the newest news. ① is shown only when there is a real link.
        allnews = [a for a in sorted(arch['articles'].values(), key=when, reverse=True) if a.get('kind') != 'fan']
        shown = set()
        direct = []
        for r in (D.get('related') or [])[:2]:
            a = arch['articles'].get(r.get('id', ''))
            if a:
                direct.append((a, r.get('why', '')))
        if not D.get('related'):
            tp = set(D.get('topics') or [])
            direct = [(a, '') for a in allnews if a.get('topic') in tp][:2] if tp else []
        if direct:
            B.append('<div class="dg-end dg-rel"><h2><span class="k">NEXT</span>この話の続きを読む</h2><ul class="dg-rel-l">'
                     + ''.join(f'<li><a href="/news/{e(a["id"])}/" data-track="click/deep/{e(slug)}/related">'
                               + (f'<small>{e(why)}</small>' if why else '') + f'<b>{e(a["title"])}</b><span>{e(a["source"])}</span></a></li>'
                               for a, why in direct) + '</ul></div>')
            shown |= {a['id'] for a, _ in direct}
        # other issues right after データと記録 (owner's request, 3 Oct 2026), like the WORLD GRID pages
        B.append(more_columns(f'/deep/{slug}/', page='deep'))
        if D.get('glossary'):
            B.append('<div class="dg-end"><h2><span class="k">GLOSSARY</span>この号の用語</h2><dl>'
                     + ''.join(f'<dt>{e(t)}</dt><dd>{e(d)}</dd>' for t, d in D['glossary']) + '</dl></div>')
        B.append('<div class="dg-end" id="sources"><h2><span class="k">SOURCES</span>出典</h2><ol class="dg-src">'
                 + ''.join(f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener" data-track="click/deep/{e(slug)}/src">{e(s["name"])}</a> <small>{e(s["title"])}</small></li>' for s in D.get('sources', []))
                 + '</ol><p class="tnote" style="margin-top:10px">発言は原文から訳し、数字は出典で確かめたものだけを使っています。</p></div>')
        if D.get('history'):
            B.append('<div class="dg-end"><h2><span class="k">UPDATES</span>更新履歴</h2><ul class="dg-hist">'
                     + ''.join(f'<li><time>{e(d)}</time>{e(t)}</li>' for d, t in D['history']) + '</ul></div>')
        same_gp = [a for a in allnews if D.get('circuit') and a.get('circuit') == D['circuit'] and a['id'] not in shown][:5]
        if same_gp:
            gp_name = (((load('circuits.json', {}) or {}).get('circuits') or {}).get(D['circuit']) or {}).get('gp', '')
            B.append(f'<div class="dg-end"><h2><span class="k">SAME GP</span>{e(gp_name or "同じグランプリ")}のほかのニュース</h2><ul class="list">'
                     + ''.join(item_li(a, flag_of) for a in same_gp) + '</ul></div>')
            shown |= {a['id'] for a in same_gp}
        latest = [a for a in allnews if a['id'] not in shown][:3]
        if latest:
            B.append('<div class="dg-end"><h2><span class="k">LATEST</span>新着ニュース</h2><ul class="list">'
                     + ''.join(item_li(a, flag_of) for a in latest) + '</ul></div>')
        rel = [lens[s] for s in D.get('lensRelated', []) if s in lens]
        if rel:
            B.append('<div class="dg-end"><h2><span class="k">WORLD GRID</span>世界はどう報じた？</h2>'
                     + ''.join(f'<a class="dg-card" href="/lens/{e(L["slug"])}/"><small>WORLD GRID · {e(L["gpLabel"])}</small><b>{e(L["title"])}</b></a>' for L in rel) + '</div>')
        B.append('<div class="dg-end">' + rules_entry('deep-issue') + '</div>')
        B.append('</article>')
        B.append(term_assets(used))

        head = MONO_FONT + f'<meta property="article:published_time" content="{e(D["published"])}">\n<style>{DEEP_CSS}{RULES_ENTRY_CSS}{RULES_CSS if used else ""}</style>\n'
        head += ld({'@context': 'https://schema.org', '@type': 'Article', 'headline': D['title'], 'description': D['dek'],
                    'datePublished': D['published'], 'dateModified': upd, 'inLanguage': 'ja', 'image': [OG_IMAGE],
                    'mainEntityOfPage': url, 'author': PUBLISHER, 'publisher': PUBLISHER, 'articleSection': 'DEEP GRID',
                    'keywords': D.get('themes', [])})
        head += ld({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'F1 Grid Walk', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'DEEP GRID', 'item': SITE + '/deep/'},
            {'@type': 'ListItem', 'position': 3, 'name': D['title'], 'item': url}]})
        # the issue's own share image when deep/<slug>/og.png exists (1200x630, placed by the column desk); else the site image
        ogp = os.path.join(ROOT, 'deep', slug, 'og.png')
        ogi = f'{SITE}/deep/{slug}/og.png?v={hashlib.md5(open(ogp, "rb").read()).hexdigest()[:8]}' if os.path.exists(ogp) else None
        write(f'deep/{slug}/index.html', page(f'{D["title"]}｜F1深掘り解説 DEEP GRID｜F1グリッドウォーク', D['dek'], url, '\n'.join(B), head, og_image=ogi, og_size=(1200, 630)))
        rows.append((url, upd, None, '0.9'))

    # top page slot (inside <!--pre:deep--> in index.html)
    ip = os.path.join(ROOT, 'index.html'); src = open(ip, encoding='utf-8').read()
    blk = ''
    if DEEPS:
        D = DEEPS[0]
        # no issue number on the top page (owner's request, 3 Oct 2026)
        blk = (f'<a class="duo-row duo-deep" href="/deep/{e(D["slug"])}/" data-track="click/top/deep"><span class="duo-q"><small>DEEP GRID</small><strong>ニュースの、その奥へ。</strong></span>'
               f'<b>{e(D["title"])}&#8288;<i aria-hidden="true">→</i></b></a>')
    out = re.sub(r'(<!--pre:deep-->).*?(<!--/pre:deep-->)', lambda m: m.group(1) + blk + m.group(2), src, count=1, flags=re.S)
    if out != src:
        open(ip, 'w', encoding='utf-8').write(out)
    if not DEEPS:
        old = os.path.join(ROOT, 'deep', 'index.html')
        if os.path.exists(old):
            os.remove(old)
        return []
    items = ''.join(f'<li><a href="/deep/{e(D["slug"])}/">{ctag("deep", deep_no(D))}<b>{e(D["title"])}</b></a>'
                    f'<p>{e(D["quick"][0] if D.get("quick") else D["dek"])}</p></li>' for D in DEEPS)
    body = ('<nav class="crumbs"><a href="/">トップ</a> › DEEP GRID</nav><div class="dg">'
            f'<div class="dg-top"><div class="dg-label"><b>DEEP GRID</b><span>{DEEP_COPY}</span></div></div>'
            '<h1>DEEP GRID</h1>'
            '<p class="dg-dek">ニュースの続きを、ニュースより深く読む。なぜ起きたのか、技術的に何を意味するのか、過去と何が違うのか。'
            'まず「先に結論」で要点をつかみ、その先は奥へ行くほど深くなる、F1 Grid Walkの深掘り記事です。</p>'
            + rules_entry('deep-index')
            + f'<ul class="dg-list">{items}</ul></div>')
    write('deep/index.html', page('F1深掘り解説 DEEP GRID｜ニュースの「なぜ」を読む｜F1グリッドウォーク',
                                  'グリッド降格はなぜ起きる？ 雨のタイヤはどう違う？ F1ニュースの「なぜ」を、先に結論、そのあと表と数字で深く読む解説記事。パワーユニット、空力、タイヤ、規則まで。',
                                  SITE + '/deep/', body, MONO_FONT + f'<style>{DEEP_CSS}{RULES_ENTRY_CSS}</style>\n', og_type='website'))
    return [(SITE + '/deep/', DEEPS[0].get('updated') or DEEPS[0]['published'], 'weekly', '0.8')] + rows



# ---------------------------------------------------------------- DEEP GRID rulebook (/deep/rules/)
RULES = None  # deep/rules.json when published (or PREVIEW_DRAFTS=1)

RULES_CSS = '''
.rb-search{position:sticky;top:0;z-index:5;background:var(--paper);padding:10px 0 10px;margin:0 0 6px;border-bottom:1px solid var(--line)}
.rb-search input{width:100%;font:inherit;font-size:16px;padding:12px 16px 12px 42px;border:1.5px solid var(--ink);border-radius:999px;background:var(--surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' stroke='%235B5F57' stroke-width='2'%3E%3Ccircle cx='8' cy='8' r='6'/%3E%3Cpath d='M13 13l4 4'/%3E%3C/svg%3E") 15px center no-repeat;color:var(--ink)}
.rb-cats{display:flex;gap:6px;overflow-x:auto;padding:10px 0 0;scrollbar-width:none}
.rb-cats::-webkit-scrollbar{display:none}
.rb-cats button{flex:0 0 auto;font:inherit;font-size:13px;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:4px 13px;cursor:pointer}
.rb-cats button[aria-pressed="true"]{background:var(--ink);color:var(--on-ink);border-color:var(--ink)}
.rb-count{font-size:12.5px;color:var(--muted);margin:8px 0 0}
.rb-none{display:none;border:1px dashed var(--line);border-radius:12px;padding:14px 16px;margin:14px 0;font-size:14.5px}
.rb-none button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:2px 11px;margin:4px 6px 0 0;cursor:pointer;color:var(--ink)}
details.rb{border-bottom:1px solid var(--line)}
details.rb>summary{list-style:none;cursor:pointer;padding:14px 0;display:block}
details.rb>summary::-webkit-details-marker{display:none}
.rb-t{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.rb-t b{font-size:17.5px}
.rb-t small{flex-shrink:0;font-size:11.5px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:0 9px}
.rb-al{display:block;font-size:12px;color:var(--muted);margin:1px 0 4px}
.rb-s{display:block;font-size:15px;line-height:1.8;color:var(--ink-2)}
.rb-s::after{content:"＋ 詳しく";display:inline-block;margin-left:8px;font-size:12px;font-weight:700;color:var(--clay)}
details[open].rb .rb-s::after{content:"－ 閉じる"}
.rb-b{padding:0 0 18px}
.rb-b p{font-size:15.5px;line-height:1.95;margin:0 0 12px}
.rb-h{font-size:12px;font-weight:700;letter-spacing:.1em;color:var(--muted);margin:14px 0 4px}
.rb-rule{display:inline-block;font-size:13px;border-left:3px solid var(--clay);padding:1px 0 1px 10px}
.rb-ex{list-style:none;margin:0;padding:0}
.rb-ex li{padding:4px 0;font-size:14.5px;line-height:1.7}
.rb-ex a::before{content:"→ ";color:var(--clay)}
.rb-see{display:flex;flex-wrap:wrap;gap:6px}
.rb-see a{font-size:13px;border:1px solid var(--line);border-radius:999px;padding:1px 11px;text-decoration:none;background:var(--surface)}
.rb-tool{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:12px 0 4px}
.rb-tool label{display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:14px;padding:5px 0}
.rb-tool select{font:inherit;font-size:14px;padding:5px 8px;border:1px solid var(--line);border-radius:8px;background:var(--paper);color:var(--ink);max-width:62%}
.rb-out{margin:10px 0 0;padding:10px 12px;border-radius:10px;background:var(--ink);color:var(--on-ink);font-weight:700;font-size:15px}
.rb-out small{display:block;font-weight:400;font-size:12px;opacity:.85}
.rb-checked{font-size:12px;color:var(--muted);margin:6px 0 0}
a.term{text-decoration:underline dotted;text-decoration-color:var(--clay);text-underline-offset:4px;color:inherit;cursor:help}
.term-pop{position:absolute;z-index:20;max-width:300px;background:var(--surface);color:var(--ink);border:1px solid var(--ink);border-radius:12px;padding:10px 12px;font-size:14px;line-height:1.7;box-shadow:0 6px 24px rgba(0,0,0,.14)}
.term-pop b{display:block;font-size:14.5px}
.term-pop a{display:inline-block;margin-top:4px;font-size:13px;font-weight:700;color:var(--clay)}
'''

RULES_JS = '''<script>
(function(){
  function norm(s){
    s=(s||'').normalize('NFKC').toLowerCase();
    s=s.replace(/[ァ-ヶ]/g,function(c){return String.fromCharCode(c.charCodeAt(0)-0x60);});
    s=s.replace(/ゔぁ/g,'ば').replace(/ゔぃ/g,'び').replace(/ゔぇ/g,'べ').replace(/ゔぉ/g,'ぼ').replace(/ゔ/g,'ぶ');
    s=s.replace(/[ぁぃぅぇぉゃゅょゎ]/g,function(c){return String.fromCharCode(c.charCodeAt(0)+1);});
    return s.replace(/[\\s・\\-ー=＝っ]/g,'');
  }
  function toks(raw){ return (raw||'').split(/[\\s　、,]+/).map(norm).filter(Boolean); }
  function lev(a,b){ var m=a.length,n=b.length,p=[],i,j; for(j=0;j<=n;j++)p[j]=j; for(i=1;i<=m;i++){ var prev=p[0]; p[0]=i; for(j=1;j<=n;j++){ var tmp=p[j]; p[j]=Math.min(p[j]+1,p[j-1]+1,prev+(a[i-1]===b[j-1]?0:1)); prev=tmp; } } return p[n]; }
  function near(q,name){ var best=lev(q,name),L=q.length,i; if(name.length>L){ for(i=0;i+L<=name.length;i++){ best=Math.min(best,lev(q,name.substr(i,L))); } } return best; }
  var q=document.getElementById('rb-q'); if(!q) return;
  var items=[].slice.call(document.querySelectorAll('.rb-list .rb')), cat='all';
  var cnt=document.getElementById('rb-count'), none=document.getElementById('rb-none'), maybe=document.getElementById('rb-maybe');
  var parent=items.length?items[0].parentNode:null, endMark=items.length?items[items.length-1].nextSibling:null;
  items.forEach(function(d,i){ d._i=i; d._k=norm([d.getAttribute('data-k'),d.getAttribute('data-names'),d.getAttribute('data-w'),d.textContent].join(' ')); d._names=(d.getAttribute('data-names')||'').split('|').map(norm).filter(Boolean); d._n=d._names.join(' '); d._w=(d.getAttribute('data-w')||'').split('|').map(norm).filter(Boolean); });
  function score(d,j){ var s=0; d._names.forEach(function(nm){ if(nm===j) s=Math.max(s,3); else if(nm.indexOf(j)===0) s=Math.max(s,2); else if(nm.indexOf(j)>=0) s=Math.max(s,1); }); if(!s) d._w.forEach(function(w){ if(w.indexOf(j)>=0||j.indexOf(w)>=0) s=0.5; }); return s; }
  function run(){
    var ts=toks(q.value), j=ts.join(''), n=0;
    items.forEach(function(d){
      var ok=(cat==='all'||d.getAttribute('data-c')===cat)&&ts.every(function(t){ return d._k.indexOf(t)>=0; });
      d.hidden=!ok; if(ok) n++; d._s=ts.length?score(d,j):0;
    });
    var any=false;
    if(!n&&ts.length>1){ any=true; items.forEach(function(d){ var ok=(cat==='all'||d.getAttribute('data-c')===cat)&&ts.some(function(t){ return d._k.indexOf(t)>=0; }); d.hidden=!ok; if(ok) n++; d._s=0; ts.forEach(function(t){ d._s=Math.max(d._s,score(d,t)); }); }); }
    if(parent){ items.slice().sort(function(a,b){ return (a.hidden-b.hidden)||(b._s-a._s)||(a._i-b._i); }).forEach(function(d){ parent.insertBefore(d,endMark); }); }
    cnt.textContent=(ts.length||cat!=='all')?n+' / '+items.length+' ENTRIES'+(any&&n?' · どれかの言葉を含む':''):items.length+' ENTRIES';
    none.style.display=n?'none':'block';
    if(!n&&maybe){
      var thr=Math.max(1,Math.floor(j.length/3)), c=[];
      items.forEach(function(d){ var b=99; d._names.forEach(function(nm){ b=Math.min(b,near(j,nm)); }); if(j&&b<=thr) c.push([b,d]); });
      c.sort(function(x,y){ return x[0]-y[0]; });
      maybe.innerHTML=''; c.slice(0,3).forEach(function(x){ var bt=document.createElement('button'); bt.type='button'; bt.textContent=x[1].getAttribute('data-t'); bt.addEventListener('click',function(){ q.value=bt.textContent; q.dispatchEvent(new Event('input')); go(); }); maybe.appendChild(bt); });
      maybe.parentNode.style.display=c.length?'block':'none';
    }
  }
  q.addEventListener('input',run);
  var cbs=[].slice.call(document.querySelectorAll('.rbx-grid button'));
  function setCat(c){ cat=c; cbs.forEach(function(x){ x.setAttribute('aria-pressed',String(x.getAttribute('data-c')===c)); }); run(); }
  cbs.forEach(function(b){ b.addEventListener('click',function(){ setCat(cat===b.getAttribute('data-c')?'all':b.getAttribute('data-c')); }); });
  /* 検索 button (and Enter): filter, close the keyboard, jump to the best match */
  function go(){ run(); q.blur(); var f=document.querySelector('.rb-list .rb:not([hidden])'); if(q.value&&f){ f.scrollIntoView({behavior:'smooth',block:'start'}); } }
  var gb=document.getElementById('rb-go'); if(gb) gb.addEventListener('click',go);
  q.addEventListener('keydown',function(ev){ if(ev.key==='Enter'){ ev.preventDefault(); go(); } });
  q.addEventListener('search',run);
  [].forEach.call(document.querySelectorAll('.rb-none button'),function(b){ b.addEventListener('click',function(){ q.value=b.textContent; run(); }); });
  /* old links (/deep/rules/#id) go to the entry's own page */
  function openHash(){ var id=location.hash.slice(1); var d=id&&document.getElementById(id); if(d&&d.classList.contains('rb')){ location.replace(d.getAttribute('href')); } }
  window.addEventListener('hashchange',openHash); openHash();
  /* full-text search: the explanations are loaded only when the reader starts searching */
  var full=false; function loadFull(){ if(full) return; full=true; fetch('/deep/rules/search.json').then(function(r){ return r.json(); }).then(function(m){ items.forEach(function(d){ var x=m[d.id]; if(x) d._k+=norm(x); }); if(q.value) run(); }).catch(function(){}); }
  q.addEventListener('focus',loadFull); q.addEventListener('input',loadFull);
  try{ var sp=new URLSearchParams(location.search), p=sp.get('q'), c=sp.get('c'); if(p){ q.value=p; q.dispatchEvent(new Event('input')); } if(c){ setCat(c); } else if(p){ run(); } }catch(e){}
  /* grid penalty calculator */
  var t=document.getElementById('pu-tool');
  if(t){ var sels=[].slice.call(t.querySelectorAll('select')), out=document.getElementById('pu-out');
    function calc(){ var p=0; sels.forEach(function(s){ p+=+s.value; });
      out.innerHTML = p===0 ? '降格なし<small>どの部品も上限の中です。</small>' : (p>15 ? '最後尾からのスタート<small>合計'+p+'グリッド。15を超えるので、数に関係なく最後尾です。</small>' : p+'グリッド降格<small>予選で決まった位置から、'+p+'グリッド後ろに下がります。</small>'); }
    sels.forEach(function(s){ s.addEventListener('change',calc); }); calc(); }
})();
</script>'''

TERM_JS = '''<script>
(function(){
  var data=JSON.parse(document.getElementById('term-data').textContent), pop=null;
  function close(){ if(pop){ pop.remove(); pop=null; } }
  document.addEventListener('click',function(ev){
    var a=ev.target.closest&&ev.target.closest('a.term');
    if(!a){ if(pop&&!(ev.target.closest&&ev.target.closest('.term-pop'))) close(); return; }
    ev.preventDefault(); close();
    var d=data[a.getAttribute('data-term')]; if(!d) return;
    pop=document.createElement('div'); pop.className='term-pop'; pop.setAttribute('role','dialog');
    var b=document.createElement('b'); b.textContent=d[0]; pop.appendChild(b);
    pop.appendChild(document.createTextNode(d[1]));
    var tid=a.getAttribute('data-term')||'';
    var l=document.createElement('a'); l.href=a.getAttribute('href'); l.textContent=tid.indexOf('person-')===0?(d[0]+'の記事をすべて見る →'):'ルールブックで詳しく →'; pop.appendChild(document.createElement('br')); pop.appendChild(l);
    document.body.appendChild(pop);
    var r=a.getBoundingClientRect(), w=Math.min(300,document.documentElement.clientWidth-32);
    pop.style.width=w+'px';
    pop.style.left=Math.max(16,Math.min(r.left+scrollX,document.documentElement.clientWidth-w-16))+'px';
    pop.style.top=(r.bottom+scrollY+8)+'px';
  });
  document.addEventListener('keydown',function(ev){ if(ev.key==='Escape') close(); });
})();
</script>'''


TEAMS_ALL = {}  # teams.json teams, for person pages
PEOPLE = []  # deep/people.json: verified names and titles (shown in the rulebook search as 人物)


def term_lookup():
    """(text to find, anchor id, popover title, popover text) for every rulebook term and person."""
    out = []
    if RULES:
        out += [(t['term'], t['id'], t['term'], t['short']) for t in RULES['terms']]
    out += [(p['name'], 'person-' + p['id'], p['name'], f'{p["role"]}（{p["org"]}）') for p in PEOPLE]
    return out


def load_rules():
    global RULES, PEOPLE
    PEOPLE = (load('deep/people.json', {}) or {}).get('people', [])
    global TEAMS_ALL
    TEAMS_ALL = (load('teams.json', {}) or {}).get('teams', {})
    R = load('deep/rules.json')
    if R and R.get('draft') and os.environ.get('PREVIEW_DRAFTS') != '1':
        old = os.path.join(ROOT, 'deep', 'rules', 'index.html')
        if os.path.exists(old):
            os.remove(old)
            try: os.rmdir(os.path.dirname(old))
            except OSError: pass
        R = None
    RULES = R
    return R


_LT_KATA = '\u30a0-\u30ff'


def _lt_ok(text, i, w):
    """True when w at text[i] is a whole word: a katakana or Latin name must not run on into more
    katakana / letters on either side (レーキ inside ブレーキ, オーバー inside オーバーテイク)."""
    def kind(c):
        if not c:
            return ''
        if re.match(f'[{_LT_KATA}]', c):
            return 'k'
        if re.match(r'[A-Za-z]', c):
            return 'l'
        return ''
    before = text[i - 1] if i > 0 else ''
    after = text[i + len(w)] if i + len(w) < len(text) else ''
    if kind(w[0]) and kind(before) == kind(w[0]):
        return False
    if kind(w[-1]) and kind(after) == kind(w[-1]):
        return False
    return True


_LT_LOOKUP = None


def _lt_lookup():
    """Names to link, longest first: every dictionary name, plus the name without its（…）note
    (ブレーキ（ディスクとキャリパー） is also found as ブレーキ)."""
    global _LT_LOOKUP
    if _LT_LOOKUP is None:
        rows = []
        for word, tid, title, text in term_lookup():
            rows.append((word, tid))
            short = re.sub(r'（.*?）', '', word).strip()
            if short != word and len(short) >= 3:
                rows.append((short, tid))
        _LT_LOOKUP = sorted(rows, key=lambda x: -len(x[0]))
    return _LT_LOOKUP


_MDLINK = re.compile(r'\[([^\]\n]+)\]\((/[^)\s]*)\)')


def body_links(text, used):
    """A body paragraph: rulebook terms linked as usual, plus [text](/site/path/) links to our own pages
    (internal paths only; e.g. to a DEEP). Link text itself is not term-linked, so links never nest."""
    out, pos = [], 0
    for m in _MDLINK.finditer(text):
        out.append(link_terms(e(text[pos:m.start()]), used))
        out.append(f'<a href="{e(m.group(2))}">{e(m.group(1))}</a>')
        pos = m.end()
    out.append(link_terms(e(text[pos:]), used))
    return ''.join(out)


def link_terms(html_text, used):
    """Underline the first appearance of each rulebook term in a paragraph (already HTML-escaped).
    Longer terms win (バーチャルセーフティカー before セーフティカー), a name is linked only as a whole word,
    and a link is never put inside another link."""
    if not RULES:
        return html_text
    taken = []  # (start, end) spans already linked, in the current string
    for word, tid in _lt_lookup():
        if tid in used:
            continue
        w = e(word)
        i = html_text.find(w)
        while i >= 0 and (any(a <= i < b or a < i + len(w) <= b for a, b in taken) or not _lt_ok(html_text, i, w)):
            i = html_text.find(w, i + 1)
        if i >= 0:
            a = f'<a class="term" href="/deep/rules/{tid}/" data-term="{tid}">{w}</a>'
            html_text = html_text[:i] + a + html_text[i + len(w):]
            shift = len(a) - len(w)
            taken = [(x + (shift if x > i else 0), y + (shift if y > i else 0)) for x, y in taken] + [(i, i + len(a))]
            used.add(tid)
    return html_text


SITE_TITLES = None


def site_titles():
    """Title of every page a column may point to, by path (news, columns, DEEP GRID, 読み解き)."""
    global SITE_TITLES
    if SITE_TITLES is None:
        T = {}
        arch = load('news/archive.json', {}) or {}
        for a in (arch.get('articles') or {}).values():
            T[f'/news/{a["id"]}/'] = a.get('title', '')
        d = os.path.join(ROOT, 'lens')
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith('.json'):
                    L = load(os.path.join('lens', fn)) or {}
                    if L.get('slug'):
                        T[f'/lens/{L["slug"]}/'] = L.get('title', '')
        for D in DEEPS:
            T[f'/deep/{D["slug"]}/'] = D.get('title', '')
        for H in HUBS.values():
            T[f'/topics/{H["slug"]}/'] = H.get('title', '')
        SITE_TITLES = T
    return SITE_TITLES


_SITE_URL_RE = r'https://f1gridwalk\.github\.io(/[A-Za-z0-9_\-/]*)'


def site_links(h):
    """Column and DEEP GRID text is also posted to note, where a bare URL is fine. On the site, a URL of
    our own page becomes a link that says where it goes (review of 12 Oct 2026):
    「名前」（URL） → 「名前」 as the link; otherwise the URL → the page title as the link."""
    if 'f1gridwalk.github.io' not in h:
        return h
    T = site_titles()
    def norm(path):
        return path if path.endswith('/') else path + '/'
    def named(m):
        return f'「<a href="{norm(m.group(2))}">{m.group(1)}</a>」'
    h = re.sub(r'「([^「」<>]{1,60})」（\s*' + _SITE_URL_RE + r'\s*）', named, h)
    def bare(m):
        path = norm(m.group(1))
        title = T.get(path) or 'このページ'
        return f'「<a href="{path}">{e(title)}</a>」'
    h = re.sub(r'\s*' + _SITE_URL_RE + r'\s*', bare, h)
    return h


SKIP_TAGS = ('a', 'h1', 'h2', 'h3', 'button', 'script', 'style', 'summary', 'textarea', 'label', 'select', 'time', 'cite')


def link_terms_html(html_text, used):
    """Like link_terms, but for a finished HTML fragment: only touches text outside tags, links, headings and buttons."""
    if not RULES:
        return html_text
    out, depth = [], 0
    for part in re.split(r'(<[^>]+>)', html_text):
        if part.startswith('<'):
            m = re.match(r'<(/?)([a-zA-Z0-9]+)', part)
            if m and m.group(2).lower() in SKIP_TAGS and not part.endswith('/>'):
                depth += -1 if m.group(1) else 1
                depth = max(depth, 0)
            out.append(part)
        else:
            out.append(link_terms(part, used) if depth == 0 and part.strip() else part)
    return ''.join(out)


def term_assets(used):
    if not used or not RULES:
        return ''
    data = {tid: [title, text] for _, tid, title, text in term_lookup() if tid in used}
    return ('<script type="application/json" id="term-data">' + json.dumps(data, ensure_ascii=False).replace('</', '<\\/') + '</script>' + TERM_JS)


PU_TOOL = '''<div class="rb-tool" id="pu-tool"><div class="rb-h" style="margin-top:0">計算してみる：この週末に新しく入れた部品は？</div>
{rows}<div class="rb-out" id="pu-out" aria-live="polite">降格なし</div>
<p class="rb-checked">目安です。実際の降格はFIAが発表します。代役の使用分や、ほかの違反による降格は含みません。</p></div>'''


RULES_ENTRY_CSS = '''
.rbx{--bd:#111311;--bg:#E4E5E2;--tx:#111311;--sub:#4A4D48;--inp:#F7F7F5;--hd:#111311;--hdt:#F7F7F5;--btn:#111311;--btnt:#F2C230;--line:#C9CBC6;background:var(--bg);color:var(--tx);border:2px solid var(--bd);border-radius:22px;overflow:hidden;margin:20px 0 10px;padding-bottom:14px}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .rbx{--bd:#D9DBDD;--bg:#24272A;--tx:#ECEDEE;--sub:#A3A8AD;--inp:#1B1D20;--hd:#ECEDEE;--hdt:#111311;--btn:#F2C230;--btnt:#111311;--line:#3A3E43}}
:root[data-theme="dark"] .rbx{--bd:#D9DBDD;--bg:#24272A;--tx:#ECEDEE;--sub:#A3A8AD;--inp:#1B1D20;--hd:#ECEDEE;--hdt:#111311;--btn:#F2C230;--btnt:#111311;--line:#3A3E43}
.rbx .mono{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;letter-spacing:.06em}
.rbx-hd{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 16px;background:var(--hd);color:var(--hdt)}
.rbx-hd b{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-size:18px;letter-spacing:.2em}
.rbx-hd span{font-size:10.5px}
.rbx p.rbx-lead{margin:12px 16px 0;font-size:14px;font-weight:700;line-height:1.6}
.rbx form,.rbx .rbx-f{display:flex;gap:8px;margin:10px 12px 0}
.rbx input{flex:1;min-width:0;font:inherit;font-size:16px;padding:12px 12px 12px 42px;border:2px solid var(--line);border-radius:999px;background:var(--inp) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' stroke='%23777B76' stroke-width='2'%3E%3Ccircle cx='8' cy='8' r='6'/%3E%3Cpath d='M13 13l4 4'/%3E%3C/svg%3E") 14px center no-repeat;color:var(--tx);outline:none}
.rbx input::placeholder{color:var(--sub)}
.rbx-in{position:relative;flex:1;min-width:0;display:flex}
.rbx-in input{padding-right:42px}
.rbx input::-webkit-search-cancel-button{-webkit-appearance:none;appearance:none;display:none}
.rbx .rbx-x{position:absolute;right:8px;top:50%;transform:translateY(-50%);width:30px;height:30px;border:0;border-radius:50%;background:var(--sub);color:var(--inp);font:700 17px/30px sans-serif;text-align:center;padding:0;cursor:pointer}
.rbx .rbx-x[hidden]{display:none}
.rbx input:focus{border-color:#F2C230}
.rbx button.go{flex-shrink:0;font:inherit;font-size:15px;font-weight:700;border:0;border-radius:999px;padding:0 18px;background:var(--btn);color:var(--btnt);cursor:pointer}
.rbx-all{display:inline-block;margin:12px 16px 0;font-size:13.5px;font-weight:700;color:var(--tx);text-decoration:none}
.rbx-all:hover{text-decoration:underline}
.rbx p.rbx-cnt{margin:10px 16px 0;font-size:11px;line-height:1.4;color:var(--sub)}
'''

MONO_FONT = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;700&display=swap">\n'


RBX_JS = ('<script>(function(){[].forEach.call(document.querySelectorAll(".rbx-in"),function(w){'
          'var i=w.querySelector("input"),x=w.querySelector(".rbx-x");if(!i||!x)return;'
          'function s(){x.hidden=!i.value;}i.addEventListener("input",s);'
          'x.addEventListener("click",function(){i.value="";s();i.dispatchEvent(new Event("input",{bubbles:true}));i.focus();});s();});})();</script>')


def rules_entry(where, on_page=False):
    """The rulebook search box (plan 1: header, one line, search; no fixed categories)."""
    if not RULES:
        return ''
    n = len(RULES['terms']) + len(PEOPLE)
    hd = f'<div class="rbx-hd"><b>RULES</b><span class="mono">{n} ENTRIES · 増えていきます</span></div><p class="rbx-lead">F1の用語・ルール・人物を、言葉で引く辞典。</p>'
    if on_page:
        return (f'<div class="rbx">{hd}<div class="rbx-f" role="search"><span class="rbx-in"><input id="rb-q" type="search" placeholder="例：降格、ハジャー" aria-label="用語とルールを検索" autocomplete="off"><button type="button" class="rbx-x" aria-label="入力を消す" hidden>×</button></span>'
                f'<button type="button" class="go" id="rb-go">検索</button></div><p class="rbx-cnt mono" id="rb-count">{n} ENTRIES</p></div>' + RBX_JS)
    return (f'<div class="rbx">{hd}<form action="/deep/rules/" method="get" role="search"><span class="rbx-in"><input type="search" name="q" placeholder="例：降格、ハジャー" aria-label="F1の用語・ルールを調べる"><button type="button" class="rbx-x" aria-label="入力を消す" hidden>×</button></span>'
            f'<button type="submit" class="go" data-track="click/rules-entry/{where}">検索</button></form>'
            f'<a class="rbx-all" href="/deep/rules/" data-track="click/rules-entry/{where}/all">すべての用語を見る →</a></div>' + RBX_JS)


def rb_url(tid):
    """Each rulebook entry has its own page (owner's request, 9 Oct 2026): /deep/rules/<id>/ (people: person-<id>)."""
    return f'/deep/rules/{tid}/'


RBP_CSS = '''
.rbl{display:block;border-bottom:1px solid var(--line);padding:14px 0;color:var(--ink);text-decoration:none}
.rbl:hover .rb-t b{text-decoration:underline;text-underline-offset:3px}
.rbl .rb-s::after{content:"詳しく →"}
.rb-t small{font-size:12px}
.rb-al{font-size:12.5px}
.rbp-eyebrow{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin:18px 0 0;font-size:13px;color:var(--muted)}
.rbp-eyebrow a{font-size:12.5px;border:1px solid var(--line);border-radius:999px;padding:1px 11px;text-decoration:none;color:var(--ink);background:var(--surface)}
.rbp h1{margin:10px 0 4px}
.rbp-al{font-size:13.5px;color:var(--muted);margin:0 0 14px}
.rbp-short{font-size:18px;line-height:1.85;font-weight:700;margin:0 0 18px;padding:14px 16px;border-left:4px solid var(--clay);background:var(--surface);border-radius:0 12px 12px 0}
.rbp-body p{font-size:16px;line-height:2;margin:0 0 14px}
.rbp .rb-h{font-size:12.5px;margin:22px 0 6px}
.rbp-body h2.rbp-sh{font-size:17px;font-weight:800;line-height:1.5;margin:26px 0 8px;padding-left:10px;border-left:3px solid var(--clay)}
.rbp-body h2.rbp-sh:first-child{margin-top:6px}
.rb-srcbox{margin:22px 0 4px}
.rbp .rb-team{margin:10px 0 0}.rbp .rb-team a{font-size:15px;font-weight:700;color:var(--ink)}
.rbp .rb-mate{margin:6px 0 0;font-size:14.5px;color:var(--ink-2)}.rbp .rb-mate a{font-weight:700;color:var(--ink)}
.rb-srcbox summary{cursor:pointer;font-size:12.5px;font-weight:700;letter-spacing:.1em;color:var(--muted);padding:6px 0}
.rbp ul.rb-src{margin:6px 0 0}
.rbp ul.rb-src li{font-size:13px;line-height:1.7;padding:3px 0}
.rbp ul.rb-src a::before{content:none}
.rbp ul.rb-src a{color:var(--ink-2);text-decoration-color:var(--line)}
.rbp ul.rb-src small{display:block;color:var(--muted);font-size:12px}
.rbp .rb-ex li{font-size:15px}
.rb-reads small{display:inline-block;margin-right:6px;font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--muted)}
.rbp .rb-see a{font-size:14px;padding:3px 13px}
.rbp-back{display:inline-block;margin:22px 0 0;font-size:14px;font-weight:700}
.rbp .rb-checked{margin-top:18px}
'''

PU_JS = '''<script>(function(){var t=document.getElementById('pu-tool');if(!t)return;var sels=[].slice.call(t.querySelectorAll('select')),out=document.getElementById('pu-out');
function calc(){var p=0;sels.forEach(function(s){p+=+s.value;});
out.innerHTML=p===0?'降格なし<small>どの部品も上限の中です。</small>':(p>15?'最後尾からのスタート<small>合計'+p+'グリッド。15を超えるので、数に関係なく最後尾です。</small>':p+'グリッド降格<small>予選で決まった位置から、'+p+'グリッド後ろに下がります。</small>');}
sels.forEach(function(s){s.addEventListener('change',calc);});calc();})();</script>'''


def _rb_titles():
    titles = {}
    for D in DEEPS:
        titles[f'/deep/{D["slug"]}/'] = 'DEEP GRID ' + deep_no(D) + ' ' + D['title']
    ldir = os.path.join(ROOT, 'lens')
    for fn in os.listdir(ldir):
        if fn.endswith('.json'):
            L = load(os.path.join('lens', fn))
            if L and L.get('slug') and not L.get('draft'):
                titles[f'/lens/{L["slug"]}/'] = f'{L.get("gpLabel", "コラム")}：{L["title"]}'
    return titles


def _rb_page(R, tid, kind, name, cat, al, short, inner, used, ld_term, desc_title, og=None):
    """One rulebook entry page."""
    url = SITE + rb_url(tid)
    crumbs = ('<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › <a href="/deep/">DEEP GRID</a> › '
              f'<a href="/deep/rules/">ルールブック</a> › {e(name)}</nav>')
    same = ''
    body = (crumbs + '<div class="dg rbp">'
            f'<div class="dg-top"><div class="dg-label"><b>DEEP GRID<i>RULES</i></b><span>{DEEP_COPY}</span></div></div>'
            f'<p class="rbp-eyebrow"><span>F1用語・ルール辞典</span><a href="/deep/rules/?c={quote(cat)}">{e(cat)}</a></p>'
            f'<h1>{e(name)}</h1>' + (f'<p class="rbp-al">{e(al)}</p>' if al else '')
            + f'<p class="rbp-short">{e(short)}</p>' + inner
            + rules_entry('term')
            + f'<a class="rbp-back" href="/deep/rules/">← ルールブックの一覧へ（{len(R["terms"]) + len(PEOPLE)}項目）</a>'
            + '</div>')
    if used:
        body += term_assets(used)
    crumbs_ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'F1 Grid Walk', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'DEEP GRID', 'item': SITE + '/deep/'},
        {'@type': 'ListItem', 'position': 3, 'name': 'ルールブック', 'item': SITE + '/deep/rules/'},
        {'@type': 'ListItem', 'position': 4, 'name': name, 'item': url}]}
    head = (MONO_FONT + f'<style>{DEEP_CSS}{RULES_CSS}{RULES_ENTRY_CSS}{RBP_CSS}</style>\n' + ld(crumbs_ld) + ld(ld_term))
    desc = re.sub(r'\s+', ' ', short)
    desc = (desc if len(desc) <= 110 else desc[:108] + '…') + ' F1の用語とルールを、2026年の規則と今季の実例でやさしく解説。'
    write(f'deep/rules/{tid}/index.html', page(desc_title, desc, url, body, head, og_image=og))


def build_rules():
    if not RULES:
        return []
    R = RULES
    url = SITE + '/deep/rules/'
    name = {t['id']: t['term'] for t in R['terms']}
    name.update({'person-' + p['id']: p['name'] for p in PEOPLE})
    by_cat = {}
    for t in sorted(R['terms'], key=lambda t: t['term']):
        by_cat.setdefault(t['cat'], []).append(t)
    titles = _rb_titles()
    items, search, sm = [], {}, []
    term_set = {'@type': 'DefinedTermSet', 'name': R['title'], 'url': url}
    for t in sorted(R['terms'], key=lambda t: (R['cats'].index(t['cat']), t['term'])):
        tid = t['id']
        keys = ' '.join(x['t'] for x in t.get('examples', []))
        search[tid] = ' '.join(re.sub(r'^## ', '', x) for x in t.get('body', []))
        al = '・'.join([x for x in t.get('aliases', []) if not re.fullmatch(r'[ぁ-ゟー]+', x)][:4])
        items.append(f'<a class="rb rbl" id="{e(tid)}" href="{rb_url(tid)}" data-c="{e(t["cat"])}" data-t="{e(t["term"])}" data-names="{e("|".join([t["term"]] + t.get("aliases", [])))}" data-w="{e("|".join(t.get("words", [])))}" data-k="{e(keys)}">'
                     f'<span class="rb-t"><b>{e(t["term"])}</b><small>{e(t["cat"])}</small></span>'
                     + (f'<span class="rb-al">{e(al)}</span>' if al else '') +
                     f'<span class="rb-s">{e(t["short"])}</span></a>')
        # the entry page
        used = {tid}
        # a body line starting with "## " is a small heading (owner's OK, 21 Oct 2026): lets long entries be scanned
        b = '<div class="rbp-body">' + ''.join((f'<h2 class="rbp-sh">{e(p[3:].strip())}</h2>' if p.startswith('## ') else f'<p>{link_terms(e(p), used)}</p>') for p in t['body']) + '</div>'
        if t.get('tool') == 'pu':
            opts = '<option value="0">なし・上限内</option><option value="10">初めて超えた（+10）</option><option value="5">2回目以降（+5）</option>'
            rows = ''.join(f'<label>{e(p)}<select aria-label="{e(p)}">{opts}</select></label>' for p in ['エンジン（ICE）', 'ターボ', 'MGU-K', 'バッテリー（ES）', '制御電子機器（CE）'])
            b += PU_TOOL.format(rows=rows) + PU_JS
        if t.get('rule'):
            b += f'<div class="rb-h">規則</div><span class="rb-rule">FIA {e(t["rule"])}</span>'
        b += f'<!--reads:{tid}-->'  # filled by add_term_reads() once every column and STORY is written
        if t.get('examples'):
            b += '<div class="rb-h">今季の実例・関連記事</div><ul class="rb-ex">' + ''.join(f'<li><a href="{e(x["u"])}">{e(x["t"])}</a></li>' for x in t['examples']) + '</ul>'
        if t.get('see'):
            b += '<div class="rb-h">あわせて読む</div><div class="rb-see">' + ''.join(f'<a href="{rb_url(s)}">{e(name.get(s, s))}</a>' for s in t['see'] if s in name) + '</div>'
        others = [x for x in by_cat.get(t['cat'], []) if x['id'] != tid and x['id'] not in (t.get('see') or [])][:12]
        if others:
            b += f'<div class="rb-h">「{e(t["cat"])}」のほかの用語</div><div class="rb-see">' + ''.join(f'<a href="{rb_url(x["id"])}">{e(x["term"])}</a>' for x in others) + '</div>'
        if t.get('src'):  # each entry's own sources, linked, on its page (owner's OK, 21 Oct 2026); "note" says what it supports
            b += (f'<details class="rb-srcbox"><summary>主な出典（{len(t["src"])}件）</summary><ul class="rb-ex rb-src">' + ''.join(
                f'<li><a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["name"])}：{e(x["title"])} ↗</a>'
                + (f'<small>{e(x["note"])}</small>' if x.get('note') else '') + '</li>' for x in t['src']) + '</ul></details>')
        chk = t.get('checked') or R['checked']
        b += f'<p class="rb-checked">規則の中身は {e(chk)} 時点で確認しています。</p>'
        used.discard(tid)
        ld_term = {'@context': 'https://schema.org', '@type': 'DefinedTerm', 'name': t['term'], 'alternateName': t.get('aliases', [])[:4],
                   'description': t['short'], 'url': SITE + rb_url(tid), 'inDefinedTermSet': term_set, 'inLanguage': 'ja'}
        main = re.sub(r'（.*?）', '', t['term']).strip() or t['term']
        og = rules_og(tid, main + 'とは', t['cat'], t['short'])
        if og:
            ld_term['image'] = og
        _rb_page(R, tid, 'term', t['term'], t['cat'], al, t['short'], b, used, ld_term,
                 f'{t["term"]}とは｜意味をやさしく解説｜F1用語・ルール辞典｜F1グリッドウォーク', og)
        sm.append((SITE + rb_url(tid), chk + 'T09:00:00+09:00', None, '0.6'))
    for p in PEOPLE:
        tid = 'person-' + p['id']
        keys = ' '.join([p['role'], p['org']] + p.get('words', []))
        al = '・'.join([x for x in [p.get('en', '')] + p.get('aliases', []) if x][:3])
        items.append(f'<a class="rb rbl" id="{e(tid)}" href="{rb_url(tid)}" data-c="人物" data-t="{e(p["name"])}" data-names="{e("|".join([p["name"], p.get("en", ""), p.get("kana", "")] + p.get("aliases", [])))}" data-k="{e(keys)}">'
                     f'<span class="rb-t"><b>{e(p["name"])}</b><small>人物</small></span>'
                     + (f'<span class="rb-al">{e(al)}</span>' if al else '') +
                     f'<span class="rb-s">{e(p["short"])}</span></a>')
        # the person's page as a fan's way in (owner's OK, 22 Oct 2026): reading first, then team, news, people around them
        b = f'<div class="rb-h" style="margin-top:0">肩書き</div><span class="rb-rule">{e(p["role"])}（{e(p["org"])}）</span>'
        tk = next((k for k, t in TEAMS_ALL.items() if t.get('name') and t['name'] in p.get('org', '')), None)
        if tk and os.path.exists(os.path.join(ROOT, 'teams', tk, 'index.html')):
            b += f'<p class="rb-team"><a href="/teams/{e(tk)}/" data-track="click/person/{e(p["id"])}/team">{e(TEAMS_ALL[tk]["name"])}の記事を、まとめて読む →</a></p>'
        if tk and p.get('role') == 'ドライバー':
            mates = [x for x in team_people(tk)[0] if x['id'] != p['id']]
            if mates:
                b += ('<p class="rb-mate">チームメイト：' + '、'.join(f'<a href="/deep/rules/person-{e(x["id"])}/" data-track="click/person/{e(p["id"])}/mate">{e(x["name"])} →</a>' for x in mates) + '</p>')
            engs = engineers_of(p)
            if engs:  # the voice on the radio (owner's OK, 23 Oct 2026)
                b += ('<p class="rb-mate">レースエンジニア：' + '、'.join(f'<a href="/deep/rules/person-{e(x["id"])}/" data-track="click/person/{e(p["id"])}/engineer">{e(x["name"])} →</a>' for x in engs) + '</p>')
        if 'エンジニア' in p.get('role', '') and p.get('role') != 'ドライバー':
            drv = [d for d in PEOPLE if d.get('role') == 'ドライバー' and p in engineers_of(d)]
            if drv:
                b += ('<p class="rb-mate">担当ドライバー：' + '、'.join(f'<a href="/deep/rules/person-{e(d["id"])}/" data-track="click/person/{e(p["id"])}/driver">{e(d["name"])} →</a>' for d in drv) + '</p>')
        pu = {tid}  # never link the person's own name on their own page (column desk, 24 Oct 2026)
        if p.get('body'):  # longer text, e.g. 「## 経歴」 (column desk request, owner's OK, 24 Oct 2026)
            b += '<div class="rbp-body" style="margin-top:22px">' + ''.join(
                (f'<h2 class="rbp-sh">{e(x[3:].strip())}</h2>' if x.startswith('## ') else f'<p>{body_links(x, pu)}</p>') for x in p['body']) + '</div>'
        b += f'<!--reads:{tid}-->'
        app = [u for u in p.get('appears', []) if u in titles]
        if app:
            b += '<div class="rb-h">登場する記事</div><ul class="rb-ex">' + ''.join(f'<li><a href="{e(u)}">{e(titles[u])}</a></li>' for u in app) + '</ul>'
        pn_ = person_news(p, ALLARTS)
        if pn_:
            b += (f'<div class="rb-h">{e(p["name"])}が出てくる最新ニュース</div><ul class="rb-ex">'
                  + ''.join(f'<li><a href="/news/{e(a["id"])}/" data-track="click/person/{e(p["id"])}/news">{e(a["title"])}</a></li>' for a in pn_) + '</ul>')
        b += f'<!--peers:{tid}-->'
        if p.get('sources'):
            b += (f'<details class="rb-srcbox"><summary>出典（肩書きの確認・{len(p["sources"])}件）</summary><ul class="rb-ex rb-src">' + ''.join(
                f'<li><a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["name"])}：{e(x["title"])} ↗</a></li>' for x in p['sources']) + '</ul></details>')
        b += f'<p class="rb-checked">{e(p.get("checked", ""))} に確認</p>'
        ld_p = {'@context': 'https://schema.org', '@type': 'Person', 'name': p['name'], 'alternateName': p.get('en', ''), 'jobTitle': p['role'],
                'worksFor': {'@type': 'Organization', 'name': p['org']}, 'url': SITE + rb_url(tid), 'description': p['short']}
        og = rules_og(tid, p['name'], '人物', f'{p["role"]}（{p["org"]}）', 'F1人物辞典')
        pu.discard(tid)
        _rb_page(R, tid, 'person', p['name'], '人物', al, p['short'], b, pu, ld_p,
                 f'{p["name"]}とは｜経歴・役職（{re.sub(r"（.*?）", "", p["org"]).strip()}）｜F1人物辞典｜F1グリッドウォーク', og)
        sm.append((SITE + rb_url(tid), (p.get('checked') or R['checked']) + 'T09:00:00+09:00', None, '0.5'))
    # remove pages of entries that no longer exist
    rdir = os.path.join(ROOT, 'deep', 'rules')
    keep = set(name) | {'sources'}
    for d in os.listdir(rdir):
        if os.path.isdir(os.path.join(rdir, d)) and d not in keep and os.path.exists(os.path.join(rdir, d, 'index.html')):
            os.remove(os.path.join(rdir, d, 'index.html'))
            try: os.rmdir(os.path.join(rdir, d))
            except OSError: pass
    write('deep/rules/search.json', json.dumps(search, ensure_ascii=False, separators=(',', ':')) + '\n')
    # logo mini-game: daily rule quiz (owner's choice, 13 Oct 2026). Small file: id, name, cat, short.
    # Entries whose short text gives away the name (or an alias) are left out.
    quiz = []
    for t in R['terms']:
        nm = re.sub(r'（[^）]*）', '', t['term']).strip()
        words = [nm, t['term']] + [a for a in (t.get('aliases') or []) if len(a) >= 2]
        sh = t.get('short') or ''
        if not sh or any(w and w in sh for w in words):
            continue
        quiz.append({'id': t['id'], 'n': nm, 'c': t['cat'], 's': sh})
    write('deep/rules/quiz.json', json.dumps({'terms': quiz}, ensure_ascii=False, separators=(',', ':')) + '\n')
    sugg = ''.join(f'<button type="button">{e(w)}</button>' for w in ['降格', 'DRS', 'ハジャー', '折原', 'ADUO'])
    body = ('<nav class="crumbs"><a href="/">トップ</a> › <a href="/deep/">DEEP GRID</a> › ルールブック</nav><div class="dg">'
            f'<div class="dg-top"><div class="dg-label"><b>DEEP GRID<i>RULES</i></b><span>{DEEP_COPY}</span></div></div>'
            f'<h1>{e(R["title"])}</h1><p class="dg-dek">{e(R["dek"])}</p>'
            + rules_entry('rules', on_page=True)
            + f'<div class="rb-none" id="rb-none">見つかりませんでした。<span style="display:none"><br>もしかして：<span id="rb-maybe"></span></span><br>こんな言葉はどうですか：<br>{sugg}</div>'
            + '<div class="rb-list">' + ''.join(items) + '</div>' +
            f'<p class="rb-checked" style="margin-top:18px">規則の中身は {e(R["checked"])} 時点で確認しています。FIAが規則を変えたときは、ここを直して日付を更新します。</p>'
            f'<div class="dg-end"><h2><span class="k">SOURCES</span>出典</h2><p class="rb-checked">説明は、FIAの規則と各国の報道（{len(R.get("sources", []))}件）で確かめています。 <a href="/deep/rules/sources/">出典の一覧を見る →</a></p></div></div>' + RULES_JS)
    src_body = ('<nav class="crumbs"><a href="/">トップ</a> › <a href="/deep/">DEEP GRID</a> › <a href="/deep/rules/">ルールブック</a> › 出典</nav><div class="dg">'
                f'<h1>ルールブックの出典</h1><p class="dg-dek">F1用語・ルール辞典の説明を確かめるのに使った資料です（{len(R.get("sources", []))}件）。</p>'
                '<ol class="dg-src">' + ''.join(f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["name"])}</a> <small>{e(s["title"])}</small></li>' for s in R.get('sources', []))
                + '</ol><a class="rbp-back" href="/deep/rules/">← ルールブックの一覧へ</a></div>')
    write('deep/rules/sources/index.html', page('ルールブックの出典｜F1用語・ルール辞典｜F1グリッドウォーク', 'F1グリッドウォークのF1用語・ルール辞典で使った資料の一覧。', SITE + '/deep/rules/sources/',
                                                 src_body, f'<meta name="robots" content="noindex,follow">\n<style>{DEEP_CSS}{RBP_CSS}</style>\n', og_type='website'))
    head = MONO_FONT + f'<style>{DEEP_CSS}{RULES_CSS}{RULES_ENTRY_CSS}{RBP_CSS}</style>\n' + ld({
        '@context': 'https://schema.org', '@type': 'DefinedTermSet', 'name': R['title'], 'description': R['dek'], 'url': url, 'inLanguage': 'ja',
        'hasDefinedTerm': [{'@type': 'DefinedTerm', 'name': t['term'], 'url': SITE + rb_url(t['id'])} for t in R['terms']]})
    write('deep/rules/index.html', page('F1用語・ルール辞典 2026｜意味をやさしく解説｜F1グリッドウォーク',
                                         f'グリッド降格、オーバーテイクモード、セーフティカー、タイヤの種類……F1の用語とルールの意味を、2026年の規則と今季の実例でやさしく解説。{len(R["terms"])}語と人物を、言葉を入れて検索できます。', url, body, head, og_type='website'))
    return [(url, R['checked'] + 'T09:00:00+09:00', 'weekly', '0.8')] + sm



def top_rules_slot():
    """Top page: rulebook search box between 最新の記事 and ランキング (owner's request, 3 Oct 2026). Fills <!--pre:rules--> in index.html."""
    ip = os.path.join(ROOT, 'index.html'); src = open(ip, encoding='utf-8').read()
    blk = ('<style>' + RULES_ENTRY_CSS + '</style>' + MONO_FONT + rules_entry('top')) if RULES else ''
    out = re.sub(r'(<!--pre:rules-->).*?(<!--/pre:rules-->)', lambda m: m.group(1) + blk + m.group(2), src, count=1, flags=re.S)
    if out != src:
        open(ip, 'w', encoding='utf-8').write(out)


# ---- per-article share image (owner's request, 8 Oct 2026) -----------------------------------------
# news/<id>/og.png: the headline on the site's paper colour. Needs Pillow and the Noto CJK fonts;
# when either is missing the article simply keeps the site-wide og-image.png.
def _og_font(system, local):
    # the system Noto CJK font, or the Japanese subset kept on the reserve branch (tools/fonts/),
    # copied into .ogfonts/ by the update routine (ROUTINE.md 7b) when the system font is missing
    for f in (system, os.path.join(ROOT, '.ogfonts', local)):
        if os.path.exists(f):
            return f
    return system


OG_SERIF = _og_font('/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc', 'NotoSerifCJK-Black-JP-sub.otf')
OG_SANS = _og_font('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 'NotoSansCJK-Bold-JP-sub.otf')
OG_VER = 'og1'
OG_KC = {'primary': '#2E6B3A', 'news': '#4B5261', 'tech': '#1F5E8A', 'rumor': '#B0532C', 'fan': '#7A4A93'}
OG_NOSTART = set('、。，．・：；？！」』）】〕〉》ー…‥ァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎ々)]}%,.!?')
OG_NOEND = set('「『（【〔〈《([{')
_OG = {}


def _og_tools():
    if 'ok' not in _OG:
        try:
            from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
            ok = os.path.exists(OG_SERIF) and os.path.exists(OG_SANS) and os.path.exists(os.path.join(ROOT, 'og-image.png'))
            if ok:
                _OG.update(Image=Image, Draw=ImageDraw, Font=ImageFont, Png=PngImagePlugin,
                           logo=Image.open(os.path.join(ROOT, 'og-image.png')).convert('RGB').crop((80, 62, 500, 172)))
            _OG['ok'] = ok
        except Exception:
            _OG['ok'] = False
    return _OG['ok']


def _og_wrap(d, text, font, w):
    lines, cur = [], ''
    for ch in text:
        t = cur + ch
        if not cur or d.textlength(t, font=font) <= w:
            cur = t
            continue
        if (ch in OG_NOSTART or cur[-1] in OG_NOEND) and len(cur) > 1:
            lines.append(cur[:-1])
            cur = cur[-1] + ch
        else:
            lines.append(cur)
            cur = ch
        cur = cur.lstrip('\u3000 ')
    if cur:
        lines.append(cur)
    return [l.rstrip('\u3000 ') for l in lines]


def article_og(a, k):
    """Write news/<id>/og.png when the headline changed; return its URL (or None to use the site image)."""
    if not _og_tools():
        return None
    src = a['source'] + ('\u3000' + a['region'] if a.get('region') else '')
    stamp = hashlib.sha1('|'.join((OG_VER, a['title'], src, k)).encode()).hexdigest()[:10]
    rel = f'news/{a["id"]}/og.png'
    p = os.path.join(ROOT, rel)
    url = f'{SITE}/{rel}?v={stamp}'
    I = _OG['Image']
    try:
        if os.path.exists(p) and I.open(p).text.get('gw') == stamp:
            return url
    except Exception:
        pass
    try:
        F, W, H = _OG['Font'].truetype, 1200, 630
        im = I.new('RGB', (W, H), '#F3EFE6')
        d = _OG['Draw'].Draw(im)
        im.paste(_OG['logo'], (80, 52))
        fs, fk = F(OG_SANS, 26), F(OG_SANS, 22)
        sw = d.textlength(src, font=fs)
        kw = d.textlength(KIND[k], font=fk) + 28
        x = W - 80 - sw
        d.text((x, 92), src, font=fs, fill='#5B5F57')
        kx = x - 18 - kw
        d.rounded_rectangle((kx, 90, kx + kw, 128), radius=8, outline=OG_KC[k], width=2)
        d.text((kx + 14, 94), KIND[k], font=fk, fill=OG_KC[k])
        for size in (68, 62, 56, 50):
            f = F(OG_SERIF, size)
            lines = _og_wrap(d, a['title'], f, 1040)
            lh = int(size * 1.38)
            maxl = 330 // lh
            if len(lines) <= maxl:
                break
        if len(lines) > maxl:
            lines = lines[:maxl]
            l = lines[-1]
            while l and d.textlength(l + '…', font=f) > 1040:
                l = l[:-1]
            lines[-1] = l + '…'
        y0 = 200 + (340 - lh * len(lines)) // 2
        for i, l in enumerate(lines):
            d.text((80, y0 + i * lh), l, font=f, fill='#1F2420')
        d.rectangle((0, 560, W, H), fill='#1F2420')
        fb = F(OG_SANS, 26)
        d.text((80, 577), '世界のF1ニュースを、日本語で。', font=fb, fill='#F3EFE6')
        u = 'f1gridwalk.github.io'
        d.text((W - 80 - d.textlength(u, font=fb), 577), u, font=fb, fill='#E8946C')
        info = _OG['Png'].PngInfo()
        info.add_text('gw', stamp)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        im.quantize(colors=48, method=I.Quantize.MEDIANCUT).save(p, optimize=True, pnginfo=info)
        return url
    except Exception:
        return None


def rules_og(tid, head, tag, sub, right='F1用語・ルール辞典'):
    """deep/rules/<id>/og.png: the entry name and its one-line explanation (owner's request, 9 Oct 2026)."""
    if not _og_tools():
        return None
    stamp = hashlib.sha1('|'.join(('rb1', head, tag, sub, right)).encode()).hexdigest()[:10]
    rel = f'deep/rules/{tid}/og.png'
    p = os.path.join(ROOT, rel)
    url = f'{SITE}/{rel}?v={stamp}'
    I = _OG['Image']
    try:
        if os.path.exists(p) and I.open(p).text.get('gw') == stamp:
            return url
    except Exception:
        pass
    try:
        F, W, H = _OG['Font'].truetype, 1200, 630
        clay = '#9E4E2B'
        im = I.new('RGB', (W, H), '#F3EFE6')
        d = _OG['Draw'].Draw(im)
        im.paste(_OG['logo'], (80, 52))
        fs, fk = F(OG_SANS, 26), F(OG_SANS, 22)
        sw = d.textlength(right, font=fs)
        kw = d.textlength(tag, font=fk) + 28
        x = W - 80 - sw
        d.text((x, 92), right, font=fs, fill='#5B5F57')
        kx = x - 18 - kw
        d.rounded_rectangle((kx, 90, kx + kw, 128), radius=8, outline=clay, width=2)
        d.text((kx + 14, 94), tag, font=fk, fill=clay)
        for size in (76, 68, 60, 52):
            f = F(OG_SERIF, size)
            lines = _og_wrap(d, head, f, 1040)
            if len(lines) <= 2:
                break
        lines = lines[:2]
        lh = int(size * 1.3)
        fsub = F(OG_SANS, 30)
        sl = _og_wrap(d, sub, fsub, 1040)
        if len(sl) > 2:
            l = sl[1]
            while l and d.textlength(l + '…', font=fsub) > 1040:
                l = l[:-1]
            sl = [sl[0], l + '…']
        slh = 46
        total = lh * len(lines) + 22 + slh * len(sl)
        y = 190 + (350 - total) // 2
        for l in lines:
            d.text((80, y), l, font=f, fill='#1F2420')
            y += lh
        y += 22
        d.rectangle((80, y + 4, 86, y + slh * len(sl) - 6), fill=clay)
        for l in sl:
            d.text((104, y), l, font=fsub, fill='#3A3E37')
            y += slh
        d.rectangle((0, 560, W, H), fill='#1F2420')
        fb = F(OG_SANS, 26)
        d.text((80, 577), 'F1の用語とルールを、やさしく。', font=fb, fill='#F3EFE6')
        u = 'f1gridwalk.github.io'
        d.text((W - 80 - d.textlength(u, font=fb), 577), u, font=fb, fill='#E8946C')
        info = _OG['Png'].PngInfo()
        info.add_text('gw', stamp)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        im.quantize(colors=48, method=I.Quantize.MEDIANCUT).save(p, optimize=True, pnginfo=info)
        return url
    except Exception:
        return None


# ---- RSS feed (owner's request, 8 Oct 2026) ---------------------------------------------------------
def rfc822(d):
    d = d.astimezone(timezone.utc)
    return d.strftime('%a, %d %b %Y %H:%M:%S +0000')


def build_feed(allarts):
    """feed.xml: the newest news summaries and columns in one RSS 2.0 feed."""
    items = []
    for a in allarts[:40]:
        items.append((when(a), a['title'], f'{SITE}/news/{a["id"]}/', a.get('summary', ''), KIND[kind_of(a)]))
    for x in ALL_COLS[:20]:
        dt = x['dt'] if x['dt'].tzinfo else x['dt'].replace(tzinfo=JST)
        items.append((dt, x['title'], SITE + x['url'], '', COL_TAG[x['kind']]))
    items.sort(key=lambda t: t[0], reverse=True)
    items = items[:50]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">', '<channel>',
           '<title>F1 Grid Walk（F1グリッドウォーク）</title>', f'<link>{SITE}/</link>',
           '<description>世界のF1ニュースを、日本語の見出しと短い要約で。海外報道の読み比べや深掘りのコラムも。</description>',
           '<language>ja</language>', f'<atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>',
           f'<lastBuildDate>{rfc822(items[0][0]) if items else rfc822(datetime.now(JST))}</lastBuildDate>']
    for dt, title, link, desc, cat in items:
        out.append(f'<item><title>{e(title)}</title><link>{e(link)}</link><guid isPermaLink="true">{e(link)}</guid>'
                   f'<pubDate>{rfc822(dt)}</pubDate><category>{e(cat)}</category>'
                   + (f'<description>{e(desc)}</description>' if desc else '') + '</item>')
    out += ['</channel>', '</rss>']
    write('feed.xml', '\n'.join(out) + '\n')


# ---- related rulebook entries on news pages (owner's request, 9 Oct 2026) ---------------------------
_KW = {}


def _kw_names(names):
    out = []
    for n in names:
        n = (n or '').strip()
        if len(n) < 2 or re.fullmatch(r'[ぁ-ゟー]+', n):
            continue
        if re.fullmatch(r'[A-Za-z0-9 .\-]+', n) and len(n) <= 2:
            continue  # GP, PU, TP … match far too much
        out.append(n)
    return out


_KATA = r'\u30a0-\u30ff'


_KW_RE = {}


def _kw_hit(n, text):
    """Whole-word match: a katakana or Latin name must not run on into more katakana / letters
    (オーバー ≠ オーバーテイク, レーキ ≠ ブレーキ). Patterns are compiled once (thousands of names)."""
    if n not in text:
        return False
    r = _KW_RE.get(n)
    if r is None:
        pre = r'(?<![A-Za-z])' if re.match(r'[A-Za-z]', n) else (f'(?<![{_KATA}])' if re.match(f'[{_KATA}]', n) else '')
        post = r'(?![A-Za-z])' if re.search(r'[A-Za-z]$', n) else (f'(?![{_KATA}])' if re.search(f'[{_KATA}]$', n) else '')
        r = _KW_RE[n] = re.compile(pre + re.escape(n) + post)
    return r.search(text) is not None


def _kw_index(allarts):
    """Entries with their names (main name first), and how common each name is across all news."""
    if _KW:
        return _KW
    ents = []
    if RULES:
        for t in RULES['terms']:
            main = re.sub(r'（.*?）', '', t['term']).strip()
            ents.append({'id': t['id'], 'kind': 'term', 'name': t['term'], 'cat': t['cat'], 'short': t['short'],
                         'main': _kw_names([t['term'], main]), 'alias': _kw_names(t.get('aliases', [])),
                         'ex': {x.get('u', '') for x in t.get('examples', [])}})
    for p in PEOPLE:
        ents.append({'id': 'person-' + p['id'], 'kind': 'person', 'name': p['name'], 'cat': '人物', 'short': p['short'],
                     'main': _kw_names([p['name']]), 'alias': _kw_names(p.get('aliases', []) + [p.get('en', '')]), 'ex': set(p.get('appears', []))})
    texts = [a['title'] + ' ' + a.get('summary', '') for a in allarts]
    df = {}
    for en in ents:
        for n in en['main'] + en['alias']:
            if n not in df:
                df[n] = sum(1 for t in texts if _kw_hit(n, t)) / max(1, len(texts))
    _KW.update(ents=ents, df=df)
    return _KW


def related_entries(a, allarts, n_terms=4, n_people=3):
    K = _kw_index(allarts)
    text = a['title'] + ' ' + a.get('summary', '')
    me = f'/news/{a["id"]}/'
    terms, people = [], []
    for en in K['ents']:
        if me in en['ex']:
            score = 0
        else:
            m = [n for n in en['main'] if _kw_hit(n, text)]
            al = [n for n in en['alias'] if _kw_hit(n, text) and (en['kind'] == 'person' or K['df'].get(n, 1) <= 0.08)]
            if m:
                if en['kind'] == 'term' and min(K['df'][n] for n in m) > 0.2:
                    continue  # very common words (グランプリ …) say little about this article
                score = 1 + min(K['df'][n] for n in m)
            elif al:
                score = 2 + min(K['df'][n] for n in al)
            else:
                continue
        pos = min([text.find(n) for n in en['main'] + en['alias'] if _kw_hit(n, text)] or [9999])
        (people if en['kind'] == 'person' else terms).append((score, pos, en))
    terms.sort(key=lambda x: (x[0], x[1]))
    people.sort(key=lambda x: (x[1], x[0]))
    return [x[2] for x in terms[:n_terms]], [x[2] for x in people[:n_people]]


# ---- topic hubs: one page per story that pulls the outlets together (prototype, owner's review 12 Oct 2026) ----
HUBS = {}


def load_hubs():
    d = os.path.join(ROOT, 'topics')
    if not os.path.isdir(d):
        return {}
    for fn in sorted(os.listdir(d)):
        if fn.endswith('.json'):
            H = load(os.path.join('topics', fn))
            if H and H.get('slug') and (not H.get('draft') or os.environ.get('PREVIEW_DRAFTS') == '1'):
                HUBS[H['slug']] = H
    return HUBS


def hub_for_article(aid):
    for H in HUBS.values():
        if any(o['id'] == aid for o in H.get('outlets', [])):
            return H
    return None


HUB_CSS = '''
.hub-k{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin:22px 0 0;font-size:12.5px;color:var(--muted);letter-spacing:.06em}
.hub-k b{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;letter-spacing:.24em;color:var(--clay)}
.hub h1{font-size:clamp(25px,6.4vw,34px);line-height:1.45;margin:10px 0 2px}
.hub h1 small{display:block;font-size:.55em;color:var(--muted);font-weight:700;margin-top:4px}
.hub-dek{font-size:16px;line-height:1.95;margin:14px 0 6px}
.hub-meta{font-size:12px;color:var(--muted);margin:0 0 6px}
.hub-meta-after{margin:26px 0 0}
.hub h2{font-size:17px;margin:30px 0 10px;padding-top:16px;border-top:2px solid var(--ink);display:flex;align-items:baseline;gap:10px}
.hub h2 i{font-style:normal;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.2em;color:var(--clay)}
.hub ul.dots{margin:0;padding-left:1.2em}.hub ul.dots li{font-size:15.5px;line-height:1.85;margin:4px 0}
.hub-o{border:1px solid var(--line);border-radius:14px;background:var(--surface);padding:12px 14px;margin:10px 0}
.hub-o .h{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;font-size:13px;color:var(--muted)}
.hub-o .ang{display:block;font-weight:700;font-size:15px;color:var(--ink);margin:6px 0 4px}
.hub-o ul{margin:0;padding-left:1.1em}.hub-o li{font-size:14.5px;line-height:1.8;margin:3px 0}
.hub-o .lk{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:8px;font-size:13px}
.hub-o .nt{font-size:12px;color:var(--muted);margin:6px 0 0}
.hub-ans{margin:16px 0 8px;padding:14px 16px;border:2px solid var(--ink);border-radius:14px;background:var(--surface)}
.hub-ans-k{font-size:12.5px;font-weight:700;color:var(--clay);letter-spacing:.08em;margin:0 0 4px}
.hub-ans p:last-child{margin:0;font-size:16px;line-height:1.95;font-weight:500}
.hub-si{margin:0}.hub-si dt{font-size:14.5px;font-weight:700;margin:10px 0 2px}.hub-si dd{margin:0 0 0 1em;font-size:14px;line-height:1.75;color:var(--ink-2)}
.hub-sub{font-size:13px;font-weight:700;color:var(--muted);margin:12px 0 4px}
.hub-nq{margin:0 0 12px}.hub-nq p{font-size:15px;font-weight:700;margin:0 0 6px}
.hub-src{font-size:14.5px;line-height:1.85;background:var(--surface);border-left:4px solid var(--clay);border-radius:0 10px 10px 0;padding:10px 14px;margin:0}
.hub-d{display:grid;grid-template-columns:auto 1fr;gap:8px 12px;margin:0}
.hub-d dt{font-size:12px;font-weight:700;border:1px solid var(--line);border-radius:999px;padding:1px 10px;height:max-content;white-space:nowrap}
.hub-d dd{margin:0;font-size:14.5px;line-height:1.8}
@media (max-width:520px){.hub-d{grid-template-columns:1fr;gap:2px}.hub-d dd{margin-bottom:10px}.hub-d dt{justify-self:start}}
.hub-q{font-weight:700;font-size:15.5px;margin:0 0 8px}
.hub-tag{display:inline-block;font-size:11px;font-weight:700;color:var(--clay);border:1px dashed var(--clay);border-radius:999px;padding:0 9px;margin-left:6px}
.hub-chips{display:flex;flex-wrap:wrap;gap:6px}
.hub-nq a.hub-nl{display:block;margin:8px 0 0;padding:10px 14px;border:1px solid var(--line);border-left:3px solid var(--clay);border-radius:10px;background:var(--surface);color:var(--ink);text-decoration:none;font-size:15px;font-weight:700;line-height:1.55}
.hub-nq a.hub-nl small{display:block;font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--muted);margin-bottom:2px}
.hub a.hub-gp{display:inline-block;margin:6px 0 14px;font-size:14.5px;font-weight:700;color:var(--ink)}
.hub-chips a{font-size:14px;border:1px solid var(--line);border-radius:999px;padding:3px 13px;background:var(--surface);text-decoration:none;color:var(--ink)}
.hub-todo{font-size:13.5px;color:var(--muted);margin:10px 0 0}
.hub-up{list-style:none;margin:0;padding:0}.hub-up li{display:grid;grid-template-columns:7.5em 1fr;gap:8px;font-size:14px;line-height:1.7;padding:6px 0;border-bottom:1px solid var(--line)}
.hub-up time{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}
.hub-story{margin:6px 0 0;padding-top:0;border-top:0}
.hub-story h2{margin-bottom:4px}
.hub-by{font-size:12.5px;color:var(--muted);margin:0 0 6px}
.hub-story h3{font-size:16.5px;line-height:1.6;margin:26px 0 8px;padding-left:10px;border-left:4px solid var(--clay)}
.hub-story p{font-size:16px;line-height:2;margin:0 0 14px;color:var(--ink)}
.hub-story p.hub-by{font-size:12.5px;line-height:1.6;color:var(--muted)}
.hub-story .cite{font-size:11.5px;color:var(--muted);white-space:nowrap}
.hub-story .hub-kw{margin:24px 0 0}
.hub-story .kw-h{font-size:14px;line-height:1.5;margin:0 0 4px;color:var(--ink)}
.hub-story .kw-p{margin-top:8px}
.hub-story .hub-kw-n{font-size:12px;line-height:1.6;color:var(--muted);margin:10px 0 0}
.hub-st-src{margin:22px 0 0;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.hub-st-src .k{font-size:12px;font-weight:700;letter-spacing:.08em;color:var(--muted);margin:0 0 6px}
.hub-st-src ul{list-style:none;margin:0;padding:0}
.hub-st-src li{display:flex;flex-direction:column;gap:1px;font-size:13px;line-height:1.6;padding:6px 0;border-top:1px solid var(--line)}
.hub-st-src li:first-child{border-top:0;padding-top:0}
.hub-st-src li b{font-size:12.5px}.hub-st-src li a{color:var(--ink);word-break:break-word}.hub-st-src li a.sub{font-size:12.5px}
.hub-st-src li small{font-size:11.5px;color:var(--muted)}
.hub-story .hub-st-note{font-size:13px;line-height:1.8;color:var(--muted);border-top:1px dashed var(--line);padding-top:10px;margin-top:18px}
.hub-pv{display:block;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--surface);color:var(--ink);text-decoration:none}
.hub-pv small{display:block;font-size:12px;font-weight:700;color:var(--clay);letter-spacing:.06em}
.hub-pv b{display:block;font-size:15.5px;line-height:1.6;margin-top:2px}
.hub-pv span{display:block;font-size:13.5px;line-height:1.75;color:var(--ink-2);margin-top:2px}
.hubbox{display:block;margin:18px 0 0;padding:12px 14px;border:2px solid var(--ink);border-radius:14px;text-decoration:none;color:var(--ink)}
.hubbox small{display:block;font-size:12px;color:var(--clay);font-weight:700;letter-spacing:.08em}
.hubbox b{display:block;font-size:16px;line-height:1.6;margin-top:2px}
.hubbox span{display:block;font-size:13px;color:var(--muted);margin-top:2px}
'''


# source tags like （The Race） in a hub story are shown small and quiet, so the story reads as one piece
STORY_CITE = re.compile(r'(（(?:The Race|GPblog|Motorsport\.com|F1公式[^）]{0,20})）)')


def story_links(txt, used, extra):
    """Rulebook links inside a 読み解き paragraph: first the story's own phrase→entry pairs
    (story["terms"], for words the dictionary name does not match, e.g. ピットロス, コースに残る),
    then the usual automatic links outside those."""
    h = e(txt)
    ids = {t['id'] for t in (RULES or {}).get('terms', [])}
    for phrase, tid in sorted(extra or [], key=lambda x: -len(x[0])):
        if tid in used or tid not in ids:
            continue
        ph = e(phrase)
        spans = [(m.start(), m.end()) for m in re.finditer(r'<a [^>]*>.*?</a>', h)]
        i = h.find(ph)
        while i >= 0 and any(a <= i < b for a, b in spans):
            i = h.find(ph, i + 1)
        if i >= 0:
            h = h[:i] + f'<a class="term" href="/deep/rules/{tid}/" data-term="{tid}">{ph}</a>' + h[i + len(ph):]
            used.add(tid)
    return link_terms_html(h, used)


def story_terms_box(html):
    """「この記事に出てくる用語」: every rulebook entry linked in the story, in reading order."""
    info = {t['id']: (t['term'], t['cat'], t['short']) for t in (RULES or {}).get('terms', [])}
    info.update({'person-' + p['id']: (p['name'], '人物', p['short']) for p in PEOPLE})
    seen = []
    for tid in re.findall(r'data-term="([^"]+)"', html):
        if tid in info and tid not in seen:
            seen.append(tid)
    if not seen:
        return ''
    return ('<aside class="kw hub-kw" aria-label="この記事に出てくる用語"><p class="kw-h">この記事に出てくる用語<small>F1 Grid Walk ルールブックより</small></p>'
            + '<div class="kw-p">' + ''.join(f'<a href="{rb_url(t)}" data-track="click/hub-kw/{e(t)}">{e(re.sub(r"（.*?）", "", info[t][0]))}</a>' for t in seen)
            + '</div><p class="hub-kw-n">本文の下線の言葉をタップすると、その場で意味が読めます。</p></aside>')


def hubs_newest():
    """Published 読み解き, newest first (by their latest update, then checked date)."""
    def key(H):
        ups = [u.get('at', '') for u in H.get('updates', [])]
        return (max(ups) if ups else '', H.get('checked', ''))
    return sorted(HUBS.values(), key=key, reverse=True)


def hub_li(H, track):
    S = H.get('story') or {}
    line = S.get('hook') or H.get('dek', '')
    return (f'<li><a class="yk-i" href="/topics/{e(H["slug"])}/" data-track="{e(track)}">'
            f'<small>{e(H.get("gp", ""))} · {e(H.get("checked", "").replace("-", "/"))}</small>'
            f'<b>{e(H["title"])}</b><span>{e(line)}</span></a></li>')


YK_CSS = """
.yk-list{list-style:none;margin:0;padding:0}
.yk-list li{border-top:1px solid var(--line)}
.yk-list li:first-child{border-top:0}
.yk-i{display:block;padding:14px 0;color:var(--ink);text-decoration:none}
.yk-i small{display:block;font-size:12px;color:var(--muted);letter-spacing:.04em}
.yk-i b{display:block;font-size:17px;line-height:1.55;margin-top:3px}
.yk-i span{display:block;font-size:14px;line-height:1.8;color:var(--ink-2);margin-top:4px;padding-left:10px;border-left:3px solid var(--clay)}
.yk-i:hover b{text-decoration:underline;text-underline-offset:3px}
.yk-box{margin:18px 0 26px;padding:14px 16px 8px;border:2px solid var(--ink);border-radius:16px;background:var(--surface)}
.yk-box h2{display:flex;align-items:baseline;gap:10px;font-size:18px;margin:0 0 4px}
.yk-box h2 i{font-style:normal;font-size:11px;letter-spacing:.2em;color:var(--clay)}
.yk-box p.yk-lead{font-size:13px;color:var(--muted);margin:0 0 4px}
.yk-all{display:inline-block;margin:8px 0 6px;font-size:14px;font-weight:700;color:var(--clay)}
.yk-mini{margin:14px 0 22px;padding:10px 14px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.yk-mh{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 10px;margin:0 0 4px}
.yk-mh b{font-size:12px;letter-spacing:.2em;color:var(--clay)}
.yk-mh span{font-size:12px;color:var(--muted)}
.yk-mini ul{list-style:none;margin:0;padding:0}
.yk-mini li a{display:block;padding:5px 0;font-size:14.5px;font-weight:700;line-height:1.55;color:var(--ink);text-decoration:none}
.yk-mini li a:hover{text-decoration:underline;text-underline-offset:3px}
.yk-mini .yk-all{margin:4px 0 2px;font-size:13px}
"""


def latest_hub():
    """The newest published topic hub (by its latest update, then checked date), shown at the top of the top page."""
    if not HUBS:
        return None
    def key(H):
        ups = [u.get('at', '') for u in H.get('updates', [])]
        return (max(ups) if ups else '', H.get('checked', ''))
    return max(HUBS.values(), key=key)


# making-of records in topics/*.json "updates" (drafts, owner's notes, approvals) stay in the data
# but are not shown to readers (review, 18 Oct 2026). "internal": true/false on an entry overrides the guess.
UPD_INTERNAL = re.compile(r'^F1 Grid Walk：|オーナー|下書き|第\d+稿|注釈|レビュー|原文を確認|読者点検')


# How far STORY readers get: half of the story, its end, the NEXT links (once each per visit; no personal data).
# Owner's OK, 24 Oct 2026 — to see whether readers who leave after one STORY reached the links at the end.
STORY_SCROLL_JS = """<script>
(function(){
  var slug = '__SLUG__';
  function gc(path, title){
    var n = 0;
    (function t(){
      if (window.goatcounter && window.goatcounter.count){ try { window.goatcounter.count({ path:path, title:title, event:true }); } catch(e){} return; }
      if (++n < 20) setTimeout(t, 500);
    })();
  }
  function top(sel){ var el = document.querySelector(sel); return el ? el.getBoundingClientRect().top : null; }
  var marks = [
    ['half', 'STORY：本文の半分まで見えた', function(){ var a = top('.hub-story .hub-by'), b = top('.hub-story .hub-kw') || top('.hub-nq'); return (a === null || b === null) ? null : (a + b) / 2; }],
    ['end', 'STORY：本文の終わりまで見えた', function(){ var b = top('.hub-story .hub-kw'); return b === null ? top('.hub-nq') : b; }],
    ['next', 'STORY：「次の疑問へ」まで見えた', function(){ return top('.hub-nq'); }]
  ];
  var busy = false;
  function check(){
    busy = false;
    var h = window.innerHeight || document.documentElement.clientHeight;
    marks = marks.filter(function(m){
      var y = m[2]();
      if (y !== null && y < h * 0.8){ gc('scroll/story/' + slug + '/' + m[0], m[1] + '（' + slug + '）'); return false; }
      return true;
    });
    if (!marks.length) window.removeEventListener('scroll', on);
  }
  function on(){ if (!busy){ busy = true; (window.requestAnimationFrame || setTimeout)(check); } }
  window.addEventListener('scroll', on, { passive:true });
})();
</script>"""


# STORY subjects the slug does not spell out (ボノ = Peter Bonnington, Jos is not in the dictionary)
STORY_SEO_NAMES = {'bono-leave-that-to-me': ['ボニントン', 'アントネッリ'],
                   'jos-verstappen-setup': ['ヨス・フェルスタッペン'],          # not Max
                   'haas-komatsu-fastest-driver': ['小松礼雄', '平川亮']}


def story_seo_title(H):
    """<title> for a STORY: the (often poetic) headline plus who it is about and the GP, so that a reader
    searching 「角田裕毅」 or 「ボルトレート」 finds it (owner's OK, 24 Oct 2026). The visible headline is unchanged.
    Who = people whose dictionary id contains a word of the slug (bortoleto-twenty-years → ボルトレート),
    or STORY_SEO_NAMES. Never guessed from the lead: a lead names other people too."""
    last = {}
    for q in PEOPLE:
        last.setdefault(q['name'].split('・')[-1], []).append(q)
    def short(q):
        n = q['name']
        return n if '・' not in n or len(last[n.split('・')[-1]]) > 1 else n.split('・')[-1]
    names = list(STORY_SEO_NAMES.get(H['slug'], []))
    if not names:
        for tok in H['slug'].split('-'):
            hits = [q for q in PEOPLE if tok in q['id'].split('-') and len(tok) >= 3]
            if len(hits) == 1 and short(hits[0]) not in names:
                names.append(short(hits[0]))
    names = [n for n in names if n not in H['title']][:2]
    parts = [H['title'] + ('　' + 'と'.join(names) if names else '')]
    if H.get('gp', '').endswith('GP'):
        parts.append(H['gp'])
    return '｜'.join(parts + ['STORY'])


def reader_updates(updates):
    """What readers see under UPDATES: the news events, corrections and real additions,
    plus one line for when the STORY went out (the approval record, else the last making-of record)."""
    def internal(u):
        return u['internal'] if 'internal' in u else bool(UPD_INTERNAL.search(u.get('t', '')))
    inner = [u for u in updates if internal(u)]
    out = [u for u in updates if not internal(u)]
    if inner:
        pub = [u for u in inner if '公開' in u.get('t', '')]
        out.append({'at': (pub[0] if pub else inner[-1])['at'], 't': 'F1 Grid Walk で STORY を公開'})
    return sorted(out, key=lambda u: u.get('at', ''))


def read_index():
    """url -> (corner label, title) for every STORY, column and DEEP issue."""
    idx = {f'/topics/{H["slug"]}/': ('STORY', H['title']) for H in HUBS.values()}
    for x in ALL_COLS:
        idx[x['url']] = (COL_TAG[x['kind']], x['title'])
    return idx


def story_gp(H):
    """The /gp/ page of the race a STORY is about, if there is one (newest year first)."""
    base = _gp_base(H.get('gp', ''))
    if not base or not base.endswith('GP'):
        return None
    hits = [g for g in GPS.values() if _gp_base(g['gp']) == base]
    return max(hits, key=lambda g: g['date']) if hits else None


TODO_MEMO = re.compile(r'確かめ|確認|追う|材料|？|\?|答え合わせ')


def reader_todo(H):
    """'準備中' lines readers see: only announcements of a later addition, never desk memos (owner's OK, 23 Oct 2026)."""
    out = []
    for t in H.get('todo', []):
        if '追記' in t and not TODO_MEMO.search(t):
            out.append(re.sub(r'追記する。?$', '追記します。', t))
    return ''.join(f'<p class="hub-todo">今後の追記：{e(t)}</p>' for t in out)


def next_html(H, rname):
    """NEXT: each question leads to the rulebook entries and, when one answers it, a STORY / column / DEEP
    (next[].links, chosen by hand: owner's OK, 21 Oct 2026). The race's /gp/ page closes the block."""
    idx = read_index()
    g = story_gp(H)
    def links(n):
        out = []
        for u in n.get('links', []):
            if u in idx and u != f'/topics/{H["slug"]}/':
                lb, t = idx[u]
                out.append(f'<a class="hub-nl" href="{e(u)}" data-track="click/hub-next/{e(H["slug"])}"><small>{e(lb)}</small>{e(t)} →</a>')
        return ''.join(out)
    return ('<h2><i>NEXT</i>次の疑問へ</h2>' + ''.join(
        f'<div class="hub-nq"><p>{e(n["q"])}</p><div class="hub-chips">' + ''.join(f'<a href="{rb_url(r)}" data-track="click/hub-rule/{e(r)}">{e(rname.get(r, r))} →</a>' for r in n.get('rules', []) if r in rname) + '</div>'
        + links(n) + '</div>' for n in H['next'])
        + (f'<a class="hub-gp" href="/gp/{e(g["slug"])}/" data-track="click/hub-gp/{e(g["slug"])}">{e(g["date"].year)} {e(g["gp"])}の記事を、まとめて読む →</a>' if g else '')
        + reader_todo(H))


def hub_box(H):
    n = len(H.get('outlets', []))
    return (f'<a class="hubbox" href="/topics/{e(H["slug"])}/" data-track="click/hub/{e(H["slug"])}"><small>F1 Grid Walk STORY</small>'
            f'<b>{e(H["title"])}</b><span>' + ('読む →' if H.get('story') else f'{n}つの報道の共通点・違い・まだ分からないこと →') + '</span></a>')


def build_hubs(arch, flag_of):
    out = []
    rname = {t['id']: t['term'] for t in (RULES or {}).get('terms', [])}
    for H in HUBS.values():
        slug = H['slug']
        url = f'{SITE}/topics/{slug}/'
        arts = arch['articles']
        b = [f'<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › <a href="/topics/">STORY</a></nav><div class="hub">',
             f'<p class="hub-k"><b>STORY</b><span>{e(H.get("gp", ""))}</span></p>',
             f'<h1>{e(H["title"])}' + (f'<small>{e(H["sub"])}</small>' if H.get('sub') and not H.get('story') else '') + '</h1>',
             f'<p class="hub-dek">{e(H["dek"])}</p>']
        if H.get('answer') and not H.get('story'):  # with a story, readers go straight to it (owner's decision, 12 Oct 2026)
            b.append(f'<div class="hub-ans"><p class="hub-ans-k">読み比べて分かったこと</p><p>{e(H["answer"])}</p></div>')
        meta = '<p class="hub-meta">' + e(H.get('checkedNote') or f'{len(H["outlets"])}つの報道の原文を {H.get("checked", "")} に確認しました。媒体の分析と、F1 Grid Walk の整理は分けて書いています。') + '</p>'
        if not H.get('story'):
            b.append(meta)
        S = H.get('story')
        blocked = set((S or {}).get('noLink', []))  # entries that would mislead here, e.g. the F1 sprint page from an F3 story (review, 18 Oct 2026)
        used = set(blocked)
        if S:
            n = sum(len(x[1]) for x in S['body'] if x[0] == 'p')
            sb = [f'<section class="hub-story" aria-label="STORY"><h2><i>STORY</i>レースの、もうひとつの物語</h2>',
                  f'<p class="hub-by">{e(S.get("by", "F1 Grid Walk 編集部"))}</p>']
            for kind, txt in S['body']:
                sb.append(f'<h3>{e(txt)}</h3>' if kind == 'h' else '<p>' + STORY_CITE.sub(r'<span class="cite">\1</span>', story_links(txt, used, S.get('terms'))) + '</p>')
            used -= blocked
            sb.append(story_terms_box(''.join(sb)))  # the story's words, tied to the rulebook (owner, 12 Oct 2026)
            if H.get('next'):  # the next questions straight after the story, before the long source list (owner's OK, 18 Oct 2026)
                sb.append(next_html(H, rname))
            if S.get('sources'):  # sources listed once at the end, not inside the text (owner's decision, 12 Oct 2026)
                sb.append('<div class="hub-st-src"><p class="k">出典</p><ul>' + ''.join(
                    f'<li><b>{e(x["name"])}</b><a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["title"])} ↗</a>'
                    + ''.join(f'<a class="sub" href="{e(l["url"])}" target="_blank" rel="noopener">{e(l["label"])} ↗</a>' for l in x.get('links', []))
                    + (f'<small>{e(x["note"])}</small>' if x.get('note') else '') + '</li>' for x in S['sources']) + '</ul></div>')
            sb.append('<p class="hub-st-note">' + ('事実の部分は、上の出典にもとづいています。' if S.get('sources') else '事実の部分は、カッコ内の媒体の報道にもとづいています。')
                      + 'それ以外は編集部の読み解きです。以下に、その材料を並べています。</p></section>')
            b.append(''.join(sb))
            pv_links = []
            for pv in H.get('preview', []):
                Lp = load(os.path.join('lens', pv['lens'] + '.json')) or {}
                if Lp.get('slug') and not Lp.get('draft'):
                    pv_links.append(f'<a class="hub-pv" href="/lens/{e(Lp["slug"])}/" data-track="click/hub-preview/{e(Lp["slug"])}">'
                                    f'<small>レース前の見立て</small><b>{e(Lp.get("title", ""))}</b>'
                                    f'<span>決勝前、注目点に「{e(re.sub(r"^.{1,4}つ目：", "", pv["h2"]).replace("「", "『").replace("」", "』"))}」を挙げていました。当時の文章のまま読めます →</span></a>')
            if pv_links:
                b.append('<h2><i>BEFORE</i>決勝前は、こう見ていた</h2>' + ''.join(pv_links))
            others = [x for x in hubs_newest() if x['slug'] != slug][:5]
            if others:  # the next 読み解き to read, right after this one (owner, 12 Oct 2026)
                b.append('<h2><i>MORE</i>ほかの STORY</h2><ul class="yk-list">' + ''.join(hub_li(x, f'click/hub-more/{x["slug"]}') for x in others) + '</ul>'
                         '<p><a class="yk-all" href="/topics/">すべての STORY →</a></p>')
            b.append(meta.replace('class="hub-meta"', 'class="hub-meta hub-meta-after"'))  # what was checked, shown with the material below the story
        if H.get('common'):
            b.append('<h2><i>COMMON</i>どの報道にも共通する事実</h2><ul class="dots">' + ''.join(f'<li>{e(x)}</li>' for x in H['common']) + '</ul>')
        shown = [o for o in H['outlets'] if arts.get(o['id'])]
        if shown:  # no compared articles → no empty ONLY HERE section (review, 18 Oct 2026)
            b.append('<h2><i>ONLY HERE</i>この記事にしかない情報</h2>' + f'<p class="hub-sub">今回比べた{len(H["outlets"])}本の中で、その記事だけが書いていること</p>')
        for o in shown:
            a = arts.get(o['id'])
            lang = LANG.get(a.get('lang'), '')
            b.append(f'<div class="hub-o"><div class="h"><span class="srcbadge" data-c="{flag_of(a)}">{e(a["source"])}</span><span>{e(a.get("region", ""))} · {e(lang)}</span></div>'
                     f'<span class="ang">{e(o["angle"])}</span><ul>' + ''.join(f'<li>{e(x)}</li>' for x in o['adds']) + '</ul>'
                     + (f'<p class="nt">{e(o["note"])}</p>' if o.get('note') else '') +
                     f'<div class="lk"><a href="/news/{e(a["id"])}/">日本語の要約</a><a href="{e(a["url"])}" target="_blank" rel="noopener" data-track="click/{e(a["id"])}">原文を読む ↗</a>'
                     + ''.join(f'<a href="{e(l["url"])}" target="_blank" rel="noopener">{e(l["label"])} ↗</a>' for l in o.get('links', [])) + '</div></div>')
        if H.get('sourceItems'):
            b.append('<h2><i>SOURCES</i>情報のもとは同じ？</h2><dl class="hub-si">' + ''.join(f'<dt>{e(x["t"])}</dt><dd>{e(x["w"])}</dd>' for x in H['sourceItems']) + '</dl>')
        elif H.get('sources'):
            b.append(f'<h2><i>SOURCES</i>情報のもとは同じ？</h2><p class="hub-src">{e(H["sources"])}</p>')
        if H.get('diffs'):
            b.append('<h2><i>DIFFERENCES</i>報道の違い</h2><dl class="hub-d">' + ''.join(f'<dt>{e(d["k"])}</dt><dd>{e(d["t"])}</dd>' for d in H['diffs']) + '</dl>')
        if H.get('unknownsFillable') or H.get('unknownsLimits'):
            b.append('<h2><i>UNKNOWN</i>まだ分からないこと</h2>')
            if H.get('unknownsFillable'):
                b.append('<p class="hub-sub">資料を足せば分かる可能性があること</p><ul class="dots">' + ''.join(f'<li>{e(x)}</li>' for x in H['unknownsFillable']) + '</ul>')
            if H.get('unknownsLimits'):
                b.append('<p class="hub-sub">公開されている情報では判断できないこと</p><ul class="dots">' + ''.join(f'<li>{e(x)}</li>' for x in H['unknownsLimits']) + '</ul>')
        elif H.get('unknowns'):
            b.append('<h2><i>UNKNOWN</i>まだ分からないこと</h2><ul class="dots">' + ''.join(f'<li>{e(x)}</li>' for x in H['unknowns']) + '</ul>')
        D = H.get('decision')
        if D:
            b.append(f'<h2><i>DECISION</i>その時点で、筋の通った判断だったか<span class="hub-tag">{e(D.get("label", ""))}</span></h2>'
                     f'<p class="hub-q">{e(D["q"])}</p><dl class="hub-d">' + ''.join(f'<dt>{e(r["k"])}</dt><dd>{e(r["t"])}</dd>' for r in D['rows']) + '</dl>')
        if H.get('next'):
            if not H.get('story'):
                b.append(next_html(H, rname))
        elif H.get('rules') or H.get('todo'):
            b.append('<h2><i>NEXT</i>次の疑問へ</h2><div class="hub-chips">' + ''.join(f'<a href="{rb_url(r)}" data-track="click/hub-rule/{e(r)}">{e(rname.get(r, r))}</a>' for r in H.get('rules', []) if r in rname) + '</div>'
                     + reader_todo(H))
        if H.get('updates'):
            def fmt(s):
                try:
                    d = datetime.fromisoformat(s).astimezone(JST); return f'{d.month}/{d.day} {d.hour:02d}:{d.minute:02d}'
                except Exception:
                    return s
            ups = reader_updates(H['updates'])
            if ups:
                b.append('<h2><i>UPDATES</i>この話題の動き</h2><ul class="hub-up">' + ''.join(f'<li><time>{e(fmt(u["at"]))}</time><span>{e(u["t"])}</span></li>' for u in ups) + '</ul>')
        b.append('<p style="margin-top:26px"><a href="/#news">← 最新の記事へ</a></p></div>' + term_assets(used))
        if H.get('story'):
            b.append(STORY_SCROLL_JS.replace('__SLUG__', slug))
        head = MONO_FONT + f'<style>{HUB_CSS}{YK_CSS}</style>\n' + (f'<style>{RULES_CSS}</style>\n' if used else '') + ld({'@context': 'https://schema.org', '@type': 'Article', 'headline': H['title'], 'description': H['dek'][:150],
                                                              'dateModified': H.get('checked', ''), 'inLanguage': 'ja', 'mainEntityOfPage': url, 'author': PUBLISHER, 'publisher': PUBLISHER,
                                                              'citation': [arts[o['id']]['url'] for o in H['outlets'] if o['id'] in arts]})
        write(f'topics/{slug}/index.html', page((story_seo_title(H) if H.get('story') else f'{H["title"]}｜' + H.get('sub', '')) + '｜F1グリッドウォーク', H['dek'][:118] + '…', url, '\n'.join(b), head))
        out.append((url, H.get('checked', '') + 'T09:00:00+09:00', None, '0.7'))
    hs = hubs_newest()
    if hs:  # topics/index.html: every 読み解き, newest first (owner's request, 12 Oct 2026)
        body = ('<nav class="crumbs"><a href="/">トップ</a> › STORY</nav><div class="hub">'
                '<p class="hub-k"><b>F1 GRID WALK</b><span>レースの、もうひとつの物語。</span></p><h1>STORY</h1>'
                '<p class="hub-dek">レースのいちばん心に残った場面を、世界の報道をもとに、F1 Grid Walk が自分の言葉で読み解きます。新しい順に並べています。</p>'
                '<ul class="yk-list">' + ''.join(hub_li(H, f'click/topics/{H["slug"]}') for H in hs) + '</ul>'
                '<p style="margin-top:26px"><a href="/columns/">コラムの一覧へ →</a></p></div>')
        write('topics/index.html', page('STORY｜レースの、もうひとつの物語｜F1グリッドウォーク独自の記事', 'レースのいちばん心に残った場面を、世界の報道をもとにF1グリッドウォークが読み解く独自記事の一覧です。',
                                        SITE + '/topics/', body, MONO_FONT + f'<style>{HUB_CSS}{YK_CSS}</style>\n', og_type='website'))
        out.append((SITE + '/topics/', hs[0].get('checked', '') + 'T09:00:00+09:00', 'weekly', '0.8'))
    return out


# ---- more ways in: GP pages, team pages, month lists (owner's choice, 14 Oct 2026) -------------------------
GP_EXTRA = {'sepang': ['マレーシアGP', 'マレーシア', 'malaysia']}  # this year's race at Sepang is officially the Bahrain GP
GP_MIN = 5          # a GP page needs at least this many news articles
GPS = {}            # slug -> race info (filled by plan_gps)
GP_OF = {}          # article id -> GP slug

ENT_CSS = """
.tm-ppl{margin:14px 0 6px;padding:10px 14px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.tm-ppl p{display:grid;grid-template-columns:5.2em 1fr;align-items:baseline;margin:4px 0;font-size:15px;line-height:1.8}
.tm-ppl span{grid-row:1/9;font-size:12px;font-weight:800;letter-spacing:.06em;color:var(--muted)}
.tm-ppl a{grid-column:2;color:var(--ink);margin:0 0 6px;text-decoration:none}
.tm-ppl a b{font-weight:700;text-decoration:underline;text-underline-offset:3px}
.tm-ppl a small{display:block;font-size:12px;font-weight:400;color:var(--muted);line-height:1.5}
.tm-ppl p.tm-ppl-h{display:block;font-size:12.5px;font-weight:800;letter-spacing:.1em;color:var(--clay);margin:0 0 6px}
.ent-grid li a em{display:block;font-style:normal;font-size:13px;font-weight:700;color:var(--ink-2);margin:2px 0 4px}
.ent-h{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;margin:6px 0 4px}
.ent-k{font-size:12px;font-weight:700;letter-spacing:.18em;color:var(--clay)}
.ent-facts{display:flex;flex-wrap:wrap;gap:6px 10px;margin:0 0 14px;font-size:13.5px;color:var(--ink-2)}
.ent-facts span{border:1px solid var(--line);border-radius:999px;padding:2px 12px;background:var(--surface)}
.ent-map{float:right;width:120px;height:120px;margin:0 0 8px 12px;border:1px solid var(--line);border-radius:14px;background:var(--surface);padding:6px}
.ent-map .u{fill:none;stroke:var(--line);stroke-width:7;stroke-linecap:round;stroke-linejoin:round}
.ent-map .t{fill:none;stroke:var(--ink);stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round}
.ent-map circle{fill:var(--clay)}
.ent-jump{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 0;clear:both}
.gp-time{list-style:none;padding:0;margin:8px 0 0;display:grid;gap:6px}.gp-time li{display:flex;justify-content:space-between;gap:12px;padding:8px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);font-size:15px}.gp-time b{font-weight:700}.gp-time span{font-variant-numeric:tabular-nums;color:var(--ink)}
.ent-jump a{font-size:13px;font-weight:700;border:1px solid var(--line);border-radius:999px;padding:4px 12px;text-decoration:none;color:var(--ink);background:var(--surface)}
.ent-grid{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.ent-grid a{display:block;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:var(--surface);color:var(--ink);text-decoration:none}
.ent-grid a:hover b{text-decoration:underline;text-underline-offset:3px}
.ent-grid small{display:block;font-size:12px;color:var(--muted)}
.ent-grid b{display:block;font-size:17px;line-height:1.5;margin-top:2px}
.ent-grid span{display:block;font-size:13px;color:var(--ink-2);margin-top:2px}
@media (min-width:600px){.ent-grid.two{grid-template-columns:1fr 1fr}}
.ent-pn{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:26px 0 0;font-size:14px;font-weight:700}
.ent-more{display:flex;flex-wrap:wrap;gap:8px 16px;margin:14px 0 0;font-size:14px;font-weight:700}
.ent-more a{color:var(--clay)}
.mon-nav{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 4px}
.mon-nav a,.mon-nav b{font-size:13.5px;border:1px solid var(--line);border-radius:999px;padding:3px 12px;text-decoration:none;color:var(--ink);background:var(--surface)}
.mon-nav b{background:var(--ink);color:var(--paper);border-color:var(--ink)}
"""


def _gp_base(name):
    return re.sub(r'（[^）]*）', '', name or '').strip()


def plan_gps(allarts, circuits):
    """Which races get a page: this season's calendar races with enough news. Articles go to the race at their
    circuit in the same year (nearest date)."""
    season = load('season.json', {}) or {}
    races = []
    for r in season.get('calendar') or []:
        c = r.get('circuit')
        if not c or c not in circuits or not r.get('date'):
            continue
        d = datetime.fromisoformat(r['date'] + 'T15:00:00+09:00')
        races.append({'slug': f'{c}-{d.year}', 'circuit': c, 'gp': r['gp'], 'round': r.get('round'), 'date': d,
                      'winner': r.get('winner', ''), 'cname': circuits[c].get('name', ''), 'arts': [], 'cols': [], 'hubs': []})
    for a in allarts:
        c = a.get('circuit')
        cand = [x for x in races if x['circuit'] == c and x['date'].year == when(a).year]
        if cand:
            x = min(cand, key=lambda x: abs((x['date'] - when(a)).total_seconds()))
            x['arts'].append(a)
    GPS.clear(); GP_OF.clear()
    for x in races:
        if len(x['arts']) >= GP_MIN:
            GPS[x['slug']] = x
            for a in x['arts']:
                GP_OF[a['id']] = x['slug']


def _gp_words(x, circuits):
    c = circuits.get(x['circuit'], {})
    w = [x['gp'], _gp_base(x['gp']), c.get('gp', ''), re.sub(r'(市街地コース|インターナショナル|サーキット)', '', c.get('name', '')).strip(), x['circuit']]
    return [v for v in w + GP_EXTRA.get(x['circuit'], []) if v and len(v) >= 3]


def gp_link(a):
    s = GP_OF.get(a['id'])
    return (s, GPS[s]) if s else (None, None)


def _cols_for_gp(x, circuits):
    """Columns of one race weekend: a column with a circuit field belongs to that circuit; others are matched by
    the GP / circuit names in their title, label and tags, within the weekend's dates (nearest race wins)."""
    def hit(col, y):
        if col.get('circuit'):
            return col['circuit'] == y['circuit']
        return any(w in col['txt'] for w in _gp_words(y, circuits))
    out = []
    for col in ALL_COLS:
        dt = col['dt']
        if not (x['date'] - timedelta(days=14) <= dt <= x['date'] + timedelta(days=9)) or not hit(col, x):
            continue
        near = min((y for y in GPS.values() if hit(col, y)), key=lambda y: abs((y['date'] - dt).total_seconds()))
        if near['slug'] == x['slug']:
            out.append(col)
    return out


def _hubs_for(pred):
    return [H for H in hubs_newest() if pred(H)]


def _day_list(arts, flag_of):
    rows, last = [], None
    for a in arts:
        dd = when(a).astimezone(JST)
        key = f'{dd.year}年{dd.month}月{dd.day}日（{"月火水木金土日"[dd.weekday()]}）'
        if key != last:
            if last is not None:
                rows.append('</ul>')
            rows.append(f'<h3 class="day">{key}</h3><ul class="list">')
            last = key
        rows.append(item_li(a, flag_of))
    if last is not None:
        rows.append('</ul>')
    return ''.join(rows)


def _crumbs_ld(items):
    return ld({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u} for i, (n, u) in enumerate(items)]})


def _map_svg(c):
    if not c or not c.get('path'):
        return ''
    st = c.get('start')
    return ('<svg class="ent-map" viewBox="0 0 100 100" role="img" aria-label="' + e(c.get('name', '')) + 'のコース図">'
            f'<path class="u" d="{c["path"]}"/><path class="t" d="{c["path"]}"/>'
            + (f'<circle cx="{st[0]}" cy="{st[1]}" r="2.6"/>' if st else '') + '</svg>')


READ_COUNT = {}    # person-id -> number of STORY / column / DEEP pieces naming them
READ_CENTRAL = {}  # url -> people a STORY / column / DEEP names in its title or lead
READ_TITLE = {}    # url -> people it names in its title
TERM_LINK = re.compile(r'<a class="term"[^>]*data-term="([^"]+)"')


def add_term_reads(n=5):
    """Rulebook entry pages: 「この言葉が出てくる読み物」— the STORY, DEEP GRID and column pages whose text
    links to that entry, newest first. Most search visitors land on the rulebook; this takes them on to
    the site's own reading (owner's OK, 18 Oct 2026). Replaces the <!--reads:id--> marker build_rules leaves."""
    reads, lead = [], {}
    for H in hubs_newest():
        ups = [u.get('at', '') for u in H.get('updates', [])]
        reads.append((max(ups) if ups else H.get('checked', ''), 'STORY', f'/topics/{H["slug"]}/', H['title']))
        lead[f'/topics/{H["slug"]}/'] = (H['title'], H.get('dek', ''))
    for x in ALL_COLS:
        reads.append((x['dt'].isoformat(), COL_TAG[x['kind']], x['url'], x['title']))
        J = load(('deep/' if x['kind'] == 'deep' else 'lens/') + x['url'].strip('/').split('/')[-1] + '.json') or {}
        lead[x['url']] = (x['title'], J.get('dek', ''))
    reads.sort(key=lambda r: r[0], reverse=True)
    # who a piece is ABOUT: named in its title or lead (owner, 22 Oct 2026 — a passing mention is not "登場")
    def about(text):
        out = set()
        for q in PEOPLE:
            nm = [a for a in [q['name']] + (q.get('aliases') or []) if len(a) >= 3 and not re.fullmatch(r'[A-Za-z .]+', a)]
            if any(_kw_hit(a, text) for a in nm):   # whole word: マイニ ≠ マイニング (column desk, 23 Oct 2026)
                out.add('person-' + q['id'])
        return out
    global READ_CENTRAL, READ_TITLE
    READ_TITLE = {u: about(t) for u, (t, _) in lead.items()}            # named in the title: the piece is about them
    READ_CENTRAL = {u: about(t + ' ' + d) for u, (t, d) in lead.items()}  # named in the title or the lead
    by_term, page_people = {}, {}
    pname = {'person-' + q['id']: q['name'] for q in PEOPLE}
    for dt, label, url, title in reads:
        f = os.path.join(ROOT, url.strip('/'), 'index.html')
        if not os.path.exists(f):
            continue
        with open(f, encoding='utf-8') as fh:
            ids = dict.fromkeys(TERM_LINK.findall(fh.read()))
        for tid in ids:
            by_term.setdefault(tid, []).append((label, url, title))
        page_people[url] = {t for t in ids if t.startswith('person-')}
        for tid in READ_CENTRAL.get(url, ()):  # named in the title or lead but never linked in the text: still theirs
            if (label, url, title) not in by_term.get(tid, []):
                by_term.setdefault(tid, []).append((label, url, title))
                page_people[url].add(tid)
    rdir = os.path.join(ROOT, 'deep', 'rules')
    for d in sorted(os.listdir(rdir)):
        f = os.path.join(rdir, d, 'index.html')
        if not os.path.exists(f):
            continue
        with open(f, encoding='utf-8') as fh:
            h = fh.read()
        mk = f'<!--reads:{d}-->'
        if mk not in h:
            continue
        allr = by_term.get(d, [])
        tier = lambda r: 2 if d in READ_TITLE.get(r[1], ()) else (1 if d in READ_CENTRAL.get(r[1], ()) else 0)
        got = sorted(allr, key=lambda r: -tier(r))[:n]  # stable: newest first within each tier
        box = ('<div class="rb-h">' + ('この人が出てくる読み物' if d.startswith('person-') else 'この言葉が出てくる読み物') + '</div><ul class="rb-ex rb-reads">' + ''.join(
            f'<li><a href="{e(u)}" data-track="click/rb-reads/{e(d)}"><small>{e(lb)}</small>{e(t)}</a></li>' for lb, u, t in got) + '</ul>') if got else ''
        h = h.replace(mk, box)
        pk = f'<!--peers:{d}-->'
        if pk in h:
            co = {}
            for ids in page_people.values():
                if d in ids:
                    for o in ids:
                        if o != d:
                            co[o] = co.get(o, 0) + 1
            peers = sorted([(c, o) for o, c in co.items() if c >= 2 and o in pname], key=lambda x: (-x[0], pname[x[1]]))[:6]
            h = h.replace(pk, ('<div class="rb-h">よく一緒に出てくる人物</div><div class="rb-see">' + ''.join(
                f'<a href="/deep/rules/{e(o)}/" data-track="click/person/peer/{e(o)}">{e(pname[o])}</a>' for _, o in peers) + '</div>') if peers else '')
        write(f'deep/rules/{d}/index.html', h)
    READ_COUNT.update({k: len(v) for k, v in by_term.items()})
    return by_term


SHARE_CSS = """
.sk{max-width:760px;margin:0 auto;padding:0 0 40px}
.sk h1{font-size:24px;margin:8px 0 6px}
.sk h2{font-size:18px;margin:34px 0 6px;padding-top:18px;border-top:2px solid var(--ink)}
.sk .lead,.sk .note{color:var(--ink-2);font-size:14px;line-height:1.8}
.sk-i{border-top:1px solid var(--line);padding:16px 0}
.sk-i .k{font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--muted)}
.sk-i b{display:block;font-size:16px;line-height:1.5;margin:2px 0 10px}
.sk-box{position:relative;margin:8px 0 0}
.sk-box small{display:block;font-size:12px;font-weight:700;color:var(--muted);margin-bottom:4px}
.sk-box textarea{width:100%;box-sizing:border-box;font:inherit;font-size:15px;line-height:1.7;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);resize:vertical}
.sk-box button{margin-top:6px;font:inherit;font-size:14px;font-weight:700;padding:8px 16px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.sk-box button.ok{background:var(--ink);color:var(--paper)}
.sk-w{font-size:12px;color:var(--muted);margin-left:8px}
.sk a.sk-x,.sk a.sk-x:visited{display:inline-block;margin:10px 0 4px;font-size:15px;font-weight:700;padding:10px 18px;border-radius:999px;background:var(--ink);color:var(--paper)!important;text-decoration:none}
"""

SHARE_JS = """<script>
document.querySelectorAll('.sk-box button').forEach(function(b){b.addEventListener('click',function(){
  var t=b.parentNode.querySelector('textarea');t.select();
  var done=function(){b.textContent='コピーしました';b.classList.add('ok');setTimeout(function(){b.textContent='コピー';b.classList.remove('ok')},1600)};
  if(navigator.clipboard){navigator.clipboard.writeText(t.value).then(done,function(){document.execCommand('copy');done()})}else{document.execCommand('copy');done()}
})});
</script>"""


def x_weight(t):
    """X counts most CJK characters as 2 and every link as 23."""
    w = 0
    for part in re.split(r'(https?://\S+)', t):
        if part.startswith('http'):
            w += 23
        else:
            w += sum(1 if ord(c) < 0x1100 else 2 for c in part)
    return w


def build_share_kit(days=7, req_days=4):
    """share/index.html — the owner's copy-and-paste desk (owner's OK, 21 Oct 2026). No AI, no tokens:
    for every STORY / column / DEEP of the last `days` days, a ready X post and a note line, each with the
    utm_source / utm_campaign that GoatCounter already records (same rule as LENS.md / DEEP.md);
    then the newest pages to ask Search Console to index, one URL per box. Not secret (all links are public),
    but noindex, not in the sitemap and not linked from the site."""
    now = datetime.now(JST)
    since = now - timedelta(days=days)
    items = []
    for H in HUBS.values():
        ups = [u.get('at', '') for u in H.get('updates', [])]
        try:
            dt = datetime.fromisoformat(max(ups)) if ups else datetime.fromisoformat(H.get('checked', '') + 'T12:00:00+09:00')
        except Exception:
            continue
        S = H.get('story') or {}
        items.append((dt, 'STORY', f'/topics/{H["slug"]}/', H['slug'], H['title'], H.get('dek') or S.get('hook', '')))
    for x in ALL_COLS:
        src = ('deep/' if x['kind'] == 'deep' else 'lens/') + x['url'].strip('/').split('/')[-1] + '.json'
        J = load(src) or {}
        items.append((x['dt'], COL_TAG[x['kind']], x['url'], x['url'].strip('/').split('/')[-1], x['title'], J.get('dek', '')))
    items = sorted([i for i in items if i[0] >= since], key=lambda i: i[0], reverse=True)

    def box(label, text, x=False):
        w = f'<span class="sk-w">X の文字数 {x_weight(text)}／280</span>' if x else ''
        return (f'<div class="sk-box"><small>{e(label)}</small><textarea rows="{8 if x else 3}" readonly>{e(text)}</textarea>'
                f'<button type="button">コピー</button>{w}</div>')

    blocks = []
    for dt, label, url, slug, title, dek in items:
        full = SITE + url
        xurl = f'{full}?utm_source=x&utm_campaign={slug}'
        nurl = f'{full}?utm_source=note&utm_campaign={slug}'
        head = f'【{label}】{title}'
        lead = re.sub(r'\s+', ' ', dek).strip()
        while lead and x_weight(f'{head}\n\n{lead}\n\n{xurl}') > 270:
            lead = lead[:-2].rstrip('、。 ') + '…'
        xt = f'{head}\n\n{lead}\n\n{xurl}' if lead and lead != '…' else f'{head}\n\n{xurl}'
        blocks.append(f'<div class="sk-i"><span class="k">{e(label)} · {e(jst_text(dt))}</span><b>{e(title)}</b>'
                      + box('X に投稿', xt, True)
                      + f'<a class="sk-x" href="https://x.com/intent/post?text={urllib.parse.quote(xt)}" target="_blank" rel="noopener">X の投稿画面を開く ↗</a>'
                      + box('note の本文に入れるリンク', f'続きは F1 Grid Walk で → {nurl}')
                      + '</div>')
    req = [SITE + u for dt, _, u, _, _, _ in items if dt >= now - timedelta(days=req_days)]
    for g in sorted(GPS.values(), key=lambda g: g['date']):
        if -7 <= (g['date'].date() - now.date()).days <= 10:
            req.insert(0, f'{SITE}/gp/{g["slug"]}/')
    req = list(dict.fromkeys(req))
    body = ('<div class="sk"><h1>共有キット</h1>'
            f'<p class="lead">オーナー用の作業ページです。最近 {days} 日の STORY・コラム・DEEP について、X と note に貼る文と、'
            'Search Console に出すURLを、ビルドのたびに自動で作っています。リンクには計測の印（utm）が付いているので、'
            'どの投稿から何人来たかが GoatCounter の「キャンペーン」に出ます。</p>'
            '<p class="note">サイトのどこからもリンクしておらず、検索にも出しません（中身はすべて公開中の記事のリンクです）。</p>'
            '<h2>X・note に貼る文</h2>' + (''.join(blocks) or '<p class="note">最近の記事はありません。</p>')
            + f'<h2>Search Console に出すURL</h2><p class="note">最近 {req_days} 日に出たページを、新しい順に並べています。開催前後のGPのページがあれば先頭に入ります。'
              '登録済みかどうかは、Search Console の「URL検査」で確かめてから出してください（1日10回ほどまで）。</p>'
            + ''.join(box('URL', u) for u in req) + '</div>' + SHARE_JS)
    write('share/index.html', page('共有キット｜F1グリッドウォーク', 'オーナー用の作業ページ', SITE + '/share/', body,
                                   f'<meta name="robots" content="noindex,nofollow">\n<style>{SHARE_CSS}</style>\n', og_type='website'))


RELATED_CSS = """<style>
.rel{margin:34px 0 8px;padding-top:16px;border-top:2px solid var(--ink)}
.rel .rel-k{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:12px;font-weight:700;letter-spacing:.14em;color:var(--clay);margin:0}
.rel h2{font-size:20px;margin:2px 0 10px}
.rel a.rel-i{display:block;margin:8px 0 0;padding:10px 14px;border:1px solid var(--line);border-left:3px solid var(--clay);border-radius:10px;background:var(--surface);color:var(--ink);text-decoration:none;font-size:15px;font-weight:700;line-height:1.55}
.rel a.rel-i small{display:block;font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--muted);margin-bottom:2px}
.rel a.rel-t{display:inline-block;margin:12px 0 0;font-size:14.5px;font-weight:700;color:var(--ink)}
</style>"""


def page_entities(text, teams):
    """Teams and people a page is about, read from its title and lead (no AI; names from teams.json / people.json)."""
    ents = set()
    for k, t in teams.items():
        names = [t.get('name') or k] + list(t.get('drivers') or [])
        if any(n and n in text for n in names):
            ents.add('team:' + k)
        if t.get('pu') and t['pu'] in text:
            ents.add('pu:' + t['pu'])
    for pp in PEOPLE:
        short = [a for a in [pp['name']] + (pp.get('aliases') or []) if len(a) >= 3 and not re.fullmatch(r'[A-Za-z ]+', a)]
        if any(a in text for a in short):
            ents.add('person:' + pp['id'])
    return ents


def add_related(n=3):
    """「この話の続き」at the end of every column and DEEP issue (owner's OK, 22 Oct 2026): STORYs, columns and
    DEEP issues about the same people / teams, best match first, then the team page. A shared person counts 2,
    a shared team or engine maker 1; at least 2 is needed, so a single team name alone does not make a link."""
    teams = (load('teams.json', {}) or {}).get('teams', {})
    pages = []
    for H in HUBS.values():
        S = H.get('story') or {}
        ups = [u.get('at', '') for u in H.get('updates', [])]
        pages.append(('STORY', f'/topics/{H["slug"]}/', H['title'], ' '.join([H['title'], H.get('dek', ''), S.get('hook', '')]), max(ups) if ups else ''))
    for x in ALL_COLS:
        J = load(('deep/' if x['kind'] == 'deep' else 'lens/') + x['url'].strip('/').split('/')[-1] + '.json') or {}
        pages.append((COL_TAG[x['kind']], x['url'], x['title'], ' '.join([x['title'], J.get('dek', ''), J.get('noteTags', '')]), x['dt'].isoformat()))
    ents = {u: page_entities(t, teams) for _, u, _, t, _ in pages}
    def w(e_):
        return 2 if e_.startswith('person:') else 1
    for label, url, title, text, dt in pages:
        if url.startswith('/topics/'):
            continue
        f = os.path.join(ROOT, url.strip('/'), 'index.html')
        if not os.path.exists(f):
            continue
        with open(f, encoding='utf-8') as fh:
            h = fh.read()
        mk = f'<!--related:{url}-->'
        if mk not in h:
            continue
        mine = ents[url]
        scored = []
        for lb2, u2, t2, _, d2 in pages:
            if u2 == url:
                continue
            sc = sum(w(e_) for e_ in mine & ents[u2])
            if sc >= 2:
                scored.append((sc, d2, lb2, u2, t2))
        scored.sort(key=lambda r: (r[0], r[1]), reverse=True)
        tm = [e_[5:] for e_ in sorted(mine) if e_.startswith('team:')]
        tm = [k for k in tm if os.path.exists(os.path.join(ROOT, 'teams', k, 'index.html'))]
        box = ''
        if scored or tm:
            box = ('<section class="rel"><p class="rel-k">MORE ON THIS</p><h2>この話の続き</h2>'
                   + ''.join(f'<a class="rel-i" href="{e(u2)}" data-track="click/rel{e(url)}"><small>{e(lb2)}</small>{e(t2)} →</a>' for _, _, lb2, u2, t2 in scored[:n])
                   + ''.join(f'<a class="rel-t" href="/teams/{e(k)}/" data-track="click/rel-team/{e(k)}">{e(teams[k].get("name", k))}の記事を、まとめて読む →</a><br>' for k in tm[:2])
                   + '</section>' + RELATED_CSS)
        write(url.strip('/') + '/index.html', h.replace(mk, box))


def driver_person(short):
    """people.json entry for a driver's short name in teams.json (drivers first)."""
    c = [p for p in PEOPLE if short == p['name'] or short in (p.get('aliases') or []) or p['name'].endswith('・' + short)]
    c.sort(key=lambda p: p.get('role') != 'ドライバー')
    return c[0] if c else None


MEMBER_GROUPS = [  # (label, pattern) — first match wins (owner's OK, 22 Oct 2026)
    ('reserve', 'リザーブ', r'リザーブ|テストドライバー|テスト兼|サードドライバー|シミュレーター|開発ドライバー'),
    ('mgmt', '代表・経営', r'チーム代表|副チーム代表|チーム副代表|CEO|会長|オーナー|株主|創業者|チェアマン'),
    ('race', 'レース現場', r'レースエンジニア|スポーティングディレクター|トラックサイド|ヘッド・オブ・レーシング|パフォーマンスエンジニア|レーシングディレクター|チーフトラックサイド'),
    ('tech', '技術', r'テクニカル|技術|CTO|チーフデザイナー|パワートレイン|パワーユニット'),
    ('mgmt', '代表・経営', r'.'),
]


def engineers_of(d):
    """Engineers whose role names this driver (「レースエンジニア（ノリス担当）」, 「…アントネッリのレースエンジニア」)."""
    short = [a for a in [d['name'].split('・')[-1]] + (d.get('aliases') or []) if len(a) >= 3 and not re.fullmatch(r'[A-Za-z .]+', a)]
    return [q for q in PEOPLE if q is not d and 'エンジニア' in q.get('role', '') and q.get('role') != 'ドライバー'
            and any(a in q['role'] for a in short)]


def team_members(k):
    """Everyone in people.json who works for team k, by group, most-read first; principal first."""
    t = TEAMS_ALL.get(k) or {}
    name = t.get('name') or ''
    ds = {x['id'] for x in team_people(k)[0]}
    out = {}
    for p in PEOPLE:
        if not name or not p.get('org', '').startswith(name) or p['id'] in ds or p.get('role') == 'ドライバー':
            continue
        g = next((gk for gk, _, pat in MEMBER_GROUPS if re.search(pat, p.get('role', ''))), 'mgmt')
        out.setdefault(g, []).append(p)
    for g, ps in out.items():
        ps.sort(key=lambda p: (not ('チーム代表' in p['role'] and not p['role'].startswith('副')), -READ_COUNT.get('person-' + p['id'], 0), p['name']))
    return out


def team_people(k):
    """(drivers, principal) for a team key: people.json entries, principal = チーム代表 of that team."""
    t = TEAMS_ALL.get(k) or {}
    ds = [x for x in (driver_person(d) for d in t.get('drivers', [])) if x]
    name = t.get('name') or ''
    pr = [p for p in PEOPLE if name and p.get('org', '').startswith(name) and 'チーム代表' in p.get('role', '') and not p.get('role', '').startswith('副')]
    return ds, (pr[0] if pr else None)


DRV_CSS = """
.drv h1{font-size:26px;margin:6px 0 4px}
.drv .lead{color:var(--ink-2);font-size:14.5px;line-height:1.8;margin:0 0 18px}
.drv h2{font-size:18px;margin:30px 0 8px;padding-top:14px;border-top:2px solid var(--ink)}
.drv-hot a{display:block;margin:8px 0 0;padding:10px 14px;border:1px solid var(--line);border-left:3px solid var(--clay);border-radius:10px;background:var(--surface);color:var(--ink);text-decoration:none}
.drv-hot b{display:block;font-size:16px}
.drv-hot span{display:block;font-size:13px;color:var(--ink-2);line-height:1.6;margin-top:2px}
.drv-tm{border-top:1px solid var(--line);padding:12px 0 10px}
.drv-tm .tn{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:800;color:var(--ink);text-decoration:none;margin-bottom:8px;padding:4px 0}
.drv-tm .tn i{display:inline-block;width:18px;height:6px;border-radius:3px}
.drv-tm .ds{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.drv-tm .ds a{display:block;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);text-decoration:none}
.drv-tm .ds b{display:block;font-size:15.5px;line-height:1.4}
.drv-tm .ds small{display:block;font-size:12px;color:var(--muted);margin-top:2px}
"""


def build_drivers(by_term):
    """drivers/index.html — the bottom bar's ドライバー tab (owner's OK, 22 Oct 2026): this season's grid by team,
    each name leading to the person's page (reading first, then news). Built from teams.json + people.json only."""
    T = load('teams.json', {}) or {}
    teams, order = T.get('teams', {}), T.get('order', [])
    find = driver_person
    grid, drivers = [], []
    for k in order:
        t = teams.get(k) or {}
        cards = []
        for d in t.get('drivers', []):
            p = find(d)
            if not p:
                continue
            reads = [r for r in by_term.get('person-' + p['id'], []) if 'person-' + p['id'] in READ_CENTRAL.get(r[1], ())]
            nn = len(person_news(p, ALLARTS))
            drivers.append((p, reads))
            sub = f'読み物 {len(reads)}本' if reads else ('ニュースあり' if nn else '')
            cards.append(f'<a href="{rb_url("person-" + p["id"])}" data-track="click/drivers/{e(p["id"])}"><b>{e(p["name"])}</b>' + (f'<small>{e(sub)}</small>' if sub else '') + '</a>')
        if not cards:
            continue
        tn = f'<i style="background:{e(t.get("c1", "#888"))}"></i>{e(t.get("name", k))}'
        head = (f'<a class="tn" href="/teams/{e(k)}/" data-track="click/drivers/team/{e(k)}">{tn} →</a>' if os.path.exists(os.path.join(ROOT, 'teams', k, 'index.html'))
                else f'<span class="tn">{tn}</span>')
        grid.append(f'<div class="drv-tm">{head}<div class="ds">{"".join(cards)}</div></div>')
    # drivers in the newest reading, newest first (one per driver)
    hot, rank = [], []
    for p, reads in drivers:
        top = [r for r in reads if 'person-' + p['id'] in READ_TITLE.get(r[1], ())]
        if top:
            rank.append((top[0], p))
    order_urls = {}
    for H in hubs_newest():
        ups = [u.get('at', '') for u in H.get('updates', [])]
        order_urls[f'/topics/{H["slug"]}/'] = max(ups) if ups else ''
    for x in ALL_COLS:
        order_urls[x['url']] = x['dt'].isoformat()
    rank.sort(key=lambda r: order_urls.get(r[0][1], ''), reverse=True)
    used_u = set()
    for (lb, u, ttl), p in rank:
        if u in used_u or len(hot) >= 3:
            continue
        used_u.add(u)
        hot.append(f'<a href="{rb_url("person-" + p["id"])}" data-track="click/drivers/hot/{e(p["id"])}"><b>{e(p["name"])}</b><span>{e(lb)}「{e(ttl)}」</span></a>')
    body = ('<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › ドライバー</nav><div class="drv">'
            f'<h1>ドライバー</h1><p class="lead">{e(T.get("season", "2026"))}年のF1を走る{len(drivers)}人を、チームごとに並べています。名前を押すと、その人の STORY・コラム・ニュースをまとめて読めます。</p>'
            + (f'<h2>最近の読み物の主役</h2><div class="drv-hot">{"".join(hot)}</div>' if hot else '')
            + '<h2>チームとドライバー</h2>' + ''.join(grid) + '</div>')
    url = SITE + '/drivers/'
    write('drivers/index.html', page('F1ドライバー一覧 2026｜チームごとの22人と記事｜F1グリッドウォーク',
                                     f'{T.get("season", "2026")}年のF1ドライバー{len(drivers)}人をチームごとに。名前から、その人のSTORY・コラム・ニュースへ。', url, body,
                                     f'<style>{DRV_CSS}</style>\n', og_type='website'))
    return [(url, datetime.now(JST).isoformat(timespec='seconds'), 'daily', '0.7')]


def top_rail_slot():
    """Phone top page: the newest STORY and the newest WORLD GRID, DEEP GRID and OFF GRID as big cards
    you swipe sideways (owner chose design B, 25 Oct 2026). Fills <!--pre:rail--> in index.html; on phones
    it replaces the STORY box and the two column rows, on wider screens it is hidden."""
    cards = []
    H = latest_hub()
    if H:
        S = H.get('story') or {}
        cards.append(('story', f'/topics/{H["slug"]}/', 'STORY' + (f' · {H["gp"]}' if H.get('gp', '').endswith('GP') else ''),
                      H['title'], S.get('hook') or H.get('dek', ''), 'STORY を読む'))
    for k in ('world', 'deep', 'off'):
        x = next((c for c in ALL_COLS if c['kind'] == k), None)
        if x:
            cards.append((k, x['url'], COL_TAG[k], x['title'], '', '読む'))
    blk = ''
    if cards:
        blk = ('<style>.top-rail{display:none}'
               '@media (max-width:520px){.top-rail{display:block;width:100vw;margin:0 0 6px calc(50% - 50vw);order:-5}'
               '.hero .hero-in,.hero .duo{display:none !important}'
               '.rail{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding:4px 16px 6px;scrollbar-width:none;-webkit-overflow-scrolling:touch}'
               '.rail::-webkit-scrollbar{display:none}'
               '.rcard{flex:0 0 84%;scroll-snap-align:start;scroll-margin-left:16px;border-radius:18px;padding:16px 16px 18px;min-height:236px;display:flex;flex-direction:column;justify-content:space-between;color:#fff;text-decoration:none}'
               '.rc-story{background:#1F2420}.rc-world{background:#B8673F}.rc-deep{background:#8E2F3B}.rc-off{background:#2F6B66}'
               '.rcard small{align-self:flex-start;font-size:10.5px;font-weight:800;letter-spacing:.08em;padding:3px 8px;border-radius:5px;background:rgba(255,255,255,.18)}'
               '.rc-story small{background:var(--hl,#FFEE9A);color:#1F2420}'
               ".rcard b{display:block;font-family:'Noto Serif JP','Hiragino Mincho ProN','Yu Mincho',serif;font-size:23px;line-height:1.4;font-weight:900;margin:12px 0 8px}"
               '.rcard p{margin:0;font-size:13.5px;line-height:1.7;opacity:.88;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}'
               '.rcard span.go{font-weight:800;font-size:13px;margin-top:12px}'
               '.rdots{display:flex;gap:6px;justify-content:center;padding:6px 0 4px}.rdots i{width:6px;height:6px;border-radius:3px;background:var(--line);transition:width .2s}.rdots i.on{background:var(--ink);width:16px}}'
               '</style><div class="top-rail" aria-label="今日の読みもの"><div class="rail" id="rail">'
               + ''.join(f'<a class="rcard rc-{k}" href="{e(u)}" data-track="click/top/rail/{k}"><div><small>{e(tag)}</small><b>{e(t)}</b>'
                         + (f'<p>{e(d)}</p>' if d else '') + f'</div><span class="go">{e(go)} →</span></a>' for k, u, tag, t, d, go in cards)
               + '</div><div class="rdots" aria-hidden="true">' + ''.join('<i></i>' for _ in cards) + '</div></div>'
               '<script>(function(){var r=document.getElementById("rail");if(!r)return;var d=r.parentNode.querySelectorAll(".rdots i");'
               'function u(){var w=r.firstElementChild?r.firstElementChild.offsetWidth+12:1,i=Math.round(r.scrollLeft/w);'
               'for(var j=0;j<d.length;j++)d[j].className=j===i?"on":"";}r.addEventListener("scroll",u,{passive:true});u();})();</script>')
    ip = os.path.join(ROOT, 'index.html'); src = open(ip, encoding='utf-8').read()
    out = re.sub(r'(<!--pre:rail-->).*?(<!--/pre:rail-->)', lambda m: m.group(1) + blk + m.group(2), src, count=1, flags=re.S)
    if out != src:
        with open(ip, 'w', encoding='utf-8') as fh:
            fh.write(out)


def top_latest_slot(allarts):
    """Top page first screen: the three newest headlines under the columns, so a visitor sees there is news
    without scrolling (owner asked to see it, 25 Oct 2026). Fills <!--pre:latest--> in index.html."""
    new = [a for a in allarts if a.get('kind') in ('news', 'tech', 'rumor')][:3]
    blk = ''
    if new:
        KL = {'news': '報道', 'tech': '技術', 'rumor': '噂'}
        blk = ('<style>.top-latest{order:2;margin:16px 2px 0}.top-latest h2{font-size:12px;font-weight:800;letter-spacing:.06em;color:var(--muted);margin:0 0 4px}'
               '.top-latest ul{list-style:none;margin:0;padding:0}.top-latest li{border-top:1px solid var(--line)}.top-latest li:first-child{border-top:0}'
               '.top-latest a{display:block;padding:9px 0;color:var(--ink);text-decoration:none;font-weight:700;font-size:15px;line-height:1.5}'
               '.top-latest a small{display:inline-block;font-size:11px;font-weight:800;color:var(--muted);margin-right:8px;border:1px solid var(--line);border-radius:4px;padding:0 5px}'
               '.top-latest .more{display:inline-block;margin-top:4px;font-size:13px;font-weight:700;color:var(--clay);text-decoration:none}</style>'
               '<div class="top-latest"><h2>最新のニュース</h2><ul>'
               + ''.join(f'<li><a href="/news/{e(a["id"])}/" data-track="click/top/latest/{i + 1}"><small>{KL[a["kind"]]}</small>{e(a["title"])}</a></li>' for i, a in enumerate(new))
               + '</ul><a class="more" href="#news" data-track="click/top/latest/more">ニュースをもっと見る ↓</a></div>')
    ip = os.path.join(ROOT, 'index.html'); src = open(ip, encoding='utf-8').read()
    out = re.sub(r'(<!--pre:latest-->).*?(<!--/pre:latest-->)', lambda m: m.group(1) + blk + m.group(2), src, count=1, flags=re.S)
    if out != src:
        with open(ip, 'w', encoding='utf-8') as fh:
            fh.write(out)


def top_people_slot():
    """Top page: one quiet line under the STORY / column boxes — the people the newest pieces are about,
    and the way to all drivers (owner's OK, 23 Oct 2026). Fills <!--pre:people--> in index.html."""
    pages = []
    for H in hubs_newest():
        ups = [u.get('at', '') for u in H.get('updates', [])]
        pages.append((max(ups) if ups else '', f'/topics/{H["slug"]}/'))
    for x in ALL_COLS:
        pages.append((x['dt'].isoformat(), x['url']))
    pages.sort(reverse=True)
    pname = {'person-' + q['id']: q for q in PEOPLE}
    picks = []
    for _, u in pages:
        for pid in sorted(READ_TITLE.get(u, ())):
            if pid in pname and pid not in picks:
                picks.append(pid)
        if len(picks) >= 4:
            break
    picks = picks[:4]
    blk = ''
    if picks:
        blk = ('<style>.ppl-strip{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px;margin:14px 2px 0;font-size:14px;line-height:1.9}'
               '.ppl-strip span{font-size:12px;font-weight:800;letter-spacing:.06em;color:var(--muted)}'
               '.ppl-strip a{font-weight:700;color:var(--ink);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}'
               '.ppl-strip a.all{color:var(--clay);text-decoration:none}</style>'
               '<p class="ppl-strip"><span>いま話題の人</span>'
               + ''.join(f'<a href="/deep/rules/{e(pid)}/" data-track="click/top/people/{e(pid)}">{e(pname[pid]["name"].split("・")[-1])}</a>' for pid in picks)
               + '<a class="all" href="/drivers/" data-track="click/top/people/all">ドライバー一覧 →</a></p>')
    ip = os.path.join(ROOT, 'index.html'); src = open(ip, encoding='utf-8').read()
    out = re.sub(r'(<!--pre:people-->).*?(<!--/pre:people-->)', lambda m: m.group(1) + blk + m.group(2), src, count=1, flags=re.S)
    if out != src:
        open(ip, 'w', encoding='utf-8').write(out)


def build_gp_pages(flag_of, circuits):
    if not GPS:
        return []
    sm = []
    order = sorted(GPS.values(), key=lambda x: x['date'])
    for i, x in enumerate(order):
        x['cols'] = _cols_for_gp(x, circuits)
        base = _gp_base(x['gp'])
        x['hubs'] = _hubs_for(lambda H: H.get('gp') and (H['gp'] in (x['gp'], base) or _gp_base(H['gp']) == base))
    for i, x in enumerate(order):
        slug, url = x['slug'], f'{SITE}/gp/{x["slug"]}/'
        y = x['date'].year
        title = f'{y} {x["gp"]}'
        facts = []
        if x.get('round'):
            facts.append(f'第{x["round"]}戦')
        facts.append(f'決勝 {x["date"].month}月{x["date"].day}日')
        facts.append(x['cname'])
        if x.get('winner'):
            facts.append(f'優勝 {x["winner"]}')
        jump = []
        if x['hubs']:
            jump.append('<a href="#gp-story">STORY</a>')
        if x['cols']:
            jump.append(f'<a href="#gp-cols">コラム（{len(x["cols"])}本）</a>')
        jump.append(f'<a href="#gp-news">ニュース（{len(x["arts"])}本）</a>')
        b = [f'<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › <a href="/gp/">GPごとに読む</a> › {e(x["gp"])}</nav>',
             _map_svg(circuits.get(x['circuit'])),
             f'<p class="ent-k">GRAND PRIX {y}</p><h1>{e(title)}</h1>',
             '<p class="ent-facts">' + ''.join(f'<span>{e(f)}</span>' for f in facts) + '</p>',
             f'<p class="lead">{e(x["gp"])}の週末を、F1 Grid Walk で読めるものすべてで振り返るページです。世界のニュースの要約、コラム、STORY を集めています。</p>',
             '<div class="ent-jump">' + ''.join(jump) + '</div>']
        wk = (load('season.json') or {}).get('weekend') or {}
        if wk.get('sessions') and wk.get('round') == x.get('round') and _gp_base(wk.get('gp', '')) == _gp_base(x['gp']):
            # this weekend's timetable in Japan time (owner's OK, 24 Oct 2026: GP pages as the weekend's entrance)
            def jst(t):
                d = datetime.fromisoformat(t.replace('Z', '+00:00')).astimezone(JST)
                return f'{d.month}/{d.day}（{"月火水木金土日"[d.weekday()]}）{d.hour}:{d.minute:02d}'
            b.append('<section id="gp-time"><h2>日程（日本時間）</h2><ul class="gp-time">' + ''.join(
                f'<li><b>{e(ss["name"])}</b><span>{e(jst(ss["start"]))}</span></li>' for ss in wk['sessions']) + '</ul></section>')
        if x['hubs']:
            b.append('<section id="gp-story"><h2>STORY</h2><ul class="yk-list">' + ''.join(hub_li(H, f'click/gp/{slug}/story') for H in x['hubs']) + '</ul></section>')
        if x['cols']:
            b.append('<section id="gp-cols"><h2>コラム</h2><ul class="col-list">' + ''.join(col_li(c, f'click/gp/{slug}/col') for c in x['cols']) + '</ul></section>')
        b.append(f'<section id="gp-news"><h2>ニュース（{len(x["arts"])}本）</h2><p class="lead">新しい順。見出しを押すと、日本語の要約と原文へのリンクがあります。</p>'
                 + _day_list(x['arts'], flag_of) + '</section>')
        pn = []
        if i > 0:
            pv = order[i - 1]
            pn.append(f'<a href="/gp/{pv["slug"]}/" data-track="click/gp/{slug}/prev">← {e(pv["gp"])}</a>')
        else:
            pn.append('<span></span>')
        if i + 1 < len(order):
            nx = order[i + 1]
            pn.append(f'<a href="/gp/{nx["slug"]}/" data-track="click/gp/{slug}/next">{e(nx["gp"])} →</a>')
        b.append('<div class="ent-pn">' + ''.join(pn) + '</div>')
        b.append('<p class="ent-more"><a href="/gp/">ほかのGPを見る</a><a href="/teams/">チームごとに読む</a><a href="/news/">ニュース一覧</a></p>')
        head = (f'<style>{ENT_CSS}{YK_CSS}{ALLCOL_CSS}</style>\n'
                + _crumbs_ld([('F1 Grid Walk', SITE + '/'), ('GPごとに読む', SITE + '/gp/'), (x['gp'], url)]))
        desc = f'{title}（第{x["round"]}戦）のニュース{len(x["arts"])}本の日本語要約と、コラム・STORY をまとめて。' if x.get('round') else f'{title}のニュースとコラムをまとめて。'
        write(f'gp/{slug}/index.html', page(f'F1 {title}｜' + ('結果・' if x.get('winner') else '') + '日程・ニュースまとめ｜F1グリッドウォーク', desc, url, '\n'.join(b), head, og_type='website'))
        last = max([when(a) for a in x['arts']] + [c['dt'] for c in x['cols']])
        sm.append((url, last.isoformat(timespec='seconds'), None, '0.7'))
    items = ''.join(
        f'<li><a href="/gp/{x["slug"]}/" data-track="click/gp-index/{x["slug"]}"><small>{x["date"].year} · 第{x["round"]}戦 · {x["date"].month}/{x["date"].day}</small>'
        f'<b>{e(x["gp"])}</b><span>ニュース {len(x["arts"])}本' + (f' · コラム {len(x["cols"])}本' if x['cols'] else '') + (f' · STORY {len(x["hubs"])}本' if x['hubs'] else '')
        + (f' · 優勝 {e(x["winner"])}' if x.get('winner') else '') + '</span></a></li>' for x in reversed(order))
    body = ('<nav class="crumbs"><a href="/">トップ</a> › GPごとに読む</nav><p class="ent-k">GRAND PRIX</p><h1>GPごとに読む</h1>'
            '<p class="lead">レースの週末ごとに、ニュース・コラム・STORY をまとめています。新しいレースから順に。</p>'
            f'<ul class="ent-grid">{items}</ul><p class="ent-more"><a href="/teams/">チームごとに読む</a><a href="/news/">ニュース一覧</a></p>')
    write('gp/index.html', page('GPごとのF1ニュースまとめ｜F1グリッドウォーク', 'F1の各グランプリの週末を、世界のニュースの日本語要約とコラムでまとめて読めます。',
                                SITE + '/gp/', body, f'<style>{ENT_CSS}</style>\n', og_type='website'))
    sm.append((SITE + '/gp/', max(u[1] for u in sm), 'daily', '0.7'))
    return sm


def build_team_pages(allarts, flag_of, teams):
    sm, cards = [], []
    for k, t in teams.items():
        arts = [a for a in allarts if k in (a.get('teams') or [])]
        if len(arts) < GP_MIN:
            continue
        name, en = t.get('name') or k, t.get('en') or ''
        cols = [c for c in ALL_COLS if k in (c.get('teams') or []) or ('#' + name) in c.get('txt', '') or name in c['title']]
        def team_hub(H):
            ids = [o.get('id') for o in H.get('outlets', [])]
            hit = sum(1 for i in ids if i in ARCH_IDS and k in (ARCH_IDS[i].get('teams') or []))
            return name in H.get('title', '') or (ids and hit * 2 >= len(ids))
        hubs = _hubs_for(team_hub)
        url = f'{SITE}/teams/{k}/'
        jump = (['<a href="#tm-story">STORY</a>'] if hubs else []) + ([f'<a href="#tm-cols">コラム（{len(cols)}本）</a>'] if cols else []) + [f'<a href="#tm-news">ニュース（{len(arts)}本）</a>']
        b = [f'<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › <a href="/teams/">チームごとに読む</a> › {e(name)}</nav>',
             f'<p class="ent-k">{e(en.upper())}</p><h1>{e(name)}のニュース・コラム</h1>',
             f'<p class="lead">{e(name)}に関する世界のF1ニュースの日本語要約と、コラム・STORY を新しい順に集めています。</p>',
             '<div class="ent-jump">' + ''.join(jump) + '</div>']
        ds, pr = team_people(k)
        mem = team_members(k)
        if ds or mem:  # team -> its people (owner's OK, 22 Oct 2026)
            def short_role(r):
                r = re.sub(r'（[^）]*）|\([^)]*\)', '', r).split('。')[0].strip()
                return r if len(r) <= 22 else r[:21] + '…'
            rows = (('<p><span>ドライバー</span>' + ''.join(f'<a href="/deep/rules/person-{e(x["id"])}/" data-track="click/team/{k}/driver"><b>{e(x["name"])} →</b></a>' for x in ds) + '</p>') if ds else '')
            for gk, gl in [('mgmt', '代表・経営'), ('tech', '技術'), ('race', 'レース現場'), ('reserve', 'リザーブ')]:
                if not mem.get(gk):
                    continue
                rows += (f'<p><span>{e(gl)}</span>' + ''.join(f'<a href="/deep/rules/person-{e(x["id"])}/" data-track="click/team/{k}/{gk}"><b>{e(x["name"])} →</b><small>{e(short_role(x["role"]))}</small></a>' for x in mem[gk][:4]) + '</p>')
            b.append(f'<div class="tm-ppl"><p class="tm-ppl-h">主なメンバー</p>{rows}</div>')
        if hubs:
            b.append('<section id="tm-story"><h2>STORY</h2><ul class="yk-list">' + ''.join(hub_li(H, f'click/team/{k}/story') for H in hubs) + '</ul></section>')
        if cols:
            b.append('<section id="tm-cols"><h2>コラム</h2><ul class="col-list">' + ''.join(col_li(c, f'click/team/{k}/col') for c in cols[:20]) + '</ul></section>')
        b.append(f'<section id="tm-news"><h2>ニュース（{len(arts)}本）</h2>' + _day_list(arts, flag_of) + '</section>')
        b.append('<p class="ent-more"><a href="/teams/">ほかのチームを見る</a><a href="/gp/">GPごとに読む</a><a href="/news/">ニュース一覧</a></p>')
        head = f'<style>{ENT_CSS}{YK_CSS}{ALLCOL_CSS}</style>\n' + _crumbs_ld([('F1 Grid Walk', SITE + '/'), ('チームごとに読む', SITE + '/teams/'), (name, url)])
        write(f'teams/{k}/index.html', page(f'{name}F1 {(load("season.json") or {}).get("season", 2026)}｜ドライバー・代表・ニュース（{en}）｜F1グリッドウォーク',
                                            f'{name}（{en}）に関する世界のF1ニュース{len(arts)}本の日本語要約と、コラム・STORY をまとめて。', url, '\n'.join(b), head, og_type='website'))
        sm.append((url, when(arts[0]).isoformat(timespec='seconds'), None, '0.6'))
        cards.append((len(arts), k, name, en, len(cols), arts[0]))
    if not cards:
        return []
    cards.sort(reverse=True)
    items = ''.join(f'<li><a href="/teams/{k}/" data-track="click/team-index/{k}"><small>{e(en)}</small><b>{e(name)}</b>'
                    + (f'<em>{e(" ／ ".join(x["name"].split("・")[-1] for x in team_people(k)[0]))}</em>' if team_people(k)[0] else '')
                    + f'<span>ニュース {n}本' + (f' · コラム {nc}本' if nc else '') + f'<br>最新：{e(la["title"])}</span></a></li>' for n, k, name, en, nc, la in cards)
    body = ('<nav class="crumbs"><a href="/">トップ</a> › チームごとに読む</nav><p class="ent-k">TEAMS</p><h1>チームごとに読む</h1>'
            '<p class="lead">好きなチームのニュースとコラムを、まとめて読めます。記事の多いチームから順に。</p>'
            f'<ul class="ent-grid two">{items}</ul><p class="ent-more"><a href="/gp/">GPごとに読む</a><a href="/news/">ニュース一覧</a></p>')
    write('teams/index.html', page('チームごとのF1ニュース｜F1グリッドウォーク', 'F1の11チームそれぞれのニュースの日本語要約とコラムを、チームごとにまとめて読めます。',
                                   SITE + '/teams/', body, f'<style>{ENT_CSS}</style>\n', og_type='website'))
    sm.append((SITE + '/teams/', max(u[1] for u in sm), 'daily', '0.7'))
    return sm


ARCH_IDS = {}
ALLARTS = []
NEWS_TOP = 100   # /news/ shows the newest articles; every month has its own page


def build_news_lists(allarts, flag_of):
    months = {}
    for a in allarts:
        d = when(a).astimezone(JST)
        months.setdefault((d.year, d.month), []).append(a)
    keys = sorted(months, reverse=True)
    def nav(cur=None):
        return '<nav class="mon-nav" aria-label="月ごとの一覧">' + ''.join(
            (f'<b>{y}年{m}月（{len(months[(y, m)])}本）</b>' if (y, m) == cur else
             f'<a href="/news/{y}-{m:02d}/" data-track="click/news/month/{y}-{m:02d}">{y}年{m}月（{len(months[(y, m)])}本）</a>') for y, m in keys) + '</nav>'
    ways = ('<p class="ent-more"><a href="/gp/" data-track="click/news/gp">GPごとに読む</a>'
            '<a href="/teams/" data-track="click/news/teams">チームごとに読む</a></p>')
    sm = []
    for (y, m) in keys:
        arts = months[(y, m)]
        url = f'{SITE}/news/{y}-{m:02d}/'
        body = (f'<nav class="crumbs"><a href="/">トップ</a> › <a href="/news/">ニュース一覧</a> › {y}年{m}月</nav>'
                f'<h1>{y}年{m}月のF1ニュース</h1><p class="lead">この月に紹介した世界のF1ニュース {len(arts)} 本。新しい順。</p>'
                + nav((y, m)) + ways + _day_list(arts, flag_of))
        write(f'news/{y}-{m:02d}/index.html', page(f'{y}年{m}月のF1ニュース一覧｜F1グリッドウォーク',
                                                  f'{y}年{m}月に紹介した世界のF1ニュース{len(arts)}本。各国の記事の見出しを日本語にして、要約と原文へのリンクを付けています。',
                                                  url, body, f'<style>{ENT_CSS}</style>\n', og_type='website'))
        sm.append((url, when(arts[0]).isoformat(timespec='seconds'), None, '0.5'))
    top = allarts[:NEWS_TOP]
    lst = ('<nav class="crumbs"><a href="/">トップ</a> › ニュース一覧</nav><h1>ニュース一覧</h1>'
           f'<p class="lead">これまでに紹介した世界のF1ニュースは {len(allarts)} 本。各国の記事の見出しを日本語にして、短い要約と原文へのリンクを付けています。'
           f'ここには新しい {len(top)} 本を並べています。それより前の記事は、月ごとの一覧からどうぞ。</p>'
           + nav() + ways + '<h2 style="font-size:18px;margin:26px 0 0">新しい記事</h2>' + _day_list(top, flag_of)
           + '<section><h2>月ごとの一覧</h2>' + nav() + '</section>')
    write('news/index.html', page('ニュース一覧｜F1 Grid Walk（F1グリッドウォーク）', '世界のF1ニュースを日本語の見出しと要約で。これまでに紹介した記事の一覧です。',
                                  SITE + '/news/', lst, f'<style>{ENT_CSS}</style>\n', og_type='website'))
    return sm


PERSON_STOP = {'ジョージ', 'マックス', 'ニコ', 'キミ', 'キー', 'Key', 'ブラウン', 'Brown', 'アレックス', 'ルイス', 'シャルル', 'ランド', 'オスカー',
               'カルロス', 'フェルナンド', 'ランス', 'ピエール', 'エステバン', 'オリバー', 'リアム', 'アイザック', 'ガブリエル', 'アンドレア', 'トト', 'セラ', 'ボノ'}


def person_news(p, allarts, n=8):
    """Newest news that names this person (full name or a surname alias no one else shares)."""
    if not hasattr(person_news, 'shared'):
        cnt = {}
        for q in PEOPLE:
            for nm in set([q['name'], q.get('en', '')] + q.get('aliases', [])):
                cnt[nm] = cnt.get(nm, 0) + 1
        person_news.shared = {k for k, v in cnt.items() if v > 1}
    names = [nm for nm in _kw_names([p['name'], p.get('en', '')] + p.get('aliases', []))
             if nm not in PERSON_STOP and nm not in person_news.shared and (len(nm) >= 3 or re.search(r'[一-龯]', nm))]
    out = []
    for a in allarts:
        text = a['title'] + ' ' + a.get('summary', '')
        if any(_kw_hit(nm, text) for nm in names):
            out.append(a)
            if len(out) >= n:
                break
    return out


def main():
    global FLAGS, LOGO, BASE_CSS_V
    FLAGS, flag_map, LOGO = shared_css()
    BASE_CSS_V = hashlib.md5((CSS + FLAGS).encode('utf-8')).hexdigest()[:8]
    write('assets/base.css', CSS + FLAGS)  # shared styles in one cached file instead of inside every page
    data = load('articles.json', {})
    teams = (load('teams.json', {}) or {}).get('teams', {})
    circuits = (load('circuits.json', {}) or {}).get('circuits', {})
    arch = load('news/archive.json', {'articles': {}, 'topics': {}})
    load_rules()
    load_deeps()
    load_hubs()

    for a in data.get('articles', []):
        if not ID_OK.match(a.get('id', '')) or not a.get('url', '').startswith('http'):
            continue
        arch['articles'][a['id']] = {k: a[k] for k in KEEP if k in a}
    for slug, t in (data.get('topics') or {}).items():
        arch['topics'][slug] = {'title': t.get('title', ''), 'summary': t.get('summary', '')}

    allarts = sorted(arch['articles'].values(), key=when, reverse=True)
    region_of = {}
    for a in allarts:
        region_of.setdefault(a['source'], a.get('region'))
    flag_of = lambda a: flag_map.get(region_of.get(a['source']) or '', 'xx')
    ARCH_IDS.update({a['id']: a for a in allarts})
    ALLARTS[:] = allarts
    plan_gps(allarts, circuits)
    team_pages = {k for k in teams if sum(1 for a in allarts if k in (a.get('teams') or [])) >= GP_MIN}

    by_topic = {}
    for a in allarts:
        if a.get('topic'):
            by_topic.setdefault(a['topic'], []).append(a)

    changed = 0
    for i, a in enumerate(allarts):
        k = kind_of(a)
        url = f'{SITE}/news/{a["id"]}/'
        d = when(a)
        lang = LANG.get(a.get('lang'), (a.get('lang') or '').upper())
        desc = re.sub(r'\s+', ' ', a.get('summary', ''))
        desc = desc if len(desc) <= 120 else desc[:118] + '…'
        body = [f'<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › <a href="/news/">ニュース一覧</a> › {KIND[k]}</nav>',
                '<article>',
                f'<div class="meta"><span class="kind {k}" title="{e(KIND_TIP[k])}">{KIND[k]}</span>'
                f'<span class="srcbadge" data-c="{flag_of(a)}">{e(a["source"])}</span>'
                f'<span>{e(a.get("region", ""))} · {e(lang)}</span>'
                + (f'<span>掲載：{e(a["source"])}　記事提供：{e(a["provider"])}</span>' if a.get('provider') else '')
                + 
                f'<time datetime="{e(a["published"])}">{e(jst_text(d))}</time></div>',
                f'<h1>{e(a["title"])}</h1>']
        if a.get('orig') and a['orig'] != a['title']:
            body.append(f'<p class="orig">原題：{e(a["orig"])}</p>')
        if k in ('rumor', 'fan'):
            body.append('<p class="warn">' + ('報道で出たうわさで、公式には確認されていない話です。' if k == 'rumor'
                        else 'ファン掲示板の話題をまとめた投稿です。未確認の話を含みます。') + '</p>')
        nused = set()
        body.append(f'<p class="summary">{link_terms(e(a.get("summary", "")), nused)}</p>')
        body.append(f'<a class="cta" href="{e(a["url"])}" target="_blank" rel="noopener" data-track="click/{e(a["id"])}" '
                    f'data-title="{e(a["source"] + " | " + a["title"])}">{e(a["source"])}で元の記事を読む\u00a0↗'
                    + (f' <small>（{e(lang)}）</small>' if a.get('lang') != 'ja' else '') + '</a>')
        body.append(f'<p class="credit">要約は F1 Grid Walk が独自にまとめたものです。記事の著作権は {e(a["source"])} に帰属します。</p>')
        kt, kp = related_entries(a, allarts)
        if kt or kp:
            kw = '<aside class="kw" aria-label="この記事のキーワード"><p class="kw-h">この記事のキーワード<small>F1 Grid Walk ルールブックより</small></p>'
            kw += ''.join(f'<a class="kw-t" href="{rb_url(x["id"])}" data-track="click/kw/{e(x["id"])}"><b>{e(x["name"])}</b><small>{e(x["cat"])}</small><span>{e(x["short"])}</span></a>' for x in kt)
            if kp:
                kw += '<p class="kw-ph">登場する人物</p><div class="kw-p">' + ''.join(f'<a href="{rb_url(x["id"])}" data-track="click/kw/{e(x["id"])}">{e(x["name"])}</a>' for x in kp) + '</div>'
            kw += '<a class="kw-all" href="/deep/rules/">ルールブックで用語を引く →</a></aside>'
            body.append(kw)
        hb = hub_for_article(a['id'])
        if hb:
            body.append(hub_box(hb))
        dg = deep_for_article(a)
        if dg:
            body.append(deep_card(dg))
        tags = []
        for tk in a.get('teams') or []:
            if tk in teams:
                tn_ = e(teams[tk].get("en") or teams[tk].get("name"))
                tags.append(f'<a href="/teams/{tk}/" data-track="click/tag/team/{tk}">{tn_}</a>' if tk in team_pages else f'<span>{tn_}</span>')
        gs, gx = gp_link(a)
        c = circuits.get(a.get('circuit') or '')
        if gs:
            tags.append(f'<a href="/gp/{gs}/" data-track="click/tag/gp/{gs}">{e(gx["gp"])}</a>')
        elif c:
            tags.append(f'<span>{e(c.get("gp", ""))}</span>')
        if a.get('cat'):
            tags.append(f'<span>{e(a["cat"])}</span>')
        if tags:
            body.append('<div class="tags">' + ''.join(tags) + '</div>')
        share_text = a['title'] + ' | F1 Grid Walk'
        body.append('<div class="share">共有：'
                    f'<a href="https://x.com/intent/tweet?text={quote(share_text)}&url={quote(url)}" target="_blank" rel="noopener" data-track="share/x">X</a>'
                    f'<a href="https://social-plugins.line.me/lineit/share?url={quote(url)}" target="_blank" rel="noopener" data-track="share/line">LINE</a>'
                    f'<a href="https://b.hatena.ne.jp/add?mode=confirm&url={quote(url)}" target="_blank" rel="noopener" data-track="share/hatena">はてブ</a>'
                    '<button type="button" id="copy" data-track="share/copy">リンクをコピー</button></div>')
        body.append('</article>')

        others = [x for x in by_topic.get(a.get('topic'), []) if x['id'] != a['id']]
        if others:
            t = arch['topics'].get(a['topic'], {})
            body.append('<section><h2>' + e(t.get('title') or 'この話題を報じたほかの媒体') + '</h2>'
                        + (f'<p class="lead">{e(t["summary"])}</p>' if t.get('summary') else '')
                        + f'<p class="lead">ほかに {len(others)} 本の記事があります。</p>'
                        + '<ul class="list">' + ''.join(item_li(x, flag_of) for x in others[:12]) + '</ul></section>')
        shown = {a['id']} | {x['id'] for x in others[:12]}
        tk = next((t for t in (a.get('teams') or []) if t in teams), None)
        if tk:
            same = [x for x in allarts if tk in (x.get('teams') or []) and x['id'] not in shown][:5]
            if same:
                tn = teams[tk].get('name') or teams[tk].get('en')
                body.append(f'<section><h2>{e(tn)}の記事</h2><ul class="list">'
                            + ''.join(item_li(x, flag_of) for x in same) + '</ul>'
                            + (f'<p><a href="/teams/{tk}/" data-track="click/news/team-all/{tk}">{e(tn)}の記事をすべて見る →</a></p>' if tk in team_pages else '')
                            + '</section>')
                shown |= {x['id'] for x in same}
        latest = [x for x in allarts if x['id'] not in shown and x.get('topic') != a.get('topic')][:6]
        if latest:
            body.append('<section><h2>最新の記事</h2><ul class="list">'
                        + ''.join(item_li(x, flag_of) for x in latest)
                        + '</ul><p><a href="/">トップで全部見る →</a>　<a href="/news/">ニュース一覧 →</a></p></section>')
        og_url = article_og(a, k)
        crumbs_ld = json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'F1 Grid Walk', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'ニュース一覧', 'item': SITE + '/news/'},
            {'@type': 'ListItem', 'position': 3, 'name': a['title'], 'item': url}]}, ensure_ascii=False)
        crumbs_ld = crumbs_ld.replace('</', '<\\/')
        art_ld = {'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': a['title'], 'description': desc,
                  'datePublished': a['published'], 'dateModified': a['published'], 'inLanguage': 'ja',
                  'image': [og_url or OG_IMAGE], 'mainEntityOfPage': url, 'author': PUBLISHER, 'publisher': PUBLISHER,
                  'isBasedOn': {'@type': 'NewsArticle', 'url': a['url'], 'headline': a.get('orig') or a['title'],
                                'publisher': {'@type': 'Organization', 'name': a['source']}}}
        if nused:
            body.append(term_assets(nused))
        head = ((f'<style>{DEEP_CSS}</style>\n' if dg else '') + (f'<style>{RULES_CSS}</style>\n' if nused else '') + f'<meta property="article:published_time" content="{e(a["published"])}">\n'
                f'<script type="application/ld+json">{crumbs_ld}</script>\n' + ld(art_ld))
        if write(f'news/{a["id"]}/index.html',
                 page(f'{a["title"]}｜F1グリッドウォーク', desc, url, '\n'.join(body), head, og_image=og_url)):
            changed += 1

    # the list pages: the newest articles on /news/, every month on its own page (14 Oct 2026)
    month_sm = build_news_lists(allarts, flag_of)

    # sitemap
    now = datetime.now(JST).isoformat(timespec='seconds')
    urls = [(SITE + '/', now, 'hourly', '1.0'), (SITE + '/news/', now, 'hourly', '0.8')]
    urls += [(f'{SITE}/news/{a["id"]}/', when(a).isoformat(timespec='seconds'), None, '0.6') for a in allarts]
    urls += [u for u in build_lenses(arch, flag_map) if u[1]]
    urls += [u for u in build_deeps(arch, flag_map) if u[1]]
    urls += build_all_columns()
    urls += build_rules()
    urls += build_hubs(arch, flag_of)
    by_term = add_term_reads()
    urls += build_drivers(by_term)
    top_people_slot()
    top_latest_slot(allarts)
    top_rail_slot()
    add_related()
    urls += month_sm
    urls += build_gp_pages(flag_of, circuits)
    urls += build_team_pages(allarts, flag_of, teams)
    build_share_kit()  # owner's copy-and-paste page, not in the sitemap
    top_rules_slot()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lm, cf, pr in urls:
        sm.append(f'  <url><loc>{e(loc)}</loc><lastmod>{lm}</lastmod>' + (f'<changefreq>{cf}</changefreq>' if cf else '') + f'<priority>{pr}</priority></url>')
    sm.append('</urlset>')
    write('sitemap.xml', '\n'.join(sm) + '\n')
    # the same URLs split in two (owner's OK, 24 Oct 2026): Search Console has shown sitemap.xml as
    # 「取得できませんでした」 for weeks although it is valid; new file names give it a fresh fetch
    head_, tail_ = sm[:2], sm[-1:]
    urls_ = [l for l in sm[2:-1] if '<loc>' in l]
    for fn_, keep in (('sitemap-news.xml', lambda l: '/news/' in l), ('sitemap-pages.xml', lambda l: '/news/' not in l)):
        write(fn_, '\n'.join(head_ + [l for l in urls_ if keep(l)] + tail_) + '\n')
    build_feed(allarts)

    # robots.txt: everything may be crawled; say where the sitemap is
    write('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/sitemap-pages.xml\nSitemap: {SITE}/sitemap-news.xml\n')

    # 404 page (GitHub Pages serves /404.html for any missing path)
    nf = ['<div class="nf"><p class="nf-code">404</p><h1>ページが見つかりませんでした</h1>'
          '<p class="lead">アドレスが間違っているか、ページが移動した可能性があります。</p>'
          '<p class="nf-go"><a class="cta" href="/">トップへ戻る</a><a href="/news/">ニュース一覧 →</a><a href="/lens/">コラム →</a></p></div>']
    if allarts:
        nf.append('<section><h2>最新の記事</h2><ul class="list">' + ''.join(item_li(x, flag_of) for x in allarts[:6]) + '</ul></section>')
    nf_html = page('ページが見つかりません｜F1グリッドウォーク', 'お探しのページは見つかりませんでした。', SITE + '/', '\n'.join(nf),
                   '<meta name="robots" content="noindex">\n<style>.nf{padding:28px 0 8px}.nf-code{font:600 64px/1 Fraunces,serif;color:var(--clay);margin:0 0 6px}'
                   '.nf-go{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center;margin-top:18px}.nf-go .cta{margin:0}</style>\n', og_type='website')
    write('404.html', nf_html.replace(f'<link rel="canonical" href="{SITE}/">\n', ''))

    prerender_index(data, flag_of, flag_map)

    arch['updatedAt'] = data.get('updatedAt', now)
    write('news/archive.json', json.dumps(arch, ensure_ascii=False, indent=1) + '\n')
    print(f'build: {len(allarts)} article pages ({changed} new or changed), news/index.html, sitemap.xml')


if __name__ == '__main__':
    main()
