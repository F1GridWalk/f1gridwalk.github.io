#!/usr/bin/env python3
"""Tell Bing (and other IndexNow engines) about pages changed in the last N hours (owner's OK, 6 Nov 2026).
Reads sitemap.xml, picks <loc> whose <lastmod> is recent, POSTs them to api.indexnow.org.
Usage: python3 tools/indexnow.py [hours=26]. Never fails the run: prints the result and exits 0."""
import json, re, sys, os, urllib.request
from datetime import datetime, timedelta, timezone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = '6f17e54200bc9c1e7ff4e034731f8c97'
HOST = 'f1gridwalk.github.io'
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 26
try:
    sm = open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    urls = []
    for loc, lm in re.findall(r'<loc>(.*?)</loc><lastmod>(.*?)</lastmod>', sm):
        try:
            if datetime.fromisoformat(lm) >= since:
                urls.append(loc)
        except Exception:
            pass
    urls = list(dict.fromkeys(urls))[:10000]
    if not urls:
        print('indexnow: nothing new'); sys.exit(0)
    body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': f'https://{HOST}/{KEY}.txt', 'urlList': urls}).encode()
    req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body,
                                 headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f'indexnow: sent {len(urls)} urls, HTTP {r.status}')
except Exception as ex:
    print(f'indexnow: failed ({ex})')
sys.exit(0)
