#!/usr/bin/env python3
"""Check the built site for mistakes that are easy to make and hard to see (owner's OK, 20 Nov 2026).

Run after build.py:  python3 tools/validate_site.py [--quiet]
Prints ERROR / WARN lines and a summary. Exit code 1 if there is any ERROR, else 0.
It never changes a file.

Checks
  pages      every index.html has a <title>, one canonical that matches its folder, an <h1>, no duplicate id
  json-ld    every <script type="application/ld+json"> parses
  dates      news pages: <time datetime>, article:published_time and JSON-LD datePublished are the same moment,
             and none is in the future
  links      local href/src (/path/ or /file) point to files that exist
  sitemap    every URL in sitemap.xml exists; no duplicates; every indexable page is in it
             (pages with noindex, 404.html and /share/ are left out on purpose)
  storyline  a resolved STORYLINE page does not say 追いかけ中
  media      one outlet is not shown under two names (tools/source-names.json) -> WARN
  size       pages over the site's own budget (home 250KB, rules index 450KB, team and month pages 150KB) -> WARN
"""
import json, os, re, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://f1gridwalk.github.io'
quiet = '--quiet' in sys.argv
errors, warns = [], []


def err(m):
    errors.append(m)


def warn(m):
    warns.append(m)


def pages():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if not x.startswith('.') and x not in ('node_modules', '__pycache__')]
        if 'index.html' in files:
            yield os.path.join(d, 'index.html')


def url_of(path):
    rel = os.path.relpath(os.path.dirname(path), ROOT).replace(os.sep, '/')
    return SITE + '/' + ('' if rel == '.' else rel + '/')


def parse_dt(s):
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None


now = datetime.now(timezone.utc)
indexable, n = set(), 0
link_re = re.compile(r'(?:href|src)="(/[^"#?]*)')
for p in pages():
    n += 1
    h = open(p, encoding='utf-8', errors='replace').read()
    u = url_of(p)
    short = u.replace(SITE, '')
    if not re.search(r'<title>[^<]+</title>', h):
        err(f'{short}: no <title>')
    can = re.findall(r'<link rel="canonical" href="([^"]+)"', h)
    noidx_ = bool(re.search(r'<meta name="robots" content="[^"]*noindex', h))
    if len(can) != 1:
        err(f'{short}: {len(can)} canonical links')
    elif can[0] != u and not noidx_:  # a left-out duplicate points to the first page on purpose
        err(f'{short}: canonical is {can[0]}')
    if re.search(r'href="/\?[^"]+"', h):
        warn(f'{short}: internal link with a query (?...)')
    if '<h1' not in h:
        warn(f'{short}: no <h1>')
    ids = re.findall(r'\sid="([^"]+)"', h)
    dup = {i for i in ids if ids.count(i) > 1} if len(ids) < 2000 else set()
    if dup:
        err(f'{short}: duplicate id {sorted(dup)[:5]}')
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            json.loads(m)
        except Exception as ex:
            err(f'{short}: JSON-LD does not parse ({ex})')
    noindex = re.search(r'<meta name="robots" content="[^"]*noindex', h)
    if not noindex and short not in ('/share/',):
        indexable.add(u)
    # dates on news pages
    if re.match(r'/news/[a-z0-9-]+/$', short) and not short.startswith(('/news/daily/', '/news/20')):
        vis = re.search(r'<time datetime="([^"]+)"', h)
        og = re.search(r'<meta property="article:published_time" content="([^"]+)"', h)
        ld = re.search(r'"datePublished": "([^"]+)"', h)
        ds = {k: parse_dt(v.group(1)) for k, v in (('time', vis), ('og', og), ('json-ld', ld)) if v}
        vals = {d for d in ds.values() if d}
        if len(vals) > 1:
            err(f'{short}: publication times differ ' + ', '.join(f'{k}={v.isoformat()}' for k, v in ds.items()))
        for k, v in ds.items():
            if v and v > now:
                err(f'{short}: {k} is in the future ({v.isoformat()})')
    # local links
    for t in set(link_re.findall(h)):
        f = os.path.join(ROOT, t.lstrip('/'))
        if t.endswith('/'):
            f = os.path.join(f, 'index.html')
        if not os.path.exists(f) and not os.path.exists(f + '.html'):
            err(f'{short}: broken link {t}')
    # storyline status
    if short.startswith('/storyline/') and short != '/storyline/' and 'sl-st sl-done' in h and '追いかけ中' in h:
        err(f'{short}: resolved but says 追いかけ中')
    # size budget
    size = len(h.encode('utf-8'))
    # the rules index keeps every entry on the page for readers and search engines; 450KB after the two-step search (21 Nov 2026)
    budget = 250_000 if short == '/' else 450_000 if short == '/deep/rules/' else 150_000 if re.match(r'/(teams/[a-z]+|news/\d{4}-\d\d)/$', short) else None
    if budget and size > budget:
        warn(f'{short}: {size // 1000}KB (budget {budget // 1000}KB)')

# the same original article on two indexable news pages
srcs = {}
for p in pages():
    short = url_of(p).replace(SITE, '')
    if not re.match(r'/news/[a-z]{2}-[a-z0-9-]+/$', short):
        continue
    h = open(p, encoding='utf-8', errors='replace').read()
    if re.search(r'<meta name="robots" content="[^"]*noindex', h):
        continue
    m = re.search(r'"isBasedOn": \{"@type": "NewsArticle", "url": "([^"]+)"', h)
    if m:
        k = re.sub(r'^http://', 'https://', m.group(1)).split('#')[0].rstrip('/').lower()
        srcs.setdefault(k, []).append(short)
for k, v in srcs.items():
    if len(v) > 1:
        err(f'duplicate source {k}: ' + ', '.join(v))

# one outlet under two names (owner's OK, 21 Nov 2026): add the variant to tools/source-names.json
try:
    names = json.load(open(os.path.join(ROOT, 'tools', 'source-names.json'), encoding='utf-8'))
    same, distinct = names.get('same', {}), {frozenset(x) for x in names.get('distinct', [])}
    shown = {same.get(a.get('source', ''), a.get('source', '')) for a in json.load(open(os.path.join(ROOT, 'news', 'archive.json'), encoding='utf-8'))['articles'].values()}
    keys = {}
    for n_ in shown:
        keys.setdefault(re.sub(r'\.(com|de|nl|it|net|co\.uk|fr|es|jp|com\.br)$', '', n_.lower().strip()), set()).add(n_)
    for v in keys.values():
        if len(v) > 1 and frozenset(v) not in distinct:
            warn('media name variants (one outlet?): ' + ' / '.join(sorted(v)))
except Exception as ex:
    warn(f'media names not checked ({ex})')

# sitemap
sm = open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read()
locs = re.findall(r'<loc>([^<]+)</loc>', sm)
seen = set()
for l in locs:
    if l in seen:
        err(f'sitemap: duplicate {l}')
    seen.add(l)
    f = os.path.join(ROOT, l.replace(SITE + '/', ''), 'index.html') if l.endswith('/') else os.path.join(ROOT, l.replace(SITE + '/', ''))
    if not os.path.exists(f):
        err(f'sitemap: {l} does not exist')
for u in sorted(indexable - seen):
    if not u.endswith('/404/'):
        err(f'sitemap: indexable page missing {u.replace(SITE, "")}')

if not quiet:
    for m in errors:
        print('ERROR', m)
    for m in warns[:200]:
        print('WARN ', m)
print(f'validate_site: {n} pages, {len(errors)} errors, {len(warns)} warnings')
sys.exit(1 if errors else 0)
