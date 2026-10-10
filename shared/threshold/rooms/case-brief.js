(() => {
  'use strict';
  const page = document.querySelector('.case-page');
  if (!page) return;
  const key = 'cc-case-tasks-' + page.dataset.case + '-20261007';
  const boxes = [...page.querySelectorAll('.case-tasks input')];
  const note = page.querySelector('.case-save-note');
  const discoveryNote = page.querySelector('[data-discovery-progress]');
  const discoveryBoxes = boxes.filter(box => box.dataset.key.startsWith('discovery-'));
  const reminders = boxes.filter(box => !box.dataset.key.startsWith('discovery-'));
  let saved = {};
  try { const value = JSON.parse(localStorage.getItem(key) || '{}'); if (value && typeof value === 'object') saved = value; } catch {}
  function update() {
    const count = reminders.filter(box => box.checked).length;
    if (note) note.textContent = count + ' of ' + reminders.length + ' reminders checked. Saved in this browser only; a tick does not confirm filing, service, or completion in the case record.';
    if (discoveryNote) discoveryNote.textContent = discoveryBoxes.filter(box => box.checked).length + ' of ' + discoveryBoxes.length + ' preparation steps checked. Saved in this browser only; ticking a step does not confirm legal completion or service.';
  }
  boxes.forEach(box => {
    box.checked = saved[box.dataset.key] === true;
    box.closest('li').classList.toggle('is-done', box.checked);
    box.addEventListener('change', () => {
      saved[box.dataset.key] = box.checked;
      box.closest('li').classList.toggle('is-done', box.checked);
      try { localStorage.setItem(key, JSON.stringify(saved)); update(); }
      catch { if (note) note.textContent = 'This browser could not save the reminder. The case record is unchanged.'; }
    });
  });
  update();
  function revealSource() {
    const target = document.getElementById(location.hash.slice(1));
    const details = target?.closest('details');
    if (details) { details.open = true; requestAnimationFrame(() => target.scrollIntoView({block:'start'})); }
  }
  window.addEventListener('hashchange', revealSource);
  page.addEventListener('click', event => {
    const link = event.target.closest('a.case-ref');
    if (link && link.hash === location.hash) revealSource();
  });
  revealSource();
})();
