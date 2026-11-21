<?php
/**
 * カレンダーページのHTML → 施策データ。WordPressに依存しない純粋関数（テスト可能）。
 */
class CFGD_Parsers {

	/** HTMLをブロック単位の行に分解する。 */
	public static function html_to_lines( $html ) {
		$html = preg_replace( '#<(script|style|noscript|svg)\b[^>]*>.*?</\1>#is', ' ', $html );
		// バナー画像の告知文（alt）も1行として拾う
		$html = preg_replace_callback( '#<img\b[^>]*\balt\s*=\s*("([^"]*)"|\'([^\']*)\')[^>]*>#i', fn( $m ) => "\n" . ( '' !== $m[2] ? $m[2] : ( $m[3] ?? '' ) ) . "\n", $html );
		$html = preg_replace( '#<(br|/p|/div|/li|/h[1-6]|/dt|/dd|/tr|/td|/th|/span|/a|/button|/time)\b[^>]*>#i', "$0\n", $html );
		$text = html_entity_decode( strip_tags( $html ), ENT_QUOTES | ENT_HTML5, 'UTF-8' );
		$out  = array();
		foreach ( preg_split( '/\R/u', $text ) as $line ) {
			$line = trim( preg_replace( '/[ \t\x{3000}]+/u', ' ', $line ) );
			if ( '' !== $line ) {
				$out[] = $line;
			}
		}
		return $out;
	}

	/**
	 * Yahoo!ショッピング「ボーナスカレンダー」。
	 * 返り値: [ ['date'=>'2026-10-15','name'=>..,'rate'=>4.0,'is_max'=>0,'cap'=>2000,'conditions'=>..,'limited'=>bool], ... ]
	 *         + 期間開催: ['start'=>..,'end'=>..] を持つ要素
	 *
	 * @param string[] $lines html_to_lines() の結果
	 * @param int      $now   基準時刻（年の判定に使う）
	 */
	public static function parse_yahoo_calendar( array $lines, $now ) {
		$year     = (int) date( 'Y', $now );
		$month    = 0;
		$day      = 0;
		$items    = array();
		$name     = null;
		$in_cal   = false;
		$period   = false;
		$p_start  = null;
		$p_end    = null;
		$weekdays = '/^[月火水木金土日]$/u';
		$n        = count( $lines );

		for ( $i = 0; $i < $n; $i++ ) {
			$l = $lines[ $i ];

			// 期間ブロック「10/08~10/21」で月を確定。
			if ( preg_match( '#^(\d{1,2})/(\d{1,2})\s*[~〜～]\s*(\d{1,2})/(\d{1,2})$#u', $l, $m ) ) {
				$in_cal = true;
				$period = false;
				$month  = (int) $m[1];
				$day    = (int) $m[2] - 1;
				$year   = self::guess_year( $month, $now );
				continue;
			}
			if ( ! $in_cal ) {
				continue;
			}
			if ( str_starts_with( $l, '期間開催の予定' ) ) {
				$period = true;
				$name   = null;
				continue;
			}
			if ( str_starts_with( $l, 'おトクなクーポン' ) ) {
				break; // カレンダー部分の終わり
			}
			if ( preg_match( '/^※/u', $l ) ) {
				if ( $period ) {
					break; // 期間開催の注記に入ったら終わり
				}
				continue;
			}

			if ( $period ) {
				// 「9 (金)」「〜」「15 (木)」
				if ( preg_match( '/^(\d{1,2})\s*\((.)\)$/u', $l, $m ) ) {
					if ( null === $p_start ) {
						$p_start = (int) $m[1];
					} else {
						$p_end = (int) $m[1];
					}
					continue;
				}
				if ( preg_match( '/^[~〜～]$/u', $l ) ) {
					continue;
				}
				if ( null !== $p_end && null === $name ) {
					$name = $l;
					continue;
				}
				if ( null !== $name && null !== ( $rate = self::rate_of( $l ) ) ) {
					$cond = $lines[ $i + 1 ] ?? '';
					list( $s, $e ) = self::period_dates( $p_start, $p_end, $now );
					$items[] = array(
						'start'      => $s,
						'end'        => $e,
						'name'       => $name,
						'rate'       => $rate[0],
						'is_max'     => $rate[1],
						'cap'        => self::cap_of( $cond ),
						'conditions' => $cond,
						'limited'    => self::is_limited( $cond ),
					);
					$name    = null;
					$p_start = null;
					$p_end   = null;
				}
				continue;
			}

			// 日付「15」、月またぎ「11/1」
			if ( preg_match( '#^(\d{1,2})/(\d{1,2})$#', $l, $m ) ) {
				$month = (int) $m[1];
				$day   = (int) $m[2];
				$year  = self::guess_year( $month, $now );
				$name  = null;
				continue;
			}
			if ( preg_match( '/^\d{1,2}$/', $l ) ) {
				$d = (int) $l;
				if ( $d < $day ) { // 月が変わった
					$month++;
					if ( $month > 12 ) {
						$month = 1;
						$year++;
					}
				}
				$day  = $d;
				$name = null;
				continue;
			}
			if ( preg_match( $weekdays, $l ) || '詳細を見る' === $l || '閉じる' === $l ) {
				continue;
			}

			$rate = self::rate_of( $l );
			if ( null !== $rate && null !== $name && $month > 0 ) {
				$cond    = $lines[ $i + 1 ] ?? '';
				$items[] = array(
					'date'       => sprintf( '%04d-%02d-%02d', $year, $month, $day ),
					'name'       => $name,
					'rate'       => $rate[0],
					'is_max'     => $rate[1],
					'cap'        => self::cap_of( $cond ),
					'conditions' => $cond,
					'limited'    => self::is_limited( $cond ),
				);
				$name = null;
				$i++; // 条件行を読み飛ばす
				continue;
			}
			if ( '先着順' === $l ) { // クーポン系（ポイントではない）
				$name = null;
				$i++;
				continue;
			}
			$name = $l;
		}
		return $items;
	}

	/** 「+4%」「＋5%」「最大+5%」「最大24%」→ [率, 最大表記か] */
	public static function rate_of( $l ) {
		// 「+4%〜+7%」のような幅のある倍率は、低いほう（だれでも付く分）を使う（2026/10/31 爆買WEEK）
		if ( preg_match( '/^[+＋]?\s*(\d+(?:\.\d+)?)\s*[%％]?\s*[~〜～]\s*[+＋]?\s*(\d+(?:\.\d+)?)\s*[%％]$/u', $l, $m ) ) {
			return array( (float) min( $m[1], $m[2] ), 0 );
		}
		if ( preg_match( '/^(最大)?\s*[+＋]?\s*(\d+(?:\.\d+)?)\s*[%％]$/u', $l, $m ) ) {
			return array( (float) $m[2], '' !== $m[1] ? 1 : 0 );
		}
		return null;
	}

	/** 「付与上限2,000円相当」→ 2000（なければ0） */
	public static function cap_of( $cond ) {
		if ( preg_match( '/上限\s*([\d,]+)\s*円/u', $cond, $m ) ) {
			return (int) str_replace( ',', '', $m[1] );
		}
		return 0;
	}

	public static function is_limited( $cond ) {
		return (bool) preg_match( '/対象ストア(限定|・商品限定)/u', $cond );
	}

	public static function guess_year( $month, $now ) {
		$y = (int) date( 'Y', $now );
		$m = (int) date( 'n', $now );
		if ( $month < $m - 6 ) {
			return $y + 1;
		}
		if ( $month > $m + 6 ) {
			return $y - 1;
		}
		return $y;
	}

	/** 「9〜15」のような日だけの期間を、今日に近い年月で日付にする。 */
	public static function period_dates( $s, $e, $now ) {
		$y  = (int) date( 'Y', $now );
		$m  = (int) date( 'n', $now );
		$sm = $m;
		// 終了日がもう過ぎた日なら来月の予定とみなす
		if ( $e < (int) date( 'j', $now ) - 1 && $s <= $e ) {
			$sm = $m + 1;
		}
		$em = $s <= $e ? $sm : $sm + 1;
		$start = mktime( 0, 0, 0, $sm, $s, $y );
		$end   = mktime( 23, 59, 59, $em, $e, $y );
		return array( date( 'Y-m-d H:i:s', $start ), date( 'Y-m-d H:i:s', $end ) );
	}

	/** 型番照合用の正規化：全角→半角、小文字、空白・記号を除去。 */
	public static function norm( $s ) {
		$s = mb_convert_kana( (string) $s, 'asKV', 'UTF-8' );
		$s = mb_strtolower( $s, 'UTF-8' );
		return preg_replace( '/[\s\-_・\/()（）「」【】\[\]]+/u', '', $s );
	}

	/**
	 * 商品名が検索語に合うか（全トークンを含み、!トークンを含まない）。
	 * 数字入りのトークンは直後に英字が続くと別品番とみなす（100J と 100JL を区別）。
	 */
	public static function name_matches( $name, $keyword ) {
		$name = self::norm( $name );
		foreach ( preg_split( '/\s+/u', trim( (string) $keyword ) ) as $t ) {
			if ( '' === $t ) {
				continue;
			}
			if ( str_starts_with( $t, '!' ) ) {
				$n = self::norm( substr( $t, 1 ) );
				if ( '' !== $n && str_contains( $name, $n ) ) {
					return false;
				}
				continue;
			}
			$n = self::norm( $t );
			if ( preg_match( '/\d/', $n ) && preg_match( '/[a-z0-9]$/', $n ) ) {
				if ( ! preg_match( '/' . preg_quote( $n, '/' ) . '(?![a-z])/u', $name ) ) {
					return false;
				}
			} elseif ( ! str_contains( $name, $n ) ) {
				return false;
			}
		}
		return true;
	}

	/** 品番名から括弧書き（右・左・ギア比）を除いた検索語。 */
	public static function name_keyword( $product ) {
		$kw = trim( (string) ( $product->keyword ?? '' ) );
		if ( '' !== $kw ) {
			return $kw;
		}
		return trim( preg_replace( '/[（(].*?[）)]/u', '', (string) $product->name ) );
	}

	/**
	 * 検索結果からJANを1つ選ぶ。検索語の全トークン（空白区切り）が商品名に含まれ、
	 * NG語（「!」始まりのトークン）を含まないものの中で、最も多く出てくるJAN。
	 *
	 * @param array  $hits    [['name'=>..,'janCode'=>..], ...]
	 * @param string $keyword 例「バルケッタ プレミアム 150DHXG !151 !Fカスタム」
	 * @return array{jan:string,count:int,total:int}|null
	 */
	public static function pick_jan( array $hits, $keyword ) {
		$need = array();
		$ng   = array();
		foreach ( preg_split( '/\s+/u', trim( $keyword ) ) as $t ) {
			if ( '' === $t ) {
				continue;
			}
			if ( str_starts_with( $t, '!' ) ) {
				$ng[] = self::norm( substr( $t, 1 ) );
			} else {
				$need[] = self::norm( $t );
			}
		}
		$count = array();
		$total = 0;
		foreach ( $hits as $h ) {
			$jan = preg_replace( '/\D/', '', (string) ( $h['janCode'] ?? '' ) );
			if ( 13 !== strlen( $jan ) ) {
				continue;
			}
			$name = self::norm( $h['name'] ?? '' );
			foreach ( $need as $t ) {
				if ( ! str_contains( $name, $t ) ) {
					continue 2;
				}
			}
			foreach ( $ng as $t ) {
				if ( '' !== $t && str_contains( $name, $t ) ) {
					continue 2;
				}
			}
			$count[ $jan ] = ( $count[ $jan ] ?? 0 ) + 1;
			$total++;
		}
		if ( ! $count ) {
			return null;
		}
		arsort( $count );
		$jan = array_key_first( $count );
		return array( 'jan' => (string) $jan, 'count' => $count[ $jan ], 'total' => $total );
	}

	/**
	 * 楽天の店舗トップ（未ログイン）から、ショップ全体のポイント倍率・クーポン見出し・
	 * 「単価◯円以上を3商品同時購入で+◯倍（上限◯pt）」企画を読む。
	 * LINE友だち・楽天モバイル・アプリ限定のクーポンは無視する。
	 *
	 * @return array{shop_rate:?float, coupons:array, triple:?array}
	 */
	public static function parse_rakuten_shop( array $lines ) {
		$out = array( 'shop_rate' => null, 'coupons' => array(), 'triple' => null );
		$ng  = '/LINE|ライン|友だち|友達|モバイル|アプリ|初回|新規|お誕生日|ランク/u';
		$n   = count( $lines );
		$seen = array();

		for ( $i = 0; $i < $n; $i++ ) {
			$l = mb_convert_kana( $lines[ $i ], 'asKV', 'UTF-8' );

			// ショップ全体の倍率「通常商品10倍」
			if ( null === $out['shop_rate'] && preg_match( '/通常商品\s*(\d+(?:\.\d+)?)\s*倍/u', $l, $m ) ) {
				$out['shop_rate'] = (float) $m[1];
			}

			// クーポン見出し「1,000円OFFクーポン」「5%OFFクーポン」
			if ( preg_match( '/クーポン/u', $l ) && ! preg_match( $ng, $l ) ) {
				if ( preg_match( '/([\d,]+)\s*円\s*(OFF|引き|オフ)/iu', $l, $m ) ) {
					$v   = (int) str_replace( ',', '', $m[1] );
					$key = 'yen' . $v;
					if ( $v > 0 && ! isset( $seen[ $key ] ) ) {
						$seen[ $key ]     = true;
						$out['coupons'][] = array( 'type' => 'yen', 'value' => $v, 'label' => $lines[ $i ] );
					}
				} elseif ( preg_match( '/(\d+(?:\.\d+)?)\s*%\s*(OFF|引き|オフ)/iu', $l, $m ) ) {
					$v   = (float) $m[1];
					$key = 'pct' . $v;
					if ( $v > 0 && $v < 100 && ! isset( $seen[ $key ] ) ) {
						$seen[ $key ]     = true;
						$out['coupons'][] = array( 'type' => 'pct', 'value' => $v, 'label' => $lines[ $i ] );
					}
				}
			}

			// 3商品同時購入企画（数行にまたがることがあるので前後をまとめて見る）
			if ( null === $out['triple'] && preg_match( '/[3３]\s*(商品|点|品)/u', $l ) ) {
				// バナーは「10」「倍」のように細切れになることがあるので前3行・後4行を見る
				$win = mb_convert_kana( implode( ' ', array_slice( $lines, max( 0, $i - 3 ), 8 ) ), 'asKV', 'UTF-8' );
				$win = preg_replace( '/通常商品\s*\d+\s*倍/u', '', $win ); // ショップ全体倍率と混同しない
				if ( preg_match( '/(同時|一緒|まとめ|一度|買いまわり|買い回り|以上購入|以上のご購入)/u', $win )
					&& preg_match( '/(\d+)\s*倍/u', $win ) ) {
					// 倍率の読み方：「特典ポイント9倍」があればそれ、「さらに10倍」なら上乗せ、
					// 「ポイント10倍」だけなら通常1倍込みの合計とみなして9倍の上乗せ。
					if ( preg_match( '/特典\s*ポイント\s*(\d+)\s*倍/u', $win, $x ) ) {
						$rate = (float) $x[1];
					} elseif ( preg_match( '/(さらに|プラス|\+)\s*(\d+)\s*倍/u', $win, $x ) ) {
						$rate = (float) $x[2];
					} else {
						preg_match_all( '/(\d+)\s*倍/u', $win, $all );
						$rate = max( 0, max( array_map( 'floatval', $all[1] ) ) - 1 );
					}
					$cap = 0;
					if ( preg_match( '/(上限|最大)\s*([\d,]+)\s*(ポイント|pt|P)/iu', $win, $c ) ) {
						$cap = (int) str_replace( ',', '', $c[2] );
					} elseif ( preg_match( '/([\d,]+)\s*(ポイント|pt)\s*(まで|上限)/iu', $win, $c ) ) {
						$cap = (int) str_replace( ',', '', $c[1] );
					}
					$min = 0;
					// 「単価100円以上」「1商品あたり100円(税抜)以上」
					if ( preg_match( '/([\d,]+)\s*円\s*(\(\s*税[抜込]\s*\))?\s*以上/u', $win, $mm ) ) {
						$min = (int) str_replace( ',', '', $mm[1] );
					}
					$out['triple'] = array(
						'rate'     => $rate,
						'cap'      => $cap,
						'min_unit' => $min,
						'entry'    => (bool) preg_match( '/エントリー/u', implode( ' ', array_slice( $lines, max( 0, $i - 8 ), 17 ) ) ),
					);
				}
			}
		}
		return $out;
	}

	/**
	 * 商品・店舗ページのURLから、モール・店舗・商品キーを取り出す。
	 *   Yahoo!  https://store.shopping.yahoo.co.jp/casting/4550133297731.html → yahoo / casting / 4550133297731
	 *   楽天    https://item.rakuten.co.jp/casting/4550133297731/          → rakuten / casting / 4550133297731
	 *   店舗トップ（商品キーなし）も可。
	 *
	 * @return array{mall:string,store:string,item:string}|null
	 */
	public static function parse_shop_url( $url ) {
		$url = trim( (string) $url );
		if ( preg_match( '~store\.shopping\.yahoo\.co\.jp/([a-z0-9][a-z0-9\-_]*)/(?:([^/?#]+)\.html)?~i', $url, $m ) ) {
			return array( 'mall' => 'yahoo', 'store' => strtolower( $m[1] ), 'item' => $m[2] ?? '' );
		}
		if ( preg_match( '~item\.rakuten\.co\.jp/([a-z0-9][a-z0-9\-_]*)/([^/?#]+)~i', $url, $m ) ) {
			return array( 'mall' => 'rakuten', 'store' => strtolower( $m[1] ), 'item' => $m[2] );
		}
		if ( preg_match( '#(?:www\.)?rakuten\.co\.jp/([a-z0-9][a-z0-9\-_]*)/?#i', $url, $m ) && ! in_array( strtolower( $m[1] ), array( 'search', 'category', 'event' ), true ) ) {
			return array( 'mall' => 'rakuten', 'store' => strtolower( $m[1] ), 'item' => '' );
		}
		return null;
	}

	/**
	 * Yahoo!直営アフィリエイトの共有リンク（展開後の長いURL）から、本体の
	 * https://affiliate.shopping.yahoo.co.jp/shp-entry?viewUrl=…&affiliateLinkId=…
	 * を取り出す。何重にもURLエンコードされているので、出てくる層まで1段ずつ戻す。
	 * 本体の文字列は発行されたまま（エンコードの段数も含めて）保存する。
	 *
	 * @return array{url:string,store:string,item:string}|null
	 */
	public static function parse_yahoo_afflink( $url ) {
		$s    = (string) $url;
		$host = 'https://affiliate.shopping.yahoo.co.jp/shp-entry?';
		for ( $i = 0; $i < 6; $i++ ) {
			$p = strpos( $s, $host );
			if ( false !== $p && preg_match( '~^(https://affiliate\.shopping\.yahoo\.co\.jp/shp-entry\?viewUrl=([^&\s]+)&affiliateLinkId=([A-Za-z0-9_\-]+))~', substr( $s, $p ), $m ) ) {
				$view = $m[2];
				for ( $j = 0; $j < 6 && ! str_contains( $view, 'store.shopping.yahoo.co.jp/' ); $j++ ) {
					$view = rawurldecode( $view );
				}
				$shop = self::parse_shop_url( $view );
				if ( ! $shop || 'yahoo' !== $shop['mall'] || '' === $shop['item'] ) {
					return null;
				}
				return array( 'url' => $m[1], 'store' => $shop['store'], 'item' => $shop['item'] );
			}
			$s = rawurldecode( $s );
		}
		return null;
	}

	/** 「5%」「５％OFF」→ ['pct',5] ／「1,000」「1000円」→ ['yen',1000] */
	public static function parse_discount( $v ) {
		$v = mb_convert_kana( (string) $v, 'asKV', 'UTF-8' );
		if ( preg_match( '/(\d+(?:\.\d+)?)\s*%/u', $v, $m ) ) {
			return array( 'pct', (float) $m[1] );
		}
		if ( preg_match( '/([\d,]+)/u', $v, $m ) ) {
			$n = (int) str_replace( ',', '', $m[1] );
			// 1〜99だけなら%とみなす（「5」と入れた場合）
			return $n > 0 && $n < 100 ? array( 'pct', (float) $n ) : array( 'yen', $n );
		}
		return null;
	}

	/**
	 * 期限の入力を日時に。「10/16 0:00」「2026-10-16 23:59」「10/16」「」（今日いっぱい）。
	 * 日付だけならその日の23:59:59。年がなければ、今日より前なら翌年。
	 */
	public static function parse_until( $v, $now, DateTimeZone $tz ) {
		$v     = trim( mb_convert_kana( (string) $v, 'asKV', 'UTF-8' ) );
		$today = ( new DateTimeImmutable( '@' . $now ) )->setTimezone( $tz );
		if ( '' === $v ) {
			return $today->format( 'Y-m-d 23:59:59' );
		}
		if ( preg_match( '#^(?:(\d{4})[/\-年])?(\d{1,2})[/\-月](\d{1,2})日?(?:\s+(\d{1,2}):(\d{2}))?#u', $v, $m ) ) {
			$y   = $m[1] ? (int) $m[1] : (int) $today->format( 'Y' );
			$has = isset( $m[4] ) && '' !== $m[4];
			$dt  = $today->setDate( $y, (int) $m[2], (int) $m[3] )->setTime( $has ? (int) $m[4] : 23, $has ? (int) $m[5] : 59, $has ? 0 : 59 );
			if ( ! $m[1] && $dt < $today->setTime( 0, 0 ) ) {
				$dt = $dt->modify( '+1 year' );
			}
			// 「10/16 0:00まで」は10/15いっぱい
			if ( $has && 0 === (int) $m[4] && 0 === (int) $m[5] ) {
				$dt = $dt->modify( '-1 second' );
			}
			return $dt->format( 'Y-m-d H:i:s' );
		}
		return null;
	}

	/**
	 * Yahoo!「ボーナスストアPlus」ページ（生HTML）から、倍率ごとの対象ストアIDを取り出す。
	 * 見出し「+9%対象ストア」「+4%対象ストア」（時期により+10%/+5%）の後ろにあるストアリンクを、次の見出しまで集める。
	 * ※+4%側は一部しか載らないことがあるので、上位（+9%など）の判定にだけ使う。
	 *
	 * @return array [ ['rate'=>9.0,'cap'=>10000,'stores'=>['cado',...]], ... ] 倍率の高い順
	 */
	public static function parse_yahoo_bsplus( $html ) {
		$html = preg_replace( '#<(script|style)\b[^>]*>.*?</\1>#is', ' ', $html );
		if ( ! preg_match_all( '/[+＋]\s*(\d+)\s*[%％]\s*対象ストア/u', $html, $m, PREG_OFFSET_CAPTURE ) ) {
			return array();
		}
		$tiers = array();
		$count = count( $m[0] );
		for ( $i = 0; $i < $count; $i++ ) {
			$from  = $m[0][ $i ][1];
			$to    = $i + 1 < $count ? $m[0][ $i + 1 ][1] : strlen( $html );
			$chunk = substr( $html, $from, $to - $from );
			$rate  = (float) $m[1][ $i ][0];
			preg_match_all( '#store\.shopping\.yahoo\.co\.jp/([a-z0-9][a-z0-9\-_]*)/#i', $chunk, $s );
			$stores = array_values( array_unique( array_map( 'strtolower', $s[1] ) ) );
			$cap    = 0;
			if ( preg_match( '/([\d,]+)\s*円相当/u', strip_tags( $chunk ), $c ) ) {
				$cap = (int) str_replace( ',', '', $c[1] );
			}
			$key = (string) $rate;
			if ( ! isset( $tiers[ $key ] ) ) {
				$tiers[ $key ] = array( 'rate' => $rate, 'cap' => $cap, 'stores' => array() );
			}
			$tiers[ $key ]['stores'] = array_values( array_unique( array_merge( $tiers[ $key ]['stores'], $stores ) ) );
			if ( ! $tiers[ $key ]['cap'] && $cap ) {
				$tiers[ $key ]['cap'] = $cap;
			}
		}
		usort( $tiers, fn( $a, $b ) => $b['rate'] <=> $a['rate'] );
		return $tiers;
	}

	/** Yahoo!の商品ページ（未ログイン）に「デイリーボーナスプラス対象」バッジがあるか。 */
	public static function has_bsplus_badge( $html ) {
		return (bool) preg_match( '/デイリーボーナスプラス|ボーナスストア\s*Plus\s*対象/u', $html );
	}

	/**
	 * 楽天「勝ったら倍」公開ページの「過去のキャンペーン開催日一覧」から、
	 * 指定日が開催日なら上乗せ倍率（2倍→+1、3倍→+2）を返す。なければ null。
	 * 行の形：「10月5日（月）」「楽天イーグルス」「2倍」「10月6日（火）0：00～23：59まで」
	 */
	public static function parse_rakuten_sports( array $lines, $ymd ) {
		list( , $m, $d ) = array_map( 'intval', explode( '-', $ymd ) );
		$n = count( $lines );
		for ( $i = 0; $i < $n; $i++ ) {
			$l = mb_convert_kana( $lines[ $i ], 'asKV', 'UTF-8' );
			if ( ! preg_match( '/(\d+)\s*月\s*(\d+)\s*日.*0\s*:\s*00\s*[～~〜-]\s*23\s*:\s*59/u', $l, $x ) ) {
				continue;
			}
			if ( (int) $x[1] !== $m || (int) $x[2] !== $d ) {
				continue;
			}
			// 同じ行か直前の数行に「2倍」「3倍」
			$ctx = mb_convert_kana( implode( ' ', array_slice( $lines, max( 0, $i - 3 ), 4 ) ), 'asKV', 'UTF-8' );
			$ctx = preg_replace( '/\d+\s*月\s*\d+\s*日/u', '', $ctx );
			if ( preg_match_all( '/([23])\s*倍/u', $ctx, $r ) ) {
				return (float) max( array_map( 'intval', $r[1] ) ) - 1;
			}
		}
		return null;
	}

	/**
	 * 店舗一覧を、探したい店舗名（1行1店舗、「|」で別名）に振り分ける。
	 *
	 * @param array    $sellers sellers_for_jan() の結果を連結したもの
	 * @param string[] $wanted  例 ['かめや', 'Joshin|ジョーシン']
	 * @return array [ 行の文字列 => [ "mall:code" => ['mall','code','name','hits'] ] ]
	 */
	public static function match_sellers( array $sellers, array $wanted ) {
		$agg = array();
		foreach ( $sellers as $s ) {
			if ( '' === (string) $s['code'] ) {
				continue;
			}
			$k = $s['mall'] . ':' . $s['code'];
			if ( ! isset( $agg[ $k ] ) ) {
				$agg[ $k ] = $s + array( 'hits' => 0 );
			}
			$agg[ $k ]['hits']++;
		}
		$out = array();
		foreach ( $wanted as $line ) {
			$line = trim( $line );
			if ( '' === $line ) {
				continue;
			}
			$out[ $line ] = array();
			foreach ( explode( '|', $line ) as $alias ) {
				$a = self::norm( $alias );
				if ( '' === $a ) {
					continue;
				}
				foreach ( $agg as $k => $s ) {
					if ( str_contains( self::norm( $s['name'] ), $a ) || str_contains( self::norm( $s['code'] ), $a ) ) {
						$out[ $line ][ $k ] = $s;
					}
				}
			}
			uasort( $out[ $line ], fn( $x, $y ) => $y['hits'] <=> $x['hits'] );
		}
		return $out;
	}

	/**
	 * 楽天カレンダー（ユーザー投稿カレンダー）。日程だけを取り出し、説明文は保存しない。
	 * 返り値: [ ['kind'=>'marathon','name'=>'お買い物マラソン','start'=>..,'end'=>..], ... ]
	 */
	public static function parse_rakuten_calendar( array $lines ) {
		$kinds = array(
			'supersale' => array( '/スーパー\s*(SALE|セール)/u', '楽天スーパーSALE' ),
			'marathon'  => array( '/マラソン/u', 'お買い物マラソン' ),
			'blackfri'  => array( '/ブラックフライデー/u', 'ブラックフライデー' ),
			'brandday'  => array( '/ブランドデー/u', '楽天ブランドデー' ),
			'wonderful' => array( '/ワンダフルデー/u', 'ワンダフルデー' ),
			'fivezero'  => array( '/5と0のつく日/u', '5と0のつく日' ),
		);
		$re_date = '/^[～~〜]?\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*\(.\)\s*(\d{1,2}:\d{2})?$/u';
		$seen    = array();
		$out     = array();
		$n       = count( $lines );

		for ( $i = 1; $i < $n - 1; $i++ ) {
			if ( ! preg_match( $re_date, $lines[ $i ], $s ) || str_starts_with( ltrim( $lines[ $i ] ), '～' ) ) {
				continue;
			}
			if ( ! preg_match( $re_date, $lines[ $i + 1 ], $e ) ) {
				continue;
			}
			$title = preg_replace( '/^\d{1,2}:\d{2}/', '', $lines[ $i - 1 ] );
			foreach ( $kinds as $kind => $def ) {
				if ( ! preg_match( $def[0], $title ) ) {
					continue;
				}
				$st    = ! empty( $s[4] ) ? $s[4] : '00:00';
				$et    = ! empty( $e[4] ) ? $e[4] : '23:59';
				$start = sprintf( '%04d-%02d-%02d %05s:00', $s[1], $s[2], $s[3], $st );
				$end   = sprintf( '%04d-%02d-%02d %05s:59', $e[1], $e[2], $e[3], $et );
				$key   = $kind . $start;
				if ( isset( $seen[ $key ] ) ) {
					break;
				}
				$seen[ $key ] = true;
				$out[]        = array( 'kind' => $kind, 'name' => $def[1], 'start' => $start, 'end' => $end );
				break;
			}
		}
		return $out;
	}

	/**
	 * 品番の短い呼び名。同じ機種の品番名に共通する頭（区切りまで）を取り、残りを出す。
	 * 「シーボーグ 100J（右）」「シーボーグ 100JL（左）」→「100J（右）」「100JL（左）」
	 */
	public static function variant_labels( array $names ) {
		$names = array_values( $names );
		$pre   = $names[0] ?? '';
		foreach ( $names as $n ) {
			$len = 0;
			$max = min( mb_strlen( $pre ), mb_strlen( $n ) );
			while ( $len < $max && mb_substr( $pre, $len, 1 ) === mb_substr( $n, $len, 1 ) ) {
				$len++;
			}
			$pre = mb_substr( $pre, 0, $len );
		}
		// 区切り（空白）まで戻す
		$cut = 0;
		foreach ( array( ' ', '　' ) as $sp ) {
			$pos = mb_strrpos( $pre, $sp );
			if ( false !== $pos && $pos + 1 > $cut ) {
				$cut = $pos + 1;
			}
		}
		$out = array();
		foreach ( $names as $n ) {
			$rest  = trim( mb_substr( $n, $cut ) );
			$out[] = '' !== $rest ? $rest : $n;
		}
		return $out;
	}


	/** 商品ページのHTMLから、Yahoo!の価格比較ページ（/products/◯◯）のIDを取る。 */
	public static function yahoo_product_id( $html ) {
		return preg_match( '#shopping\.yahoo\.co\.jp/products/([a-z0-9]+)#i', (string) $html, $m ) ? strtolower( $m[1] ) : '';
	}

	/**
	 * Yahoo!の価格比較ページ（未ログイン）を店舗ごとに読む。
	 * 各行は「ストア名（store.shopping.yahoo.co.jp/ストアID/ へのリンク）… ラベル … ポイント ◯pt（◯%）」の並び。
	 * ストアIDのリンクが出てから、別のストアIDのリンクが出るまでを1行とみなす。
	 *
	 * @return array [ storeId => ['pt'=>int,'pct'=>float,'bsp'=>bool,'entry'=>bool,'price'=>int] ]
	 */
	public static function parse_yahoo_products( $html ) {
		$html = preg_replace( '#<(script|style|noscript|svg)\b[^>]*>.*?</\1>#is', ' ', (string) $html );
		// 画像のラベル（「デイリーボーナスプラス」など）を文字として残す
		$html = preg_replace_callback( '#<img\b[^>]*\balt\s*=\s*("([^"]*)"|\'([^\']*)\')[^>]*>#i', fn( $m ) => ' ' . ( '' !== $m[2] ? $m[2] : ( $m[3] ?? '' ) ) . ' ', $html );
		if ( ! preg_match_all( '#store\.shopping\.yahoo\.co\.jp/([a-z0-9][a-z0-9\-_]*)/#i', $html, $m, PREG_OFFSET_CAPTURE ) ) {
			return array();
		}
		// 同じストアのリンクが続く間は1つの区間にまとめる
		$starts = array();
		$prev   = '';
		foreach ( $m[1] as $i => $hit ) {
			$id = strtolower( $hit[0] );
			if ( $id !== $prev ) {
				$starts[] = array( $id, $m[0][ $i ][1] );
				$prev     = $id;
			}
		}
		$out = array();
		$n   = count( $starts );
		for ( $i = 0; $i < $n; $i++ ) {
			list( $id, $from ) = $starts[ $i ];
			$to   = $i + 1 < $n ? $starts[ $i + 1 ][1] : strlen( $html );
			$text = html_entity_decode( strip_tags( substr( $html, $from, $to - $from ) ), ENT_QUOTES | ENT_HTML5, 'UTF-8' );
			$text = preg_replace( '/\s+/u', ' ', mb_convert_kana( $text, 'as', 'UTF-8' ) );
			if ( ! preg_match( '/([\d,]+)\s*pt\s*[（(]\s*(\d+(?:\.\d+)?)\s*%/u', $text, $pm ) ) {
				continue; // ポイント表示がない区間（ストアのトップへのリンクだけ等）
			}
			$row = array(
				'pt'    => (int) str_replace( ',', '', $pm[1] ),
				'pct'   => (float) $pm[2],
				'bsp'   => (bool) preg_match( '/デイリーボーナスプラス|ボーナスストア\s*Plus|BONUS\s*\+/iu', $text ),
				// 「BONUS」「BONUS+」のどちらかが付いた店は、ヤフショ感謝デー・爆買WEEKなど「対象ストア限定」の企画の対象
				// （10/22 感謝デーはBONUSのポイント東日本とBONUS+のかめやの両方に付いた。10/31 爆買WEEKはBONUS+のJoshinに付いた）
				'bonus' => (bool) preg_match( '/BONUS|ボーナス/iu', $text ),
				'entry' => str_contains( $text, '要エントリー' ),
				'price' => preg_match( '/商品価格\s*([\d,]+)\s*円/u', $text, $qm ) ? (int) str_replace( ',', '', $qm[1] ) : 0,
			);
			// 同じストアが2回出たら、ポイントの多いほう
			if ( ! isset( $out[ $id ] ) || $row['pt'] > $out[ $id ]['pt'] ) {
				$out[ $id ] = $row;
			}
		}
		return $out;
	}

	/**
	 * 価格比較ページの1行から、ボーナスストアPlusの倍率（4か9）を推定する。
	 * 未ログインの表示は「ストアポイント＋LINE連携3%＋ボーナスストアPlus（要エントリー）」。
	 *
	 * @param array $row          parse_yahoo_products() の1行
	 * @param int   $store_points APIのストアポイント（同じ商品・同じ店）。不明なら0
	 * @param int   $price        税込価格。不明なら0（行の価格を使う）
	 */
	public static function bsp_rate_from_row( array $row, $store_points = 0, $price = 0, $addon_pct = 0.0 ) {
		if ( empty( $row['bsp'] ) ) {
			return 0.0;
		}
		// $addon_pct：その日の「ボーナスストアPlusでさらに+2%」「優良ストアでさらに+3%」など上乗せ分の合計。
		// 未ログインの表示に上乗せ分が含まれていると+4%の店が+9%に見えるので差し引く（2026/10/27 キャスティングで+4%を+9%と誤判定）。
		// 含まれていない場合は+9%の店を+4%と少なめに見ることになるが、買い時を出しすぎないほうを選ぶ
		$price = $price ? (int) $price : (int) $row['price'];
		if ( $price > 0 ) {
			$base  = intdiv( $price * 10, 11 );
			$store = $store_points ? (int) $store_points : (int) floor( $base * 0.01 );
			$rest  = (int) $row['pt'] - $store - (int) floor( $base * 0.03 );
			$est   = 100 * $rest / $base;
		} else {
			$est = (float) $row['pct'] - 4;
		}
		$est -= (float) $addon_pct;
		return $est >= 6.5 ? 9.0 : 4.0;
	}
}
