<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class CFGD_Admin {

	const CAP  = 'manage_options';
	const SLUG = 'cfgd';

	public static function init() {
		add_action( 'admin_menu', function () {
			add_menu_page( '釣具の買い時', '釣具の買い時', self::CAP, self::SLUG, array( __CLASS__, 'page' ), 'dashicons-tag', 58 );
		} );
		foreach ( array( 'settings', 'products', 'campaign', 'campaign_status', 'coupon', 'coupon_delete', 'run', 'compare_check', 'store_scan', 'store_apply', 'token_reset' ) as $a ) {
			add_action( 'admin_post_cfgd_' . $a, array( __CLASS__, 'handle_' . $a ) );
		}
	}

	private static function url( $tab, $msg = '' ) {
		return add_query_arg( array_filter( array( 'page' => self::SLUG, 'tab' => $tab, 'msg' => $msg ) ), admin_url( 'admin.php' ) );
	}

	private static function guard( $action ) {
		if ( ! current_user_can( self::CAP ) ) {
			wp_die( '権限がありません' );
		}
		check_admin_referer( 'cfgd_' . $action );
	}

	private static function form_open( $action ) {
		echo '<form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">';
		echo '<input type="hidden" name="action" value="cfgd_' . esc_attr( $action ) . '">';
		wp_nonce_field( 'cfgd_' . $action );
	}

	public static function page() {
		$tab  = sanitize_key( $_GET['tab'] ?? 'status' ); // phpcs:ignore
		$tabs = array( 'status' => '状況', 'prices' => '今日の価格', 'products' => '商品', 'stores' => '店舗を探す', 'campaigns' => 'キャンペーン', 'coupons' => 'クーポン', 'settings' => '設定' );
		echo '<div class="wrap"><h1>釣具の買い時</h1><nav class="nav-tab-wrapper">';
		foreach ( $tabs as $k => $label ) {
			printf( '<a class="nav-tab %s" href="%s">%s</a>', $k === $tab ? 'nav-tab-active' : '', esc_url( self::url( $k ) ), esc_html( $label ) );
		}
		echo '</nav>';
		if ( ! empty( $_GET['msg'] ) ) { // phpcs:ignore
			echo '<div class="notice notice-success"><p>' . esc_html( sanitize_text_field( wp_unslash( $_GET['msg'] ) ) ) . '</p></div>'; // phpcs:ignore
		}
		$method = 'tab_' . $tab;
		if ( method_exists( __CLASS__, $method ) ) {
			self::$method();
		}
		echo '</div>';
	}

	/* ---------- 今日の価格 ---------- */

	/** 店舗コード → 店舗名（店舗を探すの結果から）。 */
	private static function store_names() {
		$names = array();
		foreach ( (array) ( get_option( 'cfgd_store_scan', array() )['matches'] ?? array() ) as $list ) {
			foreach ( (array) $list as $st ) {
				$names[ $st['mall'] . ':' . $st['code'] ] = $st['name'];
			}
		}
		return $names;
	}

	private static function tab_prices() {
		$s      = CFGD_Settings::all();
		$names  = self::store_names();
		$filter = sanitize_text_field( wp_unslash( $_GET['model'] ?? '' ) ); // phpcs:ignore
		$groups = array();
		foreach ( CFGD_DB::products_with_offers() as $p ) {
			$groups[ $p->model ][] = $p;
		}
		echo '<p>今日取得した価格を、品番ごとに<b>実質価格の安い順</b>で並べています。実質価格 ＝ 価格＋送料－クーポン－もらえるポイント。在庫なしは灰色で、判定には使いません。</p>';
		echo '<p>機種：';
		printf( '<a href="%s">%s</a>', esc_url( self::url( 'prices' ) ), '' === $filter ? '<b>すべて</b>' : 'すべて' );
		foreach ( array_keys( $groups ) as $m ) {
			$label = $m === $filter ? '<b>' . esc_html( $m ) . '</b>' : esc_html( $m );
			printf( ' ／ <a href="%s">%s</a>', esc_url( add_query_arg( 'model', rawurlencode( $m ), self::url( 'prices' ) ) ), $label ); // phpcs:ignore
		}
		echo '</p>';

		foreach ( $groups as $model => $products ) {
			if ( '' !== $filter && $model !== $filter ) {
				continue;
			}
			echo '<h2 style="margin-top:28px">' . esc_html( $model ) . '</h2>';
			foreach ( $products as $p ) {
				$rows = CFGD_DB::today_rows( $p->id );
				usort( $rows, fn( $a, $b ) => ( (int) $b->in_stock <=> (int) $a->in_stock ) ?: ( (int) $a->eff_price <=> (int) $b->eff_price ) );
				$hist = array_map( fn( $h ) => (int) $h->eff, CFGD_DB::daily_min_eff( $p->id, (int) $s['window_days'] ) );
				echo '<div class="card" style="max-width:720px;padding:10px 14px">';
				echo '<h3 style="margin:4px 0;display:flex;align-items:center;gap:10px">';
				if ( ! empty( $p->image_url ) ) {
					printf( '<img src="%s" alt="" width="56" height="56" style="object-fit:contain;background:#fff;border-radius:6px" referrerpolicy="no-referrer" loading="lazy">', esc_url( $p->image_url ) );
				}
				echo esc_html( $p->name ) . '</h3>';
				if ( ! $rows ) {
					echo '<p style="color:#888">今日の価格なし（取得中・どの店舗でも見つからない・JAN未確定のいずれか）</p></div>';
					continue;
				}
				$best      = $rows[0];
				$strong    = null;
				$min_total = 0;
				foreach ( $rows as $r ) {
					$t = (int) $r->price + (int) $r->shipping_yen;
					if ( $r->in_stock && ( ! $min_total || $t < $min_total ) ) {
						$min_total = $t;
					}
				}
				foreach ( $rows as $r ) {
					if ( ! $r->in_stock ) {
						continue;
					}
					$st = CFGD_Judge::strong( $r->mall, $r->store_code, (int) $r->price, (int) $r->coupon_yen, (int) $r->points_total, $s['strong_stores'], $s['strong_rate_pct'], (int) $s['strong_need_coupon'], (float) $s['strong_any_rate_pct'], array( 'total' => (int) $r->price + (int) $r->shipping_yen, 'min' => $min_total, 'over_pct' => (float) $s['strong_max_over_pct'] ) );
					if ( $st && $st['ok'] && ( ! $strong || $r->eff_price < $strong[0]->eff_price ) ) {
						$strong = array( $r, $st );
					}
				}
				if ( $best->in_stock ) {
					$v = CFGD_Judge::verdict( (int) $best->eff_price, (int) $best->price, $hist, (float) $s['tolerance_pct'], (int) $s['min_history_days'] );
					if ( ! $v['buy'] && $strong ) {
						$v['buy']    = true;
						$v['reason'] = self::store_label( $strong[0], $names ) . '：' . $strong[1]['reason'] . '（店舗の目安）';
					}
					printf(
						'<p style="margin:6px 0">最安：<b style="font-size:1.3em">%s円</b>（%s）<br><span style="color:%s">%s</span>%s</p>',
						number_format( (int) $best->eff_price ),
						esc_html( self::store_label( $best, $names ) ),
						$v['buy'] ? '#c00' : '#666',
						esc_html( $v['buy'] ? '★買い時：' . $v['reason'] : $v['reason'] ),
						null !== $v['min'] ? '<br><span style="color:#666">直近' . (int) $s['window_days'] . '日の実質最安：' . number_format( (int) $v['min'] ) . '円</span>' : ''
					);
				} else {
					echo '<p style="color:#888">在庫ありの店舗なし</p>';
				}
				echo '<table class="widefat striped" style="font-size:13px"><tbody>';
				foreach ( $rows as $r ) {
					$bd    = json_decode( (string) $r->breakdown, true );
					$lines = array_map(
						fn( $l ) => is_array( $l ) ? ( $l['label'] ?? '' ) . ' ' . number_format( (int) ( $l['yen'] ?? 0 ) ) . '円' : (string) $l,
						(array) ( $bd['lines'] ?? array() )
					);
					printf(
						'<tr style="%s"><td>%s<br><a href="%s" target="_blank" rel="noopener">商品ページ</a></td><td style="text-align:right;white-space:nowrap"><b>%s円</b><br><small>価格%s%s%s / %spt</small></td></tr>%s',
						$r->in_stock ? '' : 'opacity:.45',
						esc_html( self::store_label( $r, $names ) . ( $r->in_stock ? '' : '（在庫なし）' ) ),
						esc_url( $r->url ),
						number_format( (int) $r->eff_price ),
						number_format( (int) $r->price ),
						(int) $r->shipping_yen ? ' 送料' . number_format( (int) $r->shipping_yen ) : '',
						(int) $r->coupon_yen ? ' クーポン-' . number_format( (int) $r->coupon_yen ) : '',
						number_format( (int) $r->points_total ),
						$lines ? '<tr style="' . ( $r->in_stock ? '' : 'opacity:.45' ) . '"><td colspan="2"><small style="color:#666">' . esc_html( implode( ' / ', $lines ) ) . '</small></td></tr>' : ''
					);
				}
				echo '</tbody></table></div>';
			}
		}
	}

	private static function store_label( $r, $names ) {
		$k = $r->mall . ':' . $r->store_code;
		return ( 'rakuten' === $r->mall ? '楽天 ' : 'Yahoo! ' ) . ( $names[ $k ] ?? $r->store_code );
	}

	/* ---------- 状況 ---------- */

	private static function tab_status() {
		$deals = get_option( 'cfgd_deals', array() );
		echo '<h2>今日の買い時</h2>';
		if ( ! $deals ) {
			echo '<p>該当なし（バナーは表示されていません）</p>';
		}
		foreach ( $deals as $d ) {
			echo '<div class="card" style="max-width:720px"><h3>' . esc_html( $d['name'] ) . '</h3><pre style="white-space:pre-wrap">' . esc_html( CFGD_Runner::post_text( $d ) ) . '</pre></div>';
		}
		$prog = CFGD_Runner::progress();
		if ( $prog ) {
			echo '<div class="notice notice-info"><p><b>価格取得中：' . (int) $prog[0] . ' / ' . (int) $prog[1] . '件</b>　このページを開いている間は自動で進みます（閉じても30秒ごとに裏で続きます）。</p></div>';
			self::form_open( 'run' );
			echo '<input type="hidden" name="mode" value="continue"></form>';
			echo '<script>setTimeout(function(){var f=document.querySelectorAll("form input[name=mode][value=continue]");if(f.length){f[0].form.submit();}},3000);</script>';
		}
		self::compare_report();
		echo '<h2>直近の実行ログ</h2><pre style="background:#fff;padding:12px;max-height:420px;overflow:auto">' . esc_html( implode( "\n", (array) get_option( 'cfgd_last_log', array() ) ) ) . '</pre>';
		$next = min( array_filter( array( wp_next_scheduled( 'cfgd_run' ), wp_next_scheduled( 'cfgd_run_midnight' ) ) ) ?: array( 0 ) );
		echo '<p>次回の自動実行：' . esc_html( $next ? wp_date( 'Y-m-d H:i', $next ) : '未設定' ) . '</p>';
		self::form_open( 'run' );
		echo '<p><button class="button button-primary" name="mode" value="all">今すぐ全部実行</button> ';
		echo '<button class="button" name="mode" value="calendars">カレンダーだけ取得</button> ';
		echo '<button class="button" name="mode" value="judge">判定だけやり直す（通知なし）</button></p></form>';
	}

	public static function handle_compare_check() {
		self::guard( 'compare_check' );
		@set_time_limit( 300 ); // phpcs:ignore
		CFGD_Runner::compare_check();
		wp_safe_redirect( self::url( 'status', '価格比較ページを確認しました' ) . '#cfgd-compare' );
		exit;
	}

	private static function compare_report() {
		$c = get_option( 'cfgd_compare_check', array() );
		echo '<h2 id="cfgd-compare">Yahoo!価格比較ページの確認</h2>';
		echo '<p>機種ごとに、Yahoo!の価格比較ページが見つかるか、店ごとの「デイリーボーナスプラス」とポイントを読めるかを試します（判定には使いません。1〜2分かかります）。全部の機種で読めたら、設定の「価格比較ページでボーナスストアPlus対象店を判定」を1にしてください。</p>';
		self::form_open( 'compare_check' );
		submit_button( '価格比較ページを確認', 'secondary', 'submit', false );
		echo '</form>';
		if ( ! $c ) {
			return;
		}
		$ok = count( array_filter( $c['models'], fn( $m ) => ! $m['error'] ) );
		echo '<p><b>' . esc_html( $c['at'] ) . '：' . (int) $ok . ' / ' . count( $c['models'] ) . '機種で読めました</b></p>';
		echo '<table class="widefat striped" style="max-width:900px;font-size:13px"><thead><tr><th>機種</th><th>価格比較ページ</th><th>店数</th><th>ボーナスストアPlus（推定倍率）</th></tr></thead><tbody>';
		foreach ( $c['models'] as $model => $m ) {
			$bsp = array();
			foreach ( $m['rows'] as $store => $row ) {
				if ( $row['rate'] > 0 ) {
					$bsp[] = $store . ' +' . $row['rate'] . '%（表示' . $row['pct'] . '%）';
				}
			}
			printf(
				'<tr><td>%s<br><small>%s</small></td><td>%s</td><td>%s</td><td>%s</td></tr>',
				esc_html( $model ),
				esc_html( $m['product'] ),
				$m['id'] ? '<a href="' . esc_url( 'https://shopping.yahoo.co.jp/products/' . $m['id'] ) . '" target="_blank" rel="noopener">' . esc_html( $m['id'] ) . '</a>' : '—',
				$m['error'] ? '<span style="color:#c00">' . esc_html( $m['error'] ) . '</span>' : (int) count( $m['rows'] ),
				esc_html( $bsp ? implode( ' / ', $bsp ) : ( $m['error'] ? '' : 'なし' ) )
			);
		}
		echo '</tbody></table>';
	}

	public static function handle_run() {
		self::guard( 'run' );
		@set_time_limit( 600 ); // phpcs:ignore
		$mode = sanitize_key( $_POST['mode'] ?? 'all' ); // phpcs:ignore
		if ( 'calendars' === $mode ) {
			update_option( 'cfgd_last_log', CFGD_Runner::run_calendars(), false );
		} elseif ( 'judge' === $mode ) {
			update_option( 'cfgd_last_log', CFGD_Runner::run_judge( false ), false );
		} elseif ( 'continue' === $mode ) {
			CFGD_Runner::continue_run();
		} else {
			CFGD_Runner::run();
		}
		$prog = CFGD_Runner::progress();
		wp_safe_redirect( self::url( 'status', $prog ? "価格取得中（{$prog[0]} / {$prog[1]}件）" : '実行しました' ) );
		exit;
	}

	/* ---------- 商品・店舗 ---------- */

	private static function tab_products() {
		$lines = array();
		foreach ( CFGD_DB::products_with_offers() as $p ) {
			$jan     = $p->jan . ( $p->jan && $p->jan_auto ? '?' : '' );
			$lines[] = implode( ' | ', array( $p->model, $p->slug, $p->name, $jan, $p->keyword, $p->tags, $p->extra_stores ) );
		}
		echo '<p>1行1品番（右/左・ギア比・竿のタイプごとに1行）。</p>';
		echo '<p><code>機種 | スラッグ | 品番名 | JAN | 検索語 | タグ | 追加店舗</code></p>';
		echo '<ul style="list-style:disc;margin-left:20px">';
		echo '<li><b>機種</b>が同じ品番は、通知とバナーで1つにまとめます（「ほかに買い時：左ハンドル」など）。</li>';
		echo '<li><b>JAN</b>を空欄にすると、<b>検索語</b>でYahoo!を検索して自動で埋めます。自動で入ったJANは末尾に <code>?</code> が付くので、確認したら <code>?</code> を消して保存してください。</li>';
		echo '<li><b>検索語</b>は空白区切りで、すべて商品名に含まれるものだけを採用します。<code>!151</code> のように頭に!を付けると、その語を含むものを除外します。</li>';
		echo '<li><b>店舗</b>は「設定」の共通店舗を全品番で見ます。特定の品番だけ追加したい店舗は <code>rakuten:shopA,shopB=550;yahoo:storeC</code>。</li>';
		echo '<li>行を消すとその品番は停止します（価格履歴は残ります）。</li></ul>';
		self::form_open( 'products' );
		echo '<textarea name="lines" rows="30" style="width:100%;font-family:monospace;font-size:12px">' . esc_textarea( implode( "\n", $lines ) ) . '</textarea>';
		submit_button( '保存' );
		echo '</form>';
		self::afflink_checklist();
	}

	/** Yahoo!直営アフィリエイトの登録状況。未登録の商品ページをスマホで開いて「共有」→ショートカットで登録する。 */
	private static function afflink_checklist() {
		global $wpdb;
		$pt   = CFGD_DB::t( 'products' );
		$ot   = CFGD_DB::t( 'offers' );
		$at   = CFGD_DB::t( 'afflinks' );
		$rows = $wpdb->get_results( "SELECT p.name, o.store_code, o.item_code FROM $ot o JOIN $pt p ON p.id=o.product_id WHERE o.mall='yahoo' AND o.active=1 AND p.active=1 AND o.item_code<>'' AND o.miss_count=0 ORDER BY o.store_code, p.id" ); // phpcs:ignore
		$have = array();
		foreach ( $wpdb->get_results( "SELECT store_code, item_key FROM $at WHERE mall='yahoo'" ) as $a ) { // phpcs:ignore
			$have[ $a->store_code . '/' . $a->item_key ] = true;
		}
		echo '<h2>Yahoo!直営アフィリエイトのリンク</h2>';
		if ( ! $rows ) {
			echo '<p>初回の価格取得が終わると、ここにYahoo!の出品一覧が出ます。</p>';
			return;
		}
		$done = 0;
		$list = '';
		foreach ( $rows as $r ) {
			$key  = preg_replace( '/^[^_]+_/', '', $r->item_code );
			$ok   = isset( $have[ strtolower( $r->store_code ) . '/' . $key ] );
			$done += $ok ? 1 : 0;
			$page = 'https://store.shopping.yahoo.co.jp/' . $r->store_code . '/' . $key . '.html';
			$list .= sprintf( '<tr><td>%s</td><td>%s</td><td>%s</td></tr>', esc_html( $r->store_code ), esc_html( $r->name ), $ok ? '✓ 登録済み' : '<a href="' . esc_url( $page ) . '" target="_blank" rel="noopener">商品ページを開く</a>' );
		}
		printf( '<p>%d / %d 件登録済み。未登録の行の「商品ページを開く」をスマホで開き、アプリの「共有」で直営リンクを発行 → 「直営リンク登録」ショートカットに送ってください。未登録の出品は、バリューコマースのリンクで代わりに出します。</p>', (int) $done, count( $rows ) );
		echo '<table class="widefat striped" style="max-width:900px"><thead><tr><th>店舗</th><th>商品</th><th>直営リンク</th></tr></thead><tbody>' . $list . '</tbody></table>'; // phpcs:ignore
	}

	public static function handle_products() {
		global $wpdb;
		self::guard( 'products' );
		$pt    = CFGD_DB::t( 'products' );
		$lines = preg_split( '/\R/u', wp_unslash( $_POST['lines'] ?? '' ) ); // phpcs:ignore
		$keep  = array();
		$count = 0;

		foreach ( $lines as $line ) {
			if ( '' === trim( $line ) || str_starts_with( ltrim( $line ), '#' ) ) {
				continue;
			}
			$cols = array_pad( array_map( 'trim', explode( '|', $line ) ), 7, '' );
			if ( '' === $cols[1] || '' === $cols[2] ) {
				continue;
			}
			$slug = sanitize_title( $cols[1] );
			$jan  = preg_replace( '/\D/', '', $cols[3] );
			$row  = array(
				'model'        => sanitize_text_field( $cols[0] ),
				'slug'         => $slug,
				'name'         => sanitize_text_field( $cols[2] ),
				'jan'          => $jan,
				'jan_auto'     => ( $jan && str_ends_with( $cols[3], '?' ) ) ? 1 : 0,
				'keyword'      => sanitize_text_field( $cols[4] ),
				'tags'         => sanitize_text_field( $cols[5] ),
				'extra_stores' => sanitize_text_field( $cols[6] ),
				'active'       => 1,
			);
			$id = (int) $wpdb->get_var( $wpdb->prepare( "SELECT id FROM $pt WHERE slug=%s", $slug ) ); // phpcs:ignore
			if ( $id ) {
				$wpdb->update( $pt, $row, array( 'id' => $id ) );
			} else {
				$wpdb->insert( $pt, $row );
				$id = (int) $wpdb->insert_id;
			}
			$keep[] = $id;
			$count++;
		}
		if ( $keep ) {
			$wpdb->query( "UPDATE $pt SET active=0 WHERE id NOT IN (" . implode( ',', array_map( 'intval', $keep ) ) . ')' ); // phpcs:ignore
		} else {
			$wpdb->query( "UPDATE $pt SET active=0" ); // phpcs:ignore
		}
		CFGD_DB::sync_offers();
		wp_safe_redirect( self::url( 'products', "{$count}品番を保存しました" ) );
		exit;
	}

	/* ---------- 店舗を探す ---------- */

	const STORE_NAMES = "キャスティング|casting\nかめや\nマルニシ\n釣具のポイント\nポイント東日本\nJoshin|ジョーシン\nブンブン\nナチュラム\nFTO|フィッシングタックルオンライン\nまるきん\nアングル\nフィッシング遊";

	private static function tab_stores() {
		$names = get_option( 'cfgd_store_names', self::STORE_NAMES );
		$scan  = get_option( 'cfgd_store_scan', array() );
		echo '<p>登録済みのJAN（機種ごとに1品番、最大8機種）で楽天・Yahoo!を検索し、実際に売っている店舗の名前とコードを集めます。探したい店舗は1行1店舗、別名は <code>|</code> で区切ります。</p>';
		self::form_open( 'store_scan' );
		echo '<textarea name="names" rows="10" style="width:420px">' . esc_textarea( $names ) . '</textarea>';
		submit_button( '店舗を探す（1分ほどかかります）', 'secondary' );
		echo '</form>';
		if ( ! $scan ) {
			return;
		}

		$current = array(
			'rakuten' => CFGD_Settings::stores( 'rakuten' ),
			'yahoo'   => CFGD_Settings::stores( 'yahoo' ),
		);
		if ( ! empty( $scan['rakuten_error'] ) ) {
			echo '<div class="notice notice-error"><p><b>楽天APIエラー：</b>' . esc_html( $scan['rakuten_error'] ) . '<br>送信元URL（Referer）：' . esc_html( home_url( '/' ) ) . '</p></div>';
		}
		if ( ! empty( $scan['rakuten_log'] ) ) {
			echo '<p><b>楽天の検索件数：</b><br>' . implode( '<br>', array_map( 'esc_html', $scan['rakuten_log'] ) ) . '</p>';
		}
		echo '<h2>結果（' . esc_html( $scan['at'] ?? '' ) . '・JAN ' . esc_html( implode( ', ', $scan['jans'] ?? array() ) ) . '）</h2>';
		echo '<p>同じ会社でもモールごとに複数店舗あることがあります。見たい店舗にチェックを入れて「共通店舗に設定」を押すと、設定の共通店舗が<b>置き換わります</b>。数字は検索でヒットした回数です。</p>';
		self::form_open( 'store_apply' );
		echo '<table class="widefat striped" style="max-width:900px"><thead><tr><th>探した店舗</th><th></th><th>モール</th><th>コード</th><th>店舗名</th><th>件数</th></tr></thead><tbody>';
		foreach ( $scan['matches'] as $label => $list ) {
			if ( ! $list ) {
				printf( '<tr><td>%s</td><td colspan="5"><em>見つからず（その店舗がこのJANを扱っていないか、名前が違う）</em></td></tr>', esc_html( $label ) );
				continue;
			}
			$first = true;
			foreach ( $list as $k => $s ) {
				$checked = isset( $current[ $s['mall'] ][ $s['code'] ] ) || ( ! $current['rakuten'] && ! $current['yahoo'] );
				printf(
					'<tr><td>%s</td><td><input type="checkbox" name="pick[]" value="%s"%s></td><td>%s</td><td><code>%s</code></td><td>%s</td><td>%d</td></tr>',
					$first ? esc_html( $label ) : '',
					esc_attr( $k ),
					checked( $checked, true, false ),
					'rakuten' === $s['mall'] ? '楽天' : 'Yahoo!',
					esc_html( $s['code'] ),
					esc_html( $s['name'] ),
					(int) $s['hits']
				);
				$first = false;
			}
		}
		echo '</tbody></table>';
		submit_button( '共通店舗に設定' );
		echo '</form>';
	}

	public static function handle_store_scan() {
		global $wpdb;
		self::guard( 'store_scan' );
		@set_time_limit( 300 ); // phpcs:ignore
		$names = sanitize_textarea_field( wp_unslash( $_POST['names'] ?? '' ) ); // phpcs:ignore
		update_option( 'cfgd_store_names', $names, false );

		$pt   = CFGD_DB::t( 'products' );
		$rows = $wpdb->get_results( "SELECT model, jan, name, keyword FROM $pt WHERE active=1 AND jan<>'' ORDER BY jan_auto ASC, id ASC" ); // phpcs:ignore
		// 機種ごとに1品番ずつ、最大8機種（同じ機種ばかりだと、新製品を扱わない店舗が漏れる）
		$picked = array();
		foreach ( $rows as $r ) {
			if ( ! isset( $picked[ $r->model ] ) && count( $picked ) < 8 ) {
				$picked[ $r->model ] = $r;
			}
		}
		if ( ! $picked ) {
			wp_safe_redirect( self::url( 'stores', '先に「商品」でJANのある品番を登録してください' ) );
			exit;
		}
		$jans    = array();
		$sellers = array();
		foreach ( $picked as $r ) {
			$jans[]   = $r->jan;
			$fallback = implode( ' ', array_filter( preg_split( '/\s+/u', CFGD_Parsers::name_keyword( $r ) ), fn( $t ) => '' !== $t && ! str_starts_with( $t, '!' ) ) );
			$sellers  = array_merge( $sellers, CFGD_Fetch::sellers_for_jan( $r->jan, $fallback ) );
		}
		update_option( 'cfgd_store_scan', array(
			'at'      => wp_date( 'Y-m-d H:i' ),
			'jans'    => $jans,
			'matches' => CFGD_Parsers::match_sellers( $sellers, preg_split( '/\R/u', $names ) ),
			'rakuten_error' => CFGD_Fetch::$rakuten_error,
			'rakuten_log'   => CFGD_Fetch::$rakuten_log,
		), false );
		wp_safe_redirect( self::url( 'stores', count( $sellers ) . '件の出品から店舗を集めました' ) );
		exit;
	}

	public static function handle_store_apply() {
		self::guard( 'store_apply' );
		$picks = array_map( 'sanitize_text_field', (array) wp_unslash( $_POST['pick'] ?? array() ) ); // phpcs:ignore
		$cur   = array(
			'rakuten' => CFGD_Settings::stores( 'rakuten' ),
			'yahoo'   => CFGD_Settings::stores( 'yahoo' ),
		);
		$new   = array( 'rakuten' => array(), 'yahoo' => array() );
		foreach ( $picks as $p ) {
			list( $mall, $code ) = array_pad( explode( ':', $p, 2 ), 2, '' );
			if ( isset( $new[ $mall ] ) && '' !== $code ) {
				$ship               = $cur[ $mall ][ $code ] ?? 0; // 送料の設定は引き継ぐ
				$new[ $mall ][]     = $code . ( $ship ? '=' . $ship : '' );
			}
		}
		$new['rakuten']        = array_values( array_unique( $new['rakuten'] ) );
		$new['yahoo']          = array_values( array_unique( $new['yahoo'] ) );
		$all                   = get_option( CFGD_Settings::OPTION, array() );
		$all['stores_rakuten'] = implode( ',', $new['rakuten'] );
		$all['stores_yahoo']   = implode( ',', $new['yahoo'] );
		update_option( CFGD_Settings::OPTION, $all, false );
		CFGD_DB::sync_offers();
		wp_safe_redirect( self::url( 'stores', '楽天' . count( $new['rakuten'] ) . '店・Yahoo!' . count( $new['yahoo'] ) . '店を共通店舗にしました' ) );
		exit;
	}

	/* ---------- キャンペーン ---------- */

	private static function tab_campaigns() {
		global $wpdb;
		$t    = CFGD_DB::t( 'campaigns' );
		$rows = $wpdb->get_results( $wpdb->prepare( "SELECT * FROM $t WHERE recur<>'' OR end_at >= %s ORDER BY mall, (recur='') , start_at", wp_date( 'Y-m-d 00:00:00' ) ) ); // phpcs:ignore
		$labels = array( 'confirmed' => '計算に使う', 'hint' => '予想', 'info' => '情報のみ', 'disabled' => '無効' );

		echo '<p>「予想」は楽天カレンダー（ユーザー投稿）から拾った日程です。告知を確認したら倍率と上限を入れて「確定」にしてください。手で直した行はメモに <code>[固定]</code> が付き、自動取得で上書きされません。</p>';
		echo '<table class="widefat striped"><thead><tr><th>モール</th><th>名前</th><th>期間／繰り返し</th><th>倍率%</th><th>上限円</th><th>範囲</th><th>状態</th><th>出どころ・メモ</th><th></th></tr></thead><tbody>';
		foreach ( $rows as $r ) {
			$when = $r->recur ? '毎月 ' . $r->recur : substr( $r->start_at, 5, 11 ) . '〜' . substr( $r->end_at, 5, 11 );
			echo '<tr>';
			self::form_open( 'campaign_status' );
			printf( '<input type="hidden" name="id" value="%d">', (int) $r->id );
			printf( '<td>%s</td><td>%s<br><small>%s</small></td><td>%s</td>', esc_html( $r->mall ), esc_html( $r->name ), esc_html( $r->conditions ), esc_html( $when ) );
			printf( '<td><input name="rate_pct" value="%s" size="4"></td><td><input name="cap_yen" value="%d" size="6"></td>', esc_attr( $r->rate_pct ?? '' ), (int) $r->cap_yen );
			printf( '<td><input name="stores" value="%s" size="10" placeholder="%s"></td>', esc_attr( $r->stores ), 'limited' === $r->scope ? '対象ストア' : '全店' );
			echo '<td><select name="status">';
			foreach ( $labels as $k => $l ) {
				printf( '<option value="%s"%s>%s</option>', esc_attr( $k ), selected( $r->status, $k, false ), esc_html( $l ) );
			}
			echo '</select></td>';
			printf( '<td><small>%s %s</small></td><td><button class="button">更新</button></td>', esc_html( $r->source ), esc_html( $r->note ) );
			echo '</form></tr>';
		}
		echo '</tbody></table>';

		echo '<h2>手動で追加</h2>';
		self::form_open( 'campaign' );
		echo '<table class="form-table">';
		echo '<tr><th>モール</th><td><select name="mall"><option value="rakuten">楽天</option><option value="yahoo">Yahoo!</option></select></td></tr>';
		echo '<tr><th>名前</th><td><input name="name" class="regular-text" placeholder="お買い物マラソン（5店舗想定）"></td></tr>';
		echo '<tr><th>開始・終了</th><td><input type="datetime-local" name="start_at"> 〜 <input type="datetime-local" name="end_at"></td></tr>';
		echo '<tr><th>または毎月の日付</th><td><input name="recur" placeholder="5,10,15 / * / sun"> <small>入れると開始・終了は無視</small></td></tr>';
		echo '<tr><th>倍率%・上限円</th><td><input name="rate_pct" size="5"> % ／ 上限 <input name="cap_yen" size="7"> 円</td></tr>';
		echo '<tr><th>対象ストア</th><td><input name="stores" placeholder="空欄＝全店"></td></tr>';
		echo '</table>';
		submit_button( '追加' );
		echo '</form>';
	}

	public static function handle_campaign() {
		self::guard( 'campaign' );
		$p      = wp_unslash( $_POST ); // phpcs:ignore
		$stores = sanitize_text_field( $p['stores'] ?? '' );
		CFGD_DB::upsert_campaign( array(
			'mall'     => 'yahoo' === $p['mall'] ? 'yahoo' : 'rakuten',
			'name'     => sanitize_text_field( $p['name'] ),
			'start_at' => $p['recur'] ? null : self::dt( $p['start_at'] ),
			'end_at'   => $p['recur'] ? null : self::dt( $p['end_at'] ),
			'recur'    => sanitize_text_field( $p['recur'] ),
			'rate_pct' => '' === $p['rate_pct'] ? null : (float) $p['rate_pct'],
			'cap_yen'  => (int) $p['cap_yen'],
			'stores'   => $stores,
			'scope'    => $stores ? 'limited' : 'all',
			'status'   => 'confirmed',
			'source'   => 'manual',
			'note'     => '[固定]',
		) );
		wp_safe_redirect( self::url( 'campaigns', '追加しました' ) );
		exit;
	}

	public static function handle_campaign_status() {
		global $wpdb;
		self::guard( 'campaign_status' );
		$p   = wp_unslash( $_POST ); // phpcs:ignore
		$id  = (int) $p['id'];
		$t   = CFGD_DB::t( 'campaigns' );
		$old = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM $t WHERE id=%d", $id ) ); // phpcs:ignore
		if ( $old ) {
			$stores = sanitize_text_field( $p['stores'] ?? '' );
			$wpdb->update( $t, array(
				'rate_pct'   => '' === $p['rate_pct'] ? null : (float) $p['rate_pct'],
				'cap_yen'    => (int) $p['cap_yen'],
				'stores'     => $stores,
				'scope'      => ( $stores || 'limited' === $old->scope ) ? 'limited' : 'all',
				'status'     => sanitize_key( $p['status'] ),
				'note'       => str_contains( $old->note, '[固定]' ) ? $old->note : trim( '[固定] ' . $old->note ),
				'updated_at' => current_time( 'mysql' ),
			), array( 'id' => $id ) );
		}
		wp_safe_redirect( self::url( 'campaigns', '更新しました' ) );
		exit;
	}

	/* ---------- クーポン ---------- */

	private static function tab_coupons() {
		global $wpdb;
		$t    = CFGD_DB::t( 'coupons' );
		$rows = $wpdb->get_results( $wpdb->prepare( "SELECT * FROM $t WHERE end_at >= %s ORDER BY end_at", wp_date( 'Y-m-d H:i:s', time() - 7 * DAY_IN_SECONDS ) ) ); // phpcs:ignore
		echo '<p>全員が取得できるストアクーポンだけを登録してください（対象者限定クーポンは載せない）。</p>';
		echo '<table class="widefat striped"><thead><tr><th>モール</th><th>店舗</th><th>割引</th><th>上限</th><th>最低金額</th><th>期間</th><th>メモ</th><th></th></tr></thead><tbody>';
		foreach ( $rows as $r ) {
			$off = $r->yen ? number_format( $r->yen ) . '円' : rtrim( rtrim( $r->pct, '0' ), '.' ) . '%';
			echo '<tr>';
			printf( '<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s〜%s</td><td>%s</td><td>', esc_html( $r->mall ), esc_html( $r->store_code ), esc_html( $off ), esc_html( number_format( $r->cap_yen ) ), esc_html( number_format( $r->min_order ) ), esc_html( substr( $r->start_at, 5, 11 ) ), esc_html( substr( $r->end_at, 5, 11 ) ), esc_html( $r->note ) );
			self::form_open( 'coupon_delete' );
			printf( '<input type="hidden" name="id" value="%d"><button class="button-link-delete">削除</button></form></td></tr>', (int) $r->id );
		}
		echo '</tbody></table><h2>追加</h2>';
		self::form_open( 'coupon' );
		echo '<table class="form-table">';
		echo '<tr><th>モール・店舗</th><td><select name="mall"><option value="yahoo">Yahoo!</option><option value="rakuten">楽天</option></select> <input name="store_code" placeholder="casting"></td></tr>';
		echo '<tr><th>割引</th><td><input name="pct" size="4"> % または <input name="yen" size="6"> 円 ／ 上限 <input name="cap_yen" size="6"> 円 ／ 最低 <input name="min_order" size="7"> 円以上</td></tr>';
		echo '<tr><th>期間</th><td><input type="datetime-local" name="start_at"> 〜 <input type="datetime-local" name="end_at"></td></tr>';
		echo '<tr><th>メモ</th><td><input name="note" class="regular-text" placeholder="先着・LINE告知など"></td></tr>';
		echo '</table>';
		submit_button( '追加' );
		echo '</form>';
	}

	public static function handle_coupon() {
		global $wpdb;
		self::guard( 'coupon' );
		$p = wp_unslash( $_POST ); // phpcs:ignore
		$wpdb->insert( CFGD_DB::t( 'coupons' ), array(
			'mall'       => 'rakuten' === $p['mall'] ? 'rakuten' : 'yahoo',
			'store_code' => sanitize_text_field( $p['store_code'] ),
			'pct'        => (float) $p['pct'],
			'yen'        => (int) $p['yen'],
			'cap_yen'    => (int) $p['cap_yen'],
			'min_order'  => (int) $p['min_order'],
			'start_at'   => self::dt( $p['start_at'] ),
			'end_at'     => self::dt( $p['end_at'] ),
			'note'       => sanitize_text_field( $p['note'] ),
		) );
		wp_safe_redirect( self::url( 'coupons', '追加しました' ) );
		exit;
	}

	public static function handle_coupon_delete() {
		global $wpdb;
		self::guard( 'coupon_delete' );
		$wpdb->delete( CFGD_DB::t( 'coupons' ), array( 'id' => (int) $_POST['id'] ) ); // phpcs:ignore
		wp_safe_redirect( self::url( 'coupons', '削除しました' ) );
		exit;
	}

	/* ---------- 設定 ---------- */

	private static function tab_settings() {
		$s      = CFGD_Settings::all();
		$fields = array(
			'楽天'     => array(
				'rakuten_app_id'       => 'アプリID（UUID）',
				'rakuten_access_key'   => 'アクセスキー（pk_〜）',
				'rakuten_affiliate_id' => 'アフィリエイトID',
				'rakuten_shop_pages'   => '店舗トップからショップ倍率・クーポン・3商品企画を読む（1/0）',
				'count_unverified_coupons' => '店舗トップのクーポン（条件未確認）も計算に入れる（1/0）',
			),
			'Yahoo!'  => array(
				'yahoo_appid'        => 'Client ID',
				'yahoo_vc_affiliate' => 'バリューコマース アフィリエイトID',
				'yahoo_premium'      => 'LYPプレミアム会員前提で計算（1/0）',
				'yahoo_compare'      => '価格比較ページでボーナスストアPlus対象店を判定（1/0。状況タブで確認してから1に）',
				'bsp_unlisted_rate'  => 'ボーナスストアPlus：一覧にないがバッジのある店舗の倍率（%）',
				'yahoo_limited_map'  => '「対象ストア限定」施策を有効にする店舗（1行1施策：施策名の一部: storeId,storeId）',
			),
			'共通店舗'   => array(
				'stores_rakuten'    => '楽天ショップコード（カンマ区切り、送料別は code=550）',
				'stores_yahoo'      => 'Yahoo!ストアID（同上）',
				'miss_skip_after'   => '連続で見つからない店舗を休止するまでの回数',
				'miss_recheck_days' => '休止中の店舗を確認し直す間隔（日）',
			),
			'判定'     => array(
				'tolerance_pct'       => '許容差（本体価格の%＝ポイント何%分）',
				'strong_stores'       => '店舗の目安：対象店舗（mall:コード、カンマ区切り）',
				'strong_rate_pct'     => '店舗の目安：ポイント還元がこの%以上なら買い時',
				'strong_need_coupon'  => '店舗の目安：クーポンありも条件にする（1/0）',
				'strong_any_rate_pct' => 'どの店でも：Yahoo!のポイント還元がこの%以上なら買い時（クーポン不要・0で無効）',
				'strong_max_over_pct' => '店舗の目安・どの店でも共通：値付け（価格＋送料）が最安店よりこの%を超えて高い店は除く（0で無効）',
				'window_days'         => '比較する日数',
				'min_history_days'    => '判定を始める最低記録日数',
				'yahoo_total_cap_pct' => 'Yahoo!合計付与率の上限%',
			),
			'カレンダー'  => array(
				'yahoo_calendar_url'   => 'Yahoo!ボーナスカレンダーURL',
				'rakuten_calendar_url' => '楽天カレンダーURL',
			),
			'通知・表示' => array(
				'notify_email'    => '通知メール',
				'cooldown_days'   => '同じ商品を再通知しない日数',
				'sns_daily_limit' => 'SNS投稿の1日上限',
				'banner_enabled'  => 'バナーを表示（1/0）',
				'guide_url'       => '攻略ページのURL（公開後に入れる。空ならバナーの「買い方を見る」とSNSのURLを出さない）',
			),
			'スマホからクーポン登録' => array(
				'quick_token' => '合言葉（ショートカットのヘッダー X-CFGD-Token に入れる）',
			),
		);
		self::form_open( 'settings' );
		foreach ( $fields as $group => $list ) {
			echo '<h2>' . esc_html( $group ) . '</h2><table class="form-table">';
			foreach ( $list as $k => $label ) {
				echo '<tr><th>' . esc_html( $label ) . '</th><td>';
				if ( 'yahoo_limited_map' === $k ) {
					printf( '<textarea name="%s" rows="4" class="large-text code" placeholder="プレミアムな日曜日: casting, point-i">%s</textarea>', esc_attr( $k ), esc_textarea( $s[ $k ] ) );
				} else {
					$type = str_contains( $k, 'key' ) ? 'password' : 'text';
					$ro   = 'quick_token' === $k ? ' readonly onclick="this.select()"' : '';
					printf( '<input type="%s" name="%s" value="%s" class="regular-text code" autocomplete="off"%s>', esc_attr( $type ), esc_attr( $k ), esc_attr( $s[ $k ] ), $ro ); // phpcs:ignore
					if ( 'quick_token' === $k ) {
						echo '<p class="description">送り先URL：<code>' . esc_html( rest_url( 'cfgd/v1/coupon' ) ) . '</code></p>';
					}
				}
				echo '</td></tr>';
			}
			echo '</table>';
		}
		echo '<p>楽天の新APIは、アプリに登録した「WebサイトURL」とこのサイトのURL（' . esc_html( home_url( '/' ) ) . '）が一致している必要があります。</p>';
		submit_button( '保存' );
		echo '</form>';
		self::form_open( 'token_reset' );
		echo '<p><button class="button" onclick="return confirm(\'合言葉を作り直すと、今のショートカットは使えなくなります。よろしいですか？\')">合言葉を作り直す</button></p></form>';
	}

	public static function handle_token_reset() {
		self::guard( 'token_reset' );
		CFGD_Settings::ensure_token( true );
		wp_safe_redirect( self::url( 'settings', '合言葉を作り直しました。ショートカットの X-CFGD-Token も差し替えてください' ) );
		exit;
	}

	public static function handle_settings() {
		self::guard( 'settings' );
		$in  = wp_unslash( $_POST ); // phpcs:ignore
		$out = array();
		foreach ( CFGD_Settings::defaults() as $k => $def ) {
			if ( ! isset( $in[ $k ] ) ) {
				continue;
			}
			$out[ $k ] = 'yahoo_limited_map' === $k ? sanitize_textarea_field( $in[ $k ] ) : sanitize_text_field( $in[ $k ] );
		}
		update_option( CFGD_Settings::OPTION, $out, false );
		CFGD_DB::sync_offers();
		wp_safe_redirect( self::url( 'settings', '保存しました' ) );
		exit;
	}

	private static function dt( $v ) {
		$v = sanitize_text_field( (string) $v );
		if ( ! $v ) {
			return null;
		}
		$ts = strtotime( $v );
		return $ts ? gmdate( 'Y-m-d H:i:s', $ts ) : null; // datetime-local はタイムゾーンなしなのでそのまま
	}
}
