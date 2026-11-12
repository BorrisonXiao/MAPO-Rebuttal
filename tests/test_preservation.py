"""Check exact copy/download data and that rendering preserves all response text."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
import zipfile

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
REVIEWERS = ('EAwd', 'zXPm', 'kaLY', 'TM2s')


class ResponseText(HTMLParser):
    def __init__(self, rendered_page=False):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.rendered_page = rendered_page
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag in ('meta', 'link', 'br', 'hr', 'img', 'input', 'wbr'):
            return
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        parent = self.stack[-1] if self.stack else (not self.rendered_page, False)
        inside = parent[0] or 'response-content' in classes
        skip = parent[1] or 'web-only' in classes or tag in ('script', 'style')
        self.stack.append((inside, skip))

    def handle_endtag(self, tag):
        if tag not in ('meta', 'link', 'br', 'hr', 'img', 'input', 'wbr') and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.stack and self.stack[-1][0] and not self.stack[-1][1]:
            self.text.append(data)

    def normalized(self):
        text = ''.join(self.text).replace('\\(', '$').replace('\\)', '$')
        return re.sub(r'\s+', '', text)


class SourcePreservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'site/index.html').read_text()
        match = re.search(r'<script id="response-sources" type="application/json">(.*?)</script>', cls.html, re.S)
        cls.payload = json.loads(match.group(1))
        cls.manifest = json.loads((ROOT / 'site/source-manifest.json').read_text())

    def test_downloads_and_copy_payloads_are_exact(self):
        with zipfile.ZipFile(ROOT / 'site/responses.zip') as archive:
            self.assertEqual(set(archive.namelist()), {f'{r}.md' for r in REVIEWERS})
            for reviewer in REVIEWERS:
                with self.subTest(reviewer=reviewer):
                    raw = (ROOT / 'responses' / f'{reviewer}.md').read_bytes()
                    self.assertEqual(raw, (ROOT / 'site/responses' / f'{reviewer}.md').read_bytes())
                    self.assertEqual(raw, archive.read(f'{reviewer}.md'))
                    self.assertEqual(raw, self.payload[reviewer]['markdown'].encode('utf-8'))
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), self.manifest[f'{reviewer}.md']['sha256'])
                    self.assertEqual(len(raw), self.manifest[f'{reviewer}.md']['bytes'])

    def test_point_copy_preserves_source_slices(self):
        for reviewer in REVIEWERS:
            source = self.payload[reviewer]['markdown']
            start = re.search(r'^\*\*1\.', source, re.M).start()
            self.assertEqual(source[start:], ''.join(self.payload[reviewer]['points'].values()))

    def test_rendering_keeps_all_response_text_in_order(self):
        actual = ResponseText(rendered_page=True)
        actual.feed(self.html)
        expected = ResponseText()
        markdown = MarkdownIt('commonmark', {'html': False, 'typographer': False}).enable('table')
        for reviewer in REVIEWERS:
            expected.feed(markdown.render(self.payload[reviewer]['markdown']))
        self.assertEqual(expected.normalized(), actual.normalized())

    def test_reader_structure(self):
        self.assertEqual(len(re.findall(r'<article class="reviewer"', self.html)), 4)
        self.assertEqual(len(re.findall(r'<section class="response-point"', self.html)), 19)
        self.assertEqual(self.html.count('<table>'), 10)
        self.assertEqual(self.html.count('<caption class="sr-only web-only">'), 10)
        self.assertNotIn('https://cdn.', self.html)
        self.assertIn('vendor/mathjax/tex-svg.js', self.html)
        self.assertEqual(self.html.count('class="math"'), 2)
        self.assertTrue((ROOT / 'site/vendor/mathjax/tex-svg.js').is_file())


if __name__ == '__main__':
    unittest.main()
