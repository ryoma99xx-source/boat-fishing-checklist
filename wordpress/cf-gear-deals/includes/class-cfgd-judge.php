<?php
/**
 * 実質価格の計算と「買い時」判定。WordPressに依存しない純粋関数。
 *
 * 前提：年に一度の高額品を1回で買う想定なので、各施策の上限（月間・期間）は
 *       「この買い物1回で上限まで使える」とみなして円で頭打ちにする。
 */
class CFGD_Judge {

	/**
	 * @param array $offer {
	 *   mall: 'rakuten'|'yahoo', store: string, price: int, shipping: int,
	 *   shop_pct: float   楽天：商品倍率（例 5 = 5%、基本1%込み）／Yahoo：ストアポイント率
	 *   store_points: int Yahoo：APIのストアポイント額（あればこちらを優先）
	 * }
	 * @param object[] $campaigns 有効な施策（rate_pct, cap_yen, scope, stores, name）
	 * @param object[] $coupons   有効なクーポン（pct, yen, cap_yen, min_order, note）
	 * @param array    $opt       limited_map（施策名の一部 => ストア配列）, yahoo_total_cap_pct
	 */
	public static function effective( array $offer, array $campaigns, array $coupons, array $opt = array() ) {
		$price = (int) $offer['price'];
		$lines = array();

		// 1) クーポン（最も値引きが大きい1枚）
		$coupon = 0;
		$c_note = '';
		foreach ( $coupons as $c ) {
			if ( $price < (int) $c->min_order ) {
				continue;
			}
			$v = (int) $c->yen > 0 ? (int) $c->yen : (int) floor( $price * (float) $c->pct / 100 );
			if ( (int) $c->cap_yen > 0 ) {
				$v = min( $v, (int) $c->cap_yen );
			}
			if ( $v > $coupon ) {
				$coupon = $v;
				$c_note = $c->note;
			}
		}
		if ( $coupon > 0 ) {
			$lines[] = array( 'label' => 'クーポン' . ( $c_note ? "（{$c_note}）" : '' ), 'yen' => $coupon, 'type' => 'coupon' );
		}

		// ポイントはクーポン適用後の金額にかかる。両モールとも原則「税抜」が対象で、
		// 条件に「税込」とある施策（PayPayクレジット・楽天カード通常分など）だけ税込の決済額。
		$base    = max( 0, $price - $coupon );
		$base_ex = intdiv( (int) $base * 10, 11 ); // 小数誤差で1円ずれないよう整数で計算
		$points  = 0;

		// 2) ストア・商品のポイント
		if ( 'rakuten' === $offer['mall'] ) {
			$pct     = max( 1.0, (float) $offer['shop_pct'] );
			$v       = (int) floor( $base_ex * $pct / 100 );
			$lines[] = array( 'label' => "ショップ・商品ポイント {$pct}%", 'yen' => $v, 'type' => 'point' );
			$points += $v;
		} else {
			if ( ! empty( $offer['store_points'] ) ) {
				$v = (int) floor( (int) $offer['store_points'] * ( $price > 0 ? $base / $price : 0 ) );
			} else {
				$v = (int) floor( $base_ex * (float) $offer['shop_pct'] / 100 );
			}
			$lines[] = array( 'label' => 'ストアポイント', 'yen' => $v, 'type' => 'point' );
			$points += $v;
		}

		// 3) モールの施策（上限で頭打ち）
		$possible = array();
		$map      = $opt['limited_map'] ?? array();
		// 「5のつく日」と「プレミアムな日曜日」が重なる日（日曜の5・15・25日）は、プレミアムな日曜日が開催されない
		// （2026/10/25 運営者の内訳で確認：5のつく日+4%だけ付いていた）
		$has_five = 'yahoo' === $offer['mall'] && (bool) array_filter( $campaigns, fn( $c ) => str_contains( (string) $c->name, '5のつく日' ) );
		foreach ( $campaigns as $c ) {
			if ( null === $c->rate_pct ) {
				continue;
			}
			if ( $has_five && str_contains( (string) $c->name, 'プレミアムな日曜日' ) ) {
				continue;
			}
			$applies = true;
			$bsp     = 'yahoo' === $offer['mall'] && str_contains( (string) $c->name, 'ボーナスストアPlus' );
			// ボーナスストアPlusの名前が付く施策（「さらに+2%」「優良ストアでさらに+3%」など）は、
			// カレンダーの表記に関係なく、今日のボーナスストアPlus対象店舗だけに付ける
			if ( 'limited' === $c->scope || $bsp ) {
				$applies = self::limited_applies( $c, $offer['store'], $map );
			}
			$cap_yen = (int) $c->cap_yen;
			if ( $bsp && $cap_yen <= 0 ) {
				$cap_yen = self::bsp_cap( $c->name, (float) $c->rate_pct );
			}
			if ( 3000 > $price && $bsp && str_contains( (string) $c->name, 'さらに' ) ) {
				$applies = false; // 上乗せ分は3,000円以上の注文が対象
			}
			$on = str_contains( (string) ( $c->conditions ?? '' ), '税込' ) ? $base : $base_ex;
			$v  = (int) floor( $on * (float) $c->rate_pct / 100 );
			if ( $cap_yen > 0 ) {
				$v = min( $v, $cap_yen );
			}
			$rate  = '+' . rtrim( rtrim( (string) $c->rate_pct, '0' ), '.' ) . '%';
			$label = ( str_contains( $c->name, $rate ) ? $c->name : $c->name . ' ' . $rate ) . ( $cap_yen > 0 ? '（上限' . number_format( $cap_yen ) . '円）' : '' );
			// 「最大+5%」のような施策は、条件や本人の上限の残りで実際の付与が大きく変わる
			// （例：ヤフショ感謝デー最大+5%が、上限到達で0.7%しか付かない）ので計算に入れず「付くかも」に回す
			if ( $applies && ! empty( $c->is_max ) ) {
				$possible[] = array( 'label' => $label . '・条件と上限しだい', 'yen' => $v );
				continue;
			}
			if ( $applies ) {
				$lines[] = array( 'label' => $label, 'yen' => $v, 'type' => 'point' );
				$points += $v;
			} else {
				$possible[] = array( 'label' => $label . '・対象ストアなら', 'yen' => $v );
			}
		}

		// 4) Yahoo!は合計付与率に上限がある
		if ( 'yahoo' === $offer['mall'] && ! empty( $opt['yahoo_total_cap_pct'] ) ) {
			$cap = (int) floor( $base_ex * (float) $opt['yahoo_total_cap_pct'] / 100 );
			if ( $points > $cap ) {
				$lines[] = array( 'label' => '合計付与率の上限で調整', 'yen' => $cap - $points, 'type' => 'point' );
				$points  = $cap;
			}
		}

		$eff = $price + (int) $offer['shipping'] - $coupon - $points;

		return array(
			'price'      => $price,
			'shipping'   => (int) $offer['shipping'],
			'coupon_yen' => $coupon,
			'points'     => $points,
			'eff_price'  => $eff,
			'lines'      => $lines,
			'possible'   => $possible,
		);
	}

	/** ボーナスストアPlusの上限（ページで読めなかったとき）：+9%は10,000円、+4%と上乗せ分は5,000円相当。 */
	public static function bsp_cap( $name, $rate ) {
		return ( ! str_contains( (string) $name, 'さらに' ) && $rate >= 9 ) ? 10000 : 5000;
	}

	public static function limited_applies( $c, $store, array $map ) {
		$stores = array_filter( array_map( 'trim', explode( ',', (string) $c->stores ) ) );
		if ( in_array( $store, $stores, true ) ) {
			return true;
		}
		// 「ボーナスストアPlus +9%」「+4%」は、その日の判定で決めた店舗だけ（別の倍率の店に付けない）
		if ( preg_match( '/^ボーナスストアPlus \+\d/u', (string) $c->name ) ) {
			return false;
		}
		// 「*」：その日 BONUS / BONUS+ が付いた店。ボーナスストアPlusの名前の付く企画（上乗せ分）には使わない
		if ( ! empty( $map['*'] ) && ! str_contains( (string) $c->name, 'ボーナスストアPlus' ) && in_array( $store, (array) $map['*'], true ) ) {
			return true;
		}
		foreach ( $map as $needle => $list ) {
			if ( '*' !== $needle && '' !== $needle && str_contains( $c->name, $needle ) && in_array( $store, $list, true ) ) {
				return true;
			}
		}
		return false;
	}

	/**
	 * 買い時判定：今日の実質最安 ≤ 直近N日の実質最安 ＋ 本体価格 × 許容%。
	 *
	 * @param int   $today_eff   今日の最安オファーの実質価格
	 * @param int   $today_price そのオファーの本体価格
	 * @param int[] $history     直近N日の日ごとの実質最安（今日を含んでよい）
	 */
	/**
	 * 店舗の目安：指定店舗で、ポイント還元率（クーポン後の税抜額に対する%）が閾値以上、かつクーポンあり。
	 *
	 * @param string $stores 'yahoo:casting,yahoo:point-i' 形式
	 */
	/**
	 * @param array $price_check ['total'=>この出品の価格＋送料, 'min'=>同じ品番の在庫ありの最安（価格＋送料・ポイント前）, 'over_pct'=>許容%]
	 *                           値付けが最安より許容%を超えて高い店は、ポイントが多くても買い時にしない
	 */
	public static function strong( $mall, $store, $price, $coupon_yen, $points, $stores, $min_rate, $need_coupon, $any_rate = 0, array $price_check = array() ) {
		$list    = array_filter( array_map( 'trim', explode( ',', strtolower( (string) $stores ) ) ) );
		$listed  = in_array( strtolower( $mall . ':' . $store ), $list, true );
		$base    = intdiv( max( 0, (int) $price - (int) $coupon_yen ) * 10, 11 );
		$rate    = $base > 0 ? round( 100 * (int) $points / $base, 1 ) : 0.0;
		$ok      = $listed && $rate >= (float) $min_rate && ( ! $need_coupon || (int) $coupon_yen > 0 );
		// どの店でも、Yahoo!でポイント還元がこの%以上なら買い時（クーポン不要）
		$any_ok  = 'yahoo' === $mall && (float) $any_rate > 0 && $rate >= (float) $any_rate;
		if ( ! $listed && ! $any_ok ) {
			return null;
		}
		$ok     = $ok || $any_ok;
		$reason = 'ポイント還元' . $rate . '%' . ( (int) $coupon_yen > 0 ? '＋クーポン' . number_format( (int) $coupon_yen ) . '円' : '（クーポンなし）' );
		$min    = (int) ( $price_check['min'] ?? 0 );
		$total  = (int) ( $price_check['total'] ?? $price );
		$over   = (float) ( $price_check['over_pct'] ?? 0 );
		if ( $ok && $min > 0 && $over > 0 && $total > $min * ( 1 + $over / 100 ) ) {
			$ok      = false;
			$reason .= '・ただし値付けが最安店より' . round( 100 * ( $total - $min ) / $min, 1 ) . '%高い';
		}
		return array(
			'ok'     => $ok,
			'rate'   => $rate,
			'reason' => $reason,
		);
	}

	public static function verdict( $today_eff, $today_price, array $history, $tolerance_pct, $min_days ) {
		$days = count( $history );
		if ( $days < $min_days ) {
			return array( 'buy' => false, 'reason' => "記録{$days}日（{$min_days}日たまるまで判定しない）", 'min' => $days ? min( $history ) : null, 'diff' => null );
		}
		$min       = min( $history );
		$allowance = (int) floor( $today_price * $tolerance_pct / 100 );
		$diff      = $today_eff - $min;
		$buy       = $diff <= $allowance;
		return array(
			'buy'       => $buy,
			'min'       => $min,
			'diff'      => $diff,
			'allowance' => $allowance,
			'reason'    => $buy
				? ( $diff <= 0 ? '直近の実質最安を更新' : '実質最安との差' . number_format( $diff ) . '円（許容' . number_format( $allowance ) . '円以内）' )
				: '実質最安より' . number_format( $diff ) . '円高い',
		);
	}
}
