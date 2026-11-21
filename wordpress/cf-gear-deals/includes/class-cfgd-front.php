<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class CFGD_Front {

	public static function init() {
		add_action( 'rest_api_init', array( __CLASS__, 'routes' ) );
		add_action( 'wp_enqueue_scripts', array( __CLASS__, 'assets' ) );
		add_shortcode( 'cfgd_calendar', array( __CLASS__, 'shortcode_calendar' ) );
		add_shortcode( 'cfgd_catalog', array( __CLASS__, 'shortcode_catalog' ) );
		add_action( 'wp_footer', array( __CLASS__, 'credits' ), 99 );
	}

	/** API提供元のクレジット表示（楽天・Yahoo!とも利用規約で表示が必要）。 */
	public static function credits() {
		echo '<p class="cfgd-credit" style="text-align:center;font-size:11px;opacity:.7;margin:8px 0 72px">'
			. '<a href="https://webservice.rakuten.co.jp/" target="_blank" rel="noopener">Supported by Rakuten Developers</a>'
			. ' ／ <a href="https://developer.yahoo.co.jp/sitemap/" target="_blank" rel="noopener">Webサービス by Yahoo! JAPAN</a>'
			. '</p>';
	}

	public static function routes() {
		register_rest_route( 'cfgd/v1', '/banner', array(
			'methods'             => 'GET',
			'permission_callback' => '__return_true',
			'callback'            => array( __CLASS__, 'banner' ),
			'args'                => array( 'post_id' => array( 'sanitize_callback' => 'absint' ) ),
		) );

		// スマホのショートカットからクーポンを登録する受け口（合言葉トークン必須）
		// スマホのショートカットから、Yahoo!直営アフィリエイトのリンクを登録する受け口
		register_rest_route( 'cfgd/v1', '/afflink', array(
			'methods'             => 'POST',
			'permission_callback' => array( __CLASS__, 'check_token' ),
			'callback'            => array( __CLASS__, 'quick_afflink' ),
		) );

		register_rest_route( 'cfgd/v1', '/coupon', array(
			'methods'             => 'POST',
			'permission_callback' => array( __CLASS__, 'check_token' ),
			'callback'            => array( __CLASS__, 'quick_coupon' ),
		) );
	}

	public static function check_token( WP_REST_Request $req ) {
		$token = (string) CFGD_Settings::get( 'quick_token' );
		$given = (string) ( $req->get_header( 'x-cfgd-token' ) ?: $req->get_param( 'token' ) );
		return '' !== $token && hash_equals( $token, $given );
	}

	/** POST { url } … アプリで発行した直営リンク（yahoo.jp の短縮URLでも可） */
	public static function quick_afflink( WP_REST_Request $req ) {
		$url = esc_url_raw( (string) $req->get_param( 'url' ) );
		$hit = CFGD_Parsers::parse_yahoo_afflink( $url );
		// 短縮URLなら転送先を1段ずつたどる
		for ( $i = 0; ! $hit && $i < 5; $i++ ) {
			$res = wp_remote_head( $url, array( 'redirection' => 0, 'timeout' => 10 ) );
			$loc = is_wp_error( $res ) ? '' : wp_remote_retrieve_header( $res, 'location' );
			if ( ! $loc ) {
				break;
			}
			$url = is_array( $loc ) ? end( $loc ) : $loc;
			$hit = CFGD_Parsers::parse_yahoo_afflink( $url );
		}
		if ( ! $hit ) {
			return new WP_Error( 'cfgd_afflink', 'Yahoo!ショッピングアフィリエイトのリンクではありません（アプリの「共有」で発行したリンクを送ってください）', array( 'status' => 400 ) );
		}
		CFGD_DB::save_afflink( 'yahoo', $hit['store'], $hit['item'], $hit['url'] );
		CFGD_Runner::run_judge( false );
		return rest_ensure_response( array( 'ok' => true, 'message' => "直営リンクを登録しました：{$hit['store']} / {$hit['item']}" ) );
	}

	/**
	 * POST { url, discount: "5%"|"1000", until: "10/16 0:00"(任意), scope: "item"|"store"(任意), min: 0(任意), note(任意) }
	 */
	/** 「50000円以上」「5万円以上」から最低注文金額を読む。 */
	private static function min_from_text( $t ) {
		$t = mb_convert_kana( $t, 'as' );
		if ( preg_match( '/([\d,.]+)\s*万\s*円?\s*以上/u', $t, $m ) ) {
			return (int) round( (float) str_replace( ',', '', $m[1] ) * 10000 );
		}
		return preg_match( '/([\d,]+)\s*円?\s*以上/u', $t, $m ) ? (int) str_replace( ',', '', $m[1] ) : 0;
	}

	public static function quick_coupon( WP_REST_Request $req ) {
		global $wpdb;
		$url  = CFGD_Fetch::resolve_url( esc_url_raw( (string) $req->get_param( 'url' ) ) );
		$shop = CFGD_Parsers::parse_shop_url( $url );
		$wide = false;
		if ( ! $shop ) {
			// クーポンのページ（Yahoo!ショッピング発行・楽天発行など、店に結びつかないもの）はモール全体として受け付ける
			$host = (string) wp_parse_url( $url, PHP_URL_HOST );
			if ( preg_match( '/(^|\.)yahoo\.co\.jp$/i', $host ) ) {
				$shop = array( 'mall' => 'yahoo', 'store' => '*', 'item' => '' );
			} elseif ( preg_match( '/(^|\.)rakuten\.co\.jp$/i', $host ) ) {
				$shop = array( 'mall' => 'rakuten', 'store' => '*', 'item' => '' );
			} else {
				return new WP_Error( 'cfgd_url', '楽天かYahoo!のページのURLではありません', array( 'status' => 400 ) );
			}
			$wide = true;
		}
		$disc = CFGD_Parsers::parse_discount( (string) $req->get_param( 'discount' ) );
		if ( ! $disc || $disc[1] <= 0 ) {
			return new WP_Error( 'cfgd_discount', '割引は「5%」か「1000」の形で入れてください', array( 'status' => 400 ) );
		}
		$until = CFGD_Parsers::parse_until( (string) $req->get_param( 'until' ), time(), wp_timezone() );
		if ( ! $until ) {
			return new WP_Error( 'cfgd_until', '期限は「10/16 0:00」か「10/16」の形で入れてください', array( 'status' => 400 ) );
		}
		// 範囲：「store」か、ショートカットのリストの「店舗全体」なら店舗全体。それ以外（空欄・「この商品だけ」）はこの商品だけ
		// 「Yahoo!全体」「楽天全体」「モール全体」（mall）は、そのモールの全店舗に付ける（一部の店舗が対象外のクーポンも、除外店は分からないので全店扱い）
		$sc    = (string) $req->get_param( 'scope' );
		$scope = $wide || 'mall' === $sc || preg_match( '/Yahoo|ヤフー|楽天|モール/iu', $sc ) ? 'mall'
			: ( 'store' === $sc || str_contains( $sc, '店舗' ) || '' === $shop['item'] ? 'store' : 'item' );

		$wpdb->insert( CFGD_DB::t( 'coupons' ), array(
			'mall'       => $shop['mall'],
			'store_code' => 'mall' === $scope ? '*' : $shop['store'],
			'pct'        => 'pct' === $disc[0] ? $disc[1] : 0,
			'yen'        => 'yen' === $disc[0] ? (int) $disc[1] : 0,
			// 「10% 上限1000」「10%（最大1,000円）」のように書くと上限も入る（Yahoo!全体のクーポンに多い）
			'cap_yen'    => absint( $req->get_param( 'cap' ) ) ?: ( preg_match( '/(?:上限|最大)\s*([\d,]+)/u', mb_convert_kana( (string) $req->get_param( 'discount' ), 'as' ), $cm ) ? (int) str_replace( ',', '', $cm[1] ) : 0 ),
			// 「1500 50000円以上」「5% 3万円以上」のように書くと、最低注文金額も入る
			'min_order'  => absint( $req->get_param( 'min' ) ) ?: self::min_from_text( (string) $req->get_param( 'discount' ) ),
			'start_at'   => current_time( 'mysql' ),
			'end_at'     => $until,
			'note'       => sanitize_text_field( (string) ( $req->get_param( 'note' ) ?: 'スマホから登録' ) ),
			'source'     => 'quick',
			'verified'   => 1,
			'item_key'   => 'item' === $scope ? sanitize_text_field( $shop['item'] ) : '',
		) );

		// 登録したクーポンで今日の判定をやり直す（通知はしない）
		CFGD_Runner::run_judge( false );

		$mall = 'rakuten' === $shop['mall'] ? '楽天' : 'Yahoo!';
		$off  = 'pct' === $disc[0] ? rtrim( rtrim( (string) $disc[1], '0' ), '.' ) . '%OFF' : number_format( (int) $disc[1] ) . '円OFF';
		$msg  = ( 'mall' === $scope ? "{$mall}全体（全店舗）" : "{$mall} {$shop['store']}" . ( 'item' === $scope ? '（この商品）' : '（店舗全体）' ) ) . "に{$off}を登録しました。期限 " . wp_date( 'n/j H:i', strtotime( $until . ' ' . wp_timezone_string() ) );
		return rest_ensure_response( array( 'ok' => true, 'message' => $msg ) );
	}

	/** ページキャッシュとぶつからないよう、バナーはJSから後読みする。 */
	public static function banner( WP_REST_Request $req ) {
		$deals = get_option( 'cfgd_deals', array() );
		$now   = wp_date( 'Y-m-d H:i:s' );
		$deals = array_values( array_filter( $deals, fn( $d ) => $d['until'] >= $now ) );
		if ( ! $deals || ! CFGD_Settings::get( 'banner_enabled' ) ) {
			return rest_ensure_response( array( 'deal' => null ) );
		}

		// ページのタグ・カテゴリと商品タグが重なるものを優先
		$terms = array();
		if ( $pid = $req->get_param( 'post_id' ) ) {
			foreach ( array( 'post_tag', 'category' ) as $tax ) {
				$names = wp_get_post_terms( $pid, $tax, array( 'fields' => 'names' ) );
				if ( ! is_wp_error( $names ) ) {
					$terms = array_merge( $terms, $names );
				}
			}
		}
		usort( $deals, function ( $a, $b ) use ( $terms ) {
			$ra = self::relevance( $a['tags'], $terms );
			$rb = self::relevance( $b['tags'], $terms );
			return $rb <=> $ra ?: ( (int) ( $a['verdict']['diff'] ?? 0 ) <=> (int) ( $b['verdict']['diff'] ?? 0 ) );
		} );
		$d    = $deals[0];
		$b    = $d['best'];
		$line = '';
		if ( 'store' === ( $d['type'] ?? '' ) ) {
			// 店舗まとめ：そのページに関係のある品番をリンク先にする
			$prods = $d['products'];
			usort( $prods, fn( $x, $y ) => self::relevance( $y['tags'], $terms ) <=> self::relevance( $x['tags'], $terms ) );
			$p     = $prods[0];
			$b     = $p['best'];
			$n     = count( array_unique( array_column( $d['products'], 'model' ) ) );
			$line  = $p['name'] . ' 実質' . number_format( (int) $b['eff_price'] ) . '円' . ( $n > 1 ? ' ほか' . ( $n - 1 ) . '機種' : '' );
			$d['image'] = $p['image'];
		}
		$resp = array(
			'deal' => array(
				'key'      => $d['slug'] . '-' . wp_date( 'Ymd' ),
				'type'     => $d['type'] ?? 'product',
				'name'     => 'store' === ( $d['type'] ?? '' ) ? $d['name'] . '　' . $d['verdict']['reason'] : $d['name'],
				'line'     => $line,
				'mall'     => 'rakuten' === $b['mall'] ? '楽天' : 'Yahoo!',
				'price'    => $b['price'],
				'eff'      => $b['eff_price'],
				'points'   => $b['points'],
				'coupon'   => $b['coupon_yen'],
				'rate'     => self::point_rate( (int) $b['price'], (int) $b['coupon_yen'], (int) $b['points'] ),
				'reason'   => $d['verdict']['reason'],
				'url'      => $b['url'],
				'guide'    => esc_url_raw( (string) CFGD_Settings::get( 'guide_url' ) ),
				'image'    => $d['image'] ?? '',
				'lines'    => $b['lines'],
				'possible' => $b['possible'],
			),
		);
		$r = rest_ensure_response( $resp );
		$r->header( 'Cache-Control', 'public, max-age=600' );
		return $r;
	}

	private static function relevance( $tags, array $terms ) {
		$tags = array_filter( array_map( 'trim', explode( ',', (string) $tags ) ) );
		return count( array_intersect( $tags, $terms ) );
	}

	public static function assets() {
		if ( is_admin() || ! CFGD_Settings::get( 'banner_enabled' ) ) {
			return;
		}
		wp_enqueue_style( 'cfgd-banner', CFGD_URL . 'assets/banner.css', array(), CFGD_VERSION );
		wp_enqueue_script( 'cfgd-banner', CFGD_URL . 'assets/banner.js', array(), CFGD_VERSION, array( 'in_footer' => true, 'strategy' => 'defer' ) );
		wp_localize_script( 'cfgd-banner', 'CFGD', array(
			'endpoint' => esc_url_raw( rest_url( 'cfgd/v1/banner' ) ),
			'postId'   => is_singular() ? get_the_ID() : 0,
		) );
	}

	/**
	 * [cfgd_calendar days="21"]
	 * 紹介ページ用：今後のお得日（確定・予想）を日付順に並べる。
	 */
	/**
	 * 価格カタログ（今日の価格）：記録している全品番を、カテゴリ（商品タグ）ごと・機種ごとに1枚のカードで出す。
	 * 買い時の品番には赤いラベル。品番ごとの行は折りたたみ。
	 *
	 * [cfgd_catalog]                                  … 全カテゴリ
	 * [cfgd_catalog cats="電動リール:電動リール"]     … 1カテゴリだけ（該当0件なら空文字）
	 * [cfgd_catalog cats="電動リール:電動リール|リール:ベイトリール|竿:テンヤ竿"]
	 */
	public static function shortcode_catalog( $atts ) {
		$atts = shortcode_atts( array( 'cats' => '電動リール:電動リール|リール:ベイトリール|竿:テンヤ竿' ), $atts );
		$cats = array();
		foreach ( explode( '|', (string) $atts['cats'] ) as $c ) {
			$kv = array_map( 'trim', explode( ':', $c, 2 ) );
			if ( '' !== $kv[0] ) {
				$cats[ $kv[0] ] = ( $kv[1] ?? '' ) !== '' ? $kv[1] : $kv[0];
			}
		}
		if ( ! $cats ) {
			return '';
		}
		$single = 1 === count( $cats );

		// 今日の買い時（品番ID → [種類, 理由, 出品]）
		$labels = array();
		$now    = wp_date( 'Y-m-d H:i:s' );
		foreach ( (array) get_option( 'cfgd_deals', array() ) as $d ) {
			if ( ( $d['until'] ?? '' ) < $now ) {
				continue;
			}
			if ( 'store' === ( $d['type'] ?? '' ) ) {
				foreach ( (array) $d['products'] as $p ) {
					$labels[ (int) ( $p['product_id'] ?? 0 ) ] = array( 'store', $d['name'] . '：' . $d['verdict']['reason'], $p['best'] );
				}
			} elseif ( ! empty( $d['product_id'] ) ) {
				$labels[ (int) $d['product_id'] ] = array( 'history', '記録した範囲の実質最安圏', $d['best'] );
			}
		}

		// カテゴリ → 機種 → 品番
		$groups  = array();
		$latest  = '';
		foreach ( CFGD_DB::products_with_offers() as $p ) {
			$tags = array_map( 'trim', explode( ',', (string) $p->tags ) );
			$cat  = null;
			foreach ( array_keys( $cats ) as $c ) {
				if ( in_array( $c, $tags, true ) ) {
					$cat = $c;
					break;
				}
			}
			if ( null === $cat ) {
				continue;
			}
			$best = null;
			foreach ( CFGD_DB::latest_rows( $p->id ) as $r ) {
				if ( $r->fetched_at > $latest ) {
					$latest = $r->fetched_at;
				}
				if ( $r->in_stock && ( ! $best || (int) $r->eff_price < (int) $best['eff'] ) ) {
					$best = array(
						'eff'   => (int) $r->eff_price,
						'price' => (int) $r->price,
						'rate'  => self::point_rate( (int) $r->price, (int) $r->coupon_yen, (int) $r->points_total ),
						'mall'  => $r->mall,
						'store' => $r->store_code,
						'url'   => ( CFGD_DB::afflink_for( $r->mall, $r->store_code, (string) $r->offer_item_code ) ?: $r->url ),
					);
				}
			}
			$deal = $labels[ (int) $p->id ] ?? null;
			if ( $deal ) {
				// 買い時の出品（店舗の目安なら、その店舗）の価格とリンクを見せる
				$b    = $deal[2];
				$best = array(
					'eff'   => (int) $b['eff_price'],
					'price' => (int) $b['price'],
					'rate'  => self::point_rate( (int) $b['price'], (int) $b['coupon_yen'], (int) $b['points'] ),
					'mall'  => $b['mall'],
					'store' => $b['store'],
					'url'   => $b['url'],
				);
			}
			$model = $p->model ? $p->model : $p->name;
			if ( ! isset( $groups[ $cat ][ $model ] ) ) {
				$groups[ $cat ][ $model ] = array( 'image' => '', 'items' => array() );
			}
			if ( ! $groups[ $cat ][ $model ]['image'] && ! empty( $p->image_url ) ) {
				$groups[ $cat ][ $model ]['image'] = $p->image_url;
			}
			$groups[ $cat ][ $model ]['items'][] = array( 'name' => $p->name, 'best' => $best, 'deal' => $deal );
		}
		if ( ! $groups ) {
			return '';
		}

		$asof = $latest ? wp_date( 'n月j日 G時', strtotime( $latest ) ) . '時点' : '';
		ob_start();
		echo '<div class="cfgd-catalog">';
		printf(
			'<p class="cfgd-catalog__note"><span class="cfgd-catalog__pr">PR</span>%s楽天・Yahoo!の主な釣具店のうち在庫のある店舗で、記録した範囲の実質価格がいちばん安いものを表示しています。実質価格は、クーポンとポイント（運営者の条件で計算）を引いた額です。購入前に販売ページでご確認ください。</p>',
			esc_html( $asof ? $asof . '・' : '' )
		);
		foreach ( $cats as $tag => $label ) {
			if ( empty( $groups[ $tag ] ) ) {
				continue;
			}
			if ( ! $single ) {
				echo '<h3 class="cfgd-catalog__cat">' . esc_html( $label ) . '</h3>';
			}
			echo '<div class="cfgd-catalog__grid">';
			foreach ( $groups[ $tag ] as $model => $g ) {
				self::catalog_card( $model, $g );
			}
			echo '</div>';
		}
		echo '</div>';
		return ob_get_clean();
	}

	/** 機種カード1枚。 */
	private static function catalog_card( $model, array $g ) {
		$items  = $g['items'];
		$labels = CFGD_Parsers::variant_labels( array_column( $items, 'name' ) );
		$hot    = array_values( array_filter( $items, fn( $it ) => $it['deal'] ) );
		$prices = array_filter( array_map( fn( $it ) => $it['best']['eff'] ?? null, $items ) );
		$from   = $prices ? min( $prices ) : null;
		$rates  = array_filter( array_map( fn( $it ) => $it['best']['rate'] ?? null, $items ) );
		$top    = $rates ? max( $rates ) : 0;

		echo '<section class="cfgd-card' . ( $hot ? ' cfgd-card--hot' : '' ) . '">';
		echo '<div class="cfgd-card__head">';
		if ( $g['image'] ) {
			printf( '<img class="cfgd-card__img" src="%s" alt="%s" width="80" height="80" loading="lazy" referrerpolicy="no-referrer">', esc_url( $g['image'] ), esc_attr( $model ) );
		}
		echo '<div class="cfgd-card__title"><div class="cfgd-card__model">' . esc_html( $model ) . '</div>';
		if ( null !== $from ) {
			echo '<div class="cfgd-card__from">実質<b>' . esc_html( number_format( $from ) ) . '円</b>' . ( count( $items ) > 1 ? '〜' : '' ) . '</div>';
			if ( $top >= 1 ) {
				printf( '<span class="cfgd-pt%s">ポイント%s%s%%還元</span>', $top >= 15 ? ' is-high' : '', count( $items ) > 1 ? '最大' : '', esc_html( self::fmt_rate( $top ) ) );
			}
		} else {
			echo '<div class="cfgd-card__from is-none">在庫のある店舗なし</div>';
		}
		if ( $hot ) {
			echo '<span class="cfgd-badge">今日が買い時</span>';
			echo '<small class="cfgd-card__why">' . esc_html( $hot[0]['deal'][1] ) . '</small>';
		}
		echo '</div></div>';

		$rows = '';
		foreach ( $items as $i => $it ) {
			$b     = $it['best'];
			$badge = $it['deal'] ? '<span class="cfgd-badge cfgd-badge--sm">' . esc_html( 'store' === $it['deal'][0] ? '店舗が買い時' : '最安圏' ) . '</span>' : '';
			if ( ! $b ) {
				$rows .= '<li class="cfgd-card__row is-none"><span class="cfgd-card__var">' . esc_html( $labels[ $i ] ) . '</span><span class="cfgd-card__none">在庫なし</span></li>';
				continue;
			}
			$rows .= sprintf(
				'<li class="cfgd-card__row%s"><span class="cfgd-card__var">%s%s</span><span class="cfgd-card__eff">実質%s円<small class="cfgd-card__pt">ポイント%s%%</small></span><span class="cfgd-card__shop">%s</span><a class="cfgd-card__btn" href="%s" target="_blank" rel="sponsored noopener" data-nodal>見る</a></li>',
				$it['deal'] ? ' is-hot' : '',
				esc_html( $labels[ $i ] ),
				$badge,
				esc_html( number_format( $b['eff'] ) ),
				esc_html( self::fmt_rate( (float) ( $b['rate'] ?? 0 ) ) ),
				esc_html( self::short_store( $b['mall'], $b['store'] ) ),
				esc_url( $b['url'] )
			);
		}
		if ( count( $items ) > 1 ) {
			printf( '<details class="cfgd-card__more"><summary>品番ごとの価格（%d）</summary><ul class="cfgd-card__list">%s</ul></details>', count( $items ), $rows ); // phpcs:ignore — 上で組み立て済み
		} else {
			echo '<ul class="cfgd-card__list">' . $rows . '</ul>'; // phpcs:ignore
		}
		echo '</section>';
	}

	/** ポイント還元率（クーポン後の税抜額に対する%。Yahoo!の商品ページの「獲得◯%」と同じ考え方）。 */
	private static function point_rate( $price, $coupon, $points ) {
		$base = intdiv( max( 0, $price - $coupon ) * 10, 11 );
		return $base > 0 ? round( 100 * $points / $base, 1 ) : 0.0;
	}

	private static function fmt_rate( $r ) {
		return rtrim( rtrim( number_format( (float) $r, 1 ), '0' ), '.' );
	}

	/** 行に出す短い店名（「釣具のキャスティング ヤフー店」→「キャスティング Yahoo!」など）。 */
	private static function short_store( $mall, $code ) {
		$name = CFGD_Runner::store_name( $mall, $code );
		$name = preg_replace( '/^(釣具の|つり具の|釣具)\s*/u', '', $name );
		$name = preg_replace( '/\s*(ヤフー店|Yahoo!?店|Yahoo!?ショップ|Yahoo!?ショッピング店|楽天市場店|楽天店)$/u', '', $name );
		$name = preg_replace( '/^(Yahoo! |楽天 )/u', '', $name );
		return trim( $name ) . ( 'rakuten' === $mall ? '（楽天）' : '（Yahoo!）' );
	}

	public static function shortcode_calendar( $atts ) {
		global $wpdb;
		$atts  = shortcode_atts( array( 'days' => 21 ), $atts );
		$days  = max( 1, min( 60, (int) $atts['days'] ) );
		$table = CFGD_DB::t( 'campaigns' );
		$rows  = $wpdb->get_results( "SELECT * FROM $table WHERE status IN ('confirmed','hint','info')" ); // phpcs:ignore

		$by_day = array();
		for ( $i = 0; $i < $days; $i++ ) {
			$ts  = strtotime( wp_date( 'Y-m-d 12:00:00' ) ) + DAY_IN_SECONDS * $i;
			$key = wp_date( 'Y-m-d', $ts );
			foreach ( $rows as $r ) {
				$hit = 'hint' === $r->status || 'info' === $r->status
					? ( $r->start_at && substr( $r->start_at, 0, 10 ) <= $key && $key <= substr( $r->end_at, 0, 10 ) )
					: CFGD_DB::campaign_matches( $r, $ts );
				if ( $hit ) {
					$by_day[ $key ][] = $r;
				}
			}
		}

		ob_start();
		echo '<div class="cfgd-cal">';
		foreach ( $by_day as $day => $list ) {
			$ts = strtotime( $day . ' 12:00:00' );
			echo '<div class="cfgd-cal__day"><div class="cfgd-cal__date">' . esc_html( wp_date( 'n/j（D）', $ts ) ) . '</div><ul>';
			foreach ( $list as $r ) {
				$mall = 'rakuten' === $r->mall ? '楽天' : 'Yahoo!';
				$rate = null !== $r->rate_pct ? ( $r->is_max ? '最大' : '' ) . '+' . rtrim( rtrim( $r->rate_pct, '0' ), '.' ) . '%' : '';
				$cap  = (int) $r->cap_yen > 0 ? '（上限' . number_format( (int) $r->cap_yen ) . '円）' : '';
				$tag  = 'hint' === $r->status ? '<span class="cfgd-tag">予想</span>' : ( 'limited' === $r->scope ? '<span class="cfgd-tag">対象ストア限定</span>' : '' );
				printf(
					'<li class="cfgd-cal__item cfgd-cal__item--%1$s"><b>%2$s</b> %3$s %4$s%5$s %6$s</li>',
					esc_attr( $r->mall ),
					esc_html( $mall ),
					esc_html( $r->name ),
					esc_html( $rate ),
					esc_html( $cap ),
					$tag // phpcs:ignore — 固定文字列
				);
			}
			echo '</ul></div>';
		}
		echo '<p class="cfgd-cal__note">※Yahoo!は公式カレンダー、楽天は日付ルールと公開情報から作成しています。予想は告知前の見込みです。内容は変わることがあるため、購入前に各モールでご確認ください。</p>';
		echo '</div>';
		return ob_get_clean();
	}
}
