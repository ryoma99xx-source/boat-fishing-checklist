(() => {
 const icons = (globalThis.CutlassfishToolIcons || {}).icons || {};
 const decorate = card => {
  if (card.querySelector('.cf-tool-icon')) return;
  const btn = card.querySelector('a.tool-cta-btn'), text = card.querySelector('.tool-cta-text, .tu-tool-text'), h3 = text && text.querySelector('h3');
  if (!btn || !h3) return;
  let u; try { u = new URL(btn.href, location.href); } catch (e) { return; }
  const at = u.host + u.pathname, key = Object.keys(icons).sort((a, b) => b.length - a.length).find(k => at.startsWith(k));   // パス付き（/tipran）を先に見る
  const src = key && icons[key]; if (!src) return;
  const head = document.createElement('div'); head.className = 'cf-tool-head';
  const img = document.createElement('img'); img.className = 'cf-tool-icon'; img.src = src; img.alt = ''; img.width = 64; img.height = 64; img.loading = 'lazy'; img.decoding = 'async';
  const names = document.createElement('div'); names.className = 'cf-tool-names';
  h3.before(head); names.append(h3);
  const sub = text.querySelector('.tool-name'); if (sub) names.append(sub);
  head.append(img, names);
 };
 const run = () => {
  const stack = document.querySelector('.tools-stack'); if (!stack) return;
  stack.querySelectorAll('.tool-cta, .tool-unit').forEach(decorate);
  if (!stack.dataset.cfIconWatch) { stack.dataset.cfIconWatch = '1'; new MutationObserver(() => stack.querySelectorAll('.tool-cta, .tool-unit').forEach(decorate)).observe(stack, {childList: true, subtree: true}); }
 };
 if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, {once: true}); else run();
})();
