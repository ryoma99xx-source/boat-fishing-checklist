<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * 楽天・Yahoo!のAPI取得と、カレンダーページの取得。
 * どちらもレート制限が厳しいので、呼び出しごとに1秒以上あける。
 */
class CFGD_Fetch {

	const UA = 'CutlassfishGearDeals/0.1 (+https://cutlassfish.tokyo/)';

	/** 楽天の新API（applicationId + accessKey）。バージョンは 2026-07-01 版（20220601は2026年8月に廃止）。 */
	const RAKUTEN_SEARCH = 'https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701';

	/** 直近の楽天APIエラー（店舗探しで画面に出す）。 */
	public static $rakuten_error = '';

	/** 店舗探しでの楽天の検索件数（画面に出す）。 */
	public static $rakuten_log = array();

	private static $last_call = array();

	private static function throttle( $key ) {
		$last = self::$last_call[ $key ] ?? 0;
		$wait = 1.2 - ( microtime( true ) - $last );
		if ( $wait > 0 ) {
			usleep( (int) ( $wait * 1e6 ) );
		}
		self::$last_call[ $key ] = microtime( true );
	}

	/**
	 * 楽天：1ショップ×1商品の最安在庫あり商品。
	 * item_code があればそれで、なければ shopCode + JAN で検索する。
	 *
	 * @return array|WP_Error
	 */
	public static function rakuten( $offer, $product ) {
		$r = self::rakuten_once( $offer, $product, false );
		// 楽天は商品説明にJANがない出品が多いので、見つからなければ品番名で探し直す
		if ( is_wp_error( $r ) && 'cfgd_notfound' === $r->get_error_code() && ! $offer->item_code ) {
			$r2 = self::rakuten_once( $offer, $product, true );
			if ( ! is_wp_error( $r2 ) ) {
				return $r2;
			}
		}
		return $r;
	}

	private static function rakuten_once( $offer, $product, $by_name ) {
		$s = CFGD_Settings::all();
		if ( ! $s['rakuten_app_id'] || ! $s['rakuten_access_key'] ) {
			return new WP_Error( 'cfgd_config', '楽天のアプリIDまたはアクセスキーが未設定' );
		}
		$q = array(
			'applicationId' => $s['rakuten_app_id'],
			'accessKey'     => $s['rakuten_access_key'],
			'formatVersion' => 2,
			'availability'  => 0,
			'hits'          => 30,
			'elements'      => 'itemName,itemCode,itemPrice,itemUrl,affiliateUrl,availability,postageFlag,pointRate,pointRateStartTime,pointRateEndTime,shopCode,mediumImageUrls',
		);
		if ( $s['rakuten_affiliate_id'] ) {
			$q['affiliateId'] = $s['rakuten_affiliate_id'];
		}
		if ( $offer->item_code ) {
			$q['itemCode'] = $offer->item_code;
		} else {
			$q['shopCode'] = $offer->store_code;
			$kw            = CFGD_Parsers::name_keyword( $product );
			$q['keyword']  = $by_name
				? implode( ' ', array_filter( preg_split( '/\s+/u', $kw ), fn( $t ) => '' !== $t && ! str_starts_with( $t, '!' ) ) )
				: $product->jan;
		}

		self::throttle( 'rakuten' );
		$url = add_query_arg( array_map( 'rawurlencode', $q ), self::RAKUTEN_SEARCH );
		$res = wp_remote_get( $url, array(
			'timeout'    => 20,
			'user-agent' => self::UA,
			// 新APIはアプリに登録したWebサイトURLとの一致を確認する
			'headers'    => array( 'Referer' => home_url( '/' ), 'Origin' => untrailingslashit( home_url() ) ),
		) );
		$data = self::json( $res );
		if ( is_wp_error( $data ) ) {
			return $data;
		}

		$best = null;
		foreach ( $data['items'] ?? array() as $it ) {
			if ( ( $it['shopCode'] ?? $offer->store_code ) !== $offer->store_code ) {
				continue;
			}
			if ( $by_name && ! CFGD_Parsers::name_matches( (string) ( $it['itemName'] ?? '' ), $kw ) ) {
				continue;
			}
			$in_stock = (int) ( $it['availability'] ?? 0 ) === 1;
			$cand     = array(
				'price'     => (int) $it['itemPrice'],
				'in_stock'  => $in_stock ? 1 : 0,
				'shop_pct'  => max( 1, (float) ( $it['pointRate'] ?? 1 ) ),
				'url'       => $it['affiliateUrl'] ?? $it['itemUrl'],
				'item_name' => mb_substr( (string) $it['itemName'], 0, 250 ),
				'item_code' => (string) $it['itemCode'],
				'image'     => self::rakuten_image( $it ),
				// postageFlag 0=送料込み。1は送料別だが額が分からないので、オファーに設定した送料を使う
				'shipping'  => 0 === (int) ( $it['postageFlag'] ?? 1 ) ? 0 : (int) $offer->shipping_yen,
			);
			// 在庫あり優先、その中で最安
			if ( null === $best
				|| ( $cand['in_stock'] > $best['in_stock'] )
				|| ( $cand['in_stock'] === $best['in_stock'] && $cand['price'] < $best['price'] ) ) {
				$best = $cand;
			}
		}
		return $best ?? new WP_Error( 'cfgd_notfound', "楽天 {$offer->store_code} で {$product->jan} が見つからない" );
	}

	/** 楽天の商品画像URL（128px → 300px に差し替え）。モールのURLをそのまま表示に使う。 */
	private static function rakuten_image( $it ) {
		$u = $it['mediumImageUrls'][0] ?? '';
		$u = is_array( $u ) ? ( $u['imageUrl'] ?? '' ) : (string) $u;
		return $u ? preg_replace( '/_ex=\d+x\d+/', '_ex=300x300', $u ) : '';
	}

	/** Yahoo!：1ストア×1商品の最安在庫あり商品。 */
	public static function yahoo( $offer, $product ) {
		$s = CFGD_Settings::all();
		if ( ! $s['yahoo_appid'] ) {
			return new WP_Error( 'cfgd_config', 'Yahoo!のClient IDが未設定' );
		}
		$q = array(
			'appid'     => $s['yahoo_appid'],
			'jan_code'  => $product->jan,
			'seller_id' => $offer->store_code,
			'condition' => 'new',
			'results'   => 20,
			'sort'      => '+price',
		);
		if ( $s['yahoo_vc_affiliate'] ) {
			$q['affiliate_type'] = 'vc';
			$q['affiliate_id']   = $s['yahoo_vc_affiliate'];
		}

		self::throttle( 'yahoo' );
		$url  = add_query_arg( array_map( 'rawurlencode', $q ), 'https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch' );
		$data = self::json( wp_remote_get( $url, array( 'timeout' => 20, 'user-agent' => self::UA ) ) );
		if ( is_wp_error( $data ) ) {
			return $data;
		}

		$premium = (int) $s['yahoo_premium'] === 1;
		$best    = null;
		foreach ( $data['hits'] ?? array() as $h ) {
			$price = $premium && ! empty( $h['premiumPrice'] ) ? (int) $h['premiumPrice'] : (int) $h['price'];
			$pt    = $h['point'] ?? array();
			$amt   = $premium ? ( $pt['lyLimitedPremiumBonusAmount'] ?? 0 ) : ( $pt['lyLimitedBonusAmount'] ?? 0 );
			$times = $premium ? ( $pt['lyLimitedPremiumBonusTimes'] ?? 0 ) : ( $pt['lyLimitedBonusTimes'] ?? 0 );
			$cand  = array(
				'price'        => $price,
				'in_stock'     => ! empty( $h['inStock'] ) ? 1 : 0,
				'shop_pct'     => (float) $times,
				'store_points' => (int) $amt,
				'url'          => (string) $h['url'],
				'item_name'    => mb_substr( (string) $h['name'], 0, 250 ),
				'item_code'    => (string) ( $h['code'] ?? '' ),
				'image'        => (string) ( $h['image']['medium'] ?? $h['image']['small'] ?? '' ),
				// shipping.code 2=送料無料。それ以外はオファーに設定した送料
				'shipping'     => 2 === (int) ( $h['shipping']['code'] ?? 1 ) ? 0 : (int) $offer->shipping_yen,
			);
			if ( null === $best
				|| ( $cand['in_stock'] > $best['in_stock'] )
				|| ( $cand['in_stock'] === $best['in_stock'] && $cand['price'] < $best['price'] ) ) {
				$best = $cand;
			}
		}
		return $best ?? new WP_Error( 'cfgd_notfound', "Yahoo! {$offer->store_code} で {$product->jan} が見つからない" );
	}

	/**
	 * JAN未入力の商品を、Yahoo!の商品検索で型番から特定する。
	 * 検索語の先頭の「!」なしトークンだけを検索クエリに使い、照合は pick_jan() で行う。
	 *
	 * @return array|WP_Error|null
	 */
	public static function resolve_jan( $keyword ) {
		$appid = CFGD_Settings::get( 'yahoo_appid' );
		if ( ! $appid ) {
			return new WP_Error( 'cfgd_config', 'Yahoo!のClient IDが未設定（JAN自動取得に必要）' );
		}
		$query = implode( ' ', array_filter( preg_split( '/\s+/u', $keyword ), fn( $t ) => '' !== $t && ! str_starts_with( $t, '!' ) ) );
		self::throttle( 'yahoo' );
		$url  = add_query_arg( array_map( 'rawurlencode', array(
			'appid'     => $appid,
			'query'     => $query,
			'condition' => 'new',
			'results'   => 50,
		) ), 'https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch' );
		$data = self::json( wp_remote_get( $url, array( 'timeout' => 20, 'user-agent' => self::UA ) ) );
		if ( is_wp_error( $data ) ) {
			return $data;
		}
		return CFGD_Parsers::pick_jan( $data['hits'] ?? array(), $keyword );
	}

	/**
	 * あるJANを売っている店舗の一覧（店舗コード探し用）。
	 *
	 * @return array [ ['mall'=>..,'code'=>..,'name'=>..], ... ]
	 */
	public static function sellers_for_jan( $jan, $fallback = '' ) {
		$s   = CFGD_Settings::all();
		$out = array();

		if ( $s['rakuten_app_id'] && $s['rakuten_access_key'] ) {
			$found = self::rakuten_sellers( $jan, $s );
			$note  = "JAN {$jan}：" . count( $found ) . '件';
			// 楽天は商品説明にJANがない出品が多いので、0件なら品番名で探し直す
			if ( ! $found && '' !== $fallback ) {
				$found = self::rakuten_sellers( $fallback, $s );
				$note .= " →「{$fallback}」で" . count( $found ) . '件';
			}
			self::$rakuten_log[] = $note;
			$out = array_merge( $out, $found );
		}

		if ( $s['yahoo_appid'] ) {
			self::throttle( 'yahoo' );
			$url  = add_query_arg( array_map( 'rawurlencode', array(
				'appid'    => $s['yahoo_appid'],
				'jan_code' => $jan,
				'results'  => 100,
			) ), 'https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch' );
			$data = self::json( wp_remote_get( $url, array( 'timeout' => 20, 'user-agent' => self::UA ) ) );
			if ( ! is_wp_error( $data ) ) {
				foreach ( $data['hits'] ?? array() as $h ) {
					$out[] = array( 'mall' => 'yahoo', 'code' => $h['seller']['sellerId'] ?? '', 'name' => $h['seller']['name'] ?? '' );
				}
			}
		}
		return $out;
	}

	private static function rakuten_sellers( $keyword, $s ) {
		$out = array();
		for ( $page = 1; $page <= 2; $page++ ) {
			self::throttle( 'rakuten' );
			$url  = add_query_arg( array_map( 'rawurlencode', array(
				'applicationId' => $s['rakuten_app_id'],
				'accessKey'     => $s['rakuten_access_key'],
				'formatVersion' => 2,
				'keyword'       => $keyword,
				'hits'          => 30,
				'page'          => $page,
				'availability'  => 0,
				'elements'      => 'shopCode,shopName,itemName',
			) ), self::RAKUTEN_SEARCH );
			$data = self::json( wp_remote_get( $url, array(
				'timeout'    => 20,
				'user-agent' => self::UA,
				'headers'    => array( 'Referer' => home_url( '/' ), 'Origin' => untrailingslashit( home_url() ) ),
			) ) );
			if ( is_wp_error( $data ) ) {
				self::$rakuten_error = $data->get_error_message();
				break;
			}
			$items = $data['items'] ?? $data['Items'] ?? array();
			foreach ( $items as $it ) {
				$it = $it['item'] ?? $it['Item'] ?? $it; // formatVersion=1 で返ってきた場合にも対応
				if ( ! empty( $it['shopCode'] ) ) {
					$out[] = array( 'mall' => 'rakuten', 'code' => $it['shopCode'], 'name' => $it['shopName'] ?? $it['shopCode'] );
				}
			}
			if ( ! $items || ( $data['pageCount'] ?? 1 ) <= $page ) {
				break;
			}
		}
		return $out;
	}

	/** 短縮URL（yahoo.jp・a.r10.to など）を最大4回までたどって元のURLにする。 */
	public static function resolve_url( $url ) {
		for ( $i = 0; $i < 4; $i++ ) {
			if ( CFGD_Parsers::parse_shop_url( $url ) ) {
				return $url;
			}
			$res = wp_remote_head( $url, array( 'redirection' => 0, 'timeout' => 10, 'user-agent' => self::UA ) );
			if ( is_wp_error( $res ) ) {
				return $url;
			}
			$loc = wp_remote_retrieve_header( $res, 'location' );
			if ( ! $loc ) {
				return $url;
			}
			$url = is_array( $loc ) ? end( $loc ) : $loc;
		}
		return $url;
	}

	/** 公開ページのHTMLを取得（1日1〜2回だけ）。 */
	public static function page( $url ) {
		self::throttle( 'page' );
		$res = wp_remote_get( $url, array(
			'timeout'    => 30,
			'user-agent' => self::UA,
			'headers'    => array( 'Accept-Language' => 'ja' ),
		) );
		if ( is_wp_error( $res ) ) {
			return $res;
		}
		$code = wp_remote_retrieve_response_code( $res );
		if ( 200 !== $code ) {
			return new WP_Error( 'cfgd_http', "HTTP {$code}: {$url}" );
		}
		return wp_remote_retrieve_body( $res );
	}

	private static function json( $res ) {
		if ( is_wp_error( $res ) ) {
			return $res;
		}
		$code = wp_remote_retrieve_response_code( $res );
		$body = json_decode( wp_remote_retrieve_body( $res ), true );
		if ( 200 !== $code ) {
			$msg = is_array( $body ) ? ( $body['errors']['errorMessage'] ?? $body['error_description'] ?? $body['error'] ?? $body['Error']['Message'] ?? '' ) : '';
			if ( ! is_string( $msg ) ) {
				$msg = wp_json_encode( $msg );
			}
			return new WP_Error( 'cfgd_http', "HTTP {$code} {$msg}" );
		}
		return is_array( $body ) ? $body : new WP_Error( 'cfgd_json', 'JSONを読めない' );
	}
}
