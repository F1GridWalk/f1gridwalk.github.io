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
from urllib.parse import quote
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://f1gridwalk.github.io'
JST = timezone(timedelta(hours=9))
OG_IMAGE = SITE + '/og-image.png?v=1'

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
.tags span{font-size:12.5px;border:1px solid var(--line);border-radius:999px;padding:2px 12px;background:var(--surface)}
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
footer{margin:56px 0 0;border-top:1px solid var(--line);padding:22px 0 40px;font-size:12px;color:var(--muted)}
footer p{margin:6px 0}
@media (max-width:600px){.summary{font-size:16px}.cta{font-size:15px}}
'''


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
<style>{CSS}{FLAGS}</style>
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
  <p><a href="/">F1 Grid Walk</a> — 世界のF1ニュースを、日本語で。毎日更新。</p>
  <p>記事の著作権は各媒体に帰属します。当サイトは見出しの翻訳と独自の短い要約、原文へのリンクを掲載しています。F1 Grid Walk は非公式のファンサイトで、Formula 1 および FIA とは関係ありません。</p>
</div></footer>
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
    if best:
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
        if lens:
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
            hero.append('<section class="tw-sec lens" id="tw-lens"><h2 class="tw-h tw-h-lens"><span class="tw-dot"></span>世界の見方<span class="en">WORLD MEDIA LENS</span></h2>'
                        '<p class="tw-lead">このニュースを、世界の媒体はどう伝えたか。各記事の<b>主役</b>・<b>焦点</b>・<b>原因の説明</b>・<b>見出しの強調点</b>を読み比べました。</p>'
                        '</section>')
    else:
        a = next((x for x in arts if x.get('featured')), arts[0] if arts else None)
        if a:
            hero.append('<div class="chips"><span class="chip-feature">今日の一本</span></div>')
            hero.append(f'<h1 id="hero-title">{art(a, e(a["title"]))}</h1><p class="hero-sum">{e(a.get("summary", ""))}</p>')
    news = sorted([a for a in arts if a.get('kind', 'news') == 'news'], key=when, reverse=True)[:10]
    tech = sorted([a for a in arts if a.get('kind') == 'tech'], key=when, reverse=True)[:3]
    feed = ('<div class="grid">' + ''.join(static_card(a, flag_of) for a in news) + '</div>'
            '<p class="pre-more"><a href="/news/">すべてのニュースの一覧 →</a></p>') if news else ''
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
# WORLD MEDIA LENS: one long-form page per race, from lens/<slug>.json
# ---------------------------------------------------------------------------
LENS_CSS = '''
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
.lens-list a{font-size:17px;font-weight:800;text-decoration:none}
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


def build_lenses(arch, flag_map):
    """Render lens/<slug>/index.html for every lens/<slug>.json, plus lens/index.html. Returns sitemap rows."""
    d = os.path.join(ROOT, 'lens')
    if not os.path.isdir(d):
        return []
    region_of = {}
    for a in arch['articles'].values():
        region_of.setdefault(a['source'], a.get('region'))
    lenses = []
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
        B.append(f'<nav class="crumbs" aria-label="現在地"><a href="/">トップ</a> › <a href="/lens/">WORLD MEDIA LENS</a> › {e(L["gpLabel"])}</nav>')
        B.append(f'<div class="lens-hero" data-big="{e(L.get("big", ""))}"><div class="lens-ey">WORLD MEDIA LENS · {e(L["gpLabel"])}</div>'
                 f'<h1>{L["titleHtml"]}</h1><p class="dek">{e(L["dek"])}</p><p class="date">{e(jst_text(pub))} 公開</p>'
                 '</div>')
        if L.get('type') == 'column':
            B.append('<div class="col-body">')
            for blk in L['body']:
                k, t = blk[0], blk[1]
                if k == 'h2': B.append(f'<h2>{e(t)}</h2>')
                elif k == 'quote': B.append(f'<blockquote><p>{e(t)}</p></blockquote>')
                elif k == 'bold': B.append(f'<p><strong>{e(t)}</strong></p>')
                elif k == 'ask': B.append(f'<p class="ask">{e(t)}</p>')
                else: B.append(f'<p>{e(t)}</p>')
            B.append('</div>')
            B.append(site_entrance(arch, slug))
            if L.get('note'):
                B.append(f'<p class="lens-note">{e(L["note"])}</p>')
            L.setdefault('unreported', {'items': []}); L.setdefault('mystery', {'evidence': []})
        else:
            B.extend(lens_issue_blocks(L, slug, flag_map, region_of))
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
                    'articleSection': 'WORLD MEDIA LENS'})
        head += ld({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'F1 Grid Walk', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'WORLD MEDIA LENS', 'item': SITE + '/lens/'},
            {'@type': 'ListItem', 'position': 3, 'name': L['title'], 'item': url}]})
        used = set()
        body_html = link_terms_html('\n'.join(B), used)
        head = MONO_FONT + head + f'<style>{RULES_ENTRY_CSS}{RULES_CSS if used else ""}</style>\n'
        write(f'lens/{slug}/index.html', page(title, L['dek'], url, body_html + term_assets(used) + LENS_JS, head, og_image=ogi, og_size=(1280, 670)))
        lenses.append((pub, slug, L, url))

    lenses.sort(key=lambda x: x[0], reverse=True)
    # link the newest lens from the top page (inside <!--pre:lens--> in index.html)
    ip = os.path.join(ROOT, 'index.html'); src = open(ip, encoding='utf-8').read()
    blk = ''
    if lenses:
        p0, s0, L0, u0 = lenses[0]
        # top page: LENS and DEEP GRID as two equal rows in one frame (owner's choice E, 3 Oct 2026)
        blk = (f'<a class="duo-row duo-lens" href="/lens/{e(s0)}/" data-track="click/top/lens"><span class="duo-q"><small>WORLD MEDIA LENS</small><strong>海外の見方を、日本語で。</strong></span>'
               f'<b>{e(L0["title"])}&#8288;<i aria-hidden="true">→</i></b></a>')
    out = re.sub(r'(<!--pre:lens-->).*?(<!--/pre:lens-->)', lambda m: m.group(1) + blk + m.group(2), src, count=1, flags=re.S)
    if out != src:
        open(ip, 'w', encoding='utf-8').write(out)
    if not lenses:
        old = os.path.join(ROOT, 'lens', 'index.html')
        if os.path.exists(old):
            os.remove(old)
        return []
    items = ''.join(f'<li><a href="/lens/{e(s)}/">{e(L["title"])}</a><small>{e(L["gpLabel"])} · {e(jst_text(p))}</small></li>' for p, s, L, u in lenses)
    body = ('<nav class="crumbs"><a href="/">トップ</a> › WORLD MEDIA LENS</nav><h1>WORLD MEDIA LENS</h1>'
            '<p class="lead">毎朝7時のコラムと、レース週末の金・土・日に出すグランプリ特別号。世界の媒体の記事を読み比べて、日本語ではあまり語られない話と、見出しだけでは分からないことを届けます。</p>'
            f'<ul class="lens-list">{items}</ul>')
    write('lens/index.html', page('WORLD MEDIA LENS｜F1 Grid Walk（F1グリッドウォーク）', '世界のF1報道を読み比べるコラム。毎朝のコラムと、レース週末のグランプリ特別号。',
                                  SITE + '/lens/', body, f'<style>{LENS_CSS}</style>\n', og_type='website'))
    return [(SITE + '/lens/', lenses[0][0].isoformat(timespec='seconds') if lenses else None, 'weekly', '0.8')] + \
           [(u, p.isoformat(timespec='seconds'), None, '0.9') for p, s, L, u in lenses]



# ---------------------------------------------------------------- DEEP GRID
# deep/<slug>.json -> deep/<slug>/index.html, deep/index.html. "ニュースの、その奥へ。"
DEEP_COPY = 'ニュースの、その奥へ。'
DEEPS = []  # published issues, newest first (filled by load_deeps)

DEEP_CSS = '''
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
            out.append(f'<p>{link_terms(e(b["p"]), used) if used is not None else e(b["p"])}</p>')
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
    return ''.join(out)


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
        if D.get('glossary'):
            B.append('<div class="dg-end"><h2><span class="k">GLOSSARY</span>この号の用語</h2><dl>'
                     + ''.join(f'<dt>{e(t)}</dt><dd>{e(d)}</dd>' for t, d in D['glossary']) + '</dl></div>')
        B.append('<div class="dg-end" id="sources"><h2><span class="k">SOURCES</span>出典</h2><ol class="dg-src">'
                 + ''.join(f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener" data-track="click/deep/{e(slug)}/src">{e(s["name"])}</a> <small>{e(s["title"])}</small></li>' for s in D.get('sources', []))
                 + '</ol><p class="tnote" style="margin-top:10px">発言は原文から訳し、数字は出典で確かめたものだけを使っています。</p></div>')
        if D.get('history'):
            B.append('<div class="dg-end"><h2><span class="k">UPDATES</span>更新履歴</h2><ul class="dg-hist">'
                     + ''.join(f'<li><time>{e(d)}</time>{e(t)}</li>' for d, t in D['history']) + '</ul></div>')
        # links out: TODAY (newest news on the same circuit/teams/topics), WORLD MEDIA LENS, other issues
        news = [a for a in sorted(arch['articles'].values(), key=when, reverse=True)
                if a.get('kind') != 'fan' and deep_for_article(a) is D][:5]
        if news:
            B.append('<div class="dg-end"><h2><span class="k">TODAY</span>このテーマの最新ニュース</h2><ul class="list">'
                     + ''.join(item_li(a, flag_of) for a in news) + '</ul></div>')
        rel = [lens[s] for s in D.get('lensRelated', []) if s in lens]
        if rel:
            B.append('<div class="dg-end"><h2><span class="k">WORLD MEDIA LENS</span>世界はどう報じた？</h2>'
                     + ''.join(f'<a class="dg-card" href="/lens/{e(L["slug"])}/"><small>WORLD MEDIA LENS · {e(L["gpLabel"])}</small><b>{e(L["title"])}</b></a>' for L in rel) + '</div>')
        others = [x for x in DEEPS if x is not D][:3]
        B.append('<div class="dg-end"><h2><span class="k">DEEP GRID</span>ほかの号</h2>'
                 + ''.join(deep_card(x, 'dg-card', '読む') for x in others)
                 + rules_entry('deep-issue')
                 + '<a class="dg-card" href="/deep/"><small>DEEP GRID</small><b>すべての号を見る →</b></a></div>')
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
        write(f'deep/{slug}/index.html', page(f'{D["title"]}｜DEEP GRID｜F1グリッドウォーク', D['dek'], url, '\n'.join(B), head))
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
    items = ''.join(f'<li><a href="/deep/{e(D["slug"])}/"><small>DEEP GRID {deep_no(D)}</small><b>{e(D["title"])}</b></a>'
                    f'<p>{e(D["quick"][0] if D.get("quick") else D["dek"])}</p></li>' for D in DEEPS)
    body = ('<nav class="crumbs"><a href="/">トップ</a> › DEEP GRID</nav><div class="dg">'
            f'<div class="dg-top"><div class="dg-label"><b>DEEP GRID</b><span>{DEEP_COPY}</span></div></div>'
            '<h1>DEEP GRID</h1>'
            '<p class="dg-dek">ニュースの続きを、ニュースより深く読む。なぜ起きたのか、技術的に何を意味するのか、過去と何が違うのか。'
            'まず「先に結論」で要点をつかみ、その先は奥へ行くほど深くなる、F1 Grid Walkの深掘り記事です。</p>'
            + rules_entry('deep-index')
            + f'<ul class="dg-list">{items}</ul></div>')
    write('deep/index.html', page('DEEP GRID｜ニュースの、その奥へ。｜F1グリッドウォーク',
                                  'F1のニュースの「なぜ」を深く読む、F1 Grid Walkの深掘り記事。パワーユニット、空力、タイヤ、規則、データ、歴史まで。',
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
  var items=[].slice.call(document.querySelectorAll('details.rb')), cat='all';
  var cnt=document.getElementById('rb-count'), none=document.getElementById('rb-none'), maybe=document.getElementById('rb-maybe');
  var parent=items.length?items[0].parentNode:null, endMark=items.length?items[items.length-1].nextSibling:null;
  items.forEach(function(d,i){ d._i=i; d._k=norm(d.getAttribute('data-k')); d._names=(d.getAttribute('data-names')||'').split('|').map(norm).filter(Boolean); d._n=d._names.join(' '); d._w=(d.getAttribute('data-w')||'').split('|').map(norm).filter(Boolean); });
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
    items.forEach(function(d){ if(!d.hidden) d.open = ts.length>0 && (n<=2 || d._s===3); });
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
  function go(){ run(); q.blur(); var f=document.querySelector('details.rb:not([hidden])'); if(q.value&&f){ f.scrollIntoView({behavior:'smooth',block:'start'}); } }
  var gb=document.getElementById('rb-go'); if(gb) gb.addEventListener('click',go);
  q.addEventListener('keydown',function(ev){ if(ev.key==='Enter'){ ev.preventDefault(); go(); } });
  q.addEventListener('search',run);
  [].forEach.call(document.querySelectorAll('.rb-none button'),function(b){ b.addEventListener('click',function(){ q.value=b.textContent; run(); }); });
  function openHash(){ var id=location.hash.slice(1); var d=id&&document.getElementById(id); if(d&&d.tagName==='DETAILS'){ d.hidden=false; d.open=true; setTimeout(function(){d.scrollIntoView({block:'start'});},50);} }
  window.addEventListener('hashchange',openHash); openHash();
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
    var l=document.createElement('a'); l.href=a.getAttribute('href'); l.textContent='ルールブックで詳しく →'; pop.appendChild(document.createElement('br')); pop.appendChild(l);
    document.body.appendChild(pop);
    var r=a.getBoundingClientRect(), w=Math.min(300,document.documentElement.clientWidth-32);
    pop.style.width=w+'px';
    pop.style.left=Math.max(16,Math.min(r.left+scrollX,document.documentElement.clientWidth-w-16))+'px';
    pop.style.top=(r.bottom+scrollY+8)+'px';
  });
  document.addEventListener('keydown',function(ev){ if(ev.key==='Escape') close(); });
})();
</script>'''


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


def link_terms(html_text, used):
    """Underline the first appearance of each rulebook term in a paragraph (already HTML-escaped)."""
    if not RULES:
        return html_text
    for word, tid, _, _ in term_lookup():
        if tid in used:
            continue
        w = e(word)
        i = html_text.find(w)
        if i >= 0:
            html_text = html_text[:i] + f'<a class="term" href="/deep/rules/#{tid}" data-term="{tid}">{w}</a>' + html_text[i + len(w):]
            used.add(tid)
    return html_text


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


def build_rules():
    if not RULES:
        return []
    R = RULES
    url = SITE + '/deep/rules/'
    name = {t['id']: t['term'] for t in R['terms']}
    cats = ''.join(f'<button type="button" data-c="{e(c)}" aria-pressed="false">{e(c)}</button>' for c in R['cats'])
    items = []
    for t in sorted(R['terms'], key=lambda t: (R['cats'].index(t['cat']), t['term'])):
        # search also hits names and words inside the explanation and this season's examples (e.g. a driver's name)
        keys = ' '.join([t['term']] + t.get('aliases', []) + t.get('words', []) + [t['short']] + t.get('body', []) + [x['t'] for x in t.get('examples', [])])
        b = ''.join(f'<p>{e(p)}</p>' for p in t['body'])
        if t.get('tool') == 'pu':
            opts = '<option value="0">なし・上限内</option><option value="10">初めて超えた（+10）</option><option value="5">2回目以降（+5）</option>'
            rows = ''.join(f'<label>{e(p)}<select aria-label="{e(p)}">{opts}</select></label>' for p in ['エンジン（ICE）', 'ターボ', 'MGU-K', 'バッテリー（ES）', '制御電子機器（CE）'])
            b += PU_TOOL.format(rows=rows)
        if t.get('rule'):
            b += f'<div class="rb-h">規則</div><span class="rb-rule">FIA {e(t["rule"])}</span>'
        if t.get('examples'):
            b += '<div class="rb-h">今季の実例・関連記事</div><ul class="rb-ex">' + ''.join(f'<li><a href="{e(x["u"])}">{e(x["t"])}</a></li>' for x in t['examples']) + '</ul>'
        if t.get('see'):
            b += '<div class="rb-h">あわせて読む</div><div class="rb-see">' + ''.join(f'<a href="#{e(s)}">{e(name.get(s, s))}</a>' for s in t['see']) + '</div>'
        al = '・'.join([x for x in t.get('aliases', []) if not re.fullmatch(r'[\u3041-\u309f\u30fc]+', x)][:4])
        items.append(f'<details class="rb" id="{e(t["id"])}" data-c="{e(t["cat"])}" data-t="{e(t["term"])}" data-names="{e("|".join([t["term"]] + t.get("aliases", [])))}" data-w="{e("|".join(t.get("words", [])))}" data-k="{e(keys)}">'
                     f'<summary><span class="rb-t"><b>{e(t["term"])}</b><small>{e(t["cat"])}</small></span>'
                     + (f'<span class="rb-al">{e(al)}</span>' if al else '') +
                     f'<span class="rb-s">{e(t["short"])}</span></summary><div class="rb-b">{b}</div></details>')
    titles = {}
    for D in DEEPS:
        titles[f'/deep/{D["slug"]}/'] = 'DEEP GRID ' + deep_no(D) + ' ' + D['title']
    ldir = os.path.join(ROOT, 'lens')
    for fn in os.listdir(ldir):
        if fn.endswith('.json'):
            L = load(os.path.join('lens', fn))
            if L and L.get('slug') and not L.get('draft'):
                titles[f'/lens/{L["slug"]}/'] = f'{L.get("gpLabel", "コラム")}：{L["title"]}'
    for p in PEOPLE:
        keys = ' '.join([p['name'], p.get('kana', ''), p.get('en', ''), p['role'], p['org'], p['short']] + p.get('aliases', []) + p.get('words', []))
        b = f'<div class="rb-h" style="margin-top:0">肩書き</div><span class="rb-rule">{e(p["role"])}（{e(p["org"])}）</span>'
        app = [u for u in p.get('appears', []) if u in titles]
        if app:
            b += '<div class="rb-h">登場する記事</div><ul class="rb-ex">' + ''.join(f'<li><a href="{e(u)}">{e(titles[u])}</a></li>' for u in app) + '</ul>'
        if p.get('sources'):
            b += '<div class="rb-h">出典（肩書きの確認）</div><ul class="rb-ex">' + ''.join(f'<li><a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["name"])}：{e(x["title"])}</a></li>' for x in p['sources']) + '</ul>'
        b += f'<p class="rb-checked">{e(p.get("checked", ""))} に確認</p>'
        al = '・'.join([x for x in [p.get('en', '')] + p.get('aliases', []) if x][:3])
        items.append(f'<details class="rb" id="person-{e(p["id"])}" data-c="人物" data-t="{e(p["name"])}" data-names="{e("|".join([p["name"], p.get("en", ""), p.get("kana", "")] + p.get("aliases", [])))}" data-k="{e(keys)}">'
                     f'<summary><span class="rb-t"><b>{e(p["name"])}</b><small>人物</small></span>'
                     + (f'<span class="rb-al">{e(al)}</span>' if al else '') +
                     f'<span class="rb-s">{e(p["short"])}</span></summary><div class="rb-b">{b}</div></details>')
    sugg = ''.join(f'<button type="button">{e(w)}</button>' for w in ['降格', 'DRS', 'ハジャー', '折原', 'ADUO'])
    body = ('<nav class="crumbs"><a href="/">トップ</a> › <a href="/deep/">DEEP GRID</a> › ルールブック</nav><div class="dg">'
            f'<div class="dg-top"><div class="dg-label"><b>DEEP GRID<i>RULES</i></b><span>{DEEP_COPY}</span></div></div>'
            f'<h1>{e(R["title"])}</h1><p class="dg-dek">{e(R["dek"])}</p>'
            + rules_entry('rules', on_page=True)
            + f'<div class="rb-none" id="rb-none">見つかりませんでした。<span style="display:none"><br>もしかして：<span id="rb-maybe"></span></span><br>こんな言葉はどうですか：<br>{sugg}</div>'
            + ''.join(items) +
            f'<p class="rb-checked" style="margin-top:18px">規則の中身は {e(R["checked"])} 時点で確認しています。FIAが規則を変えたときは、ここを直して日付を更新します。</p>'
            '<div class="dg-end"><h2><span class="k">SOURCES</span>出典</h2><ol class="dg-src">'
            + ''.join(f'<li><a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["name"])}</a> <small>{e(s["title"])}</small></li>' for s in R.get('sources', []))
            + '</ol></div></div>' + RULES_JS)
    head = MONO_FONT + f'<style>{DEEP_CSS}{RULES_CSS}{RULES_ENTRY_CSS}</style>\n' + ld({
        '@context': 'https://schema.org', '@type': 'DefinedTermSet', 'name': R['title'], 'description': R['dek'], 'url': url, 'inLanguage': 'ja',
        'hasDefinedTerm': [{'@type': 'DefinedTerm', 'name': t['term'], 'alternateName': t.get('aliases', [])[:4], 'description': t['short'],
                            'url': f'{url}#{t["id"]}'} for t in R['terms']]})
    if PEOPLE:
        head += ld({'@context': 'https://schema.org', '@graph': [{'@type': 'Person', 'name': p['name'], 'alternateName': p.get('en', ''), 'jobTitle': p['role'],
                    'worksFor': {'@type': 'Organization', 'name': p['org']}, 'url': f'{url}#person-{p["id"]}'} for p in PEOPLE]})
    write('deep/rules/index.html', page(f'{R["title"]}｜F1の用語とルール辞典｜F1グリッドウォーク', R['dek'], url, body, head, og_type='website'))
    return [(url, R['checked'] + 'T09:00:00+09:00', 'weekly', '0.8')]



def main():
    global FLAGS, LOGO
    FLAGS, flag_map, LOGO = shared_css()
    data = load('articles.json', {})
    teams = (load('teams.json', {}) or {}).get('teams', {})
    circuits = (load('circuits.json', {}) or {}).get('circuits', {})
    arch = load('news/archive.json', {'articles': {}, 'topics': {}})
    load_rules()
    load_deeps()

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
        dg = deep_for_article(a)
        if dg:
            body.append(deep_card(dg))
        tags = []
        for tk in a.get('teams') or []:
            if tk in teams:
                tags.append(f'<span>{e(teams[tk].get("en") or teams[tk].get("name"))}</span>')
        c = circuits.get(a.get('circuit') or '')
        if c:
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
        latest = [x for x in allarts if x['id'] != a['id'] and x.get('topic') != a.get('topic')][:6]
        if latest:
            body.append('<section><h2>最新の記事</h2><ul class="list">'
                        + ''.join(item_li(x, flag_of) for x in latest)
                        + '</ul><p><a href="/">トップで全部見る →</a>　<a href="/news/">ニュース一覧 →</a></p></section>')
        crumbs_ld = json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'F1 Grid Walk', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'ニュース一覧', 'item': SITE + '/news/'},
            {'@type': 'ListItem', 'position': 3, 'name': a['title'], 'item': url}]}, ensure_ascii=False)
        crumbs_ld = crumbs_ld.replace('</', '<\\/')
        art_ld = {'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': a['title'], 'description': desc,
                  'datePublished': a['published'], 'dateModified': a['published'], 'inLanguage': 'ja',
                  'image': [OG_IMAGE], 'mainEntityOfPage': url, 'author': PUBLISHER, 'publisher': PUBLISHER,
                  'isBasedOn': {'@type': 'NewsArticle', 'url': a['url'], 'headline': a.get('orig') or a['title'],
                                'publisher': {'@type': 'Organization', 'name': a['source']}}}
        if nused:
            body.append(term_assets(nused))
        head = ((f'<style>{DEEP_CSS}</style>\n' if dg else '') + (f'<style>{RULES_CSS}</style>\n' if nused else '') + f'<meta property="article:published_time" content="{e(a["published"])}">\n'
                f'<script type="application/ld+json">{crumbs_ld}</script>\n' + ld(art_ld))
        if write(f'news/{a["id"]}/index.html',
                 page(f'{a["title"]}｜F1グリッドウォーク', desc, url, '\n'.join(body), head)):
            changed += 1

    # the list page: every article, newest first, grouped by day (JST)
    rows, last = [], None
    for a in allarts:
        dd = when(a).astimezone(JST)
        key = f'{dd.year}年{dd.month}月{dd.day}日（{"月火水木金土日"[dd.weekday()]}）'
        if key != last:
            if last is not None:
                rows.append('</ul>')
            rows.append(f'<h2 class="day">{key}</h2><ul class="list">')
            last = key
        rows.append(item_li(a, flag_of))
    if last is not None:
        rows.append('</ul>')
    lst = ('<nav class="crumbs"><a href="/">トップ</a> › ニュース一覧</nav>'
           '<h1>ニュース一覧</h1>'
           f'<p class="lead">これまでに紹介した世界のF1ニュース {len(allarts)} 本。各国の記事の見出しを日本語にして、短い要約と原文へのリンクを付けています。新しい順。</p>'
           + ''.join(rows))
    write('news/index.html', page('ニュース一覧｜F1 Grid Walk（F1グリッドウォーク）', '世界のF1ニュースを日本語の見出しと要約で。これまでに紹介した記事の一覧です。',
                                  SITE + '/news/', lst, og_type='website'))

    # sitemap
    now = datetime.now(JST).isoformat(timespec='seconds')
    urls = [(SITE + '/', now, 'hourly', '1.0'), (SITE + '/news/', now, 'hourly', '0.8')]
    urls += [(f'{SITE}/news/{a["id"]}/', when(a).isoformat(timespec='seconds'), None, '0.6') for a in allarts]
    urls += [u for u in build_lenses(arch, flag_map) if u[1]]
    urls += [u for u in build_deeps(arch, flag_map) if u[1]]
    urls += build_rules()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lm, cf, pr in urls:
        sm.append(f'  <url><loc>{e(loc)}</loc><lastmod>{lm}</lastmod>' + (f'<changefreq>{cf}</changefreq>' if cf else '') + f'<priority>{pr}</priority></url>')
    sm.append('</urlset>')
    write('sitemap.xml', '\n'.join(sm) + '\n')

    # robots.txt: everything may be crawled; say where the sitemap is
    write('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')

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
