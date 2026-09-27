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
KEEP = ('id', 'kind', 'primary', 'lang', 'region', 'source', 'cat', 'circuit', 'teams', 'topic',
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
var cp=document.getElementById('copy');
if(cp) cp.addEventListener('click',function(){{
  var done=function(){{cp.textContent='コピーしました';setTimeout(function(){{cp.textContent='リンクをコピー';}},1400);}};
  try{{navigator.clipboard.writeText(location.href).then(done,function(){{window.prompt('このURLをコピーしてください',location.href);}});}}catch(e){{window.prompt('このURLをコピーしてください',location.href);}}
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
            body.append('<section><h2>新着ニュース</h2><ul class="list">'
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
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lm, cf, pr in urls:
        sm.append(f'  <url><loc>{e(loc)}</loc><lastmod>{lm}</lastmod>' + (f'<changefreq>{cf}</changefreq>' if cf else '') + f'<priority>{pr}</priority></url>')
    sm.append('</urlset>')
    write('sitemap.xml', '\n'.join(sm) + '\n')

    arch['updatedAt'] = data.get('updatedAt', now)
    write('news/archive.json', json.dumps(arch, ensure_ascii=False, indent=1) + '\n')
    print(f'build: {len(allarts)} article pages ({changed} new or changed), news/index.html, sitemap.xml')


if __name__ == '__main__':
    main()
