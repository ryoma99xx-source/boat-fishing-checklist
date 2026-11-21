<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class CFGD_Settings {
	const OPTION = 'cfgd_settings';

	public static function defaults() {
		return array(
			// API
			'rakuten_app_id'       => '',
			'rakuten_access_key'   => '',
			'rakuten_affiliate_id' => '',
			'yahoo_appid'          => '',
			'yahoo_vc_affiliate'   => '', // バリューコマースのアフィリエイトID（affiliate_type=vc）
			// 全商品で共通に見る店舗（カンマ区切り。送料別は code=550）
			'stores_rakuten'       => '',
			'stores_yahoo'         => '',
			'rakuten_shop_pages'   => 1, // 楽天の店舗トップ（未ログイン）からショップ倍率・クーポン・3商品企画を読む
			'count_unverified_coupons' => 1, // 店舗トップの見出しだけのクーポン（条件未確認）も計算に入れる
			'miss_skip_after'      => 3, // 連続で見つからない店舗は…
			'miss_recheck_days'    => 7, // …この日数に1回だけ確認する
			// 判定
			'tolerance_pct'        => 3,   // 90日実質最安からの許容差（本体価格に対する%＝ポイント何%分か）
			'window_days'          => 90,
			'min_history_days'     => 14,  // 記録がこの日数に満たない商品は「買い時」にしない
			// 店舗の目安：この店舗でポイント還元がN%以上（かつクーポンあり）なら、90日の記録に関係なく買い時
			'strong_stores'        => 'yahoo:casting,yahoo:point-i,yahoo:point-eastjapan',
			'strong_rate_pct'      => 18,  // 「20%前後」の下限
			'strong_need_coupon'   => 1,
			'strong_max_over_pct'  => 10,  // 値付け（ポイント前）が最安店よりこの%を超えて高い店は、ポイントが多くても買い時にしない
			'strong_any_rate_pct'  => 20,  // どの店でも、Yahoo!でポイント還元がこの%以上なら買い時（クーポン不要。0で無効）
			'yahoo_compare'        => 0,   // Yahoo!の価格比較ページでボーナスストアPlus対象店を判定する（確認してから1にする）
			'bsp_unlisted_rate'    => 4,   // 価格比較ページで分からないときは少なめ（+4%）に見る   // ボーナスストアPlus：一覧に載っていないがバッジのある店舗の倍率（%）
			'yahoo_premium'        => 1,   // LYPプレミアム会員前提でストアポイントを計算
			'yahoo_total_cap_pct'  => 48.5, // Yahoo!の合計付与率上限
			// カレンダー
			'yahoo_calendar_url'   => 'https://shopping.yahoo.co.jp/promotion/campaign/dailybonus/calendar/',
			'rakuten_calendar_url' => 'https://calendar.rakuten.co.jp/cal/8607',
			// Yahoo!の「対象ストア限定」施策を、どのストアで有効とみなすか
			// 1行1施策：施策名の一部: storeId,storeId
			'yahoo_limited_map'    => '',
			// 通知・投稿
			'notify_email'         => get_option( 'admin_email' ),
			'cooldown_days'        => 7,   // 同じ商品を再通知しない日数
			'sns_daily_limit'      => 1,
			// 攻略ページ（公開してから入れる。空のあいだはバナーの「買い方を見る」とSNSのURLを出さない）
			'guide_url'            => '',
			'banner_enabled'       => 1,
			// スマホのショートカットからクーポンを登録するときの合言葉（有効化時に自動生成）
			'quick_token'          => '',
		);
	}

	public static function all() {
		return wp_parse_args( get_option( self::OPTION, array() ), self::defaults() );
	}

	/** 合言葉トークンがなければ作る。 */
	public static function ensure_token( $force = false ) {
		$all = get_option( self::OPTION, array() );
		if ( $force || empty( $all['quick_token'] ) ) {
			$all['quick_token'] = wp_generate_password( 32, false, false );
			update_option( self::OPTION, $all, false );
		}
		return $all['quick_token'];
	}

	public static function get( $key ) {
		$all = self::all();
		return $all[ $key ] ?? null;
	}

	/** 「casting,point-i=550」→ ['casting'=>0, 'point-i'=>550] */
	public static function stores( $mall ) {
		$out = array();
		foreach ( array_filter( array_map( 'trim', explode( ',', (string) self::get( 'stores_' . $mall ) ) ) ) as $tok ) {
			list( $code, $ship ) = array_pad( explode( '=', $tok, 2 ), 2, 0 );
			$out[ trim( $code ) ] = (int) $ship;
		}
		return $out;
	}

	/** 「施策名の一部: store1,store2」を配列に。 */
	public static function yahoo_limited_map() {
		$map   = array();
		$lines = preg_split( '/\R/u', (string) self::get( 'yahoo_limited_map' ) );
		foreach ( $lines as $line ) {
			if ( ! str_contains( $line, ':' ) ) {
				continue;
			}
			list( $name, $stores ) = array_map( 'trim', explode( ':', $line, 2 ) );
			if ( '' === $name ) {
				continue;
			}
			$map[ $name ] = array_filter( array_map( 'trim', explode( ',', $stores ) ) );
		}
		return $map;
	}
}
