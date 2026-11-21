<?php
/**
 * 記事一覧（/articles/）と釣行記の年表（/fishing-log/）。テーマのヘッダー・フッターの中に出す。
 *
 * @package cutlassfish-archive
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$cfa_mode  = get_query_var( 'cf_archive' );
$cfa_items = CF_Archive::items();
if ( 'log' === $cfa_mode ) {
	$cfa_items = array_values( array_filter( $cfa_items, function ( $it ) { return $it['log']; } ) );
}
$cfa_wd = array( '日', '月', '火', '水', '木', '金', '土' );

/* 絞り込みの選択肢（件数の多い順） */
$cfa_sp  = array();
$cfa_cat = array();
$cfa_ym  = array();
foreach ( $cfa_items as $it ) {
	foreach ( $it['sp'] as $k => $v ) {
		$cfa_sp[ $k ] = array( $v, ( isset( $cfa_sp[ $k ] ) ? $cfa_sp[ $k ][1] : 0 ) + 1 );
	}
	foreach ( $it['cat'] as $k => $v ) {
		$cfa_cat[ $k ] = array( $v, ( isset( $cfa_cat[ $k ] ) ? $cfa_cat[ $k ][1] : 0 ) + 1 );
	}
	$ym            = substr( $it['date'], 0, 7 );
	$cfa_ym[ $ym ] = ( isset( $cfa_ym[ $ym ] ) ? $cfa_ym[ $ym ] : 0 ) + 1;
}
uasort( $cfa_sp, function ( $a, $b ) { return $b[1] - $a[1]; } );
uasort( $cfa_cat, function ( $a, $b ) { return $b[1] - $a[1]; } );

get_header();
?>

<section class="page-hero"><div class="bg"></div><div class="wrap content">
  <span class="label en"><?php echo 'log' === $cfa_mode ? 'FISHING LOG' : 'ARCHIVE'; ?></span>
  <h1 class="en"><?php echo 'log' === $cfa_mode ? '釣行記の年表' : '記事一覧'; ?></h1>
  <p class="ja"><?php echo 'log' === $cfa_mode ? 'これまでの釣行記を、月ごとに並べています。' : 'これまでの記事を全部並べています。魚・テーマ・年月で絞り込んだり、言葉で探したりできます。'; ?></p>
</div></section>

<div class="wrap"><p class="crumb"><a href="<?php echo esc_url( home_url( '/' ) ); ?>">HOME</a> ／ <span><?php echo 'log' === $cfa_mode ? 'FISHING LOG' : 'ARCHIVE'; ?></span></p></div>

<section class="section"><div class="wrap cfa">
<style>
.cfa{max-width:860px}
.cfa-bar{padding:4px 0 10px;margin:0 0 6px;border-bottom:1px solid rgba(255,255,255,.12)}
.cfa-q{display:flex;gap:8px}
.cfa-q input{flex:1 1 auto;min-width:0;background:#0e1520;border:1px solid rgba(255,255,255,.25);color:#eef3f7;border-radius:8px;padding:11px 12px;font-size:16px}
.cfa-q button{flex:none;background:#1b2531;color:#eef3f7;border:0;border-radius:8px;padding:0 14px;font-size:14px;cursor:pointer}
.cfa-sel{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.cfa-sel select{flex:1 1 130px;min-width:0;background:#0e1520;border:1px solid rgba(255,255,255,.25);color:#eef3f7;border-radius:8px;padding:9px 10px;font-size:15px}
.cfa-cnt{margin:8px 0 0;font-size:13px;color:var(--muted,#9cabbd)}
.cfa-cnt a{color:#41c9c6;margin-left:10px}
.cfa-y{margin:34px 0 4px;font-size:22px;font-weight:700}
.cfa-m{margin:22px 0 6px;font-size:15px;font-weight:700;color:#41c9c6}
.cfa-m small{color:var(--muted,#9cabbd);font-weight:400;margin-left:8px}
.cfa-list{list-style:none;margin:0;padding:0}
.cfa-row{border-top:1px solid rgba(255,255,255,.1)}
.cfa-row a{display:flex;gap:12px;align-items:flex-start;padding:12px 2px;color:#eef3f8 !important;text-decoration:none}
.cfa-row img,.cfa-row .cfa-noimg{flex:none;width:72px;height:72px;object-fit:cover;border-radius:8px;margin:0;background:#16202c}
.cfa-row .cfa-t{display:block;font-size:15px;font-weight:700;line-height:1.55}
.cfa-row .cfa-meta{display:block;margin-top:4px;font-size:12px;color:var(--muted,#9cabbd);line-height:1.5}
.cfa-row .cfa-tag{display:inline-block;margin:0 4px 0 0;padding:0 7px;border:1px solid rgba(65,201,198,.5);border-radius:999px;color:#41c9c6;font-size:11px}
.cfa-row .cfa-ex{display:block;margin-top:4px;font-size:13px;color:#b9c6d4;line-height:1.6}
.cfa-none{color:var(--muted,#9cabbd);margin:24px 0}
.cfa-hide{display:none !important}
.cfa-switch{margin:22px 0 0;font-size:14px}
.cfa-switch a{color:#41c9c6}
</style>

<div class="cfa-bar">
  <form class="cfa-q" onsubmit="return false"><input type="search" id="cfa-q" placeholder="言葉で探す（例：テンヤ 色、サワラ 置き竿）" aria-label="記事を探す" enterkeyhint="search"><button type="button" id="cfa-clear">消す</button></form>
  <div class="cfa-sel">
    <select id="cfa-sp" aria-label="魚で絞り込む"><option value="">すべての魚</option><?php foreach ( $cfa_sp as $k => $v ) : ?><option value="<?php echo esc_attr( $k ); ?>"><?php echo esc_html( $v[0] . '（' . $v[1] . '）' ); ?></option><?php endforeach; ?></select>
    <?php if ( 'log' !== $cfa_mode ) : ?>
    <select id="cfa-cat" aria-label="テーマで絞り込む"><option value="">すべてのテーマ</option><option value="__log">釣行記だけ</option><?php foreach ( $cfa_cat as $k => $v ) : ?><option value="<?php echo esc_attr( $k ); ?>"><?php echo esc_html( $v[0] . '（' . $v[1] . '）' ); ?></option><?php endforeach; ?></select>
    <?php endif; ?>
    <select id="cfa-ym" aria-label="年月で絞り込む"><option value="">すべての年月</option><?php foreach ( $cfa_ym as $k => $n ) : ?><option value="<?php echo esc_attr( $k ); ?>"><?php echo esc_html( (int) substr( $k, 0, 4 ) . '年' . (int) substr( $k, 5, 2 ) . '月（' . $n . '）' ); ?></option><?php endforeach; ?></select>
  </div>
  <p class="cfa-cnt" id="cfa-cnt"></p>
</div>

<?php
$cfa_y = '';
$cfa_m = '';
$cfa_open = false;
foreach ( $cfa_items as $it ) :
	$y  = substr( $it['date'], 0, 4 );
	$ym = substr( $it['date'], 0, 7 );
	if ( $ym !== $cfa_m ) {
		if ( $cfa_open ) {
			echo '</ul>';
		}
		if ( 'log' === $cfa_mode && $y !== $cfa_y ) {
			echo '<h2 class="cfa-y" data-y="' . esc_attr( $y ) . '">' . esc_html( $y ) . '年</h2>';
			$cfa_y = $y;
		}
		echo '<h3 class="cfa-m" data-ym="' . esc_attr( $ym ) . '">' . esc_html( (int) substr( $ym, 0, 4 ) . '年' . (int) substr( $ym, 5, 2 ) . '月' ) . '<small>' . esc_html( $cfa_ym[ $ym ] . '本' ) . '</small></h3><ul class="cfa-list" data-ym="' . esc_attr( $ym ) . '">';
		$cfa_m    = $ym;
		$cfa_open = true;
	}
	$title = $it['title'];
	$when  = gmdate( 'Y.m.d', strtotime( $it['date'] ) ) . '（' . $cfa_wd[ (int) gmdate( 'w', strtotime( $it['date'] ) ) ] . '）';
	if ( 'log' === $cfa_mode ) {
		$title = trim( preg_replace( '/^【釣行記】\s*/u', '', $title ) );
		if ( preg_match( '/^(\d{2})-(\d{2})-(\d{2})\s*/', $title, $m ) ) {   // タイトルの日付（釣行日）を優先
			$d     = strtotime( '20' . $m[1] . '-' . $m[2] . '-' . $m[3] );
			$when  = '釣行日 ' . gmdate( 'Y.m.d', $d ) . '（' . $cfa_wd[ (int) gmdate( 'w', $d ) ] . '）';
			$title = trim( substr( $title, strlen( $m[0] ) ) );
		}
	}
	$q = $it['title'] . ' ' . $it['ex'] . ' ' . implode( ' ', $it['sp'] ) . ' ' . implode( ' ', $it['cat'] );
	?>
	<li class="cfa-row" data-sp="<?php echo esc_attr( implode( ' ', array_keys( $it['sp'] ) ) ); ?>" data-cat="<?php echo esc_attr( implode( ' ', array_keys( $it['cat'] ) ) . ( $it['log'] ? ' __log' : '' ) ); ?>" data-ym="<?php echo esc_attr( $ym ); ?>" data-q="<?php echo esc_attr( $q ); ?>"><a href="<?php echo esc_url( $it['url'] ); ?>">
		<?php echo $it['img'] ? '<img src="' . esc_url( $it['img'] ) . '" alt="" loading="lazy" width="72" height="72">' : '<span class="cfa-noimg"></span>'; ?>
		<span style="min-width:0"><span class="cfa-t"><?php echo esc_html( $title ); ?></span>
		<span class="cfa-meta"><?php echo esc_html( $when ); ?> <?php foreach ( $it['sp'] as $v ) { echo '<span class="cfa-tag">' . esc_html( $v ) . '</span>'; } ?><?php if ( 'log' !== $cfa_mode ) { foreach ( $it['cat'] as $v ) { echo '<span class="cfa-tag">' . esc_html( $v ) . '</span>'; } } ?></span>
		<?php if ( $it['ex'] ) : ?><span class="cfa-ex"><?php echo esc_html( $it['ex'] . ( mb_strlen( $it['ex'] ) >= 70 ? '…' : '' ) ); ?></span><?php endif; ?></span>
	</a></li>
<?php endforeach;
if ( $cfa_open ) {
	echo '</ul>';
}
?>
<p class="cfa-none cfa-hide" id="cfa-none">当てはまる記事がありません。言葉を短くするか、絞り込みを外してみてください。</p>
<p class="cfa-switch"><?php if ( 'log' === $cfa_mode ) : ?><a href="<?php echo esc_url( home_url( '/articles/' ) ); ?>">→ すべての記事の一覧へ</a><?php else : ?><a href="<?php echo esc_url( home_url( '/fishing-log/' ) ); ?>">→ 釣行記の年表へ</a><?php endif; ?></p>

<script>
(function(){
var $=function(s){return document.querySelector(s)},$$=function(s){return Array.prototype.slice.call(document.querySelectorAll(s))};
var norm=function(x){return String(x||'').normalize('NFKC').toLowerCase().replace(/[ぁ-ゖ]/g,function(c){return String.fromCharCode(c.charCodeAt(0)+0x60)})};
var rows=$$('.cfa-row');rows.forEach(function(r){r._q=norm(r.dataset.q)});
var q=$('#cfa-q'),sp=$('#cfa-sp'),cat=$('#cfa-cat'),ym=$('#cfa-ym');
var p=new URLSearchParams(location.search);if(p.get('q'))q.value=p.get('q');if(p.get('fish')&&sp.querySelector('option[value="'+p.get('fish')+'"]'))sp.value=p.get('fish');
if(cat&&p.get('topic')&&cat.querySelector('option[value="'+p.get('topic')+'"]'))cat.value=p.get('topic');
function apply(){var t=norm(q.value).split(/\s+/).filter(Boolean),s=sp.value,c=cat?cat.value:'',m=ym.value,n=0;
  rows.forEach(function(r){var ok=(!s||(' '+r.dataset.sp+' ').indexOf(' '+s+' ')>=0)&&(!c||(' '+r.dataset.cat+' ').indexOf(' '+c+' ')>=0)&&(!m||r.dataset.ym===m)&&t.every(function(w){return r._q.indexOf(w)>=0});
    r.classList.toggle('cfa-hide',!ok);if(ok)n++});
  $$('.cfa-list').forEach(function(u){var v=u.querySelectorAll('.cfa-row:not(.cfa-hide)').length,h=u.previousElementSibling;u.classList.toggle('cfa-hide',!v);
    if(h&&h.classList.contains('cfa-m')){h.classList.toggle('cfa-hide',!v);var sm=h.querySelector('small');if(sm)sm.textContent=v+'本'}});
  $$('.cfa-y').forEach(function(h){var y=h.dataset.y,v=$$('.cfa-row:not(.cfa-hide)').some(function(r){return r.dataset.ym.indexOf(y)===0});h.classList.toggle('cfa-hide',!v)});
  var on=t.length||s||c||m;$('#cfa-cnt').innerHTML=(on?n+'本見つかりました':'全'+rows.length+'本')+(on?'<a href="#" id="cfa-reset">絞り込みを外す</a>':'');
  var rs=$('#cfa-reset');if(rs)rs.onclick=function(e){e.preventDefault();q.value='';sp.value='';if(cat)cat.value='';ym.value='';apply()};
  $('#cfa-none').classList.toggle('cfa-hide',n>0)}
[q].forEach(function(el){el.addEventListener('input',apply)});[sp,cat,ym].forEach(function(el){if(el)el.addEventListener('change',apply)});
$('#cfa-clear').onclick=function(){q.value='';apply();q.focus()};apply();
})();
</script>
</div></section>

<?php get_footer(); ?>
