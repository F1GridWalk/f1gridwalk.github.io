#!/usr/bin/env python3
"""Turn the data desk's race-analysis page (one self-contained HTML, Artifact) into the fragment build.py wraps as
/gp/<slug>/data/ (owner's OK to preview, 24 Nov 2026).

Usage: python3 tools/gpdata_import.py <artifact.html> <gp-slug>      -> writes gpdata/<gp-slug>.html
What it does: keeps the page's own markup and script; drops its <head>, title, fonts and the LAB label; moves the colour
tokens the site already has to the site's own; scopes every CSS rule under .gd so nothing leaks into the site's styles.
"""
import os, re, sys

src, slug = sys.argv[1], sys.argv[2]
h = open(src, encoding='utf-8').read()
h = h.split('<body>', 1)[-1]
styles = re.findall(r'<style>(.*?)</style>', h, re.S)
css = max(styles, key=len)
i = h.index(css) + len(css) + len('</style>')
j = h.index('<script>', i)
markup = h[i:j].strip()
script = h[j:h.rindex('</script>') + len('</script>')]

SITE_TOKENS = {'paper', 'surface', 'line', 'ink', 'muted', 'clay', 'sans', 'logo'}
root = re.search(r':root\{(.*?)\}', css, re.S).group(1)
own = ';'.join(d for d in root.split(';') if d.strip() and d.split(':', 1)[0].strip().lstrip('-') not in SITE_TOKENS)
dark = re.search(r':root\[data-theme="dark"\]\{(.*?)\}', css, re.S).group(1)
own_dark = ';'.join(d for d in dark.split(';') if d.strip().startswith('--') and d.split(':', 1)[0].strip().lstrip('-') not in SITE_TOKENS)
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
css = re.sub(r':root\{.*?\}', '', css, count=1, flags=re.S)
css = re.sub(r'@media \(prefers-color-scheme:dark\)\{:root:not\(\[data-theme="light"\]\)\{.*?\}\}', '', css, flags=re.S)
css = re.sub(r':root\[data-theme="dark"\]\{.*?\}', '', css, flags=re.S)
css = re.sub(r'(^|\})\s*body(::before)?\{[^}]*\}', r'\1', css)
def scope(block):
    """Scope plain rules under .gd; keep @media / @keyframes blocks, scoping the rules inside @media (V14 brought these)."""
    res, k = [], 0
    while True:
        o = block.find('{', k)
        if o < 0:
            return res
        sel = block[k:o].strip()
        depth, m = 1, o + 1
        while depth:
            depth += {'{': 1, '}': -1}.get(block[m], 0)
            m += 1
        body = block[o + 1:m - 1]
        if sel.startswith('@media'):
            res.append(sel + '{' + ''.join(scope(body)) + '}')
        elif sel.startswith('@'):
            res.append(sel + '{' + body + '}')
        elif sel:
            res.append(','.join('.gd ' + x.strip().replace('.wrap', '.gdw') for x in sel.split(',')) + '{' + body.strip() + '}')
        k = m


out = scope(css)
# the page's own colours live on :root, because its script reads them from the root element (this style is on this page only)
scoped = (':root{' + own + '}.gd{font-size:15px;line-height:1.65}'
          '@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){' + own_dark + '}}'
          ':root[data-theme="dark"]{' + own_dark + '}' + ''.join(out)
          + '.gd .bar{top:0;margin-top:6px}.gd h1{margin-top:4px}.gd section{margin-top:26px;padding-top:16px}.gd .bar+section{border-top:0;padding-top:0}.gd .legend svg{width:26px;display:inline-block}'
          '.gd .qa li{border:0;border-bottom:1px solid var(--line);border-radius:0;margin:0;padding:5px 0;font-size:13px;color:var(--ink)}')  # the site's own .warn box would wrap the data-quality rows (26 Nov 2026)
markup = re.sub(r'<span class="lab">.*?</span>\s*', '', markup, flags=re.S)
markup = markup.replace('<div class="wrap">', '<div class="gdw">', 1)  # the site already has a .wrap
markup = markup.replace('この試作は本サイトには載っていません。', 'ファンによる非営利の分析です。')
os.makedirs('gpdata', exist_ok=True)
open(f'gpdata/{slug}.html', 'w', encoding='utf-8').write(
    f'<!-- gpdata/{slug}.html: the race-analysis page from the data desk, imported by tools/gpdata_import.py -->\n'
    f'<style>{scoped}</style>\n<div class="gd">{markup}</div>\n{script}\n')
print('wrote', f'gpdata/{slug}.html', len(scoped), 'css', len(markup), 'markup', len(script), 'script')
