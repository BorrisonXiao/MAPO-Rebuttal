"""Optional end-to-end check: pip install playwright; playwright install chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'test-artifacts'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'site')))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_address[1]}'
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'], timeout=25000)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, permissions=['clipboard-read', 'clipboard-write'], reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(url, wait_until='networkidle')
            page.wait_for_function("window.MathJax && MathJax.startup && MathJax.startup.document && document.querySelectorAll('mjx-container').length === 2")
            assert page.locator('table').count() == 10
            assert page.locator('article.reviewer').count() == 4
            page.screenshot(path=str(ARTIFACTS / 'desktop.png'))
            for reviewer in ('EAwd', 'zXPm', 'kaLY', 'TM2s'):
                button = page.locator(f'.reviewer-header button[data-copy="{reviewer}"]')
                button.click()
                expected = (ROOT / 'responses' / f'{reviewer}.md').read_text()
                assert page.evaluate('navigator.clipboard.readText()') == expected, reviewer
            for button in page.locator('button[data-point]').all():
                reviewer, point = button.get_attribute('data-copy'), button.get_attribute('data-point')
                button.click()
                expected = page.evaluate('([r,p]) => JSON.parse(document.getElementById("response-sources").textContent)[r].points[p]', [reviewer, point])
                assert page.evaluate('navigator.clipboard.readText()') == expected, (reviewer, point)
            page.locator('#theme-toggle').click()
            assert page.locator('html').get_attribute('data-theme') in ('light', 'dark')
            page.locator('#EAwd').scroll_into_view_if_needed()
            page.screenshot(path=str(ARTIFACTS / 'desktop-theme.png'))
            # Explicitly force a clipboard failure, exercising local-file/restricted-browser behavior.
            page.evaluate("Object.defineProperty(navigator.clipboard, 'writeText', {value: async () => {throw new Error('Clipboard denied');}})")
            page.locator('.reviewer-header button[data-copy="EAwd"]').click()
            assert page.locator('#copy-fallback').is_visible()
            assert page.locator('#copy-fallback textarea').input_value() == (ROOT / 'responses/EAwd.md').read_text()
            page.locator('#copy-fallback button[type="submit"]').click()
            for width in (390, 768, 1024, 1440):
                page.set_viewport_size({'width': width, 'height': 844})
                page.evaluate('window.scrollTo(0,0)')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'Page overflows at {width}px'
                if width == 390:
                    page.screenshot(path=str(ARTIFACTS / 'mobile.png'))
                    page.locator('#TM2s-3').scroll_into_view_if_needed()
                    page.screenshot(path=str(ARTIFACTS / 'mobile-table.png'))
            assert not errors, errors
            print(json.dumps({'result': 'passed', 'reviewers': 4, 'point_copy_buttons': 19, 'tables': 10, 'math_expressions': 2, 'responsive_widths': [390, 768, 1024, 1440], 'page_errors': errors}))
            browser.close()
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
