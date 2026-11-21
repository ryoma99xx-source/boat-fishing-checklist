<?php
/**
 * Plugin Name: Cutlassfish Archive（記事一覧・釣行記の年表・検索）
 * Description: 過去記事を見つけやすくします。全記事一覧（/articles/：魚・テーマ・年月で絞り込み、文字で検索）、釣行記の年表（/fishing-log/）、メニューの検索欄、記事の下の「前後の記事」と「同じ魚の記事」。釣果速報は一覧に入れません。
 * Version: 1.0.1
 * Author: 3rd-Penguin Fishing Lab.
 * License: GPLv2 or later
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class CF_Archive {
	const V     = '1.0.1';
	const TYPES = array( 'tachiuo_post' );   // 釣り記事だけ。釣果速報（tbt_catch）・動画・初期の投稿（Hello world!）は入れない
	const CACHE = 'cf_archive_items_v1';

	public static function init() {
		add_action( 'init', array( __CLASS__, 'rewrite' ) );
		add_action( 'init', array( __CLASS__, 'maybe_flush' ), 99 );
		add_filter( 'query_vars', array( __CLASS__, 'query_vars' ) );
		add_action( 'parse_query', array( __CLASS__, 'parse_query' ) );
		add_action( 'pre_get_posts', array( __CLASS__, 'pre_get_posts' ) );
		add_filter( 'template_include', array( __CLASS__, 'template' ), 99 );
		add_filter( 'document_title_parts', array( __CLASS__, 'title' ) );
		add_filter( 'pre_get_document_title', array( __CLASS__, 'doc_title' ), PHP_INT_MAX );
		foreach ( array( 'title', 'og_title', 'twitter_title' ) as $k ) {          // SEO SIMPLE PACK の出力も、このページ用に
			add_filter( 'ssp_output_' . $k, array( __CLASS__, 'doc_title_ssp' ), 99 );
		}
		foreach ( array( 'canonical', 'og_url' ) as $k ) {
			add_filter( 'ssp_output_' . $k, array( __CLASS__, 'ssp_url' ), 99 );
		}
		foreach ( array( 'description', 'og_description', 'twitter_description' ) as $k ) {
			add_filter( 'ssp_output_' . $k, array( __CLASS__, 'ssp_desc' ), 99 );
		}
		add_filter( 'body_class', array( __CLASS__, 'body_class' ) );
		add_action( 'wp_footer', array( __CLASS__, 'menu_js' ), 20 );
		add_filter( 'the_content', array( __CLASS__, 'after_content' ), 30 );
		add_action( 'save_post', array( __CLASS__, 'clear' ) );
		add_action( 'deleted_post', array( __CLASS__, 'clear' ) );
		add_action( 'set_object_terms', array( __CLASS__, 'clear' ) );
	}

	/* ---------- URL ---------- */
	public static function rewrite() {
		add_rewrite_rule( '^articles/?$', 'index.php?cf_archive=all', 'top' );
		add_rewrite_rule( '^fishing-log/?$', 'index.php?cf_archive=log', 'top' );
	}
	public static function maybe_flush() {   // ZIP で更新したときも、一度だけ URL を登録し直す
		if ( get_option( 'cf_archive_rules' ) !== self::V ) {
			flush_rewrite_rules( false );
			update_option( 'cf_archive_rules', self::V, false );
		}
	}
	public static function query_vars( $v ) {
		$v[] = 'cf_archive';
		return $v;
	}
	private static function mode() {
		$m = get_query_var( 'cf_archive' );
		return in_array( $m, array( 'all', 'log' ), true ) ? $m : '';
	}
	public static function parse_query( $q ) {
		if ( $q->is_main_query() && in_array( $q->get( 'cf_archive' ), array( 'all', 'log' ), true ) ) {
			$q->is_home = false;
			$q->is_404  = false;
		}
	}
	public static function pre_get_posts( $q ) {
		if ( $q->is_main_query() && in_array( $q->get( 'cf_archive' ), array( 'all', 'log' ), true ) ) {
			$q->set( 'posts_per_page', 1 );
			$q->set( 'no_found_rows', true );
		}
	}
	public static function title( $parts ) {
		$m = self::mode();
		if ( $m ) {
			$parts['title'] = 'all' === $m ? '記事一覧' : '釣行記の年表';
		}
		return $parts;
	}
	private static function page_title() {
		return ( 'all' === self::mode() ? '記事一覧' : '釣行記の年表' ) . ' | ' . get_bloginfo( 'name' );
	}
	public static function doc_title( $t ) {
		return self::mode() ? self::page_title() : $t;
	}
	public static function doc_title_ssp( $v ) {
		return self::mode() ? self::page_title() : $v;
	}
	public static function ssp_url( $v ) {
		$m = self::mode();
		return $m ? home_url( 'all' === $m ? '/articles/' : '/fishing-log/' ) : $v;
	}
	public static function ssp_desc( $v ) {
		$m = self::mode();
		if ( ! $m ) {
			return $v;
		}
		return 'all' === $m ? '東京湾の魚・釣りの記事を全部並べた一覧です。魚・テーマ・年月で絞り込んだり、言葉で探したりできます。' : 'これまでの釣行記を、月ごとに並べた年表です。';
	}
	public static function body_class( $c ) {
		if ( self::mode() ) {
			$c[] = 'cf-archive-page';
		}
		return $c;
	}
	public static function template( $t ) {
		if ( self::mode() ) {
			status_header( 200 );
			return __DIR__ . '/template.php';
		}
		return $t;
	}

	/* ---------- データ（12時間キャッシュ。記事を保存すると作り直す） ---------- */
	public static function clear() {
		delete_transient( self::CACHE );
	}
	public static function items() {
		$c = get_transient( self::CACHE );
		if ( is_array( $c ) ) {
			return $c;
		}
		$ids   = get_posts( array( 'post_type' => self::TYPES, 'post_status' => 'publish', 'numberposts' => -1, 'orderby' => 'date', 'order' => 'DESC', 'fields' => 'ids', 'suppress_filters' => true ) );
		$items = array();
		foreach ( $ids as $id ) {
			$sp  = self::terms( $id, 'species' );
			$cat = self::terms( $id, 'tachiuo_cat' );
			$th    = get_post_thumbnail_id( $id );
			$img   = $th ? wp_get_attachment_image_src( $th, 'thumbnail' ) : false;
			$title = html_entity_decode( get_the_title( $id ), ENT_QUOTES, 'UTF-8' );
			$ex    = has_excerpt( $id ) ? get_post_field( 'post_excerpt', $id ) : wp_strip_all_tags( strip_shortcodes( get_post_field( 'post_content', $id ) ) );
			$ex    = trim( preg_replace( '/\s+/u', ' ', $ex ) );
			$items[] = array(
				'id'    => $id,
				'title' => $title,
				'url'   => get_permalink( $id ),
				'date'  => get_the_date( 'Y-m-d', $id ),
				'sp'    => $sp,
				'cat'   => $cat,
				'img'   => $img ? $img[0] : '',
				'ex'    => mb_substr( $ex, 0, 70 ),
				'log'   => 0 === strpos( $title, '【釣行記】' ),
			);
		}
		set_transient( self::CACHE, $items, 12 * HOUR_IN_SECONDS );
		return $items;
	}

	private static function terms( $id, $tax ) {
		$out = array();
		if ( taxonomy_exists( $tax ) && is_object_in_taxonomy( get_post_type( $id ), $tax ) ) {
			$t = get_the_terms( $id, $tax );
			if ( $t && ! is_wp_error( $t ) ) {
				foreach ( $t as $term ) {
					$out[ $term->slug ] = html_entity_decode( $term->name, ENT_QUOTES, 'UTF-8' );
				}
			}
		}
		return $out;
	}

	/* ---------- メニューに検索欄と一覧への入口 ---------- */
	public static function menu_js() {
		$all = esc_url( home_url( '/articles/' ) );
		$log = esc_url( home_url( '/fishing-log/' ) );
		?>
<style>
.cfa-nav-search{display:flex;gap:8px;margin:6px 0 10px;max-width:420px}
.cfa-nav-search input{flex:1 1 auto;min-width:0;background:#0e1520;border:1px solid rgba(255,255,255,.25);color:#eef3f7;border-radius:8px;padding:10px 12px;font-size:16px}
.cfa-nav-search button{flex:none;background:#41c9c6;color:#03161c;border:0;border-radius:8px;padding:0 16px;font-weight:700;font-size:15px;cursor:pointer}
</style>
<script>
(function(){var nav=document.querySelector('#overlay nav');if(!nav||nav.querySelector('.cfa-nav-search'))return;
var f=document.createElement('form');f.className='cfa-nav-search';f.action='<?php echo $all; ?>';f.method='get';f.setAttribute('role','search');
f.innerHTML='<input type="search" name="q" placeholder="記事を探す（例：テンヤ 色）" aria-label="記事を探す" enterkeyhint="search"><button type="submit">検索</button>';
var a=document.createElement('a');a.href='<?php echo $all; ?>';a.className='en';a.innerHTML='ARCHIVE<small>記事一覧</small>';
var b=document.createElement('a');b.href='<?php echo $log; ?>';b.className='en';b.innerHTML='FISHING LOG<small>釣行記の年表</small>';
var first=nav.firstElementChild;var ref=first?first.nextSibling:null;
[f,a,b].forEach(function(el){nav.insertBefore(el,ref)});})();
</script>
		<?php
	}

	/* ---------- 記事の下：前後の記事・同じ魚の記事・一覧への入口 ---------- */
	public static function after_content( $html ) {
		if ( is_feed() || ! is_singular( self::TYPES ) || ! in_the_loop() || ! is_main_query() ) {
			return $html;
		}
		$id    = get_the_ID();
		$items = self::items();
		$idx   = null;
		foreach ( $items as $i => $it ) {
			if ( (int) $it['id'] === (int) $id ) {
				$idx = $i;
				break;
			}
		}
		if ( null === $idx ) {
			return $html;
		}
		$me    = $items[ $idx ];
		$newer = $idx > 0 ? $items[ $idx - 1 ] : null;
		$older = isset( $items[ $idx + 1 ] ) ? $items[ $idx + 1 ] : null;
		$same  = array();
		if ( $me['sp'] ) {
			$sk = array_keys( $me['sp'] );
			foreach ( $items as $it ) {
				if ( (int) $it['id'] !== (int) $id && array_intersect( $sk, array_keys( $it['sp'] ) ) ) {
					$same[] = $it;
					if ( count( $same ) >= 6 ) {
						break;
					}
				}
			}
		}
		$o  = self::css();
		$o .= '<nav class="cfa-after" aria-label="ほかの記事">';
		if ( $older || $newer ) {
			$o .= '<div class="cfa-pn">';
			$o .= $older ? self::pn( $older, '← 前の記事' ) : '<span></span>';
			$o .= $newer ? self::pn( $newer, '次の記事 →' ) : '<span></span>';
			$o .= '</div>';
		}
		if ( $same ) {
			$name = reset( $me['sp'] );
			$o   .= '<p class="cfa-h">' . esc_html( $name ) . 'の記事</p><ul class="cfa-same">';
			foreach ( $same as $it ) {
				$o .= '<li><a href="' . esc_url( $it['url'] ) . '"><span class="cfa-d">' . esc_html( str_replace( '-', '.', $it['date'] ) ) . '</span>' . esc_html( $it['title'] ) . '</a></li>';
			}
			$o .= '</ul>';
		}
		$o .= '<div class="cfa-btns"><a href="' . esc_url( home_url( '/articles/' ) ) . '">記事一覧で探す</a><a href="' . esc_url( home_url( '/fishing-log/' ) ) . '">釣行記の年表</a></div>';
		$o .= '</nav>';
		return $html . $o;
	}
	private static function pn( $it, $label ) {
		$img = $it['img'] ? '<img src="' . esc_url( $it['img'] ) . '" alt="" loading="lazy" width="72" height="72">' : '';
		return '<a class="cfa-pn-a" href="' . esc_url( $it['url'] ) . '">' . $img . '<span><small>' . esc_html( $label ) . '</small>' . esc_html( $it['title'] ) . '</span></a>';
	}
	public static function css() {
		static $done = false;
		if ( $done ) {
			return '';
		}
		$done = true;
		return '<style>
.cfa-after{margin:44px 0 10px;padding-top:24px;border-top:1px solid rgba(255,255,255,.14)}
.cfa-pn{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cfa-pn-a{display:flex;gap:10px;align-items:center;padding:10px;border:1px solid rgba(255,255,255,.18);border-radius:10px;background:#0f1a28;color:#eef3f8 !important;text-decoration:none;font-size:13px;line-height:1.5;min-width:0}
.cfa-pn-a img{flex:none;width:56px;height:56px;object-fit:cover;border-radius:6px;margin:0}
.cfa-pn-a span{min-width:0;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical}
.cfa-pn-a small{display:block;color:#41c9c6;font-weight:700;font-size:12px}
.cfa-h{margin:26px 0 8px;font-weight:700;font-size:15px}
.cfa-same{list-style:none;margin:0;padding:0}
.cfa-same li{border-top:1px solid rgba(255,255,255,.1)}
.cfa-same a{display:block;padding:9px 2px;color:#eef3f8 !important;text-decoration:none;font-size:14px;line-height:1.6}
.cfa-d{display:inline-block;min-width:6.2em;color:#9cabbd;font-size:12px}
.cfa-btns{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 0}
.cfa-btns a{flex:1 1 140px;text-align:center;padding:12px 14px;border:2px solid #41c9c6;border-radius:10px;color:#ffffff !important;text-decoration:none;font-weight:700;font-size:14px}
@media (max-width:520px){.cfa-pn{grid-template-columns:1fr}}
</style>';
	}
}

CF_Archive::init();

register_activation_hook( __FILE__, function () {
	CF_Archive::rewrite();
	flush_rewrite_rules( false );
	update_option( 'cf_archive_rules', CF_Archive::V, false );
} );
register_deactivation_hook( __FILE__, function () {
	delete_option( 'cf_archive_rules' );
	flush_rewrite_rules( false );
} );
