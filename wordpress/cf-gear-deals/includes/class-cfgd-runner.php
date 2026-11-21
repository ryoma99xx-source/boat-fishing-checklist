<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class CFGD_Runner {

	private static $log    = array();
	private static $alerts = array();

	private static function log( $msg, $alert = false ) {
		self::$log[] = wp_date( 'H:i:s' ) . ' ' . $msg;
		if ( $alert ) {
			self::$alerts[] = $msg;
		}
	}

	const STATE = 'cfgd_run_state';

	/**
	 * 毎日の本処理：カレンダー → 価格 → 判定 → 通知。
	 * 価格取得は出品数×1秒以上かかるので、40秒ずつ区切って続きを予約する
	 * （WP-CLI のときは最後まで一気に進める）。
	 */
	public static function run() {
		self::$log    = array();
		self::$alerts = array();
		self::run_calendars();
		self::run_shop_pages();
		self::resolve_jans();
		update_option( self::STATE, array(
			'started' => time(),
			'done'    => array(),
			'stats'   => array( 'rak_up' => 0, 'rak_all' => 0, 'skipped' => 0 ),
			'log'     => self::$log,
			'alerts'  => self::$alerts,
		), false );
		if ( defined( 'WP_CLI' ) && WP_CLI ) {
			return self::continue_run();
		}
		// 画面からの実行やWP-Cronでは、ここで一度区切る（サーバーの時間制限対策）
		update_option( 'cfgd_last_log', array_merge( self::$log, array( '… 価格取得の準備ができました（自動で続けます）' ) ), false );
		wp_schedule_single_event( time() + 5, 'cfgd_run_continue' );
		return self::$log;
	}

	/** 途中の実行があれば続きを進める。終わったら判定・通知まで行う。 */
	public static function continue_run() {
		$state = get_option( self::STATE );
		if ( ! $state ) {
			return (array) get_option( 'cfgd_last_log', array() );
		}
		if ( get_transient( 'cfgd_step_lock' ) ) {
			return $state['log'];
		}
		set_transient( 'cfgd_step_lock', 1, 120 );
		@set_time_limit( 120 ); // phpcs:ignore

		self::$log    = $state['log'];
		self::$alerts = $state['alerts'];
		$cli          = defined( 'WP_CLI' ) && WP_CLI;
		$deadline     = $cli ? PHP_INT_MAX : time() + 40;
		$left         = self::run_prices( $state, $deadline );
		if ( 0 === $left && (int) CFGD_Settings::get( 'yahoo_compare' ) === 1 ) {
			// 価格のあとに、Yahoo!の価格比較ページで今日のボーナスストアPlus対象店を確かめる（機種ごとに1ページ）
			$left = self::run_compare_pages( $state, $deadline );
		}

		if ( $left > 0 ) {
			$state['log']    = self::$log;
			$state['alerts'] = self::$alerts;
			update_option( self::STATE, $state, false );
			update_option( 'cfgd_last_log', array_merge( self::$log, array( '… 価格取得中 ' . count( $state['done'] ) . '件済み・残り' . $left . '件（自動で続けます）' ) ), false );
			if ( ! wp_next_scheduled( 'cfgd_run_continue' ) ) {
				wp_schedule_single_event( time() + 30, 'cfgd_run_continue' );
			}
			delete_transient( 'cfgd_step_lock' );
			return self::$log;
		}

		self::finish_prices( $state );
		delete_option( self::STATE );
		self::run_yahoo_bsplus( $state['cmp'] ?? array(), $state['cmp_seen'] ?? array() );
		update_option( 'cfgd_bonus_today', array( 'd' => wp_date( 'Y-m-d' ), 'stores' => array_keys( $state['cmp_bonus'] ?? array() ) ), false );
		self::run_judge( true );
		self::send_alerts();
		self::log( '完了（' . round( ( time() - $state['started'] ) / 60, 1 ) . '分）' );
		update_option( 'cfgd_last_log', self::$log, false );
		delete_transient( 'cfgd_step_lock' );
		return self::$log;
	}

	/** 価格取得の進み具合 [済み, 全体]。実行中でなければ null。 */
	public static function progress() {
		$state = get_option( self::STATE );
		if ( ! $state ) {
			return null;
		}
		$total = 0;
		foreach ( CFGD_DB::products_with_offers() as $p ) {
			if ( $p->jan ) {
				$total += count( $p->offers );
			}
		}
		return array( count( $state['done'] ), $total );
	}

	public static function run_calendars() {
		$s = CFGD_Settings::all();

		// Yahoo!（公式・HTMLに日程と上限が入っている）
		$html = CFGD_Fetch::page( $s['yahoo_calendar_url'] );
		if ( is_wp_error( $html ) ) {
			self::log( 'Yahoo!カレンダー取得失敗: ' . $html->get_error_message(), true );
		} else {
			$items = CFGD_Parsers::parse_yahoo_calendar( CFGD_Parsers::html_to_lines( $html ), time() );
			if ( ! $items ) {
				self::log( 'Yahoo!カレンダーから施策を読み取れなかった（ページ構造が変わった可能性）', true );
			}
			foreach ( $items as $it ) {
				$is_period = isset( $it['start'] );
				CFGD_DB::upsert_campaign( array(
					'mall'       => 'yahoo',
					'name'       => $it['name'],
					'start_at'   => $is_period ? $it['start'] : $it['date'] . ' 00:00:00',
					'end_at'     => $is_period ? $it['end'] : $it['date'] . ' 23:59:59',
					'rate_pct'   => $it['rate'],
					'cap_yen'    => $it['cap'],
					'is_max'     => $it['is_max'],
					'scope'      => $it['limited'] ? 'limited' : 'all',
					'conditions' => mb_substr( $it['conditions'], 0, 250 ),
					// 「最大◯%」の期間イベントは他施策込みの合計表記なので、加算せず情報扱い
					'status'     => ( $is_period && $it['is_max'] ) ? 'info' : 'confirmed',
					'source'     => 'yahoo_cal',
				) );
			}
			self::log( 'Yahoo!カレンダー: ' . count( $items ) . '件' );
		}

		// 楽天（ユーザー投稿カレンダー → 予想として保存、確定は手動）
		$html = CFGD_Fetch::page( $s['rakuten_calendar_url'] );
		if ( is_wp_error( $html ) ) {
			self::log( '楽天カレンダー取得失敗: ' . $html->get_error_message(), true );
		} else {
			$items = CFGD_Parsers::parse_rakuten_calendar( CFGD_Parsers::html_to_lines( $html ) );
			$new   = 0;
			foreach ( $items as $it ) {
				if ( 'fivezero' === $it['kind'] || 'wonderful' === $it['kind'] ) {
					continue; // 日付ルールで持っている
				}
				list( $state ) = CFGD_DB::upsert_campaign( array(
					'mall'     => 'rakuten',
					'name'     => $it['name'],
					'start_at' => $it['start'],
					'end_at'   => $it['end'],
					'status'   => 'hint',
					'source'   => 'rakuten_cal',
				), false );
				if ( 'inserted' === $state && strtotime( $it['end'] ) > time() ) {
					$new++;
					self::log( "楽天の予定を検知：{$it['name']} {$it['start']}〜{$it['end']}（管理画面で倍率・上限を入れて確定してください）", true );
				}
			}
			self::log( '楽天カレンダー: ' . count( $items ) . "件（新規{$new}）" );
		}

		// 楽天「勝ったら倍」：公開ページの開催日一覧に今日があれば加算（1回1,000ptまで・要エントリー）
		$html = CFGD_Fetch::page( 'https://event.rakuten.co.jp/campaign/sports/' );
		if ( ! is_wp_error( $html ) ) {
			$today = wp_date( 'Y-m-d' );
			$plus  = CFGD_Parsers::parse_rakuten_sports( CFGD_Parsers::html_to_lines( $html ), $today );
			if ( null !== $plus ) {
				CFGD_DB::upsert_campaign( array(
					'mall'       => 'rakuten',
					'name'       => '勝ったら倍',
					'start_at'   => $today . ' 00:00:00',
					'end_at'     => $today . ' 23:59:59',
					'rate_pct'   => $plus,
					'cap_yen'    => 1000,
					'conditions' => '要エントリー（開催日ごと）',
					'status'     => 'confirmed',
					'source'     => 'rakuten_sports',
				) );
				self::log( "楽天 勝ったら倍：本日 +{$plus}倍（上限1,000pt）" );
			}
		}
		return self::$log;
	}

	/**
	 * 楽天の店舗トップを未ログインで1日1回読み、
	 * ショップ全体の倍率・クーポン見出し・3商品同時購入企画を反映する。
	 */
	public static function run_shop_pages() {
		global $wpdb;
		if ( ! CFGD_Settings::get( 'rakuten_shop_pages' ) ) {
			return;
		}
		$ot     = CFGD_DB::t( 'offers' );
		$ct     = CFGD_DB::t( 'coupons' );
		$codes  = $wpdb->get_col( "SELECT DISTINCT store_code FROM $ot WHERE mall='rakuten' AND active=1" ); // phpcs:ignore
		$rates  = array();
		$today0 = wp_date( 'Y-m-d 00:00:00' );
		$today9 = wp_date( 'Y-m-d 23:59:59' );

		foreach ( $codes as $code ) {
			$html = CFGD_Fetch::page( 'https://www.rakuten.co.jp/' . rawurlencode( $code ) . '/' );
			if ( is_wp_error( $html ) ) {
				self::log( "楽天 {$code} 店舗トップ取得失敗: " . $html->get_error_message() );
				continue;
			}
			$info = CFGD_Parsers::parse_rakuten_shop( CFGD_Parsers::html_to_lines( $html ) );

			if ( $info['shop_rate'] ) {
				$rates[ $code ] = $info['shop_rate'];
			}

			// その日のクーポン見出しで入れ替える（消えたクーポンは自然に外れる）
			$wpdb->query( $wpdb->prepare( "DELETE FROM $ct WHERE mall='rakuten' AND store_code=%s AND source='shop_page'", $code ) ); // phpcs:ignore
			foreach ( $info['coupons'] as $c ) {
				$wpdb->insert( $ct, array(
					'mall'       => 'rakuten',
					'store_code' => $code,
					'pct'        => 'pct' === $c['type'] ? $c['value'] : 0,
					'yen'        => 'yen' === $c['type'] ? $c['value'] : 0,
					'cap_yen'    => 0,
					'min_order'  => 0,
					'start_at'   => $today0,
					'end_at'     => $today9,
					'note'       => '店舗トップの見出し・条件は未確認',
					'source'     => 'shop_page',
					'verified'   => 0,
				) );
			}

			// 3商品同時購入企画（キャスティング・ポイントでたまにある）
			if ( $info['triple'] ) {
				$t = $info['triple'];
				CFGD_DB::upsert_campaign( array(
					'mall'       => 'rakuten',
					'name'       => "3点以上購入で+{$t['rate']}倍（{$code}）",
					'start_at'   => $today0,
					'end_at'     => $today9,
					'rate_pct'   => $t['rate'],
					'cap_yen'    => $t['cap'],
					'scope'      => 'limited',
					'stores'     => $code,
					'conditions' => ( $t['min_unit'] ? '1商品' . number_format( $t['min_unit'] ) . '円以上を' : '' ) . '3点以上購入' . ( $t['entry'] ? '・要エントリー' : '' ),
					'status'     => 'confirmed',
					'source'     => 'shop_page',
				) );
				self::log( "楽天 {$code}: 3点以上購入で+{$t['rate']}倍（上限" . number_format( $t['cap'] ) . 'pt）を検知', true );
			}

			$parts = array();
			if ( $info['shop_rate'] ) {
				$parts[] = "ショップ{$info['shop_rate']}倍";
			}
			if ( $info['coupons'] ) {
				$parts[] = 'クーポン' . implode( '・', array_map( fn( $c ) => 'pct' === $c['type'] ? $c['value'] . '%' : number_format( $c['value'] ) . '円', $info['coupons'] ) );
			}
			self::log( "楽天 {$code} 店舗トップ: " . ( $parts ? implode( '／', $parts ) : '特になし' ) );
		}
		update_option( 'cfgd_rak_shop_rates', array( 'd' => wp_date( 'Y-m-d' ), 'rates' => $rates ), false );
	}

	/**
	 * Yahoo!ボーナスストアPlusの対象判定（1日1回）。
	 * 公式ページの上位倍率（+9%など）のリストに載っていればその倍率、
	 * 載っていなくても商品ページに「デイリーボーナスプラス対象」バッジがあれば最低倍率（+4%など）。
	 */
	/**
	 * Yahoo!の価格比較ページ（未ログインでも店ごとに「デイリーボーナスプラス」とポイント%が出る）を機種ごとに1ページ読み、
	 * 今日のボーナスストアPlus対象店と倍率を集める。結果は $state['cmp'][店] = 倍率、$state['cmp_seen'][店] = true。
	 *
	 * @return int 残りの機種数
	 */
	public static function run_compare_pages( array &$state, $deadline ) {
		global $wpdb;
		$state['cmp']      = $state['cmp'] ?? array();
		$state['cmp_seen'] = $state['cmp_seen'] ?? array();
		$state['cmp_done'] = $state['cmp_done'] ?? array();
		$pt                = CFGD_DB::t( 'products' );
		$models            = array();
		foreach ( CFGD_DB::products_with_offers() as $p ) {
			if ( $p->jan ) {
				$models[ $p->model ? $p->model : $p->name ][] = $p;
			}
		}
		$left = 0;
		foreach ( $models as $model => $list ) {
			if ( in_array( $model, $state['cmp_done'], true ) ) {
				continue;
			}
			if ( time() >= $deadline ) {
				$left++;
				continue;
			}
			$state['cmp_done'][] = $model;

			$res = self::compare_model( $list );
			if ( $res['error'] ) {
				self::log( "価格比較ページ（{$model}）: {$res['error']}" );
				continue;
			}
			$hits = array();
			foreach ( $res['rows'] as $store => $row ) {
				$state['cmp_seen'][ $store ] = true;
				if ( ! empty( $row['bonus'] ) || ! empty( $row['bsp'] ) ) {
					$state['cmp_bonus'][ $store ] = true;
				}
				if ( $row['rate'] > 0 ) {
					$state['cmp'][ $store ] = max( (float) ( $state['cmp'][ $store ] ?? 0 ), $row['rate'] );
					$hits[]                 = "{$store} +{$row['rate']}%";
				}
			}
			self::log( "価格比較ページ（{$model}）: " . count( $res['rows'] ) . '店' . ( $hits ? '、ボーナスストアPlus ' . implode( ', ', $hits ) : '' ) );
		}
		return $left;
	}

	/**
	 * 1機種ぶん：価格比較ページのIDを見つけ（なければYahoo!の商品ページから）、ページを読んで店ごとのボーナスストアPlus倍率を出す。
	 *
	 * @return array ['id'=>, 'product'=>品番名, 'rows'=>[店=>行+rate], 'error'=>'']
	 */
	public static function compare_model( array $list ) {
		global $wpdb;
		$pt   = CFGD_DB::t( 'products' );
		$prod = null;
		foreach ( $list as $p ) {
			if ( ! empty( $p->yahoo_product_id ) ) {
				$prod = $p;
				break;
			}
		}
		if ( ! $prod ) {
			$tried = 0;
			foreach ( $list as $p ) {
				foreach ( $p->offers as $o ) {
					if ( 'yahoo' !== $o->mall || ! $o->item_code || $tried >= 3 ) {
						continue;
					}
					$tried++;
					$key  = preg_replace( '/^[^_]+_/', '', $o->item_code );
					$page = CFGD_Fetch::page( 'https://store.shopping.yahoo.co.jp/' . rawurlencode( $o->store_code ) . '/' . rawurlencode( $key ) . '.html' );
					$id   = is_wp_error( $page ) ? '' : CFGD_Parsers::yahoo_product_id( $page );
					if ( $id ) {
						$wpdb->update( $pt, array( 'yahoo_product_id' => $id ), array( 'id' => $p->id ) );
						$p->yahoo_product_id = $id;
						$prod                = $p;
						break 2;
					}
				}
			}
		}
		if ( ! $prod ) {
			return array( 'id' => '', 'product' => '', 'rows' => array(), 'error' => '商品ページに価格比較ページへのリンクがなかった（Yahoo!の商品コード未取得の場合も）' );
		}
		$html = CFGD_Fetch::page( 'https://shopping.yahoo.co.jp/products/' . rawurlencode( $prod->yahoo_product_id ) );
		if ( is_wp_error( $html ) ) {
			return array( 'id' => $prod->yahoo_product_id, 'product' => $prod->name, 'rows' => array(), 'error' => '価格比較ページを開けなかった（' . $html->get_error_message() . '）' );
		}
		$rows = CFGD_Parsers::parse_yahoo_products( $html );
		if ( ! $rows ) {
			return array( 'id' => $prod->yahoo_product_id, 'product' => $prod->name, 'rows' => array(), 'error' => '価格比較ページは開けたが、店の行を読み取れなかった' );
		}
		// 同じ品番・同じ店のAPIの価格とストアポイントで倍率を推定
		$api = array();
		foreach ( CFGD_DB::latest_rows( $prod->id ) as $r ) {
			if ( 'yahoo' === $r->mall ) {
				$api[ strtolower( $r->store_code ) ] = $r;
			}
		}
		// 今日のボーナスストアPlusの上乗せ分（さらに+2%・優良ストアでさらに+3% など）
		// ＋ BONUS店に付く「対象ストア限定」の企画（爆買WEEK・感謝デーなど）。未ログインの表示にはこれも含まれるので差し引く
		// （10/31 爆買WEEK+4%を含んだ表示から、キャスティングの+4%を+9%と誤判定した）
		$addon = 0.0;
		$lim   = 0.0;
		foreach ( CFGD_DB::active_campaigns( 'yahoo', time() ) as $c ) {
			$name = (string) $c->name;
			if ( str_contains( $name, 'ボーナスストアPlus' ) ) {
				if ( str_contains( $name, 'さらに' ) ) {
					$addon += (float) $c->rate_pct;
				}
			} elseif ( 'limited' === $c->scope && null !== $c->rate_pct ) {
				$lim += (float) $c->rate_pct;
			}
		}
		foreach ( $rows as $store => $row ) {
			$a                      = $api[ $store ] ?? null;
			$sub                    = $addon + ( ! empty( $row['bonus'] ) || ! empty( $row['bsp'] ) ? $lim : 0.0 );
			$rows[ $store ]['rate'] = CFGD_Parsers::bsp_rate_from_row( $row, $a ? (int) $a->store_points : 0, $a ? (int) $a->price : 0, $sub );
		}
		return array( 'id' => $prod->yahoo_product_id, 'product' => $prod->name, 'rows' => $rows, 'error' => '' );
	}

	/** 管理画面の「価格比較ページを確認」：全機種を試して結果を保存する（判定には使わない）。 */
	public static function compare_check() {
		$models = array();
		foreach ( CFGD_DB::products_with_offers() as $p ) {
			if ( $p->jan ) {
				$models[ $p->model ? $p->model : $p->name ][] = $p;
			}
		}
		$out = array();
		foreach ( $models as $model => $list ) {
			$out[ $model ] = self::compare_model( $list );
		}
		update_option( 'cfgd_compare_check', array( 'at' => wp_date( 'Y-m-d H:i' ), 'models' => $out ), false );
		return $out;
	}

	/**
	 * @param array $cmp  価格比較ページで分かった対象店 [店 => 倍率]
	 * @param array $seen 価格比較ページに出てきた店 [店 => true]（出てきてラベルがなければ対象外と確定）
	 */
	public static function run_yahoo_bsplus( array $cmp = array(), array $seen = array() ) {
		global $wpdb;
		$ot    = CFGD_DB::t( 'offers' );
		$html  = CFGD_Fetch::page( 'https://shopping.yahoo.co.jp/promotion/campaign/bsplus/' );
		$tiers = is_wp_error( $html ) ? array() : CFGD_Parsers::parse_yahoo_bsplus( $html );
		if ( ! $tiers ) {
			// ページが読めない日は+9%/+4%（上限10,000/5,000円）で判定だけ行う
			$tiers = array( array( 'rate' => 9.0, 'cap' => 10000, 'stores' => array() ), array( 'rate' => 4.0, 'cap' => 5000, 'stores' => array() ) );
			self::log( 'ボーナスストアPlusのページを読めなかったため、倍率は+9%/+4%の既定値で判定' );
		}
		$low   = end( $tiers );
		$found = array();

		$stores = $wpdb->get_results( "SELECT store_code, MAX(item_code) AS item_code FROM $ot WHERE mall='yahoo' AND active=1 AND item_code<>'' GROUP BY store_code" ); // phpcs:ignore
		foreach ( $stores as $st ) {
			$code = strtolower( $st->store_code );
			$tier = null;
			foreach ( $tiers as $t ) {
				if ( $t !== $low && in_array( $code, $t['stores'], true ) ) {
					$tier = $t;
					break;
				}
			}
			if ( ! $tier && isset( $cmp[ $code ] ) ) {
				$r    = (float) $cmp[ $code ];
				$tier = array( 'rate' => $r, 'cap' => $r >= 9 ? 10000 : 5000, 'stores' => array() );
			}
			if ( ! $tier && ! isset( $seen[ $code ] ) ) {
				// 価格比較ページに出てこなかった店だけ、商品コード「store_pagekey」から商品ページを1つ開いてバッジを見る
				$key  = preg_replace( '/^[^_]+_/', '', $st->item_code );
				$page = CFGD_Fetch::page( 'https://store.shopping.yahoo.co.jp/' . rawurlencode( $st->store_code ) . '/' . rawurlencode( $key ) . '.html' );
				if ( ! is_wp_error( $page ) && CFGD_Parsers::has_bsplus_badge( $page ) ) {
					// 一覧に載っていないのにバッジがある店舗。未ログインのページからは+4%か+9%か分からないので、
					// 設定の倍率（初期値+9%：2026/10/20 かめやで確認）を使う
					$r    = (float) CFGD_Settings::get( 'bsp_unlisted_rate' );
					$tier = array( 'rate' => $r, 'cap' => $r >= 9 ? 10000 : 5000, 'stores' => array() );
					self::log( "ボーナスストアPlus: {$st->store_code} は一覧になくバッジあり → +{$r}%として計算" );
				}
			}
			if ( $tier ) {
				$found[ (string) $tier['rate'] ]['tier']     = $tier;
				$found[ (string) $tier['rate'] ]['stores'][] = $st->store_code;
			}
		}

		$today  = wp_date( 'Y-m-d' );
		$all    = array();
		// 今日の分は毎回作り直す（倍率の判定が変わったときに古い行が残って二重に付かないように）
		$wpdb->query( $wpdb->prepare( 'DELETE FROM ' . CFGD_DB::t( 'campaigns' ) . " WHERE source='yahoo_bsp' AND start_at=%s", $today . ' 00:00:00' ) ); // phpcs:ignore
		foreach ( $found as $f ) {
			$rate = $f['tier']['rate'];
			// 上限は倍率で決める（ページの読み取りで+4%に10,000円が付いたことがあるため）
			$cap  = $rate >= 9 ? 10000 : 5000;
			CFGD_DB::upsert_campaign( array(
				'mall'       => 'yahoo',
				'name'       => "ボーナスストアPlus +{$rate}%",
				'start_at'   => $today . ' 00:00:00',
				'end_at'     => $today . ' 23:59:59',
				'rate_pct'   => $rate,
				'cap_yen'    => $cap,
				'scope'      => 'limited',
				'stores'     => implode( ',', $f['stores'] ),
				'conditions' => '要エントリー・対象ストア限定（1日上限）',
				'status'     => 'confirmed',
				'source'     => 'yahoo_bsp',
			) );
			$all = array_merge( $all, $f['stores'] );
			self::log( "ボーナスストアPlus +{$rate}%: " . implode( ', ', $f['stores'] ) );
		}
		if ( ! $found ) {
			self::log( 'ボーナスストアPlus: 今日は対象店舗なし' );
		}
		update_option( 'cfgd_bsp_today', array( 'd' => $today, 'stores' => $all ), false );
	}

	/** 今日のボーナスストアPlus対象店舗（カレンダーの「ボーナスストアPlusでさらに+2%」の判定に使う）。 */
	public static function bsp_stores() {
		$o = get_option( 'cfgd_bsp_today', array() );
		return ( $o['d'] ?? '' ) === wp_date( 'Y-m-d' ) ? (array) $o['stores'] : array();
	}

	/**
	 * その出品に使えるクーポン。商品限定のクーポン（item_key あり）は、同じ商品にだけ使う。
	 * 出品の商品コード：Yahoo!「store_pagekey」、楽天「shop:itemid」。
	 */
	public static function coupons_for( $row, $now, $count_unverified ) {
		$key = (string) ( $row->offer_item_code ?? '' );
		$key = 'yahoo' === $row->mall ? preg_replace( '/^[^_]+_/', '', $key ) : preg_replace( '/^[^:]+:/', '', $key );
		$out = array();
		foreach ( CFGD_DB::active_coupons( $row->mall, $row->store_code, $now ) as $c ) {
			if ( ! $count_unverified && 0 === (int) $c->verified ) {
				continue;
			}
			if ( '' !== (string) $c->item_key && strcasecmp( $c->item_key, $key ) !== 0 ) {
				continue;
			}
			$out[] = $c;
		}
		return $out;
	}

	/** 今日のショップ全体倍率（取得した日のものだけ有効）。 */
	public static function shop_rates() {
		$o = get_option( 'cfgd_rak_shop_rates', array() );
		return ( $o['d'] ?? '' ) === wp_date( 'Y-m-d' ) ? (array) $o['rates'] : array();
	}

	/** JAN未入力の商品を型番から特定する（Yahoo!検索）。 */
	public static function resolve_jans() {
		global $wpdb;
		$pt = CFGD_DB::t( 'products' );
		foreach ( $wpdb->get_results( "SELECT * FROM $pt WHERE active=1 AND jan='' AND keyword<>''" ) as $p ) { // phpcs:ignore
			$r = CFGD_Fetch::resolve_jan( $p->keyword );
			if ( is_wp_error( $r ) ) {
				self::log( "JAN自動取得 {$p->name}: " . $r->get_error_message(), true );
				return;
			}
			if ( ! $r ) {
				self::log( "JAN自動取得 {$p->name}: 検索語「{$p->keyword}」に合う商品なし", true );
				continue;
			}
			$wpdb->update( $pt, array( 'jan' => $r['jan'], 'jan_auto' => 1 ), array( 'id' => $p->id ) );
			self::log( "JAN自動取得 {$p->name} → {$r['jan']}（{$r['total']}件中{$r['count']}件が一致。管理画面で確認してください）", true );
		}
	}

	/**
	 * 未取得の出品を締め切りまで取得する。
	 *
	 * @return int 残りの出品数
	 */
	public static function run_prices( array &$state, $deadline ) {
		$products = CFGD_DB::products_with_offers();
		$done     = array_flip( $state['done'] );
		$left     = 0;
		foreach ( $products as $p ) {
			if ( ! $p->jan ) {
				continue;
			}
			foreach ( $p->offers as $o ) {
				if ( isset( $done[ (int) $o->id ] ) ) {
					continue;
				}
				if ( time() >= $deadline ) {
					$left++;
					continue;
				}
				$done[ (int) $o->id ] = true;
				$state['done'][]      = (int) $o->id;
				if ( CFGD_DB::should_skip( $o ) ) {
					$state['stats']['skipped']++;
					continue;
				}
				$r = 'rakuten' === $o->mall ? CFGD_Fetch::rakuten( $o, $p ) : CFGD_Fetch::yahoo( $o, $p );
				if ( is_wp_error( $r ) ) {
					if ( 'cfgd_notfound' === $r->get_error_code() ) {
						CFGD_DB::mark_offer( $o->id, false ); // 取り扱いなし（ログは出さない）
					} else {
						self::log( "{$p->name} / {$o->mall}:{$o->store_code} … " . $r->get_error_message(), 'cfgd_config' === $r->get_error_code() );
					}
					continue;
				}
				CFGD_DB::mark_offer( $o->id, true );
				// 商品画像：まだなければ最初に見つかったものを使う（https のみ）
				if ( empty( $p->image_url ) && ! empty( $r['image'] ) && str_starts_with( $r['image'], 'https://' ) ) {
					global $wpdb;
					$wpdb->update( CFGD_DB::t( 'products' ), array( 'image_url' => esc_url_raw( $r['image'] ) ), array( 'id' => $p->id ) );
					$p->image_url = $r['image'];
				}
				if ( 'rakuten' === $o->mall ) {
					$state['stats']['rak_all']++;
					if ( $r['shop_pct'] >= 2 ) {
						$state['stats']['rak_up']++;
					}
				}
				// 見つかった商品コードを覚えておく（次回から確実に同じ商品を引く）
				if ( ! empty( $r['item_code'] ) && $o->item_code !== $r['item_code'] && ( 'yahoo' === $o->mall || ! $o->item_code ) ) {
					global $wpdb;
					$wpdb->update( CFGD_DB::t( 'offers' ), array( 'item_code' => $r['item_code'] ), array( 'id' => $o->id ) );
				}
				CFGD_DB::save_price( $o->id, array(
					'price'        => $r['price'],
					'shipping_yen' => $r['shipping'],
					'shop_pct'     => $r['shop_pct'],
					'store_points' => $r['store_points'] ?? 0,
					'in_stock'     => $r['in_stock'],
					'url'          => $r['url'],
					'item_name'    => $r['item_name'],
					'eff_price'    => $r['price'] + $r['shipping'], // 判定で上書き
					'breakdown'    => '',
				) );
			}
		}
		return $left;
	}

	private static function finish_prices( array $state ) {
		$st = $state['stats'];
		// 楽天のショップ倍率が一斉に上がったら、イベント開始の可能性
		$prev = (int) get_option( 'cfgd_rak_up_ratio', 0 );
		$now  = $st['rak_all'] ? (int) round( 100 * $st['rak_up'] / $st['rak_all'] ) : 0;
		if ( $st['rak_all'] >= 4 && $now >= 50 && $prev < 50 ) {
			self::log( "楽天でポイント倍率の付いた出品が{$now}%に増えた（イベント開始の可能性）", true );
		}
		update_option( 'cfgd_rak_up_ratio', $now, false );
		self::log( '価格取得: ' . count( $state['done'] ) . "出品（取り扱いなしで休止中 {$st['skipped']}件、楽天で見つかった出品 {$st['rak_all']}件）" );
	}

	/** 今日の行に実質価格を入れ直し、買い時を判定する。 */
	public static function run_judge( $notify ) {
		global $wpdb;
		$s     = CFGD_Settings::all();
		$now   = time();
		$map   = CFGD_Settings::yahoo_limited_map();
		// 「ボーナスストアPlusでさらに+2%」は、今日のボーナスストアPlus対象店舗に付く（「優良ストアで」の方は手動で対象を指定）
		// 「対象ストア限定」の企画（感謝デー・爆買WEEKなど）は、価格比較ページで BONUS / BONUS+ が付いていた店に付ける
		$bonus = get_option( 'cfgd_bonus_today', array() );
		if ( ( $bonus['d'] ?? '' ) === wp_date( 'Y-m-d' ) && ! empty( $bonus['stores'] ) ) {
			$map['*'] = array_merge( $map['*'] ?? array(), (array) $bonus['stores'] );
		}
		$map['ボーナスストアPlus'] = array_merge( $map['ボーナスストアPlus'] ?? array(), $map['ボーナスストアPlusで'] ?? array(), self::bsp_stores() );
		$opt   = array( 'limited_map' => $map, 'yahoo_total_cap_pct' => $s['yahoo_total_cap_pct'] );
		$camps = array(
			'rakuten' => CFGD_DB::active_campaigns( 'rakuten', $now ),
			'yahoo'   => CFGD_DB::active_campaigns( 'yahoo', $now ),
		);
		$deals = array();
		$shop  = self::shop_rates();
		$unver = (int) $s['count_unverified_coupons'] === 1;

		foreach ( CFGD_DB::products_with_offers() as $p ) {
			$best    = null;
			$strong  = null; // 店舗の目安を満たす出品のうち最安
			$results = array();
			foreach ( CFGD_DB::today_rows( $p->id ) as $row ) {
				$res = CFGD_Judge::effective(
					array(
						'mall'         => $row->mall,
						'store'        => $row->store_code,
						'price'        => (int) $row->price,
						'shipping'     => (int) $row->shipping_yen,
						// 楽天：商品単位の倍率と、店舗トップのショップ全体倍率の大きい方
						'shop_pct'     => 'rakuten' === $row->mall ? max( (float) $row->shop_pct, (float) ( $shop[ $row->store_code ] ?? 0 ) ) : (float) $row->shop_pct,
						'store_points' => (int) $row->store_points,
					),
					$camps[ $row->mall ],
					self::coupons_for( $row, $now, $unver ),
					$opt
				);
				$wpdb->update( CFGD_DB::t( 'prices' ), array(
					'eff_price'    => $res['eff_price'],
					'points_total' => $res['points'],
					'coupon_yen'   => $res['coupon_yen'],
					'breakdown'    => wp_json_encode( array( 'lines' => $res['lines'], 'possible' => $res['possible'] ), JSON_UNESCAPED_UNICODE ),
				), array( 'id' => $row->id ) );

				if ( $row->in_stock ) {
					$results[] = array( $row, $res );
				}
			}
			// ポイント前の最安（価格＋送料）。値付けがこれより大きく高い店は、ポイントが多くても買い時にしない
			$min_total = 0;
			foreach ( $results as list( $row, $res ) ) {
				$t = (int) $row->price + (int) $row->shipping_yen;
				if ( ! $min_total || $t < $min_total ) {
					$min_total = $t;
				}
			}
			foreach ( $results as list( $row, $res ) ) {
				$st = CFGD_Judge::strong(
					$row->mall, $row->store_code, (int) $row->price, $res['coupon_yen'], $res['points'],
					$s['strong_stores'], $s['strong_rate_pct'], (int) $s['strong_need_coupon'], (float) $s['strong_any_rate_pct'],
					array( 'total' => (int) $row->price + (int) $row->shipping_yen, 'min' => $min_total, 'over_pct' => (float) $s['strong_max_over_pct'] )
				);
				if ( null === $best || $res['eff_price'] < $best['eff_price'] ) {
					$best = self::offer_pick( $res, $row );
				}
				if ( $st && $st['ok'] && ( null === $strong || $res['eff_price'] < $strong['eff_price'] ) ) {
					$strong = self::offer_pick( $res, $row ) + array( 'strong' => $st );
				}
			}
			if ( ! $best ) {
				continue;
			}
			$hist = array_map( 'intval', wp_list_pluck( CFGD_DB::daily_min_eff( $p->id, $s['window_days'] ), 'eff' ) );
			$v    = CFGD_Judge::verdict( $best['eff_price'], $best['price'], $hist, (float) $s['tolerance_pct'], (int) $s['min_history_days'] );
			$v['rule'] = $v['buy'] ? 'history' : '';
			// 90日の基準に届かなくても、店舗の目安（ポイント・キャスティングで還元20%前後＋クーポン）を満たせば買い時
			if ( ! $v['buy'] && $strong ) {
				$v    = array(
					'buy'    => true,
					'rule'   => 'store',
					'min'    => $v['min'],
					'diff'   => null !== $v['min'] ? $strong['eff_price'] - $v['min'] : 0,
					'reason' => $strong['strong']['reason'] . '（店舗の目安）',
				);
				$best = $strong;
			}
			self::log( "{$p->name}: 実質" . number_format( $best['eff_price'] ) . "円（{$best['mall']}:{$best['store']}）→ " . ( $v['buy'] ? '買い時' : '見送り' ) . " / {$v['reason']}" );

			if ( $v['buy'] ) {
				$deals[] = array(
					'product_id' => (int) $p->id,
					'slug'       => $p->slug,
					'model'      => $p->model ? $p->model : $p->name,
					'name'       => $p->name,
					'tags'       => $p->tags,
					'image'      => (string) ( $p->image_url ?? '' ),
					'verdict'    => $v,
					'best'       => $best,
					'until'      => wp_date( 'Y-m-d 23:59:59' ),
				);
			}
		}

		$deals = self::group_by_store( $deals );
		update_option( 'cfgd_deals', $deals, false );
		if ( $notify ) {
			self::notify_deals( $deals );
		}
		return self::$log;
	}

	/**
	 * 同じ機種（右/左・ギア比・竿のタイプ違い）の買い時をまとめ、
	 * いちばんお得な品番を代表にして「ほかに買い時の品番」を添える。
	 */
	/** 判定・バナー・投稿で使う出品の情報。Yahoo!は直営アフィリエイトのリンクがあればそちらを使う（料率が高い）。 */
	private static function offer_pick( array $res, $row ) {
		$direct = CFGD_DB::afflink_for( $row->mall, $row->store_code, $row->offer_item_code ?? '' );
		return $res + array(
			'mall'      => $row->mall,
			'store'     => $row->store_code,
			'url'       => $direct ? $direct : $row->url,
			'direct'    => (bool) $direct,
			'item_code' => $row->offer_item_code ?? '',
		);
	}

	/** SNS投稿に入れる攻略ページ（今日の価格）へのURL行。未設定なら空。 */
	private static function guide_line() {
		$u = trim( (string) CFGD_Settings::get( 'guide_url' ) );
		if ( '' === $u ) {
			return '';
		}
		return '今日の価格と買い方 ' . strtok( $u, '#' ) . "#catalog\n";
	}

	/** 小さいほどお得（並べ替え用）。 */
	private static function rank( array $d ) {
		return (int) ( $d['verdict']['diff'] ?? 0 ) - (int) ( $d['verdict']['allowance'] ?? 0 );
	}

	/** 店舗コード → 表示名（「店舗を探す」の結果から）。 */
	public static function store_name( $mall, $code ) {
		foreach ( (array) ( get_option( 'cfgd_store_scan', array() )['matches'] ?? array() ) as $list ) {
			foreach ( (array) $list as $st ) {
				if ( $st['mall'] === $mall && $st['code'] === $code ) {
					return $st['name'];
				}
			}
		}
		return ( 'rakuten' === $mall ? '楽天 ' : 'Yahoo! ' ) . $code;
	}

	/**
	 * 店舗の目安で買い時になった品番は、店舗ごとに1件へまとめる
	 * （お得さの差は商品より店舗の施策で決まるため。「今日はキャスティングが買い時」）。
	 * 90日の記録で買い時になった品番は、これまでどおり機種ごとに1件。
	 */
	public static function group_by_store( array $deals ) {
		$by_store = array();
		$items    = array();
		foreach ( $deals as $d ) {
			if ( 'store' === ( $d['verdict']['rule'] ?? '' ) ) {
				$by_store[ $d['best']['mall'] . ':' . $d['best']['store'] ][] = $d;
			} else {
				$items[] = $d;
			}
		}
		$out = array();
		foreach ( $by_store as $key => $list ) {
			usort( $list, fn( $a, $b ) => $b['best']['strong']['rate'] <=> $a['best']['strong']['rate'] );
			$head  = $list[0];
			$b     = $head['best'];
			$out[] = array(
				'type'     => 'store',
				'group'    => 'store-' . sanitize_title( $key ),
				'slug'     => 'store-' . sanitize_title( $b['store'] ),
				'name'     => self::store_name( $b['mall'], $b['store'] ),
				'mall'     => $b['mall'],
				'store'    => $b['store'],
				'rate'     => $b['strong']['rate'],
				'coupon'   => (int) $b['coupon_yen'],
				'tags'     => implode( ',', array_unique( array_merge( ...array_map( fn( $d ) => explode( ',', (string) $d['tags'] ), $list ) ) ) ),
				'image'    => $head['image'],
				'verdict'  => array( 'buy' => true, 'rule' => 'store', 'diff' => -1000000, 'allowance' => 0, 'min' => null, 'reason' => $b['strong']['reason'] ),
				'best'     => $b,
				'products' => array_map( fn( $d ) => array(
					'product_id' => (int) $d['product_id'],
					'name'  => $d['name'],
					'model' => $d['model'],
					'tags'  => $d['tags'],
					'image' => $d['image'],
					'best'  => $d['best'],
				), $list ),
				'until'    => $head['until'],
			);
		}
		foreach ( self::group_by_model( $items ) as $d ) {
			$d['type'] = 'product';
			$out[]     = $d;
		}
		return $out;
	}

	public static function group_by_model( array $deals ) {
		$groups = array();
		foreach ( $deals as $d ) {
			$k              = $d['model'];
			$groups[ $k ][] = $d;
		}
		$out = array();
		foreach ( $groups as $model => $list ) {
			usort( $list, fn( $a, $b ) => self::rank( $a ) <=> self::rank( $b ) );
			$head             = $list[0];
			$head['variants'] = array_map( fn( $d ) => $d['name'], $list );
			$head['group']    = sanitize_title( $model );
			$out[]            = $head;
		}
		return $out;
	}

	private static function notify_deals( array $deals ) {
		$s        = CFGD_Settings::all();
		$notified = get_option( 'cfgd_notified', array() );
		$today    = wp_date( 'Y-m-d' );
		$posted   = (int) get_option( 'cfgd_posted_' . $today, 0 );

		// 差が小さい（よりお得な）順に
		// 店舗まとめ（diff を大きくマイナスにしてある）を先に、あとは差が小さい（よりお得な）順に
		usort( $deals, fn( $a, $b ) => self::rank( $a ) <=> self::rank( $b ) );

		foreach ( $deals as $d ) {
			$last = $notified[ $d['group'] ] ?? '';
			if ( $last && strtotime( $last ) > time() - DAY_IN_SECONDS * (int) $s['cooldown_days'] ) {
				continue;
			}
			if ( $posted >= (int) $s['sns_daily_limit'] ) {
				break;
			}
			$text = self::post_text( $d );

			/**
			 * SNS投稿のフック。既存の Cutlassfish Buffer Publisher 側でこのアクションを受けて
			 * X・Instagram・Threads に流す（カード画像はそちらで生成）。
			 */
			do_action( 'cfgd_deal_found', $d, $text );

			self::log( "通知: {$d['name']}" . ( 'store' === ( $d['type'] ?? '' ) ? '（店舗まとめ ' . count( $d['products'] ) . '品番）' : '' ) );
			if ( 'yahoo' === $d['best']['mall'] && empty( $d['best']['direct'] ) ) {
				$page = 'https://store.shopping.yahoo.co.jp/' . $d['best']['store'] . '/' . preg_replace( '/^[^_]+_/', '', (string) $d['best']['item_code'] ) . '.html';
				self::$alerts[] = "直営リンク未登録のため、バリューコマースのリンクで投稿しました。次回のために、この商品ページで直営リンクを発行して登録してください：\n{$page}";
			}
			self::$alerts[]                 = "買い時: {$d['name']}\n{$text}";
			$notified[ $d['group'] ]   = $today;
			$posted++;
		}
		update_option( 'cfgd_notified', $notified, false );
		update_option( 'cfgd_posted_' . $today, $posted, false );
	}

	public static function post_text( array $d ) {
		if ( 'store' === ( $d['type'] ?? '' ) ) {
			$out  = "【今日は{$d['name']}が買い時】\n";
			$out .= $d['verdict']['reason'] . "\n";
			$seen = array();
			foreach ( $d['products'] as $p ) {
				if ( isset( $seen[ $p['model'] ] ) || count( $seen ) >= 5 ) {
					continue;
				}
				$seen[ $p['model'] ] = true;
				$out .= '・' . $p['name'] . ' 実質' . number_format( (int) $p['best']['eff_price'] ) . '円（本体' . number_format( (int) $p['best']['price'] ) . "円）\n";
			}
			$rest = count( $d['products'] ) - count( $seen );
			if ( $rest > 0 ) {
				$out .= "ほか{$rest}品番\n";
			}
			$out .= "ポイントは運営者の条件での計算です。本日中の情報なので、購入前に販売ページでご確認ください。\n";
			$out .= self::guide_line() . '#PR';
			return $out;
		}
		$b    = $d['best'];
		$mall = 'rakuten' === $b['mall'] ? '楽天' : 'Yahoo!';
		$out  = "【買い時】{$d['name']}\n";
		$out .= "{$mall}で本体" . number_format( $b['price'] ) . '円 → 実質' . number_format( $b['eff_price'] ) . "円\n";
		$out .= '（ポイント' . number_format( $b['points'] ) . '円相当' . ( $b['coupon_yen'] ? '・クーポン' . number_format( $b['coupon_yen'] ) . '円' : '' ) . "）\n";
		if ( null !== ( $d['verdict']['min'] ?? null ) ) {
			$out .= '直近90日の実質最安 ' . number_format( (int) $d['verdict']['min'] ) . "円\n";
		}
		$conds = array();
		foreach ( $b['lines'] as $l ) {
			if ( 'point' === $l['type'] && ! str_starts_with( $l['label'], 'ショップ' ) && ! str_starts_with( $l['label'], 'ストア' ) ) {
				$conds[] = $l['label'];
			}
		}
		if ( $conds ) {
			$out .= '条件：' . implode( '／', $conds ) . "\n";
		}
		$others = array_slice( $d['variants'] ?? array(), 1 );
		if ( $others ) {
			$out .= 'ほかに買い時：' . implode( '、', $others ) . "\n";
		}
		$out .= "本日中の情報です。購入前に販売ページで価格をご確認ください。\n";
		$out .= self::guide_line() . '#PR';
		return $out;
	}

	private static function send_alerts() {
		$to = CFGD_Settings::get( 'notify_email' );
		if ( ! self::$alerts || ! $to ) {
			return;
		}
		wp_mail( $to, '[釣具の買い時] ' . wp_date( 'n/j' ) . ' のお知らせ', implode( "\n\n", self::$alerts ) . "\n\n---\n" . implode( "\n", self::$log ) );
	}
}
