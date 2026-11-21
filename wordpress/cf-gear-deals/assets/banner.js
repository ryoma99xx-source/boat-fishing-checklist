(function () {
  if (!window.CFGD || !window.fetch) return;

  var KEY = 'cfgd-dismissed';
  function dismissed(k) {
    try { return localStorage.getItem(KEY) === k; } catch (e) { return false; }
  }
  function dismiss(k) {
    try { localStorage.setItem(KEY, k); } catch (e) {}
  }
  function yen(n) { return Number(n).toLocaleString('ja-JP'); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  var url = CFGD.endpoint + (CFGD.endpoint.indexOf('?') < 0 ? '?' : '&') + 'post_id=' + (CFGD.postId || 0);
  fetch(url, { credentials: 'omit' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      var d = data && data.deal;
      if (!d || dismissed(d.key)) return;

      var bar = el('aside', 'cfgd-bar');
      bar.setAttribute('aria-label', '今日の買い時');

      var link = el('a', 'cfgd-bar__link');
      link.href = d.url;
      link.rel = 'sponsored noopener';
      // バリューコマースのLinkSwitchに書き換えさせない（すでにアフィリエイトリンクなので、二重に包まれると飛び先が壊れる）
      link.setAttribute('data-nodal', '');
      link.target = '_blank';

      if (d.image && /^https:\/\//.test(d.image)) {
        var img = el('img', 'cfgd-bar__img');
        img.src = d.image;
        img.alt = '';
        img.width = 44;
        img.height = 44;
        img.loading = 'lazy';
        img.referrerPolicy = 'no-referrer';
        img.onerror = function () { img.remove(); };
        link.appendChild(img);
      }
      link.appendChild(el('span', 'cfgd-bar__pr', 'PR'));
      var body = el('span', 'cfgd-bar__body');
      var head = el('span', 'cfgd-bar__head');
      head.appendChild(el('span', 'cfgd-bar__label', d.type === 'store' ? '今日はこの店が買い時' : '今日が買い時'));
      if (d.points > 0) {
        head.appendChild(el('span', 'cfgd-bar__pt', yen(d.points) + 'pt' + (d.rate ? '（' + d.rate + '%）' : '')));
      }
      body.appendChild(head);
      body.appendChild(el('span', 'cfgd-bar__name', d.name));
      body.appendChild(el('span', 'cfgd-bar__price', d.line ? d.line :
        d.mall + ' 実質' + yen(d.eff) + '円（ポイント' + yen(d.points) + '円相当' +
        (d.coupon ? '・クーポン' + yen(d.coupon) + '円' : '') + '）'));
      link.appendChild(body);
      bar.appendChild(link);

      // 攻略ページへの「買い方を見る」（攻略ページ自身では出さない）
      if (d.guide && /^https?:\/\//.test(d.guide)) {
        var gpath = '';
        try { gpath = new URL(d.guide).pathname; } catch (e) {}
        if (!gpath || location.pathname.indexOf(gpath) !== 0) {
          var g = el('a', 'cfgd-bar__guide', '買い方を見る →');
          g.href = d.guide;
          bar.appendChild(g);
        }
      }

      var close = el('button', 'cfgd-bar__close', '×');
      close.type = 'button';
      close.setAttribute('aria-label', '閉じる');
      close.addEventListener('click', function () {
        dismiss(d.key);
        bar.remove();
      });
      bar.appendChild(close);

      document.body.appendChild(bar);
    })
    .catch(function () {});
})();


// 価格カタログ：「品番ごとの価格」を開いたとき、テーマ側の高さ制限（max-height・overflow:hidden）で
// 下のカードが隠れてスクロールできなくなるのを防ぐ。開いたカードを含む枠の高さ制限を外す。
(function () {
  if (!document.addEventListener) return;
  document.addEventListener('toggle', function (e) {
    var d = e.target;
    if (!d || !d.matches || !d.matches('details.cfgd-card__more') || !d.open) return;
    var el = d.closest('.cfgd-catalog');
    for (var i = 0; el && el !== document.body && i < 8; i++, el = el.parentElement) {
      var cs = window.getComputedStyle(el);
      var clamped = cs.maxHeight !== 'none' || ((cs.overflowY === 'hidden' || cs.overflow === 'hidden') && el.scrollHeight > el.clientHeight + 2);
      if (clamped) {
        el.style.maxHeight = 'none';
        el.style.height = 'auto';
        el.style.overflow = 'visible';
        el.classList.add('cfgd-unclamped');
      }
    }
  }, true);
})();
