// app/static/js/quotation/v2_sync.js
// V2同期: 実行ボタン→ v2_core の計算 → プレビュー反映 → 明細2行upsert → 合計/利益更新
// 依存: v2_core.js, details_table.js, update_profit_preview.js

(function () {
	if (window.__v2SyncLoaded) return;
	window.__v2SyncLoaded = true;

	function _setText(id, v) {
		const el = document.getElementById(id);
		if (!el) return;
		el.textContent = (v === undefined || v === null || v === "") ? "-" : String(v);
	}

	function _renderOk({ designHoursCeil, designSell, setupHoursCeil, setupSell }) {
		_setText("sum_designHoursCeil", designHoursCeil);
		_setText("sum_designSell", Number(designSell || 0).toLocaleString());
		_setText("sum_setupHoursCeil", setupHoursCeil);
		_setText("sum_setupSell", Number(setupSell || 0).toLocaleString());
		_setText("sum_missing", "-");
		_setText("sum_fixedRow1", "");
		_setText("sum_fixedRow2", "");
		const ngBlock = document.getElementById("v2_ng_reason_block");
		if (ngBlock) ngBlock.classList.add("d-none");
	}

	function _renderNg(missingArr) {
		_setText("sum_designHoursCeil", "-");
		_setText("sum_designSell", "-");
		_setText("sum_setupHoursCeil", "-");
		_setText("sum_setupSell", "-");
		_setText("sum_fixedRow1", "");
		_setText("sum_fixedRow2", "");
		_setText("sum_missing", (missingArr && missingArr.length) ? missingArr.join(", ") : "-");
		const ngBlock = document.getElementById("v2_ng_reason_block");
		if (ngBlock) ngBlock.classList.remove("d-none");
	}

	function runEstimateV2() {
		try {
			if (!window.__v2 || typeof window.__v2.readParamsV2FromWizard !== "function") {
				console.error("[V2] __v2.readParamsV2FromWizard missing");
				_renderNg(["V2コア未ロード"]);
				return;
			}

			const p = window.__v2.readParamsV2FromWizard();
			const vres = window.__v2.validateEstimateV2(p);

			if (!vres.ok) {
				_renderNg(vres.missing);
				return;
			}

			const m = window.__v2.deriveRouteMetricsV2(p);
			const design = window.__v2.calcDesignHoursV2(p, m);
			const setup = window.__v2.calcSetupHoursV2(p, m);

			const designAmt = window.__v2.convertAmounts(design);
			const setupAmt = window.__v2.convertAmounts(setup);

			// V2実行時点の売価合計・原価合計を保持
			const v2SellTotal = Number(designAmt.sell || 0) + Number(setupAmt.sell || 0);
			const v2CostTotal = Number(designAmt.cost || 0) + Number(setupAmt.cost || 0);

			window.QUOTE_TOTALS = {
				sellBeforeDiscount: Math.round(v2SellTotal),
				costTotal: Math.round(v2CostTotal)
			};

			window.LAST_PROFIT_TOTALS = {
				sellBeforeDiscount: Math.round(v2SellTotal),
				costTotal: Math.round(v2CostTotal)
			};

			// デバッグ保持
			window.V2_LAST_RESULT = { p, m, design, setup, designAmt, setupAmt };

			// プレビュー更新
			_renderOk({
				designHoursCeil: designAmt.hoursCeil,
				designSell: designAmt.sell,
				setupHoursCeil: setupAmt.hoursCeil,
				setupSell: setupAmt.sell
			});

			// 明細2行 upsert（存在すれば）
			if (typeof window.upsertV2FixedRows === "function") {
				window.upsertV2FixedRows({
					designSell: designAmt.sell,
					designCost: designAmt.cost,
					setupSell: setupAmt.sell,
					setupCost: setupAmt.cost
				});
			} else {
				console.warn("[V2] upsertV2FixedRows not found");
			}

			// 合計・利益更新（存在すれば）
			window.updateGrandTotal?.();
			window.updateTotalProfitPreview?.({ applyDiscount: false });

		} catch (e) {
			console.error("[V2] runEstimateV2 failed:", e);
			_renderNg(["V2実行エラー(コンソール参照)"]);
		}
	}

	// export（未定義を一切出さない）
	window.runEstimateV2 = runEstimateV2;

	// 既存bootが initV2WizardBindings を探しているなら、no-opで満たす
	window.initV2WizardBindings = window.initV2WizardBindings || function () {};

	// ボタンに確実にバインド
	document.addEventListener("DOMContentLoaded", () => {
		const btn = document.getElementById("v2_run");
		if (!btn) return;
		if (btn.__v2Bound) return;
		btn.__v2Bound = true;

		btn.addEventListener("click", () => runEstimateV2());
	});
})();
// V2同期: 入力同期・runEstimateV2・固定行upsert
	// 依存: v2_core.js, details_table.js, common.js

	(function () {
	    if (window.__v2SyncLoaded) return;
	    window.__v2SyncLoaded = true;

	    // --- V2ウィザード表示制御（常時全ステップ表示） ---
	    function _showStep(stepNo) {
	        // 何もしない（全ステップ常時表示）
	    }

	    // --- V2計算・同期本体 ---
	    function runEstimateV2() {
	        const p = window.__v2.readParamsV2FromWizard();
	        const vres = window.__v2.validateEstimateV2(p);
	        if (!vres.ok) {
	            _renderNg(vres.missing);
	            return;
	        }
	        const m = window.__v2.deriveRouteMetricsV2(p);
	        const design = window.__v2.calcDesignHoursV2(p, m);
	        const setup = window.__v2.calcSetupHoursV2(p, m);
	        const designAmt = window.__v2.convertAmounts(design);
	        const setupAmt = window.__v2.convertAmounts(setup);
        // V2実行時点の売価合計・原価合計を保持
        const v2SellTotal = Number(designAmt.sell || 0) + Number(setupAmt.sell || 0);
        const v2CostTotal = Number(designAmt.cost || 0) + Number(setupAmt.cost || 0);

        window.QUOTE_TOTALS = {
            sellBeforeDiscount: Math.round(v2SellTotal),
            costTotal: Math.round(v2CostTotal)
        };

        window.LAST_PROFIT_TOTALS = {
            sellBeforeDiscount: Math.round(v2SellTotal),
            costTotal: Math.round(v2CostTotal)
        };
	        // V2結果をwindowに保持（デバッグ用）
	        window.V2_LAST_RESULT = { p, m, design, setup, designAmt, setupAmt };
	        // プレビュー欄更新
	        _renderOk({
	            designHoursCeil: designAmt.hoursCeil,
	            designSell: designAmt.sell,
	            setupHoursCeil: setupAmt.hoursCeil,
	            setupSell: setupAmt.sell,
	            missing: '',
	            fixedRow1: '',
	            fixedRow2: ''
	        });
	        // 明細2行固定反映
	        if (window.upsertV2FixedRows) {
	            window.upsertV2FixedRows({
	                designSell: designAmt.sell,
	                designCost: designAmt.cost,
	                setupSell: setupAmt.sell,
	                setupCost: setupAmt.cost
	            });
	        }
	        // 合計・利益再計算
	        if (typeof window.updateTotalProfitPreview === "function") {
            window.updateTotalProfitPreview({ applyDiscount: false });
	        }
	    }

	    // プレビュー欄更新
	    function _renderOk(obj) {
	        document.getElementById('sum_designHoursCeil').textContent = obj.designHoursCeil || '-';
	        document.getElementById('sum_designSell').textContent = obj.designSell || '-';
	        document.getElementById('sum_setupHoursCeil').textContent = obj.setupHoursCeil || '-';
	        document.getElementById('sum_setupSell').textContent = obj.setupSell || '-';
	        document.getElementById('sum_missing').textContent = obj.missing || '';
	        document.getElementById('sum_fixedRow1').textContent = obj.fixedRow1 || '';
	        document.getElementById('sum_fixedRow2').textContent = obj.fixedRow2 || '';
	    }
	    function _renderNg(missing) {
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
