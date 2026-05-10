// app/static/js/quotation/v2_live_summary.js
// V2ライブサマリー: 表示更新・バインドのみ専任（軽量・副作用なし）
// 依存: v2_core.js, v2_sync.js, common.js（_debounce があれば利用）

(function () {
  if (window.__v2LiveSummaryLoaded) return;
  window.__v2LiveSummaryLoaded = true;

  function _root() {
    return document.getElementById("v2-estimate-wizard") || document.getElementById("v2_wizard");
  }

  function _setTextByIds(ids, v) {
    for (const id of ids) {
      const el = document.getElementById(id);
      if (!el) continue;
      el.textContent = (v == null || v === "") ? "-" : String(v);
    }
  }

  function _fmtInt(n) {
    if (typeof window._fmtInt === "function") return window._fmtInt(n);
    if (!Number.isFinite(n)) return "-";
    return Math.round(n).toLocaleString();
  }

  function _fmt1(n) {
    if (typeof window._fmt1 === "function") return window._fmt1(n);
    if (!Number.isFinite(n)) return "-";
    return Number(n).toFixed(1);
  }

  // --- サマリー表示更新（副作用なし：coreを直接呼ぶ） ---
  function v2UpdateLiveSummary() {
    try {
      // V2 core 未ロード or wizard無しなら何もしない
      if (!window.__v2
        || typeof window.__v2.readParamsV2FromWizard !== "function"
        || typeof window.__v2.validateEstimateV2 !== "function"
        || typeof window.__v2.deriveRouteMetricsV2 !== "function"
        || typeof window.__v2.calcDesignHoursV2 !== "function"
        || typeof window.__v2.calcSetupHoursV2 !== "function"
        || typeof window.__v2.convertAmounts !== "function") {
        return;
      }
      if (!_root()) return;

      const p = window.__v2.readParamsV2FromWizard();
      const v = window.__v2.validateEstimateV2(p);

      // 入力値（存在する要素だけ更新）
      _setTextByIds(["sum_vehicleCount"], p.vehicleCount ?? "-");
      _setTextByIds(["sum_stationCount"], p.stationCount ?? "-");
      _setTextByIds(["sum_areaShort_m"], (p.areaShort_m > 0) ? p.areaShort_m : "-");
      _setTextByIds(["sum_areaLong_m"],  (p.areaLong_m  > 0) ? p.areaLong_m  : "-");

      (p.routes || []).forEach((r) => {
        const k = String(r.key || "").replace("T", "");
        _setTextByIds([`sum_qty_T${k}`], r.qty ?? "-");
        _setTextByIds([`sum_veh_T${k}`], r.veh ?? "-");
      });

      _setTextByIds(["sum_equipmentCount"], p.equipmentCount ?? "-");
      _setTextByIds(["sum_signalPoints"], p.signalPoints ?? "-");
      _setTextByIds(["sum_junctionCount"], p.junctionCount ?? "-");
      _setTextByIds(["sum_minAisleWidth_m"], p.minAisleWidth_m ?? "-");
      _setTextByIds(["sum_tapeStops"], p.tapeStops ?? "-");
      _setTextByIds(["sum_lmSpots"], p.lmSpots ?? "-");

      // NG理由表示
      _setTextByIds(["sum_missing"], (v.missing && v.missing.length) ? v.missing.join(" / ") : "-");

      if (!v.ok) {
        // OK欄の数値をクリア（存在する要素だけ）
        [
          "sum_designHoursRaw","sum_designHoursCeil","sum_designCost","sum_designSell",
          "sum_setupHoursRaw","sum_setupHoursCeil","sum_setupCost","sum_setupSell",
          "sum_costRate","sum_sellRate",
          "sum_fixedRow1","sum_fixedRow2"
        ].forEach((id) => _setTextByIds([id], "-"));

        // もう一系統のID（v2_summary_*）もクリアしておく（HTML揺れ対策）
        _setTextByIds(["v2_summary_design_fee","v2_summary_setup_fee","v2_summary_total_with_fee"], "-");
        _setTextByIds(["v2_summary_design_cost","v2_summary_setup_cost"], "-");
        return;
      }

      // --- 派生値 ---
      const m = window.__v2.deriveRouteMetricsV2(p);
      const design = window.__v2.convertAmounts(window.__v2.calcDesignHoursV2(p, m));
      const setup  = window.__v2.convertAmounts(window.__v2.calcSetupHoursV2(p, m));

      // sum_* 系（旧UI想定）
      _setTextByIds(["sum_designHoursRaw"], _fmt1(design.hoursRaw));
      _setTextByIds(["sum_designHoursCeil"], _fmtInt(design.hoursCeil));
      _setTextByIds(["sum_designCost"], _fmtInt(design.cost));
      _setTextByIds(["sum_designSell"], _fmtInt(design.sell));

      _setTextByIds(["sum_setupHoursRaw"], _fmt1(setup.hoursRaw));
      _setTextByIds(["sum_setupHoursCeil"], _fmtInt(setup.hoursCeil));
      _setTextByIds(["sum_setupCost"], _fmtInt(setup.cost));
      _setTextByIds(["sum_setupSell"], _fmtInt(setup.sell));

      _setTextByIds(["sum_costRate"], _fmtInt(design.costRate));
      _setTextByIds(["sum_sellRate"], _fmtInt(design.sellRate));

      _setTextByIds(["sum_fixedRow1"], `設計費（V2自動算出）: ${_fmtInt(design.sell)} 円`);
      _setTextByIds(["sum_fixedRow2"], `現地セットアップ費（V2自動算出）: ${_fmtInt(setup.sell)} 円`);

      // v2_summary_* 系（今回あなたが使っているID想定）
      _setTextByIds(["v2_summary_design_fee"], _fmtInt(design.sell));
      _setTextByIds(["v2_summary_setup_fee"], _fmtInt(setup.sell));
      _setTextByIds(["v2_summary_total_with_fee"], _fmtInt((design.sell || 0) + (setup.sell || 0)));
      _setTextByIds(["v2_summary_design_cost"], _fmtInt(design.cost));
      _setTextByIds(["v2_summary_setup_cost"], _fmtInt(setup.cost));

    } catch (err) {
      console.warn("[V2] v2UpdateLiveSummary failed:", err);
    }
  }

  // --- バインド（監視対象をwizard内に限定 + debounce） ---
  function initV2LiveSummaryBindings() {
    console.log("[V2] initV2LiveSummaryBindings called");
    if (window.__v2LiveSummaryBound) return;
    window.__v2LiveSummaryBound = true;

    const root = _root();
    if (!root) return;

    const debounce = (typeof window._debounce === "function")
      ? window._debounce
      : (fn) => fn;

    // 表示更新（軽いので即時でも可）
    const onInput = (e) => {
      const el = e.target;
      if (!el || !el.id) return;
      if (!String(el.id).startsWith("v2_")) return;
      v2UpdateLiveSummary();
      debouncedSync();
    };

    // 固定行/利益などの「同期」は重くなり得るので debounce
    const debouncedSync = debounce(() => {
      if (window.__v2 && typeof window.__v2.syncFromInputs === "function") {
        window.__v2.syncFromInputs({
          updateFixedRows: true,
          updateProfit: true,
          updateStep4IfVisible: false,
          clearOnNg: true
        });
      }
    }, 250);

    root.addEventListener("input", onInput);
    root.addEventListener("change", onInput);

    // 初回描画
    v2UpdateLiveSummary();

    // __v2が遅延ロードされるケースの保険（最大1秒）
    if (!window.__v2LiveKickOnceStarted) {
      window.__v2LiveKickOnceStarted = true;
      let tries = 0;
      const timer = setInterval(() => {
        tries++;
        if (window.__v2 && typeof window.__v2.readParamsV2FromWizard === "function") {
          clearInterval(timer);
          v2UpdateLiveSummary();
        }
        if (tries >= 10) clearInterval(timer);
      }, 100);
    }
  }

  // export
  window.v2UpdateLiveSummary = v2UpdateLiveSummary;
  window.initV2LiveSummaryBindings = initV2LiveSummaryBindings;
})();
