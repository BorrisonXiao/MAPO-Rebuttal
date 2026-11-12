(() => {
  'use strict';
  const sources = JSON.parse(document.getElementById('response-sources').textContent);
  const status = document.getElementById('copy-status');
  let toastTimer;
  function notify(message) {
    clearTimeout(toastTimer);
    status.textContent = message;
    status.hidden = false;
    toastTimer = setTimeout(() => { status.hidden = true; }, 2600);
  }
  function fallback(text) {
    const dialog = document.getElementById('copy-fallback');
    const textarea = dialog.querySelector('textarea');
    textarea.value = text;
    dialog.showModal();
    textarea.focus();
    textarea.select();
  }
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const reviewer = button.dataset.copy;
      const point = button.dataset.point;
      const text = point ? sources[reviewer].points[point] : sources[reviewer].markdown;
      try {
        await navigator.clipboard.writeText(text);
        notify(point ? `${reviewer}, point ${point}: Markdown copied` : `${reviewer}: original Markdown copied`);
      } catch (_) {
        fallback(text);
      }
    });
  });
  document.getElementById('select-fallback').addEventListener('click', () => {
    const textarea = document.querySelector('#copy-fallback textarea');
    textarea.focus();
    textarea.select();
  });
  const themeButton = document.getElementById('theme-toggle');
  themeButton.addEventListener('click', () => {
    const current = document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('mapo-theme', next); } catch (_) {}
  });
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      const active = entries.filter(entry => entry.isIntersecting).sort((a,b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!active) return;
      document.querySelectorAll('.sidebar a[aria-current]').forEach(link => link.removeAttribute('aria-current'));
      const link = document.querySelector(`.sidebar a[href="#${active.target.id}"]`);
      if (link) link.setAttribute('aria-current', 'location');
    }, { rootMargin: '-5% 0px -65% 0px' });
    document.querySelectorAll('.response-point').forEach(point => observer.observe(point));
  }
})();
