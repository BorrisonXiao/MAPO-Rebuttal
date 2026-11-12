"""Verify the upload archive and all text in the Markdown-to-LaTeX conversion."""
import json
from pathlib import Path
import re
import unittest
import zipfile

from markdown_it import MarkdownIt

from build import REVIEWERS, inline_math
from build_overleaf import escape

ROOT = Path(__file__).resolve().parents[1]


def visible_inline(tex):
    """Read the small generated LaTeX subset independently of its renderer."""
    symbols = {'eta': 'η', 'lambda': 'λ', 'pm': '±', 'textendash': '–',
               'textbackslash': '\\', 'textasciitilde': '~', 'textasciicircum': '^'}
    wrappers = {'textbf', 'emph', 'texttt', 'subsection*', 'ensuremath'}
    result, i = [], 0
    while i < len(tex):
        char = tex[i]
        if char == '\\':
            match = re.match(r'\\([A-Za-z]+\*?|.)', tex[i:])
            if not match:
                raise ValueError('Incomplete LaTeX escape')
            name = match.group(1)
            i += len(match.group(0))
            if name in symbols:
                result.append(symbols[name])
            elif name in wrappers:
                pass
            elif name in '&%$#_{}':
                result.append(name)
            elif name == '\\':
                result.append(' ')
            else:
                raise ValueError(f'Unhandled LaTeX command: {name}')
        elif char in '{}$':
            i += 1
        elif char == '&':
            result.append(' ')
            i += 1
        else:
            result.append(char)
            i += 1
    return ''.join(result)


def visible_document(tex):
    layout_prefixes = (
        r'\par\medskip', r'\begingroup', r'\small', r'\setlength{',
        r'\renewcommand{', r'\noindent\begin{tabularx}', r'\toprule',
        r'\midrule', r'\bottomrule', r'\end{tabularx}', r'\par\endgroup',
        r'\begin{quote}', r'\end{quote}',
    )
    text = '\n'.join(line for line in tex.splitlines() if not line.startswith(layout_prefixes))
    return re.sub(r'\s+', '', visible_inline(text))


def visible_markdown(source):
    md = MarkdownIt('commonmark', {'html': False, 'typographer': False}).enable('table')
    md.inline.ruler.before('escape', 'math_inline', inline_math)
    text = []
    for token in md.parse(source):
        for child in token.children or []:
            if child.type in ('text', 'code_inline'):
                text.append(child.content)
            elif child.type == 'math_inline':
                text.append(child.content.replace(r'\eta', 'η'))
    return re.sub(r'\s+', '', ''.join(text))


class OverleafProject(unittest.TestCase):
    def test_escaped_characters_keep_their_text(self):
        original = r'\ & % $ # _ { } ~ ^ η λ ± –'
        self.assertEqual(original, visible_inline(escape(original)))

    def test_latex_preserves_each_reviewers_text_and_numbers(self):
        for reviewer in REVIEWERS:
            with self.subTest(reviewer=reviewer):
                source = (ROOT / 'responses' / f'{reviewer}.md').read_text()
                tex = (ROOT / 'overleaf/responses' / f'{reviewer}.tex').read_text()
                self.assertEqual(visible_markdown(source), visible_document(tex))

    def test_archive_is_complete_and_preserves_originals(self):
        expected = {'main.tex', 'README.md', 'source-manifest.json'}
        expected.update(f'{folder}/{r}.{ext}' for r in REVIEWERS for folder, ext in [('responses', 'tex'), ('markdown', 'md')])
        with zipfile.ZipFile(ROOT / 'site/mapo-rebuttal-overleaf.zip') as archive:
            self.assertEqual(set(archive.namelist()), expected)
            self.assertIsNone(archive.testzip())
            for name in expected:
                self.assertEqual(archive.read(name), (ROOT / 'overleaf' / name).read_bytes())
            for reviewer in REVIEWERS:
                self.assertEqual(archive.read(f'markdown/{reviewer}.md'), (ROOT / 'responses' / f'{reviewer}.md').read_bytes())
            main = archive.read('main.tex').decode()
            for reviewer in REVIEWERS:
                self.assertIn(r'\input{responses/' + reviewer + '}', main)
            self.assertEqual(json.loads(archive.read('source-manifest.json')), json.loads((ROOT / 'site/source-manifest.json').read_text()))


if __name__ == '__main__':
    unittest.main()
