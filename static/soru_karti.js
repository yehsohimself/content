/* Soru kartı (2026-11-02): asistan bir şey sormak isteyince sohbette tek tek ilerleyen kart: seçenekler, birden çok seçim, "Başka bir şey", ileri ve geri.
   Kullanım: SoruKarti.html(anahtar, sorular, metin => gönder(metin)); sorular = [{soru, secenekler:[...], coklu}]. Sayfa yeniden çizse de durum anahtarda kalır.
   Bitince cevaplar normal bir mesaj olarak gönderilir; kartı kullanmak zorunlu değil, kişi yazma kutusundan da cevap verebilir. */
window.SoruKarti = (() => {
  const st = document.createElement('style'); st.textContent = `
.vh-sk{margin:8px 0 2px;padding:14px;border-radius:16px;border:1px solid var(--hair2,var(--cizgi2,rgba(128,128,128,.28)));background:var(--surface,var(--yuzey,var(--kart,transparent)));color:var(--ink,inherit);font-size:14.5px;line-height:1.4;width:100%;box-sizing:border-box;text-align:left}
.vh-sk-u{display:flex;align-items:center;gap:8px;margin-bottom:8px;min-height:18px;color:var(--muted,var(--ink3,#8e8e98));font-size:12.5px;font-variant-numeric:tabular-nums}
.vh-sk-n{display:flex;gap:4px;flex:1}.vh-sk-n i{width:16px;height:3px;border-radius:2px;background:var(--hair2,var(--cizgi2,rgba(128,128,128,.3)))}.vh-sk-n i.vh-sk-sec{background:var(--vurgu,currentColor)}
.vh-sk-g{animation:vhSkG .24s cubic-bezier(.22,1,.36,1)}
@keyframes vhSkG{from{opacity:0;transform:translateX(10px)}}
.vh-sk p{margin:0 0 10px;font-weight:600;font-size:15px;color:var(--ink,inherit)}
.vh-sk-l{display:flex;flex-direction:column;gap:6px}
.vh-sk .vh-sk-s{display:flex;align-items:center;gap:10px;width:100%;text-align:left;font:inherit;color:inherit;background:none;border:1px solid var(--hair2,var(--cizgi2,rgba(128,128,128,.28)));border-radius:11px;padding:9px 12px;cursor:pointer;transition:border-color .12s,background .12s}
.vh-sk-s:hover,.vh-sk-s:focus-visible{border-color:var(--vurgu,currentColor);outline:none}
.vh-sk-s>i{flex:none;width:16px;height:16px;border:1.5px solid var(--muted,var(--ink3,#8e8e98));border-radius:50%;display:grid;place-items:center;font:700 11px/1 var(--sans,inherit);font-style:normal;color:transparent}
.vh-sk-s.c>i{border-radius:5px}
.vh-sk-s.vh-sk-sec{border-color:var(--vurgu,currentColor);background:color-mix(in srgb,var(--vurgu,#5b7cf5) 12%,transparent)}
.vh-sk-s.vh-sk-sec>i{background:var(--vurgu,currentColor);border-color:var(--vurgu,currentColor);color:var(--vurgu-ink,#fff)}
.vh-sk input{width:100%;box-sizing:border-box;margin-top:6px;font:inherit;font-size:16px;color:inherit;background:none;border:1px solid var(--hair2,var(--cizgi2,rgba(128,128,128,.28)));border-radius:11px;padding:9px 12px;outline:none}
@media (min-width:700px){.vh-sk input{font-size:14.5px}}
.vh-sk input:focus{border-color:var(--vurgu,currentColor)}
.vh-sk-a{display:flex;align-items:center;gap:8px;margin-top:12px}.vh-sk-a span{flex:1}
.vh-sk-a button{font:inherit;font-size:14px;border:0;background:none;color:var(--muted,var(--ink3,#8e8e98));padding:7px 10px;border-radius:10px;cursor:pointer}
.vh-sk-a button.ana{background:var(--vurgu,#5b7cf5);color:var(--vurgu-ink,#fff);font-weight:600;padding:7px 16px}
.vh-sk-a button.ana:disabled{opacity:.4;cursor:default}
@media (prefers-reduced-motion:reduce){.vh-sk-g{animation:none}}`; document.head.appendChild(st);

  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const Y = k => ((document.documentElement.lang || '').toLowerCase().startsWith('en')
    ? {b: 'Something else…', g: 'Back', i: 'Next', a: 'Skip', s: 'Send', c: 'You can pick more than one'}
    : {b: 'Başka bir şey…', g: 'Geri', i: 'İleri', a: 'Atla', s: 'Gönder', c: 'Birden çok seçebilirsiniz'})[k];
  const D = {}, GON = {};
  const cevap = (d, i) => { const c = d.c[i] || {s: [], b: ''}; return [...c.s, c.b.trim()].filter(Boolean); };
  const hepsi = d => d.q.some((_, i) => cevap(d, i).length);

  function ic(k){ const d = D[k], q = d.q[d.i], c = d.c[d.i] || (d.c[d.i] = {s: [], b: ''}), son = d.i === d.q.length - 1, n = d.q.length;
    const u = n > 1 ? `<div class="vh-sk-u"><span class="vh-sk-n">${d.q.map((_, i) => `<i class="${i <= d.i ? 'vh-sk-sec' : ''}"></i>`).join('')}</span><span>${d.i + 1} / ${n}</span></div>` : '';
    const iki = q.coklu || n > 1;
    return `${u}<div class="vh-sk-g"><p>${esc(q.soru)}</p>${q.coklu ? `<div class="vh-sk-u" style="margin-top:-6px">${Y('c')}</div>` : ''}
      <div class="vh-sk-l" role="group" aria-label="${esc(q.soru)}">${q.secenekler.map((s, j) => { const on = c.s.includes(s); return `<button type="button" class="vh-sk-s${q.coklu ? ' c' : ''}${on ? ' vh-sk-sec' : ''}" data-sk-s="${j}" aria-pressed="${on}"><i>✓</i><span>${esc(s)}</span></button>`; }).join('')}</div>
      <input type="text" data-sk-b placeholder="${Y('b')}" value="${esc(c.b)}" aria-label="${Y('b')}"></div>
      <div class="vh-sk-a">${d.i ? `<button type="button" data-sk-a="g">${Y('g')}</button>` : ''}<span></span>${n > 1 && !son ? `<button type="button" data-sk-a="i2">${Y('a')}</button>` : ''}
        ${iki || c.b ? `<button type="button" class="ana" data-sk-a="${son ? 's' : 'i'}" ${son ? (hepsi(d) ? '' : 'disabled') : (cevap(d, d.i).length ? '' : 'disabled')}>${Y(son ? 's' : 'i')}</button>` : ''}</div>`; }

  function gonder(k){ const d = D[k], tek = d.q.length === 1;
    const L = d.q.map((q, i) => [q.soru, cevap(d, i).join(', ')]).filter(x => x[1]); if (!L.length) return;
    const m = tek ? L[0][1] : L.map(x => `${x[0]} ${x[1]}`).join('\n'); d.bitti = true; document.querySelectorAll(`[data-sk="${CSS.escape(k)}"]`).forEach(e => e.remove()); GON[k](m); }
  function yenile(el, k){ el.innerHTML = ic(k); }

  document.addEventListener('click', e => { const el = e.target.closest('.vh-sk'); if (!el) return; const k = el.dataset.sk, d = D[k]; if (!d) return;
    const s = e.target.closest('[data-sk-s]'), a = e.target.closest('[data-sk-a]');
    if (s){ const q = d.q[d.i], c = d.c[d.i], t = q.secenekler[+s.dataset.skS];
      if (q.coklu){ c.s = c.s.includes(t) ? c.s.filter(x => x !== t) : [...c.s, t]; yenile(el, k); return; }
      c.s = c.s.includes(t) ? [] : [t]; c.b = '';
      if (c.s.length && d.q.length === 1) return gonder(k);
      if (c.s.length && d.i < d.q.length - 1){ yenile(el, k); setTimeout(() => { if (D[k] === d && !d.bitti){ d.i++; const y = document.querySelector(`[data-sk="${CSS.escape(k)}"]`); if (y) yenile(y, k); } }, 170); return; }
      yenile(el, k); return; }
    if (a){ const w = a.dataset.skA; if (w === 's') return gonder(k); if (w === 'g') d.i--; else d.i++; yenile(el, k); } });
  document.addEventListener('input', e => { if (!e.target.matches?.('[data-sk-b]')) return; const el = e.target.closest('.vh-sk'), d = D[el.dataset.sk]; if (!d) return; const c = d.c[d.i], once = c.b.trim(); c.b = e.target.value;
    if (!d.q[d.i].coklu && c.b.trim()) c.s = [];
    if (!!once !== !!c.b.trim()){ const p = e.target.selectionStart; yenile(el, el.dataset.sk); const y = el.querySelector('[data-sk-b]'); y.focus(); y.setSelectionRange(p, p); } });
  document.addEventListener('keydown', e => { if (e.key !== 'Enter' || !e.target.matches?.('[data-sk-b]') || !e.target.value.trim()) return; e.preventDefault(); e.stopPropagation(); const el = e.target.closest('.vh-sk'), k = el.dataset.sk, d = D[k];
    if (d.i === d.q.length - 1) gonder(k); else { d.i++; yenile(el, k); } }, true);

  function html(k, sorular, fn){ const q = (sorular || []).filter(x => x && x.soru && (x.secenekler || []).length); if (!q.length) return ''; GON[k] = fn;
    if (!D[k]) D[k] = {q, i: 0, c: {}, bitti: false}; if (D[k].bitti) return ''; return `<div class="vh-sk" data-sk="${esc(k)}">${ic(k)}</div>`; }
  return {html};
})();
