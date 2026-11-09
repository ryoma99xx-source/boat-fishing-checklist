const ORIGIN='https://www1.kaiho.mlit.go.jp';
export async function upstream(url){
 const r=await fetch(url,{signal:AbortSignal.timeout(12000),headers:{'User-Agent':'SHIO-TokyoBay/1.0'}});
 if(!r.ok)throw new Error('公式データの取得に失敗しました ('+r.status+')');return r;
}
export function validDate(s){if(!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;const dt=new Date(s+'T00:00:00Z');return Number.isFinite(dt.getTime())&&dt.toISOString().slice(0,10)===s;}
// Official chart pixel -> lat/lon, per area. 01 東京湾: lat = 35 + (631 - y)/840, lon = 139.5 + (x - 30)/675.
// 03 瀬戸内: read from the chart's own 10' ticks (x=30 is 130°40', 25.862 px per 10'; y=187 is 34°00', 31.385 px per 10').
export const JCG_AREAS={'01':{lat:y=>35+(631-y)/840,lon:x=>139.5+(x-30)/675,min:20},'03':{lat:y=>34+(187-y)/188.31,lon:x=>130+40/60+(x-30)/155.17,min:20}};
export function parseStations(html,area='01'){const A=JCG_AREAS[area];
 return [...html.matchAll(/coords\s*=\s*["']?(\d+),(\d+),\d+\s+ALT=["']([\d.]+)kn\./gi)].map(m=>({x:+m[1],y:+m[2],lat:A.lat(+m[2]),lon:A.lon(+m[1]),speed:+m[3]}));
}
export const TIDE_STATIONS={TK:{name:'東京',lat:35.65,lon:139.766667},Z1:{name:'油壺',lat:35.166667,lon:139.616667},MR:{name:'布良',lat:34.916667,lon:139.833333},TT:{name:'館山',lat:34.983333,lon:139.85},ZF:{name:'勝浦',lat:35.133333,lon:140.25},CS:{name:'銚子漁港',lat:35.75,lon:140.866667},OS:{name:'大阪',lat:34.65,lon:135.433},KB:{name:'神戸',lat:34.683,lon:135.183},AM:{name:'尼崎',lat:34.7,lon:135.4},J5:{name:'西宮',lat:34.717,lon:135.333},IO:{name:'泉大津',lat:34.517,lon:135.4},J2:{name:'岸和田',lat:34.467,lon:135.367},AK:{name:'明石',lat:34.65,lon:134.983},ST:{name:'洲本',lat:34.35,lon:134.9},WY:{name:'和歌山',lat:34.217,lon:135.15}};
export function parseTides(raw,date,code='TK'){
 if(!TIDE_STATIONS[code])throw new Error('対応していない潮位地点です。');
 const lines=raw.split(/\r?\n/),find=d=>{const [y,m,day]=d.split('-').map(Number);return lines.find(l=>+l.slice(72,74)===y%100&&+l.slice(74,76)===m&&+l.slice(76,78)===day)};
 const line=find(date),year=date.slice(0,4);
 if(!line)throw new Error('この日付の潮位表が見つかりません。');
 const value=s=>{const v=parseInt(s,10);return !Number.isFinite(v)||v===999?null:v};
 const hours=Array.from({length:24},(_,i)=>value(line.slice(i*3,i*3+3)));
 const next=new Date(date+'T00:00:00Z');next.setUTCDate(next.getUTCDate()+1);const nextLine=find(next.toISOString().slice(0,10));
 function events(row,offset=0){const out=[];if(!row)return out;for(const [start,type]of [[80,'high'],[108,'low']])for(let i=0;i<4;i++){const h=parseInt(row.slice(start+i*7,start+i*7+2),10),m=parseInt(row.slice(start+i*7+2,start+i*7+4),10),height=value(row.slice(start+i*7+4,start+i*7+7));if(!Number.isFinite(h)||!Number.isFinite(m)||height===null||h<0||m<0||h>24||m>59||h===24&&m!==0)continue;out.push({type,hour:offset+h+m/60,height,time:String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')})}return out.sort((a,b)=>a.hour-b.hour)}
 return {date,code,station:TIDE_STATIONS[code].name,coordinates:TIDE_STATIONS[code],hours,dayHours:[...hours,nextLine?value(nextLine.slice(0,3)):null],events:events(line),nextDayEvents:events(nextLine,24),timezone:'JST',datum:'潮位表基準面からの高さ',source:`https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/${year}/${code}.txt`};
}
export async function current(date,hour,area='01'){if(!JCG_AREAS[area])throw new Error('対応していない海域です。');
 const [year,month,day]=date.split('-').map(Number);
 const source=`${ORIGIN}/TIDE/pred2/cgi-bin/CurrPredCgi_K.cgi?area=${area}&year=${year}&month=${month}&day=${day}&hour=${hour}`;
 const html=await(await upstream(source)).text();const stations=parseStations(html,area);
 if(stations.length<20)throw new Error('公式推算図を読み取れませんでした。時間をおいて再取得してください。');
 const expected=`${area}_${date.replaceAll('-','')}${String(hour).padStart(2,'0')}_.png`;
 if(!html.includes(expected))throw new Error('要求時刻と推算図の時刻が一致しません。');
 const imagePath=`${ORIGIN}/TIDE/pred2/CurrPred/curr_img/${expected}`;
 const bytes=new Uint8Array(await(await upstream(imagePath)).arrayBuffer());
 let binary='';for(const b of bytes)binary+=String.fromCharCode(b);
 return {date,hour,area,stations,image:'data:image/png;base64,'+btoa(binary),source,generatedAt:new Date().toISOString()};
}
