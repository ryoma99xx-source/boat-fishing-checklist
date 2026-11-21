<?php
/**
 * Plugin Name: Cutlassfish Gear Deals
 * Description: 楽天・Yahoo!の釣具（高額品）の実質価格を毎日記録し、「直近90日の実質最安＋ポイント3%以内」に入ったときだけバナー表示・SNS通知する。
 * Version: 0.9.12
 * Author: 3rd Penguin
 * Requires PHP: 8.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'CFGD_VERSION', '0.9.12' );
define( 'CFGD_DIR', plugin_dir_path( __FILE__ ) );
define( 'CFGD_URL', plugin_dir_url( __FILE__ ) );

require_once CFGD_DIR . 'includes/class-cfgd-settings.php';
require_once CFGD_DIR . 'includes/class-cfgd-db.php';
require_once CFGD_DIR . 'includes/class-cfgd-parsers.php';
require_once CFGD_DIR . 'includes/class-cfgd-judge.php';
require_once CFGD_DIR . 'includes/class-cfgd-fetch.php';
require_once CFGD_DIR . 'includes/class-cfgd-runner.php';
require_once CFGD_DIR . 'includes/class-cfgd-front.php';
require_once CFGD_DIR . 'includes/class-cfgd-admin.php';

register_activation_hook( __FILE__, function () {
	CFGD_DB::install();
	CFGD_DB::seed_rules();
	CFGD_Settings::ensure_token();
	if ( ! wp_next_scheduled( 'cfgd_run' ) ) {
		// 6:00 JST と 18:00 JST 前後に実行（twicedaily）。
		wp_schedule_event( strtotime( 'tomorrow 06:00:00 Asia/Tokyo' ), 'twicedaily', 'cfgd_run' );
	}
} );

register_deactivation_hook( __FILE__, function () {
	wp_clear_scheduled_hook( 'cfgd_run' );
	wp_clear_scheduled_hook( 'cfgd_run_continue' );
	wp_clear_scheduled_hook( 'cfgd_run_midnight' );
} );

add_action( 'plugins_loaded', function () {
	if ( get_option( 'cfgd_db_version' ) !== CFGD_VERSION ) {
		CFGD_DB::install();
		CFGD_DB::seed_rules(); // 追加された初期ルールだけ入る（既存は上書きしない）
		CFGD_Settings::ensure_token();
	}
} );

add_action( 'cfgd_run', array( 'CFGD_Runner', 'run' ) );
add_action( 'cfgd_run_continue', array( 'CFGD_Runner', 'continue_run' ) );
// Yahoo!のボーナスストアPlus・5のつく日などは0時に切り替わるので、6時・18時に加えて0時10分にも回す
add_action( 'cfgd_run_midnight', array( 'CFGD_Runner', 'run' ) );
add_action( 'init', function () {
	if ( ! wp_next_scheduled( 'cfgd_run_midnight' ) ) {
		wp_schedule_event( strtotime( 'tomorrow 00:10:00 Asia/Tokyo' ), 'daily', 'cfgd_run_midnight' );
	}
} );

CFGD_Front::init();
CFGD_Admin::init();

if ( defined( 'WP_CLI' ) && WP_CLI ) {
	/**
	 * wp cfgd run        … カレンダー取得 → 価格取得 → 判定 → 通知
	 * wp cfgd calendars  … カレンダーだけ取得
	 * wp cfgd judge      … 取得せず判定だけやり直す
	 */
	WP_CLI::add_command( 'cfgd', new class() {
		public function run() {
			$log = CFGD_Runner::run();
			WP_CLI::log( implode( "\n", (array) get_option( 'cfgd_last_log', $log ) ) );
		}
		public function calendars() {
			$log = CFGD_Runner::run_calendars();
			WP_CLI::log( implode( "\n", $log ) );
		}
		public function judge() {
			$log = CFGD_Runner::run_judge( false );
			WP_CLI::log( implode( "\n", $log ) );
		}
	} );
}
