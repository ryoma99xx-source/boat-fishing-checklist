(() => {
 const cfg = globalThis.DragonCounterTool || {};
 const url = cfg.url || 'https://dragon-counter.cutlassfish.tokyo/';
 const articleUrl = cfg.articleUrl || 'https://cutlassfish.tokyo/article/dragon-counter/';
 const card = `<div class="tool-cta" data-dragon-counter-tool="5">
  <div class="tool-cta-text">
    <h3 class="en">DRAGON COUNTER</h3>
    <span class="tool-name">ドラゴンカウンター</span>
    <p class="ja">タチウオの釣果を時間の経過と共に、テンヤ・潮・船の向きと一緒に記録する無料ツール。釣り場を選ぶと潮回りと満潮・干潮が自動で入り、ドラゴン（指5以上）や大漁も残せます。記録は端末の中だけに保存されます。</p>
  </div>
  <a class="tool-cta-btn en" href="${url}" target="_blank" rel="noopener">OPEN TOOL →</a>
</div>`;
 // TOOL 05 always sits right after TOOL 04 (the tide map card is added by another plugin, sometimes later).
 const place = stack => {
  const d = stack.querySelector('[data-dragon-counter-tool]'), t = stack.querySelector('[data-tide-map-tool]');
  if (d && t && (t.compareDocumentPosition(d) & Node.DOCUMENT_POSITION_PRECEDING)) t.after(d);
 };
 const run = () => {
  const stack = document.querySelector('.tools-stack');
  if (stack && !stack.querySelector('[data-dragon-counter-tool]')) stack.insertAdjacentHTML('beforeend', card);
  if (stack) { place(stack); if (!stack.dataset.dragonWatch) { stack.dataset.dragonWatch = '1'; new MutationObserver(() => place(stack)).observe(stack, {childList: true}); } }
  if (articleUrl) for (const text of document.querySelectorAll('[data-dragon-counter-tool] .tool-cta-text')) {
   if (text.querySelector('[data-dragon-counter-article]')) continue;
   const link = document.createElement('a');
   link.className = 'tool-read en'; link.dataset.dragonCounterArticle = '5';
   link.href = articleUrl; link.textContent = 'READ ARTICLE →'; text.append(link);
  }
  for (const nav of document.querySelectorAll('.overlay nav')) {
   if (nav.querySelector('[data-dragon-counter-nav]')) continue;
   const links = nav.querySelectorAll('a.nav-tool');
   if (!links.length) continue;
   const link = document.createElement('a');
   link.href = url; link.className = 'en nav-tool'; link.dataset.dragonCounterNav = '5';
   link.target = '_blank'; link.rel = 'noopener';
   link.innerHTML = 'DRAGON COUNTER<small>ドラゴンカウンター</small>';
   links[links.length - 1].after(link);
  }
 };
 if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, {once:true}); else run();
})();
