/* アプリ内ブラウザ（Instagram・Threads・LINE・Facebook など）で開かれたときの「ブラウザで開く」案内と、
   ブラウザで開かれたときの「ホーム画面に追加」案内。オーナー指示 2026-11-24。
   3つのカウンター（dragon-counter.cutlassfish.tokyo）と cutlassfish.tokyo（プラグイン cutlassfish-open-in-browser）で同じものを使う。
   <script src="https://dragon-counter.cutlassfish.tokyo/inapp.js" data-kind="app|site" data-name="タイラバカウンター" defer></script>
   - アプリ内ブラウザ：画面の下に帯。iPhone は Safari で開き直す（x-safari-https://、効かないアプリもあるので「…」メニューの案内とリンクのコピーも）。Android は Chrome で開き直す（intent://）。
   - ブラウザ（ホーム画面に追加していない）：2回目に来たときから、小さな「ホーム画面に追加」の帯。閉じたら30日出さない。
   - ホーム画面から開いているときは何も出さない。 */
(()=>{
  const me=document.currentScript||{dataset:{}},KIND=(me.dataset&&me.dataset.kind)||'site',NAME=(me.dataset&&me.dataset.name)||'このサイト';
  const ua=navigator.userAgent||'';
  const inapp=/Instagram|FBAN|FBAV|FB_IAB|FBIOS|Barcelona|Threads|\bLine\/|MicroMessenger|KAKAOTALK|Twitter|TikTok|musical_ly|BytedanceWebview|YJApp|Yahoo.*Japan/i.test(ua);
  const ios=/iPhone|iPad|iPod/.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1),android=/Android/i.test(ua);
  const standalone=(window.matchMedia&&matchMedia('(display-mode: standalone)').matches)||navigator.standalone===true;
  if(standalone)return;
  let prompt=null;window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();prompt=e});   // Android の「ホーム画面に追加」（早く来るので先に受ける）
  const ls={get:k=>{try{return localStorage.getItem(k)}catch(e){return null}},set:(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}}};
  const ss={get:k=>{try{return sessionStorage.getItem(k)}catch(e){return null}},set:(k,v)=>{try{sessionStorage.setItem(k,v)}catch(e){}}};
  const css=`.iab{position:fixed;left:8px;right:8px;bottom:calc(8px + env(safe-area-inset-bottom,0px));z-index:2147483000;background:#0b1422;color:#eef3f8;border:2px solid #41c9c6;border-radius:14px;
    padding:12px 14px 10px;box-shadow:0 6px 24px rgba(0,0,0,.45);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",sans-serif;max-width:560px;margin:0 auto}
  .iab.top{top:calc(8px + env(safe-area-inset-top,0px));bottom:auto}.iab b{color:#fff}.iab p{margin:0 28px 8px 0}.iab .iab-x{position:absolute;top:6px;right:8px;background:none;border:0;color:#9cabbd;font-size:22px;line-height:1;padding:4px;cursor:pointer}
  .iab .iab-b{display:flex;flex-wrap:wrap;gap:8px}.iab .iab-b a,.iab .iab-b button{flex:1 1 auto;min-height:44px;border-radius:10px;border:1px solid #41c9c6;background:transparent;color:#41c9c6;font:inherit;font-weight:700;padding:8px 12px;text-align:center;text-decoration:none;cursor:pointer}
  .iab .iab-b .on{background:#41c9c6;color:#03161c}.iab .iab-how{display:none;margin:10px 0 2px;padding:10px 12px;border-radius:10px;background:#101c2e;font-size:14px}.iab.how .iab-how{display:block}
  .iab .iab-how ol{margin:0;padding-left:1.3em}.iab small{color:#9cabbd;font-size:12px}.iab .iab-msg{display:none;margin:8px 0 0;color:#e3a43b;font-size:14px;font-weight:700}.iab.copied .iab-msg{display:block}
  .iab kbd{display:inline-block;border:1px solid #44566e;border-radius:6px;padding:0 6px;font:inherit;font-size:13px;background:#0b1422}`;
  const add=html=>{const s=document.createElement('style');s.textContent=css;document.head.appendChild(s);const d=document.createElement('div');d.className='iab'+(KIND==='app'?' top':'');d.setAttribute('role','dialog');d.innerHTML=html;document.body.appendChild(d);return d};
  const close=(d,key,store)=>{d.remove();store.set(key,String(Date.now()))};
  const url=location.href;
  const copy=async d=>{let ok=false;try{await navigator.clipboard.writeText(url);ok=true}catch(e){}
    if(!ok){const t=document.createElement('textarea');t.value=url;t.style.cssText='position:fixed;opacity:0';document.body.appendChild(t);t.select();try{ok=document.execCommand('copy')}catch(e){}t.remove()}
    d.classList.add('copied');d.querySelector('.iab-msg').textContent=ok?'リンクをコピーしました。いつも使っているブラウザを開いて、アドレス欄に貼り付けてください。':'コピーできませんでした。上の手順のとおり、メニューから開いてください。'};
  const run=()=>{
    if(inapp){
      if(ss.get('iab-x'))return;
      /* 開き直し：LINE は ?openExternalBrowser=1 でいつものブラウザに出る（iPhone・Android とも）。Android はほかのアプリでも intent://（既定のブラウザ）。
         iPhone の Instagram・Threads などはページから外に出す方法が無い（x-safari- は効かなかった：オーナー確認 2026-11-24）ので、「…」メニューの案内を最初から見せる */
      const line=/\bLine\//i.test(ua),strong=KIND==='app';
      const ext=line?url+(url.includes('?')?'&':'?')+'openExternalBrowser=1':android?`intent://${location.host}${location.pathname}${location.search}${location.hash}#Intent;scheme=https;end`:'';
      const where=ios?'右上（または右下）の <kbd>…</kbd>':'右上の <kbd>︙</kbd> または <kbd>…</kbd>';
      const msg=strong?`<b>${NAME}は、いつも使っているブラウザ（Safari・Chrome など）で開いて使ってください。</b>このアプリの中のブラウザでは、記録が残らないことがあり、ホーム画面にも追加できません。`
        :`<b>いつも使っているブラウザ（Safari・Chrome など）で開くと、また見に来やすくなります。</b>このアプリの中では、閉じると見つけにくく、ホーム画面にも追加できません。`;
      const d=add(`<button class="iab-x" aria-label="閉じる">×</button><p>${msg}</p>
        <div class="iab-how"><ol><li>${where} を押す</li><li>「外部ブラウザで開く」を押す<br><small>（アプリによって「ブラウザで開く」「Safariで開く」「Chromeで開く」など）</small></li><li>開いたブラウザで「ホーム画面に追加」をすると、アイコンから開けるようになります</li></ol></div>
        <div class="iab-b" style="margin-top:10px">${ext?`<a class="on" href="${ext}">ブラウザで開く</a>`:''}<button class="iab-copy${ext?'':' on'}">リンクをコピー</button></div>
        <p class="iab-msg"></p>`);
      d.classList.add('how');
      d.querySelector('.iab-x').onclick=()=>close(d,'iab-x',ss);d.querySelector('.iab-copy').onclick=()=>copy(d);
      return}
    // ブラウザ：2回目からホーム画面に追加の案内
    const n=+(ls.get('a2hs-n')||0)+1;ls.set('a2hs-n',String(n));
    const x=+(ls.get('a2hs-x')||0);if(n<2||Date.now()-x<30*864e5)return;
    if(!ios&&!android)return;
    const d=add(`<button class="iab-x" aria-label="閉じる">×</button><p><b>ホーム画面に追加すると、${NAME}をアイコンからすぐ開けます。</b></p><div class="iab-b"><button class="iab-add on">${ios?'やり方を見る':'ホーム画面に追加'}</button></div>
      <div class="iab-how"><ol>${ios?'<li><kbd>共有</kbd>（□に↑）を押す<br><small>Safari は画面の下（iPad は右上）、Chrome はアドレス欄の右</small></li><li>「ホーム画面に追加」を押す（見えないときは下へずらす）</li><li>右上の「追加」を押す</li>':'<li>ブラウザのメニュー（<kbd>︙</kbd> や <kbd>≡</kbd>）を押す</li><li>「ホーム画面に追加」（または「アプリをインストール」「ページを追加」）を押す</li>'}</ol></div>`);
    d.querySelector('.iab-x').onclick=()=>close(d,'a2hs-x',ls);
    d.querySelector('.iab-add').onclick=async()=>{if(prompt){prompt.prompt();try{await prompt.userChoice}catch(e){}close(d,'a2hs-x',ls)}else d.classList.toggle('how')};
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
