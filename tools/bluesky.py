#!/usr/bin/env python3
"""Post the day's new columns and STORY to Bluesky (owner's OK, 20 Nov 2026).

Needs two secret values in the environment (the owner sets them; the password is an *app password*,
made in Bluesky's settings, never the account password):
  BSKY_HANDLE        e.g. f1gridwalk.bsky.social
  BSKY_APP_PASSWORD  the app password
Without them it does nothing. Never fails the run: prints the result and exits 0.

Picks /lens/ and /topics/ pages whose <lastmod> in sitemap.xml is within the last N hours (default 26),
skips any already in tools/bluesky-posted.json, posts at most MAX of them (newest first) with a link card,
and adds them to that file (commit it with the rest of the run).
Usage: python3 tools/bluesky.py [hours=26]
"""
import json, os, re, sys, html, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://f1gridwalk.github.io'
PDS = 'https://bsky.social/xrpc/'
MAX = 3
LOG = os.path.join(ROOT, 'tools', 'bluesky-posted.json')


def call(method, data=None, token=None, raw=None, ctype='application/json'):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(PDS + method, data=body, method='POST' if body is not None else 'GET',
                                 headers={'Content-Type': ctype, **({'Authorization': 'Bearer ' + token} if token else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def meta(path):
    """Title, description and og image of a built page."""
    f = os.path.join(ROOT, path.strip('/'), 'index.html')
    h = open(f, encoding='utf-8').read()
    g = lambda pat: html.unescape((re.search(pat, h) or [None, ''])[1])
    title = re.sub(r'｜F1グリッドウォーク$', '', g(r'<title>([^<]*)</title>'))
    title = re.sub(r'｜[^｜]*$', '', title) if title.count('｜') >= 2 else title
    return title, g(r'<meta name="description" content="([^"]*)"'), g(r'<meta property="og:image" content="([^"]*)"')


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 26
    handle, pw = os.environ.get('BSKY_HANDLE'), os.environ.get('BSKY_APP_PASSWORD')
    if not handle or not pw:
        print('bluesky: no BSKY_HANDLE / BSKY_APP_PASSWORD, skipped'); return
    sm = open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    new = []
    for loc, lm in re.findall(r'<loc>(.*?)</loc><lastmod>(.*?)</lastmod>', sm):
        if re.match(re.escape(SITE) + r'/(lens|topics)/[^/]+/$', loc):
            try:
                if datetime.fromisoformat(lm) >= since:
                    new.append((lm, loc))
            except Exception:
                pass
    done = json.load(open(LOG)) if os.path.exists(LOG) else []
    todo = [loc for lm, loc in sorted(new, reverse=True) if loc not in done][:MAX]
    if not todo:
        print('bluesky: nothing new'); return
    s = call('com.atproto.server.createSession', {'identifier': handle, 'password': pw})
    tok, did = s['accessJwt'], s['did']
    posted = 0
    for loc in todo:
        try:
            title, desc, img = meta(loc.replace(SITE, ''))
            kind = 'STORY' if '/topics/' in loc else 'コラム'
            text = f'【{kind}】{title}'[:280]
            ext = {'uri': loc, 'title': title[:300], 'description': desc[:300]}
            if img:
                try:
                    p = os.path.join(ROOT, re.sub(r'\?.*$', '', img).replace(SITE + '/', ''))
                    data = open(p, 'rb').read()
                    if len(data) < 950_000:
                        ext['thumb'] = call('com.atproto.repo.uploadBlob', token=tok, raw=data, ctype='image/png')['blob']
                except Exception:
                    pass
            rec = {'$type': 'app.bsky.feed.post', 'text': text, 'langs': ['ja'],
                   'createdAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                   'embed': {'$type': 'app.bsky.embed.external', 'external': ext}}
            call('com.atproto.repo.createRecord', {'repo': did, 'collection': 'app.bsky.feed.post', 'record': rec}, token=tok)
            done.append(loc)
            posted += 1
        except Exception as ex:
            print(f'bluesky: failed on {loc} ({ex})')
    json.dump(done[-500:], open(LOG, 'w'), ensure_ascii=False, indent=0)
    print(f'bluesky: posted {posted} of {len(todo)}')


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        print(f'bluesky: failed ({ex})')
