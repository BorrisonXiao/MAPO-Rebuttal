#!/usr/bin/env python3
"""Export editable LaTeX responses and an Overleaf upload archive."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import zipfile

from markdown_it import MarkdownIt

from build import REVIEWERS, inline_math

ROOT = Path(__file__).resolve().parent
ESCAPES = {
    '\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
    'η': r'\ensuremath{\eta}', 'λ': r'\ensuremath{\lambda}',
    '±': r'\ensuremath{\pm}', '–': r'\textendash{}',
}


def escape(text):
    return ''.join(ESCAPES.get(char, char) for char in text)


def render_inline(tokens):
    result = []
    for token in tokens:
        if token.type == 'text':
            result.append(escape(token.content))
        elif token.type == 'math_inline':
            result.append('$' + token.content + '$')
        elif token.type in ('strong_open', 'em_open'):
            result.append(r'\textbf{' if token.type == 'strong_open' else r'\emph{')
        elif token.type in ('strong_close', 'em_close'):
            result.append('}')
        elif token.type == 'code_inline':
            result.append(r'\texttt{' + escape(token.content) + '}')
        elif token.type == 'softbreak':
            result.append('\n')
        elif token.type == 'hardbreak':
            result.append('\\\\\n')
        else:
            raise ValueError(f'Unhandled inline token: {token.type}')
    return ''.join(result)


def render_table(tokens):
    rows, row = [], None
    for token in tokens:
        if token.type == 'tr_open':
            row = []
        elif token.type == 'inline':
            row.append(render_inline(token.children or []))
        elif token.type == 'tr_close':
            rows.append(row)
    columns = len(rows[0])
    if not all(len(row) == columns for row in rows):
        raise ValueError('Inconsistent table column count')
    result = [r'\par\medskip', r'\begingroup', r'\small',
              r'\setlength{\tabcolsep}{5pt}', r'\renewcommand{\arraystretch}{1.2}',
              r'\noindent\begin{tabularx}{\linewidth}{@{}' + 'L' + 'R' * (columns - 1) + r'@{}}',
              r'\toprule']
    for index, row in enumerate(rows):
        if index == 0:
            row = [r'\textbf{' + cell + '}' for cell in row]
        result.append(' & '.join(row) + r' \\')
        if index == 0:
            result.append(r'\midrule')
    result.extend([r'\bottomrule', r'\end{tabularx}', r'\par\endgroup\medskip', ''])
    return '\n'.join(result)


def convert(source):
    md = MarkdownIt('commonmark', {'html': False, 'typographer': False}).enable('table')
    md.inline.ruler.before('escape', 'math_inline', inline_math)
    tokens = md.parse(source)
    result, index = [], 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == 'paragraph_open':
            inline = tokens[index + 1]
            assert inline.type == 'inline' and tokens[index + 2].type == 'paragraph_close'
            children = inline.children or []
            if re.fullmatch(r'\*\*\d+\..+\*\*', inline.content):
                heading = md.parseInline(inline.content[2:-2])[0].children or []
                result.append(r'\subsection*{' + render_inline(heading) + '}\n')
            else:
                result.append(render_inline(children) + '\n')
            index += 3
        elif token.type == 'blockquote_open':
            result.append(r'\begin{quote}\small\color{ReviewQuote}')
            index += 1
        elif token.type == 'blockquote_close':
            result.append('\\end{quote}\n')
            index += 1
        elif token.type == 'table_open':
            end = index + 1
            while tokens[end].type != 'table_close':
                end += 1
            result.append(render_table(tokens[index:end + 1]))
            index = end + 1
        else:
            raise ValueError(f'Unhandled block token: {token.type}')
    return '\n'.join(result).rstrip() + '\n'


PREAMBLE = r'''% Overleaf main document. Compile with pdfLaTeX (the default).
\documentclass[11pt,a4paper]{article}
\usepackage[margin=0.8in]{geometry}
\usepackage{cmap}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb}
\usepackage{microtype}
\usepackage{array,tabularx,booktabs}
\usepackage{xcolor}
\usepackage{titlesec}
\usepackage{hyperref}
\definecolor{ReviewQuote}{HTML}{4B5563}
\definecolor{LinkBlue}{HTML}{225C94}
\hypersetup{colorlinks=true,linkcolor=LinkBlue,urlcolor=LinkBlue,
  pdftitle={MAPO rebuttal drafts},pdfauthor={}}
\newcolumntype{L}{>{\raggedright\arraybackslash}X}
\newcolumntype{R}{>{\raggedleft\arraybackslash}X}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.65em}
\setlength{\emergencystretch}{3em}
\titleformat{\section}{\Large\bfseries}{}{0pt}{}
\titleformat{\subsection}{\normalsize\bfseries}{}{0pt}{}
\titlespacing*{\subsection}{0pt}{1.5em}{0.7em}
\begin{document}
'''

README = '''# MAPO rebuttal: editable Overleaf project

Upload `mapo-rebuttal-overleaf.zip` using Overleaf's **New Project → Upload
Project**, then open `main.tex` and compile with **pdfLaTeX** (the default).

Edit one reviewer file at a time:

- `responses/EAwd.tex`
- `responses/zXPm.tex`
- `responses/kaLY.tex`
- `responses/TM2s.tex`

`main.tex` includes these four files in reviewer order. Each reviewer begins on
a new page. Tables, quotations, emphasis, and mathematical notation are ordinary
LaTeX, so this project needs no Markdown conversion step or shell escape in
Overleaf. All required packages are part of Overleaf's standard TeX installation.

The response wording and numerical values are unchanged from the Markdown
originals included in `markdown/`. Conversion changes only formatting and the
escaping required by LaTeX. `source-manifest.json` records the originals' hashes.
The reviewer labels in `main.tex` are document navigation, outside the responses.

Edit the `.tex` files directly in Overleaf. The Markdown files are reference
copies and do not automatically synchronize with subsequent LaTeX edits.
'''


def build_overleaf():
    project = ROOT / 'overleaf'
    (project / 'responses').mkdir(parents=True, exist_ok=True)
    (project / 'markdown').mkdir(exist_ok=True)
    manifest, sections = {}, []
    files = [project / 'main.tex', project / 'README.md', project / 'source-manifest.json']
    for reviewer in REVIEWERS:
        original = (ROOT / 'responses' / f'{reviewer}.md').read_bytes()
        tex = project / 'responses' / f'{reviewer}.tex'
        markdown = project / 'markdown' / f'{reviewer}.md'
        tex.write_text(convert(original.decode('utf-8')), encoding='utf-8')
        markdown.write_bytes(original)
        files.extend([tex, markdown])
        manifest[f'{reviewer}.md'] = {'sha256': hashlib.sha256(original).hexdigest(), 'bytes': len(original)}
        sections.append(r'\pdfbookmark[0]{Reviewer ' + reviewer + '}{reviewer-' + reviewer + '}\n'
                        + r'\section*{Reviewer ' + reviewer + '}\n'
                        + r'\input{responses/' + reviewer + '}\n')
    (project / 'main.tex').write_text(PREAMBLE + '\n\\clearpage\n\n'.join(sections) + '\n\\end{document}\n', encoding='utf-8')
    (project / 'README.md').write_text(README, encoding='utf-8')
    (project / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    site = ROOT / 'site'
    site.mkdir(exist_ok=True)
    archive_path = site / 'mapo-rebuttal-overleaf.zip'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(path.relative_to(project).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    print(f'Built {archive_path.relative_to(ROOT)}: main.tex, four editable reviewer files, and original Markdown.')


if __name__ == '__main__':
    build_overleaf()
