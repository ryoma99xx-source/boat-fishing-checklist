<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class CFGD_DB {

	public static function t( $name ) {
		global $wpdb;
		return $wpdb->prefix . 'cfgd_' . $name;
	}

	public static function install() {
		global $wpdb;
		require_once ABSPATH . 'wp-admin/includes/upgrade.php';
		$c = $wpdb->get_charset_collate();

		dbDelta( "CREATE TABLE " . self::t( 'products' ) . " (
  id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  slug varchar(64) NOT NULL,
  model varchar(128) NOT NULL DEFAULT '',
  name varchar(255) NOT NULL,
  jan varchar(20) NOT NULL DEFAULT '',
  jan_auto tinyint(1) NOT NULL DEFAULT 0,
  keyword varchar(255) NOT NULL DEFAULT '',
  tags varchar(255) NOT NULL DEFAULT '',
  extra_stores varchar(255) NOT NULL DEFAULT '',
  image_url varchar(500) NOT NULL DEFAULT '',
  yahoo_product_id varchar(20) NOT NULL DEFAULT '',
  active tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY  (id),
  UNIQUE KEY slug (slug)
) $c;" );

		dbDelta( "CREATE TABLE " . self::t( 'offers' ) . " (
  id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  product_id bigint(20) unsigned NOT NULL,
  mall varchar(10) NOT NULL,
  store_code varchar(64) NOT NULL,
  item_code varchar(128) NOT NULL DEFAULT '',
  shipping_yen int(11) NOT NULL DEFAULT 0,
  active tinyint(1) NOT NULL DEFAULT 1,
  miss_count int(11) NOT NULL DEFAULT 0,
  last_checked date NULL,
  PRIMARY KEY  (id),
  UNIQUE KEY offer (product_id,mall,store_code)
) $c;" );

		dbDelta( "CREATE TABLE " . self::t( 'prices' ) . " (
  id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  offer_id bigint(20) unsigned NOT NULL,
  d date NOT NULL,
  price int(11) NOT NULL,
  shipping_yen int(11) NOT NULL DEFAULT 0,
  shop_pct decimal(5,2) NOT NULL DEFAULT 0,
  store_points int(11) NOT NULL DEFAULT 0,
  coupon_yen int(11) NOT NULL DEFAULT 0,
  points_total int(11) NOT NULL DEFAULT 0,
  eff_price int(11) NOT NULL,
  in_stock tinyint(1) NOT NULL DEFAULT 1,
  url text NOT NULL,
  item_name varchar(255) NOT NULL DEFAULT '',
  breakdown text NOT NULL,
  fetched_at datetime NOT NULL,
  PRIMARY KEY  (id),
  UNIQUE KEY offer_day (offer_id,d),
  KEY d (d)
) $c;" );

		dbDelta( "CREATE TABLE " . self::t( 'campaigns' ) . " (
  id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  mall varchar(10) NOT NULL,
  name varchar(191) NOT NULL,
  start_at datetime NULL,
  end_at datetime NULL,
  recur varchar(64) NOT NULL DEFAULT '',
  rate_pct decimal(5,2) NULL,
  cap_yen int(11) NOT NULL DEFAULT 0,
  is_max tinyint(1) NOT NULL DEFAULT 0,
  scope varchar(10) NOT NULL DEFAULT 'all',
  stores varchar(255) NOT NULL DEFAULT '',
  conditions varchar(255) NOT NULL DEFAULT '',
  status varchar(12) NOT NULL DEFAULT 'confirmed',
  source varchar(20) NOT NULL DEFAULT 'manual',
  note varchar(255) NOT NULL DEFAULT '',
  updated_at datetime NOT NULL,
  PRIMARY KEY  (id),
  UNIQUE KEY uniq (mall,name,start_at,source)
) $c;" );

		dbDelta( "CREATE TABLE " . self::t( 'coupons' ) . " (
  id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  mall varchar(10) NOT NULL,
  store_code varchar(64) NOT NULL,
  pct decimal(5,2) NOT NULL DEFAULT 0,
  yen int(11) NOT NULL DEFAULT 0,
  cap_yen int(11) NOT NULL DEFAULT 0,
  min_order int(11) NOT NULL DEFAULT 0,
  start_at datetime NOT NULL,
  end_at datetime NOT NULL,
  note varchar(255) NOT NULL DEFAULT '',
  source varchar(20) NOT NULL DEFAULT 'manual',
  verified tinyint(1) NOT NULL DEFAULT 1,
  item_key varchar(128) NOT NULL DEFAULT '',
  PRIMARY KEY  (id)
) $c;" );

		// Yahoo!直営アフィリエイトのリンク（商品×店舗ごとにスマホで発行して登録）
		dbDelta( "CREATE TABLE " . self::t( 'afflinks' ) . " (
  id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  mall varchar(10) NOT NULL,
  store_code varchar(64) NOT NULL,
  item_key varchar(128) NOT NULL,
  url text NOT NULL,
  created_at datetime NOT NULL,
  PRIMARY KEY  (id),
  UNIQUE KEY item (mall,store_code,item_key)
) $c;" );

		update_option( 'cfgd_db_version', CFGD_VERSION );
	}

	/**
	 * 日付で決まる定例施策の初期値。値は公開情報からの初期値なので、管理画面で必ず確認する。
	 * 不確かなものは status=disabled で入れておく。
	 */
	public static function seed_rules() {
		// [モール, 名前, 繰り返し, 倍率%, 上限円, 状態, メモ, 条件]
		// 倍率と上限は2026年10月時点の公開情報＋運営者のステータス。条件に「税込」とあるものは税込額にかかる。
		$rules = array(
			// Yahoo!（LYPプレミアム・LINE連携・PayPayクレジットの運営者ステータス）
			array( 'yahoo', 'LINEと連携で毎日もらえる', '*', 3, 5000, 'confirmed', '支払方法指定あり。上限は月間', '' ),
			array( 'yahoo', 'LYPプレミアム会員', '*', 2, 5000, 'confirmed', '支払方法指定あり。上限は月間', '' ),
			array( 'yahoo', 'PayPayクレジット', '*', 1.5, 0, 'confirmed', '通常ポイント', '税込決済額対象' ),
			array( 'yahoo', '5のつく日', '5,15,25', 4, 2000, 'confirmed', '要エントリー・PayPay払い。上限は開催回ごと（2026年9月から2,000pt）。カレンダーから取れた日はそちらを優先', '' ),
			array( 'yahoo', 'ボーナスストアPlus（手動）', '*', 4, 5000, 'disabled', '通常は毎日の自動判定（ボーナスストアPlus +◯%）を使う。自動判定が止まったときの予備', '' ),
			// 楽天（楽天モバイル・楽天カード・楽天銀行の運営者ステータス）
			array( 'rakuten', 'SPU 楽天モバイル', '*', 4, 2000, 'confirmed', '要エントリー。上限は月間', '' ),
			array( 'rakuten', 'SPU 楽天カード（通常分）', '*', 1, 0, 'confirmed', '上限なし', '税込決済額対象' ),
			array( 'rakuten', 'SPU 楽天カード（特典分）', '*', 1, 1000, 'confirmed', '上限は月間', '' ),
			array( 'rakuten', 'SPU 楽天銀行（カード引き落とし）', '*', 0.5, 1000, 'confirmed', '引き落としのみなら+0.3倍の場合あり。会員ページで確認', '' ),
			array( 'rakuten', '5と0のつく日', '5,10,15,20,25,30', 1, 1000, 'confirmed', '要エントリー・楽天カード利用。上限は月間', '' ),
			array( 'rakuten', 'ワンダフルデー', '1', 2, 0, 'disabled', '3,000円以上・要エントリー。上限を確認してから有効化', '' ),
			array( 'rakuten', 'ご愛顧感謝デー', '18', 3, 0, 'disabled', '会員ランクで変わる（ダイヤ4倍・プラチナ3倍・ゴールド2倍＝通常込み）。自分のランクに合わせて直して有効化', '' ),
		);
		foreach ( $rules as $r ) {
			self::upsert_campaign( array(
				'mall'     => $r[0],
				'name'     => $r[1],
				'recur'    => $r[2],
				'rate_pct' => $r[3],
				'cap_yen'  => $r[4],
				'status'   => $r[5],
				'note'       => $r[6],
				'conditions' => $r[7],
				'scope'      => str_starts_with( $r[1], 'ボーナスストアPlus' ) ? 'limited' : 'all',
				'stores'     => str_starts_with( $r[1], 'ボーナスストアPlus' ) ? 'casting' : '',
				'source'     => 'rule',
			), false );
		}
	}

	/**
	 * @param bool $overwrite 既存行の rate/cap/status を上書きするか（ルールは手で直す前提なので false）。
	 */
	public static function upsert_campaign( array $c, $overwrite = true ) {
		global $wpdb;
		$row = wp_parse_args( $c, array(
			'mall' => '', 'name' => '', 'start_at' => null, 'end_at' => null, 'recur' => '',
			'rate_pct' => null, 'cap_yen' => 0, 'is_max' => 0, 'scope' => 'all', 'stores' => '',
			'conditions' => '', 'status' => 'confirmed', 'source' => 'manual', 'note' => '',
		) );
		$row['updated_at'] = current_time( 'mysql' );

		$table = self::t( 'campaigns' );
		$where = $row['start_at']
			? $wpdb->prepare( 'mall=%s AND name=%s AND start_at=%s AND source=%s', $row['mall'], $row['name'], $row['start_at'], $row['source'] )
			: $wpdb->prepare( 'mall=%s AND name=%s AND start_at IS NULL AND source=%s', $row['mall'], $row['name'], $row['source'] );
		$existing = $wpdb->get_row( "SELECT * FROM $table WHERE $where" ); // phpcs:ignore

		if ( ! $existing ) {
			$wpdb->insert( $table, $row );
			return array( 'inserted', (int) $wpdb->insert_id );
		}
		// 管理画面で手を入れた行（メモに[固定]）は自動取得で上書きしない。
		if ( $overwrite && ! str_contains( (string) $existing->note, '[固定]' ) ) {
			$wpdb->update( $table, $row, array( 'id' => $existing->id ) );
			return array( 'updated', (int) $existing->id );
		}
		return array( 'kept', (int) $existing->id );
	}

	/** 指定日時に有効な施策（rule/confirmed のみ。hint は返さない）。 */
	public static function active_campaigns( $mall, $ts ) {
		global $wpdb;
		$table = self::t( 'campaigns' );
		$rows  = $wpdb->get_results( $wpdb->prepare( "SELECT * FROM $table WHERE mall=%s AND status='confirmed'", $mall ) ); // phpcs:ignore
		$out   = array();
		foreach ( $rows as $r ) {
			if ( ! self::campaign_matches( $r, $ts ) ) {
				continue;
			}
			// 同じ名前の施策が日付ルールとカレンダーの両方にあれば、カレンダー（実際の告知）を使う
			$key = preg_replace( '/\s+/u', '', $r->name );
			if ( isset( $out[ $key ] ) && 'rule' !== $out[ $key ]->source ) {
				continue;
			}
			$out[ $key ] = $r;
		}
		return array_values( $out );
	}

	/** 予想（hint）・情報（info）の施策。表示用。 */
	public static function hint_campaigns( $from_ts, $to_ts ) {
		global $wpdb;
		$table = self::t( 'campaigns' );
		return $wpdb->get_results( $wpdb->prepare(
			"SELECT * FROM $table WHERE status IN ('hint','info') AND end_at >= %s AND start_at <= %s ORDER BY start_at", // phpcs:ignore
			wp_date( 'Y-m-d H:i:s', $from_ts ),
			wp_date( 'Y-m-d H:i:s', $to_ts )
		) );
	}

	public static function campaign_matches( $c, $ts ) {
		$recur = trim( (string) $c->recur );
		if ( '' !== $recur ) {
			if ( '*' === $recur ) {
				return true;
			}
			$dom = (int) wp_date( 'j', $ts );
			$dow = strtolower( wp_date( 'D', $ts ) ); // sun, mon ...
			foreach ( array_map( 'trim', explode( ',', strtolower( $recur ) ) ) as $token ) {
				if ( (string) $dom === $token || $dow === $token ) {
					return true;
				}
			}
			return false;
		}
		if ( ! $c->start_at || ! $c->end_at ) {
			return false;
		}
		$now = wp_date( 'Y-m-d H:i:s', $ts );
		return $c->start_at <= $now && $now <= $c->end_at;
	}

	public static function active_coupons( $mall, $store, $ts ) {
		global $wpdb;
		$table = self::t( 'coupons' );
		$now   = wp_date( 'Y-m-d H:i:s', $ts );
		return $wpdb->get_results( $wpdb->prepare(
			// store_code が「*」のクーポンは、そのモールの全店舗で使えるもの（Yahoo!ショッピング発行のクーポンなど）
			"SELECT * FROM $table WHERE mall=%s AND store_code IN (%s, '*') AND start_at<=%s AND end_at>=%s", // phpcs:ignore
			$mall, $store, $now, $now
		) );
	}

	public static function products_with_offers() {
		global $wpdb;
		$p   = self::t( 'products' );
		$o   = self::t( 'offers' );
		$out = array();
		foreach ( $wpdb->get_results( "SELECT * FROM $p WHERE active=1 ORDER BY id" ) as $prod ) { // phpcs:ignore
			$prod->offers = $wpdb->get_results( $wpdb->prepare( "SELECT * FROM $o WHERE product_id=%d AND active=1", $prod->id ) ); // phpcs:ignore
			$out[]        = $prod;
		}
		return $out;
	}

	/**
	 * 出品（商品×店舗）を、共通店舗＋商品ごとの追加店舗に合わせて作り直す。
	 * 外れた店舗は active=0（価格履歴は残す）。
	 */
	public static function sync_offers() {
		global $wpdb;
		$pt     = self::t( 'products' );
		$ot     = self::t( 'offers' );
		$common = array(
			'rakuten' => CFGD_Settings::stores( 'rakuten' ),
			'yahoo'   => CFGD_Settings::stores( 'yahoo' ),
		);
		foreach ( $wpdb->get_results( "SELECT id, extra_stores FROM $pt WHERE active=1" ) as $p ) { // phpcs:ignore
			$want = $common;
			// extra_stores: "rakuten:a,b=550;yahoo:c"
			foreach ( array_filter( explode( ';', (string) $p->extra_stores ) ) as $chunk ) {
				if ( ! preg_match( '/^(rakuten|yahoo):(.*)$/', trim( $chunk ), $m ) ) {
					continue;
				}
				foreach ( array_filter( array_map( 'trim', explode( ',', $m[2] ) ) ) as $tok ) {
					list( $code, $ship )       = array_pad( explode( '=', $tok, 2 ), 2, 0 );
					$want[ $m[1] ][ trim( $code ) ] = (int) $ship;
				}
			}
			$wpdb->update( $ot, array( 'active' => 0 ), array( 'product_id' => $p->id ) );
			foreach ( $want as $mall => $stores ) {
				foreach ( $stores as $code => $ship ) {
					$id   = (int) $wpdb->get_var( $wpdb->prepare( "SELECT id FROM $ot WHERE product_id=%d AND mall=%s AND store_code=%s", $p->id, $mall, $code ) ); // phpcs:ignore
					$data = array( 'product_id' => $p->id, 'mall' => $mall, 'store_code' => $code, 'shipping_yen' => $ship, 'active' => 1 );
					if ( $id ) {
						$wpdb->update( $ot, $data, array( 'id' => $id ) );
					} else {
						$wpdb->insert( $ot, $data );
					}
				}
			}
		}
	}

	/** 見つからなかった回数を記録。連続で見つからない店舗は週1回だけ確認する。 */
	public static function mark_offer( $offer_id, $found ) {
		global $wpdb;
		$ot = self::t( 'offers' );
		if ( $found ) {
			$wpdb->query( $wpdb->prepare( "UPDATE $ot SET miss_count=0, last_checked=%s WHERE id=%d", wp_date( 'Y-m-d' ), $offer_id ) ); // phpcs:ignore
		} else {
			$wpdb->query( $wpdb->prepare( "UPDATE $ot SET miss_count=miss_count+1, last_checked=%s WHERE id=%d", wp_date( 'Y-m-d' ), $offer_id ) ); // phpcs:ignore
		}
	}

	public static function should_skip( $offer ) {
		$after = (int) CFGD_Settings::get( 'miss_skip_after' );
		if ( (int) $offer->miss_count < $after || ! $offer->last_checked ) {
			return false;
		}
		return strtotime( $offer->last_checked ) > time() - DAY_IN_SECONDS * (int) CFGD_Settings::get( 'miss_recheck_days' );
	}

	public static function save_afflink( $mall, $store, $item, $url ) {
		global $wpdb;
		$wpdb->replace( self::t( 'afflinks' ), array(
			'mall'       => $mall,
			'store_code' => strtolower( $store ),
			'item_key'   => $item,
			'url'        => $url,
			'created_at' => current_time( 'mysql' ),
		) );
	}

	/** 出品の商品コード（Yahoo!「store_pagekey」）から直営リンクを探す。 */
	public static function afflink_for( $mall, $store, $item_code ) {
		global $wpdb;
		if ( 'yahoo' !== $mall || ! $item_code ) {
			return null;
		}
		$key = preg_replace( '/^[^_]+_/', '', $item_code );
		$t   = self::t( 'afflinks' );
		return $wpdb->get_var( $wpdb->prepare( "SELECT url FROM $t WHERE mall=%s AND store_code=%s AND item_key=%s", $mall, strtolower( $store ), $key ) ); // phpcs:ignore
	}

	public static function save_price( $offer_id, array $row ) {
		global $wpdb;
		$row['offer_id']   = $offer_id;
		$row['d']          = wp_date( 'Y-m-d' );
		$row['fetched_at'] = current_time( 'mysql' );
		$wpdb->replace( self::t( 'prices' ), $row );
	}

	/** 商品の直近N日の、日ごとの実質最安（在庫ありのみ）。 */
	public static function daily_min_eff( $product_id, $days ) {
		global $wpdb;
		$p = self::t( 'prices' );
		$o = self::t( 'offers' );
		return $wpdb->get_results( $wpdb->prepare(
			"SELECT pr.d, MIN(pr.eff_price) AS eff FROM $p pr JOIN $o o ON o.id=pr.offer_id
			 WHERE o.product_id=%d AND pr.in_stock=1 AND pr.d >= %s GROUP BY pr.d ORDER BY pr.d", // phpcs:ignore
			$product_id,
			wp_date( 'Y-m-d', time() - DAY_IN_SECONDS * (int) $days )
		) );
	}

	/** その品番の、いちばん新しい取得日の行（朝の取得前でも前日の価格を出すため）。 */
	public static function latest_rows( $product_id ) {
		global $wpdb;
		$p = self::t( 'prices' );
		$o = self::t( 'offers' );
		$d = $wpdb->get_var( $wpdb->prepare( "SELECT MAX(pr.d) FROM $p pr JOIN $o o ON o.id=pr.offer_id WHERE o.product_id=%d", $product_id ) ); // phpcs:ignore
		if ( ! $d ) {
			return array();
		}
		return $wpdb->get_results( $wpdb->prepare(
			"SELECT pr.*, o.mall, o.store_code, o.item_code AS offer_item_code FROM $p pr JOIN $o o ON o.id=pr.offer_id
			 WHERE o.product_id=%d AND pr.d=%s", // phpcs:ignore
			$product_id,
			$d
		) );
	}

	public static function today_rows( $product_id ) {
		global $wpdb;
		$p = self::t( 'prices' );
		$o = self::t( 'offers' );
		return $wpdb->get_results( $wpdb->prepare(
			"SELECT pr.*, o.mall, o.store_code, o.item_code AS offer_item_code FROM $p pr JOIN $o o ON o.id=pr.offer_id
			 WHERE o.product_id=%d AND pr.d=%s", // phpcs:ignore
			$product_id,
			wp_date( 'Y-m-d' )
		) );
	}
}
