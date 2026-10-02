#!/usr/bin/env python3
"""
Builds two single-file versions of the site into website/dist/:

  Growth-and-Beyond-Website.html   standalone page (double-click to open, no server needed)
  homepage-for-wordpress.html      paste-in block for a WordPress page (Elementor HTML widget).
                                   All CSS is scoped under #gb-site so theme / Elementor styles
                                   can't override it, and the content breaks out to full width.

Usage:  python3 website/tools/build-embeds.py
"""
import base64
import os
import re

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(W, 'dist')


def read(path):
    with open(os.path.join(W, path), encoding='utf-8') as f:
        return f.read()


def b64(path):
    with open(os.path.join(W, path), 'rb') as f:
        return base64.b64encode(f.read()).decode()


def inline_fonts(css):
    css = re.sub(r'url\("\.\./(assets/fonts/[^"]+\.woff2)"\) format\("woff2"\)',
                 lambda m: f'url("data:font/woff2;base64,{b64(m.group(1))}") format("woff2")', css)
    assert 'assets/fonts' not in css
    return css


def check_script(js):
    assert '</script' not in js.lower(), 'script contains a closing tag'
    return js


# ---------- scoping for WordPress ----------
SCOPE = '#gb-site'


def scope_selector(sel):
    sel = sel.strip()
    if sel == ':root':
        return f':root, {SCOPE}'
    first, _, rest = sel.partition(' ')
    if re.match(r'^(html|body|\.js)\b', first):
        return sel if not rest else f'{first} {SCOPE} {rest}'
    return f'{SCOPE} {sel}'


def scope_css(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out, i, n = [], 0, len(css)

    def block_end(start):
        depth = 0
        for j in range(start, n):
            if css[j] == '{':
                depth += 1
            elif css[j] == '}':
                depth -= 1
                if depth == 0:
                    return j
        raise ValueError('unbalanced braces')

    while i < n:
        brace = css.find('{', i)
        close = css.find('}', i)
        if brace == -1 or (close != -1 and close < brace):
            out.append(css[i:close + 1] if close != -1 else css[i:])
            i = close + 1 if close != -1 else n
            continue
        head = css[i:brace].strip()
        if head.startswith('@media') or head.startswith('@supports'):
            out.append(head + ' {')
            i = brace + 1
            continue
        end = block_end(brace)
        if head.startswith('@'):
            out.append(css[i:end + 1])
        else:
            sels = ', '.join(scope_selector(s) for s in head.split(','))
            out.append(sels + ' ' + css[brace:end + 1])
        i = end + 1
    return '\n'.join(out)


WP_EXTRA = f"""
{SCOPE} {{
  position: relative;
  width: 100vw;
  max-width: 100vw;
  margin-left: calc(50% - 50vw);
  margin-right: calc(50% - 50vw);
  background: #061430;
  color: #f2f6fc;
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.7;
  text-align: left;
}}
/* theme / Elementor kit styles colour headings and text directly; keep ours */
{SCOPE} h1, {SCOPE} h2, {SCOPE} h3, {SCOPE} h4, {SCOPE} p, {SCOPE} li, {SCOPE} span, {SCOPE} small,
{SCOPE} strong, {SCOPE} em, {SCOPE} b, {SCOPE} blockquote, {SCOPE} figcaption, {SCOPE} label {{ color: inherit; }}
{SCOPE} h1, {SCOPE} h2, {SCOPE} h3, {SCOPE} h4 {{ text-transform: none; }}
body.admin-bar {SCOPE} .site-header, body.admin-bar {SCOPE} .scroll-progress {{ top: 32px; }}
@media (max-width: 782px) {{
  body.admin-bar {SCOPE} .site-header, body.admin-bar {SCOPE} .scroll-progress {{ top: 46px; }}
}}
"""


def body_content(html):
    start = html.index('<a class="skip-link"')
    end = html.index('  <script src="js/main.js"')
    return html[start:end].rstrip()


def main():
    os.makedirs(DIST, exist_ok=True)
    html = read('index.html')
    css = inline_fonts(read('css/styles.css'))
    main_js = check_script(read('js/main.js'))
    globe_js = check_script(read('js/hero-globe.js'))

    # 1) standalone single file
    page = html
    page = page.replace('  <link rel="stylesheet" href="css/styles.css">', '  <style>\n' + css + '\n  </style>')
    page = re.sub(r'  <link rel="preload" href="assets/fonts/[^"]+" as="font" type="font/woff2" crossorigin>\n', '', page)
    page = page.replace('<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">',
                        f'<link rel="icon" href="data:image/svg+xml;base64,{b64("assets/favicon.svg")}" type="image/svg+xml">')
    page = page.replace('<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">',
                        f'<link rel="apple-touch-icon" href="data:image/png;base64,{b64("assets/apple-touch-icon.png")}">')
    page = page.replace('  <script src="js/main.js" defer></script>', '  <script>\n' + main_js + '\n  </script>')
    page = page.replace('  <script type="module" src="js/hero-globe.js"></script>', '  <script type="module">\n' + globe_js + '\n  </script>')
    with open(os.path.join(DIST, 'Growth-and-Beyond-Website.html'), 'w', encoding='utf-8') as f:
        f.write(page)

    # 2) WordPress paste-in block
    ld = re.search(r'<script type="application/ld\+json">.*?</script>', html, flags=re.S).group(0)
    wp = '\n'.join([
        '<!-- Growth & Beyond homepage. Paste this whole file into ONE Elementor "HTML" widget on a page set to "Elementor Canvas". -->',
        "<script>document.documentElement.classList.add('js');</script>",
        '<style>\n' + scope_css(css) + WP_EXTRA + '</style>',
        ld,
        f'<div id="{SCOPE[1:]}">',
        body_content(html),
        '</div>',
        '<script>\n' + main_js + '\n</script>',
        '<script type="module">\n' + globe_js + '\n</script>',
        '',
    ])
    with open(os.path.join(DIST, 'homepage-for-wordpress.html'), 'w', encoding='utf-8') as f:
        f.write(wp)

    for name in sorted(os.listdir(DIST)):
        print(f'{name}: {os.path.getsize(os.path.join(DIST, name)) // 1024} KB')


if __name__ == '__main__':
    main()
