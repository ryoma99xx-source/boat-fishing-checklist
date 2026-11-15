(() => {
 const cfg = globalThis.TipranCounterTool || {};
 const url = cfg.url || 'https://dragon-counter.cutlassfish.tokyo/tipran/';
 const articleUrl = cfg.articleUrl || '';
 const card = `<div class="tool-cta" data-tipran-counter-tool="6">
  <div class="tool-cta-text">
    <h3 class="en">TIPRUN COUNTER</h3>
    <span class="tool-name">ティップランカウンター</span>
    <p class="ja">アオリイカの釣果を時間と一緒に、エギ・シンカー・潮・船の向きと一緒に記録する無料ツール。エギ・シンカー・竿・リールは写真付きのカタログから選べ、釣り場を選ぶと潮回りと満潮・干潮が自動で入ります。記録は端末に保存され、釣果データは匿名で集計に使います。</p>
  </div>
  <a class="tool-cta-btn en" href="${url}" target="_blank" rel="noopener">OPEN TOOL →</a>
</div>`;
 // TOOL 06 sits right after TOOL 05 (the other tool cards are added by other plugins, sometimes later).
 const place = stack => {
  const me = stack.querySelector('[data-tipran-counter-tool]'), d = stack.querySelector('[data-dragon-counter-tool]');
  if (me && d && d.nextElementSibling !== me) d.after(me);
 };
 const run = () => {
  const stack = document.querySelector('.tools-stack');
  if (stack && !stack.querySelector('[data-tipran-counter-tool]')) stack.insertAdjacentHTML('beforeend', card);
  if (stack) { place(stack); if (!stack.dataset.tipranWatch) { stack.dataset.tipranWatch = '1'; new MutationObserver(() => place(stack)).observe(stack, {childList: true}); } }
  if (articleUrl) for (const text of document.querySelectorAll('[data-tipran-counter-tool] .tool-cta-text')) {
   if (text.querySelector('[data-tipran-counter-article]')) continue;
   const link = document.createElement('a');
   link.className = 'tool-read en'; link.dataset.tipranCounterArticle = '6';
   link.href = articleUrl; link.textContent = 'READ ARTICLE →'; text.append(link);
  }
  for (const nav of document.querySelectorAll('.overlay nav')) {
   if (nav.querySelector('[data-tipran-counter-nav]')) continue;
   const links = nav.querySelectorAll('a.nav-tool');
   if (!links.length) continue;
   const link = document.createElement('a');
   link.href = url; link.className = 'en nav-tool'; link.dataset.tipranCounterNav = '6';
   link.target = '_blank'; link.rel = 'noopener';
   link.innerHTML = 'TIPRUN COUNTER<small>ティップランカウンター</small>';
   const after = nav.querySelector('[data-dragon-counter-nav]') || links[links.length - 1];
   after.after(link);
  }
 };
 if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, {once:true}); else run();
 // the dragon counter card/menu may be added after us: re-run once the page has settled
 window.addEventListener('load', () => setTimeout(run, 50), {once:true});
})();
