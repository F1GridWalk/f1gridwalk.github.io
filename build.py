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
.cta{display:flex;align-items:center;justify-content:center;gap:10px;min-height:56px;padding:12px 22px;border-radius:999px;background:var(--ink);color:var(--on-ink);font-weight:700;font-size:16px;text-decoration:none;text-align:center}
.cta:hover{color:var(--on-ink);opacity:.9}
.cta small{font-weight:500;opacity:.8;font-size:12.5px}
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


def page(title, desc, canonical, body, extra_head='', og_type='article'):
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
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{OG_IMAGE}">
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
  <p><a href="/">F1 Grid Walk</a> — 世界のF1ニュースを、日本語で。日本時間の0時・6時・12時・18時ごろに更新。</p>
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


def static_card(a, flag_of):
    k = kind_of(a)
    return (f'<article class="card" data-c="{flag_of(a)}"><div class="card-meta">'
            f'<span class="kind {k}" title="{e(KIND_TIP[k])}">{KIND[k]}</span>'
            f'<span class="srcbadge" data-c="{flag_of(a)}">{e(a["source"])}</span>'
            f'<span class="rg">{e(a.get("region", ""))}</span>'
            f'<time datetime="{e(a["published"])}">{short_jst(a)}</time></div>'
            f'<h3>{ext(a["url"], e(a["title"]))}</h3><p>{e(a.get("summary", ""))}</p>'
            f'<a class="perma" href="/news/{e(a["id"])}/">詳細・共有 ›</a></article>')


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
                    f'<h1 id="hero-title">{ext(pick["url"], e(info.get("title") or pick["title"]))}</h1>'
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
                      + ext(x['url'], f'<span class="kind {k}" style="margin-right:6px">{KIND[k]}</span>' + e(x['title']), 'tl-title')
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
                links = ''.join(f'<li data-c="{flag_of(x)}"><span class="srcbadge" data-c="{flag_of(x)}">{e(x["source"])}</span>{ext(x["url"], e(x["title"]))}</li>' for x in g_arts)
                cols.append(f'<article class="lens-col" data-c="{fc}"><div class="lens-who">{flag}{e(g.get("label", ""))}'
                            + (f'<small>{small}</small>' if small else '') + '</div>'
                            f'<p class="lens-focus"><small>焦点</small>{e(g.get("focus", ""))}</p>'
                            + (f'<ul class="lens-pts">{pts}</ul>' if pts else '')
                            + (f'<details class="lens-src"><summary>記事を見る</summary><ul>{links}</ul></details>' if links else '')
                            + '</article>')
            hero.append('<section class="tw-sec lens" id="tw-lens"><h2 class="tw-h tw-h-lens"><span class="tw-dot"></span>世界の見方<span class="en">WORLD MEDIA LENS</span></h2>'
                        '<p class="tw-lead">このニュースを、世界の媒体はどう伝えたか。各記事の主役・焦点・原因の説明・見出しの強調点を読み比べました。</p>'
                        '</section>')
    else:
        a = next((x for x in arts if x.get('featured')), arts[0] if arts else None)
        if a:
            hero.append('<div class="chips"><span class="chip-feature">今日の一本</span></div>')
            hero.append(f'<h1 id="hero-title">{ext(a["url"], e(a["title"]))}</h1><p class="hero-sum">{e(a.get("summary", ""))}</p>')
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
        topic_arts = sorted([a for a in arch['articles'].values() if a.get('topic') == L.get('topic') and a.get('kind') != 'fan'], key=when, reverse=True)
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
                 f'<div class="lens-stats"><div><b>{len(L["unreported"]["items"])}</b>日本語で見当たらない話</div>'
                 f'<div><b>1</b>あなたが解く謎</div><div><b>{n_src}</b>媒体・{n_cty}か国</div></div></div>')
        U = L['unreported']
        B.append('<section class="lens-sec"><div class="lens-sh"><span class="no">1</span><h2>日本では見当たらなかった話</h2></div>'
                 f'<p class="lens-lead">{e(U.get("lead", "海外の記事にだけ書かれていた話です。"))}</p>')
        for i, it in enumerate(U['items'], 1):
            cc = flag_map.get(it.get('region', ''), 'xx')
            k = it.get('kind', 'news')
            also = ''
            if it.get('also'):
                also = '<span class="also">同じ話を伝えた媒体：' + '、'.join(lens_src_link(x, flag_map, region_of) for x in it['also']) + '</span>'
            B.append(f'<article class="uc"><div class="ucn">NO.{i:02d}</div>'
                     f'<div class="ucm"><span class="bigflag" data-c="{cc}"></span><div><b>{e(it["source"])}</b><small>{e(it.get("region", ""))} · {e(LANG.get(it.get("lang"), ""))}</small></div>'
                     f'<span class="kind {k}" title="{e(KIND_TIP.get(k, ""))}">{KIND.get(k, "報道")}</span></div>'
                     f'<h3>{e(it["headline"])}</h3><p>{e(it["body"])}</p>'
                     f'<div class="ucf"><span class="stamp">日本語の記事 見当たらず</span>'
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

        title = f'{L["title"]}｜WORLD MEDIA LENS'
        head = f'<meta property="article:published_time" content="{e(L["published"])}">\n<style>{LENS_CSS}</style>\n'
        write(f'lens/{slug}/index.html', page(title, L['dek'], url, '\n'.join(B) + LENS_JS, head))
        lenses.append((pub, slug, L, url))

    lenses.sort(key=lambda x: x[0], reverse=True)
    # link the newest lens from the top page (inside <!--pre:lens--> in index.html)
    ip = os.path.join(ROOT, 'index.html'); src = open(ip, encoding='utf-8').read()
    blk = ''
    if lenses:
        p0, s0, L0, u0 = lenses[0]
        blk = (f'<a class="lens-link" href="/lens/{e(s0)}/"><small>WORLD MEDIA LENS · {e(L0["gpLabel"])}</small>'
               f'<b>{e(L0["title"])}</b><span>世界の記事を読み比べた特集。謎の答え合わせと投票も →</span></a>')
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
            '<p class="lead">1レースにつき1本。世界の媒体の記事を読み比べて、日本では見当たらなかった話と、見出しだけでは分からないことを日本語でまとめます。</p>'
            f'<ul class="lens-list">{items}</ul>')
    write('lens/index.html', page('WORLD MEDIA LENS｜F1 Grid Walk', '世界のF1報道を読み比べて、日本では見当たらなかった話をまとめる、1レース1本の記事。',
                                  SITE + '/lens/', body, f'<style>{LENS_CSS}</style>\n', og_type='website'))
    return [(SITE + '/lens/', lenses[0][0].isoformat(timespec='seconds') if lenses else None, 'weekly', '0.8')] + \
           [(u, p.isoformat(timespec='seconds'), None, '0.9') for p, s, L, u in lenses]



def main():
    global FLAGS, LOGO
    FLAGS, flag_map, LOGO = shared_css()
    data = load('articles.json', {})
    teams = (load('teams.json', {}) or {}).get('teams', {})
    circuits = (load('circuits.json', {}) or {}).get('circuits', {})
    arch = load('news/archive.json', {'articles': {}, 'topics': {}})

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
        body.append(f'<p class="summary">{e(a.get("summary", ""))}</p>')
        body.append(f'<a class="cta" href="{e(a["url"])}" target="_blank" rel="noopener" data-track="click/{e(a["id"])}" '
                    f'data-title="{e(a["source"] + " | " + a["title"])}">{e(a["source"])}で元の記事を読む ↗'
                    + (f' <small>（{e(lang)}）</small>' if a.get('lang') != 'ja' else '') + '</a>')
        body.append(f'<p class="credit">要約は F1 Grid Walk が独自にまとめたものです。記事の著作権は {e(a["source"])} に帰属します。</p>')
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
        head = (f'<meta property="article:published_time" content="{e(a["published"])}">\n'
                f'<script type="application/ld+json">{crumbs_ld}</script>\n')
        if write(f'news/{a["id"]}/index.html',
                 page(f'{a["title"]}｜F1 Grid Walk', desc, url, '\n'.join(body), head)):
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
    write('news/index.html', page('ニュース一覧｜F1 Grid Walk', '世界のF1ニュースを日本語の見出しと要約で。これまでに紹介した記事の一覧です。',
                                  SITE + '/news/', lst, og_type='website'))

    # sitemap
    now = datetime.now(JST).isoformat(timespec='seconds')
    urls = [(SITE + '/', now, 'hourly', '1.0'), (SITE + '/news/', now, 'hourly', '0.8')]
    urls += [(f'{SITE}/news/{a["id"]}/', when(a).isoformat(timespec='seconds'), None, '0.6') for a in allarts]
    urls += [u for u in build_lenses(arch, flag_map) if u[1]]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lm, cf, pr in urls:
        sm.append(f'  <url><loc>{e(loc)}</loc><lastmod>{lm}</lastmod>' + (f'<changefreq>{cf}</changefreq>' if cf else '') + f'<priority>{pr}</priority></url>')
    sm.append('</urlset>')
    write('sitemap.xml', '\n'.join(sm) + '\n')

    prerender_index(data, flag_of, flag_map)

    arch['updatedAt'] = data.get('updatedAt', now)
    write('news/archive.json', json.dumps(arch, ensure_ascii=False, indent=1) + '\n')
    print(f'build: {len(allarts)} article pages ({changed} new or changed), news/index.html, sitemap.xml')


if __name__ == '__main__':
    main()
