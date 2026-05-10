/**
 * v2_sync.js
 * V2ウィザードの「実行」ボタン処理
 * 依存: v2_core_new.js, details_table.js, update_profit_preview.js
 */

(function () {
	if (window.__v2SyncLoaded) return;
	window.__v2SyncLoaded = true;

	/**
	 * プレビューカードの要素テキストを設定
	 */
	function _setText(id, v) {
		const el = document.getElementById(id);
		if (!el) return;
		el.textContent = (v === undefined || v === null || v === "") ? "-" : String(v);
	}

	/**
	 * 計算成功時のプレビュー表示
	 */
	function _renderOk(result) {
		const { designHours, setupHours, amounts, metrics } = result;

		_setText("sum_designHoursCeil", designHours);
		_setText("sum_designSell", Number(amounts.designSellAmount || 0).toLocaleString());
		_setText("sum_setupHoursCeil", setupHours);
		_setText("sum_setupSell", Number(amounts.setupSellAmount || 0).toLocaleString());

		// メトリクス表示
		_setText("sum_estimatedPatternScore", metrics.estimated_pattern_score.toFixed(2));
		_setText("sum_layoutScaleScore", metrics.layout_scale_score.toFixed(2));
		_setText("sum_landmarkFactor", metrics.landmark_factor.toFixed(2));
		_setText("sum_plcSignalCount", metrics.plc_signal_count);

		_setText("sum_missing", "-");
		const ngBlock = document.getElementById("v2_ng_reason_block");
		if (ngBlock) ngBlock.classList.add("d-none");
	}

	/**
	 * 計算失敗時のプレビュー表示
	 */
	function _renderNg(message) {
		_setText("sum_designHoursCeil", "-");
		_setText("sum_designSell", "-");
		_setText("sum_setupHoursCeil", "-");
		_setText("sum_setupSell", "-");
		_setText("sum_estimatedPatternScore", "-");
		_setText("sum_layoutScaleScore", "-");
		_setText("sum_landmarkFactor", "-");
		_setText("sum_plcSignalCount", "-");
		_setText("sum_missing", message || "-");
		const ngBlock = document.getElementById("v2_ng_reason_block");
		if (ngBlock) ngBlock.classList.remove("d-none");
	}

	/**
	 * V2推定を実行して、結果を反映する
	 */
	function runEstimateV2() {
		try {
			// v2_core_new.js のグローバル関数を直接呼び出す
			if (typeof readParamsV2FromWizard === "function") {
				const params = readParamsV2FromWizard();
				const metrics = deriveComplexityMetricsV2(params);
				const designHours = calcDesignHoursV2(params, metrics);
				const setupHours = calcSetupHoursV2(params, metrics);
				const amounts = convertAmountsV2(designHours, setupHours);

				const result = { params, metrics, designHours, setupHours, amounts };

				// V2実行時点の売価合計・原価合計を保持
				const v2SellTotal = Number(amounts.designSellAmount || 0) + Number(amounts.setupSellAmount || 0);
				const v2CostTotal = Number(amounts.designCostAmount || 0) + Number(amounts.setupCostAmount || 0);

				window.QUOTE_TOTALS = {
					sellBeforeDiscount: Math.round(v2SellTotal),
					costTotal: Math.round(v2CostTotal)
				};

				window.LAST_PROFIT_TOTALS = {
					sellBeforeDiscount: Math.round(v2SellTotal),
					costTotal: Math.round(v2CostTotal)
				};

				// デバッグ保持
				window.V2_LAST_RESULT = result;

				// プレビュー更新
				_renderOk(result);

				// 明細2行 upsert
				if (typeof upsertV2FixedRows === "function") {
					upsertV2FixedRows({
						designCostAmount: amounts.designCostAmount,
						designSellAmount: amounts.designSellAmount,
						setupCostAmount: amounts.setupCostAmount,
						setupSellAmount: amounts.setupSellAmount
					});
				}

				// 合計・利益更新
				if (typeof updateGrandTotal === "function") {
					updateGrandTotal();
				}
				if (typeof updateTotalProfitPreview === "function") {
					updateTotalProfitPreview({ applyDiscount: false });
				}
			} else {
				_renderNg("V2コア未ロード");
				console.error("[V2] v2_core_new.js が読み込まれていません");
			}
		} catch (e) {
			console.error("[V2] runEstimateV2 failed:", e);
			_renderNg("V2実行エラー(コンソール参照)");
		}
	}

	// export
	window.runEstimateV2 = runEstimateV2;

	// ボタンにバインド（複数回実行されないようにチェック）
	function bindButtonClick() {
		const btn = document.getElementById("v2_run");
		if (!btn) return;
		if (btn.__v2Bound) return;
		btn.__v2Bound = true;
		btn.addEventListener("click", () => runEstimateV2());
	}

	// ドキュメント準備完了後またはすぐに実行
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", bindButtonClick);
	} else {
		// DOMContentLoaded は既に発火済み、直接実行
		bindButtonClick();
	}
})();

	        document.getElementById('sum_designHoursCeil').textContent = '-';
	        document.getElementById('sum_designSell').textContent = '-';
	        document.getElementById('sum_setupHoursCeil').textContent = '-';
	        document.getElementById('sum_setupSell').textContent = '-';
	        document.getElementById('sum_missing').textContent = (missing && missing.length) ? missing.join(', ') : '-';
	        document.getElementById('sum_fixedRow1').textContent = '';
	        document.getElementById('sum_fixedRow2').textContent = '';
	    }

	    // --- export ---
	    window.__v2 = window.__v2 || {};
	    window.__v2.syncFromInputs = syncV2FromInputs;
	    window.initV2WizardBindings = initV2WizardBindings;
	    window.runEstimateV2 = runEstimateV2;
	})();
