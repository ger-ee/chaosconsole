/* ChaosConsole's install and standalone-window controls. */
(() => {
  'use strict';
  let installPrompt;
  const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    document.querySelectorAll('[data-install-app]').forEach(button => { button.hidden = false; });
  });
  window.addEventListener('appinstalled', () => {
    installPrompt = null;
    document.querySelectorAll('[data-install-app]').forEach(button => { button.hidden = true; });
    const status = document.querySelector('[data-install-status]');
    if (status) status.textContent = 'ChaosConsole has been added. Open it from your apps.';
  });
  document.addEventListener('click', async event => {
    if (!event.target.closest('[data-install-app]') || !installPrompt) return;
    const prompt = installPrompt;
    installPrompt = null;
    document.querySelectorAll('[data-install-app]').forEach(button => { button.hidden = true; });
    try { await prompt.prompt(); await prompt.userChoice; } catch (_) { /* Manual instructions remain available. */ }
  });
  function mount() {
    const isApp = standalone();
    document.documentElement.classList.toggle('cc-app-window', isApp);
    document.querySelectorAll('[data-browser-only]').forEach(el => { el.hidden = isApp; });
    if (isApp) {
      const status = document.querySelector('[data-install-status]');
      if (status) status.textContent = 'You’re using the ChaosConsole app.';
      const nav = document.createElement('nav');
      nav.className = 'cc-app-nav';
      nav.setAttribute('aria-label', 'App navigation');
      nav.innerHTML = '<button type="button" aria-label="Go back">← Back</button><a href="/" aria-label="ChaosConsole home">Home</a><button type="button" aria-label="Reload this page">↻ Refresh</button>';
      const buttons = nav.querySelectorAll('button');
      buttons[0].onclick = () => history.length > 1 ? history.back() : location.assign('/');
      buttons[1].onclick = () => location.reload();
      document.body.append(nav);
    }
    if ('serviceWorker' in navigator && window.isSecureContext) {
      navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' }).catch(() => {
        // The online app remains usable if a browser declines service workers.
      });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
