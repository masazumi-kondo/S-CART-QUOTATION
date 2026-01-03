// ==============================
// V2 Live Summary (Right Card)
// ==============================
(function () {
    // debounce helper for input sync
    function _debounce(fn, waitMs) {
      let t = null;
      return function (...args) {
        if (t) clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), waitMs);
      };
    }
  // Guard: HTMLが無いページでは何もしない
  function _sumEl(id) { return document.getElementById(id); }
  function _setText(id, v) {
    const el = _sumEl(id);
    if (!el) return;
    el.textContent = (v == null || v === "") ? "-" : String(v);
  }
  function _fmtInt(n) {
    if (!Number.isFinite(n)) return "-";
    return Math.round(n).toLocaleString();
  }
  function _fmt1(n) {
    if (!Number.isFinite(n)) return "-";
    return Number(n).toFixed(1);
  }

  // 公開：外から呼べるように
  window.v2UpdateLiveSummary = function v2UpdateLiveSummary() {
    try {
      // V2ウィザードが存在しないページでは何もしない
      if (!document.getElementById("v2-estimate-wizard")) return;

      // 既存関数が無い場合は落とさない
      // すべてwindow.__v2経由で呼ぶ
      if (!window.__v2) return;
      const {
        readParamsV2FromWizard,
        validateEstimateV2,
        deriveRouteMetricsV2,
        calcDesignHoursV2,
        calcSetupHoursV2,
        convertAmounts
      } = window.__v2;
      if (typeof readParamsV2FromWizard !== "function") return;
      if (typeof validateEstimateV2 !== "function") return;
      if (typeof deriveRouteMetricsV2 !== "function") return;

      const p = readParamsV2FromWizard();
      const v = validateEstimateV2(p);

      if (v.ok) {
        // --- 入力値 ---
        _setText("sum_vehicleCount", p.vehicleCount ?? "-");
        _setText("sum_stationCount", p.stationCount ?? "-");
        _setText("sum_areaShort_m", p.areaShort_m ?? "-");
        _setText("sum_areaLong_m", p.areaLong_m ?? "-");

        // routes
        (p.routes || []).forEach((r) => {
          const k = (r.key || "").replace("T", "");
          _setText(`sum_qty_T${k}`, r.qty ?? "-");
          _setText(`sum_veh_T${k}`, r.veh ?? "-");
        });

        // optional
        _setText("sum_equipmentCount", p.equipmentCount ?? "-");
        _setText("sum_signalPoints", p.signalPoints ?? "-");
        _setText("sum_junctionCount", p.junctionCount ?? "-");
        _setText("sum_minAisleWidth_m", p.minAisleWidth_m ?? "-");
        _setText("sum_tapeStops", p.tapeStops ?? "-");
        _setText("sum_lmSpots", p.lmSpots ?? "-");

        // NG理由（デバッグ欄）
        _setText("sum_missing", (v.missing && v.missing.length) ? v.missing.join(" / ") : "-");

        // --- 派生値 ---
        const m = deriveRouteMetricsV2(p);
        const design = convertAmounts(calcDesignHoursV2(p, m));
        const setup  = convertAmounts(calcSetupHoursV2(p, m));
        _setText("sum_designHoursRaw", _fmt1(design.hoursRaw));
        _setText("sum_designHoursCeil", _fmtInt(design.hoursCeil));
        _setText("sum_designCost", _fmtInt(design.cost));
        _setText("sum_designSell", _fmtInt(design.sell));
        _setText("sum_setupHoursRaw", _fmt1(setup.hoursRaw));
        _setText("sum_setupHoursCeil", _fmtInt(setup.hoursCeil));
        _setText("sum_setupCost", _fmtInt(setup.cost));
        _setText("sum_setupSell", _fmtInt(setup.sell));
        _setText("sum_costRate", _fmtInt(design.costRate));
        _setText("sum_sellRate", _fmtInt(design.sellRate));
        // 明細反映予定
        _setText("sum_fixedRow1", `設計費（V2自動算出）: ${_fmtInt(design.sell)} 円`);
        _setText("sum_fixedRow2", `現地セットアップ費（V2自動算出）: ${_fmtInt(setup.sell)} 円`);
      } else {
        // NG時は結果欄をリセット
        ["sum_designHoursRaw","sum_designHoursCeil","sum_designCost","sum_designSell",
         "sum_setupHoursRaw","sum_setupHoursCeil","sum_setupCost","sum_setupSell",
         "sum_costRate","sum_sellRate"].forEach((id) => _setText(id, "-"));
        _setText("sum_fixedRow1", "-");
        _setText("sum_fixedRow2", "-");
      }
    } catch (err) {
      console.warn("[V2] v2UpdateLiveSummary failed:", err);
    }
  };

  // デバッグトグル
  function _bindV2DebugToggle() {
    const t = _sumEl("v2_debug_toggle");
    const d = _sumEl("v2_debug_detail");
    if (!t || !d) return;
    const apply = () => { d.style.display = t.checked ? "" : "none"; };
    t.addEventListener("change", apply);
    apply();
  }

  // 入力イベントで更新（v2_ prefixだけ）
  function _bindV2LiveSummaryInputs() {
    const root = document.getElementById("v2-estimate-wizard");
    if (!root) return;

    // debounce sync for fixed rows/profit preview
    const debouncedSync = _debounce(() => {
      if (window.__v2 && typeof window.__v2.syncFromInputs === "function") {
        window.__v2.syncFromInputs({
          updateFixedRows: true,
          updateProfit: true,
          updateStep4IfVisible: false,
          clearOnNg: true
        });
      }
    }, 250);

    const handler = (e) => {
      const el = e.target;
      if (!el || !el.id) return;
      if (!String(el.id).startsWith("v2_")) return;
      window.v2UpdateLiveSummary?.();
      debouncedSync();
    };

    root.addEventListener("input", handler);
    root.addEventListener("change", handler);
  }

  // init
  function _initV2LiveSummary() {
    _bindV2DebugToggle();
    _bindV2LiveSummaryInputs();
    // 初期描画
    window.v2UpdateLiveSummary?.();

    // __v2 が後から来る場合に備え、1回だけ遅延同期（最大1秒程度で打ち切り）
    if (!window.__v2KickOnceStarted) {
      window.__v2KickOnceStarted = true;
      (function _kickOnceWhenV2Ready() {
        let tries = 0;
        const timer = setInterval(() => {
          tries++;
          if (window.__v2 && typeof window.__v2.readParamsV2FromWizard === "function") {
            clearInterval(timer);
            window.v2UpdateLiveSummary?.();
          }
          if (tries >= 10) clearInterval(timer);
        }, 100);
      })();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _initV2LiveSummary, { once: true });
  } else {
    _initV2LiveSummary();
  }
})();
// Step2 qty>0 のとき veh 未入力なら vehicleCount を自動セット
function _autoFillV2VehiclesIfBlank() {
  const vc = parseInt(document.getElementById("v2_vehicleCount")?.value || "", 10);
  const vehicleCount = Number.isFinite(vc) && vc > 0 ? vc : 0;

  for (let i = 1; i <= 6; i++) {
    const qtyEl = document.getElementById(`v2_qty_T${i}`);
    const vehEl = document.getElementById(`v2_veh_T${i}`);
    if (!qtyEl || !vehEl) continue;

    const qty = parseInt(qtyEl.value || "0", 10) || 0;
    const vehRaw = parseInt(vehEl.value || "", 10);
    const veh = Number.isFinite(vehRaw) ? vehRaw : 0;

    // qty>0 なのに veh が未入力/0 の場合のみ自動セット（手入力は上書きしない）
    if (qty > 0 && veh <= 0 && vehicleCount > 0) {
      vehEl.value = String(vehicleCount);
    }
  }
}

// capture=true で「他の click より先に」実行させる（順序事故を潰す）
// V2本体ロジックはDOMContentLoaded内でバインドするので、ここでは不要

// 明細行生成
window.createDetailRow = function () {
  const row = document.createElement("tr");

  // 製品 select
  const tdProduct = document.createElement("td");
  const select = document.createElement("select");
  select.name = "product_id[]";
  select.className = "form-select product-select-custom";
  select.innerHTML = '<option value="">選択</option>';
  if (Array.isArray(window.products)) {
    window.products.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name || p.id; // 表示は name 優先
      select.appendChild(opt);
    });
  }
  tdProduct.appendChild(select);
  row.appendChild(tdProduct);


  // 品名（description）
  const tdName = document.createElement("td");
  const descInput = document.createElement("input");
  descInput.type = "text";
  descInput.name = "description[]";
  descInput.className = "form-control";
  tdName.appendChild(descInput);
  // コード（code）hidden input
  const codeInput = document.createElement("input");
  codeInput.type = "hidden";
  codeInput.name = "code[]";
  codeInput.value = "";
  tdName.appendChild(codeInput);
  row.appendChild(tdName);

  // 単価
  const tdUnitPrice = document.createElement("td");
  const unitPriceInput = document.createElement("input");
  unitPriceInput.type = "number";
  unitPriceInput.name = "unit_price[]";
  unitPriceInput.className = "form-control text-end";
  unitPriceInput.min = "0";
  unitPriceInput.step = "1";
  unitPriceInput.readOnly = false; // 初期は編集可
  tdUnitPrice.appendChild(unitPriceInput);
  row.appendChild(tdUnitPrice);

  // 数量
  const tdQty = document.createElement("td");
  const qtyInput = document.createElement("input");
  qtyInput.type = "number";
  qtyInput.name = "quantity[]";
  qtyInput.className = "form-control text-end";
  qtyInput.min = "0";
  qtyInput.step = "1";
  tdQty.appendChild(qtyInput);
  row.appendChild(tdQty);

  // 小計
  const tdSubtotal = document.createElement("td");
  const subtotalInput = document.createElement("input");
  subtotalInput.type = "text";
  subtotalInput.name = "subtotal[]";
  subtotalInput.className = "form-control text-end";
  subtotalInput.readOnly = true;
  tdSubtotal.appendChild(subtotalInput);
  row.appendChild(tdSubtotal);


  // 追加/削除ボタン（テンプレと統一: ＋/－）
  const tdRemove = document.createElement("td");
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "btn btn-outline-secondary btn-sm add-row";
  addBtn.textContent = "＋";
  tdRemove.appendChild(addBtn);
  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "btn btn-outline-danger btn-sm remove-row";
  removeBtn.textContent = "－";
  tdRemove.appendChild(removeBtn);
  row.appendChild(tdRemove);

  // 行イベントをバインド
  if (typeof window.bindDetailRowEvents === "function") {
    window.bindDetailRowEvents(row);
  }


  return row;
};

// 明細行追加
window.addDetailRow = function () {
  const tbody = document.getElementById("detail-body");
  if (!tbody || typeof window.createDetailRow !== "function") return;
  const row = window.createDetailRow();
  tbody.appendChild(row);
  window.updateGrandTotal();
};

// ==============================
// 初期化
// ==============================

document.addEventListener("DOMContentLoaded", function () {
  if (window.__quotationFormDomBound) return;
  window.__quotationFormDomBound = true;
  console.log("[quotation_form.js] DOMContentLoaded - init start");

  // --- 明細テーブル: 製品選択・単価・数量のイベント委譲（最小diff, 二重バインド防止） ---
  if (!window.__quotationDetailDelegated) {
    window.__quotationDetailDelegated = true;
    const tbody = document.getElementById("detail-body");
    const table = document.getElementById("details-table");
    const delegateTarget = tbody || table;
    if (delegateTarget) {
      delegateTarget.addEventListener("change", function (e) {
        // 1) 製品 select の change
        const sel = e.target.closest('select[name="product_id[]"]');
        if (sel) {
          const tr = sel.closest("tr");
          if (!tr) return;

          const productId = sel.value;

          const unitPriceEl = tr.querySelector('input[name="unit_price[]"]');
          const qtyEl = tr.querySelector('input[name="quantity[]"]');
          const subtotalEl = tr.querySelector('input[name="subtotal[]"]');
          const codeEl = tr.querySelector('input[name="code[]"]');
          const descEl = tr.querySelector('input[name="description[]"]');

          let p = null;
          if (Array.isArray(window.products)) {
            p = window.products.find((x) => String(x.id) === String(productId));
          }

          // 商品マスタ反映（必要な分だけ）
          if (p) {
            if (descEl && !descEl.value) descEl.value = p.name || descEl.value;
            if (codeEl) codeEl.value = p.code || p.id || "";
            if (unitPriceEl) unitPriceEl.value = String(Math.round(Number(p.price || 0)));
          } else {
            // 未選択の場合のリセット（必要なら）
            if (codeEl) codeEl.value = "";
            // desc はユーザー自由入力もあるので消さない運用ならここは触らない
            if (unitPriceEl) unitPriceEl.value = unitPriceEl.value || "";
          }

          // 小計更新
          if (unitPriceEl && qtyEl && subtotalEl) {
            const subtotal = safeParseFloat(unitPriceEl.value) * safeParseFloat(qtyEl.value);
            subtotalEl.value = subtotal > 0 ? Math.round(subtotal).toLocaleString() : "";
          }

          window.updateGrandTotal?.();
          return; // ここで終了（下の unit_price/quantity 分岐に落とさない）
        }

        // 2) unit_price / quantity の change
        const unitPriceEl2 = e.target.closest('input[name="unit_price[]"]');
        const qtyEl2 = e.target.closest('input[name="quantity[]"]');
        if (unitPriceEl2 || qtyEl2) {
          const tr = (unitPriceEl2 || qtyEl2).closest("tr");
          if (!tr) return;

          const up = tr.querySelector('input[name="unit_price[]"]');
          const qty = tr.querySelector('input[name="quantity[]"]');
          const subtotalEl = tr.querySelector('input[name="subtotal[]"]');

          if (up && qty && subtotalEl) {
            const subtotal = safeParseFloat(up.value) * safeParseFloat(qty.value);
            subtotalEl.value = subtotal > 0 ? Math.round(subtotal).toLocaleString() : "";
          }

          window.updateGrandTotal?.();
        }
      });
    }
  }

  const table = document.getElementById("details-table");
  const tbody = document.getElementById("detail-body");

  // --- PATCH: 追加/削除ボタンのイベント委譲（class="add-row"/"remove-row"/"remove-row-btn"） ---
  if (table && tbody) {
    table.addEventListener("click", (e) => {
      const addBtn = e.target.closest("button.add-row");
      if (addBtn) {
        e.preventDefault();
        const tr = addBtn.closest("tr");
        // 事故防止: 固定行なら何もしない
        if (tr && tr.classList.contains("js-fixed-row")) return;
        const row = window.createDetailRow?.();
        if (row && tr && tr.parentNode === tbody) {
          tr.insertAdjacentElement("afterend", row); // 押した行の直後に追加
        } else {
          window.addDetailRow?.(); // フォールバック
        }
        window.updateGrandTotal?.();
        return;
      }

      const rmBtn = e.target.closest("button.remove-row, button.remove-row-btn");
      if (rmBtn) {
        e.preventDefault();
        const tr = rmBtn.closest("tr");
        if (!tr) return;
        if (tr.classList.contains("js-fixed-row")) return;

        const rows = Array.from(tbody.querySelectorAll("tr"));
        if (rows.length <= 1) {
          tr.querySelectorAll("input, select, textarea").forEach((el) => {
            if (el.type === "checkbox" || el.type === "radio") el.checked = false;
            else el.value = "";
          });
        } else {
          tr.remove();
        }
        window.updateGrandTotal?.();
      }
    });
  }

  // --- 既存の初期化・バインド処理 ---
  if (tbody && Array.isArray(window.INITIAL_DETAILS) && window.INITIAL_DETAILS.length > 0) {
    tbody.innerHTML = "";
    window.INITIAL_DETAILS.forEach(function (d) {
      if (typeof window.createDetailRow === "function") {
        const row = window.createDetailRow();
        if (row) {
          const isFixed = d.label === "設計費（パラメータ）" || d.label === "現地セットアップ（パラメータ）";
          const pidStr = (d.product_id == null ? "" : String(d.product_id)).trim();
          const hasProduct = pidStr !== "" && pidStr !== "0";
          if (hasProduct && row.querySelector('select[name="product_id[]"]')) {
            const sel = row.querySelector('select[name="product_id[]"]');
            if (d.quantity !== undefined && row.querySelector('input[name="quantity[]"]')) {
              row.querySelector('input[name="quantity[]"]').value = d.quantity;
            }
            sel.value = pidStr;
            if (!isFixed) {
              sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
          }
          tbody.appendChild(row);
        }
      }
    }); // ← forEachの正しい閉じカッコ
    window.updateGrandTotal();
  } else if (tbody) {
    const rows = Array.from(tbody.querySelectorAll("tr"));
    if (rows.length === 0) {
      if (typeof window.addDetailRow === "function") {
        window.addDetailRow();
      }
    } else {
      rows.forEach((row) => {
        if (typeof window.bindDetailRowEvents === "function") {
          window.bindDetailRowEvents(row);
        }
      });
    }
  }



  // updateGrandTotalをラップして、V2_LAST_FEESがあれば利益プレビューも追随
  if (!window.__updateGrandTotalWrapped && typeof window.updateGrandTotal === "function") {
    window.__updateGrandTotalWrapped = true;
    const _origUpdateGrandTotal = window.updateGrandTotal;
    window.updateGrandTotal = function (...args) {
      const ret = _origUpdateGrandTotal.apply(this, args);
      const st = window.V2_LAST_FEES;
      if (st && st.fees && typeof window.updateTotalProfitPreview === "function") {
        window.updateTotalProfitPreview(st.fees, st.designCost || 0, st.setupCost || 0);
      }
      return ret;
    };
  }

  window.updateGrandTotal();
// ==============================
// V2 Wizard: run -> Step4 render -> fixed rows upsert -> profit update
// ==============================

(function () {
  // --- helpers ---
  function _v2_el(id) { return document.getElementById(id); }
  function _v2_int(id, def = 0) {
    const v = _v2_el(id)?.value;
    if (v == null || String(v).trim() === "") return def;
    const n = parseInt(v, 10);
    return Number.isFinite(n) ? n : def;
  }
  function _v2_float(id, def = 0) {
    const v = _v2_el(id)?.value;
    if (v == null || String(v).trim() === "") return def;
    const n = parseFloat(String(v));
    return Number.isFinite(n) ? n : def;
  }
  function _v2_isBlank(id) {
    const v = _v2_el(id)?.value;
    return v == null || String(v).trim() === "";
  }
  function _v2_fmtInt(n) { return Math.round(n || 0).toLocaleString(); }
  function _v2_fmt1(n) { return (n || 0).toFixed(1); }

  function _v2_showStep(stepNo) {
    document.querySelectorAll("[data-v2-step]").forEach((sec) => {
      const s = parseInt(sec.getAttribute("data-v2-step"), 10);
      sec.style.display = (s === stepNo) ? "" : "none";
    });
  }

  function _v2_bindWizardNav() {
    document.querySelectorAll("[data-v2-next]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const n = parseInt(btn.getAttribute("data-v2-next"), 10);
        if (Number.isFinite(n)) _v2_showStep(n);
      });
    });
    document.querySelectorAll("[data-v2-prev]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const p = parseInt(btn.getAttribute("data-v2-prev"), 10);
        if (Number.isFinite(p)) _v2_showStep(p);
      });
    });
  }

  // --- Step2 metrics read ---
  // (exported at end of IIFE)
  function readParamsV2FromWizard() {
    const routes = [];
    for (let i = 1; i <= 6; i++) {
      routes.push({
        key: `T${i}`,
        qty: _v2_int(`v2_qty_T${i}`, 0),
        veh: _v2_int(`v2_veh_T${i}`, 0),
      });
    }

    return {
      vehicleCount: _v2_int("v2_vehicleCount", 0),
      stationCount: _v2_int("v2_stationCount", 0),
      areaShort_m: _v2_float("v2_areaShort_m", 0),
      areaLong_m: _v2_float("v2_areaLong_m", 0),

      // optional (Step3)
      equipmentCount: _v2_int("v2_equipmentCount", 0),
      signalPoints: _v2_int("v2_signalPoints", 0),
      junctionCount: _v2_int("v2_junctionCount", 0),
      minAisleWidth_m: _v2_float("v2_minAisleWidth_m", 0), // 0 means "unknown"
      tapeStops: _v2_int("v2_tapeStops", 0),
      lmSpots: _v2_int("v2_lmSpots", 0),

      routes,
    };
  }

  // --- validation: "missing only" if NG ---
  // (exported at end of IIFE)
  function validateEstimateV2(p) {
    const missing = [];

    if (!(p.vehicleCount > 0)) missing.push("AGV台数");
    if (!(p.stationCount >= 0)) missing.push("ステーション数");
    if (!(p.areaShort_m > 0)) missing.push("走行エリア：短辺");
    if (!(p.areaLong_m > 0)) missing.push("走行エリア：長辺");

    // hard NG: >300m
    if (p.areaShort_m > 300) missing.push("走行エリア：短辺（300m超）");
    if (p.areaLong_m > 300) missing.push("走行エリア：長辺（300m超）");

    // Step2 required: at least one template qty>0
    const totalQty = (p.routes || []).reduce((a, r) => a + (r.qty || 0), 0);
    if (!(totalQty > 0)) missing.push("ルートテンプレート数量（T1〜T6のいずれかを1以上）");

    // if qty>0, veh must be >0 (autoFill should satisfy, but still validate)
    (p.routes || []).forEach((r) => {
      if ((r.qty || 0) > 0 && !((r.veh || 0) > 0)) {
        missing.push(`担当台数（${r.key}）`);
      }
    });

    return { ok: missing.length === 0, missing };
  }

  // --- derive route metrics (simple, observable) ---
  // (exported at end of IIFE)
  function deriveRouteMetricsV2(p) {
    const routes = p.routes || [];
    const totalQty = routes.reduce((a, r) => a + (r.qty || 0), 0);
    const weightedVeh = routes.reduce((a, r) => a + (r.qty || 0) * (r.veh || 0), 0);

    // complexity score by template (adjust later)
    const tplWeight = { T1: 1.0, T2: 1.4, T3: 1.4, T4: 1.7, T5: 2.0, T6: 2.2 };
    const complexity = routes.reduce((a, r) => a + (r.qty || 0) * (tplWeight[r.key] || 1.0), 0);

    // area size proxy (m^2)
    const area = Math.max(0, (p.areaShort_m || 0) * (p.areaLong_m || 0));

    return {
      totalQty,
      weightedVeh,
      complexity,
      area,
    };
  }

  // --- V2 hours: coefficients are placeholders; tune later ---
  // (exported at end of IIFE)
  function calcDesignHoursV2(p, m) {
    // Base + scale by vehicles/stations/route complexity + interfaces + signals + constraints
    const base = 10;

    const perVehicle = 1.2 * (p.vehicleCount || 0);
    const perStation = 0.25 * (p.stationCount || 0);
    const perQty = 0.6 * (m.totalQty || 0);
    const perComplexity = 1.1 * (m.complexity || 0);

    const perEquipment = 1.0 * (p.equipmentCount || 0);
    const perSignals = 0.05 * (p.signalPoints || 0);
    const perJunction = 0.3 * (p.junctionCount || 0);

    const perTape = 0.12 * (p.tapeStops || 0);
    const perLm = 0.35 * (p.lmSpots || 0);

    // narrow aisle penalty if known and <2.0
    const narrowPenalty = (p.minAisleWidth_m > 0 && p.minAisleWidth_m < 2.0) ? 6 : 0;

    // area penalty (very rough): big sites take longer in mapping/design
    const areaPenalty = (m.area > 0) ? Math.min(12, (m.area / 20000) * 3) : 0;

    const raw = base + perVehicle + perStation + perQty + perComplexity
      + perEquipment + perSignals + perJunction + perTape + perLm
      + narrowPenalty + areaPenalty;

    return Math.max(0, raw);
  }

  // (exported at end of IIFE)
  function calcSetupHoursV2(p, m) {
    // Base + scale by route patterns (checks) + vehicles + equipment + constraints + troubleshooting allowances
    const base = 8;

    const perVehicle = 1.5 * (p.vehicleCount || 0);
    const perQty = 0.9 * (m.totalQty || 0);
    const perComplexity = 0.9 * (m.complexity || 0);

    const perEquipment = 1.2 * (p.equipmentCount || 0);
    const perSignals = 0.03 * (p.signalPoints || 0);
    const perJunction = 0.25 * (p.junctionCount || 0);

    const perTape = 0.10 * (p.tapeStops || 0);
    const perLm = 0.25 * (p.lmSpots || 0);

    const narrowPenalty = (p.minAisleWidth_m > 0 && p.minAisleWidth_m < 2.0) ? 8 : 0;

    const areaPenalty = (m.area > 0) ? Math.min(10, (m.area / 25000) * 2.5) : 0;

    const raw = base + perVehicle + perQty + perComplexity
      + perEquipment + perSignals + perJunction + perTape + perLm
      + narrowPenalty + areaPenalty;

    return Math.max(0, raw);
  }

  // (exported at end of IIFE)
  function convertAmounts(hours) {
    // rates: prefer rates-json if your app sets them; fallback to constants you stated
    const costRate = Number.isFinite(window.LABOR_RATE) ? window.LABOR_RATE : 17760;
    const sellRate = Number.isFinite(window.DESIGN_SELL_RATE) ? window.DESIGN_SELL_RATE : 29600; // use one sell rate for both
    const h = Math.ceil(hours || 0);

    return {
      hoursRaw: hours || 0,
      hoursCeil: h,
      cost: h * costRate,
      sell: h * sellRate,
      costRate,
      sellRate,
    };
  }

  // ==============================
  // V2: Sync fixed rows + profit preview on input change
  // ==============================
  // NOTE: This function does NOT navigate steps (no _v2_showStep).
  // It only syncs: Step4 numbers (if visible), fixed detail rows, totals, profit preview.
  function syncV2FromInputs(opts = {}) {
    const {
      updateFixedRows = true,
      updateProfit = true,
      updateStep4IfVisible = true,
      clearOnNg = true
    } = opts;

    // veh auto fill before read
    if (typeof _autoFillV2VehiclesIfBlank === "function") _autoFillV2VehiclesIfBlank();

    const p = readParamsV2FromWizard();
    const v = validateEstimateV2(p);

    // If NG: optionally clear fixed rows / profit preview to avoid stale values
    if (!v.ok) {
      const step4 = document.querySelector('[data-v2-step="4"]');
      const step4Visible = step4 && step4.style.display !== "none";
      if (step4Visible) _renderNg(v.missing);

      // clearOnNg: 固定費行・利益プレビュー・キャッシュをクリア
      if (clearOnNg) {
        // V2_LAST_FEESをクリア
        window.V2_LAST_FEES = null;
        // 利益プレビューをクリア（関数があれば）
        if (typeof window.updateTotalProfitPreview === "function") {
          window.updateTotalProfitPreview({ designFee: 0, setupFee: 0, totalWithFee: 0 }, 0, 0);
        }
        // 固定費行を0円にする
        if (typeof _upsertFixedRowByDescription === "function") {
          _upsertFixedRowByDescription("設計費（V2自動算出）", 0, 1, window.V2_PRODUCT_ID_DESIGN_FEE || "");
          _upsertFixedRowByDescription("現地セットアップ費（V2自動算出）", 0, 1, window.V2_PRODUCT_ID_SETUP_FEE || "");
          window.updateGrandTotal?.();
        }
      }
      return { ok: false, missing: v.missing, params: p };
    }

    const m = deriveRouteMetricsV2(p);
    const designHours = calcDesignHoursV2(p, m);
    const setupHours = calcSetupHoursV2(p, m);

    const design = convertAmounts(designHours);
    const setup = convertAmounts(setupHours);

    // Step4が表示中の時だけ数値表示を追随（Step遷移はしない）
    if (updateStep4IfVisible) {
      const step4 = document.querySelector('[data-v2-step="4"]');
      const step4Visible = step4 && step4.style.display !== "none";
      if (step4Visible) {
        const sb = _buildSafetyBreakdownV2(p, m);
        _renderOk(design, setup, sb.design, sb.setup);
      }
    }

    // fixed rows
    if (updateFixedRows) {
      _upsertFixedRowByDescription("設計費（V2自動算出）", design.sell, 1, window.V2_PRODUCT_ID_DESIGN_FEE || "");
      _upsertFixedRowByDescription("現地セットアップ費（V2自動算出）", setup.sell, 1, window.V2_PRODUCT_ID_SETUP_FEE || "");
      window.updateGrandTotal?.();
    }

    // cache for discount recalc
    const fees = {
      designFee: design.sell,
      setupFee: setup.sell,
      totalWithFee: (design.sell || 0) + (setup.sell || 0),
    };
    window.V2_LAST_FEES = { fees, designCost: design.cost, setupCost: setup.cost };

    // profit preview
    if (updateProfit && typeof window.updateTotalProfitPreview === "function") {
      window.updateTotalProfitPreview(fees, design.cost, setup.cost);
    }

    return { ok: true, design, setup, params: p, metrics: m };
  }

  // export: allow live summary side to call sync
  window.__v2 = window.__v2 || {};
  window.__v2.syncFromInputs = syncV2FromInputs;

  // --- Export V2 functions for Live Summary ---
  window.__v2 = window.__v2 || {};
  window.__v2.readParamsV2FromWizard = readParamsV2FromWizard;
  window.__v2.validateEstimateV2 = validateEstimateV2;
  window.__v2.deriveRouteMetricsV2 = deriveRouteMetricsV2;
  window.__v2.calcDesignHoursV2 = calcDesignHoursV2;
  window.__v2.calcSetupHoursV2 = calcSetupHoursV2;
  window.__v2.convertAmounts = convertAmounts;
  // 初期サマリ描画（export直後が確実）
  window.v2UpdateLiveSummary?.();

  function _renderSafetyList(ulId, breakdown) {
    const ul = _v2_el(ulId);
    if (!ul) return;
    ul.innerHTML = "";
    (breakdown || []).forEach((b) => {
      const li = document.createElement("li");
      const pct = (b.rate != null) ? ` (+${Math.round(b.rate * 100)}%)` : "";
      li.textContent = `${b.label || "要因"}${pct}`;
      ul.appendChild(li);
    });
  }

  // --- fixed rows: description-based upsert ---
  function _upsertFixedRowByDescription(description, unitPrice, quantity, productId = "") {
    const tbody = document.getElementById("detail-body");
    if (!tbody) return null;

    const descNorm = String(description || "").trim();
    if (!descNorm) return null;

    // 2-stage search: fixed rows first, then all rows as fallback (with recovery)
    function findTarget(rows) {
      let exact = null;
      let prefix = null;
      for (const r of rows) {
        const v = (r.querySelector('input[name="description[]"]')?.value || "").trim();
        if (v === descNorm) { exact = r; break; }
        if (!prefix && v.startsWith(descNorm)) prefix = r;
      }
      return exact || prefix;
    }
        let rows = Array.from(tbody.querySelectorAll("tr"));
    let target = findTarget(rows);
    // fallback: scan all rows if not found (recovery)
    // 修正: 全行を対象にし、description一致で救済する
    if (!target) {
      const all = Array.from(tbody.querySelectorAll("tr"));
      target = findTarget(all);
    }
    if (!target) {
      // 固定行が無い場合は新規作成して追加
      if (typeof window.createDetailRow === "function") {
        target = window.createDetailRow();
        if (target) {
          target.classList.add("js-fixed-row");
          tbody.appendChild(target);
        }
      }
    }
    if (!target) return null; // それでも無理なら安全に抜ける

    // disable product select but keep hidden product_id[] posted
    const sel = target.querySelector('select[name="product_id[]"]');
    if (sel) {
      // 既存の hidden product_id[] が複数ある場合は1つに正規化（POST配列の破綻防止）
      const hiddens = Array.from(target.querySelectorAll('input[type="hidden"][name="product_id[]"]'));
      if (hiddens.length > 1) {
        hiddens.slice(1).forEach((x) => x.remove());
      }
      // UI表示目的で入れる（option が無いIDなら反映されないが害はない）
      if (productId) sel.value = String(productId);

      sel.disabled = true;
      sel.setAttribute("data-post-disabled", "1");

      let hidden = target.querySelector('input[type="hidden"][name="product_id[]"]');
      if (!hidden) {
        hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = "product_id[]";
        (sel.closest("td") || sel.parentNode).appendChild(hidden);
      }
      // ★ここが本題：固定費の productId を投稿する
      hidden.value = productId ? String(productId) : "";
    }
// ...existing code...

    // set values
    const desc = target.querySelector('input[name="description[]"]');
    const up = target.querySelector('input[name="unit_price[]"]');
    const qty = target.querySelector('input[name="quantity[]"]');
    const sub = target.querySelector('input[name="subtotal[]"]');

    if (desc) { desc.value = descNorm; desc.readOnly = true; }
    if (up) { up.value = String(Math.round(unitPrice || 0)); up.readOnly = true; }
    if (qty) { qty.value = String(Math.round(quantity || 1)); qty.readOnly = true; }

    const subtotal = Math.round((unitPrice || 0) * (quantity || 1));
    if (sub) sub.value = subtotal > 0 ? subtotal.toLocaleString() : "";

    // disable buttons
    const addBtn = target.querySelector("button.add-row");
    const rmBtn = target.querySelector("button.remove-row, button.remove-row-btn");
    if (addBtn) addBtn.disabled = true;
    if (rmBtn) rmBtn.disabled = true;

    return target;
  }

  function _renderNg(missing) {
    const okBox = _v2_el("v2_resultOk");
    const ngBox = _v2_el("v2_resultNg");
    if (okBox) okBox.style.display = "none";
    if (ngBox) ngBox.style.display = "";

    const ul = _v2_el("v2_missingList");
    if (ul) {
      ul.innerHTML = "";
      (missing || []).forEach((m) => {
        const li = document.createElement("li");
        li.textContent = String(m);
        ul.appendChild(li);
      });
    }

    // 安全側：Safety欄は空にする（未定義参照しない）
    _renderSafetyList("v2_designSafetyList", []);
    _renderSafetyList("v2_setupSafetyList", []);
  }

  function _buildSafetyBreakdownV2(p, m) {
    // store {label, rate} only (per your design)
    const common = [];

    if ((p.equipmentCount || 0) > 0) common.push({ label: "外部設備連携あり", rate: 0.10 });
    if ((p.signalPoints || 0) >= 16) common.push({ label: "信号点数が多い", rate: 0.10 });
    if ((p.junctionCount || 0) >= 10) common.push({ label: "交差点/合流が多い", rate: 0.10 });
    if ((p.tapeStops || 0) > 0) common.push({ label: "磁気テープ停止点あり", rate: 0.05 });
    if ((p.lmSpots || 0) > 0) common.push({ label: "ランドマーク対策あり", rate: 0.08 });
    if (p.minAisleWidth_m > 0 && p.minAisleWidth_m < 2.0) common.push({ label: "狭通路（すれ違い不可）", rate: 0.15 });
    if ((m.complexity || 0) >= 10) common.push({ label: "ルートが複雑", rate: 0.12 });

    // design/setup can share for now; later split if needed
    return { design: common.slice(), setup: common.slice() };
  }

  // --- run estimate ---
  function runEstimateV2() {
    // ensure Step2 veh auto-fill happens before reading params
    if (typeof _autoFillV2VehiclesIfBlank === "function") _autoFillV2VehiclesIfBlank();

    const p = readParamsV2FromWizard();
    const v = validateEstimateV2(p);

    // always go Step4
    _v2_showStep(4);

    if (!v.ok) {
      _renderNg(v.missing);
      // do not calculate / do not touch fixed rows
      return;
    }

    const m = deriveRouteMetricsV2(p);

    // compute
    const designHours = calcDesignHoursV2(p, m);
    const setupHours = calcSetupHoursV2(p, m);

    const design = convertAmounts(designHours);
    const setup = convertAmounts(setupHours);

    // safety breakdown
    const sb = _buildSafetyBreakdownV2(p, m);

    // render
    _renderOk(design, setup, sb.design, sb.setup);

    // upsert fixed rows into 明細 (sell price in unit_price)
    _upsertFixedRowByDescription("設計費（V2自動算出）", design.sell, 1, window.V2_PRODUCT_ID_DESIGN_FEE || "");
    _upsertFixedRowByDescription("現地セットアップ費（V2自動算出）", setup.sell, 1, window.V2_PRODUCT_ID_SETUP_FEE || "");

    // totals/profit update
    window.updateGrandTotal?.();

    const fees = {
      designFee: design.sell,
      setupFee: setup.sell,
      totalWithFee: (design.sell || 0) + (setup.sell || 0),
    };

    // keep last for discount re-calc
    window.V2_LAST_FEES = { fees, designCost: design.cost, setupCost: setup.cost };

    if (typeof window.updateTotalProfitPreview === "function") {
      window.updateTotalProfitPreview(fees, design.cost, setup.cost);
    }
    // ライブサマリーも同期
    window.v2UpdateLiveSummary?.();
  }

  function _bindV2Run() {
    const runBtn = _v2_el("v2_btn_run");
    if (!runBtn) return;

    // click -> run, then stay on Step4
    runBtn.addEventListener("click", function (e) {
      // type=button but keep safe
      e.preventDefault();
      runEstimateV2();
    });
  }

  function _bindDiscountRecalcForV2() {
    const el = document.getElementById("discount_amount");
    if (!el) return;
    el.addEventListener("input", function () {
      const st = window.V2_LAST_FEES;
      if (!st || !st.fees) return;
      if (typeof window.updateTotalProfitPreview === "function") {
        window.updateTotalProfitPreview(st.fees, st.designCost || 0, st.setupCost || 0);
      }
    });
  }

  function _v2_init() {
    if (window.__v2WizardBound) return;
    window.__v2WizardBound = true;
    _v2_bindWizardNav();
    _bindV2Run();
    _bindDiscountRecalcForV2();
    _v2_showStep(1);
  }

  // すでにDOMが出来ている可能性が高いので即時/保険の両対応
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _v2_init, { once: true });
  } else {
    _v2_init();
  }
  // --- Initial live summary sync ---
  if (typeof window.v2UpdateLiveSummary === "function") {
    window.v2UpdateLiveSummary();
  }
})();

  setTimeout(() => {
    const selects = document.querySelectorAll('select.product-select-custom');
    console.log(`[quotation_form.js] product-select-custom count (init):`, selects.length);
  }, 0);

  console.log(
    "[quotation_form.js] typeof updateAutoFeePreview =",
    typeof window.updateAutoFeePreview,
    ", typeof calcDesignHours =",
    typeof window.calcDesignHours,
    ", typeof updateTotalProfitPreview =",
    typeof window.updateTotalProfitPreview
  );

  // ==============================
  // 診断用: POST配列長チェック（submit時にconsole出力 / 1回だけ）
  // ==============================
  if (!window.__postLenDiagBound) {
    window.__postLenDiagBound = true;
    const form = document.querySelector("form");
    if (form) {
      form.addEventListener("submit", () => {
        const len = (sel) => document.querySelectorAll(sel).length;
        console.log("[POST len]",
          "product_id[]:", len('select[name="product_id[]"]') + len('input[type="hidden"][name="product_id[]"]'),
          "desc[]:", len('input[name="description[]"]'),
          "unit_price[]:", len('input[name="unit_price[]"]'),
          "qty[]:", len('input[name="quantity[]"]'),
          "subtotal[]:", len('input[name="subtotal[]"]'),
        );
      });
    }
  }

  console.log("[quotation_form.js] DOMContentLoaded - init done");
});

