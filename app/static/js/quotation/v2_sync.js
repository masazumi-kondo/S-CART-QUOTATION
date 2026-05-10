/**
 * v2_sync.js - V2ウィザード実行処理
 * 
 * 責務：
 * 1. V2計算エンジン(v2_core_new.js)の呼び出し
 * 2. プレビューカードのDOM更新
 * 3. 明細固定行の追加/更新 (details_table.js)
 * 4. 合計・利益の再計算 (update_profit_preview.js)
 * 
 * 依存: v2_core_new.js, details_table.js, update_profit_preview.js
 */

(function () {
	"use strict";

	// 多重ロード防止
	if (window.__v2SyncLoaded) return;
	window.__v2SyncLoaded = true;

	// ============================================
	// DOM更新ユーティリティ
	// ============================================

	/**
	 * @param {string} id - 要素ID
	 * @param {*} value - 設定値
	 */
	function setText(id, value) {
		const el = document.getElementById(id);
		if (!el) {
			console.warn("[v2_sync] missing element:", id);
			return;
		}
		const text = value == null ? "-" : String(value);
		el.textContent = text;
	}

	/**
	 * 数値を ¥ 記号付きで表示
	 */
	function formatYen(v) {
		const n = Number(v || 0);
		return Math.round(n).toLocaleString("ja-JP");
	}

	/**
	 * 工数を時間表記で表示 (h)
	 */
	function formatHours(v) {
		const n = Number(v || 0);
		return n.toLocaleString("ja-JP", { maximumFractionDigits: 1 });
	}

	/**
	 * 数値をロケール形式で表示
	 */
	function formatNumber(v) {
		const n = Number(v || 0);
		return n.toLocaleString("ja-JP", { maximumFractionDigits: 2 });
	}

	// ============================================
	// プレビューカード更新
	// ============================================

	/**
	 * V2計算結果をプレビューカードに反映
	 * @param {Object} result - runEstimateV2の戻り値
	 */
	function renderV2Result(result) {
		if (!result) return;

		const { designHours, setupHours, amounts, metrics } = result;

		// 工数表示
		setText("sum_designHoursCeil", formatHours(designHours));
		setText("sum_setupHoursCeil", formatHours(setupHours));

		// 金額表示
		setText("sum_designSell", formatYen(amounts?.designSellAmount));
		setText("sum_setupSell", formatYen(amounts?.setupSellAmount));

		// メトリクス表示
		setText("sum_estimatedPatternScore", formatNumber(metrics?.estimated_pattern_score));
		setText("sum_layoutScaleScore", formatNumber(metrics?.layout_scale_score));
		setText("sum_landmarkFactor", formatNumber(metrics?.landmark_factor));
		setText("sum_plcSignalCount", formatNumber(metrics?.plc_signal_count));

		// エラーブロック隠す
		const ngBlock = document.getElementById("v2_ng_reason_block");
		if (ngBlock) ngBlock.classList.add("d-none");
	}

	/**
	 * エラー表示
	 */
	function renderV2Error(message) {
		setText("sum_designHoursCeil", "-");
		setText("sum_setupHoursCeil", "-");
		setText("sum_designSell", "-");
		setText("sum_setupSell", "-");
		setText("sum_estimatedPatternScore", "-");
		setText("sum_layoutScaleScore", "-");
		setText("sum_landmarkFactor", "-");
		setText("sum_plcSignalCount", "-");
		setText("sum_missing", message || "エラー");

		const ngBlock = document.getElementById("v2_ng_reason_block");
		if (ngBlock) ngBlock.classList.remove("d-none");
	}

	// ============================================
	// メイン実行関数
	// ============================================

	/**
	 * V2推定を実行
	 * 
	 * 処理フロー：
	 * 1. V2ウィザード入力から params を読む
	 * 2. params をバリデーション
	 * 3. metrics を計算
	 * 4. designHours, setupHours を計算
	 * 5. amounts (金額) を計算
	 * 6. result オブジェクトを作成 → window.V2_LAST_RESULT へ保存
	 * 7. プレビューカードを更新
	 * 8. 明細固定行を追加/更新
	 * 9. 合計・利益を再計算
	 */
	function runEstimateV2() {
		console.log("[v2_sync] runEstimateV2 started");
		
		try {
			// ---- 計算エンジン確認 ----
			if (typeof readParamsV2FromWizard !== "function") {
				console.error("[v2_sync] readParamsV2FromWizard not found");
				renderV2Error("V2エンジン未ロード");
				return;
			}

			// ---- Step 1: パラメータ読み取り ----
			console.log("[v2_sync] Step 1: Reading params");
			const params = readParamsV2FromWizard();
			console.log("[v2_sync] params:", params);

			// ---- Step 2: バリデーション (オプション) ----
			if (typeof validateEstimateV2 === "function") {
				const validation = validateEstimateV2(params);
				if (validation.isValid === false) {
					console.warn("[v2_sync] validation failed:", validation);
					renderV2Error(validation.message || "入力エラー");
					return;
				}
			}

			// ---- Step 3-5: メトリクス・工数・金額計算 ----
			console.log("[v2_sync] Step 3: Calculating metrics");
			const metrics = deriveComplexityMetricsV2(params);
			console.log("[v2_sync] metrics:", metrics);
			
			console.log("[v2_sync] Step 4: Calculating design hours");
			const designHours = calcDesignHoursV2(params, metrics);
			console.log("[v2_sync] designHours:", designHours);
			
			console.log("[v2_sync] Step 5: Calculating setup hours");
			const setupHours = calcSetupHoursV2(params, metrics);
			console.log("[v2_sync] setupHours:", setupHours);
			
			console.log("[v2_sync] Step 6: Converting to amounts");
			const amounts = convertAmountsV2(designHours, setupHours);
			console.log("[v2_sync] amounts:", amounts);

			// ---- Step 6: Result オブジェクト作成 ----
			console.log("[v2_sync] Step 7: Creating result object");
			const result = {
				params,
				metrics,
				designHours,
				setupHours,
				amounts
			};

			// グローバルに保存（デバッグ・確認用）
			window.V2_LAST_RESULT = result;
			console.log("[v2_sync] V2_LAST_RESULT saved");

			// ---- Step 7: プレビューカード更新 ----
			console.log("[v2_sync] Step 8: Rendering preview");
			renderV2Result(result);
			console.log("[v2_sync] Preview rendered");

			// ---- Step 8: 明細固定行を追加/更新 ----
			console.log("[v2_sync] Step 9: Upserting fixed rows");
			const designSell = Number(amounts?.designSellAmount || 0);
			const designCost = Number(amounts?.designCostAmount || 0);
			const setupSell = Number(amounts?.setupSellAmount || 0);
			const setupCost = Number(amounts?.setupCostAmount || 0);

			if (typeof window.upsertV2FixedRows === "function") {
				window.upsertV2FixedRows({
					designSellAmount: designSell,
					designCostAmount: designCost,
					setupSellAmount: setupSell,
					setupCostAmount: setupCost
				});
				console.log("[v2_sync] upsertV2FixedRows called");
			} else {
				console.warn("[v2_sync] upsertV2FixedRows not found");
			}

			// ---- Step 9: 合計・利益更新 ----
			console.log("[v2_sync] Step 10: Updating totals");
			if (typeof window.updateGrandTotal === "function") {
				window.updateGrandTotal();
				console.log("[v2_sync] updateGrandTotal called");
			}

			if (typeof window.updateTotalProfitPreview === "function") {
				window.updateTotalProfitPreview({ applyDiscount: false });
				console.log("[v2_sync] updateTotalProfitPreview called");
			}

			console.log("[v2_sync] V2 estimate completed successfully");

		} catch (e) {
			console.error("[v2_sync] runEstimateV2 exception:", e);
			renderV2Error("実行エラー (コンソール参照)");
		}
	}

	// ============================================
	// グローバル登録
	// ============================================

	window.runEstimateV2 = runEstimateV2;

	// ============================================
	// イベントバインド
	// ============================================

	function setupButtonHandler() {
		const btn = document.getElementById("v2_run");
		if (!btn) {
			console.warn("[v2_sync] v2_run button not found");
			return;
		}

		// 多重バインド防止
		if (btn.__v2Bound) return;
		btn.__v2Bound = true;

		btn.addEventListener("click", function (e) {
			e.preventDefault();
			console.log("[v2_sync] v2_run clicked");
			runEstimateV2();
		});

		console.log("[v2_sync] button bound to v2_run");
	}

	// DOMContentLoaded または即座に実行
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", setupButtonHandler);
	} else {
		setupButtonHandler();
	}

})();

