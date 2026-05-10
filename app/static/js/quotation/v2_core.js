
// app/static/js/quotation/v2_core.js
// V2コア: UIから入力を読む → validate → metrics → 工数計算 → 金額換算
// 依存: なし（ただし rates-json が window.rates に入っていれば利用）

(function () {
  if (window.__v2CoreLoaded) return;
  window.__v2CoreLoaded = true;

  function _el(id) { return document.getElementById(id); }

  function _num(v, def = 0) {
    if (v === null || v === undefined) return def;
    const s = String(v).replace(/,/g, "").trim();
    if (s === "") return def;
    const n = Number(s);
    return Number.isFinite(n) ? n : def;
  }

  function _int(id, def = 0) {
    const el = _el(id);
    return _num(el ? el.value : null, def) | 0;
  }

  function _float(id, def = 0) {
    const el = _el(id);
    return _num(el ? el.value : null, def);
  }

  // --- Step2/3 read ---
  function readParamsV2FromWizard() {
    const allRows = [];

    for (let i = 1; i <= 6; i++) {
      const tbody = document.getElementById(`v2_step2_tbody_T${i}`);
      if (!tbody) continue;

      const trs = Array.from(tbody.querySelectorAll("tr"));
      trs.forEach((tr, idx) => {
        const rowIndex = idx + 1;

        const vehicle = _int(`v2_vehicle_T${i}_${rowIndex}`, 0);
        const station = _int(`v2_station_T${i}_${rowIndex}`, 0);
        const short_m = _float(`v2_short_T${i}_${rowIndex}`, 0);
        const long_m  = _float(`v2_long_T${i}_${rowIndex}`, 0);
        const wait    = _int(`v2_wait_T${i}_${rowIndex}`, 0);
        const memo    = _el(`v2_memo_T${i}_${rowIndex}`)?.value || "";

        allRows.push({ tidx: i, rowIndex, vehicle, station, short_m, long_m, wait, memo });
      });
    }

    const activeRows = allRows.filter(r =>
      (r.vehicle > 0) || (r.station > 0) || (r.short_m > 0) || (r.long_m > 0) || (r.wait > 0) || (r.memo && r.memo.trim() !== "")
    );

    return {
      activeRows,
      equipmentCount: _int("v2_equipmentCount", 0),
      signalPoints:   _int("v2_signalPoints", 0),
      chargerCount:   _int("v2_chargerCount", 0),
      elevatorCount:  _int("v2_elevatorCount", 0),
      autoDoorCount:  _int("v2_autoDoorCount", 0)
    };
  }

  function validateEstimateV2(p) {
    const missing = [];

    if (!p.activeRows || p.activeRows.length === 0) {
      missing.push("ルートテンプレート行が1行以上");
      return { ok: false, missing };
    }

    const vehicleTotal = p.activeRows.reduce((s, r) => s + (r.vehicle || 0), 0);
    if (vehicleTotal <= 0) missing.push("台数が0");

    p.activeRows.forEach(r => {
      if ((r.station || 0) <= 0) missing.push(`T${r.tidx}-${r.rowIndex}: ステーション数が0`);
    });

    return { ok: missing.length === 0, missing };
  }

  function deriveRouteMetricsV2(p) {
    const rows = p.activeRows || [];
    const vehicleCountTotal = rows.reduce((s, r) => s + (r.vehicle || 0), 0);
    const stationCountTotal = rows.reduce((s, r) => s + (r.station || 0), 0);
    const routeRowCount = rows.length;

    // ざっくりの規模指数（今はUI一致優先で保守的に）
    const areaSizeIndex = rows.reduce((s, r) => s + Math.max(r.short_m || 0, r.long_m || 0), 0);
    const waitTotal = rows.reduce((s, r) => s + (r.wait || 0), 0);
    const templateWeightedCount = rows.reduce((s, r) => s + (r.tidx || 0), 0);

    return { vehicleCountTotal, stationCountTotal, routeRowCount, areaSizeIndex, waitTotal, templateWeightedCount };
  }

  function calcDesignHoursV2(p, m) {
    const C = window.COEF_V2 || {
      design_base: 40,
      design_per_vehicle: 6.0,
      design_per_station: 0.8,
      design_per_routeRow: 2.5,
      design_per_templateWeight: 0.5,
      design_per_areaIndex: 0.1,
      design_if_equipment: 2.0,
      design_if_signal: 0.3,
      design_if_charger: 1.0,
      design_if_elevator: 2.0,
      design_if_autoDoor: 1.0
    };

    const raw =
      C.design_base +
      C.design_per_vehicle * (m.vehicleCountTotal || 0) +
      C.design_per_station * (m.stationCountTotal || 0) +
      C.design_per_routeRow * (m.routeRowCount || 0) +
      C.design_per_templateWeight * (m.templateWeightedCount || 0) +
      C.design_per_areaIndex * (m.areaSizeIndex || 0) +
      C.design_if_equipment * (p.equipmentCount || 0) +
      C.design_if_signal * (p.signalPoints || 0) +
      C.design_if_charger * (p.chargerCount || 0) +
      C.design_if_elevator * (p.elevatorCount || 0) +
      C.design_if_autoDoor * (p.autoDoorCount || 0);

    const ceil = Math.ceil(raw);
    return { hoursRaw: raw, hoursCeil: ceil };
  }

  function calcSetupHoursV2(p, m) {
    const C = window.COEF_V2 || {
      setup_base: 40,
      setup_per_vehicle: 6.0,
      setup_per_station: 0.8,
      setup_per_routeRow: 2.5,
      setup_per_wait: 1.0,
      setup_if_equipment: 2.0,
      setup_if_signal: 0.3,
      setup_if_charger: 1.0,
      setup_if_elevator: 2.0,
      setup_if_autoDoor: 1.0
    };

    const raw =
      C.setup_base +
      C.setup_per_vehicle * (m.vehicleCountTotal || 0) +
      C.setup_per_station * (m.stationCountTotal || 0) +
      C.setup_per_routeRow * (m.routeRowCount || 0) +
      C.setup_per_wait * (m.waitTotal || 0) +
      C.setup_if_equipment * (p.equipmentCount || 0) +
      C.setup_if_signal * (p.signalPoints || 0) +
      C.setup_if_charger * (p.chargerCount || 0) +
      C.setup_if_elevator * (p.elevatorCount || 0) +
      C.setup_if_autoDoor * (p.autoDoorCount || 0);

    const ceil = Math.ceil(raw);
    return { hoursRaw: raw, hoursCeil: ceil };
  }

  function convertAmounts(hoursObj) {
    const hoursRaw = (hoursObj && typeof hoursObj === "object") ? hoursObj.hoursRaw : _num(hoursObj, 0);
    const hoursCeil = (hoursObj && typeof hoursObj === "object") ? (hoursObj.hoursCeil | 0) : Math.ceil(_num(hoursObj, 0));

    // 既定
    let costRate = 17760;
    let sellRate = 29600;

    // rates-json 連携があれば採用
    if (window.rates && typeof window.rates === "object") {
      if (Number.isFinite(window.rates.labor)) costRate = window.rates.labor;
      if (Number.isFinite(window.rates.sell)) sellRate = window.rates.sell;
    }

    return {
      hoursRaw: Math.round(hoursRaw * 10) / 10,
      hoursCeil,
      costRate,
      sellRate,
      cost: hoursCeil * costRate,
      sell: hoursCeil * sellRate
    };
  }

  // export
  window.__v2 = window.__v2 || {};
  window.__v2.readParamsV2FromWizard = readParamsV2FromWizard;
  window.__v2.validateEstimateV2 = validateEstimateV2;
  window.__v2.deriveRouteMetricsV2 = deriveRouteMetricsV2;
  window.__v2.calcDesignHoursV2 = calcDesignHoursV2;
  window.__v2.calcSetupHoursV2 = calcSetupHoursV2;
  window.__v2.convertAmounts = convertAmounts;

})();
