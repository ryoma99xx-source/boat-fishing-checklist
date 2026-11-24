/* サイトの定期点検（表示・エラー・はみ出し・リンク切れ・配信ファイルの改ざん・見た目の変化）。オーナー指示 2026-11-24。
   ops/SITE-MAINTENANCE.md の手順で、毎日（--daily）と毎週（--weekly）に Claude の定期作業から動かす。読むだけで、サイトには何も書かない。

     node ops/sitecheck/sitecheck.cjs --daily            主なページ＋配信ファイルの照合
     node ops/sitecheck/sitecheck.cjs --weekly           ＋サイトマップの全ページ・ページ内リンク・見た目の比較（ops/sitecheck/baseline）
     node ops/sitecheck/sitecheck.cjs --weekly --update-baseline   見た目の基準を今の状態で置き換える

   問題があれば最後に「要確認」と一覧を出し、終了コード 1。Playwright（require('playwright')）を使う。 */
const {chromium,devices}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const REPO=path.resolve(__dirname,'..','..'),DC=path.join(REPO,'sites','dragon-counter');
const A=process.argv.slice(2),WEEKLY=A.includes('--weekly'),UPD=A.includes('--update-baseline');
const OUT=process.env.SITECHECK_OUT||path.join(require('os').tmpdir(),'sitecheck');fs.mkdirSync(OUT,{recursive:true});
const BASE=path.join(__dirname,'baseline');
const OWN=/(^|\.)cutlassfish\.tokyo$/;
// 主なページ：url・名前・あるはずのもの（CSS セレクタ、または JS の式）
const PAGES=[
 ['https://cutlassfish.tokyo/','サイトのトップ',['.cfna-sec .cfna-card']],
 ['https://cutlassfish.tokyo/article/tachiuo-tenya-kihon/','記事：テンヤタチウオ 基本のキ',[]],
 ['https://cutlassfish.tokyo/article/tairaba-head-catalog/','記事：タイラバ ヘッドのカタログ',['.tcat-bar']],
 ['https://cutlassfish.tokyo/article/tairaba-tie-catalog/','記事：タイラバ ネクタイのカタログ',['.tcat-bar']],
 ['https://cutlassfish.tokyo/shopping/','セール情報',[]],
 ['https://dragon-counter.cutlassfish.tokyo/','ドラゴンカウンター',['js:typeof render==="function"']],
 ['https://dragon-counter.cutlassfish.tokyo/tipran/','ティップランカウンター',['js:typeof render==="function"']],
 ['https://dragon-counter.cutlassfish.tokyo/tairaba/','タイラバカウンター',['js:typeof render==="function"']],
 ['https://dragon-counter.cutlassfish.tokyo/tenya-catalog/','テンヤカタログ',['.tcat-bar']],
 ['https://dragon-counter.cutlassfish.tokyo/egi-catalog/','エギカタログ',['.tcat-bar']],
 ['https://dragon-counter.cutlassfish.tokyo/tairaba-catalog/','タイラバ ヘッドのカタログ',['.tcat-bar']],
 ['https://dragon-counter.cutlassfish.tokyo/tairaba-catalog/ties/','タイラバ ネクタイのカタログ',['.tcat-bar']],
 ['https://dragon-counter.cutlassfish.tokyo/links/','リンク集',['a.l']],
 ['https://tide-current-map.cutlassfish.tokyo/','東京湾の潮と流れ',[]],
];
const problems=[],notes=[];
const bad=(m)=>{problems.push(m);console.log('  ✗ '+m)},ok=(m)=>console.log('  ✓ '+m);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const slug=u=>u.replace(/^https?:\/\//,'').replace(/[^\w]+/g,'_').replace(/_+$/,'');

async function checkPage(b,[url,name,need]){
  const c=await b.newContext({...devices['iPhone 13'],deviceScaleFactor:1});const p=await c.newPage();
  const errs=[],fails=[];
  p.on('pageerror',e=>errs.push(String(e.message).slice(0,160)));
  p.on('response',r=>{try{const u=new URL(r.url());if(OWN.test(u.hostname)&&r.status()>=400&&!/favicon|apple-touch/.test(u.pathname))fails.push(r.status()+' '+u.pathname)}catch(e){}});
  let st=0;try{const r=await p.goto(url,{waitUntil:'domcontentloaded',timeout:45000});st=r?r.status():0}catch(e){bad(`${name}：開けない（${String(e.message).slice(0,80)}）`);await c.close();return}
  await p.waitForTimeout(4000);
  if(st>=400){bad(`${name}：HTTP ${st}`);await c.close();return}
  const miss=[];for(const s of need){const has=s.startsWith('js:')?await p.evaluate(s.slice(3)).catch(()=>false):!!(await p.$(s));if(!has)miss.push(s)}
  const ov=await p.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
  const msg=[];if(errs.length)msg.push('画面のエラー '+errs.length+'件（'+errs[0]+'）');if(fails.length)msg.push('読めない部品 '+fails.length+'件（'+[...new Set(fails)].slice(0,3).join('、')+'）');
  if(miss.length)msg.push('あるはずのものが無い：'+miss.join('、'));if(ov>4)msg.push('横に '+ov+'px はみ出している');
  if(msg.length)bad(`${name}：${msg.join('／')}`);else ok(`${name}`);
  if(WEEKLY){const f=path.join(OUT,slug(url)+'.jpg');await p.screenshot({path:f,type:'jpeg',quality:55,clip:{x:0,y:0,width:390,height:844}});await diffShot(f,name,url)}
  await c.close();
}

/* 見た目の比較：基準（ops/sitecheck/baseline/*.jpg。--update-baseline のときだけ作り直す）と、画面の最初の1枚分をくらべる。違いが大きいときだけ知らせる（記事が増えるなどの小さな変化は気にしない） */
async function diffShot(f,name,url){
  const bf=path.join(BASE,slug(url)+'.jpg');
  if(!fs.existsSync(bf)||UPD){fs.mkdirSync(BASE,{recursive:true});fs.copyFileSync(f,bf);if(!UPD)notes.push(`${name}：見た目の基準を新しく作った`);return}
  const b2=await chromium.launch();const p=await b2.newPage();
  const r=await p.evaluate(async([a,c])=>{const ld=s=>new Promise(r=>{const i=new Image();i.onload=()=>r(i);i.src=s});const [x,y]=await Promise.all([ld(a),ld(c)]);
    const W=97,H=211,cv=document.createElement('canvas');cv.width=W;cv.height=H;const g=cv.getContext('2d');const px=i=>{g.drawImage(i,0,0,W,H);return g.getImageData(0,0,W,H).data};
    const d1=px(x),d2=px(y);let n=0;for(let i=0;i<d1.length;i+=4){const d=Math.abs(d1[i]-d2[i])+Math.abs(d1[i+1]-d2[i+1])+Math.abs(d1[i+2]-d2[i+2]);if(d>90)n++}return n/(W*H)},
    ['data:image/jpeg;base64,'+fs.readFileSync(bf).toString('base64'),'data:image/jpeg;base64,'+fs.readFileSync(f).toString('base64')]);
  await b2.close();
  if(r>0.35)notes.push(`${name}：見た目が前回から大きく変わった（${Math.round(r*100)}%）→ ${f} と ${bf} を見くらべる`);
}

/* 配信ファイルの照合：ドラゴンカウンターのサーバーにあるファイルが、リポジトリと同じか（改ざん・公開し忘れ） */
async function checkFiles(){
  const list=fs.readFileSync(path.join(DC,'SHA256SUMS'),'utf8').trim().split('\n').map(l=>l.split(/\s+/)).map(([h,f])=>[f,h]);
  for(const f of ['tairaba/index.html','tipran/index.html','inapp.js','tenya-catalog/catalog.js','links/index.html','tairaba-catalog/index.html','egi-catalog/index.html','tenya-catalog/index.html'])
    if(fs.existsSync(path.join(DC,'public',f)))list.push([f,sha(fs.readFileSync(path.join(DC,'public',f)))]);
  let n=0;const diff=[];
  for(const [f,h] of list){if(/\.php$/.test(f))continue;try{const r=await fetch('https://dragon-counter.cutlassfish.tokyo/'+f+'?sc='+Date.now(),{headers:{'Cache-Control':'no-cache'}});if(!r.ok){diff.push(f+'（HTTP '+r.status+'）');continue}
    const b=Buffer.from(await r.arrayBuffer());n++;if(sha(b)!==h)diff.push(f)}catch(e){diff.push(f+'（'+e.message+'）')}}
  if(diff.length)bad('ドラゴンカウンターの配信ファイルがリポジトリと違う：'+diff.join('、')+'（公開の直後なら、反映待ちのことがある）');else ok(`配信ファイル ${n}個がリポジトリと同じ`);
}

/* 毎週：サイトマップの全ページと、主なページのリンク先が開けるか（404 探し）。数が多いので HEAD（だめなら GET）で軽く */
async function checkLinks(b){
  const seen=new Map();const urls=new Set();
  try{const idx=await (await fetch('https://cutlassfish.tokyo/wp-sitemap.xml')).text();for(const m of idx.matchAll(/<loc>([^<]+)<\/loc>/g)){const x=await (await fetch(m[1])).text();for(const n of x.matchAll(/<loc>([^<]+)<\/loc>/g))urls.add(n[1])}}catch(e){bad('サイトマップを読めない：'+e.message)}
  const c=await b.newContext();const p=await c.newPage();
  for(const [u] of PAGES){try{await p.goto(u,{waitUntil:'domcontentloaded',timeout:45000});await p.waitForTimeout(1500);for(const h of await p.$$eval('a[href]',a=>a.map(x=>x.href)))try{const x=new URL(h);if(OWN.test(x.hostname)&&!x.hash)urls.add(x.origin+x.pathname)}catch(e){}}catch(e){}}
  await c.close();
  const st=async u=>{try{let r=await fetch(u,{method:'HEAD',redirect:'follow'});if(r.status>=400&&r.status!==404)r=await fetch(u,{redirect:'follow'});return r.status}catch(e){return 0}};
  const L=[...urls].filter(u=>!/\/wp-(admin|login)|\/feed\/?$|admin-ajax|xmlrpc/.test(u));const broken=[];
  for(let i=0;i<L.length;i+=6)(await Promise.all(L.slice(i,i+6).map(async u=>[u,await st(u)]))).forEach(([u,s])=>{if(s===404||s===410||s===0)broken.push(s+' '+u)});
  if(broken.length)bad(`開けないリンク ${broken.length}件：`+broken.slice(0,15).join('、'));else ok(`リンク ${L.length}件を確認（開けないものなし）`);
}

(async()=>{
  console.log(`サイトの点検（${WEEKLY?'毎週':'毎日'}）${new Date().toISOString()}`);
  const b=await chromium.launch();
  console.log('■ 主なページ（スマホ幅）');for(const pg of PAGES)await checkPage(b,pg);
  console.log('■ 配信ファイル');await checkFiles();
  if(WEEKLY){console.log('■ リンク切れ');await checkLinks(b)}
  await b.close();
  if(notes.length){console.log('■ メモ');notes.forEach(n=>console.log('  - '+n))}
  console.log(problems.length?`要確認（${problems.length}件）`:'問題なし');problems.forEach(x=>console.log(' - '+x));
  process.exit(problems.length?1:0);
})();
