#!/usr/bin/env python3
"""Render the original reviewer responses without editing their Markdown."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import zipfile

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
REVIEWERS = ('EAwd', 'zXPm', 'kaLY', 'TM2s')
POINT = re.compile(r'^\*\*(\d+\..+?)\*\*[ \t]*$', re.M)


def inline_math(state, silent):
    """Render dollar-delimited TeX without changing the saved source."""
    start = state.pos
    if state.src[start] != '$' or state.src.startswith('$$', start):
        return False
    end = state.src.find('$', start + 1)
    if end < 0 or '\n' in state.src[start + 1:end]:
        return False
    if not silent:
        token = state.push('math_inline', '', 0)
        token.content = state.src[start + 1:end]
    state.pos = end + 1
    return True


def render_math(tokens, idx, options, env):
    tex = html.escape(tokens[idx].content, quote=True)
    return f'<span class="math" data-tex="{tex}">\\({tex}\\)</span>'


def safe_json(data):
    return json.dumps(data, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')


def split_response(source):
    points = list(POINT.finditer(source))
    if not points:
        raise ValueError('Expected numbered, bold point headings')
    result = []
    for i, match in enumerate(points):
        end = points[i + 1].start() if i + 1 < len(points) else len(source)
        result.append((match.group(1), source[match.start():end], source[match.end():end]))
    assert source[:points[0].start()] + ''.join(p[1] for p in result) == source
    return source[:points[0].start()], result


def build(source_dir=None):
    sources = ROOT / 'responses'
    if source_dir:
        source_dir = Path(source_dir)
        # Copy bytes, including line endings and trailing whitespace.
        for reviewer in REVIEWERS:
            original = (source_dir / f'{reviewer}.md').read_bytes()
            (sources / f'{reviewer}.md').write_bytes(original)
    site = ROOT / 'site'
    site.mkdir(exist_ok=True)
    (site / 'responses').mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'vendor', site / 'vendor', dirs_exist_ok=True)
    (site / '.nojekyll').write_text('')

    md = MarkdownIt('commonmark', {'html': False, 'typographer': False}).enable('table')
    md.inline.ruler.before('escape', 'math_inline', inline_math)
    md.renderer.rules['math_inline'] = render_math
    payload, manifest, nav, articles = {}, {}, [], []
    table_number = 0

    for reviewer in REVIEWERS:
        raw = (sources / f'{reviewer}.md').read_bytes()
        source = raw.decode('utf-8')
        (site / 'responses' / f'{reviewer}.md').write_bytes(raw)
        manifest[f'{reviewer}.md'] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        intro, points = split_response(source)
        payload[reviewer] = {'markdown': source, 'points': {}}
        links, rendered_points = [], []

        def render(markdown, label):
            nonlocal table_number
            rendered = md.render(markdown)
            def table(match):
                nonlocal table_number
                table_number += 1
                caption = html.escape(f'Table {table_number}. {reviewer}, {label}')
                return f'<div class="table-scroll" role="region" aria-label="{caption}" tabindex="0"><table><caption class="sr-only web-only">{caption}</caption>'
            rendered = re.sub(r'<table>', table, rendered)
            return rendered.replace('</table>', '</table></div>')

        for title, exact_point, body in points:
            number = title.split('.', 1)[0]
            point_id = f'{reviewer}-{number}'
            payload[reviewer]['points'][number] = exact_point
            links.append(f'<li><a href="#{point_id}">{html.escape(title)}</a></li>')
            rendered_points.append(f'''<section class="response-point" id="{point_id}">
<div class="point-heading"><h3>{html.escape(title)}</h3><button class="copy-button web-only" data-copy="{reviewer}" data-point="{number}" aria-label="Copy Markdown for {reviewer}, point {number}">Copy point</button></div>
{render(body, title)}</section>''')

        nav.append(f'''<details open><summary><a href="#{reviewer}">{reviewer}</a><span>{len(points)} points</span></summary><ol>{''.join(links)}</ol></details>''')
        articles.append(f'''<article class="reviewer" id="{reviewer}" aria-labelledby="label-{reviewer}">
<header class="reviewer-header"><div><p class="eyebrow">Reviewer</p><h2 id="label-{reviewer}">{reviewer}</h2></div>
<div class="reviewer-actions"><button class="copy-button primary" data-copy="{reviewer}">Copy Markdown</button><a class="button" href="responses/{reviewer}.md" download>Download .md</a></div></header>
<div class="response-content">{render(intro, 'opening')}{''.join(rendered_points)}</div></article>''')

    with zipfile.ZipFile(site / 'responses.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for reviewer in REVIEWERS:
            info = zipfile.ZipInfo(f'{reviewer}.md', date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (sources / f'{reviewer}.md').read_bytes())
    (site / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    css = '\n'.join((ROOT / 'assets' / name).read_text() for name in ('theme.css', 'viewer.css'))
    js = (ROOT / 'assets' / 'viewer.js').read_text()
    document = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="MAPO rebuttal drafts, rendered from the original Markdown with exact-source copying and downloads.">
<meta name="color-scheme" content="light dark">
<title>MAPO · Rebuttal drafts</title>
<style>{css}</style>
<script>try {{ const theme = localStorage.getItem('mapo-theme'); if (theme) document.documentElement.dataset.theme = theme; }} catch (_) {{}}</script>
<script>window.MathJax = {{tex: {{inlineMath: [['\\\\(', '\\\\)']], displayMath: [['\\\\[', '\\\\]']]}}, svg: {{fontCache: 'global'}}, options: {{skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']}}}};</script>
<script id="MathJax-script" defer src="vendor/mathjax/tex-svg.js"></script>
</head>
<body>
<a class="skip-link" href="#main">Skip to responses</a>
<div class="layout">
<aside class="sidebar" aria-label="Response navigation">
<a class="brand" href="#top">MAPO<span>Rebuttal drafts</span></a>
<nav aria-label="Reviewers and points">{''.join(nav)}</nav>
<div class="sidebar-footer"><a href="mapo-rebuttal-overleaf.zip" download>Download Overleaf project ↓</a><a href="responses.zip" download>Download all Markdown ↓</a><a href="https://github.com/BorrisonXiao/MAPO-Rebuttal">View repository ↗</a><button id="theme-toggle" type="button">Switch theme</button></div>
</aside>
<main id="main">
<header class="page-header" id="top"><p class="eyebrow">Collaborator reading copy</p><h1>MAPO rebuttal drafts</h1><p>Four reviewer responses, with tables and equations rendered for reading. <strong>Copy Markdown</strong> copies the original text, ready to paste into OpenReview.</p><div class="reviewer-actions page-downloads"><a class="button" href="mapo-rebuttal-overleaf.zip" download>Download Overleaf project (.zip)</a></div><div class="mobile-reviewers" aria-label="Jump to reviewer">{''.join(f'<a href="#{r}">{r}</a>' for r in REVIEWERS)}</div></header>
{''.join(articles)}
<footer class="page-footer">Rendered from the original Markdown without content edits. <a href="source-manifest.json">Source checksums</a> · <a href="#top">Back to top ↑</a></footer>
</main>
</div>
<div id="copy-status" role="status" aria-live="polite" class="toast" hidden></div>
<dialog id="copy-fallback"><form method="dialog"><h2>Copy Markdown</h2><p>Your browser could not access the clipboard. Select and copy the original text below.</p><textarea aria-label="Original Markdown" spellcheck="false"></textarea><div><button type="button" id="select-fallback">Select all</button><button type="submit">Close</button></div></form></dialog>
<script id="response-sources" type="application/json">{safe_json(payload)}</script>
<script>{js}</script>
</body>
</html>
'''
    (site / 'index.html').write_text(document, encoding='utf-8')
    from build_overleaf import build_overleaf
    build_overleaf()
    print(f'Built site/index.html: {len(REVIEWERS)} reviewers, {sum(len(v["points"]) for v in payload.values())} points, {table_number} tables. Original Markdown preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, help='Optional directory of original reviewer Markdown to snapshot before building')
    build(parser.parse_args().source_dir)
