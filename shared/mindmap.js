/* Chaos Console mind map — one JSON spec in, one inline SVG + detail panel + list fallback out.
   Usage: ConsoleMindMap(document.getElementById('x'), spec)
   spec = { root:{label, sub}, caption, branches:[{label, tone, note, refs, href, children:[{label, tone, note, refs, href}]}],
            refMarkup: ids => html }   // optional: how to render source refs in the detail panel
   tones: open | closing | court | closed | neutral | risk */
(function () {
  'use strict';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const wrap = (text, max) => {
    const words = String(text).split(/\s+/), lines = []; let cur = '';
    for (const w of words) { if ((cur + ' ' + w).trim().length > max && cur) { lines.push(cur); cur = w; } else cur = (cur + ' ' + w).trim(); }
    if (cur) lines.push(cur); return lines.slice(0, 3);
  };
  const toneWord = { open: 'Open', closing: 'Closing', court: 'Court date', closed: 'Closed', neutral: '', risk: 'At risk', done: 'Done' };

  window.ConsoleMindMap = function (el, spec) {
    if (!el || !spec) return;
    const B = spec.branches || [];
    // split branches left/right, balancing by weight (children + 1)
    const left = [], right = []; let lw = 0, rw = 0;
    B.forEach((b, i) => { b._i = i; const w = (b.children?.length || 0) + 1.2; if (lw <= rw) { left.push(b); lw += w; } else { right.push(b); rw += w; } });
    const LEAF_H = 46, LEAF_W = 236, BR_W = 196, BR_H = 56, GAP = 18, COL = 258;
    const ROOT_W = Math.max(220, Math.min(300, Math.max(String(spec.root.label).length * 9, String(spec.root.sub || '').length * 6.4) + 44));
    const blockH = b => Math.max(BR_H + GAP, (b.children?.length || 0) * LEAF_H + GAP);
    const sideH = arr => arr.reduce((a, b) => a + blockH(b), 0);
    const H = Math.max(sideH(left), sideH(right), 260) + 60;
    const CX = 760, W = 1520, CY = H / 2;
    const nodes = []; let paths = '';
    const place = (arr, dir) => {
      let y = (H - sideH(arr)) / 2;
      arr.forEach(b => {
        const h = blockH(b), by = y + h / 2, bx = CX + dir * COL;
        nodes.push({ kind: 'branch', x: bx, y: by, w: BR_W, h: BR_H, d: b, dir });
        paths += `<path class="mm-link mm-${esc(b.tone || 'neutral')}" d="M${CX + dir * ROOT_W / 2} ${CY} C${CX + dir * (ROOT_W / 2 + 60)} ${CY}, ${bx - dir * (BR_W / 2 + 60)} ${by}, ${bx - dir * BR_W / 2} ${by}"/>`;
        const kids = b.children || []; const top = by - (kids.length * LEAF_H) / 2 + LEAF_H / 2;
        kids.forEach((c, k) => {
          const cy = top + k * LEAF_H, cx = bx + dir * (COL + 20);
          nodes.push({ kind: 'leaf', x: cx, y: cy, w: LEAF_W, h: LEAF_H - 8, d: c, dir, parent: b });
          paths += `<path class="mm-link mm-thin mm-${esc(c.tone || b.tone || 'neutral')}" d="M${bx + dir * BR_W / 2} ${by} C${bx + dir * (BR_W / 2 + 50)} ${by}, ${cx - dir * (LEAF_W / 2 + 50)} ${cy}, ${cx - dir * LEAF_W / 2} ${cy}"/>`;
        });
        y += h;
      });
    };
    place(left, -1); place(right, 1);
    const all = []; let idx = 0;
    const box = n => {
      const id = idx++; all[id] = n;
      const lines = wrap(n.d.label, n.kind === 'branch' ? 20 : 30), fs = n.kind === 'branch' ? 15 : 12.5, lh = fs * 1.25;
      const y0 = n.y - ((lines.length - 1) * lh) / 2;
      return `<g class="mm-node mm-${n.kind} mm-${esc(n.d.tone || (n.parent?.tone) || 'neutral')}" data-mm="${id}" tabindex="0" role="button" aria-label="${esc(n.d.label)}${n.d.tone && toneWord[n.d.tone] ? ' · ' + toneWord[n.d.tone] : ''}">
<rect x="${n.x - n.w / 2}" y="${n.y - n.h / 2}" width="${n.w}" height="${n.h}" rx="${n.kind === 'branch' ? 6 : 4}"/>
${lines.map((l, i) => `<text x="${n.x}" y="${y0 + i * lh}" text-anchor="middle" dominant-baseline="central" font-size="${fs}">${esc(l)}</text>`).join('')}
</g>`;
    };
    const rootLines = wrap(spec.root.label, 22);
    const svg = `<svg class="mm-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(spec.caption || spec.root.label)}" xmlns="http://www.w3.org/2000/svg">
<g class="mm-links">${paths}</g>
<g class="mm-root" data-mm="root" tabindex="0" role="button" aria-label="${esc(spec.root.label)}"><rect x="${CX - ROOT_W / 2}" y="${CY - 40}" width="${ROOT_W}" height="80" rx="40"/>
${rootLines.map((l, i) => `<text x="${CX}" y="${CY - ((rootLines.length - 1) * 20) / 2 + i * 20 - (spec.root.sub ? 8 : 0)}" text-anchor="middle" dominant-baseline="central" font-size="16">${esc(l)}</text>`).join('')}
${spec.root.sub ? `<text class="mm-sub" x="${CX}" y="${CY + 22}" text-anchor="middle" dominant-baseline="central" font-size="11">${esc(spec.root.sub)}</text>` : ''}</g>
${nodes.map(box).join('')}
</svg>`;
    const list = `<details class="mm-list"><summary>Read the map as a list</summary><ul>${B.map(b => `<li><strong>${esc(b.label)}</strong>${b.tone && toneWord[b.tone] ? ` <em>${toneWord[b.tone]}</em>` : ''}${b.note ? `<p>${esc(b.note)}</p>` : ''}${(b.children || []).length ? `<ul>${b.children.map(c => `<li>${c.href ? `<a href="${esc(c.href)}">${esc(c.label)}</a>` : esc(c.label)}${c.note ? ` — ${esc(c.note)}` : ''}</li>`).join('')}</ul>` : ''}</li>`).join('')}</ul></details>`;
    el.classList.add('mm');
    el.innerHTML = `<figure class="mm-figure">${svg}<figcaption>${esc(spec.caption || '')}</figcaption></figure><div class="mm-detail" role="region" aria-live="polite" aria-label="Selected node"></div>${list}`;
    const detail = el.querySelector('.mm-detail');
    const refMarkup = spec.refMarkup || (ids => (ids || []).map(i => `<span class="mm-ref">[${esc(i)}]</span>`).join(' '));
    const show = id => {
      el.querySelectorAll('.mm-node,.mm-root').forEach(g => g.classList.toggle('is-sel', g.dataset.mm === String(id)));
      if (id === 'root') { detail.innerHTML = `<span class="mm-kicker">The centre</span><h3>${esc(spec.root.label)}</h3><p>${esc(spec.root.note || spec.caption || '')}</p>`; return; }
      const n = all[id]; if (!n) return; const d = n.d, parent = n.parent;
      detail.innerHTML = `<span class="mm-kicker">${parent ? esc(parent.label) + ' · ' : ''}${esc(toneWord[d.tone || parent?.tone || 'neutral'] || 'Branch')}</span><h3>${esc(d.label)}</h3><p>${esc(d.note || '')} ${refMarkup(d.refs)}</p>${d.href ? `<a class="mm-jump" href="${esc(d.href)}">${esc(d.hrefLabel || 'Open the section')} →</a>` : ''}${n.kind === 'branch' && (d.children || []).length ? `<ul class="mm-kids">${d.children.map(c => `<li>${esc(c.label)}</li>`).join('')}</ul>` : ''}`;
    };
    el.addEventListener('click', e => { const g = e.target.closest('[data-mm]'); if (g) show(g.dataset.mm); });
    el.addEventListener('keydown', e => { if (e.key !== 'Enter' && e.key !== ' ') return; const g = e.target.closest('[data-mm]'); if (g) { e.preventDefault(); show(g.dataset.mm); } });
    show(spec.initial != null ? spec.initial : 'root');
  };
})();
